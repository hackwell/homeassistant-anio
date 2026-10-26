"""School way times: model, API call and binary sensor."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.anio.api import AnioApiClient, AnioAuth, SchoolWayTime
from custom_components.anio.api.models import to_local_time
from custom_components.anio.binary_sensor import AnioSchoolWaySensor

from .conftest import TEST_DEVICE_ID

# Shape of GET /v1/school-way-time/{deviceId}; "0111100" = Monday to Thursday
API_ITEM = {
    "id": "a" * 24,
    "days": "0111100",
    "deviceId": TEST_DEVICE_ID,
    "isEnabled": True,
    # Shifted back by deviceTimezone: the app shows 07:35 to 08:05
    "startTime": "06:35",
    "endTime": "07:05",
    "createdAt": "2026-09-01T10:00:00.000Z",
    "updatedAt": "2026-09-01T10:00:00.000Z",
    "deviceTimezone": "+01:00",
}
# 2026-10-26 is a Monday, 2026-10-30 a Friday
MONDAY = datetime(2026, 10, 26, tzinfo=UTC)
FRIDAY = datetime(2026, 10, 30, tzinfo=UTC)


def _at(day: datetime, hour: int, minute: int) -> datetime:
    """Return the given day at a time."""
    return day.replace(hour=hour, minute=minute)


def test_parse_api_item() -> None:
    """Test the API's format is read and converted to local time."""
    school_way = SchoolWayTime.model_validate(API_ITEM)

    assert school_way.days == ["MON", "TUE", "WED", "THU"]
    assert school_way.enabled is True
    assert (school_way.start_time, school_way.end_time) == ("06:35", "07:05")
    assert (school_way.local_start_time, school_way.local_end_time) == (
        "07:35",
        "08:05",
    )


@pytest.mark.parametrize(
    ("value", "offset", "expected"),
    [
        ("06:35", "+01:00", "07:35"),
        ("23:00", "+01:00", "00:00"),
        ("00:30", "-02:00", "22:30"),
        ("06:35", "+05:30", "12:05"),
        ("06:35", None, "06:35"),
        ("06:35", "Europe/Berlin", "06:35"),
        ("soon", "+01:00", "soon"),
    ],
)
def test_to_local_time(value: str, offset: str | None, expected: str) -> None:
    """Test API times are shifted by deviceTimezone."""
    assert to_local_time(value, offset) == expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (_at(MONDAY, 7, 35), True),
        (_at(MONDAY, 8, 4), True),
        (_at(MONDAY, 8, 5), False),
        (_at(MONDAY, 6, 50), False),
        (_at(FRIDAY, 7, 50), False),
    ],
    ids=["start", "inside", "end", "api_time_is_not_local", "friday"],
)
def test_is_active(now: datetime, expected: bool) -> None:
    """Test the window covers its days and local times only."""
    assert SchoolWayTime.model_validate(API_ITEM).is_active(now) is expected


def test_disabled_or_unreadable_is_never_active() -> None:
    """Test disabled windows and unreadable times are off."""
    disabled = SchoolWayTime.model_validate({**API_ITEM, "isEnabled": False})
    unreadable = SchoolWayTime.model_validate({**API_ITEM, "startTime": "soon"})

    assert not disabled.is_active(_at(MONDAY, 7, 50))
    assert not unreadable.is_active(_at(MONDAY, 7, 50))


def test_window_past_midnight() -> None:
    """Test a window ending after midnight belongs to its start day."""
    night = SchoolWayTime.model_validate(
        {
            **API_ITEM,
            "days": "0100000",
            "startTime": "23:00",
            "endTime": "01:00",
            "deviceTimezone": None,
        }
    )

    assert night.is_active(_at(MONDAY, 23, 30))
    # Tuesday 00:30 still belongs to Monday's window
    assert night.is_active(_at(MONDAY, 0, 30).replace(day=27))
    assert not night.is_active(_at(MONDAY, 0, 30))


def _client(*responses: tuple[int, object]) -> tuple[AnioApiClient, MagicMock]:
    """Create a client whose requests return the given (status, JSON)."""
    mocks = []
    for status, body in responses:
        response = MagicMock()
        response.status = status
        response.json = AsyncMock(return_value=body)
        response.text = AsyncMock(return_value="")
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=None)
        mocks.append(response)
    session = MagicMock()
    session.request.side_effect = mocks
    auth = AsyncMock(spec=AnioAuth)
    auth.ensure_valid_token = AsyncMock(return_value="test_token")
    auth.app_uuid = "test-uuid"
    return AnioApiClient(session=session, auth=auth), session


