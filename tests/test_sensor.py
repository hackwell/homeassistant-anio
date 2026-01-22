"""Tests for ANIO sensor entities."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.anio.const import DOMAIN
from custom_components.anio.sensor import (
    AnioBatterySensor,
    AnioLastSeenSensor,
    AnioStepsSensor,
    async_setup_entry,
)

from .conftest import TEST_DEVICE_ID, TEST_DEVICE_NAME


class TestAnioBatterySensor:
    """Tests for AnioBatterySensor."""

    @pytest.fixture
    def battery_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioBatterySensor:
        """Create a battery sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioBatterySensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, battery_sensor: AnioBatterySensor) -> None:
        """Test unique ID format."""
        assert battery_sensor.unique_id == f"{TEST_DEVICE_ID}_battery"

    def test_name(self, battery_sensor: AnioBatterySensor) -> None:
        """Test sensor name."""
        assert battery_sensor.name == f"{TEST_DEVICE_NAME} Battery"

    def test_device_class(self, battery_sensor: AnioBatterySensor) -> None:
        """Test device class."""
        assert battery_sensor.device_class == SensorDeviceClass.BATTERY

    def test_native_unit(self, battery_sensor: AnioBatterySensor) -> None:
        """Test native unit of measurement."""
        assert battery_sensor.native_unit_of_measurement == PERCENTAGE

    def test_state_class(self, battery_sensor: AnioBatterySensor) -> None:
        """Test state class."""
        assert battery_sensor.state_class == SensorStateClass.MEASUREMENT

    def test_entity_category(self, battery_sensor: AnioBatterySensor) -> None:
        """Test entity category."""
        assert battery_sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_native_value(self, battery_sensor: AnioBatterySensor) -> None:
        """Test battery value from coordinator data."""
        # Mock data has battery = 85 from conftest
        assert battery_sensor.native_value == 85

    def test_native_value_no_data(self, hass: HomeAssistant) -> None:
        """Test battery value when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        sensor = AnioBatterySensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.native_value is None


class TestAnioLastSeenSensor:
    """Tests for AnioLastSeenSensor."""

    @pytest.fixture
    def last_seen_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioLastSeenSensor:
        """Create a last seen sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioLastSeenSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, last_seen_sensor: AnioLastSeenSensor) -> None:
        """Test unique ID format."""
        assert last_seen_sensor.unique_id == f"{TEST_DEVICE_ID}_last_seen"

    def test_name(self, last_seen_sensor: AnioLastSeenSensor) -> None:
        """Test sensor name."""
        assert last_seen_sensor.name == f"{TEST_DEVICE_NAME} Last Seen"

    def test_device_class(self, last_seen_sensor: AnioLastSeenSensor) -> None:
        """Test device class."""
        assert last_seen_sensor.device_class == SensorDeviceClass.TIMESTAMP

    def test_entity_category(self, last_seen_sensor: AnioLastSeenSensor) -> None:
        """Test entity category."""
        assert last_seen_sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_native_value(self, last_seen_sensor: AnioLastSeenSensor) -> None:
        """Test last seen value from coordinator data."""
        value = last_seen_sensor.native_value
        assert value is not None
        assert isinstance(value, datetime)

    def test_native_value_no_data(self, hass: HomeAssistant) -> None:
        """Test last seen value when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        sensor = AnioLastSeenSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.native_value is None


class TestAnioStepsSensor:
    """Tests for AnioStepsSensor."""

    @pytest.fixture
    def steps_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioStepsSensor:
        """Create a steps sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioStepsSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, steps_sensor: AnioStepsSensor) -> None:
        """Test unique ID format."""
        assert steps_sensor.unique_id == f"{TEST_DEVICE_ID}_steps"

    def test_name(self, steps_sensor: AnioStepsSensor) -> None:
        """Test sensor name."""
        assert steps_sensor.name == f"{TEST_DEVICE_NAME} Steps"

    def test_state_class(self, steps_sensor: AnioStepsSensor) -> None:
        """Test state class for daily reset."""
        assert steps_sensor.state_class == SensorStateClass.TOTAL_INCREASING

    def test_icon(self, steps_sensor: AnioStepsSensor) -> None:
        """Test sensor icon."""
        assert steps_sensor.icon == "mdi:walk"

    def test_native_value(self, steps_sensor: AnioStepsSensor) -> None:
        """Test steps value from coordinator data."""
        # Mock data has stepCount = 5432 from conftest
        assert steps_sensor.native_value == 5432

    def test_native_value_no_data(self, hass: HomeAssistant) -> None:
        """Test steps value when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        sensor = AnioStepsSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.native_value is None

    def test_extra_state_attributes(self, steps_sensor: AnioStepsSensor) -> None:
        """Test extra state attributes."""
        attrs = steps_sensor.extra_state_attributes
        assert attrs is not None
        assert "step_target" in attrs
        assert attrs["step_target"] == 10000


class TestSensorSetup:
    """Tests for sensor platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_coordinator_data: dict,
    ) -> None:
        """Test sensor platform setup."""
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

        # Should create battery, last_seen, and steps sensors for each device
        assert len(entities) == 3
        assert any(isinstance(e, AnioBatterySensor) for e in entities)
        assert any(isinstance(e, AnioLastSeenSensor) for e in entities)
        assert any(isinstance(e, AnioStepsSensor) for e in entities)

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test sensor platform setup with no devices."""
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
