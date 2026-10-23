"""Button platform for ANIO integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AnioApiClient
from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import AnioEntity, async_setup_device_entities, translate_api_errors

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANIO button entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    client: AnioApiClient = hass.data[DOMAIN][entry.entry_id]["client"]

    async_setup_device_entities(
        entry,
        coordinator,
        async_add_entities,
        lambda device_id: [
            AnioRingButton(coordinator, client, device_id),
            AnioPowerOffButton(coordinator, client, device_id),
            AnioFlowerButton(coordinator, client, device_id),
        ],
    )


class AnioRingButton(AnioEntity, ButtonEntity):
    """Button that makes the ANIO watch ring and vibrate ("find my watch").

    POST /v1/device/{id}/find is the ANIO app's "Uhr finden": the watch rings
    loudly. It does not request a new location; the watch reports its
    position on its own interval (60 minutes by default on the ANIO 6).
    """

    _attr_translation_key = "ring"

    _attr_icon = "mdi:bell-ring"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
    ) -> None:
        """Initialize the ring button.

        Args:
            coordinator: The data update coordinator.
            client: The ANIO API client.
            device_id: The ANIO device ID.
        """
        super().__init__(coordinator, device_id)
        self._client = client
        # Kept from the former "Locate" button so entity IDs don't change
        self._attr_unique_id = f"{device_id}_locate"

    async def async_press(self) -> None:
        """Make the watch ring."""
        _LOGGER.info("Making device %s ring", self._device_id)
        with translate_api_errors():
            await self._client.find_device(self._device_id)


class AnioPowerOffButton(AnioEntity, ButtonEntity):
    """Button entity for powering off ANIO watch."""

    _attr_translation_key = "power_off"

    _attr_icon = "mdi:power"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
    ) -> None:
        """Initialize the power off button.

        Args:
            coordinator: The data update coordinator.
            client: The ANIO API client.
            device_id: The ANIO device ID.
        """
        super().__init__(coordinator, device_id)
        self._client = client
        self._attr_unique_id = f"{device_id}_power_off"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.warning(
            "Power off requested for device %s. This will turn off the watch!",
            self._device_id,
        )

        with translate_api_errors():
            await self._client.power_off_device(self._device_id)

        _LOGGER.info("Power off command sent to device %s", self._device_id)


class AnioFlowerButton(AnioEntity, ButtonEntity):
    """Button entity for sending a flower (praise) to the ANIO watch."""

    _attr_translation_key = "flower"

    _attr_icon = "mdi:flower"

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
    ) -> None:
        """Initialize the flower button.

        Args:
            coordinator: The data update coordinator.
            client: The ANIO API client.
            device_id: The ANIO device ID.
        """
        super().__init__(coordinator, device_id)
        self._client = client
        self._attr_unique_id = f"{device_id}_flower"

        # A flower adds a reward heart. Watches without hearts (e.g. the
        # ANIO 6, hasHearts=false) accept it but show nothing, so the button
        # starts disabled there.
        device_state = self.device_state
        if device_state and not device_state.device.config.has_hearts:
            self._attr_entity_registry_enabled_default = False

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Sending flower to device %s", self._device_id)
        with translate_api_errors():
            await self._client.send_flower(self._device_id)