@pytest.mark.asyncio
async def test_client_reads_v2_local_times() -> None:
    """Test /v2 is used; its times are already local and not shifted again."""
    v2_item = {**API_ITEM, "startTime": "07:35", "endTime": "08:05"}
    client, session = _client((200, [v2_item, {"broken": True}]))

    school_ways = await client.get_school_way_times(TEST_DEVICE_ID)

    assert [(sw.local_start_time, sw.local_end_time) for sw in school_ways] == [
        ("07:35", "08:05")
    ]
    assert session.request.call_args.args[1].endswith(
        f"/v2/school-way-time/{TEST_DEVICE_ID}"
    )


@pytest.mark.asyncio
async def test_client_falls_back_to_v1() -> None:
    """Test /v1 (shifted by deviceTimezone) is used if /v2 is missing."""
    client, session = _client((404, {}), (200, [API_ITEM]))

    school_ways = await client.get_school_way_times(TEST_DEVICE_ID)

    assert [sw.local_start_time for sw in school_ways] == ["07:35"]
    assert session.request.call_args.args[1].endswith(
        f"/v1/school-way-time/{TEST_DEVICE_ID}"
    )


def _sensor(mock_coordinator_data: dict) -> AnioSchoolWaySensor:
    """Create a school way sensor with one school way time."""
    mock_coordinator_data[TEST_DEVICE_ID].school_way_times = [
        SchoolWayTime.model_validate(API_ITEM)
    ]
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    return AnioSchoolWaySensor(coordinator, TEST_DEVICE_ID)


@pytest.mark.parametrize(
    ("now", "expected"),
    [(_at(MONDAY, 7, 50), True), (_at(MONDAY, 12, 0), False)],
    ids=["on_the_way", "at_school"],
)
def test_sensor_state(
    mock_coordinator_data: dict, now: datetime, expected: bool
) -> None:
    """Test the sensor is on during a school way time."""
    sensor = _sensor(mock_coordinator_data)

    with patch("custom_components.anio.binary_sensor.dt_util.now", return_value=now):
        assert sensor.is_on is expected


def test_sensor_attributes(mock_coordinator_data: dict) -> None:
    """Test the school way times are listed in local time, like in the app."""
    sensor = _sensor(mock_coordinator_data)

    assert sensor.unique_id == f"{TEST_DEVICE_ID}_school_way"
    assert sensor.extra_state_attributes == {
        "periods": [
            {
                "start": "07:35",
                "end": "08:05",
                "days": "MON, TUE, WED, THU",
                "enabled": True,
            }
        ]
    }


def test_sensor_without_data() -> None:
    """Test the sensor is unknown without device data."""
    coordinator = MagicMock()
    coordinator.data = {}
    sensor = AnioSchoolWaySensor(coordinator, TEST_DEVICE_ID)

    assert sensor.is_on is None
    assert sensor.extra_state_attributes is None


def test_sensor_updates_every_minute(mock_coordinator_data: dict) -> None:
    """Test the minute tick writes the state without fetching data."""
    sensor = _sensor(mock_coordinator_data)

    with patch.object(sensor, "async_write_ha_state") as write_state:
        sensor._handle_minute(_at(MONDAY, 7, 35))

    write_state.assert_called_once()
    sensor.coordinator.async_request_refresh.assert_not_called()


def test_minute_tick_writes_only_on_change(mock_coordinator_data: dict) -> None:
    """Test the state is written when a window starts or ends, not every minute."""
    sensor = _sensor(mock_coordinator_data)
    now = "custom_components.anio.binary_sensor.dt_util.now"

    with patch.object(sensor, "async_write_ha_state") as write_state:
        for minute, (hour, mins) in enumerate(
            [(7, 33), (7, 34), (7, 35), (7, 36), (8, 5)]
        ):
            with patch(now, return_value=_at(MONDAY, hour, mins)):
                sensor._handle_minute(_at(MONDAY, hour, mins))
            if minute == 0:
                write_state.reset_mock()

    # 07:34 off (unchanged), 07:35 on, 07:36 on (unchanged), 08:05 off
    assert write_state.call_count == 2
