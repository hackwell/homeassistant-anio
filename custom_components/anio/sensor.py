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
                AnioNextAlarmSensor(coordinator, device_id),
                AnioTrackingModeSensor(coordinator, device_id),
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
        return "Battery"

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
        return "Last Seen"

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
        return "Signal Strength"

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
        return "Last Message"

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


class AnioNextAlarmSensor(AnioEntity, SensorEntity):
    """Sensor entity for the next alarm on the ANIO watch."""

    _attr_icon = "mdi:alarm"

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the next alarm sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_next_alarm"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Next Alarm"

    @property
    def native_value(self) -> str | None:
        """Return the next enabled alarm time."""
        device_state = self.coordinator.data.get(self._device_id)
        if not device_state:
            return None

        enabled_alarms = [a for a in device_state.alarms if a.enabled]
        if not enabled_alarms:
            return None

        # Sort by time and return the earliest
        enabled_alarms.sort(key=lambda a: a.time)
        return enabled_alarms[0].time

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None] | None:
        """Return additional alarm attributes."""
        device_state = self.coordinator.data.get(self._device_id)
        if not device_state:
            return None

        enabled_alarms = [a for a in device_state.alarms if a.enabled]
        next_alarm = None
        if enabled_alarms:
            enabled_alarms.sort(key=lambda a: a.time)
            next_alarm = enabled_alarms[0]

        return {
            "alarm_count": len(device_state.alarms),
            "enabled_count": len(enabled_alarms),
            "next_alarm_days": ", ".join(next_alarm.days) if next_alarm else None,
        }


class AnioTrackingModeSensor(AnioEntity, SensorEntity):
    """Sensor entity for the ANIO watch tracking mode."""

    _attr_icon = "mdi:crosshairs-gps"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the tracking mode sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_tracking_mode"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Tracking Mode"

    @property
    def native_value(self) -> str | None:
        """Return the current tracking mode."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.tracking_mode
        return None
