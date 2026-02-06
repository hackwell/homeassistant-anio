"""Integration tests for ANIO token lifecycle and data flow.

Covers the 4 critical bug fixes:
- Token persistence across HA restarts (on_token_refresh callback)
- Refresh token rotation (new refresh token from API)
- client-id header included in refresh requests
- 401 → AnioAuthError (not AnioApiError) in API client
"""

from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_EMAIL
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.anio.api import (
    AnioApiClient,
    AnioAuth,
    AnioAuthError,
    Device,
    DeviceConfig,
    DeviceSettings,
    Geofence,
    UserInfo,
)
from custom_components.anio.const import (
    API_URL,
    CLIENT_ID,
    CONF_ACCESS_TOKEN,
    CONF_APP_UUID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from custom_components.anio.coordinator import AnioDataUpdateCoordinator

from .conftest import (
    TEST_ACCESS_TOKEN,
    TEST_APP_UUID,
    TEST_DEVICE_ID,
    TEST_DEVICE_NAME,
    TEST_EMAIL,
    TEST_REFRESH_TOKEN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(exp: int) -> str:
    """Build a minimal JWT with the given exp timestamp."""
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "user123", "exp": exp}).encode()
    ).rstrip(b"=").decode()
    signature = "fakesig"
    return f"{header}.{payload}.{signature}"


def _expired_jwt() -> str:
    """Return a JWT that expired 1 hour ago."""
    return _make_jwt(int(time.time()) - 3600)


def _valid_jwt() -> str:
    """Return a JWT valid for 1 hour."""
    return _make_jwt(int(time.time()) + 3600)


class _MockResponse:
    """Async-context-manager mock for aiohttp responses."""

    def __init__(
        self,
        status: int = 200,
        json_data: dict | list | None = None,
        text: str = "",
    ) -> None:
        self.status = status
        self._json_data = json_data
        self._text = text
        self.headers: dict[str, str] = {}

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# 1. Token Refresh Persistence
# ---------------------------------------------------------------------------

class TestTokenRefreshPersistence:
    """Verify on_token_refresh callback is invoked with new tokens."""

    @pytest.mark.asyncio
    async def test_ensure_valid_token_triggers_callback(self) -> None:
        """Expired JWT triggers refresh, callback receives new tokens."""
        new_access = _valid_jwt()
        new_refresh = "new_refresh_token_abc"

        callback = AsyncMock()
        session = MagicMock()
        session.post = MagicMock(
            return_value=_MockResponse(
                200, {"accessToken": new_access, "refreshToken": new_refresh}
            )
        )

        auth = AnioAuth(
            session=session,
            access_token=_expired_jwt(),
            refresh_token=TEST_REFRESH_TOKEN,
            app_uuid=TEST_APP_UUID,
            on_token_refresh=callback,
        )

        result = await auth.ensure_valid_token()

        assert result == new_access
        callback.assert_awaited_once_with(new_access, new_refresh)


# ---------------------------------------------------------------------------
# 2. Token Rotation (new refresh token)
# ---------------------------------------------------------------------------

class TestTokenRotation:
    """Verify that a rotated refresh token is captured."""

    @pytest.mark.asyncio
    async def test_rotated_refresh_token_stored(self) -> None:
        """When API returns a new refreshToken, auth stores it."""
        new_access = _valid_jwt()
        rotated_refresh = "rotated_refresh_xyz"

        callback = AsyncMock()
        session = MagicMock()
        session.post = MagicMock(
            return_value=_MockResponse(
                200, {"accessToken": new_access, "refreshToken": rotated_refresh}
            )
        )

        auth = AnioAuth(
            session=session,
            access_token=_expired_jwt(),
            refresh_token="old_refresh",
            app_uuid=TEST_APP_UUID,
            on_token_refresh=callback,
        )

        await auth.refresh()

        assert auth.refresh_token == rotated_refresh
        assert auth.access_token == new_access
        # Callback must receive the rotated refresh
        callback.assert_awaited_once_with(new_access, rotated_refresh)

    @pytest.mark.asyncio
    async def test_refresh_without_new_refresh_keeps_old(self) -> None:
        """When API omits refreshToken, the old one is preserved."""
        new_access = _valid_jwt()

        session = MagicMock()
        session.post = MagicMock(
            return_value=_MockResponse(200, {"accessToken": new_access})
        )

        auth = AnioAuth(
            session=session,
            access_token=_expired_jwt(),
            refresh_token="keep_this_refresh",
            app_uuid=TEST_APP_UUID,
        )

        await auth.refresh()

        assert auth.refresh_token == "keep_this_refresh"
        assert auth.access_token == new_access


