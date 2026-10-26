"""Sensor platform for ANIO integration."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import AlarmClock
from .api.models import WEEKDAYS
from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import AnioEntity, async_setup_device_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANIO sensor entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    async_setup_device_entities(
        entry,
        coordinator,
        async_add_entities,
        lambda device_id: [
            AnioBatterySensor(coordinator, device_id),
            AnioLastSeenSensor(coordinator, device_id),
            AnioSignalStrengthSensor(coordinator, device_id),
            AnioLastMessageSensor(coordinator, device_id),
            AnioNextAlarmSensor(coordinator, device_id),
            AnioTrackingModeSensor(coordinator, device_id),
        ],
    )


class AnioBatterySensor(AnioEntity, SensorEntity):
    """Sensor entity for ANIO watch battery level."""

    _attr_translation_key = "battery"

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
    def native_value(self) -> int | None:
        """Return the battery level."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.battery_level
        return None


class AnioLastSeenSensor(AnioEntity, SensorEntity):
    """Sensor entity for ANIO watch last seen timestamp."""

    _attr_translation_key = "last_seen"

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
    def native_value(self) -> datetime | None:
        """Return the last seen timestamp."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.last_seen
        return None


class AnioSignalStrengthSensor(AnioEntity, SensorEntity):
    """Sensor entity for ANIO watch signal strength."""

    _attr_translation_key = "signal_strength"

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
    def native_value(self) -> int | None:
        """Return the signal strength."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.signal_strength
        return None


class AnioLastMessageSensor(AnioEntity, SensorEntity):
    """Sensor entity for the last message received from the ANIO watch."""

    _attr_translation_key = "last_message"

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


def next_alarm(
    alarms: list[AlarmClock], now: datetime
) -> tuple[AlarmClock, datetime] | None:
    """Find the enabled alarm that rings next, honouring its weekdays.

    Args:
        alarms: The alarms of a watch.
        now: The current local time.

    Returns:
        The alarm and when it rings, or None if no alarm is enabled.
    """
    upcoming: list[tuple[AlarmClock, datetime]] = []
    for alarm in alarms:
        if not alarm.enabled:
            continue
        try:
            alarm_time = time.fromisoformat(alarm.time)
        except ValueError:
            continue
        # One week ahead covers every weekday; today only if still to come
        for offset in range(8):
            day = now + timedelta(days=offset)
            # WEEKDAYS starts on Sunday, weekday() on Monday
            weekday = WEEKDAYS[(day.weekday() + 1) % 7]
            # An alarm without days is treated as daily
            if alarm.days and weekday not in alarm.days:
                continue
            rings_at = day.replace(
                hour=alarm_time.hour,
                minute=alarm_time.minute,
                second=0,
                microsecond=0,
            )
            if rings_at > now:
                upcoming.append((alarm, rings_at))
                break
    return min(upcoming, key=lambda item: item[1], default=None)


class AnioNextAlarmSensor(AnioEntity, SensorEntity):
    """Sensor entity for the next alarm on the ANIO watch."""

    _attr_translation_key = "next_alarm"

    # Settings, not history; not stored in the recorder database
    _unrecorded_attributes = frozenset(
        {"alarm_count", "enabled_count", "next_alarm_days"}
    )

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
    def native_value(self) -> str | None:
        """Return the next enabled alarm time."""
        device_state = self.coordinator.data.get(self._device_id)
        if not device_state:
            return None

        upcoming = next_alarm(device_state.alarms, dt_util.now())
        return upcoming[0].time if upcoming else None

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None] | None:
        """Return additional alarm attributes."""
        device_state = self.coordinator.data.get(self._device_id)
        if not device_state:
            return None

        upcoming = next_alarm(device_state.alarms, dt_util.now())
        alarm, rings_at = upcoming if upcoming else (None, None)

        return {
            "alarm_count": len(device_state.alarms),
            "enabled_count": sum(1 for a in device_state.alarms if a.enabled),
            "next_alarm_days": ", ".join(alarm.days) if alarm else None,
            "next_alarm_at": rings_at.isoformat() if rings_at else None,
        }


class AnioTrackingModeSensor(AnioEntity, SensorEntity):
    """Sensor entity for the ANIO watch tracking mode."""

    _attr_translation_key = "tracking_mode"

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
    def native_value(self) -> str | None:
        """Return the current tracking mode."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.tracking_mode
        return None
