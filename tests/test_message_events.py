"""Tests for anio_message_received events and the last message from the watch."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.anio.api.models import ChatMessage
from custom_components.anio.coordinator import AnioDataUpdateCoordinator

from .conftest import TEST_DEVICE_ID, TEST_DEVICE_NAME

START = datetime(2026, 10, 23, 15, 0, tzinfo=UTC)


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


def chat(
    message_id: str,
    sender: str = "DEVICE",
    text: str | None = "Hello!",
    minute: int = 0,
    msg_type: str = "TEXT",
) -> ChatMessage:
    """Create a chat message as returned by GET /v1/chat/{deviceId}."""
    return ChatMessage.model_validate(
        {
            "id": message_id,
            "deviceId": TEST_DEVICE_ID,
            "text": text,
            "type": msg_type,
            "sender": sender,
            "createdAt": (START + timedelta(minutes=minute)).isoformat(),
        }
    )


class TestMessageEvents:
    """Tests for anio_message_received, based on the chat history."""

    @pytest.fixture
    def coordinator(
        self, hass: HomeAssistant, mock_api_client: AsyncMock
    ) -> AnioDataUpdateCoordinator:
        """Create a coordinator without the HA frame helper."""
        with patch("homeassistant.helpers.frame.report_usage"):
            return AnioDataUpdateCoordinator(
                hass=hass,
                client=mock_api_client,
                scan_interval=300,
            )

    def _fire(
        self, coordinator: AnioDataUpdateCoordinator, messages: list[ChatMessage]
    ) -> None:
        coordinator._fire_message_events(TEST_DEVICE_ID, TEST_DEVICE_NAME, messages)

    def test_existing_messages_not_fired_on_first_poll(
        self, hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test old messages are not reported again after a restart."""
        self._fire(coordinator, [chat("old1"), chat("old2", minute=1)])
        hass.bus.async_fire.assert_not_called()

        # They stay known on the next poll
        self._fire(coordinator, [chat("old1"), chat("old2", minute=1)])
        hass.bus.async_fire.assert_not_called()

    def test_new_message_fires_event(
        self, hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test a new message from the watch fires the event once."""
        self._fire(coordinator, [])
        emoji = chat("new1", text="🙂", msg_type="EMOJI", minute=5)
        self._fire(coordinator, [emoji])
        self._fire(coordinator, [emoji])

        hass.bus.async_fire.assert_called_once()
        event_type, data = hass.bus.async_fire.call_args.args
        assert event_type == "anio_message_received"
        assert data == {
            "device_id": TEST_DEVICE_ID,
            "device_name": TEST_DEVICE_NAME,
            "message_id": "new1",
            "message_type": "EMOJI",
            "content": "🙂",
            "sender": "DEVICE",
            "timestamp": emoji.created_at.isoformat(),
        }

    def test_message_without_text(
        self, hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test a voice message without text fires with empty content."""
        self._fire(coordinator, [])
        self._fire(coordinator, [chat("voice1", text=None, msg_type="VOICE")])

        _, data = hass.bus.async_fire.call_args.args
        assert data["message_type"] == "VOICE"
        assert data["content"] == ""

    def test_seen_ids_trimmed_keeps_newest(
        self, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test trimming the seen IDs drops the oldest, not random ones."""
        self._fire(coordinator, [chat(f"m{i}", minute=i) for i in range(1001)])

        assert len(coordinator._seen_message_ids) == 500
        assert "m1000" in coordinator._seen_message_ids
        assert "m0" not in coordinator._seen_message_ids

    def test_message_text_not_logged(
        self,
        hass: HomeAssistant,
        coordinator: AnioDataUpdateCoordinator,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the message content never ends up in the debug log."""
        caplog.set_level(logging.DEBUG, logger="custom_components.anio")
        self._fire(coordinator, [])
        self._fire(coordinator, [chat("new1", text="Secret pickup place")])

        hass.bus.async_fire.assert_called_once()
        assert "Fired TEXT message event" in caplog.text
        assert "Secret" not in caplog.text


class TestUpdateWithChatHistory:
    """Tests for the coordinator update with the chat history."""

    @pytest.fixture
    def coordinator(
        self, hass: HomeAssistant, mock_api_client: AsyncMock
    ) -> AnioDataUpdateCoordinator:
        """Create a coordinator without the HA frame helper."""
        with patch("homeassistant.helpers.frame.report_usage"):
            return AnioDataUpdateCoordinator(
                hass=hass,
                client=mock_api_client,
                scan_interval=300,
            )

    @pytest.mark.asyncio
    async def test_last_message_is_newest_from_watch(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test the newest watch message is used; the API sends newest first."""
        mock_api_client.get_chat_history.return_value = [
            chat("app2", sender="APP", minute=30),
            chat("watch2", text="newer", minute=20),
            chat("watch1", text="older", minute=10),
        ]

        data = await coordinator._async_update_data()

        assert data[TEST_DEVICE_ID].last_message is not None
        assert data[TEST_DEVICE_ID].last_message.id == "watch2"

    @pytest.mark.asyncio
    async def test_update_fires_event_for_new_watch_message(
        self,
        hass: HomeAssistant,
        coordinator: AnioDataUpdateCoordinator,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test a message arriving between two polls fires the event."""
        mock_api_client.get_chat_history.return_value = [chat("old", minute=1)]
        await coordinator._async_update_data()
        hass.bus.async_fire.assert_not_called()

        mock_api_client.get_chat_history.return_value = [
            chat("new", minute=2),
            chat("old", minute=1),
        ]
        await coordinator._async_update_data()

        hass.bus.async_fire.assert_called_once()
        assert hass.bus.async_fire.call_args.args[1]["message_id"] == "new"

    @pytest.mark.asyncio
    async def test_activity_feed_not_requested(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test the activity feed (which has no chat messages) isn't polled."""
        await coordinator._async_update_data()

        mock_api_client.get_activity.assert_not_called()
