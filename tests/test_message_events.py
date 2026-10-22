"""Tests for anio_message_received events."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.anio.api.models import ActivityItem
from custom_components.anio.coordinator import AnioDataUpdateCoordinator

from .conftest import TEST_DEVICE_ID


class TestMessageEvents:
    """Tests for anio_message_received events."""

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

    @staticmethod
    def _message(
        message_id: str, sender: str = "DEVICE", text: str | None = "Hello!"
    ) -> ActivityItem:
        """Create a message activity item."""
        return ActivityItem(
            id=f"activity_{message_id}",
            deviceId=TEST_DEVICE_ID,
            type="MESSAGE",
            timestamp=datetime.now(timezone.utc),
            data={
                "id": message_id,
                "deviceId": TEST_DEVICE_ID,
                "text": text,
                "type": "TEXT" if text else "EMOJI",
                "sender": sender,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            },
        )

    @pytest.mark.asyncio
    async def test_existing_messages_not_fired_on_first_poll(
        self, hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test old messages are not reported again after a restart."""
        await coordinator._process_messages(
            [self._message("old1", "WATCH"), self._message("old2", "DEVICE")]
        )

        hass.bus.async_fire.assert_not_called()

        # They stay known on the next poll
        await coordinator._process_messages([self._message("old1", "WATCH")])
        hass.bus.async_fire.assert_not_called()

    @pytest.mark.asyncio
    async def test_device_sender_fires_event(
        self, hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test messages with sender DEVICE (as sent by the API) fire the event."""
        await coordinator._process_messages([])
        await coordinator._process_messages([self._message("new1", "DEVICE")])

        hass.bus.async_fire.assert_called_once()
        event_type, data = hass.bus.async_fire.call_args.args
        assert event_type == "anio_message_received"
        assert data["message_id"] == "new1"
        assert data["sender"] == "DEVICE"
        assert data["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_app_messages_not_fired(
        self, hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test messages sent from the app are not reported as received."""
        await coordinator._process_messages([])
        await coordinator._process_messages([self._message("own1", "APP")])

        hass.bus.async_fire.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_without_text(
        self, hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test a message without text (emoji/voice) doesn't break the update."""
        await coordinator._process_messages([])
        await coordinator._process_messages(
            [self._message("emoji1", "WATCH", text=None)]
        )

        hass.bus.async_fire.assert_called_once()
        assert "emoji1" in coordinator._seen_message_ids

    @pytest.mark.asyncio
    async def test_seen_ids_trimmed_keeps_newest(
        self, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test trimming the seen IDs drops the oldest, not random ones."""
        await coordinator._process_messages(
            [self._message(f"m{i}") for i in range(1001)]
        )

        assert len(coordinator._seen_message_ids) == 500
        assert "m1000" in coordinator._seen_message_ids
        assert "m0" not in coordinator._seen_message_ids