# ---------------------------------------------------------------------------
# 3. client-id Header in Refresh
# ---------------------------------------------------------------------------

class TestClientIdHeader:
    """Verify client-id header is sent on refresh requests."""

    @pytest.mark.asyncio
    async def test_refresh_sends_client_id(self) -> None:
        """POST to refresh endpoint must include client-id header."""
        new_access = _valid_jwt()

        session = MagicMock()
        session.post = MagicMock(
            return_value=_MockResponse(200, {"accessToken": new_access})
        )

        auth = AnioAuth(
            session=session,
            access_token=_expired_jwt(),
            refresh_token=TEST_REFRESH_TOKEN,
            app_uuid=TEST_APP_UUID,
        )

        await auth.refresh()

        session.post.assert_called_once()
        call_kwargs = session.post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert headers.get("client-id") == CLIENT_ID


# ---------------------------------------------------------------------------
# 4. 401 → AnioAuthError in API Client
# ---------------------------------------------------------------------------

class TestApiClient401:
    """Verify 401 raises AnioAuthError (not AnioApiError)."""

    @pytest.mark.asyncio
    async def test_get_devices_401_raises_auth_error(self) -> None:
        """A 401 from the server must surface as AnioAuthError."""
        session = MagicMock()
        session.request = MagicMock(
            return_value=_MockResponse(401, text="Unauthorized")
        )

        auth_mock = AsyncMock(spec=AnioAuth)
        auth_mock.ensure_valid_token = AsyncMock(return_value=TEST_ACCESS_TOKEN)
        auth_mock.app_uuid = TEST_APP_UUID

        client = AnioApiClient(session=session, auth=auth_mock)

        with pytest.raises(AnioAuthError):
            await client.get_devices()


# ---------------------------------------------------------------------------
# 5. 401 → ConfigEntryAuthFailed in Coordinator
# ---------------------------------------------------------------------------

class TestCoordinatorAuthFlow:
    """Verify coordinator translates AnioAuthError → ConfigEntryAuthFailed."""

    @pytest.mark.asyncio
    @patch("homeassistant.helpers.frame.report_usage")
    async def test_auth_error_becomes_config_entry_auth_failed(
        self, _report_usage: MagicMock, hass: MagicMock
    ) -> None:
        """AnioAuthError from client must become ConfigEntryAuthFailed."""
        mock_client = AsyncMock(spec=AnioApiClient)
        mock_client.get_devices = AsyncMock(
            side_effect=AnioAuthError("Access token rejected by server")
        )

        coordinator = AnioDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# 6. Full Data Flow: API → Coordinator → State
# ---------------------------------------------------------------------------

