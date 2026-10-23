"""Tests for ANIO API client."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.anio.api import (
    AnioApiClient,
    AnioApiError,
    AnioAuth,
    AnioDeviceNotFoundError,
    AnioMessageTooLongError,
    AnioRateLimitError,
)
from custom_components.anio.api.models import ChatMessage, Device, Geofence


class TestAnioApiClient:
    """Tests for AnioApiClient class."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock aiohttp session."""
        session = MagicMock()
        session.request = MagicMock()
        return session

    @pytest.fixture
    def mock_auth(self) -> AsyncMock:
        """Create a mock auth handler."""
        auth = AsyncMock(spec=AnioAuth)
        auth.ensure_valid_token = AsyncMock(return_value="test_token")
        auth.app_uuid = "test-uuid"
        return auth

    @pytest.fixture
    def client(self, mock_session: MagicMock, mock_auth: AsyncMock) -> AnioApiClient:
        """Create an API client for testing."""
        return AnioApiClient(session=mock_session, auth=mock_auth)

    def _create_mock_response(
        self,
        status: int = 200,
        json_data: dict | list | None = None,
        text: str = "",
        headers: dict | None = None,
    ) -> MagicMock:
        """Create a mock response."""
        response = MagicMock()
        response.status = status
        response.json = AsyncMock(return_value=json_data)
        response.text = AsyncMock(return_value=text)
        response.headers = headers or {}
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=None)
        return response

    @pytest.mark.asyncio
    async def test_get_devices_success(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test getting devices successfully."""
        device_data = [
            {
                "id": "device123",
                "imei": "123456789012345",
                "config": {
                    "generation": "6",
                    "type": "WATCH",
                    "firmwareVersion": "V2.00.12",
                },
                "settings": {
                    "name": "Test Watch",
                    "hexColor": "#FF0000",
                },
            }
        ]

        mock_session.request.return_value = self._create_mock_response(
            json_data=device_data
        )

        devices = await client.get_devices()

        assert len(devices) == 1
        assert isinstance(devices[0], Device)
        assert devices[0].id == "device123"
        assert devices[0].settings.name == "Test Watch"

    @pytest.mark.asyncio
    async def test_get_devices_empty(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test getting devices when none exist."""
        mock_session.request.return_value = self._create_mock_response(json_data=[])

        devices = await client.get_devices()

        assert devices == []

    @pytest.mark.asyncio
    async def test_get_device_success(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test getting a single device."""
        device_data = {
            "id": "device123",
            "imei": "123456789012345",
            "config": {
                "generation": "6",
                "type": "WATCH",
                "firmwareVersion": "V2.00.12",
            },
            "settings": {
                "name": "Test Watch",
                "hexColor": "#FF0000",
            },
        }

        mock_session.request.return_value = self._create_mock_response(
            json_data=device_data
        )

        device = await client.get_device("device123")

        assert isinstance(device, Device)
        assert device.id == "device123"

    @pytest.mark.asyncio
    async def test_get_device_not_found(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test getting a device that doesn't exist."""
        mock_session.request.return_value = self._create_mock_response(status=404)

        with pytest.raises(AnioDeviceNotFoundError):
            await client.get_device("nonexistent")

    @pytest.mark.asyncio
    async def test_find_device(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test requesting device location."""
        mock_session.request.return_value = self._create_mock_response(status=200)

        await client.find_device("device123")

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "POST"
        assert "/v1/device/device123/find" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_power_off_device(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test powering off a device."""
        mock_session.request.return_value = self._create_mock_response(status=200)

        await client.power_off_device("device123")

        call_args = mock_session.request.call_args
        assert call_args[0][0] == "POST"
        assert "/v1/device/device123/poweroff" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_send_text_message_success(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test sending a text message."""
        message_data = {
            "id": "msg123",
            "deviceId": "device123",
            "text": "Hello!",
            "type": "TEXT",
            "sender": "APP",
            "isReceived": False,
            "isRead": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        mock_session.request.return_value = self._create_mock_response(
            status=201, json_data=message_data
        )

        message = await client.send_text_message("device123", "Hello!")

        assert isinstance(message, ChatMessage)
        assert message.text == "Hello!"
        assert message.type == "TEXT"

    @pytest.mark.asyncio
    async def test_send_text_message_too_long(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test sending a message that's too long."""
        long_message = "x" * 100  # Exceeds 95 character limit

        with pytest.raises(AnioMessageTooLongError) as exc_info:
            await client.send_text_message("device123", long_message, max_length=95)

        assert exc_info.value.length == 100
        assert exc_info.value.max_length == 95

    @pytest.mark.asyncio
    async def test_send_text_message_with_username(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test sending a message with username."""
        message_data = {
            "id": "msg123",
            "deviceId": "device123",
            "text": "Hello!",
            "username": "Mom",
            "type": "TEXT",
            "sender": "APP",
            "isReceived": False,
            "isRead": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        mock_session.request.return_value = self._create_mock_response(
            status=201, json_data=message_data
        )

        await client.send_text_message("device123", "Hello!", username="Mom")

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["json"]["username"] == "Mom"

    @pytest.mark.asyncio
    async def test_send_emoji_message_success(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test sending an emoji message."""
        message_data = {
            "id": "msg123",
            "deviceId": "device123",
            "text": "E01",
            "type": "EMOJI",
            "sender": "APP",
            "isReceived": False,
            "isRead": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        mock_session.request.return_value = self._create_mock_response(
            status=201, json_data=message_data
        )

        message = await client.send_emoji_message("device123", "E01")

        assert isinstance(message, ChatMessage)
        assert message.type == "EMOJI"

    @pytest.mark.asyncio
    async def test_send_emoji_message_invalid_code(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test sending an invalid emoji code."""
        with pytest.raises(AnioApiError, match="Invalid emoji code"):
            await client.send_emoji_message("device123", "E99")

    @pytest.mark.asyncio
    async def test_get_geofences_success(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test getting the geofences of a device (API format)."""
        geofence_data = [
            {
                "id": "geo123",
                "name": "Home",
                "icon": "house",
                "location": [52.5200, 13.4050],
                "radiusInKm": 0.3,
                "startTime": "07:00",
                "endTime": "18:00",
                "isEnabled": True,
                "deviceId": "device123",
                "deviceTimezone": "+02:00",
            }
        ]

        mock_session.request.return_value = self._create_mock_response(
            json_data=geofence_data
        )

        geofences = await client.get_geofences("device123")

        method, url = mock_session.request.call_args.args[:2]
        assert method == "GET"
        assert url.endswith("/v1/geofence/device123")
        assert len(geofences) == 1
        assert isinstance(geofences[0], Geofence)
        assert geofences[0].name == "Home"
        assert geofences[0].latitude == 52.5200
        assert geofences[0].longitude == 13.4050
        assert geofences[0].radius == 300
        assert geofences[0].start_time == "07:00"
        assert geofences[0].is_enabled is True

    @pytest.mark.asyncio
    async def test_rate_limit_handling(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test rate limit handling with exponential backoff."""
        # First call returns 429, second call succeeds
        rate_limit_response = self._create_mock_response(
            status=429, headers={"Retry-After": "1"}
        )
        success_response = self._create_mock_response(json_data=[])

        mock_session.request.side_effect = [rate_limit_response, success_response]

        # This should succeed after retry
        devices = await client.get_devices()

        assert devices == []
        assert mock_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_max_retries(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test rate limit max retries exceeded."""
        rate_limit_response = self._create_mock_response(
            status=429, headers={"Retry-After": "1"}
        )

        # Always return 429
        mock_session.request.return_value = rate_limit_response

        with pytest.raises(AnioRateLimitError, match="Max retries exceeded"):
            await client.get_devices()

    @pytest.mark.asyncio
    async def test_api_error(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test API error handling."""
        mock_session.request.return_value = self._create_mock_response(
            status=500, text="Internal Server Error"
        )

        with pytest.raises(AnioApiError):
            await client.get_devices()

    @pytest.mark.asyncio
    async def test_get_activity(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test getting activity feed."""
        activity_data = [
            {
                "id": "act123",
                "deviceId": "device123",
                "type": "MESSAGE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

        mock_session.request.return_value = self._create_mock_response(
            json_data=activity_data
        )

        activity = await client.get_activity()

        assert len(activity) == 1
        assert activity[0].type == "MESSAGE"


    @staticmethod
    def _device(device_id: str, **settings: str) -> dict:
        """Create device data as returned by /v1/device/list."""
        return {
            "id": device_id,
            "imei": "123456789012345",
            "config": {"generation": "6", "type": "WATCH", "firmwareVersion": "V2"},
            "settings": {"name": "Test Watch", "hexColor": "#FF0000", **settings},
        }

    @pytest.mark.asyncio
    async def test_get_devices_accepts_unknown_values(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test new values in fields the integration doesn't use are accepted."""
        device = self._device("device123", gender="DIVERSE")
        device["config"]["type"] = "TRACKER"
        mock_session.request.return_value = self._create_mock_response(
            json_data=[device]
        )

        devices = await client.get_devices()

        assert [d.id for d in devices] == ["device123"]
        assert devices[0].settings.gender == "DIVERSE"
        assert devices[0].config.type == "TRACKER"

    @pytest.mark.asyncio
    async def test_get_devices_skips_unreadable_device(
        self,
        client: AnioApiClient,
        mock_session: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test one unreadable device doesn't hide the others."""
        broken = {"id": "broken", "imei": "1", "config": {"generation": "6"}}
        mock_session.request.return_value = self._create_mock_response(
            json_data=[self._device("device123"), broken]
        )

        devices = await client.get_devices()

        assert [d.id for d in devices] == ["device123"]
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
        assert "Skipping a device" in warnings[0].getMessage()

        # The same problem is only reported once as a warning
        await client.get_devices()
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1

    @pytest.mark.asyncio
    async def test_get_geofences_skips_unreadable_geofence(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test one unreadable geofence doesn't stop the update."""
        mock_session.request.return_value = self._create_mock_response(
            json_data=[
                {"id": "g1", "name": "Home", "location": [52.52, 13.40], "radiusInKm": 0.1},
                {"id": "g2", "name": "Broken", "location": [999, 13.40], "radiusInKm": 0.1},
            ]
        )

        geofences = await client.get_geofences("device123")

        assert [g.id for g in geofences] == ["g1"]

    @pytest.mark.asyncio
    async def test_get_last_location_unreadable_is_none(
        self, client: AnioApiClient, mock_session: MagicMock
    ) -> None:
        """Test an unreadable location is treated like no location."""
        mock_session.request.return_value = self._create_mock_response(
            json_data={"position": [52.52, 13.40]}
        )

        assert await client.get_last_location("device123") is None


class TestDescribeParseError:
    """Tests for logging parse errors without API data."""

    def test_validation_error_without_input(self) -> None:
        """Test only field names and error types are kept."""
        from pydantic import ValidationError

        from custom_components.anio.api.client import _describe_parse_error

        with pytest.raises(ValidationError) as exc_info:
            ChatMessage.model_validate(
                {
                    "id": "m1",
                    "deviceId": "d1",
                    "text": {"secret": "Secret pickup place"},
                    "type": "STICKER",
                    "sender": "DEVICE",
                    "createdAt": "2026-10-23T10:00:00Z",
                }
            )

        description = _describe_parse_error(exc_info.value)

        assert "text: string_type" in description
        assert "type: literal_error" in description
        assert "Secret" not in description
        assert "STICKER" not in description

    def test_other_errors_only_type_name(self) -> None:
        """Test non-validation errors are reduced to their type name."""
        from custom_components.anio.api.client import _describe_parse_error

        assert _describe_parse_error(KeyError("Secret pickup place")) == "KeyError"
