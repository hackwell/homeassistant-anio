"""Tests for ANIO notify platform."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.notify import ATTR_MESSAGE, ATTR_TARGET
from homeassistant.core import HomeAssistant

from custom_components.anio.api import (
    AnioApiError,
    AnioMessageTooLongError,
    ChatMessage,
)
from custom_components.anio.const import DOMAIN, MESSAGE_TYPE_EMOJI, MESSAGE_TYPE_TEXT
from custom_components.anio.notify import (
    AnioNotifyEntity,
    async_setup_entry,
)

from .conftest import TEST_DEVICE_ID, TEST_DEVICE_NAME


class TestAnioNotifyEntity:
    """Tests for AnioNotifyEntity."""

    @pytest.fixture
    def notify_entity(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> AnioNotifyEntity:
        """Create a notify entity for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioNotifyEntity(
            coordinator=coordinator,
            client=mock_api_client,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, notify_entity: AnioNotifyEntity) -> None:
        """Test unique ID format."""
        assert notify_entity.unique_id == f"{TEST_DEVICE_ID}_notify"

    def test_name(self, notify_entity: AnioNotifyEntity) -> None:
        """Test entity name."""
        assert notify_entity.name == f"{TEST_DEVICE_NAME} Message"

    @pytest.mark.asyncio
    async def test_send_text_message_success(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test sending a text message successfully."""
        mock_message = ChatMessage(
            id="msg123",
            device_id=TEST_DEVICE_ID,
            text="Hello!",
            type=MESSAGE_TYPE_TEXT,
            sender="APP",
            is_received=False,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        mock_api_client.send_text_message.return_value = mock_message

        await notify_entity.async_send_message("Hello!")

        mock_api_client.send_text_message.assert_called_once_with(
            TEST_DEVICE_ID,
            "Hello!",
            username=None,
        )

    @pytest.mark.asyncio
    async def test_send_text_message_with_username(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test sending a text message with a custom sender name."""
        mock_message = ChatMessage(
            id="msg123",
            device_id=TEST_DEVICE_ID,
            text="Hello!",
            type=MESSAGE_TYPE_TEXT,
            sender="APP",
            is_received=False,
            is_read=False,
            created_at=datetime.now(timezone.utc),
            username="Mom",
        )
        mock_api_client.send_text_message.return_value = mock_message

        await notify_entity.async_send_message("Hello!", data={"username": "Mom"})

        mock_api_client.send_text_message.assert_called_once_with(
            TEST_DEVICE_ID,
            "Hello!",
            username="Mom",
        )

    @pytest.mark.asyncio
    async def test_send_emoji_message_success(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test sending an emoji message successfully."""
        mock_message = ChatMessage(
            id="msg123",
            device_id=TEST_DEVICE_ID,
            text="E01",
            type=MESSAGE_TYPE_EMOJI,
            sender="APP",
            is_received=False,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        mock_api_client.send_emoji_message.return_value = mock_message

        await notify_entity.async_send_message(
            "E01",
            data={"message_type": "emoji"},
        )

        mock_api_client.send_emoji_message.assert_called_once_with(
            TEST_DEVICE_ID,
            "E01",
        )

    @pytest.mark.asyncio
    async def test_send_message_too_long(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test sending a message that's too long."""
        mock_api_client.send_text_message.side_effect = AnioMessageTooLongError(
            length=100,
            max_length=95,
        )

        with pytest.raises(AnioMessageTooLongError):
            await notify_entity.async_send_message("x" * 100)

    @pytest.mark.asyncio
    async def test_send_message_api_error(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test API error handling."""
        mock_api_client.send_text_message.side_effect = AnioApiError("API Error")

        with pytest.raises(AnioApiError):
            await notify_entity.async_send_message("Hello!")


class TestNotifySetup:
    """Tests for notify platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test notify platform setup."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
                "client": mock_api_client,
            }
        }

        entities = []

        async def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Should create one notify entity per device
        assert len(entities) == 1
        assert isinstance(entities[0], AnioNotifyEntity)

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test notify platform setup with no devices."""
        coordinator = MagicMock()
        coordinator.data = {}

        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
                "client": mock_api_client,
            }
        }

        entities = []

        async def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        assert len(entities) == 0


class TestNotifyServiceValidation:
    """Tests for notify service validation."""

    @pytest.fixture
    def notify_entity(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> AnioNotifyEntity:
        """Create a notify entity for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioNotifyEntity(
            coordinator=coordinator,
            client=mock_api_client,
            device_id=TEST_DEVICE_ID,
        )

    @pytest.mark.asyncio
    async def test_empty_message(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test sending an empty message does nothing."""
        await notify_entity.async_send_message("")

        mock_api_client.send_text_message.assert_not_called()
        mock_api_client.send_emoji_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_whitespace_only_message(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test sending a whitespace-only message does nothing."""
        await notify_entity.async_send_message("   ")

        mock_api_client.send_text_message.assert_not_called()
        mock_api_client.send_emoji_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_emoji_code(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test sending an invalid emoji code."""
        mock_api_client.send_emoji_message.side_effect = AnioApiError(
            "Invalid emoji code"
        )

        with pytest.raises(AnioApiError, match="Invalid emoji code"):
            await notify_entity.async_send_message(
                "E99",
                data={"message_type": "emoji"},
            )

    @pytest.mark.asyncio
    async def test_valid_emoji_codes(
        self,
        notify_entity: AnioNotifyEntity,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test all valid emoji codes E01-E12."""
        mock_message = ChatMessage(
            id="msg123",
            device_id=TEST_DEVICE_ID,
            text="E01",
            type=MESSAGE_TYPE_EMOJI,
            sender="APP",
            is_received=False,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        mock_api_client.send_emoji_message.return_value = mock_message

        for i in range(1, 13):
            emoji_code = f"E{i:02d}"
            await notify_entity.async_send_message(
                emoji_code,
                data={"message_type": "emoji"},
            )

        assert mock_api_client.send_emoji_message.call_count == 12
