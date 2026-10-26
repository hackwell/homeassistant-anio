"""ANIO API client for Home Assistant integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any, cast

import aiohttp
from pydantic import ValidationError

from ..const import (
    API_URL,
    DEFAULT_SENDER_NAME,
    RATE_LIMIT_BACKOFF_BASE,
    RATE_LIMIT_MAX_RETRIES,
    RATE_LIMIT_MAX_WAIT,
    VALID_EMOJI_CODES,
)
from .exceptions import (
    AnioApiError,
    AnioAuthError,
    AnioConnectionError,
    AnioDeviceNotFoundError,
    AnioInvalidEmojiError,
    AnioMessageTooLongError,
    AnioRateLimitError,
)
from .models import (
    ActivityItem,
    AlarmClock,
    ChatMessage,
    Device,
    DeviceLocation,
    Geofence,
    SchoolWayTime,
    SilenceTime,
)

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from .auth import AnioAuth

_LOGGER = logging.getLogger(__name__)


def _describe_parse_error(err: Exception) -> str:
    """Describe a parse error without the API data it contains.

    Pydantic includes the offending input value in its message, which can be
    a chat text or location. Only log field names and error types.
    """
    if isinstance(err, ValidationError):
        return "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['type']}"
            for error in err.errors(include_input=False, include_url=False)
        )
    return type(err).__name__


def _parse_retry_after(value: str | None) -> int | None:
    """Convert a Retry-After header into seconds.

    The header holds either a number of seconds or an HTTP date.

    Args:
        value: The header value.

    Returns:
        Seconds to wait, or None if the value is missing or unreadable.
    """
    if not value:
        return None
    if value.strip().isdigit():
        return int(value)
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    return max(0, round((retry_at - datetime.now(UTC)).total_seconds()))


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
        # Set when the API asked for a long pause; no requests until then
        self._rate_limited_until: datetime | None = None
        # Parse problems already reported as warning (logged once each)
        self._reported_parse_errors: set[str] = set()

    def _warn_unreadable(self, what: str, err: ValidationError) -> None:
        """Log an unreadable API entry, as warning only the first time.

        Args:
            what: Short description of the skipped entry.
            err: The validation error.
        """
        message = f"{what}: {_describe_parse_error(err)}"
        if message in self._reported_parse_errors:
            _LOGGER.debug("%s", message)
            return
        self._reported_parse_errors.add(message)
        _LOGGER.warning("%s", message)

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
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
        if self._rate_limited_until:
            remaining = (self._rate_limited_until - datetime.now(UTC)).total_seconds()
            if remaining > 0:
                raise AnioRateLimitError(
                    "Rate limited, waiting for the ANIO API",
                    retry_after=round(remaining),
                )
            self._rate_limited_until = None

        token = await self._auth.ensure_valid_token()

        extra_headers = kwargs.pop("headers", {})
        headers = {
            "Authorization": f"Bearer {token}",
            "app-uuid": self._auth.app_uuid,
            "Content-Type": "application/json",
            **extra_headers,
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
                else:
                    if response.status == 401:
                        raise AnioAuthError("Access token rejected by server")

                    if response.status == 404:
                        raise AnioDeviceNotFoundError("unknown")

                    if response.status >= 400:
                        text = await response.text()
                        raise AnioApiError(f"API error: {text}", response.status)

                    self._retry_count = 0  # Reset on success

                    if response.status == 204:
                        return None

                    return cast(dict | list, await response.json())

        except aiohttp.ClientError as err:
            raise AnioConnectionError(f"Connection failed: {err}") from err

        # Wait only after the 429 response has been released, then retry
        await self._handle_rate_limit(retry_after)
        return await self._request(method, endpoint, headers=extra_headers, **kwargs)

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

        wait_time = _parse_retry_after(retry_after)
        if wait_time is None:
            wait_time = RATE_LIMIT_BACKOFF_BASE**self._retry_count

        if wait_time > RATE_LIMIT_MAX_WAIT:
            self._retry_count = 0
            self._rate_limited_until = datetime.now(UTC) + timedelta(seconds=wait_time)
            _LOGGER.warning("Rate limited, pausing requests for %d seconds", wait_time)
            raise AnioRateLimitError(
                "Rate limited, waiting for the ANIO API", retry_after=wait_time
            )

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

        # Validate each device on its own, so one unexpected entry doesn't
        # make all watches unavailable.
        result = []
        for item in data:
            try:
                result.append(Device.model_validate(item))
            except ValidationError as err:
                self._warn_unreadable("Skipping a device the integration can't read", err)
        return result

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
        """Make the watch ring and vibrate (ANIO app: "Uhr finden").

        This does not request a new location.

        Args:
            device_id: The device ID.
        """
        await self._request("POST", f"/v1/device/{device_id}/find")
        _LOGGER.debug("Ring request sent to device %s", device_id)

    async def locate_device(self, device_id: str) -> None:
        """Ask the watch for a new position now (ANIO app: "Einmalortung").

        The watch stays silent; the position arrives within about a minute.

        Args:
            device_id: The device ID.
        """
        await self._request("POST", f"/v1/device/{device_id}/cr")
        _LOGGER.debug("Locate request sent to device %s", device_id)

    async def set_explorer_mode(self, device_id: str, active: bool) -> None:
        """Start or stop the explorer mode (locating every 5 minutes for 1 h).

        Args:
            device_id: The device ID.
            active: True to start, False to stop.
        """
        await self._request(
            "POST", "/v1/explorer", json={"deviceId": device_id, "activate": active}
        )
        _LOGGER.debug("Explorer mode %s for device %s", active, device_id)

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
            username: Sender name shown on the watch (default "Home Assistant").
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
            "username": username or DEFAULT_SENDER_NAME,
        }

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
            username: Sender name shown on the watch (default "Home Assistant").

        Returns:
            The created message.

        Raises:
            AnioApiError: If invalid emoji code.
        """
        if emoji_code not in VALID_EMOJI_CODES:
            raise AnioInvalidEmojiError(emoji_code)

        payload: dict[str, str] = {
            "deviceId": device_id,
            "text": emoji_code,
            "username": username or DEFAULT_SENDER_NAME,
        }

        data = await self._request("POST", "/v1/chat/message/emoji", json=payload)
        return ChatMessage.model_validate(data)

    async def get_activity(self, device_id: str) -> list[ActivityItem]:
        """Get the alerts of a device (geofence entered/left, low battery, ...).

        Chat messages are not part of this feed.

        Args:
            device_id: The device ID.

        Returns:
            List of activity items.
        """
        data = await self._request(
            "GET", "/v1/activity", params={"deviceId": device_id}
        )
        if not isinstance(data, list):
            return []

        result = []
        for item in data:
            try:
                result.append(ActivityItem.model_validate(item))
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug(
                    "Failed to parse activity item: %s", _describe_parse_error(err)
                )

        return result

    async def get_geofences(self, device_id: str) -> list[Geofence]:
        """Get the geofences of a device.

        Args:
            device_id: The device ID.

        Returns:
            List of geofences.
        """
        try:
            data = await self._request("GET", f"/v1/geofence/{device_id}")
            if not isinstance(data, list):
                return []
        except AnioDeviceNotFoundError:
            _LOGGER.debug("No geofences for device %s (404)", device_id)
            return []

        # One broken geofence shouldn't stop the whole update
        result = []
        for item in data:
            try:
                result.append(Geofence.model_validate(item))
            except ValidationError as err:
                self._warn_unreadable(
                    "Skipping a geofence the integration can't read", err
                )
        return result

    async def get_device_locations(self, device_id: str) -> list[DeviceLocation]:
        """Get location entries for a device.

        Args:
            device_id: The device ID.

        Returns:
            List of location entries, empty on 404.
        """
        try:
            data = await self._request("GET", f"/v1/location/{device_id}")
            if not isinstance(data, list):
                return []
            return [DeviceLocation.model_validate(loc) for loc in data]
        except AnioDeviceNotFoundError:
            _LOGGER.debug("No location data for device %s (404)", device_id)
            return []

    async def get_last_location(self, device_id: str) -> DeviceLocation | None:
        """Get the most recent location for a device.

        Args:
            device_id: The device ID.

        Returns:
            The last location entry, or None if unavailable.
        """
        try:
            data = await self._request("GET", f"/v1/location/{device_id}/last")
            if not isinstance(data, dict):
                return None
            return DeviceLocation.model_validate(data)
        except ValidationError as err:
            # Treat an unreadable location like no location (battery and
            # signal become unknown) instead of failing the whole update.
            self._warn_unreadable(
                f"Ignoring a location the integration can't read for device {device_id}",
                err,
            )
            return None
        except AnioDeviceNotFoundError:
            _LOGGER.debug("No last location for device %s (404)", device_id)
            return None

    async def send_flower(self, device_id: str, amount: int = 1) -> None:
        """Send a flower (praise) to a device.

        Args:
            device_id: The device ID.
            amount: Number of flowers to send (0-99).
        """
        await self._request(
            "POST", f"/v1/device/{device_id}/flower", json={"amount": amount}
        )
        _LOGGER.debug("Flower sent to device %s", device_id)

    async def get_chat_history(self, device_id: str) -> list[ChatMessage]:
        """Get chat history for a device.

        Args:
            device_id: The device ID.

        Returns:
            List of chat messages, empty on 404.
        """
        try:
            data = await self._request("GET", f"/v1/chat/{device_id}")
            if not isinstance(data, list):
                return []

            result = []
            for msg in data:
                try:
                    result.append(ChatMessage.model_validate(msg))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Failed to parse chat message: %s",
                        _describe_parse_error(err),
                    )
            return result
        except AnioDeviceNotFoundError:
            _LOGGER.debug("No chat history for device %s (404)", device_id)
            return []

    async def get_alarms(self, device_id: str) -> list[AlarmClock]:
        """Get alarm clocks for a device.

        Args:
            device_id: The device ID.

        Returns:
            List of alarm clocks, empty on error.
        """
        try:
            data = await self._request("GET", f"/v1/alarm-clock/{device_id}")
            if not isinstance(data, list):
                return []

            result = []
            for item in data:
                try:
                    result.append(AlarmClock.model_validate(item))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Failed to parse alarm clock: %s",
                        _describe_parse_error(err),
                    )
            return result
        except AnioDeviceNotFoundError:
            _LOGGER.debug("No alarms for device %s (404)", device_id)
            return []

    async def create_alarm(
        self,
        device_id: str,
        time: str,
        days: list[str],
    ) -> AlarmClock | None:
        """Create an alarm clock for a device.

        Args:
            device_id: The device ID.
            time: Alarm time in HH:MM format.
            days: List of day codes (e.g. ["MON", "TUE"]).

        Returns:
            The created alarm, or None on failure.
        """
        payload = {
            "deviceId": device_id,
            "time": time,
            "days": days,
        }
        data = await self._request("POST", "/v1/alarm-clock", json=payload)
        if isinstance(data, dict):
            return AlarmClock.model_validate(data)
        return None

    async def delete_alarm(self, alarm_id: str) -> None:
        """Delete an alarm clock.

        Args:
            alarm_id: The alarm ID.
        """
        await self._request("DELETE", f"/v1/alarm-clock/{alarm_id}")

    async def get_silence_times(self, device_id: str) -> list[SilenceTime]:
        """Get silence time entries for a device.

        Args:
            device_id: The device ID.

        Returns:
            List of silence times, empty on error.
        """
        try:
            data = await self._request("GET", f"/v1/silence-time/{device_id}")
            if not isinstance(data, list):
                return []

            result = []
            for item in data:
                try:
                    result.append(SilenceTime.model_validate(item))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Failed to parse silence time: %s",
                        _describe_parse_error(err),
                    )
            return result
        except AnioDeviceNotFoundError:
            _LOGGER.debug("No silence times for device %s (404)", device_id)
            return []

    async def get_school_way_times(self, device_id: str) -> list[SchoolWayTime]:
        """Get the school way times of a device.

        Args:
            device_id: The device ID.

        Returns:
            List of school way times, empty on error.
        """
        try:
            # The ANIO app uses /v2, which already returns local times
            data = await self._request("GET", f"/v2/school-way-time/{device_id}")
            local = True
        except AnioDeviceNotFoundError:
            local = False
        try:
            if not local:
                # /v1 times are shifted back by deviceTimezone; see to_local_time
                data = await self._request("GET", f"/v1/school-way-time/{device_id}")
            if not isinstance(data, list):
                return []

            result = []
            for item in data:
                if local and isinstance(item, dict):
                    item = {k: v for k, v in item.items() if k != "deviceTimezone"}
                try:
                    result.append(SchoolWayTime.model_validate(item))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Failed to parse school way time: %s",
                        _describe_parse_error(err),
                    )
            return result
        except AnioDeviceNotFoundError:
            _LOGGER.debug("No school way times for device %s (404)", device_id)
            return []

    async def enable_silence_times(self, device_id: str) -> None:
        """Enable all silence times for a device.

        Args:
            device_id: The device ID.
        """
        await self._request("POST", f"/v1/silence-time/{device_id}/enable")

    async def disable_silence_times(self, device_id: str) -> None:
        """Disable all silence times for a device.

        Args:
            device_id: The device ID.
        """
        await self._request("POST", f"/v1/silence-time/{device_id}/disable")

    async def get_tracking_mode(self, device_id: str) -> str | None:
        """Get the tracking mode for a device.

        Args:
            device_id: The device ID.

        Returns:
            Tracking mode string, or None if unavailable.
        """
        try:
            data = await self._request(
                "GET", f"/v1/device/{device_id}/trackingMode"
            )
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                return data.get("trackingMode") or data.get("mode")
            return None
        except (AnioDeviceNotFoundError, AnioApiError):
            _LOGGER.debug("No tracking mode for device %s", device_id)
            return None

    async def update_device_settings(
        self, device_id: str, **kwargs: str | int | bool
    ) -> None:
        """Update device settings.

        Args:
            device_id: The device ID.
            **kwargs: Settings to update (e.g. ringProfile="SILENT").
        """
        await self._request(
            "PATCH", f"/v1/device/{device_id}/settings", json=kwargs
        )
