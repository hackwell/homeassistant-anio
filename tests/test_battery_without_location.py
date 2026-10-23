"""Tests for battery and signal values without a location."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.anio.coordinator import AnioDataUpdateCoordinator

from .conftest import TEST_DEVICE_ID


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


class TestBatteryWithoutLocation:
    """Tests for battery and signal values when no location is available."""

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
    async def test_battery_unknown_without_location(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test a missing last location gives unknown, not 0 %."""
        mock_api_client.get_last_location.return_value = None

        data = await coordinator._async_update_data()

        assert data[TEST_DEVICE_ID].battery_level is None
        assert data[TEST_DEVICE_ID].signal_strength is None

    @pytest.mark.asyncio
    async def test_battery_from_last_location(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test battery and signal come from the last location."""
        from custom_components.anio.api.models import DeviceLocation

        mock_api_client.get_last_location.return_value = DeviceLocation(
            position=[52.52, 13.405],
            batteryLevel=42,
            signalStrength=70,
            positionDeterminedBy="GPS",
            date=datetime.now(timezone.utc),
            lastResponse=datetime.now(timezone.utc),
            deviceId=TEST_DEVICE_ID,
        )

        data = await coordinator._async_update_data()

        assert data[TEST_DEVICE_ID].battery_level == 42
        assert data[TEST_DEVICE_ID].signal_strength == 70
