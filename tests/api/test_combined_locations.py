"""GET /v1/location/last returns the last location of all watches."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.anio.api import AnioApiClient, AnioAuth

LOCATION = {
    "id": "l1",
    "position": [52.52, 13.405],
    "speed": 0,
    "direction": 0,
    "batteryLevel": 51,
    "positionDeterminedBy": "GPS",
    "signalStrength": 60,
    "date": "2026-10-26T07:27:00.000Z",
    "deviceId": "watch1",
    "trackingMode": "NORMAL",
    "createdAt": "2026-10-26T07:27:00.000Z",
    "updatedAt": "2026-10-26T07:27:00.000Z",
    "lastResponse": "2026-10-26T07:27:00.000Z",
}


def _client(status: int, body: object) -> tuple[AnioApiClient, MagicMock]:
    """Create a client whose request returns the given status and JSON."""
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=body)
    response.text = AsyncMock(return_value="")
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.request.return_value = response
    auth = AsyncMock(spec=AnioAuth)
    auth.ensure_valid_token = AsyncMock(return_value="test_token")
    auth.app_uuid = "test-uuid"
    return AnioApiClient(session=session, auth=auth), session


@pytest.mark.asyncio
async def test_locations_by_device() -> None:
    """Test the list is keyed by device ID; unreadable entries are skipped."""
    client, session = _client(200, [LOCATION, {"deviceId": "broken"}])

    locations = await client.get_last_locations()

    assert locations is not None
    assert list(locations) == ["watch1"]
    assert locations["watch1"].tracking_mode == "NORMAL"
    assert session.request.call_args.args[1].endswith("/v1/location/last")


@pytest.mark.asyncio
async def test_unavailable_returns_none() -> None:
    """Test a missing route means the per-watch requests are used."""
    client, _ = _client(404, {})

    assert await client.get_last_locations() is None
