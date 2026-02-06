"""Tests for ANIO sensor entities."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.anio.const import DOMAIN
from custom_components.anio.sensor import (
    AnioBatterySensor,
    AnioLastMessageSensor,
    AnioLastSeenSensor,
    AnioNextAlarmSensor,
    AnioSignalStrengthSensor,
    AnioTrackingModeSensor,
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
        assert battery_sensor.name == "Battery"

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
        assert last_seen_sensor.name == "Last Seen"

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

        def add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, add_entities)

        # Should create 6 sensors per device
        assert len(entities) == 6
        assert any(isinstance(e, AnioBatterySensor) for e in entities)
        assert any(isinstance(e, AnioLastSeenSensor) for e in entities)
        assert any(isinstance(e, AnioSignalStrengthSensor) for e in entities)
        assert any(isinstance(e, AnioLastMessageSensor) for e in entities)
        assert any(isinstance(e, AnioNextAlarmSensor) for e in entities)
        assert any(isinstance(e, AnioTrackingModeSensor) for e in entities)

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

        def add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, add_entities)

        assert len(entities) == 0


class TestAnioSignalStrengthSensor:
    """Tests for AnioSignalStrengthSensor."""

    @pytest.fixture
    def signal_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioSignalStrengthSensor:
        """Create a signal strength sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioSignalStrengthSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, signal_sensor: AnioSignalStrengthSensor) -> None:
        """Test unique ID format."""
        assert signal_sensor.unique_id == f"{TEST_DEVICE_ID}_signal_strength"

    def test_name(self, signal_sensor: AnioSignalStrengthSensor) -> None:
        """Test sensor name."""
        assert signal_sensor.name == "Signal Strength"

    def test_icon(self, signal_sensor: AnioSignalStrengthSensor) -> None:
        """Test sensor icon."""
        assert signal_sensor.icon == "mdi:signal"

    def test_native_unit(self, signal_sensor: AnioSignalStrengthSensor) -> None:
        """Test native unit of measurement."""
        assert signal_sensor.native_unit_of_measurement == PERCENTAGE

    def test_state_class(self, signal_sensor: AnioSignalStrengthSensor) -> None:
        """Test state class."""
        assert signal_sensor.state_class == SensorStateClass.MEASUREMENT

    def test_entity_category(self, signal_sensor: AnioSignalStrengthSensor) -> None:
        """Test entity category."""
        assert signal_sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_native_value(self, signal_sensor: AnioSignalStrengthSensor) -> None:
        """Test signal strength value from coordinator data."""
        assert signal_sensor.native_value == 60

    def test_native_value_no_data(self, hass: HomeAssistant) -> None:
        """Test signal strength value when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        sensor = AnioSignalStrengthSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.native_value is None


class TestAnioLastMessageSensor:
    """Tests for AnioLastMessageSensor."""

    @pytest.fixture
    def message_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioLastMessageSensor:
        """Create a last message sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioLastMessageSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, message_sensor: AnioLastMessageSensor) -> None:
        """Test unique ID format."""
        assert message_sensor.unique_id == f"{TEST_DEVICE_ID}_last_message"

    def test_name(self, message_sensor: AnioLastMessageSensor) -> None:
        """Test sensor name."""
        assert message_sensor.name == "Last Message"

    def test_icon(self, message_sensor: AnioLastMessageSensor) -> None:
        """Test sensor icon."""
        assert message_sensor.icon == "mdi:message-text"

    def test_native_value(self, message_sensor: AnioLastMessageSensor) -> None:
        """Test last message value from coordinator data."""
        assert message_sensor.native_value == "Hi Mom!"

    def test_extra_state_attributes(self, message_sensor: AnioLastMessageSensor) -> None:
        """Test extra state attributes contain message metadata."""
        attrs = message_sensor.extra_state_attributes
        assert attrs is not None
        assert attrs["sender"] == "WATCH"
        assert attrs["type"] == "TEXT"
        assert attrs["is_read"] is False
        assert "created_at" in attrs

    def test_native_value_no_data(self, hass: HomeAssistant) -> None:
        """Test last message value when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        sensor = AnioLastMessageSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.native_value is None
        assert sensor.extra_state_attributes is None


class TestAnioNextAlarmSensor:
    """Tests for AnioNextAlarmSensor."""

    @pytest.fixture
    def alarm_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioNextAlarmSensor:
        """Create a next alarm sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioNextAlarmSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, alarm_sensor: AnioNextAlarmSensor) -> None:
        """Test unique ID format."""
        assert alarm_sensor.unique_id == f"{TEST_DEVICE_ID}_next_alarm"

    def test_name(self, alarm_sensor: AnioNextAlarmSensor) -> None:
        """Test sensor name."""
        assert alarm_sensor.name == "Next Alarm"

    def test_icon(self, alarm_sensor: AnioNextAlarmSensor) -> None:
        """Test sensor icon."""
        assert alarm_sensor.icon == "mdi:alarm"

    def test_native_value(self, alarm_sensor: AnioNextAlarmSensor) -> None:
        """Test next alarm value from coordinator data."""
        assert alarm_sensor.native_value == "07:30"

    def test_extra_state_attributes(self, alarm_sensor: AnioNextAlarmSensor) -> None:
        """Test extra state attributes contain alarm metadata."""
        attrs = alarm_sensor.extra_state_attributes
        assert attrs is not None
        assert attrs["alarm_count"] == 1
        assert attrs["enabled_count"] == 1
        assert "MON" in attrs["next_alarm_days"]

    def test_native_value_no_data(self, hass: HomeAssistant) -> None:
        """Test next alarm value when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        sensor = AnioNextAlarmSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.native_value is None


class TestAnioTrackingModeSensor:
    """Tests for AnioTrackingModeSensor."""

    @pytest.fixture
    def tracking_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
    ) -> AnioTrackingModeSensor:
        """Create a tracking mode sensor for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioTrackingModeSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, tracking_sensor: AnioTrackingModeSensor) -> None:
        """Test unique ID format."""
        assert tracking_sensor.unique_id == f"{TEST_DEVICE_ID}_tracking_mode"

    def test_name(self, tracking_sensor: AnioTrackingModeSensor) -> None:
        """Test sensor name."""
        assert tracking_sensor.name == "Tracking Mode"

    def test_icon(self, tracking_sensor: AnioTrackingModeSensor) -> None:
        """Test sensor icon."""
        assert tracking_sensor.icon == "mdi:crosshairs-gps"

    def test_entity_category(self, tracking_sensor: AnioTrackingModeSensor) -> None:
        """Test entity category."""
        from homeassistant.const import EntityCategory
        assert tracking_sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_native_value(self, tracking_sensor: AnioTrackingModeSensor) -> None:
        """Test tracking mode value from coordinator data."""
        assert tracking_sensor.native_value == "NORMAL"

    def test_native_value_no_data(self, hass: HomeAssistant) -> None:
        """Test tracking mode value when no data available."""
        coordinator = MagicMock()
        coordinator.data = {}
        sensor = AnioTrackingModeSensor(
            coordinator=coordinator,
            device_id=TEST_DEVICE_ID,
        )
        assert sensor.native_value is None
