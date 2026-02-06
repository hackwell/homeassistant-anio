"""Tests for ANIO switch entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.anio.const import DOMAIN
from custom_components.anio.switch import AnioSilenceTimeSwitch, async_setup_entry

from .conftest import TEST_DEVICE_ID


class TestAnioSilenceTimeSwitch:
    """Tests for AnioSilenceTimeSwitch."""

    @pytest.fixture
    def silence_switch(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> AnioSilenceTimeSwitch:
        """Create a silence time switch for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        coordinator.async_request_refresh = AsyncMock()
        return AnioSilenceTimeSwitch(
            coordinator=coordinator,
            client=mock_api_client,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, silence_switch: AnioSilenceTimeSwitch) -> None:
        """Test unique ID format."""
        assert silence_switch.unique_id == f"{TEST_DEVICE_ID}_silence_time"

    def test_name(self, silence_switch: AnioSilenceTimeSwitch) -> None:
        """Test switch name."""
        assert silence_switch.name == "Silence Time"

    def test_icon(self, silence_switch: AnioSilenceTimeSwitch) -> None:
        """Test switch icon."""
        assert silence_switch.icon == "mdi:volume-off"

    def test_entity_category(self, silence_switch: AnioSilenceTimeSwitch) -> None:
        """Test entity category."""
        assert silence_switch.entity_category == EntityCategory.CONFIG

    def test_is_on(self, silence_switch: AnioSilenceTimeSwitch) -> None:
        """Test is_on reflects enabled silence times."""
        # Mock data has one enabled silence time
        assert silence_switch.is_on is True

    def test_is_on_no_data(self, hass: HomeAssistant) -> None:
        """Test is_on when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        client = AsyncMock()
        switch = AnioSilenceTimeSwitch(
            coordinator=coordinator,
            client=client,
            device_id=TEST_DEVICE_ID,
        )
        assert switch.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on(self, silence_switch: AnioSilenceTimeSwitch) -> None:
        """Test turning on silence times."""
        await silence_switch.async_turn_on()
        silence_switch._client.enable_silence_times.assert_called_once_with(
            TEST_DEVICE_ID
        )
        silence_switch.coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off(self, silence_switch: AnioSilenceTimeSwitch) -> None:
        """Test turning off silence times."""
        await silence_switch.async_turn_off()
        silence_switch._client.disable_silence_times.assert_called_once_with(
            TEST_DEVICE_ID
        )
        silence_switch.coordinator.async_request_refresh.assert_called_once()

    def test_extra_state_attributes(
        self, silence_switch: AnioSilenceTimeSwitch
    ) -> None:
        """Test extra state attributes contain silence time details."""
        attrs = silence_switch.extra_state_attributes
        assert attrs is not None
        assert attrs["silence_time_count"] == 1
        assert len(attrs["periods"]) == 1
        assert attrs["periods"][0]["start"] == "22:00"
        assert attrs["periods"][0]["end"] == "07:00"
        assert attrs["periods"][0]["enabled"] is True


class TestSwitchSetup:
    """Tests for switch platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test switch platform setup."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
                "client": mock_api_client,
            }
        }

        entities = []

        def add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, add_entities)

        # Should create 1 switch per device
        assert len(entities) == 1
        assert isinstance(entities[0], AnioSilenceTimeSwitch)

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test switch platform setup with no devices."""
        coordinator = MagicMock()
        coordinator.data = {}

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
                "client": mock_api_client,
            }
        }

        entities = []

        def add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, add_entities)

        assert len(entities) == 0
