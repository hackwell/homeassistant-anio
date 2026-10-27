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
from .entity import AnioEntity, async_setup_device_entities, translate_api_errors

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

    async_setup_device_entities(
        entry,
        coordinator,
        async_add_entities,
        lambda device_id: [AnioRingProfileSelect(coordinator, client, device_id)],
    )


class AnioRingProfileSelect(AnioEntity, SelectEntity):
    """Select entity for the ANIO watch ring profile."""

    _attr_translation_key = "ring_profile"

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
    def current_option(self) -> str | None:
        """Return the current ring profile."""
        device_state = self.coordinator.data.get(self._device_id)
        if not device_state:
            return None
        option = device_state.device.settings.ring_profile.lower()
        return option if option in RING_PROFILES else None

    async def async_select_option(self, option: str) -> None:
        """Set the ring profile."""
        with translate_api_errors():
            await self._client.update_device_settings(
                self._device_id, ringProfile=option.upper()
            )
        await self.coordinator.async_request_refresh()
