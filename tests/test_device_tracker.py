"""Tests for ANIO device tracker platform."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from homeassistant.components.device_tracker import SourceType
from homeassistant.core import HomeAssistant

from custom_components.anio.api import LocationInfo
from custom_components.anio.const import DOMAIN
from custom_components.anio.device_tracker import (
    AnioDeviceTracker,
    async_setup_entry,
)

from .conftest import TEST_DEVICE_ID, TEST_DEVICE_NAME


class TestAnioDeviceTracker:
    """Tests for AnioDeviceTracker."""

    @pytest.fixture
    def device_tracker(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioDeviceTracker:
        """Create a device tracker for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioDeviceTracker(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, device_tracker: AnioDeviceTracker) -> None:
        """Test unique ID format."""
        assert device_tracker.unique_id == f"{TEST_DEVICE_ID}_location"

    def test_name(self, device_tracker: AnioDeviceTracker) -> None:
        """Test tracker name."""
        assert device_tracker.name == f"{TEST_DEVICE_NAME} Location"

    def test_source_type(self, device_tracker: AnioDeviceTracker) -> None:
        """Test source type is GPS."""
        assert device_tracker.source_type == SourceType.GPS

    def test_latitude(self, device_tracker: AnioDeviceTracker) -> None:
        """Test latitude from location data."""
        # Mock data has lat=52.5200 from conftest
        assert device_tracker.latitude == 52.5200

    def test_longitude(self, device_tracker: AnioDeviceTracker) -> None:
        """Test longitude from location data."""
        # Mock data has lng=13.4050 from conftest
        assert device_tracker.longitude == 13.4050

    def test_location_accuracy(self, device_tracker: AnioDeviceTracker) -> None:
        """Test location accuracy."""
        # Mock data has accuracy=10 from conftest
        assert device_tracker.location_accuracy == 10

    def test_latitude_no_location(self, hass: HomeAssistant, mock_device_state) -> None:
        """Test latitude when no location available."""
        mock_device_state.location = None
        coordinator = MagicMock()
        coordinator.data = {TEST_DEVICE_ID: mock_device_state}

        tracker = AnioDeviceTracker(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert tracker.latitude is None
        assert tracker.longitude is None

    def test_latitude_no_data(self, hass: HomeAssistant) -> None:
        """Test latitude when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}

        tracker = AnioDeviceTracker(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert tracker.latitude is None
        assert tracker.longitude is None

    def test_extra_state_attributes(
        self,
        device_tracker: AnioDeviceTracker,
    ) -> None:
        """Test extra state attributes include location metadata."""
        attrs = device_tracker.extra_state_attributes
        assert attrs is not None
        assert "accuracy" in attrs
        assert "last_update" in attrs

    def test_extra_state_attributes_no_location(
        self,
        hass: HomeAssistant,
        mock_device_state,
    ) -> None:
        """Test extra state attributes when no location."""
        mock_device_state.location = None
        coordinator = MagicMock()
        coordinator.data = {TEST_DEVICE_ID: mock_device_state}

        tracker = AnioDeviceTracker(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        attrs = tracker.extra_state_attributes
        assert attrs is None or attrs == {}


class TestDeviceTrackerSetup:
    """Tests for device tracker platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_coordinator_data: dict,
    ) -> None:
        """Test device tracker platform setup."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
            }
        }

        entities = []

        async def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Should create one tracker per device
        assert len(entities) == 1
        assert isinstance(entities[0], AnioDeviceTracker)

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device tracker platform setup with no devices."""
        coordinator = MagicMock()
        coordinator.data = {}

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
            }
        }

        entities = []

        async def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        assert len(entities) == 0

    @pytest.mark.asyncio
    async def test_async_setup_entry_multiple_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_device_state,
    ) -> None:
        """Test device tracker platform setup with multiple devices."""
        # Create second device state
        from copy import deepcopy

        device_state_2 = deepcopy(mock_device_state)
        device_state_2.device.id = "device456"
        device_state_2.device.settings.name = "Second Watch"

        coordinator = MagicMock()
        coordinator.data = {
            TEST_DEVICE_ID: mock_device_state,
            "device456": device_state_2,
        }

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
            }
        }

        entities = []

        async def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        assert len(entities) == 2
