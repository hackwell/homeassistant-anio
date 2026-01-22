"""Tests for ANIO button platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.anio.api import AnioApiError
from custom_components.anio.button import (
    AnioLocateButton,
    AnioPowerOffButton,
    async_setup_entry,
)
from custom_components.anio.const import DOMAIN

from .conftest import TEST_DEVICE_ID, TEST_DEVICE_NAME


class TestAnioLocateButton:
    """Tests for AnioLocateButton."""

    @pytest.fixture
    def locate_button(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> AnioLocateButton:
        """Create a locate button for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        coordinator.async_request_refresh = AsyncMock()
        return AnioLocateButton(
            coordinator=coordinator,
            client=mock_api_client,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, locate_button: AnioLocateButton) -> None:
        """Test unique ID format."""
        assert locate_button.unique_id == f"{TEST_DEVICE_ID}_locate"

    def test_name(self, locate_button: AnioLocateButton) -> None:
        """Test button name."""
        assert locate_button.name == f"{TEST_DEVICE_NAME} Locate"

    def test_icon(self, locate_button: AnioLocateButton) -> None:
        """Test button icon."""
        assert locate_button.icon == "mdi:crosshairs-gps"

    def test_entity_category(self, locate_button: AnioLocateButton) -> None:
        """Test entity category."""
        assert locate_button.entity_category == EntityCategory.DIAGNOSTIC

    @pytest.mark.asyncio
    async def test_async_press(
        self,
        locate_button: AnioLocateButton,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test pressing the locate button."""
        await locate_button.async_press()

        mock_api_client.find_device.assert_called_once_with(TEST_DEVICE_ID)
        locate_button.coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_press_api_error(
        self,
        locate_button: AnioLocateButton,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test API error when pressing locate button."""
        mock_api_client.find_device.side_effect = AnioApiError("API Error")

        with pytest.raises(AnioApiError):
            await locate_button.async_press()


class TestAnioPowerOffButton:
    """Tests for AnioPowerOffButton."""

    @pytest.fixture
    def power_off_button(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> AnioPowerOffButton:
        """Create a power off button for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioPowerOffButton(
            coordinator=coordinator,
            client=mock_api_client,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, power_off_button: AnioPowerOffButton) -> None:
        """Test unique ID format."""
        assert power_off_button.unique_id == f"{TEST_DEVICE_ID}_power_off"

    def test_name(self, power_off_button: AnioPowerOffButton) -> None:
        """Test button name."""
        assert power_off_button.name == f"{TEST_DEVICE_NAME} Power Off"

    def test_icon(self, power_off_button: AnioPowerOffButton) -> None:
        """Test button icon."""
        assert power_off_button.icon == "mdi:power"

    def test_entity_category(self, power_off_button: AnioPowerOffButton) -> None:
        """Test entity category."""
        assert power_off_button.entity_category == EntityCategory.CONFIG

    def test_device_class(self, power_off_button: AnioPowerOffButton) -> None:
        """Test device class."""
        # Power off is a restart-type action
        assert power_off_button.device_class == ButtonDeviceClass.RESTART

    @pytest.mark.asyncio
    async def test_async_press(
        self,
        power_off_button: AnioPowerOffButton,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test pressing the power off button."""
        await power_off_button.async_press()

        mock_api_client.power_off_device.assert_called_once_with(TEST_DEVICE_ID)

    @pytest.mark.asyncio
    async def test_async_press_api_error(
        self,
        power_off_button: AnioPowerOffButton,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test API error when pressing power off button."""
        mock_api_client.power_off_device.side_effect = AnioApiError("API Error")

        with pytest.raises(AnioApiError):
            await power_off_button.async_press()


class TestButtonSetup:
    """Tests for button platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test button platform setup."""
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

        # Should create locate and power_off buttons per device
        assert len(entities) == 2
        assert any(isinstance(e, AnioLocateButton) for e in entities)
        assert any(isinstance(e, AnioPowerOffButton) for e in entities)

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test button platform setup with no devices."""
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

    @pytest.mark.asyncio
    async def test_async_setup_entry_multiple_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_device_state,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test button platform setup with multiple devices."""
        from copy import deepcopy

        device_state_2 = deepcopy(mock_device_state)
        device_state_2.device.id = "device456"
        device_state_2.device.settings.name = "Second Watch"

        coordinator = MagicMock()
        coordinator.data = {
            TEST_DEVICE_ID: mock_device_state,
            "device456": device_state_2,
        }

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

        # 2 buttons per device (locate + power_off)
        assert len(entities) == 4
