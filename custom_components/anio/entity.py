"""Base entity for ANIO integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from .api import AnioDeviceState, Geofence
    from .coordinator import AnioDataUpdateCoordinator
else:
    from .api import Geofence


class AnioEntity(CoordinatorEntity["AnioDataUpdateCoordinator"]):
    """Base class for ANIO entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: The data update coordinator.
            device_id: The ANIO device ID.
        """
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_state(self) -> AnioDeviceState | None:
        """Get the current device state from coordinator data."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._device_id)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.device_state is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the device registry."""
        state = self.device_state

        if state:
            device = state.device
            return DeviceInfo(
                identifiers={(DOMAIN, device.id)},
                name=device.settings.name,
                manufacturer="ANIO",
                model=f"Generation {device.config.generation}",
                sw_version=device.config.firmware_version,
            )

        # Fallback if state not available yet
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"ANIO {self._device_id[:8]}",
            manufacturer="ANIO",
        )


class AnioGeofenceEntity(CoordinatorEntity["AnioDataUpdateCoordinator"]):
    """Base class for ANIO geofence entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        device_id: str,
        geofence: Geofence,
    ) -> None:
        """Initialize the geofence entity.

        Args:
            coordinator: The data update coordinator.
            device_id: The ANIO device ID.
            geofence: The geofence object.
        """
        super().__init__(coordinator)
        self._device_id = device_id
        self._geofence = geofence

    @property
    def device_state(self) -> AnioDeviceState | None:
        """Get the current device state from coordinator data."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._device_id)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.device_state is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the device registry."""
        state = self.device_state

        if state:
            device = state.device
            return DeviceInfo(
                identifiers={(DOMAIN, device.id)},
                name=device.settings.name,
                manufacturer="ANIO",
                model=f"Generation {device.config.generation}",
                sw_version=device.config.firmware_version,
            )

        # Fallback if state not available yet
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"ANIO {self._device_id[:8]}",
            manufacturer="ANIO",
        )

    @property
    def is_inside(self) -> bool:
        """Check if the device is inside this geofence."""
        return self.coordinator.is_device_in_geofence(
            self._device_id,
            self._geofence.id,
        )
