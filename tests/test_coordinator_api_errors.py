"""Tests for coordinator handling of API errors."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.anio.api import AnioApiError, AnioAuthError
from custom_components.anio.coordinator import AnioDataUpdateCoordinator


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


class TestCoordinatorApiErrors:
    """Tests for API errors that are not connection or auth related."""

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
    async def test_server_error_raises_update_failed(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test a server error (e.g. failed token refresh) is temporary."""
        mock_api_client.get_devices.side_effect = AnioApiError(
            "Token refresh failed: Service Unavailable", 503
        )

        with pytest.raises(UpdateFailed, match="API error"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_auth_error_still_raises_auth_failed(
        self, coordinator: AnioDataUpdateCoordinator, mock_api_client: AsyncMock
    ) -> None:
        """Test a rejected refresh token still starts re-authentication."""
        mock_api_client.get_devices.side_effect = AnioAuthError("Refresh token expired")

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()
