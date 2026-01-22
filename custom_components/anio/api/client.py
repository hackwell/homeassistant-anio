"""ANIO API client for Home Assistant integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import aiohttp

from ..const import (
    API_URL,
    RATE_LIMIT_BACKOFF_BASE,
    RATE_LIMIT_MAX_RETRIES,
    VALID_EMOJI_CODES,
)
from .exceptions import (
    AnioApiError,
    AnioConnectionError,
    AnioDeviceNotFoundError,
    AnioMessageTooLongError,
    AnioRateLimitError,
)
from .models import ActivityItem, ChatMessage, Device, Geofence, LocationInfo

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from .auth import AnioAuth

_LOGGER = logging.getLogger(__name__)


class AnioApiClient:
    """Client for the ANIO Cloud API."""

    def __init__(self, session: ClientSession, auth: AnioAuth) -> None:
        """Initialize the API client.

        Args:
            session: aiohttp client session.
            auth: Authentication handler.
        """
        self._session = session
        self._auth = auth
        self._retry_count = 0

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: dict,
    ) -> dict | list | None:
        """Make an authenticated API request.

        Args:
            method: HTTP method.
            endpoint: API endpoint.
            **kwargs: Additional arguments for aiohttp request.

        Returns:
            JSON response data.

        Raises:
            AnioApiError: If the request fails.
            AnioRateLimitError: If rate limited.
            AnioConnectionError: If connection fails.
        """
        token = await self._auth.ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "app-uuid": self._auth.app_uuid,
            "Content-Type": "application/json",
            **kwargs.pop("headers", {}),
        }

        url = f"{API_URL}{endpoint}"

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                **kwargs,
            ) as response:
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    await self._handle_rate_limit(retry_after)
                    # Retry the request
                    return await self._request(method, endpoint, **kwargs)

                if response.status == 404:
                    raise AnioDeviceNotFoundError("unknown")

                if response.status >= 400:
                    text = await response.text()
                    raise AnioApiError(f"API error: {text}", response.status)

                self._retry_count = 0  # Reset on success

                if response.status == 204:
                    return None

                return await response.json()

        except aiohttp.ClientError as err:
            raise AnioConnectionError(f"Connection failed: {err}") from err

    async def _handle_rate_limit(self, retry_after: str | None) -> None:
        """Handle rate limiting with exponential backoff.

        Args:
            retry_after: Retry-After header value.

        Raises:
            AnioRateLimitError: If max retries exceeded.
        """
        self._retry_count += 1

        if self._retry_count > RATE_LIMIT_MAX_RETRIES:
            self._retry_count = 0
            raise AnioRateLimitError("Max retries exceeded")

        if retry_after:
            wait_time = int(retry_after)
        else:
            wait_time = RATE_LIMIT_BACKOFF_BASE**self._retry_count

        _LOGGER.warning(
            "Rate limited, waiting %d seconds (attempt %d/%d)",
            wait_time,
            self._retry_count,
            RATE_LIMIT_MAX_RETRIES,
        )
        await asyncio.sleep(wait_time)

    async def get_devices(self) -> list[Device]:
        """Get all devices for the authenticated user.

        Returns:
            List of devices.
        """
        data = await self._request("GET", "/v1/device/list")
        if not isinstance(data, list):
            return []
        return [Device.model_validate(d) for d in data]

    async def get_device(self, device_id: str) -> Device:
        """Get a specific device.

        Args:
            device_id: The device ID.

        Returns:
            The device.

        Raises:
            AnioDeviceNotFoundError: If device not found.
        """
        try:
            data = await self._request("GET", f"/v1/device/{device_id}")
            return Device.model_validate(data)
        except AnioDeviceNotFoundError:
            raise AnioDeviceNotFoundError(device_id) from None

    async def find_device(self, device_id: str) -> None:
        """Request current location from a device.

        Args:
            device_id: The device ID.
        """
        await self._request("POST", f"/v1/device/{device_id}/find")
        _LOGGER.debug("Location request sent to device %s", device_id)

    async def power_off_device(self, device_id: str) -> None:
        """Power off a device.

        Args:
            device_id: The device ID.
        """
        await self._request("POST", f"/v1/device/{device_id}/poweroff")
        _LOGGER.info("Power off command sent to device %s", device_id)

    async def send_text_message(
        self,
        device_id: str,
        text: str,
        username: str | None = None,
        max_length: int = 95,
    ) -> ChatMessage:
        """Send a text message to a device.

        Args:
            device_id: The device ID.
            text: Message text.
            username: Optional sender name.
            max_length: Maximum message length.

        Returns:
            The created message.

        Raises:
            AnioMessageTooLongError: If message exceeds max length.
        """
        if len(text) > max_length:
            raise AnioMessageTooLongError(len(text), max_length)

        payload: dict[str, str] = {
            "deviceId": device_id,
            "text": text,
        }
        if username:
            payload["username"] = username

        data = await self._request("POST", "/v1/chat/message/text", json=payload)
        return ChatMessage.model_validate(data)

    async def send_emoji_message(
        self,
        device_id: str,
        emoji_code: str,
        username: str | None = None,
    ) -> ChatMessage:
        """Send an emoji message to a device.

        Args:
            device_id: The device ID.
            emoji_code: Emoji code (E01-E12).
            username: Optional sender name.

        Returns:
            The created message.

        Raises:
            AnioApiError: If invalid emoji code.
        """
        if emoji_code not in VALID_EMOJI_CODES:
            raise AnioApiError(
                f"Invalid emoji code: {emoji_code}. Valid codes: {VALID_EMOJI_CODES}"
            )

        payload: dict[str, str] = {
            "deviceId": device_id,
            "text": emoji_code,
        }
        if username:
            payload["username"] = username

        data = await self._request("POST", "/v1/chat/message/emoji", json=payload)
        return ChatMessage.model_validate(data)

    async def get_activity(
        self,
        from_time: datetime | None = None,
    ) -> list[ActivityItem]:
        """Get activity feed including messages.

        Args:
            from_time: Optional start time for activity feed.

        Returns:
            List of activity items.
        """
        params = {}
        if from_time:
            params["from"] = from_time.isoformat()

        data = await self._request("GET", "/v1/activity", params=params)
        if not isinstance(data, list):
            return []

        result = []
        for item in data:
            try:
                result.append(ActivityItem.model_validate(item))
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Failed to parse activity item: %s", err)

        return result

    async def get_geofences(self) -> list[Geofence]:
        """Get all geofences.

        Returns:
            List of geofences.
        """
        try:
            data = await self._request("GET", "/v1/geofence")
            if not isinstance(data, list):
                return []
            return [Geofence.model_validate(g) for g in data]
        except AnioDeviceNotFoundError:
            # 404 means no geofences exist, which is valid
            _LOGGER.debug("No geofences found (404 response)")
            return []

    async def get_device_location(self, device_id: str) -> LocationInfo | None:
        """Get the current location of a device.

        This is typically included in the device activity feed.

        Args:
            device_id: The device ID.

        Returns:
            Location info or None if not available.
        """
        # Location is usually obtained from activity feed
        # This is a placeholder for direct location query if available
        activity = await self.get_activity()

        for item in activity:
            if item.device_id == device_id and item.type == "LOCATION" and item.data:
                try:
                    return LocationInfo.model_validate(item.data)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Failed to parse location: %s", err)

        return None
