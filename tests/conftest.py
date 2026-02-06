"""Fixtures for ANIO integration tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant

# Try to import from pytest-homeassistant-custom-component, fall back to mock
try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    MockConfigEntry = MagicMock


@pytest.fixture
def hass() -> HomeAssistant:
    """Create a Home Assistant instance for testing."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.options = MagicMock()
    hass.config_entries.options.async_init = AsyncMock()
    hass.config_entries.options.async_configure = AsyncMock()
    hass.config_entries.flow = MagicMock()
    hass.config_entries.flow.async_init = AsyncMock()
    hass.config_entries.flow.async_configure = AsyncMock()
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.bus.async_listen = MagicMock()
    return hass

from custom_components.anio.api import (
    AlarmClock,
    AnioApiClient,
    AnioAuth,
    AnioDeviceState,
    ChatMessage,
    Device,
    DeviceConfig,
    DeviceSettings,
    Geofence,
    LocationInfo,
    SilenceTime,
    UserInfo,
)
from custom_components.anio.const import (
    CONF_ACCESS_TOKEN,
    CONF_APP_UUID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

# Test data
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"
TEST_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxOTk5OTk5OTk5fQ.test"
TEST_REFRESH_TOKEN = "refresh_token_12345"
TEST_APP_UUID = "12345678-1234-1234-1234-123456789012"
TEST_DEVICE_ID = "4645a84ad7"
TEST_DEVICE_NAME = "Marla"


@pytest.fixture
def mock_device_config() -> DeviceConfig:
    """Create a mock device config."""
    return DeviceConfig(
        generation="6",
        type="WATCH",
        firmwareVersion="ANIO6_Kids_V2.00.12.B",
        maxChatMessageLength=95,
        maxPhonebookEntries=20,
        maxGeofences=5,
        hasTextChat=True,
        hasVoiceChat=True,
        hasEmojis=True,
        hasStepCounter=True,
        hasLocatingSwitch=True,
    )


@pytest.fixture
def mock_device_settings() -> DeviceSettings:
    """Create mock device settings."""
    return DeviceSettings(
        name=TEST_DEVICE_NAME,
        hexColor="#E7451B",
        phoneNr="+491234567890",
        gender="FEMALE",
        stepTarget=10000,
        stepCount=5432,
        battery=85,
        isLocatingActive=True,
        ringProfile="RING_AND_VIBRATE",
    )


@pytest.fixture
def mock_device(mock_device_config: DeviceConfig, mock_device_settings: DeviceSettings) -> Device:
    """Create a mock device."""
    return Device(
        id=TEST_DEVICE_ID,
        imei="123456789012345",
        config=mock_device_config,
        settings=mock_device_settings,
        user=UserInfo(id="user123", username="Parent"),
    )


@pytest.fixture
def mock_location() -> LocationInfo:
    """Create mock location info."""
    return LocationInfo(
        lat=52.5200,
        lng=13.4050,
        accuracy=10,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_geofence() -> Geofence:
    """Create a mock geofence."""
    return Geofence(
        id="geofence123",
        name="Home",
        lat=52.5200,
        lng=13.4050,
        radius=100,
    )


@pytest.fixture
def mock_chat_message() -> ChatMessage:
    """Create a mock chat message from the watch."""
    return ChatMessage(
        id="msg123",
        deviceId=TEST_DEVICE_ID,
        text="Hi Mom!",
        type="TEXT",
        sender="WATCH",
        isReceived=True,
        isRead=False,
        createdAt=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_alarm() -> AlarmClock:
    """Create a mock alarm clock."""
    return AlarmClock(
        id="alarm123",
        deviceId=TEST_DEVICE_ID,
        time="07:30",
        days=["MON", "TUE", "WED", "THU", "FRI"],
        enabled=True,
        label="School",
    )


@pytest.fixture
def mock_silence_time() -> SilenceTime:
    """Create a mock silence time."""
    return SilenceTime(
        id="silence123",
        deviceId=TEST_DEVICE_ID,
        startTime="22:00",
        endTime="07:00",
        days=["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
        enabled=True,
    )


@pytest.fixture
def mock_device_state(
    mock_device: Device,
    mock_location: LocationInfo,
    mock_geofence: Geofence,
    mock_chat_message: ChatMessage,
    mock_alarm: AlarmClock,
    mock_silence_time: SilenceTime,
) -> AnioDeviceState:
    """Create mock device state."""
    return AnioDeviceState(
        device=mock_device,
        location=mock_location,
        geofences=[mock_geofence],
        last_seen=datetime.now(timezone.utc),
        is_online=True,
        battery_level_value=85,
        signal_strength=60,
        last_message=mock_chat_message,
        alarms=[mock_alarm],
        silence_times=[mock_silence_time],
        tracking_mode="NORMAL",
    )


@pytest.fixture
def mock_auth() -> Generator[AsyncMock, None, None]:
    """Create a mock auth handler."""
    auth = AsyncMock(spec=AnioAuth)
    auth.access_token = TEST_ACCESS_TOKEN
    auth.refresh_token = TEST_REFRESH_TOKEN
    auth.app_uuid = TEST_APP_UUID
    auth.is_token_valid = True
    auth.ensure_valid_token = AsyncMock(return_value=TEST_ACCESS_TOKEN)
    auth.login = AsyncMock()
    auth.refresh = AsyncMock(return_value=TEST_ACCESS_TOKEN)
    auth.logout = AsyncMock()
    yield auth


@pytest.fixture
def mock_api_client(
    mock_auth: AsyncMock,
    mock_device: Device,
    mock_geofence: Geofence,
) -> Generator[AsyncMock, None, None]:
    """Create a mock API client."""
    client = AsyncMock(spec=AnioApiClient)
    client.get_devices = AsyncMock(return_value=[mock_device])
    client.get_device = AsyncMock(return_value=mock_device)
    client.get_geofences = AsyncMock(return_value=[mock_geofence])
    client.get_activity = AsyncMock(return_value=[])
    client.get_device_locations = AsyncMock(return_value=[])
    client.get_last_location = AsyncMock(return_value=None)
    client.send_flower = AsyncMock()
    client.get_chat_history = AsyncMock(return_value=[])
    client.find_device = AsyncMock()
    client.power_off_device = AsyncMock()
    client.send_text_message = AsyncMock()
    client.send_emoji_message = AsyncMock()
    client.get_alarms = AsyncMock(return_value=[])
    client.create_alarm = AsyncMock(return_value=None)
    client.delete_alarm = AsyncMock()
    client.get_silence_times = AsyncMock(return_value=[])
    client.enable_silence_times = AsyncMock()
    client.disable_silence_times = AsyncMock()
    client.get_tracking_mode = AsyncMock(return_value=None)
    client.update_device_settings = AsyncMock()
    yield client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.title = TEST_EMAIL
    entry.data = {
        CONF_EMAIL: TEST_EMAIL,
        CONF_ACCESS_TOKEN: TEST_ACCESS_TOKEN,
        CONF_REFRESH_TOKEN: TEST_REFRESH_TOKEN,
        CONF_APP_UUID: TEST_APP_UUID,
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_coordinator_data(mock_device_state: AnioDeviceState) -> dict[str, AnioDeviceState]:
    """Create mock coordinator data."""
    return {TEST_DEVICE_ID: mock_device_state}


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock async_setup_entry."""
    with patch(
        "custom_components.anio.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_unload_entry() -> Generator[AsyncMock, None, None]:
    """Mock async_unload_entry."""
    with patch(
        "custom_components.anio.async_unload_entry",
        return_value=True,
    ) as mock_unload:
        yield mock_unload


def create_mock_response(
    status: int = 200,
    json_data: dict[str, Any] | list[Any] | None = None,
    text: str = "",
) -> MagicMock:
    """Create a mock aiohttp response.

    Args:
        status: HTTP status code.
        json_data: JSON response data.
        text: Text response.

    Returns:
        Mock response object.
    """
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data)
    response.text = AsyncMock(return_value=text)
    response.headers = {}
    return response
