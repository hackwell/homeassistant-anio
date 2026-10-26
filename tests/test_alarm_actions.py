"""Actions to create and delete alarms on a watch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anio.api import (
    AlarmClock,
    AnioApiClient,
    AnioAuth,
    AnioConnectionError,
)
from custom_components.anio.api.models import format_weekday_bits
from custom_components.anio.const import DOMAIN
from custom_components.anio.services import async_setup_services

from .conftest import TEST_DEVICE_ID


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (["MON", "TUE", "WED", "THU", "FRI"], "0111110"),
        (["SAT", "SUN"], "1000001"),
        ([], "0000000"),
    ],
)
def test_format_weekday_bits(days: list[str], expected: str) -> None:
    """Test day codes become the API's Sunday-first bitstring."""
    assert format_weekday_bits(days) == expected


@pytest.mark.asyncio
async def test_client_create_alarm_payload() -> None:
    """Test the payload matches what the API accepted on an ANIO 6."""
    response = MagicMock()
    response.status = 201
    response.json = AsyncMock(
        return_value={
            "id": "a1",
            "deviceId": TEST_DEVICE_ID,
            "time": "06:30",
            "days": "0111110",
            "isEnabled": False,
        }
    )
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.request.return_value = response
    auth = AsyncMock(spec=AnioAuth)
    auth.ensure_valid_token = AsyncMock(return_value="test_token")
    auth.app_uuid = "test-uuid"
    client = AnioApiClient(session=session, auth=auth)

    alarm = await client.create_alarm(
        TEST_DEVICE_ID, "06:30", ["MON", "TUE", "WED", "THU", "FRI"], enabled=False
    )

    assert session.request.call_args.kwargs["json"] == {
        "deviceId": TEST_DEVICE_ID,
        "time": "06:30",
        "days": "0111110",
        "isEnabled": False,
    }
    assert alarm is not None
    assert alarm.days == ["MON", "TUE", "WED", "THU", "FRI"]


@pytest.fixture
async def watch(
    hass: HomeAssistant, mock_coordinator_data: dict, mock_api_client: AsyncMock
) -> tuple[str, MagicMock]:
    """Set up the actions with one watch; return its device ID and coordinator."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, TEST_DEVICE_ID)}
    )
    mock_coordinator_data[TEST_DEVICE_ID].alarms = [
        AlarmClock(id="a1", time="06:30", days=["MON"], enabled=True),
        AlarmClock(id="a2", time="07:00", days=["SAT"], enabled=True),
    ]
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    coordinator.client = mock_api_client
    coordinator.async_request_refresh = AsyncMock()
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator}}
    await async_setup_services(hass)
    return device.id, coordinator


@pytest.mark.asyncio
async def test_create_alarm(
    hass: HomeAssistant, watch: tuple[str, MagicMock], mock_api_client: AsyncMock
) -> None:
    """Test creating an alarm, with Monday to Friday as default days."""
    device_id, coordinator = watch

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {"device_id": device_id, "time": "06:45"},
        blocking=True,
    )

    mock_api_client.create_alarm.assert_awaited_once_with(
        TEST_DEVICE_ID,
        "06:45",
        ["MON", "TUE", "WED", "THU", "FRI"],
        enabled=True,
    )
    coordinator.invalidate_slow_data.assert_called_once_with(TEST_DEVICE_ID)
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_alarm_with_days_disabled(
    hass: HomeAssistant, watch: tuple[str, MagicMock], mock_api_client: AsyncMock
) -> None:
    """Test given days and a disabled alarm are passed on."""
    device_id, _ = watch

    await hass.services.async_call(
        DOMAIN,
        "create_alarm",
        {
            "device_id": device_id,
            "time": "09:00:00",
            "days": ["sat", "sun"],
            "enabled": False,
        },
        blocking=True,
    )

    mock_api_client.create_alarm.assert_awaited_once_with(
        TEST_DEVICE_ID, "09:00", ["SAT", "SUN"], enabled=False
    )


@pytest.mark.asyncio
async def test_delete_alarm(
    hass: HomeAssistant, watch: tuple[str, MagicMock], mock_api_client: AsyncMock
) -> None:
    """Test the alarm at the given time is deleted, others stay."""
    device_id, coordinator = watch

    await hass.services.async_call(
        DOMAIN, "delete_alarm", {"device_id": device_id, "time": "06:30"}, blocking=True
    )

    mock_api_client.delete_alarm.assert_awaited_once_with("a1")
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_unknown_alarm(
    hass: HomeAssistant, watch: tuple[str, MagicMock], mock_api_client: AsyncMock
) -> None:
    """Test deleting a time without alarm explains the problem."""
    device_id, _ = watch

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "delete_alarm",
            {"device_id": device_id, "time": "05:00"},
            blocking=True,
        )

    assert err.value.translation_key == "alarm_not_found"
    mock_api_client.delete_alarm.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_device(
    hass: HomeAssistant, watch: tuple[str, MagicMock]
) -> None:
    """Test a device that isn't an ANIO watch is rejected."""
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "create_alarm",
            {"device_id": "nope", "time": "06:30"},
            blocking=True,
        )

    assert err.value.translation_key == "device_not_found"


@pytest.mark.asyncio
async def test_api_error_is_translated(
    hass: HomeAssistant, watch: tuple[str, MagicMock], mock_api_client: AsyncMock
) -> None:
    """Test API errors become readable messages."""
    device_id, _ = watch
    mock_api_client.create_alarm.side_effect = AnioConnectionError()

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            DOMAIN,
            "create_alarm",
            {"device_id": device_id, "time": "06:30"},
            blocking=True,
        )

    assert err.value.translation_key == "cannot_connect"