class TestFullDataFlow:
    """End-to-end: mock API endpoints and verify coordinator state."""

    @pytest.fixture
    def mock_device_raw(self) -> dict:
        """Raw device dict as would be returned by the API."""
        return {
            "id": TEST_DEVICE_ID,
            "imei": "123456789012345",
            "config": {
                "generation": "6",
                "type": "WATCH",
                "firmwareVersion": "ANIO6_Kids_V2.00.12.B",
                "maxChatMessageLength": 95,
                "maxPhonebookEntries": 20,
                "maxGeofences": 5,
                "hasTextChat": True,
                "hasVoiceChat": True,
                "hasEmojis": True,
                "hasStepCounter": True,
                "hasLocatingSwitch": True,
            },
            "settings": {
                "name": TEST_DEVICE_NAME,
                "hexColor": "#E7451B",
                "phoneNr": "+491234567890",
                "gender": "FEMALE",
                "stepTarget": 10000,
                "stepCount": 5432,
                "battery": 85,
                "isLocatingActive": True,
                "ringProfile": "RING_AND_VIBRATE",
            },
            "user": {"id": "user123", "username": "Parent"},
        }

    @pytest.fixture
    def mock_geofence_raw(self) -> dict:
        return {
            "id": "geofence123",
            "name": "Home",
            "lat": 52.5200,
            "lng": 13.4050,
            "radius": 100,
        }

    @pytest.fixture
    def mock_location_raw(self) -> dict:
        """Raw location dict as returned by /v1/location/{deviceId}/last."""
        now = datetime.now(timezone.utc)
        return {
            "position": [52.5200, 13.4050],
            "batteryLevel": 92,
            "signalStrength": 60,
            "positionDeterminedBy": "GPS",
            "date": (now - timedelta(minutes=2)).isoformat(),
            "lastResponse": now.isoformat(),
            "speed": 0,
            "direction": 0,
            "deviceId": TEST_DEVICE_ID,
        }

    @pytest.mark.asyncio
    @patch("homeassistant.helpers.frame.report_usage")
    async def test_data_flows_from_api_to_state(
        self,
        _report_usage: MagicMock,
        hass: MagicMock,
        mock_device_raw: dict,
        mock_geofence_raw: dict,
        mock_location_raw: dict,
    ) -> None:
        """Verify device state is populated with battery, location, name, online, geofences."""
        from custom_components.anio.api.models import DeviceLocation

        device = Device.model_validate(mock_device_raw)
        geofence = Geofence.model_validate(mock_geofence_raw)
        last_location = DeviceLocation.model_validate(mock_location_raw)

        mock_client = AsyncMock(spec=AnioApiClient)
        mock_client.get_devices = AsyncMock(return_value=[device])
        mock_client.get_geofences = AsyncMock(return_value=[geofence])
        mock_client.get_activity = AsyncMock(return_value=[])
        mock_client.get_last_location = AsyncMock(return_value=last_location)
        mock_client.get_chat_history = AsyncMock(return_value=[])
        mock_client.get_alarms = AsyncMock(return_value=[])
        mock_client.get_silence_times = AsyncMock(return_value=[])
        mock_client.get_tracking_mode = AsyncMock(return_value=None)

        coordinator = AnioDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
        )

        data = await coordinator._async_update_data()

        assert TEST_DEVICE_ID in data
        state = data[TEST_DEVICE_ID]

        # Verify key device attributes
        assert state.name == TEST_DEVICE_NAME
        assert state.battery_level == 92
        # Location from /v1/location endpoint
        assert state.location is not None
        assert state.location.latitude == 52.5200
        assert state.location.longitude == 13.4050
        # Has lastResponse → online
        assert state.is_online is True
        assert state.signal_strength == 60
        # Geofences are present
        assert len(coordinator.geofences) == 1
        assert coordinator.geofences[0].name == "Home"


# ---------------------------------------------------------------------------
# 7. Setup Wires Token Callback
# ---------------------------------------------------------------------------

