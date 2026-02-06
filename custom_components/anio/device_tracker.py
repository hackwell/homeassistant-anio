"""Device tracker platform for ANIO integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up ANIO device tracker entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    entities: list[TrackerEntity] = []

    for device_id in coordinator.data:
        entities.append(AnioDeviceTracker(coordinator, device_id))

    async_add_entities(entities)


class AnioDeviceTracker(AnioEntity, TrackerEntity):
    """Device tracker entity for ANIO watch location."""

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the device tracker.

        Args:
            coordinator: The data update coordinator.
            device_id: The ANIO device ID.
        """
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_location"

    @property
    def name(self) -> str:
        """Return the name of the tracker."""
        return "Location"

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state and device_state.location:
            return device_state.location.latitude
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state and device_state.location:
            return device_state.location.longitude
        return None

    @property
    def location_accuracy(self) -> int | None:
        """Return the location accuracy in meters."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state and device_state.location:
            return device_state.location.accuracy
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state and device_state.location:
            return {
                "accuracy": device_state.location.accuracy,
                "last_update": device_state.location.timestamp.isoformat()
                if device_state.location.timestamp
                else None,
            }
        return None
