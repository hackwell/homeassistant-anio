"""Binary sensor platform for ANIO integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Geofence
from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import AnioEntity, AnioGeofenceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANIO binary sensor entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    entities: list[BinarySensorEntity] = []

    for device_id in coordinator.data:
        # Add online status sensor for each device
        entities.append(AnioOnlineSensor(coordinator, device_id))

        # Add geofence sensors for each device/geofence combination
        for geofence in coordinator.geofences:
            entities.append(
                AnioGeofenceSensor(coordinator, device_id, geofence)
            )

    async_add_entities(entities)


class AnioOnlineSensor(AnioEntity, BinarySensorEntity):
    """Binary sensor entity for ANIO watch online status."""

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
    def name(self) -> str:
        """Return the name of the sensor."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return f"{device_state.device.settings.name} Online"
        return "ANIO Online"

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
    def name(self) -> str:
        """Return the name of the sensor."""
        device_state = self.coordinator.data.get(self._device_id)
        device_name = "ANIO"
        if device_state:
            device_name = device_state.device.settings.name
        return f"{device_name} at {self._geofence.name}"

    @property
    def is_on(self) -> bool | None:
        """Return True if the device is inside the geofence."""
        return self.coordinator.is_device_in_geofence(
            self._device_id, self._geofence.id
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        return {
            "geofence_name": self._geofence.name,
            "latitude": self._geofence.latitude,
            "longitude": self._geofence.longitude,
            "radius_meters": self._geofence.radius,
        }
