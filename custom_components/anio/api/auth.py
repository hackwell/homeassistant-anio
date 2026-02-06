"""Authentication handling for the ANIO API."""

from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import aiohttp

from ..const import API_URL, CLIENT_ID, TOKEN_REFRESH_BUFFER
from .exceptions import AnioAuthError, AnioConnectionError, AnioOtpRequiredError
from .models import AuthTokens

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from aiohttp import ClientSession

    TokenRefreshCallback = Callable[[str, str], Coroutine[None, None, None]]

_LOGGER = logging.getLogger(__name__)


class AnioAuth:
    """Handle authentication with the ANIO API."""

    def __init__(
        self,
        session: ClientSession,
        email: str | None = None,
        password: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        app_uuid: str | None = None,
        on_token_refresh: TokenRefreshCallback | None = None,
    ) -> None:
        """Initialize the auth handler.

        Args:
            session: aiohttp client session.
            email: User email for login.
            password: User password for login.
            access_token: Existing access token.
            refresh_token: Existing refresh token.
            app_uuid: App UUID for API requests.
            on_token_refresh: Callback when tokens are refreshed.
        """
        self._session = session
        self._email = email
        self._password = password
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._app_uuid = app_uuid or str(uuid.uuid4())
        self._token_expiry: datetime | None = None
        self._on_token_refresh = on_token_refresh

        if access_token:
            self._token_expiry = self._parse_jwt_expiry(access_token)

    @property
    def access_token(self) -> str | None:
        """Get the current access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        """Get the current refresh token."""
        return self._refresh_token

    @property
    def app_uuid(self) -> str:
        """Get the app UUID."""
        return self._app_uuid

    @property
    def is_token_valid(self) -> bool:
        """Check if the current token is valid."""
        if not self._access_token or not self._token_expiry:
            return False

        # Consider token invalid if it expires within the buffer period
        buffer = timedelta(seconds=TOKEN_REFRESH_BUFFER)
        return datetime.now(timezone.utc) < (self._token_expiry - buffer)

    def _parse_jwt_expiry(self, token: str) -> datetime | None:
        """Parse the expiry time from a JWT token.

        Args:
            token: The JWT token.

        Returns:
            The expiry datetime or None if parsing fails.
        """
        try:
            # JWT format: header.payload.signature
            parts = token.split(".")
            if len(parts) != 3:
                return None

            # Decode the payload (with padding fix)
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding

            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)

            if "exp" in data:
                return datetime.fromtimestamp(data["exp"], tz=timezone.utc)
        except (ValueError, KeyError, json.JSONDecodeError) as err:
            _LOGGER.debug("Failed to parse JWT expiry: %s", err)

        return None

    async def login(self, otp_code: str | None = None) -> AuthTokens:
        """Authenticate with email and password.

        Args:
            otp_code: OTP code for 2FA if required.

        Returns:
            AuthTokens with access and refresh tokens.

        Raises:
            AnioAuthError: If authentication fails.
            AnioOtpRequiredError: If OTP code is required.
            AnioConnectionError: If connection fails.
        """
        if not self._email or not self._password:
            raise AnioAuthError("Email and password are required for login")

        headers = {
            "client-id": CLIENT_ID,
            "app-uuid": self._app_uuid,
            "Content-Type": "application/json",
        }

        payload: dict[str, str] = {
            "email": self._email,
            "password": self._password,
        }

        if otp_code:
            payload["otpCode"] = otp_code

        try:
            async with self._session.post(
                f"{API_URL}/v1/auth/login",
                headers=headers,
                json=payload,
            ) as response:
                if response.status == 401:
                    raise AnioAuthError("Invalid email or password")

                if response.status != 200:
                    text = await response.text()
                    raise AnioAuthError(f"Login failed: {text}")

                data = await response.json()
                tokens = AuthTokens.model_validate(data)

                if tokens.is_otp_required and not otp_code:
                    raise AnioOtpRequiredError()

                self._access_token = tokens.access_token
                self._refresh_token = tokens.refresh_token
                self._token_expiry = self._parse_jwt_expiry(tokens.access_token)

                _LOGGER.debug("Login successful, token expires at %s", self._token_expiry)
                return tokens

        except aiohttp.ClientError as err:
            raise AnioConnectionError(f"Connection failed: {err}") from err

    async def refresh(self) -> str:
        """Refresh the access token.

        Returns:
            The new access token.

        Raises:
            AnioAuthError: If refresh fails.
            AnioConnectionError: If connection fails.
        """
        if not self._refresh_token:
            raise AnioAuthError("No refresh token available")

        headers = {
            "Authorization": f"Bearer {self._refresh_token}",
            "client-id": CLIENT_ID,
            "app-uuid": self._app_uuid,
        }

        try:
            async with self._session.post(
                f"{API_URL}/v1/auth/refresh-access-token",
                headers=headers,
            ) as response:
                if response.status == 401:
                    raise AnioAuthError("Refresh token expired")

                if response.status != 200:
                    text = await response.text()
                    raise AnioAuthError(f"Token refresh failed: {text}")

                data = await response.json()
                self._access_token = data.get("accessToken")
                self._token_expiry = self._parse_jwt_expiry(self._access_token or "")

                # Capture rotated refresh token if provided
                new_refresh = data.get("refreshToken")
                if new_refresh:
                    self._refresh_token = new_refresh

                _LOGGER.debug(
                    "Token refreshed, new expiry at %s", self._token_expiry
                )

                # Notify listeners about token update
                if self._on_token_refresh:
                    await self._on_token_refresh(
                        self._access_token or "",
                        self._refresh_token or "",
                    )

                return self._access_token or ""

        except aiohttp.ClientError as err:
            raise AnioConnectionError(f"Connection failed: {err}") from err

    async def ensure_valid_token(self) -> str:
        """Ensure we have a valid access token, refreshing if necessary.

        Returns:
            A valid access token.

        Raises:
            AnioAuthError: If no valid token can be obtained.
        """
        if self.is_token_valid and self._access_token:
            return self._access_token

        _LOGGER.debug("Token expired or expiring soon, refreshing...")
        return await self.refresh()

    async def logout(self) -> None:
        """Logout and invalidate the session.

        Raises:
            AnioConnectionError: If connection fails.
        """
        if not self._access_token:
            return

        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            async with self._session.post(
                f"{API_URL}/v1/auth/logout",
                headers=headers,
            ) as response:
                if response.status == 200:
                    _LOGGER.debug("Logout successful")

        except aiohttp.ClientError as err:
            _LOGGER.warning("Logout failed: %s", err)

        finally:
            self._access_token = None
            self._refresh_token = None
            self._token_expiry = None
