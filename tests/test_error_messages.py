"""Actions report readable, translated errors instead of raw API exceptions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.anio.api import (
    AnioApiError,
    AnioAuthError,
    AnioConnectionError,
    AnioInvalidEmojiError,
    AnioMessageTooLongError,
    AnioRateLimitError,
)
from custom_components.anio.entity import translate_api_errors
from custom_components.anio.notify import AnioNotifyEntity
from custom_components.anio.select import AnioRingProfileSelect
from custom_components.anio.switch import AnioSilenceTimeSwitch

from .conftest import TEST_DEVICE_ID

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "anio"
TRANSLATION_FILES = [
    COMPONENT_DIR / "strings.json",
    COMPONENT_DIR / "translations" / "en.json",
    COMPONENT_DIR / "translations" / "de.json",
]


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


@pytest.mark.parametrize(
    ("error", "expected", "key"),
    [
        (AnioMessageTooLongError(120, 95), ServiceValidationError, "message_too_long"),
        (AnioInvalidEmojiError("E12"), ServiceValidationError, "invalid_emoji"),
        (AnioAuthError(), HomeAssistantError, "auth_failed"),
        (AnioRateLimitError(), HomeAssistantError, "rate_limited"),
        (AnioConnectionError(), HomeAssistantError, "cannot_connect"),
        (AnioApiError("boom", 500), HomeAssistantError, "api_error"),
    ],
)
def test_errors_are_translated(
    error: Exception, expected: type[Exception], key: str
) -> None:
    """Test each API error becomes a translated Home Assistant error."""
    with pytest.raises(expected) as exc_info, translate_api_errors():
        raise error

    assert type(exc_info.value) is expected
    assert exc_info.value.translation_domain == "anio"
    assert exc_info.value.translation_key == key
    assert exc_info.value.__cause__ is error


def test_invalid_emoji_lists_valid_codes() -> None:
    """Test the message for an unknown emoji lists E01-E09."""
    with pytest.raises(ServiceValidationError) as exc_info, translate_api_errors():
        raise AnioInvalidEmojiError("E12")

    placeholders = exc_info.value.translation_placeholders
    assert placeholders["code"] == "E12"
    assert placeholders["valid_codes"].startswith("E01, E02")
    assert placeholders["valid_codes"].endswith("E09")


@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.name)
def test_used_error_keys_are_translated(path: Path) -> None:
    """Test every translation_key used for errors exists in each file."""
    source = (COMPONENT_DIR / "entity.py").read_text(encoding="utf-8")
    used = set(re.findall(r'translation_key="([a-z_]+)"', source))
    exceptions = json.loads(path.read_text(encoding="utf-8"))["exceptions"]

    assert used <= set(exceptions), used - set(exceptions)


@pytest.mark.asyncio
async def test_notify_uses_the_watch_max_length(
    mock_coordinator_data: dict, mock_api_client: AsyncMock
) -> None:
    """Test the text limit comes from the watch's config."""
    mock_coordinator_data[TEST_DEVICE_ID].device.config.max_chat_message_length = 50
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    entity = AnioNotifyEntity(coordinator, mock_api_client, TEST_DEVICE_ID)

    await entity.async_send_message("Hello!")

    assert mock_api_client.send_text_message.call_args.kwargs["max_length"] == 50


@pytest.mark.asyncio
async def test_select_and_switch_errors_are_translated(
    mock_coordinator_data: dict, mock_api_client: AsyncMock
) -> None:
    """Test settings actions also raise translated errors."""
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    coordinator.async_request_refresh = AsyncMock()
    mock_api_client.update_device_settings.side_effect = AnioConnectionError()
    mock_api_client.enable_silence_times.side_effect = AnioRateLimitError()

    select = AnioRingProfileSelect(coordinator, mock_api_client, TEST_DEVICE_ID)
    switch = AnioSilenceTimeSwitch(coordinator, mock_api_client, TEST_DEVICE_ID)

    with pytest.raises(HomeAssistantError) as select_error:
        await select.async_select_option("SILENT")
    with pytest.raises(HomeAssistantError) as switch_error:
        await switch.async_turn_on()

    assert select_error.value.translation_key == "cannot_connect"
    assert switch_error.value.translation_key == "rate_limited"
