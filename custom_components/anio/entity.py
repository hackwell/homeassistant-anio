"""Base entity for ANIO integration."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import (
    AnioApiError,
    AnioAuthError,
    AnioConnectionError,
    AnioInvalidEmojiError,
    AnioMessageTooLongError,
    AnioRateLimitError,
)
from .const import DOMAIN, VALID_EMOJI_CODES

if TYPE_CHECKING:
    from .api import AnioDeviceState, Geofence
    from .coordinator import AnioDataUpdateCoordinator
else:
    from .api import Geofence


@contextmanager
def translate_api_errors() -> Iterator[None]:
    """Turn API errors of an action into translated Home Assistant errors.

    Invalid input (message too long, unknown emoji) becomes a
    ServiceValidationError, everything else a HomeAssistantError, so the user
    sees a readable message instead of a stack trace.
    """
    try:
        yield
    except AnioMessageTooLongError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="message_too_long",
            translation_placeholders={
                "length": str(err.length),
                "max_length": str(err.max_length),
            },
        ) from err
    except AnioInvalidEmojiError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_emoji",
            translation_placeholders={
                "code": err.emoji_code,
                "valid_codes": ", ".join(VALID_EMOJI_CODES),
            },
        ) from err
    except AnioAuthError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="auth_failed"
        ) from err
    except AnioRateLimitError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="rate_limited"
        ) from err
    except AnioConnectionError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="cannot_connect"
        ) from err
    except AnioApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"error": str(err)},
        ) from err


@callback
def async_setup_device_entities(
    entry: ConfigEntry,
    coordinator: AnioDataUpdateCoordinator,
    async_add_entities: AddEntitiesCallback,
    create_entities: Callable[[str], Iterable[Entity]],
) -> None:
    """Add the entities of each watch, also for watches added to the account later.

    Args:
        entry: Config entry.
        coordinator: The data update coordinator.
        async_add_entities: Callback to add entities.
        create_entities: Creates the entities of one device ID.
    """
    known: set[str] = set()

    @callback
    def _add_new_devices() -> None:
        new_devices = [d for d in (coordinator.data or {}) if d not in known]
        if not new_devices:
            return
        known.update(new_devices)
        async_add_entities(
            [entity for device_id in new_devices for entity in create_entities(device_id)]
        )

    _add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_devices))


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
        self._attr_translation_placeholders = {"geofence_name": geofence.name}

    @property
    def device_state(self) -> AnioDeviceState | None:
        """Get the current device state from coordinator data."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._device_id)
        return None

    @property
    def available(self) -> bool:
        """Return False once the geofence was deleted in the ANIO app."""
        device_state = self.device_state
        return (
            self.coordinator.last_update_success
            and device_state is not None
            and any(g.id == self._geofence.id for g in device_state.geofences)
        )

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
    def _current_geofence(self) -> Geofence:
        """Return the geofence as of the last update (e.g. after a rename)."""
        device_state = self.device_state
        if device_state:
            for geofence in device_state.geofences:
                if geofence.id == self._geofence.id:
                    return geofence
        return self._geofence

    @callback
    def _handle_coordinator_update(self) -> None:
        """Keep the geofence name current, e.g. after a rename in the app."""
        self._attr_translation_placeholders = {
            "geofence_name": self._current_geofence.name
        }
        super()._handle_coordinator_update()

    @property
    def is_inside(self) -> bool:
        """Check if the device is inside this geofence."""
        return self.coordinator.is_device_in_geofence(
            self._device_id,
            self._geofence.id,
        )
