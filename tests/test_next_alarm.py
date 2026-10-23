"""Next Alarm honours the weekdays of each alarm."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from custom_components.anio.api import AlarmClock
from custom_components.anio.sensor import AnioNextAlarmSensor, next_alarm

from .conftest import TEST_DEVICE_ID

WEEKDAYS_ONLY = ["MON", "TUE", "WED", "THU", "FRI"]
# 2026-10-24 is a Saturday
SATURDAY_MORNING = datetime(2026, 10, 24, 6, 0, tzinfo=UTC)


def _alarm(
    alarm_id: str, time: str, days: list[str], enabled: bool = True
) -> AlarmClock:
    """Create an alarm."""
    return AlarmClock(id=alarm_id, time=time, days=days, enabled=enabled)


def test_weekday_alarm_skips_the_weekend() -> None:
    """Test a weekday-only alarm is not shown for Saturday."""
    school = _alarm("school", "07:00", WEEKDAYS_ONLY)

    result = next_alarm([school], SATURDAY_MORNING)

    assert result is not None
    alarm, rings_at = result
    assert alarm is school
    assert rings_at == datetime(2026, 10, 26, 7, 0, tzinfo=UTC)  # Monday


def test_earliest_upcoming_alarm_wins() -> None:
    """Test a later weekend alarm beats an earlier weekday-only one."""
    school = _alarm("school", "07:00", WEEKDAYS_ONLY)
    weekend = _alarm("weekend", "09:00", ["SAT", "SUN"])

    result = next_alarm([school, weekend], SATURDAY_MORNING)

    assert result is not None
    alarm, rings_at = result
    assert alarm is weekend
    assert rings_at == datetime(2026, 10, 24, 9, 0, tzinfo=UTC)


def test_passed_alarm_rings_on_the_next_matching_day() -> None:
    """Test an alarm that already rang today moves to its next day."""
    saturday = _alarm("sat", "05:00", ["SAT"])

    result = next_alarm([saturday], SATURDAY_MORNING)

    assert result is not None
    assert result[1] == datetime(2026, 10, 31, 5, 0, tzinfo=UTC)


def test_alarm_without_days_is_daily() -> None:
    """Test an alarm without weekdays rings every day."""
    daily = _alarm("daily", "05:30", [])

    result = next_alarm([daily], SATURDAY_MORNING)

    assert result is not None
    assert result[1] == datetime(2026, 10, 25, 5, 30, tzinfo=UTC)


def test_disabled_and_unreadable_alarms_are_ignored() -> None:
    """Test disabled alarms and unreadable times are skipped."""
    alarms = [
        _alarm("off", "06:30", [*WEEKDAYS_ONLY, "SAT"], enabled=False),
        _alarm("broken", "later", ["SAT"]),
    ]

    assert next_alarm(alarms, SATURDAY_MORNING) is None


def test_sensor_shows_next_alarm(mock_coordinator_data: dict) -> None:
    """Test the sensor state and attributes on a Saturday."""
    mock_coordinator_data[TEST_DEVICE_ID].alarms = [
        _alarm("school", "07:00", WEEKDAYS_ONLY),
        _alarm("weekend", "09:00", ["SAT", "SUN"]),
    ]
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    sensor = AnioNextAlarmSensor(coordinator=coordinator, device_id=TEST_DEVICE_ID)

    with patch(
        "custom_components.anio.sensor.dt_util.now", return_value=SATURDAY_MORNING
    ):
        value = sensor.native_value
        attrs = sensor.extra_state_attributes

    assert value == "09:00"
    assert attrs is not None
    assert attrs["next_alarm_days"] == "SAT, SUN"
    assert attrs["next_alarm_at"] == "2026-10-24T09:00:00+00:00"
    assert attrs["enabled_count"] == 2
