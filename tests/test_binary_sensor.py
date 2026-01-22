"""Tests for ANIO binary sensor entities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.anio.api import AnioDeviceState, Geofence
from custom_components.anio.binary_sensor import (
    AnioGeofenceSensor,
    AnioOnlineSensor,
    async_setup_entry,
)
from custom_components.anio.const import DOMAIN

from .conftest import TEST_DEVICE_ID, TEST_DEVICE_NAME


class TestAnioOnlineSensor:
    """Tests for AnioOnlineSensor."""

    @pytest.fixture
    def online_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioOnlineSensor:
        """Create an online sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioOnlineSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, online_sensor: AnioOnlineSensor) -> None:
        """Test unique ID format."""
        assert online_sensor.unique_id == f"{TEST_DEVICE_ID}_online"

    def test_name(self, online_sensor: AnioOnlineSensor) -> None:
        """Test sensor name."""
        assert online_sensor.name == f"{TEST_DEVICE_NAME} Online"

    def test_device_class(self, online_sensor: AnioOnlineSensor) -> None:
        """Test device class."""
        assert online_sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY

    def test_entity_category(self, online_sensor: AnioOnlineSensor) -> None:
        """Test entity category."""
        assert online_sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_is_on_when_online(self, online_sensor: AnioOnlineSensor) -> None:
        """Test is_on returns True when device is online."""
        # Mock data has is_online = True from conftest
        assert online_sensor.is_on is True

    def test_is_on_when_offline(self, hass: HomeAssistant, mock_device_state: AnioDeviceState) -> None:
        """Test is_on returns False when device is offline."""
        mock_device_state.is_online = False
        coordinator = MagicMock()
        coordinator.data = {TEST_DEVICE_ID: mock_device_state}

        sensor = AnioOnlineSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.is_on is False

    def test_is_on_no_data(self, hass: HomeAssistant) -> None:
        """Test is_on returns None when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        sensor = AnioOnlineSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.is_on is None


class TestAnioGeofenceSensor:
    """Tests for AnioGeofenceSensor."""

    @pytest.fixture
    def geofence_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_geofence: Geofence,
    ) -> AnioGeofenceSensor:
        """Create a geofence sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        coordinator.is_device_in_geofence = MagicMock(return_value=True)
        return AnioGeofenceSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
            geofence=mock_geofence,
        )

    def test_unique_id(self, geofence_sensor: AnioGeofenceSensor, mock_geofence: Geofence) -> None:
        """Test unique ID format."""
        expected_id = f"{TEST_DEVICE_ID}_geofence_{mock_geofence.id}"
        assert geofence_sensor.unique_id == expected_id

    def test_name(self, geofence_sensor: AnioGeofenceSensor, mock_geofence: Geofence) -> None:
        """Test sensor name."""
        expected_name = f"{TEST_DEVICE_NAME} at {mock_geofence.name}"
        assert geofence_sensor.name == expected_name

    def test_device_class(self, geofence_sensor: AnioGeofenceSensor) -> None:
        """Test device class."""
        assert geofence_sensor.device_class == BinarySensorDeviceClass.PRESENCE

    def test_is_on_inside_geofence(self, geofence_sensor: AnioGeofenceSensor) -> None:
        """Test is_on returns True when device is inside geofence."""
        assert geofence_sensor.is_on is True

    def test_is_on_outside_geofence(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_geofence: Geofence,
    ) -> None:
        """Test is_on returns False when device is outside geofence."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        coordinator.is_device_in_geofence = MagicMock(return_value=False)

        sensor = AnioGeofenceSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
            geofence=mock_geofence,
        )
        assert sensor.is_on is False

    def test_extra_state_attributes(
        self,
        geofence_sensor: AnioGeofenceSensor,
        mock_geofence: Geofence,
    ) -> None:
        """Test extra state attributes include geofence info."""
        attrs = geofence_sensor.extra_state_attributes
        assert attrs is not None
        assert "geofence_name" in attrs
        assert attrs["geofence_name"] == mock_geofence.name
        assert "radius_meters" in attrs
        assert attrs["radius_meters"] == mock_geofence.radius
        assert "latitude" in attrs
        assert "longitude" in attrs


class TestBinarySensorSetup:
    """Tests for binary sensor platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_coordinator_data: dict,
        mock_geofence: Geofence,
    ) -> None:
        """Test binary sensor platform setup."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        coordinator.geofences = [mock_geofence]
        coordinator.is_device_in_geofence = MagicMock(return_value=True)

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
            }
        }

        entities = []

        async def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Should create online sensor + geofence sensors for each device
        assert len(entities) >= 1
        assert any(isinstance(e, AnioOnlineSensor) for e in entities)
        # One geofence sensor per device per geofence
        geofence_sensors = [e for e in entities if isinstance(e, AnioGeofenceSensor)]
        assert len(geofence_sensors) == 1

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test binary sensor platform setup with no devices."""
        coordinator = MagicMock()
        coordinator.data = {}
        coordinator.geofences = []

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
    async def test_async_setup_entry_multiple_geofences(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_coordinator_data: dict,
    ) -> None:
        """Test binary sensor platform setup with multiple geofences."""
        geofence1 = Geofence(
            id="geo1",
            name="Home",
            lat=52.5200,
            lng=13.4050,
            radius=100,
        )
        geofence2 = Geofence(
            id="geo2",
            name="School",
            lat=52.5300,
            lng=13.4100,
            radius=200,
        )

        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        coordinator.geofences = [geofence1, geofence2]
        coordinator.is_device_in_geofence = MagicMock(return_value=False)

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
            }
        }

        entities = []

        async def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Should have 1 online sensor + 2 geofence sensors per device
        geofence_sensors = [e for e in entities if isinstance(e, AnioGeofenceSensor)]
        assert len(geofence_sensors) == 2
