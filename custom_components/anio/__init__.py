"""The ANIO Smartwatch integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
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
]


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
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store components for platform access
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "auth": auth,
        "client": client,
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
    """Handle options update.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.
    """
    await hass.config_entries.async_reload(entry.entry_id)
