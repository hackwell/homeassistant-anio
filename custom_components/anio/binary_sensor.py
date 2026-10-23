"""Binary sensor platform for ANIO integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Geofence
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

    # Online status sensor for each watch
    async_setup_device_entities(
        entry,
        coordinator,
        async_add_entities,
        lambda device_id: [AnioOnlineSensor(coordinator, device_id)],
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
        self._attr_translation_placeholders = {"geofence_name": geofence.name}

    @property
    def _current_geofence(self) -> Geofence:
        """Return the geofence as of the last update (e.g. after a rename)."""
        device_state = self.device_state
        if device_state:
            for geofence in device_state.geofences:
                if geofence.id == self._geofence.id:
                    return geofence
        return self._geofence

    @property
    def available(self) -> bool:
        """Return False once the geofence was deleted in the ANIO app."""
        device_state = self.device_state
        return super().available and any(
            geofence.id == self._geofence.id
            for geofence in (device_state.geofences if device_state else [])
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Keep the geofence name current, e.g. after a rename in the app."""
        self._attr_translation_placeholders = {
            "geofence_name": self._current_geofence.name
        }
        super()._handle_coordinator_update()

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
            "active_from": geofence.start_time,
            "active_until": geofence.end_time,
            "enabled_in_anio": geofence.is_enabled,
        }