class TestSetupWiresCallback:
    """Verify async_setup_entry passes on_token_refresh that persists tokens."""

    @pytest.mark.asyncio
    async def test_setup_entry_wires_token_callback(self) -> None:
        """on_token_refresh callback calls async_update_entry on config entry."""
        from homeassistant.core import HomeAssistant

        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.data = {
            CONF_EMAIL: TEST_EMAIL,
            CONF_ACCESS_TOKEN: TEST_ACCESS_TOKEN,
            CONF_REFRESH_TOKEN: TEST_REFRESH_TOKEN,
            CONF_APP_UUID: TEST_APP_UUID,
        }
        entry.options = {}
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        entry.async_on_unload = MagicMock()

        captured_callback = None

        def capture_auth_init(*args, **kwargs):
            nonlocal captured_callback
            captured_callback = kwargs.get("on_token_refresh")
            auth_instance = MagicMock(spec=AnioAuth)
            auth_instance.app_uuid = TEST_APP_UUID
            auth_instance.ensure_valid_token = AsyncMock(return_value=TEST_ACCESS_TOKEN)
            return auth_instance

        with (
            patch(
                "custom_components.anio.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.anio.AnioAuth",
                side_effect=capture_auth_init,
            ),
            patch(
                "custom_components.anio.AnioApiClient",
                return_value=AsyncMock(spec=AnioApiClient),
            ),
            patch(
                "custom_components.anio.AnioDataUpdateCoordinator",
            ) as mock_coord_cls,
        ):
            mock_coord = AsyncMock()
            mock_coord.data = {}
            mock_coord_cls.return_value = mock_coord

            from custom_components.anio import async_setup_entry

            result = await async_setup_entry(hass, entry)
            assert result is True

        # Callback was wired
        assert captured_callback is not None

        # Invoke the callback and verify it persists tokens
        await captured_callback("new_access", "new_refresh")

        hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = hass.config_entries.async_update_entry.call_args
        updated_data = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data", {})
        assert updated_data[CONF_ACCESS_TOKEN] == "new_access"
        assert updated_data[CONF_REFRESH_TOKEN] == "new_refresh"


# ---------------------------------------------------------------------------
# 8. Expired Token → Refresh → Successful API Call
# ---------------------------------------------------------------------------

class TestExpiredTokenRefreshChain:
    """Full chain: expired token triggers refresh, then API call succeeds."""

    @pytest.mark.asyncio
    async def test_expired_token_refreshes_then_fetches(self) -> None:
        """AnioAuth refreshes expired JWT, then AnioApiClient fetches devices."""
        expired = _expired_jwt()
        new_access = _valid_jwt()

        # Track call order
        call_order: list[str] = []

        def mock_post(*args, **kwargs):
            call_order.append("refresh")
            return _MockResponse(
                200, {"accessToken": new_access, "refreshToken": "fresh_refresh"}
            )

        device_data = [
            {
                "id": TEST_DEVICE_ID,
                "imei": "123456789012345",
                "config": {
                    "generation": "6",
                    "type": "WATCH",
                    "firmwareVersion": "FW1",
                    "maxChatMessageLength": 95,
                    "maxPhonebookEntries": 20,
                    "maxGeofences": 5,
                    "hasTextChat": True,
                    "hasVoiceChat": True,
                    "hasEmojis": True,
                    "hasStepCounter": True,
                    "hasLocatingSwitch": True,
                },
                "settings": {
                    "name": TEST_DEVICE_NAME,
                    "hexColor": "#000000",
                    "battery": 75,
                    "stepTarget": 10000,
                    "stepCount": 100,
                    "isLocatingActive": True,
                    "ringProfile": "RING_AND_VIBRATE",
                },
                "user": {"id": "u1"},
            }
        ]

        def mock_request(*args, **kwargs):
            call_order.append("api_request")
            return _MockResponse(200, device_data)

        session = MagicMock()
        session.post = MagicMock(side_effect=mock_post)
        session.request = MagicMock(side_effect=mock_request)

        auth = AnioAuth(
            session=session,
            access_token=expired,
            refresh_token=TEST_REFRESH_TOKEN,
            app_uuid=TEST_APP_UUID,
        )

        client = AnioApiClient(session=session, auth=auth)
        devices = await client.get_devices()

        assert len(devices) == 1
        assert devices[0].id == TEST_DEVICE_ID
        assert devices[0].settings.name == TEST_DEVICE_NAME
        # Refresh happened before the API request
        assert call_order == ["refresh", "api_request"]
        # Auth now holds the new tokens
        assert auth.access_token == new_access
        assert auth.refresh_token == "fresh_refresh"
