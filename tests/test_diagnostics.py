"""Tests for the diagnostics download."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.anio.api.models import ChatMessage
from custom_components.anio.const import DOMAIN
from custom_components.anio.diagnostics import async_get_config_entry_diagnostics

from .conftest import (
    TEST_ACCESS_TOKEN,
    TEST_APP_UUID,
    TEST_DEVICE_ID,
    TEST_DEVICE_NAME,
    TEST_EMAIL,
    TEST_REFRESH_TOKEN,
)


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


@pytest.mark.asyncio
async def test_diagnostics_without_personal_data(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_coordinator_data: dict,
) -> None:
    """Test diagnostics keep technical data and drop personal data."""
    state = mock_coordinator_data[TEST_DEVICE_ID]
    state.location.source = "GPS"
    state.last_message = ChatMessage.model_validate(
        {
            "id": "msg1",
            "deviceId": TEST_DEVICE_ID,
            "text": "Secret pickup place",
            "username": "Mama",
            "type": "TEXT",
            "sender": "DEVICE",
            "createdAt": datetime.now(UTC).isoformat(),
        }
    )
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(seconds=300)
    coordinator.last_exception = None
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {"coordinator": coordinator}}

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    dumped = json.dumps(result)

    # Personal data and secrets are gone
    for secret in (
        TEST_EMAIL,
        TEST_ACCESS_TOKEN,
        TEST_REFRESH_TOKEN,
        TEST_APP_UUID,
        TEST_DEVICE_ID,
        TEST_DEVICE_NAME,
        state.device.imei,
        state.device.settings.phone_nr,
        "Secret pickup place",
        "Mama",
        str(state.location.latitude),
        str(state.location.longitude),
        str(state.geofences[0].latitude),
    ):
        assert secret not in dumped, secret

    # Technical data useful for bug reports is kept
    device = result["devices"]["device_1"]
    assert device["device"]["config"]["firmware_version"] == (
        state.device.config.firmware_version
    )
    assert device["location"]["source"] == "GPS"
    assert device["location"]["accuracy"] == state.location.accuracy
    assert device["last_message"]["type"] == "TEXT"
    assert device["last_message"]["sender"] == "DEVICE"
    assert len(device["geofences"]) == 1
    assert result["coordinator"]["update_interval_seconds"] == 300
    assert result["entry"]["options"] == dict(mock_config_entry.options)
