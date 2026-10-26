"""The ANIO Smartwatch integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnioApiClient, AnioAuth
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_APP_UUID,
    CONF_REFRESH_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import AnioDataUpdateCoordinator
from .services import async_setup_services

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# Platforms to set up
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.BUTTON,
    Platform.NOTIFY,
    Platform.SWITCH,
    Platform.SELECT,
]


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:  # noqa: ARG001
    """Register the integration's actions.

    Args:
        hass: Home Assistant instance.
        config: The YAML configuration (unused; set up from the UI).

    Returns:
        True.
    """
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ANIO Smartwatch from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.

    Returns:
        True if setup was successful.
    """
    hass.data.setdefault(DOMAIN, {})

    # Get the aiohttp session
    session = async_get_clientsession(hass)

    async def _on_token_refresh(access_token: str, refresh_token: str) -> None:
        """Persist refreshed tokens to the config entry."""
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_ACCESS_TOKEN: access_token,
                CONF_REFRESH_TOKEN: refresh_token,
            },
        )
        _LOGGER.debug("Persisted refreshed tokens to config entry")

    # Create auth handler with stored tokens
    auth = AnioAuth(
        session=session,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        app_uuid=entry.data.get(CONF_APP_UUID),
        on_token_refresh=_on_token_refresh,
    )

    # Create API client
    client = AnioApiClient(session=session, auth=auth)

    # Get scan interval from options or default
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

    # Create coordinator
    coordinator = AnioDataUpdateCoordinator(
        hass=hass,
        client=client,
        scan_interval=scan_interval,
        config_entry=entry,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store components for platform access
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "auth": auth,
        "client": client,
        # Snapshot of the options this setup was built with, so the update
        # listener can tell an options change apart from a token refresh.
        "options": dict(entry.options),
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info(
        "ANIO integration set up with %d devices",
        len(coordinator.data) if coordinator.data else 0,
    )

    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow removing a watch that is no longer part of the ANIO account.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.
        device_entry: The device to remove.

    Returns:
        True if the device may be removed.
    """
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    current = coordinator.data or {}
    return not any(
        domain == DOMAIN and device_id in current
        for domain, device_id in device_entry.identifiers
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.

    Returns:
        True if unload was successful.
    """
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    _LOGGER.info("ANIO integration unloaded")

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options have changed.

    Home Assistant calls update listeners for every config entry update,
    including the ones made by ``_on_token_refresh`` when refreshed tokens are
    persisted to ``entry.data``. Reloading in that case would briefly make all
    entities unavailable on every token refresh, so only reload when the
    options actually differ from the ones the entry was set up with.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.
    """
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if entry_data is not None and entry_data.get("options") == dict(entry.options):
        _LOGGER.debug("Config entry data updated without option changes, no reload")
        return

    await hass.config_entries.async_reload(entry.entry_id)
