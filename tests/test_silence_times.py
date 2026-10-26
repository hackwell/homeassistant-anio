"""Tests for reading silence times and alarms in the API's format."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.anio.api.models import (
    AlarmClock,
    AnioDeviceState,
    Device,
    SilenceTime,
    parse_weekdays,
)
from custom_components.anio.switch import AnioSilenceTimeSwitch

from .conftest import TEST_DEVICE_ID

# Shape of GET /v1/silence-time/{deviceId} as returned by the API
API_SILENCE_TIMES = [
    {
        "id": "s1",
        "days": "0111100",
        "deviceId": TEST_DEVICE_ID,
        "endTime": "13:00",
        "startTime": "08:00",
        "isEnabled": True,
    },
    {
        "id": "s2",
        "days": "0000010",
        "deviceId": TEST_DEVICE_ID,
        "endTime": "12:00",
        "startTime": "08:00",
        "isEnabled": True,
    },
]


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


class TestParseWeekdays:
    """Tests for the weekday bitstring."""

    @pytest.mark.parametrize(
        ("bits", "days"),
        [
            ("0111110", ["MON", "TUE", "WED", "THU", "FRI"]),
            ("0111100", ["MON", "TUE", "WED", "THU"]),
            ("0000010", ["FRI"]),
            ("1000001", ["SUN", "SAT"]),
            ("0000000", []),
        ],
    )
    def test_bitstring_starts_with_sunday(self, bits: str, days: list[str]) -> None:
        """Test the bitstring is read Sunday first."""
        assert parse_weekdays(bits) == days

    @pytest.mark.parametrize("value", ["011", "abcdefg", None, 5])
    def test_unexpected_values(self, value: object) -> None:
        """Test unexpected values give no days instead of failing."""
        assert parse_weekdays(value) == []

    def test_list_passes_through(self) -> None:
        """Test lists of day names are kept."""
        assert parse_weekdays(["MON", "FRI"]) == ["MON", "FRI"]


class TestModels:
    """Tests for the silence time and alarm models."""

    def test_silence_time_from_api(self) -> None:
        """Test a silence time in the API's format is read."""
        silence = SilenceTime.model_validate(API_SILENCE_TIMES[0])

        assert silence.days == ["MON", "TUE", "WED", "THU"]
        assert silence.enabled is True
        assert silence.start_time == "08:00"
        assert silence.end_time == "13:00"

    def test_disabled_silence_time(self) -> None:
        """Test isEnabled false is honoured."""
        silence = SilenceTime.model_validate(
            {**API_SILENCE_TIMES[0], "isEnabled": False}
        )

        assert silence.enabled is False

    def test_alarm_from_api(self) -> None:
        """Test an alarm with a bitstring and isEnabled is read."""
        alarm = AlarmClock.model_validate(
            {"id": "a1", "time": "07:00", "days": "0111110", "isEnabled": False}
        )

        assert alarm.days == ["MON", "TUE", "WED", "THU", "FRI"]
        assert alarm.enabled is False


class TestSilenceTimeSwitch:
    """Tests for the silence time switch with API data."""

    def test_switch_shows_api_silence_times(
        self, hass: HomeAssistant, mock_device: Device
    ) -> None:
        """Test the switch is on and lists the periods from the API."""
        state = AnioDeviceState(
            device=mock_device,
            silence_times=[SilenceTime.model_validate(s) for s in API_SILENCE_TIMES],
        )
        coordinator = MagicMock()
        coordinator.data = {TEST_DEVICE_ID: state}
        switch = AnioSilenceTimeSwitch(coordinator, MagicMock(), TEST_DEVICE_ID)

        assert switch.is_on is True
        attrs = switch.extra_state_attributes
        assert attrs is not None
        assert attrs["silence_time_count"] == 2
        assert attrs["periods"][0] == {
            "start": "08:00",
            "end": "13:00",
            "days": "MON, TUE, WED, THU",
            "enabled": True,
        }
        assert attrs["periods"][1]["days"] == "FRI"


def test_silence_times_are_not_shifted() -> None:
    """Test silence times (no deviceTimezone) stay as the app shows them."""
    silence = SilenceTime.model_validate(
        {
            "id": "s1",
            "days": "0111100",
            "isEnabled": True,
            "startTime": "08:00",
            "endTime": "16:00",
        }
    )

    assert (silence.local_start_time, silence.local_end_time) == ("08:00", "16:00")
