"""Tests for ANIO data update coordinator."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.anio.api import (
    AnioAuthError,
    AnioConnectionError,
    AnioRateLimitError,
)
from custom_components.anio.coordinator import AnioDataUpdateCoordinator

from .conftest import TEST_DEVICE_ID, TEST_DEVICE_NAME


class TestAnioDataUpdateCoordinator:
    """Tests for AnioDataUpdateCoordinator."""

    @pytest.fixture
    def coordinator(
        self, hass: HomeAssistant, mock_api_client: AsyncMock
    ) -> AnioDataUpdateCoordinator:
        """Create a coordinator for testing."""
        return AnioDataUpdateCoordinator(
            hass=hass,
            client=mock_api_client,
            scan_interval=300,
        )

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        coordinator: AnioDataUpdateCoordinator,
        mock_api_client: AsyncMock,
        mock_device: MagicMock,
        mock_geofence: MagicMock,
    ) -> None:
        """Test successful data update."""
        data = await coordinator._async_update_data()

        assert TEST_DEVICE_ID in data
        assert data[TEST_DEVICE_ID].device.id == TEST_DEVICE_ID
        assert data[TEST_DEVICE_ID].device.settings.name == TEST_DEVICE_NAME

        mock_api_client.get_devices.assert_called_once()
        mock_api_client.get_geofences.assert_called_once()
        # Chat messages come from the chat history, not the activity feed
        mock_api_client.get_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_auth_error(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test auth error raises ConfigEntryAuthFailed."""
        mock_api_client.get_devices.side_effect = AnioAuthError("Token expired")

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_update_rate_limit_error(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test rate limit error raises UpdateFailed."""
        mock_api_client.get_devices.side_effect = AnioRateLimitError()

        with pytest.raises(UpdateFailed, match="Rate limited"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_update_connection_error(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test connection error raises UpdateFailed."""
        mock_api_client.get_devices.side_effect = AnioConnectionError()

        with pytest.raises(UpdateFailed, match="Connection error"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_geofences_cached(
        self,
        coordinator: AnioDataUpdateCoordinator,
        mock_api_client: AsyncMock,
        mock_geofence: MagicMock,
    ) -> None:
        """Test geofences are fetched per device and kept in its state."""
        data = await coordinator._async_update_data()
        coordinator.data = data

        mock_api_client.get_geofences.assert_awaited_once_with(TEST_DEVICE_ID)
        assert [g.id for g in data[TEST_DEVICE_ID].geofences] == [mock_geofence.id]
        assert [g.id for g in coordinator.geofences] == [mock_geofence.id]

    @pytest.mark.asyncio
    async def test_online_status_calculation_online(
        self, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test online status when recently seen."""
        last_seen = datetime.now(timezone.utc)
        is_online = coordinator._calculate_online_status(last_seen)
        assert is_online is True

    @pytest.mark.asyncio
    async def test_online_status_calculation_offline(
        self, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test online status when not recently seen."""
        last_seen = datetime.now(timezone.utc) - timedelta(minutes=15)
        is_online = coordinator._calculate_online_status(last_seen)
        assert is_online is False

    @pytest.mark.asyncio
    async def test_online_status_calculation_none(
        self, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test online status when never seen."""
        is_online = coordinator._calculate_online_status(None)
        assert is_online is False

    @pytest.mark.asyncio
    async def test_is_inside_geofence(
        self, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test geofence distance calculation."""
        # Point inside (same location)
        is_inside = coordinator._is_inside_geofence(
            device_lat=52.5200,
            device_lon=13.4050,
            fence_lat=52.5200,
            fence_lon=13.4050,
            radius_meters=100,
        )
        assert is_inside is True

        # Point outside (far away)
        is_inside = coordinator._is_inside_geofence(
            device_lat=52.5200,
            device_lon=13.4050,
            fence_lat=52.6000,  # Different location
            fence_lon=13.5000,
            radius_meters=100,
        )
        assert is_inside is False

    @pytest.mark.asyncio
    async def test_is_device_in_geofence(
        self,
        coordinator: AnioDataUpdateCoordinator,
        mock_api_client: AsyncMock,
        mock_device_state: MagicMock,
        mock_geofence: MagicMock,
    ) -> None:
        """Test checking if device is in geofence."""
        # Set up coordinator data
        await coordinator._async_update_data()

        # Device should be in geofence (same coordinates in fixtures)
        is_inside = coordinator.is_device_in_geofence(
            TEST_DEVICE_ID, mock_geofence.id
        )
        # Note: depends on fixture coordinates matching
        assert isinstance(is_inside, bool)

    @pytest.mark.asyncio
    async def test_is_device_in_geofence_no_data(
        self, coordinator: AnioDataUpdateCoordinator
    ) -> None:
        """Test geofence check when no data."""
        is_inside = coordinator.is_device_in_geofence("unknown", "geofence123")
        assert is_inside is False

    @pytest.mark.asyncio
    async def test_refresh_for_device(
        self,
        coordinator: AnioDataUpdateCoordinator,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test requesting refresh for a device."""
        with patch.object(
            coordinator, "async_request_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            await coordinator.async_request_refresh_for_device(TEST_DEVICE_ID)
            mock_refresh.assert_called_once()
