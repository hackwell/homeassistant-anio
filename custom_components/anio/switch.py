"""Switch platform for ANIO integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up ANIO switch entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    client: AnioApiClient = hass.data[DOMAIN][entry.entry_id]["client"]

    async_setup_device_entities(
        entry,
        coordinator,
        async_add_entities,
        lambda device_id: [
            AnioSilenceTimeSwitch(coordinator, client, device_id),
            AnioExplorerModeSwitch(coordinator, client, device_id),
        ],
    )


class AnioExplorerModeSwitch(AnioEntity, SwitchEntity):
    """Explorer mode: the watch locates every 5 minutes for an hour.

    There is no API to read the explorer mode itself; it shows up as
    tracking mode EXPLORER, which ends on its own after an hour.
    """

    _attr_translation_key = "explorer_mode"

    _attr_icon = "mdi:compass-outline"

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
    ) -> None:
        """Initialize the explorer mode switch."""
        super().__init__(coordinator, device_id)
        self._client = client
        self._attr_unique_id = f"{device_id}_explorer_mode"

    @property
    def is_on(self) -> bool:
        """Return True while the watch is in explorer mode."""
        device_state = self.coordinator.data.get(self._device_id)
        return bool(device_state and device_state.tracking_mode == "EXPLORER")

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Start the explorer mode."""
        with translate_api_errors():
            await self._client.set_explorer_mode(self._device_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Stop the explorer mode."""
        with translate_api_errors():
            await self._client.set_explorer_mode(self._device_id, False)
        await self.coordinator.async_request_refresh()


class AnioSilenceTimeSwitch(AnioEntity, SwitchEntity):
    """Switch entity for toggling silence times on the ANIO watch."""

    _attr_translation_key = "silence_time"

    _attr_icon = "mdi:volume-off"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
    ) -> None:
        """Initialize the silence time switch."""
        super().__init__(coordinator, device_id)
        self._client = client
        self._attr_unique_id = f"{device_id}_silence_time"

    @property
    def is_on(self) -> bool:
        """Return true if any silence time is enabled."""
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return any(st.enabled for st in device_state.silence_times)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Enable silence times."""
        with translate_api_errors():
            await self._client.enable_silence_times(self._device_id)
        self.coordinator.invalidate_slow_data(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Disable silence times."""
        with translate_api_errors():
            await self._client.disable_silence_times(self._device_id)
        self.coordinator.invalidate_slow_data(self._device_id)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return silence time period details."""
        device_state = self.coordinator.data.get(self._device_id)
        if not device_state:
            return None

        periods = []
        for st in device_state.silence_times:
            periods.append(
                {
                    "start": st.start_time,
                    "end": st.end_time,
                    "days": ", ".join(st.days),
                    "enabled": st.enabled,
                }
            )

        return {
            "silence_time_count": len(device_state.silence_times),
            "periods": periods,
        }
