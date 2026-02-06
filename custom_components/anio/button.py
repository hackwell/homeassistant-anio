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
from .entity import AnioEntity

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

    entities: list[ButtonEntity] = []

    for device_id in coordinator.data:
        entities.extend(
            [
                AnioLocateButton(coordinator, client, device_id),
                AnioPowerOffButton(coordinator, client, device_id),
                AnioFlowerButton(coordinator, client, device_id),
            ]
        )

    async_add_entities(entities)


class AnioLocateButton(AnioEntity, ButtonEntity):
    """Button entity for triggering ANIO watch location request."""

    _attr_icon = "mdi:crosshairs-gps"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
    ) -> None:
        """Initialize the locate button.

        Args:
            coordinator: The data update coordinator.
            client: The ANIO API client.
            device_id: The ANIO device ID.
        """
        super().__init__(coordinator, device_id)
        self._client = client
        self._attr_unique_id = f"{device_id}_locate"

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return "Locate"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Requesting location for device %s", self._device_id)

        await self._client.find_device(self._device_id)

        # Request a coordinator refresh to get the new location
        await self.coordinator.async_request_refresh()

        _LOGGER.debug("Location request sent for device %s", self._device_id)


class AnioPowerOffButton(AnioEntity, ButtonEntity):
    """Button entity for powering off ANIO watch."""

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

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return "Power Off"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.warning(
            "Power off requested for device %s. This will turn off the watch!",
            self._device_id,
        )

        await self._client.power_off_device(self._device_id)

        _LOGGER.info("Power off command sent to device %s", self._device_id)


class AnioFlowerButton(AnioEntity, ButtonEntity):
    """Button entity for sending a flower (praise) to the ANIO watch."""

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

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return "Flower"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Sending flower to device %s", self._device_id)
        await self._client.send_flower(self._device_id)
