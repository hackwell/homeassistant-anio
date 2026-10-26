"""Binary sensor platform for ANIO integration."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .api import AnioDeviceState, Geofence
from .api.models import TimeWindow
from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import AnioEntity, AnioGeofenceEntity, async_setup_device_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANIO binary sensor entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    # Online status, school way and silence time sensors for each watch
    async_setup_device_entities(
        entry,
        coordinator,
        async_add_entities,
        lambda device_id: [
            AnioOnlineSensor(coordinator, device_id),
            AnioSchoolWaySensor(coordinator, device_id),
            AnioSilenceActiveSensor(coordinator, device_id),
        ],
    )

    # A sensor for each geofence, also for geofences added in the app later
    known_geofences: set[tuple[str, str]] = set()

    @callback
    def _add_new_geofences() -> None:
        new: list[BinarySensorEntity] = []
        for device_id, device_state in (coordinator.data or {}).items():
            for geofence in device_state.geofences:
                if (device_id, geofence.id) in known_geofences:
                    continue
                known_geofences.add((device_id, geofence.id))
                new.append(AnioGeofenceSensor(coordinator, device_id, geofence))
        if new:
            async_add_entities(new)

    _add_new_geofences()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_geofences))


class AnioOnlineSensor(AnioEntity, BinarySensorEntity):
    """Binary sensor entity for ANIO watch online status."""

    _attr_translation_key = "online"

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the online sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_online"

    @property
    def is_on(self) -> bool | None:
        """Return True if the device is online."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.is_online
        return None


class AnioTimeWindowSensor(AnioEntity, BinarySensorEntity):
    """On while one of the watch's weekly time windows is running."""

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the time window sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_{self.translation_key}"

    def _windows(self, device_state: AnioDeviceState) -> Sequence[TimeWindow]:
        """Return the time windows this sensor watches."""
        raise NotImplementedError

    async def async_added_to_hass(self) -> None:
        """Re-check the time windows every minute, without API requests."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(self.hass, self._handle_minute, second=0)
        )

    @callback
    def _handle_minute(self, _now: datetime) -> None:
        """Update the state when a minute starts."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return True while a time window is running."""
        device_state = self.coordinator.data.get(self._device_id)
        if not device_state:
            return None
        now = dt_util.now()
        return any(window.is_active(now) for window in self._windows(device_state))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the time windows in local time."""
        device_state = self.coordinator.data.get(self._device_id)
        if not device_state:
            return None

        return {
            "periods": [
                {
                    "start": window.local_start_time,
                    "end": window.local_end_time,
                    "days": ", ".join(window.days),
                    "enabled": window.enabled,
                }
                for window in self._windows(device_state)
            ],
        }


class AnioSchoolWaySensor(AnioTimeWindowSensor):
    """On while one of the watch's school way times is running."""

    _attr_translation_key = "school_way"

    _attr_icon = "mdi:school"

    def _windows(self, device_state: AnioDeviceState) -> Sequence[TimeWindow]:
        """Return the school way times."""
        return device_state.school_way_times


class AnioSilenceActiveSensor(AnioTimeWindowSensor):
    """On while a silence time is running, so the watch is silent."""

    _attr_translation_key = "silence_active"

    _attr_icon = "mdi:volume-off"

    def _windows(self, device_state: AnioDeviceState) -> Sequence[TimeWindow]:
        """Return the silence times."""
        return device_state.silence_times


class AnioGeofenceSensor(AnioGeofenceEntity, BinarySensorEntity):
    """Binary sensor entity for ANIO geofence presence."""

    _attr_device_class = BinarySensorDeviceClass.PRESENCE
    _attr_translation_key = "geofence"

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
        geofence: Geofence,
    ) -> None:
        """Initialize the geofence sensor."""
        super().__init__(coordinator, device_id, geofence)
        self._attr_unique_id = f"{device_id}_geofence_{geofence.id}"

    @property
    def is_on(self) -> bool | None:
        """Return True if the device is inside the geofence."""
        return self.coordinator.is_device_in_geofence(
            self._device_id, self._geofence.id
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        geofence = self._current_geofence
        return {
            "geofence_name": geofence.name,
            "latitude": geofence.latitude,
            "longitude": geofence.longitude,
            "radius_meters": geofence.radius,
            # ANIO only monitors the geofence in this window; the sensor
            # always shows whether the watch is inside.
            "active_from": geofence.local_start_time,
            "active_until": geofence.local_end_time,
            "enabled_in_anio": geofence.is_enabled,
        }
