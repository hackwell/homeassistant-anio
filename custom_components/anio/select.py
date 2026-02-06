"""Select platform for ANIO integration."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AnioApiClient
from .const import DOMAIN, RING_PROFILES
from .coordinator import AnioDataUpdateCoordinator
from .entity import AnioEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANIO select entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    client: AnioApiClient = hass.data[DOMAIN][entry.entry_id]["client"]

    entities: list[SelectEntity] = []

    for device_id in coordinator.data:
        entities.append(AnioRingProfileSelect(coordinator, client, device_id))

    async_add_entities(entities)


class AnioRingProfileSelect(AnioEntity, SelectEntity):
    """Select entity for the ANIO watch ring profile."""

    _attr_icon = "mdi:bell-ring"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = RING_PROFILES

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
    ) -> None:
        """Initialize the ring profile select."""
        super().__init__(coordinator, device_id)
        self._client = client
        self._attr_unique_id = f"{device_id}_ring_profile"

    @property
    def name(self) -> str:
        """Return the name of the select."""
        return "Ring Profile"

    @property
    def current_option(self) -> str | None:
        """Return the current ring profile."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return device_state.device.settings.ring_profile
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the ring profile."""
        await self._client.update_device_settings(
            self._device_id, ringProfile=option
        )
        await self.coordinator.async_request_refresh()
