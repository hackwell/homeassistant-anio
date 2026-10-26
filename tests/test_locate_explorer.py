"""Locate Now button and Explorer Mode switch (#33)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.anio.api import AnioApiClient, AnioAuth, AnioConnectionError
from custom_components.anio.button import (
    LOCATE_COOLDOWN,
    LOCATE_REFRESH_DELAY,
    AnioLocateButton,
)
from custom_components.anio.switch import AnioExplorerModeSwitch

from .conftest import TEST_DEVICE_ID


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


@pytest.fixture
def coordinator(mock_coordinator_data: dict) -> MagicMock:
    """Create a coordinator mock with the test watch."""
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def _client_with_response() -> tuple[AnioApiClient, MagicMock]:
    """Create a client whose requests succeed without content."""
    response = MagicMock()
    response.status = 204
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.request.return_value = response
    auth = AsyncMock(spec=AnioAuth)
    auth.ensure_valid_token = AsyncMock(return_value="test_token")
    auth.app_uuid = "test-uuid"
    return AnioApiClient(session=session, auth=auth), session


@pytest.mark.asyncio
async def test_client_locate_request() -> None:
    """Test Locate Now calls the app's one-time locate (CR) route."""
    client, session = _client_with_response()

    await client.locate_device(TEST_DEVICE_ID)

    method, url = session.request.call_args.args[:2]
    assert method == "POST"
    assert url.endswith(f"/v1/device/{TEST_DEVICE_ID}/cr")


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [True, False])
async def test_client_explorer_request(active: bool) -> None:
    """Test the explorer mode body matches the ANIO app."""
    client, session = _client_with_response()

    await client.set_explorer_mode(TEST_DEVICE_ID, active)

    method, url = session.request.call_args.args[:2]
    assert method == "POST"
    assert url.endswith("/v1/explorer")
    assert session.request.call_args.kwargs["json"] == {
        "deviceId": TEST_DEVICE_ID,
        "activate": active,
    }


class TestLocateButton:
    """Tests for the Locate Now button."""

    @pytest.fixture
    def button(
        self, hass: HomeAssistant, coordinator: MagicMock, mock_api_client: AsyncMock
    ) -> AnioLocateButton:
        """Create the button."""
        button = AnioLocateButton(coordinator, mock_api_client, TEST_DEVICE_ID)
        button.hass = hass
        return button

    def test_ids(self, button: AnioLocateButton) -> None:
        """Test unique ID and translation key (no clash with the Ring button)."""
        assert button.unique_id == f"{TEST_DEVICE_ID}_locate_now"
        assert button.translation_key == "locate_now"

    @pytest.mark.asyncio
    async def test_press_locates_and_refreshes_later(
        self, button: AnioLocateButton, mock_api_client: AsyncMock
    ) -> None:
        """Test a press sends CR and schedules a refresh for the new position."""
        with patch("custom_components.anio.button.async_call_later") as call_later:
            await button.async_press()

        mock_api_client.locate_device.assert_awaited_once_with(TEST_DEVICE_ID)
        assert call_later.call_args.args[1] == LOCATE_REFRESH_DELAY

        await call_later.call_args.args[2](None)
        button.coordinator.async_request_refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_second_press_within_cooldown_is_rejected(
        self, button: AnioLocateButton, mock_api_client: AsyncMock
    ) -> None:
        """Test the watch isn't asked again while it is still locating."""
        with patch("custom_components.anio.button.async_call_later"):
            await button.async_press()
            with pytest.raises(ServiceValidationError) as err:
                await button.async_press()

        assert err.value.translation_key == "locate_cooldown"
        assert 0 < int(err.value.translation_placeholders["seconds"]) <= LOCATE_COOLDOWN
        mock_api_client.locate_device.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failed_press_does_not_block(
        self, button: AnioLocateButton, mock_api_client: AsyncMock
    ) -> None:
        """Test a failed request can be retried right away."""
        mock_api_client.locate_device.side_effect = [AnioConnectionError(), None]

        with patch("custom_components.anio.button.async_call_later"):
            with pytest.raises(HomeAssistantError):
                await button.async_press()
            await button.async_press()

        assert mock_api_client.locate_device.await_count == 2


class TestExplorerModeSwitch:
    """Tests for the Explorer Mode switch."""

    @pytest.fixture
    def switch(
        self, coordinator: MagicMock, mock_api_client: AsyncMock
    ) -> AnioExplorerModeSwitch:
        """Create the switch."""
        return AnioExplorerModeSwitch(coordinator, mock_api_client, TEST_DEVICE_ID)

    def test_ids(self, switch: AnioExplorerModeSwitch) -> None:
        """Test unique ID and translation key."""
        assert switch.unique_id == f"{TEST_DEVICE_ID}_explorer_mode"
        assert switch.translation_key == "explorer_mode"

    @pytest.mark.parametrize(
        ("tracking_mode", "expected"),
        [("EXPLORER", True), ("NORMAL", False), ("SCHOOLWAY", False), (None, False)],
    )
    def test_state_follows_tracking_mode(
        self,
        switch: AnioExplorerModeSwitch,
        mock_coordinator_data: dict,
        tracking_mode: str | None,
        expected: bool,
    ) -> None:
        """Test the switch is on while the tracking mode is EXPLORER."""
        mock_coordinator_data[TEST_DEVICE_ID].tracking_mode = tracking_mode
        assert switch.is_on is expected

    @pytest.mark.asyncio
    async def test_turn_on_and_off(
        self, switch: AnioExplorerModeSwitch, mock_api_client: AsyncMock
    ) -> None:
        """Test turning on and off sends activate and refreshes."""
        await switch.async_turn_on()
        await switch.async_turn_off()

        assert [c.args for c in mock_api_client.set_explorer_mode.await_args_list] == [
            (TEST_DEVICE_ID, True),
            (TEST_DEVICE_ID, False),
        ]
        assert switch.coordinator.async_request_refresh.await_count == 2

    @pytest.mark.asyncio
    async def test_error_is_translated(
        self, switch: AnioExplorerModeSwitch, mock_api_client: AsyncMock
    ) -> None:
        """Test API errors become readable messages."""
        mock_api_client.set_explorer_mode.side_effect = AnioConnectionError()

        with pytest.raises(HomeAssistantError) as err:
            await switch.async_turn_on()

        assert err.value.translation_key == "cannot_connect"
