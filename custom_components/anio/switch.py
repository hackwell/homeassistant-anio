"""Switch platform for ANIO integration."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AnioApiClient, AnioDeviceState, Geofence
from .api.models import TimeWindow
from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import (
    AnioEntity,
    AnioGeofenceEntity,
    async_setup_device_entities,
    translate_api_errors,
)

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

    # One switch per school way time, silence time and geofence, also for
    # entries added in the ANIO app later
    language = hass.config.language
    known: set[tuple[str, str]] = set()

    @callback
    def _add_new_entries() -> None:
        new: list[SwitchEntity] = []
        for device_id, state in (coordinator.data or {}).items():
            for school_way in state.school_way_times:
                if (device_id, school_way.id) not in known:
                    known.add((device_id, school_way.id))
                    new.append(
                        AnioSchoolWayTimeSwitch(
                            coordinator, client, device_id, school_way, language
                        )
                    )
            for silence in state.silence_times:
                if (device_id, silence.id) not in known:
                    known.add((device_id, silence.id))
                    new.append(
                        AnioSilenceTimeEntrySwitch(
                            coordinator, client, device_id, silence, language
                        )
                    )
            for geofence in state.geofences:
                if (device_id, geofence.id) not in known:
                    known.add((device_id, geofence.id))
                    new.append(
                        AnioGeofenceMonitoringSwitch(
                            coordinator, client, device_id, geofence
                        )
                    )
        if new:
            async_add_entities(new)

    _add_new_entries()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entries))


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


class AnioTimeEntrySwitch(AnioEntity, SwitchEntity):
    """Switches one school way or silence time on or off, e.g. for holidays.

    Times and days stay as set in the ANIO app.
    """

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
        window: TimeWindow,
        language: str,
    ) -> None:
        """Initialize the switch.

        Args:
            coordinator: The data update coordinator.
            client: The ANIO API client.
            device_id: The ANIO device ID.
            window: The school way or silence time.
            language: Home Assistant's language, for the weekdays in the name.
        """
        super().__init__(coordinator, device_id)
        self._client = client
        self._window = window
        self._language = language
        self._attr_unique_id = f"{device_id}_{self.translation_key}_{window.id}"
        self._attr_translation_placeholders = {"period": window.describe(language)}

    def _windows(self, device_state: AnioDeviceState) -> Sequence[TimeWindow]:
        """Return the entries of this kind."""
        raise NotImplementedError

    async def _set_enabled(self, enabled: bool) -> None:
        """Switch the entry in the ANIO cloud."""
        raise NotImplementedError

    @property
    def _current(self) -> TimeWindow | None:
        """Return the entry as of the last update, None once deleted."""
        device_state = self.device_state
        if device_state:
            for window in self._windows(device_state):
                if window.id == self._window.id:
                    return window
        return None

    @property
    def available(self) -> bool:
        """Return False once the entry was deleted in the ANIO app."""
        return super().available and self._current is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Follow changed times or days in the name."""
        if (window := self._current) is not None:
            self._attr_translation_placeholders = {
                "period": window.describe(self._language)
            }
        super()._handle_coordinator_update()

    @property
    def is_on(self) -> bool | None:
        """Return True if the entry is enabled."""
        window = self._current
        return window.enabled if window else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the local times and days."""
        window = self._current
        if window is None:
            return None
        return {
            "start": window.local_start_time,
            "end": window.local_end_time,
            "days": ", ".join(window.days),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Enable the entry."""
        await self._switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Disable the entry."""
        await self._switch(False)

    async def _switch(self, enabled: bool) -> None:
        """Switch the entry and fetch the new state."""
        with translate_api_errors():
            await self._set_enabled(enabled)
        self.coordinator.invalidate_slow_data(self._device_id)
        await self.coordinator.async_request_refresh()


class AnioSchoolWayTimeSwitch(AnioTimeEntrySwitch):
    """One school way time; off e.g. during the school holidays."""

    _attr_translation_key = "school_way_time"

    _attr_icon = "mdi:school"

    def _windows(self, device_state: AnioDeviceState) -> Sequence[TimeWindow]:
        """Return the school way times."""
        return device_state.school_way_times

    async def _set_enabled(self, enabled: bool) -> None:
        """Switch the school way time."""
        await self._client.set_school_way_time_enabled(self._window.id, enabled)


class AnioSilenceTimeEntrySwitch(AnioTimeEntrySwitch):
    """One silence time; off e.g. during the school holidays."""

    _attr_translation_key = "silence_time_entry"

    _attr_icon = "mdi:volume-off"

    def _windows(self, device_state: AnioDeviceState) -> Sequence[TimeWindow]:
        """Return the silence times."""
        return device_state.silence_times

    async def _set_enabled(self, enabled: bool) -> None:
        """Switch the silence time."""
        await self._client.set_silence_time_enabled(self._window.id, enabled)


class AnioGeofenceMonitoringSwitch(AnioGeofenceEntity, SwitchEntity):
    """Switches ANIO's monitoring (alerts) of one geofence on or off.

    The "At ..." sensor shows presence either way; this only controls
    whether ANIO watches the geofence and sends its alerts.
    """

    _attr_translation_key = "geofence_monitoring"

    _attr_icon = "mdi:map-marker-check"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
        geofence: Geofence,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id, geofence)
        self._client = client
        self._attr_unique_id = f"{device_id}_geofence_{geofence.id}_monitoring"

    @property
    def is_on(self) -> bool:
        """Return True if ANIO monitors the geofence."""
        return self._current_geofence.is_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Start monitoring the geofence."""
        await self._switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Stop monitoring the geofence."""
        await self._switch(False)

    async def _switch(self, enabled: bool) -> None:
        """Switch the monitoring and fetch the new state."""
        with translate_api_errors():
            await self._client.set_geofence_enabled(self._geofence.id, enabled)
        self.coordinator.invalidate_slow_data(self._device_id)
        await self.coordinator.async_request_refresh()
