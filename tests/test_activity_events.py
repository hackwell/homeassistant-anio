"""Tests for anio_activity events (ANIO's own alerts)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.anio.api.models import ActivityItem
from custom_components.anio.coordinator import AnioDataUpdateCoordinator

from .conftest import TEST_DEVICE_ID, TEST_DEVICE_NAME

START = datetime(2026, 10, 23, 15, 0, tzinfo=UTC)


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


@pytest.fixture
def coordinator(
    hass: HomeAssistant, mock_api_client: AsyncMock
) -> AnioDataUpdateCoordinator:
    """Create a coordinator without the HA frame helper."""
    with patch("homeassistant.helpers.frame.report_usage"):
        return AnioDataUpdateCoordinator(
            hass=hass, client=mock_api_client, scan_interval=300
        )


def alert(
    activity_id: str,
    activity_type: str = "GEOFENCE_ENTERED",
    minute: int = 0,
    geofence: dict | None = None,
) -> ActivityItem:
    """Create an alert as returned by GET /v1/activity?deviceId=..."""
    data: dict = {
        "id": activity_id,
        "text": "Kids Watch has arrived at School",
        "type": activity_type,
        "deviceId": TEST_DEVICE_ID,
        "createdAt": (START + timedelta(minutes=minute)).isoformat(),
    }
    if geofence is not None:
        data["geofence"] = geofence
    return ActivityItem.model_validate(data)


SCHOOL = {
    "id": "geo2",
    "name": "School",
    "location": [52.53, 13.41],
    "radiusInKm": 0.3,
    "startTime": "07:00",
    "endTime": "14:00",
    "isEnabled": True,
}


def test_model_from_api() -> None:
    """Test an alert in the API format is read."""
    item = alert("a1", geofence=SCHOOL)

    assert item.type == "GEOFENCE_ENTERED"
    assert item.geofence_id == "geo2"
    assert item.geofence_name == "School"
    assert item.created_at == START


def test_existing_alerts_not_fired_on_first_poll(
    hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
) -> None:
    """Test old alerts are not reported again after a restart."""
    coordinator._fire_activity_events(
        TEST_DEVICE_ID, TEST_DEVICE_NAME, [alert("old1"), alert("old2", minute=1)]
    )
    coordinator._fire_activity_events(
        TEST_DEVICE_ID, TEST_DEVICE_NAME, [alert("old1"), alert("old2", minute=1)]
    )

    hass.bus.async_fire.assert_not_called()


def test_new_geofence_alert_fires_event(
    hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
) -> None:
    """Test a new geofence alert fires anio_activity once."""
    coordinator._fire_activity_events(TEST_DEVICE_ID, TEST_DEVICE_NAME, [])
    item = alert("new1", geofence=SCHOOL, minute=5)
    coordinator._fire_activity_events(TEST_DEVICE_ID, TEST_DEVICE_NAME, [item])
    coordinator._fire_activity_events(TEST_DEVICE_ID, TEST_DEVICE_NAME, [item])

    hass.bus.async_fire.assert_called_once()
    event_type, data = hass.bus.async_fire.call_args.args
    assert event_type == "anio_activity"
    assert data == {
        "device_id": TEST_DEVICE_ID,
        "device_name": TEST_DEVICE_NAME,
        "activity_id": "new1",
        "type": "GEOFENCE_ENTERED",
        "text": "Kids Watch has arrived at School",
        "geofence_id": "geo2",
        "geofence_name": "School",
        "timestamp": item.created_at.isoformat(),
    }


def test_low_battery_alert_without_geofence(
    hass: HomeAssistant, coordinator: AnioDataUpdateCoordinator
) -> None:
    """Test alerts without a geofence fire with empty geofence fields."""
    coordinator._fire_activity_events(TEST_DEVICE_ID, TEST_DEVICE_NAME, [])
    coordinator._fire_activity_events(
        TEST_DEVICE_ID, TEST_DEVICE_NAME, [alert("bat1", "LOW_BATTERY")]
    )

    _, data = hass.bus.async_fire.call_args.args
    assert data["type"] == "LOW_BATTERY"
    assert data["geofence_id"] is None
    assert data["geofence_name"] is None


def test_alert_text_not_logged(
    hass: HomeAssistant,
    coordinator: AnioDataUpdateCoordinator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the alert text (contains the child's name) isn't logged."""
    caplog.set_level(logging.DEBUG, logger="custom_components.anio")
    coordinator._fire_activity_events(TEST_DEVICE_ID, TEST_DEVICE_NAME, [])
    coordinator._fire_activity_events(
        TEST_DEVICE_ID, TEST_DEVICE_NAME, [alert("new1", geofence=SCHOOL)]
    )

    assert "Fired GEOFENCE_ENTERED activity event" in caplog.text
    assert "arrived at School" not in caplog.text


@pytest.mark.asyncio
async def test_update_fires_alerts_oldest_first(
    hass: HomeAssistant,
    coordinator: AnioDataUpdateCoordinator,
    mock_api_client: AsyncMock,
) -> None:
    """Test new alerts between two polls fire in chronological order."""
    mock_api_client.get_activity.return_value = [alert("old", minute=0)]
    await coordinator._async_update_data()
    hass.bus.async_fire.assert_not_called()

    # The API order is not guaranteed; events must be oldest first
    mock_api_client.get_activity.return_value = [
        alert("left", "GEOFENCE_LEFT", minute=20, geofence=SCHOOL),
        alert("old", minute=0),
        alert("entered", "GEOFENCE_ENTERED", minute=10, geofence=SCHOOL),
    ]
    await coordinator._async_update_data()

    mock_api_client.get_activity.assert_awaited_with(TEST_DEVICE_ID)
    fired = [call.args[1]["activity_id"] for call in hass.bus.async_fire.call_args_list]
    assert fired == ["entered", "left"]
