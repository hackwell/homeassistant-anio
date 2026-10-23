"""Tests for geofences in the format of GET /v1/geofence/{deviceId}."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pydantic import ValidationError

from custom_components.anio.api.models import (
    AnioDeviceState,
    Device,
    Geofence,
    LocationInfo,
)
from custom_components.anio.binary_sensor import AnioGeofenceSensor

from .conftest import TEST_DEVICE_ID

# Shape of one entry of GET /v1/geofence/{deviceId}
API_GEOFENCE = {
    "id": "g1",
    "name": "Home",
    "icon": "house",
    "location": [52.5200, 13.4050],
    "radiusInKm": 0.3,
    "startTime": "07:00",
    "endTime": "18:00",
    "isEnabled": True,
    "deviceId": TEST_DEVICE_ID,
    "deviceTimezone": "+02:00",
}


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


class TestGeofenceModel:
    """Tests for the geofence model."""

    def test_api_format(self) -> None:
        """Test a geofence from the API is read, location is [lat, lng]."""
        geofence = Geofence.model_validate(API_GEOFENCE)

        assert geofence.latitude == 52.5200
        assert geofence.longitude == 13.4050
        assert geofence.radius == 300
        assert geofence.start_time == "07:00"
        assert geofence.end_time == "18:00"
        assert geofence.is_enabled is True

    @pytest.mark.parametrize(
        "location", [[52.52], [52.52, 13.40, 1.0], [99.0, 13.40], [52.52, 200.0]]
    )
    def test_invalid_location(self, location: list[float]) -> None:
        """Test invalid centers are rejected."""
        with pytest.raises(ValidationError):
            Geofence.model_validate({**API_GEOFENCE, "location": location})


class TestGeofenceSensor:
    """Tests for the geofence binary sensor."""

    @staticmethod
    def _sensor(
        device: Device, geofences: list[Geofence], location: LocationInfo | None
    ) -> AnioGeofenceSensor:
        """Create a geofence sensor on a coordinator with one device."""
        from custom_components.anio.coordinator import AnioDataUpdateCoordinator

        coordinator = MagicMock()
        coordinator.data = {
            TEST_DEVICE_ID: AnioDeviceState(
                device=device, location=location, geofences=geofences
            )
        }
        # Use the real calculation of the coordinator
        coordinator.is_device_in_geofence = (
            lambda device_id, geofence_id: AnioDataUpdateCoordinator.is_device_in_geofence(
                coordinator, device_id, geofence_id
            )
        )
        coordinator._is_inside_geofence = (
            lambda *args: AnioDataUpdateCoordinator._is_inside_geofence(
                coordinator, *args
            )
        )
        return AnioGeofenceSensor(coordinator, TEST_DEVICE_ID, geofences[0])

    def test_inside_and_outside(self, mock_device: Device) -> None:
        """Test inside within the radius, outside beyond it."""
        geofence = Geofence.model_validate(API_GEOFENCE)  # radius 300 m

        near = LocationInfo(lat=52.5207, lng=13.4050)  # ~78 m north
        far = LocationInfo(lat=52.5290, lng=13.4050)  # ~1 km north

        assert self._sensor(mock_device, [geofence], near).is_on is True
        assert self._sensor(mock_device, [geofence], far).is_on is False

    def test_attributes_include_time_window(self, mock_device: Device) -> None:
        """Test radius in meters and ANIO's monitoring window are exposed."""
        geofence = Geofence.model_validate(API_GEOFENCE)
        sensor = self._sensor(mock_device, [geofence], None)

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert attrs["radius_meters"] == 300
        assert attrs["active_from"] == "07:00"
        assert attrs["active_until"] == "18:00"
        assert attrs["enabled_in_anio"] is True

    def test_name_follows_rename(self, mock_device: Device) -> None:
        """Test a geofence renamed in the ANIO app shows its new name."""
        original = Geofence.model_validate(API_GEOFENCE)
        sensor = self._sensor(mock_device, [original], None)

        renamed = Geofence.model_validate({**API_GEOFENCE, "name": "Zuhause"})
        sensor.coordinator.data[TEST_DEVICE_ID].geofences = [renamed]

        assert sensor.name == "At Zuhause"
        assert sensor.extra_state_attributes["geofence_name"] == "Zuhause"
