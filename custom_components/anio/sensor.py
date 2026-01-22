"""Sensor platform for ANIO integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import AnioEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANIO sensor entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    entities: list[SensorEntity] = []

    for device_id in coordinator.data:
        entities.extend(
            [
                AnioBatterySensor(coordinator, device_id),
                AnioLastSeenSensor(coordinator, device_id),
                AnioStepsSensor(coordinator, device_id),
            ]
        )

    async_add_entities(entities)


class AnioBatterySensor(AnioEntity, SensorEntity):
    """Sensor entity for ANIO watch battery level."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_battery"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return f"{device_state.device.settings.name} Battery"
        return "ANIO Battery"

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.device.settings.battery
        return None


class AnioLastSeenSensor(AnioEntity, SensorEntity):
    """Sensor entity for ANIO watch last seen timestamp."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the last seen sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_last_seen"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return f"{device_state.device.settings.name} Last Seen"
        return "ANIO Last Seen"

    @property
    def native_value(self) -> datetime | None:
        """Return the last seen timestamp."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.last_seen
        return None


class AnioStepsSensor(AnioEntity, SensorEntity):
    """Sensor entity for ANIO watch step counter."""

    _attr_icon = "mdi:walk"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "steps"

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the steps sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_steps"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return f"{device_state.device.settings.name} Steps"
        return "ANIO Steps"

    @property
    def native_value(self) -> int | None:
        """Return the current step count."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.device.settings.step_count
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return {
                "step_target": device_state.device.settings.step_target,
            }
        return None
