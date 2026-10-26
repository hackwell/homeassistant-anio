"""Switches for single school way times, silence times and geofences."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.anio.api import (
    AnioApiClient,
    AnioAuth,
    AnioConnectionError,
    Geofence,
    SchoolWayTime,
    SilenceTime,
)
from custom_components.anio.api.models import format_weekdays
from custom_components.anio.switch import (
    AnioGeofenceMonitoringSwitch,
    AnioSchoolWayTimeSwitch,
    AnioSilenceTimeEntrySwitch,
)

from .conftest import TEST_DEVICE_ID

SCHOOL_WAY = SchoolWayTime.model_validate(
    {
        "id": "sw1",
        "days": "0111110",
        "isEnabled": True,
        "startTime": "07:35",
        "endTime": "08:05",
    }
)
SILENCE = SilenceTime.model_validate(
    {
        "id": "si1",
        "days": "0111100",
        "isEnabled": False,
        "startTime": "08:00",
        "endTime": "16:00",
    }
)


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


@pytest.fixture
def coordinator(mock_coordinator_data: dict) -> MagicMock:
    """Create a coordinator with one school way and one silence time."""
    state = mock_coordinator_data[TEST_DEVICE_ID]
    state.school_way_times = [SCHOOL_WAY]
    state.silence_times = [SILENCE]
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    coordinator.last_update_success = True
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.mark.parametrize(
    ("days", "language", "expected"),
    [
        (["MON", "TUE", "WED", "THU", "FRI"], "de", "Mo–Fr"),
        (["MON", "TUE", "WED", "THU"], "de", "Mo–Do"),
        (["FRI"], "de", "Fr"),
        (["SAT", "SUN"], "de", "Sa, So"),
        (["MON", "WED"], "de", "Mo, Mi"),
        (["MON", "TUE", "WED", "SAT", "SUN"], "de", "Mo–Mi, Sa, So"),
        (["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"], "de", "täglich"),
        (["MON", "TUE", "WED", "THU", "FRI"], "en", "Mon–Fri"),
        (["MON", "TUE", "WED", "THU", "FRI"], "en-GB", "Mon–Fri"),
        ([], "de", ""),
    ],
)
def test_format_weekdays(days: list[str], language: str, expected: str) -> None:
    """Test weekdays are written compactly, Monday first."""
    assert format_weekdays(days, language) == expected


def test_describe() -> None:
    """Test the period used in entity names."""
    assert SCHOOL_WAY.describe("de") == "07:35–08:05 Mo–Fr"
    assert SILENCE.describe("en") == "08:00–16:00 Mon–Thu"


def _client() -> tuple[AnioApiClient, MagicMock]:
    """Create a client whose requests succeed."""
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={})
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.request.return_value = response
    auth = AsyncMock(spec=AnioAuth)
    auth.ensure_valid_token = AsyncMock(return_value="test_token")
    auth.app_uuid = "test-uuid"
    return AnioApiClient(session=session, auth=auth), session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("set_school_way_time_enabled", "/v2/school-way-time/x1"),
        ("set_silence_time_enabled", "/v1/silence-time/x1"),
        ("set_geofence_enabled", "/v1/geofence/x1"),
    ],
)
async def test_client_sends_only_the_flag(method: str, path: str) -> None:
    """Test only isEnabled is sent, so times and days stay (tested on a watch)."""
    client, session = _client()

    await getattr(client, method)("x1", False)

    assert session.request.call_args.args[0] == "PATCH"
    assert session.request.call_args.args[1].endswith(path)
    assert session.request.call_args.kwargs["json"] == {"isEnabled": False}


class TestTimeEntrySwitches:
    """Tests for the school way and silence time switches."""

    def test_school_way_switch(
        self, coordinator: MagicMock, mock_api_client: AsyncMock
    ) -> None:
        """Test name, ID, state and attributes."""
        switch = AnioSchoolWayTimeSwitch(
            coordinator, mock_api_client, TEST_DEVICE_ID, SCHOOL_WAY, "de"
        )

        assert switch.unique_id == f"{TEST_DEVICE_ID}_school_way_time_sw1"
        assert switch.translation_placeholders == {"period": "07:35–08:05 Mo–Fr"}
        assert switch.entity_category == EntityCategory.CONFIG
        assert switch.is_on is True
        assert switch.available is True
        assert switch.extra_state_attributes == {
            "start": "07:35",
            "end": "08:05",
            "days": "MON, TUE, WED, THU, FRI",
        }

    def test_silence_switch_state(
        self, coordinator: MagicMock, mock_api_client: AsyncMock
    ) -> None:
        """Test a disabled silence time (e.g. holidays) is off."""
        switch = AnioSilenceTimeEntrySwitch(
            coordinator, mock_api_client, TEST_DEVICE_ID, SILENCE, "de"
        )

        assert switch.unique_id == f"{TEST_DEVICE_ID}_silence_time_entry_si1"
        assert switch.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_and_off(
        self, coordinator: MagicMock, mock_api_client: AsyncMock
    ) -> None:
        """Test switching calls the API and fetches the slow data again."""
        school = AnioSchoolWayTimeSwitch(
            coordinator, mock_api_client, TEST_DEVICE_ID, SCHOOL_WAY, "de"
        )
        silence = AnioSilenceTimeEntrySwitch(
            coordinator, mock_api_client, TEST_DEVICE_ID, SILENCE, "de"
        )

        await school.async_turn_off()
        await silence.async_turn_on()

        mock_api_client.set_school_way_time_enabled.assert_awaited_once_with(
            "sw1", False
        )
        mock_api_client.set_silence_time_enabled.assert_awaited_once_with("si1", True)
        assert coordinator.invalidate_slow_data.call_count == 2
        assert coordinator.async_request_refresh.await_count == 2

    @pytest.mark.asyncio
    async def test_error_is_translated(
        self, coordinator: MagicMock, mock_api_client: AsyncMock
    ) -> None:
        """Test API errors become readable messages."""
        mock_api_client.set_school_way_time_enabled.side_effect = AnioConnectionError()
        switch = AnioSchoolWayTimeSwitch(
            coordinator, mock_api_client, TEST_DEVICE_ID, SCHOOL_WAY, "de"
        )

        with pytest.raises(HomeAssistantError) as err:
            await switch.async_turn_off()

        assert err.value.translation_key == "cannot_connect"
        coordinator.invalidate_slow_data.assert_not_called()

    def test_follows_changes_and_deletion(
        self, coordinator: MagicMock, mock_api_client: AsyncMock
    ) -> None:
        """Test the name follows new times; deleted entries become unavailable."""
        switch = AnioSchoolWayTimeSwitch(
            coordinator, mock_api_client, TEST_DEVICE_ID, SCHOOL_WAY, "de"
        )
        state = coordinator.data[TEST_DEVICE_ID]
        state.school_way_times = [SCHOOL_WAY.model_copy(update={"start_time": "07:40"})]

        with patch.object(switch, "async_write_ha_state"):
            switch._handle_coordinator_update()
        assert switch.translation_placeholders == {"period": "07:40–08:05 Mo–Fr"}

        state.school_way_times = []
        assert switch.available is False
        assert switch.is_on is None


class TestGeofenceMonitoringSwitch:
    """Tests for the geofence monitoring switch."""

    @pytest.fixture
    def switch(
        self,
        coordinator: MagicMock,
        mock_api_client: AsyncMock,
        mock_geofence: Geofence,
    ) -> AnioGeofenceMonitoringSwitch:
        """Create the switch for the test geofence."""
        return AnioGeofenceMonitoringSwitch(
            coordinator, mock_api_client, TEST_DEVICE_ID, mock_geofence
        )

    def test_ids_and_state(
        self, switch: AnioGeofenceMonitoringSwitch, mock_geofence: Geofence
    ) -> None:
        """Test name placeholder, ID and state."""
        assert (
            switch.unique_id
            == f"{TEST_DEVICE_ID}_geofence_{mock_geofence.id}_monitoring"
        )
        assert switch.translation_placeholders == {"geofence_name": mock_geofence.name}
        assert switch.is_on is mock_geofence.is_enabled

    @pytest.mark.asyncio
    async def test_turn_off(
        self,
        switch: AnioGeofenceMonitoringSwitch,
        mock_api_client: AsyncMock,
        mock_geofence: Geofence,
        coordinator: MagicMock,
    ) -> None:
        """Test switching off calls the API and refreshes."""
        await switch.async_turn_off()

        mock_api_client.set_geofence_enabled.assert_awaited_once_with(
            mock_geofence.id, False
        )
        coordinator.invalidate_slow_data.assert_called_once_with(TEST_DEVICE_ID)
        coordinator.async_request_refresh.assert_awaited_once()

    def test_unavailable_after_deletion(
        self, switch: AnioGeofenceMonitoringSwitch, coordinator: MagicMock
    ) -> None:
        """Test a geofence deleted in the app makes the switch unavailable."""
        coordinator.data[TEST_DEVICE_ID].geofences = []
        assert switch.available is False
