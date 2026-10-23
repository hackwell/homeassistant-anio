"""DataUpdateCoordinator for the ANIO integration."""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    AnioApiClient,
    AnioApiError,
    AnioAuthError,
    AnioConnectionError,
    AnioDeviceState,
    AnioRateLimitError,
    Geofence,
    LocationInfo,
)
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_MESSAGE_RECEIVED,
    SENDER_DEVICE,
    SENDER_WATCH,
)

_LOGGER = logging.getLogger(__name__)

# Consider device offline if last seen more than 10 minutes ago
ONLINE_THRESHOLD = timedelta(minutes=10)


class AnioDataUpdateCoordinator(DataUpdateCoordinator[dict[str, AnioDeviceState]]):
    """Coordinator for fetching ANIO device data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: AnioApiClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            client: ANIO API client.
            scan_interval: Polling interval in seconds.
            config_entry: The config entry this coordinator belongs to.
        """
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._last_activity_check: datetime | None = None
        # Insertion-ordered, so trimming drops the oldest IDs
        self._seen_message_ids: dict[str, None] = {}
        # The first poll only records the messages that already exist, so
        # old messages are not reported again after every restart.
        self._messages_primed = False
        self._geofences: list[Geofence] = []

    @property
    def geofences(self) -> list[Geofence]:
        """Get cached geofences."""
        return self._geofences

    async def _async_update_data(self) -> dict[str, AnioDeviceState]:
        """Fetch data from the ANIO API.

        Returns:
            Dictionary mapping device IDs to their state.

        Raises:
            ConfigEntryAuthFailed: If authentication fails.
            UpdateFailed: If data fetch fails.
        """
        try:
            # Fetch devices
            devices = await self.client.get_devices()

            # Fetch geofences (cached, refreshed each poll)
            self._geofences = await self.client.get_geofences()

            # Fetch activity for messages
            activity = await self.client.get_activity()
            self._last_activity_check = datetime.now(UTC)

            # Process incoming messages and fire events
            await self._process_messages(activity)

            # Build state for each device
            result: dict[str, AnioDeviceState] = {}

            for device in devices:
                # Fetch last location from /v1/location/{deviceId}/last
                latest = await self.client.get_last_location(device.id)

                location: LocationInfo | None = None
                last_seen: datetime | None = None
                battery_level: int | None = None
                signal_strength: int | None = None

                if latest:
                    location = LocationInfo(
                        lat=latest.latitude,
                        lng=latest.longitude,
                        accuracy=0,
                        timestamp=latest.date,
                    )
                    last_seen = latest.last_response
                    battery_level = latest.battery_level
                    signal_strength = latest.signal_strength

                # Fetch chat history and find last WATCH/DEVICE message
                last_message = None
                chat_messages = await self.client.get_chat_history(device.id)
                for msg in reversed(chat_messages):
                    if msg.sender in (SENDER_WATCH, SENDER_DEVICE):
                        last_message = msg
                        break

                # Fetch alarms, silence times, and tracking mode
                alarms = await self.client.get_alarms(device.id)
                silence_times = await self.client.get_silence_times(device.id)
                tracking_mode = await self.client.get_tracking_mode(device.id)

                is_online = self._calculate_online_status(last_seen)

                state = AnioDeviceState(
                    device=device,
                    location=location,
                    # Inside/outside is computed on demand by is_device_in_geofence
                    geofences=list(self._geofences),
                    last_seen=last_seen,
                    is_online=is_online,
                    battery_level_value=battery_level,
                    signal_strength=signal_strength,
                    last_message=last_message,
                    alarms=alarms,
                    silence_times=silence_times,
                    tracking_mode=tracking_mode,
                )
                result[device.id] = state

            _LOGGER.debug(
                "Updated %d devices, %d geofences",
                len(result),
                len(self._geofences),
            )
            return result

        except AnioAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AnioRateLimitError as err:
            raise UpdateFailed(f"Rate limited: {err}") from err
        except AnioConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except AnioApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

    def _calculate_online_status(self, last_seen: datetime | None) -> bool:
        """Calculate if a device is online based on last seen time.

        Args:
            last_seen: Last seen datetime.

        Returns:
            True if device is considered online.
        """
        if last_seen is None:
            return False

        now = datetime.now(UTC)
        return (now - last_seen) < ONLINE_THRESHOLD

    def _is_inside_geofence(
        self,
        device_lat: float,
        device_lon: float,
        fence_lat: float,
        fence_lon: float,
        radius_meters: int,
    ) -> bool:
        """Check if device is inside a geofence using Haversine formula.

        Args:
            device_lat: Device latitude.
            device_lon: Device longitude.
            fence_lat: Geofence center latitude.
            fence_lon: Geofence center longitude.
            radius_meters: Geofence radius in meters.

        Returns:
            True if device is inside the geofence.
        """
        # Earth's radius in meters
        earth_radius = 6371000

        # Convert to radians
        lat1 = math.radians(device_lat)
        lat2 = math.radians(fence_lat)
        delta_lat = math.radians(fence_lat - device_lat)
        delta_lon = math.radians(fence_lon - device_lon)

        # Haversine formula
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = earth_radius * c

        return distance <= radius_meters

    def is_device_in_geofence(
        self,
        device_id: str,
        geofence_id: str,
    ) -> bool:
        """Check if a device is inside a specific geofence.

        Args:
            device_id: The device ID.
            geofence_id: The geofence ID.

        Returns:
            True if device is inside the geofence.
        """
        if not self.data or device_id not in self.data:
            return False

        state = self.data[device_id]
        if not state.location:
            return False

        for geofence in self._geofences:
            if geofence.id == geofence_id:
                return self._is_inside_geofence(
                    state.location.latitude,
                    state.location.longitude,
                    geofence.latitude,
                    geofence.longitude,
                    geofence.radius,
                )

        return False

    async def _process_messages(self, activity: list[Any]) -> None:
        """Process activity items for incoming messages and fire events.

        Args:
            activity: Activity items from the API.
        """
        fire_events = self._messages_primed
        self._messages_primed = True

        for item in activity:
            # Check if this is a message from the watch
            if (
                hasattr(item, "type")
                and item.type == "MESSAGE"
                and hasattr(item, "data")
                and item.data
            ):
                message_data = item.data
                message_id = message_data.get("id")

                # Skip if we've already processed this message
                if message_id and message_id in self._seen_message_ids:
                    continue

                # Check if it's from the watch (the API reports WATCH or DEVICE)
                sender = message_data.get("sender")
                if fire_events and sender in (SENDER_WATCH, SENDER_DEVICE):
                    # Get device name
                    device_id = message_data.get("deviceId", "")
                    device_name = "Unknown"

                    if self.data and device_id in self.data:
                        device_name = self.data[device_id].name

                    # Fire Home Assistant event
                    self.hass.bus.async_fire(
                        EVENT_MESSAGE_RECEIVED,
                        {
                            "device_id": device_id,
                            "device_name": device_name,
                            "message_id": message_id,
                            "message_type": message_data.get("type", "TEXT"),
                            "content": message_data.get("text", ""),
                            "sender": sender,
                            "timestamp": message_data.get("createdAt"),
                        },
                    )

                    _LOGGER.debug(
                        "Fired %s message event for device %s",
                        message_data.get("type", "TEXT"),
                        device_id,
                    )

                # Mark message as seen
                if message_id:
                    self._seen_message_ids[message_id] = None

                    # Limit the size of seen messages, keeping the newest 500
                    if len(self._seen_message_ids) > 1000:
                        for old_id in list(self._seen_message_ids)[:-500]:
                            del self._seen_message_ids[old_id]

    async def async_request_refresh_for_device(self, device_id: str) -> None:
        """Request a data refresh after a device action.

        Args:
            device_id: The device ID that triggered the refresh.
        """
        _LOGGER.debug("Refresh requested for device %s", device_id)
        await self.async_request_refresh()
