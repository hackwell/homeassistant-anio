"""Tests for ANIO API authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.anio.api import AnioAuth, AnioAuthError, AnioOtpRequiredError
from custom_components.anio.api.models import AuthTokens


class TestAnioAuth:
    """Tests for AnioAuth class."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock aiohttp session."""
        session = MagicMock()
        session.post = MagicMock()
        return session

    @pytest.fixture
    def auth(self, mock_session: MagicMock) -> AnioAuth:
        """Create an auth instance for testing."""
        return AnioAuth(
            session=mock_session,
            email="test@example.com",
            password="password123",
        )

    def test_init_with_credentials(self, mock_session: MagicMock) -> None:
        """Test initialization with email and password."""
        auth = AnioAuth(
            session=mock_session,
            email="test@example.com",
            password="password123",
        )
        assert auth.access_token is None
        assert auth.refresh_token is None
        assert auth.app_uuid is not None

    def test_init_with_tokens(self, mock_session: MagicMock) -> None:
        """Test initialization with existing tokens."""
        # Token with expiry far in the future
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE5OTk5OTk5OTl9.test"
        auth = AnioAuth(
            session=mock_session,
            access_token=token,
            refresh_token="refresh_token",
            app_uuid="test-uuid",
        )
        assert auth.access_token == token
        assert auth.refresh_token == "refresh_token"
        assert auth.app_uuid == "test-uuid"

    def test_is_token_valid_no_token(self, mock_session: MagicMock) -> None:
        """Test is_token_valid returns False when no token."""
        auth = AnioAuth(session=mock_session)
        assert auth.is_token_valid is False

    def test_is_token_valid_with_valid_token(self, mock_session: MagicMock) -> None:
        """Test is_token_valid returns True for valid token."""
        # Create a token that expires far in the future
        future_exp = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        import base64
        import json
        payload = base64.urlsafe_b64encode(
            json.dumps({"exp": future_exp}).encode()
        ).decode().rstrip("=")
        token = f"header.{payload}.signature"

        auth = AnioAuth(
            session=mock_session,
            access_token=token,
        )
        assert auth.is_token_valid is True

    def test_is_token_valid_with_expired_token(self, mock_session: MagicMock) -> None:
        """Test is_token_valid returns False for expired token."""
        # Create a token that expired in the past
        past_exp = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        import base64
        import json
        payload = base64.urlsafe_b64encode(
            json.dumps({"exp": past_exp}).encode()
        ).decode().rstrip("=")
        token = f"header.{payload}.signature"

        auth = AnioAuth(
            session=mock_session,
            access_token=token,
        )
        assert auth.is_token_valid is False

    @pytest.mark.asyncio
    async def test_login_success(self, auth: AnioAuth, mock_session: MagicMock) -> None:
        """Test successful login."""
        response_data = {
            "accessToken": "new_access_token",
            "refreshToken": "new_refresh_token",
            "isOtpCodeRequired": False,
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = mock_response

        tokens = await auth.login()

        assert isinstance(tokens, AuthTokens)
        assert tokens.access_token == "new_access_token"
        assert tokens.refresh_token == "new_refresh_token"
        assert auth.access_token == "new_access_token"
        assert auth.refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(
        self, auth: AnioAuth, mock_session: MagicMock
    ) -> None:
        """Test login with invalid credentials."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = mock_response

        with pytest.raises(AnioAuthError, match="Invalid email or password"):
            await auth.login()

    @pytest.mark.asyncio
    async def test_login_otp_required(
        self, auth: AnioAuth, mock_session: MagicMock
    ) -> None:
        """Test login when OTP is required."""
        response_data = {
            "accessToken": "",
            "refreshToken": "",
            "isOtpCodeRequired": True,
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = mock_response

        with pytest.raises(AnioOtpRequiredError):
            await auth.login()

    @pytest.mark.asyncio
    async def test_login_with_otp(
        self, auth: AnioAuth, mock_session: MagicMock
    ) -> None:
        """Test login with OTP code."""
        response_data = {
            "accessToken": "new_access_token",
            "refreshToken": "new_refresh_token",
            "isOtpCodeRequired": False,
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = mock_response

        tokens = await auth.login(otp_code="123456")

        assert tokens.access_token == "new_access_token"
        # Verify OTP was included in request
        call_kwargs = mock_session.post.call_args
        assert "json" in call_kwargs.kwargs
        assert call_kwargs.kwargs["json"]["otpCode"] == "123456"

    @pytest.mark.asyncio
    async def test_refresh_success(self, mock_session: MagicMock) -> None:
        """Test successful token refresh."""
        auth = AnioAuth(
            session=mock_session,
            refresh_token="old_refresh_token",
            app_uuid="test-uuid",
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"accessToken": "new_access_token"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = mock_response

        new_token = await auth.refresh()

        assert new_token == "new_access_token"
        assert auth.access_token == "new_access_token"

    @pytest.mark.asyncio
    async def test_refresh_no_token(self, mock_session: MagicMock) -> None:
        """Test refresh without refresh token."""
        auth = AnioAuth(session=mock_session)

        with pytest.raises(AnioAuthError, match="No refresh token available"):
            await auth.refresh()

    @pytest.mark.asyncio
    async def test_refresh_expired(self, mock_session: MagicMock) -> None:
        """Test refresh with expired token."""
        auth = AnioAuth(
            session=mock_session,
            refresh_token="expired_token",
        )

        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = mock_response

        with pytest.raises(AnioAuthError, match="Refresh token expired"):
            await auth.refresh()

    @pytest.mark.asyncio
    async def test_ensure_valid_token_already_valid(
        self, mock_session: MagicMock
    ) -> None:
        """Test ensure_valid_token when token is already valid."""
        # Create a valid token
        future_exp = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        import base64
        import json
        payload = base64.urlsafe_b64encode(
            json.dumps({"exp": future_exp}).encode()
        ).decode().rstrip("=")
        token = f"header.{payload}.signature"

        auth = AnioAuth(
            session=mock_session,
            access_token=token,
            refresh_token="refresh_token",
        )

        result = await auth.ensure_valid_token()

        assert result == token
        # Verify no refresh was attempted
        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_valid_token_needs_refresh(
        self, mock_session: MagicMock
    ) -> None:
        """Test ensure_valid_token when token needs refresh."""
        # Create an expired token
        past_exp = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        import base64
        import json
        payload = base64.urlsafe_b64encode(
            json.dumps({"exp": past_exp}).encode()
        ).decode().rstrip("=")
        token = f"header.{payload}.signature"

        auth = AnioAuth(
            session=mock_session,
            access_token=token,
            refresh_token="refresh_token",
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"accessToken": "new_token"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = mock_response

        result = await auth.ensure_valid_token()

        assert result == "new_token"

    @pytest.mark.asyncio
    async def test_logout(self, mock_session: MagicMock) -> None:
        """Test logout."""
        auth = AnioAuth(
            session=mock_session,
            access_token="access_token",
            refresh_token="refresh_token",
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post.return_value = mock_response

        await auth.logout()

        assert auth.access_token is None
        assert auth.refresh_token is None
