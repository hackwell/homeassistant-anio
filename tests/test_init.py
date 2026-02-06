"""Tests for ANIO integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant

from custom_components.anio import (
    async_setup_entry,
    async_unload_entry,
)
from custom_components.anio.const import (
    CONF_ACCESS_TOKEN,
    CONF_APP_UUID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)

from .conftest import (
    TEST_ACCESS_TOKEN,
    TEST_APP_UUID,
    TEST_EMAIL,
    TEST_REFRESH_TOKEN,
)


class TestIntegrationSetup:
    """Tests for integration setup."""

    @pytest.fixture
    def mock_config_entry_loaded(self, hass: HomeAssistant) -> MagicMock:
        """Create a mock config entry that appears loaded."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.domain = DOMAIN
        entry.title = TEST_EMAIL
        entry.data = {
            CONF_EMAIL: TEST_EMAIL,
            CONF_ACCESS_TOKEN: TEST_ACCESS_TOKEN,
            CONF_REFRESH_TOKEN: TEST_REFRESH_TOKEN,
            CONF_APP_UUID: TEST_APP_UUID,
        }
        entry.options = {}
        entry.state = ConfigEntryState.LOADED
        return entry

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry_loaded: MagicMock,
        mock_auth: AsyncMock,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test successful setup of config entry."""
        with (
            patch(
                "custom_components.anio.AnioAuth",
                return_value=mock_auth,
            ),
            patch(
                "custom_components.anio.AnioApiClient",
                return_value=mock_api_client,
            ),
            patch(
                "custom_components.anio.AnioDataUpdateCoordinator",
            ) as mock_coordinator_class,
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ) as mock_forward,
        ):
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            result = await async_setup_entry(hass, mock_config_entry_loaded)

            assert result is True
            assert DOMAIN in hass.data
            assert mock_config_entry_loaded.entry_id in hass.data[DOMAIN]

            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            mock_forward.assert_called_once_with(
                mock_config_entry_loaded, PLATFORMS
            )

    @pytest.mark.asyncio
    async def test_async_setup_entry_auth_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry_loaded: MagicMock,
    ) -> None:
        """Test setup fails when auth fails."""
        from custom_components.anio.api import AnioAuthError

        with patch(
            "custom_components.anio.AnioAuth",
        ) as mock_auth_class:
            mock_auth = mock_auth_class.return_value
            mock_auth.ensure_valid_token = AsyncMock(
                side_effect=AnioAuthError("Token expired")
            )

            with pytest.raises(Exception):
                await async_setup_entry(hass, mock_config_entry_loaded)

    @pytest.mark.asyncio
    async def test_async_setup_entry_coordinator_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry_loaded: MagicMock,
        mock_auth: AsyncMock,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test setup fails when coordinator first refresh fails."""
        from homeassistant.exceptions import ConfigEntryNotReady

        with (
            patch(
                "custom_components.anio.AnioAuth",
                return_value=mock_auth,
            ),
            patch(
                "custom_components.anio.AnioApiClient",
                return_value=mock_api_client,
            ),
            patch(
                "custom_components.anio.AnioDataUpdateCoordinator",
            ) as mock_coordinator_class,
        ):
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            mock_coordinator_class.return_value = mock_coordinator

            with pytest.raises(Exception):
                await async_setup_entry(hass, mock_config_entry_loaded)


class TestIntegrationUnload:
    """Tests for integration unload."""

    @pytest.fixture
    def mock_config_entry_with_data(self, hass: HomeAssistant) -> MagicMock:
        """Create a mock config entry with runtime data."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.domain = DOMAIN
        entry.title = TEST_EMAIL
        entry.data = {
            CONF_EMAIL: TEST_EMAIL,
            CONF_ACCESS_TOKEN: TEST_ACCESS_TOKEN,
            CONF_REFRESH_TOKEN: TEST_REFRESH_TOKEN,
            CONF_APP_UUID: TEST_APP_UUID,
        }
        entry.options = {}

        # Set up hass.data with runtime data
        coordinator = MagicMock()
        hass.data[DOMAIN] = {
            entry.entry_id: {
                "coordinator": coordinator,
                "auth": MagicMock(),
                "client": MagicMock(),
            }
        }
        return entry

    @pytest.mark.asyncio
    async def test_async_unload_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_data: MagicMock,
    ) -> None:
        """Test successful unload of config entry."""
        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, mock_config_entry_with_data)

            assert result is True
            mock_unload.assert_called_once_with(
                mock_config_entry_with_data, PLATFORMS
            )
            # Data should be cleaned up
            assert mock_config_entry_with_data.entry_id not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_async_unload_entry_platform_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_data: MagicMock,
    ) -> None:
        """Test unload when platform unload fails."""
        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await async_unload_entry(hass, mock_config_entry_with_data)

            assert result is False
            # Data should NOT be cleaned up on failure
            assert mock_config_entry_with_data.entry_id in hass.data[DOMAIN]


class TestDomainData:
    """Tests for domain data structure."""

    def test_platforms_list(self) -> None:
        """Test PLATFORMS constant contains expected platforms."""
        expected_platforms = [
            "sensor",
            "binary_sensor",
            "device_tracker",
            "button",
            "notify",
            "switch",
            "select",
        ]
        assert set(PLATFORMS) == set(expected_platforms)

    @pytest.mark.asyncio
    async def test_hass_data_structure(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_auth: AsyncMock,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test hass.data structure after setup."""
        with (
            patch(
                "custom_components.anio.AnioAuth",
                return_value=mock_auth,
            ),
            patch(
                "custom_components.anio.AnioApiClient",
                return_value=mock_api_client,
            ),
            patch(
                "custom_components.anio.AnioDataUpdateCoordinator",
            ) as mock_coordinator_class,
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ),
        ):
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            await async_setup_entry(hass, mock_config_entry)

            # Verify structure
            entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
            assert "coordinator" in entry_data
            assert "auth" in entry_data
            assert "client" in entry_data
