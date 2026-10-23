"""Diagnostics support for the ANIO integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import CONF_ACCESS_TOKEN, CONF_APP_UUID, CONF_REFRESH_TOKEN, DOMAIN
from .coordinator import AnioDataUpdateCoordinator

# Account data, identifiers and anything that could identify the child or
# where it is. Matched at any depth.
TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_APP_UUID,
    "id",
    "device_id",
    "imei",
    "name",
    "username",
    "phone_nr",
    "gender",
    "text",
    "latitude",
    "longitude",
    # Geofence center; the watch position is handled separately below
    "location",
}
# For the watch position keep accuracy, time and how it was determined
LOCATION_TO_REDACT = {"latitude", "longitude"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.

    Returns:
        Diagnostics data without personal data.
    """
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    devices: dict[str, Any] = {}
    for index, state in enumerate((coordinator.data or {}).values(), start=1):
        data = state.model_dump(mode="json")
        location = data.pop("location", None)
        device = async_redact_data(data, TO_REDACT)
        device["location"] = (
            async_redact_data(location, LOCATION_TO_REDACT) if location else None
        )
        devices[f"device_{index}"] = device

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "last_exception": (
                repr(coordinator.last_exception)
                if coordinator.last_exception
                else None
            ),
        },
        "devices": devices,
    }
