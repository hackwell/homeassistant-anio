"""Actions of the ANIO integration that target a watch, not an entity."""

from __future__ import annotations

from datetime import time

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import translate_api_errors

try:
    import probatio as vol
except ImportError:  # Home Assistant < 2026.9 still uses voluptuous
    import voluptuous as vol  # type: ignore[no-redef]

SERVICE_CREATE_ALARM = "create_alarm"
SERVICE_DELETE_ALARM = "delete_alarm"
ATTR_DEVICE_ID = "device_id"
ATTR_TIME = "time"
ATTR_DAYS = "days"
ATTR_ENABLED = "enabled"

DAY_OPTIONS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

CREATE_ALARM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_TIME): cv.time,
        vol.Optional(ATTR_DAYS, default=DAY_OPTIONS[:5]): vol.All(
            cv.ensure_list, [vol.In(DAY_OPTIONS)]
        ),
        vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
    }
)
DELETE_ALARM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_TIME): cv.time,
    }
)


def _resolve_watch(
    hass: HomeAssistant, device_registry_id: str
) -> tuple[AnioDataUpdateCoordinator, str]:
    """Find the coordinator and ANIO device ID of a Home Assistant device.

    Args:
        hass: Home Assistant instance.
        device_registry_id: The device chosen in the action.

    Returns:
        The coordinator of its account and the ANIO device ID.

    Raises:
        ServiceValidationError: If the device is no ANIO watch of a loaded entry.
    """
    device = dr.async_get(hass).async_get(device_registry_id)
    anio_ids = [
        identifier
        for domain, identifier in (device.identifiers if device else set())
        if domain == DOMAIN
    ]
    for entry_data in hass.data.get(DOMAIN, {}).values():
        coordinator: AnioDataUpdateCoordinator = entry_data["coordinator"]
        for anio_id in anio_ids:
            if coordinator.data and anio_id in coordinator.data:
                return coordinator, anio_id
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="device_not_found",
        translation_placeholders={"device_id": device_registry_id},
    )


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register the alarm actions.

    Args:
        hass: Home Assistant instance.
    """

    async def create_alarm(call: ServiceCall) -> None:
        coordinator, device_id = _resolve_watch(hass, call.data[ATTR_DEVICE_ID])
        alarm_time: time = call.data[ATTR_TIME]
        with translate_api_errors():
            await coordinator.client.create_alarm(
                device_id,
                alarm_time.strftime("%H:%M"),
                [day.upper() for day in call.data[ATTR_DAYS]],
                enabled=call.data[ATTR_ENABLED],
            )
        coordinator.invalidate_slow_data(device_id)
        await coordinator.async_request_refresh()

    async def delete_alarm(call: ServiceCall) -> None:
        coordinator, device_id = _resolve_watch(hass, call.data[ATTR_DEVICE_ID])
        wanted = call.data[ATTR_TIME].strftime("%H:%M")
        state = coordinator.data[device_id]
        matches = [alarm for alarm in state.alarms if alarm.time[:5] == wanted]
        if not matches:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="alarm_not_found",
                translation_placeholders={"time": wanted},
            )
        with translate_api_errors():
            for alarm in matches:
                await coordinator.client.delete_alarm(alarm.id)
        coordinator.invalidate_slow_data(device_id)
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_ALARM, create_alarm, schema=CREATE_ALARM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_ALARM, delete_alarm, schema=DELETE_ALARM_SCHEMA
    )
