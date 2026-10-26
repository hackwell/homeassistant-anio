"""Silence Time Active sensor: on while the watch is silent."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.anio.api import SilenceTime
from custom_components.anio.binary_sensor import AnioSilenceActiveSensor

from .conftest import TEST_DEVICE_ID

# 2026-10-26 is a Monday, 2026-10-30 a Friday
MONDAY = datetime(2026, 10, 26, tzinfo=UTC)
FRIDAY = datetime(2026, 10, 30, tzinfo=UTC)


def _sensor(
    mock_coordinator_data: dict, enabled: bool = True
) -> AnioSilenceActiveSensor:
    """Create the sensor with the silence times of the test watch."""
    mock_coordinator_data[TEST_DEVICE_ID].silence_times = [
        SilenceTime.model_validate(
            {
                "id": "s1",
                "days": "0111100",
                "isEnabled": enabled,
                "startTime": "08:00",
                "endTime": "16:00",
            }
        ),
        SilenceTime.model_validate(
            {
                "id": "s2",
                "days": "0000010",
                "isEnabled": enabled,
                "startTime": "08:00",
                "endTime": "12:30",
            }
        ),
    ]
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    return AnioSilenceActiveSensor(coordinator, TEST_DEVICE_ID)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (MONDAY.replace(hour=10), True),
        (MONDAY.replace(hour=16, minute=30), False),
        (FRIDAY.replace(hour=12), True),
        (FRIDAY.replace(hour=13), False),
    ],
    ids=["monday_school", "monday_afternoon", "friday_school", "friday_afternoon"],
)
def test_on_during_silence_time(
    mock_coordinator_data: dict, now: datetime, expected: bool
) -> None:
    """Test the sensor follows the silence times."""
    sensor = _sensor(mock_coordinator_data)

    with patch("custom_components.anio.binary_sensor.dt_util.now", return_value=now):
        assert sensor.is_on is expected


def test_off_when_silence_times_are_switched_off(mock_coordinator_data: dict) -> None:
    """Test disabled silence times (switch off) never make the watch silent."""
    sensor = _sensor(mock_coordinator_data, enabled=False)

    with patch(
        "custom_components.anio.binary_sensor.dt_util.now",
        return_value=MONDAY.replace(hour=10),
    ):
        assert sensor.is_on is False


def test_unique_id_and_attributes(mock_coordinator_data: dict) -> None:
    """Test the unique ID and the listed periods."""
    sensor = _sensor(mock_coordinator_data)

    assert sensor.unique_id == f"{TEST_DEVICE_ID}_silence_active"
    assert sensor.translation_key == "silence_active"
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs["periods"][0] == {
        "start": "08:00",
        "end": "16:00",
        "days": "MON, TUE, WED, THU",
        "enabled": True,
    }
