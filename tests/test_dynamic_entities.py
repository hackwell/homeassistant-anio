"""Watches and geofences added later get entities without a reload."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.anio import async_remove_config_entry_device
from custom_components.anio.api.models import AnioDeviceState, Geofence
from custom_components.anio.binary_sensor import (
    AnioGeofenceSensor,
    AnioOnlineSensor,
)
from custom_components.anio.binary_sensor import (
    async_setup_entry as binary_sensor_setup,
)
from custom_components.anio.const import DOMAIN
from custom_components.anio.sensor import AnioBatterySensor
from custom_components.anio.sensor import async_setup_entry as sensor_setup

from .conftest import TEST_DEVICE_ID

SECOND_DEVICE_ID = "second0001"


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


def geofence(geofence_id: str, name: str) -> Geofence:
    """Create a geofence."""
    return Geofence(
        id=geofence_id, name=name, location=[52.52, 13.405], radiusInKm=0.1
    )


class Platform:
    """Collects added entities and the coordinator listeners of a platform."""

    def __init__(
        self, hass: HomeAssistant, entry: MagicMock, data: dict
    ) -> None:
        self.coordinator = MagicMock()
        self.coordinator.data = data
        self.coordinator.last_update_success = True
        self.listeners: list = []
        self.coordinator.async_add_listener = lambda listener: (
            self.listeners.append(listener) or MagicMock()
        )
        hass.data[DOMAIN] = {
            entry.entry_id: {"coordinator": self.coordinator, "client": AsyncMock()}
        }
        self.added: list = []

    def add_entities(self, entities: list, update: bool = False) -> None:
        self.added.extend(entities)

    def update(self) -> None:
        """Simulate a coordinator update."""
        for listener in self.listeners:
            listener()


@pytest.mark.asyncio
async def test_new_watch_gets_entities(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_coordinator_data: dict,
    mock_device_state: AnioDeviceState,
) -> None:
    """Test a watch added to the account later gets its sensors."""
    platform = Platform(hass, mock_config_entry, mock_coordinator_data)
    await sensor_setup(hass, mock_config_entry, platform.add_entities)
    assert {e._device_id for e in platform.added} == {TEST_DEVICE_ID}

    first_count = len(platform.added)
    platform.update()  # nothing new
    assert len(platform.added) == first_count

    platform.coordinator.data[SECOND_DEVICE_ID] = mock_device_state
    platform.update()

    new = platform.added[first_count:]
    assert {e._device_id for e in new} == {SECOND_DEVICE_ID}
    assert any(isinstance(e, AnioBatterySensor) for e in new)


@pytest.mark.asyncio
async def test_new_geofence_gets_sensor(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_coordinator_data: dict,
) -> None:
    """Test a geofence added in the ANIO app later gets a sensor."""
    state = mock_coordinator_data[TEST_DEVICE_ID]
    state.geofences = [geofence("home", "Home")]
    platform = Platform(hass, mock_config_entry, mock_coordinator_data)
    await binary_sensor_setup(hass, mock_config_entry, platform.add_entities)

    assert sum(isinstance(e, AnioOnlineSensor) for e in platform.added) == 1
    assert [e._geofence.id for e in platform.added if isinstance(e, AnioGeofenceSensor)] == ["home"]

    state.geofences = [geofence("home", "Home"), geofence("school", "School")]
    platform.update()
    platform.update()  # added only once

    geofence_sensors = [e for e in platform.added if isinstance(e, AnioGeofenceSensor)]
    assert [e._geofence.id for e in geofence_sensors] == ["home", "school"]


def test_deleted_geofence_becomes_unavailable(mock_coordinator_data: dict) -> None:
    """Test a geofence deleted in the app makes its sensor unavailable."""
    state = mock_coordinator_data[TEST_DEVICE_ID]
    home = geofence("home", "Home")
    state.geofences = [home]
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    coordinator.last_update_success = True
    sensor = AnioGeofenceSensor(coordinator, TEST_DEVICE_ID, home)
    assert sensor.available is True

    state.geofences = []

    assert sensor.available is False


@pytest.mark.asyncio
async def test_remove_device_only_when_gone(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_coordinator_data: dict,
) -> None:
    """Test a watch can be removed in HA only once it left the account."""
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {"coordinator": coordinator}}

    current = MagicMock(identifiers={(DOMAIN, TEST_DEVICE_ID)})
    gone = MagicMock(identifiers={(DOMAIN, "removed123")})

    assert await async_remove_config_entry_device(hass, mock_config_entry, current) is False
    assert await async_remove_config_entry_device(hass, mock_config_entry, gone) is True
