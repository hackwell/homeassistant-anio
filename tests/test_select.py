"""Tests for ANIO select entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.anio.const import DOMAIN, RING_PROFILES
from custom_components.anio.select import AnioRingProfileSelect, async_setup_entry

from .conftest import TEST_DEVICE_ID


class TestAnioRingProfileSelect:
    """Tests for AnioRingProfileSelect."""

    @pytest.fixture
    def ring_select(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> AnioRingProfileSelect:
        """Create a ring profile select for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        coordinator.async_request_refresh = AsyncMock()
        return AnioRingProfileSelect(
            coordinator=coordinator,
            client=mock_api_client,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, ring_select: AnioRingProfileSelect) -> None:
        """Test unique ID format."""
        assert ring_select.unique_id == f"{TEST_DEVICE_ID}_ring_profile"

    def test_name(self, ring_select: AnioRingProfileSelect) -> None:
        """Test select name."""
        assert ring_select.name == "Ring Profile"

    def test_icon(self, ring_select: AnioRingProfileSelect) -> None:
        """Test select icon."""
        assert ring_select.icon == "mdi:bell-ring"

    def test_entity_category(self, ring_select: AnioRingProfileSelect) -> None:
        """Test entity category."""
        assert ring_select.entity_category == EntityCategory.CONFIG

    def test_options(self, ring_select: AnioRingProfileSelect) -> None:
        """Test available options."""
        assert ring_select.options == RING_PROFILES
        assert "RING_AND_VIBRATE" in ring_select.options
        assert "VIBRATE_ONLY" in ring_select.options
        assert "SILENT" in ring_select.options

    def test_current_option(self, ring_select: AnioRingProfileSelect) -> None:
        """Test current option from coordinator data."""
        # Mock device settings has ringProfile="RING_AND_VIBRATE"
        assert ring_select.current_option == "RING_AND_VIBRATE"

    def test_current_option_no_data(self, hass: HomeAssistant) -> None:
        """Test current option when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        client = AsyncMock()
        select = AnioRingProfileSelect(
            coordinator=coordinator,
            client=client,
            device_id=TEST_DEVICE_ID,
        )
        assert select.current_option is None

    @pytest.mark.asyncio
    async def test_select_option(self, ring_select: AnioRingProfileSelect) -> None:
        """Test selecting a ring profile option."""
        await ring_select.async_select_option("SILENT")
        ring_select._client.update_device_settings.assert_called_once_with(
            TEST_DEVICE_ID, ringProfile="SILENT"
        )
        ring_select.coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_option_vibrate(
        self, ring_select: AnioRingProfileSelect
    ) -> None:
        """Test selecting vibrate only profile."""
        await ring_select.async_select_option("VIBRATE_ONLY")
        ring_select._client.update_device_settings.assert_called_once_with(
            TEST_DEVICE_ID, ringProfile="VIBRATE_ONLY"
        )


class TestSelectSetup:
    """Tests for select platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test select platform setup."""
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

        # Should create 1 select per device
        assert len(entities) == 1
        assert isinstance(entities[0], AnioRingProfileSelect)

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test select platform setup with no devices."""
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
