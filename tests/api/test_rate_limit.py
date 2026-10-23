"""Rate limiting: Retry-After formats and long pauses."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.anio.api import AnioApiClient, AnioAuth, AnioRateLimitError
from custom_components.anio.api.client import _parse_retry_after


def _response(status: int, headers: dict | None = None) -> MagicMock:
    """Create a mock response."""
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=[])
    response.text = AsyncMock(return_value="")
    response.headers = headers or {}
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    return response


@pytest.fixture
def session() -> MagicMock:
    """Create a mock aiohttp session."""
    return MagicMock()


@pytest.fixture
def client(session: MagicMock) -> AnioApiClient:
    """Create an API client for testing."""
    auth = AsyncMock(spec=AnioAuth)
    auth.ensure_valid_token = AsyncMock(return_value="test_token")
    auth.app_uuid = "test-uuid"
    return AnioApiClient(session=session, auth=auth)


def test_parse_retry_after_seconds() -> None:
    """Test a number of seconds."""
    assert _parse_retry_after("5") == 5


def test_parse_retry_after_http_date() -> None:
    """Test an HTTP date instead of seconds."""
    retry_at = datetime.now(UTC) + timedelta(seconds=120)

    seconds = _parse_retry_after(format_datetime(retry_at, usegmt=True))

    assert seconds is not None
    assert 115 <= seconds <= 120


@pytest.mark.parametrize(
    "value", [None, "", "soon"], ids=["missing", "empty", "unreadable"]
)
def test_parse_retry_after_unusable(value: str | None) -> None:
    """Test values that fall back to exponential backoff."""
    assert _parse_retry_after(value) is None


def test_parse_retry_after_past_date() -> None:
    """Test a date in the past means no wait."""
    past = datetime.now(UTC) - timedelta(minutes=5)
    assert _parse_retry_after(format_datetime(past, usegmt=True)) == 0


@pytest.mark.asyncio
async def test_waits_after_releasing_the_response(
    client: AnioApiClient, session: MagicMock
) -> None:
    """Test the retry waits only after the 429 response was closed."""
    events: list[str] = []
    limited = _response(429, {"Retry-After": "2"})
    limited.__aexit__ = AsyncMock(side_effect=lambda *_: events.append("released"))
    session.request.side_effect = [limited, _response(200)]

    async def fake_sleep(seconds: float) -> None:
        events.append(f"sleep {seconds}")

    with patch("custom_components.anio.api.client.asyncio.sleep", fake_sleep):
        assert await client.get_devices() == []

    assert events == ["released", "sleep 2"]
    assert session.request.call_count == 2


@pytest.mark.asyncio
async def test_long_retry_after_pauses_requests(
    client: AnioApiClient, session: MagicMock
) -> None:
    """Test a long Retry-After fails fast and blocks requests until then."""
    session.request.return_value = _response(429, {"Retry-After": "3600"})
    sleep = AsyncMock()

    with patch("custom_components.anio.api.client.asyncio.sleep", sleep):
        with pytest.raises(AnioRateLimitError) as first:
            await client.get_devices()
        with pytest.raises(AnioRateLimitError) as second:
            await client.get_devices()

    sleep.assert_not_awaited()
    assert first.value.retry_after == 3600
    assert second.value.retry_after is not None
    assert 3590 <= second.value.retry_after <= 3600
    # The second call didn't reach the API
    assert session.request.call_count == 1


@pytest.mark.asyncio
async def test_requests_resume_after_the_pause(
    client: AnioApiClient, session: MagicMock
) -> None:
    """Test requests are sent again once the pause is over."""
    client._rate_limited_until = datetime.now(UTC) - timedelta(seconds=1)
    session.request.return_value = _response(200)

    assert await client.get_devices() == []
    assert client._rate_limited_until is None
