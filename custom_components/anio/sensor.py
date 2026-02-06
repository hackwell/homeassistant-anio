"""Sensor platform for ANIO integration."""

from __future__ import annotations

from datetime import datetime

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
                AnioSignalStrengthSensor(coordinator, device_id),
                AnioLastMessageSensor(coordinator, device_id),
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
            return device_state.battery_level
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


class AnioSignalStrengthSensor(AnioEntity, SensorEntity):
    """Sensor entity for ANIO watch signal strength."""

    _attr_icon = "mdi:signal"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the signal strength sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_signal_strength"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return f"{device_state.device.settings.name} Signal Strength"
        return "ANIO Signal Strength"

    @property
    def native_value(self) -> int | None:
        """Return the signal strength."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.signal_strength
        return None


class AnioLastMessageSensor(AnioEntity, SensorEntity):
    """Sensor entity for the last message received from the ANIO watch."""

    _attr_icon = "mdi:message-text"

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the last message sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_last_message"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return f"{device_state.device.settings.name} Last Message"
        return "ANIO Last Message"

    @property
    def native_value(self) -> str | None:
        """Return the last message text."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state and device_state.last_message:
            return device_state.last_message.text
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | bool | None] | None:
        """Return additional message attributes."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state and device_state.last_message:
            msg = device_state.last_message
            return {
                "sender": msg.sender,
                "type": msg.type,
                "created_at": msg.created_at.isoformat(),
                "is_read": msg.is_read,
            }
        return None
