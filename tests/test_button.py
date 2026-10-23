"""Tests for ANIO button platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.anio.api import AnioApiError
from custom_components.anio.button import (
    AnioFlowerButton,
    AnioPowerOffButton,
    AnioRingButton,
    async_setup_entry,
)
from custom_components.anio.const import DOMAIN

from .conftest import TEST_DEVICE_ID


@pytest.fixture
def hass(mock_hass: HomeAssistant) -> HomeAssistant:
    """Use the mocked Home Assistant instance in these unit tests."""
    return mock_hass


class TestAnioRingButton:
    """Tests for AnioRingButton (formerly "Locate")."""

    @pytest.fixture
    def ring_button(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> AnioRingButton:
        """Create a ring button for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        coordinator.async_request_refresh = AsyncMock()
        return AnioRingButton(
            coordinator=coordinator,
            client=mock_api_client,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id_unchanged(self, ring_button: AnioRingButton) -> None:
        """Test the unique ID of the former Locate button is kept."""
        assert ring_button.unique_id == f"{TEST_DEVICE_ID}_locate"

    def test_name(self, ring_button: AnioRingButton) -> None:
        """Test button name."""
        assert ring_button.name == "Ring"

    def test_icon(self, ring_button: AnioRingButton) -> None:
        """Test button icon."""
        assert ring_button.icon == "mdi:bell-ring"

    def test_entity_category(self, ring_button: AnioRingButton) -> None:
        """Test entity category."""
        assert ring_button.entity_category == EntityCategory.DIAGNOSTIC

    @pytest.mark.asyncio
    async def test_async_press_rings_without_refresh(
        self,
        ring_button: AnioRingButton,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test pressing rings the watch and doesn't trigger a useless refresh."""
        await ring_button.async_press()

        mock_api_client.find_device.assert_called_once_with(TEST_DEVICE_ID)
        ring_button.coordinator.async_request_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_press_api_error(
        self,
        ring_button: AnioRingButton,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test API error when pressing the ring button."""
        mock_api_client.find_device.side_effect = AnioApiError("API Error")

        with pytest.raises(AnioApiError):
            await ring_button.async_press()


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
        assert power_off_button.name == "Power Off"

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

        def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Should create locate, power_off, and flower buttons per device
        assert len(entities) == 3
        assert any(isinstance(e, AnioRingButton) for e in entities)
        assert any(isinstance(e, AnioPowerOffButton) for e in entities)
        assert any(isinstance(e, AnioFlowerButton) for e in entities)

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

        def async_add_entities(new_entities: list, update: bool = True) -> None:
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

        def async_add_entities(new_entities: list, update: bool = True) -> None:
            entities.extend(new_entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # 3 buttons per device (locate + power_off + flower)
        assert len(entities) == 6


class TestAnioFlowerButton:
    """Tests for AnioFlowerButton."""

    @pytest.fixture
    def flower_button(
        self,
        hass: HomeAssistant,
        mock_coordinator_data: dict,
        mock_api_client: AsyncMock,
    ) -> AnioFlowerButton:
        """Create a flower button for testing."""
        coordinator = MagicMock()
        coordinator.data = mock_coordinator_data
        return AnioFlowerButton(
            coordinator=coordinator,
            client=mock_api_client,
            device_id=TEST_DEVICE_ID,
        )

    def test_unique_id(self, flower_button: AnioFlowerButton) -> None:
        """Test unique ID format."""
        assert flower_button.unique_id == f"{TEST_DEVICE_ID}_flower"

    def test_name(self, flower_button: AnioFlowerButton) -> None:
        """Test button name."""
        assert flower_button.name == "Flower"

    def test_icon(self, flower_button: AnioFlowerButton) -> None:
        """Test button icon."""
        assert flower_button.icon == "mdi:flower"

    def test_entity_category(self, flower_button: AnioFlowerButton) -> None:
        """Test entity category is None (user-facing action)."""
        assert flower_button.entity_category is None

    @pytest.mark.asyncio
    async def test_async_press(
        self,
        flower_button: AnioFlowerButton,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test pressing the flower button."""
        await flower_button.async_press()
        mock_api_client.send_flower.assert_called_once_with(TEST_DEVICE_ID)

    @pytest.mark.asyncio
    async def test_async_press_api_error(
        self,
        flower_button: AnioFlowerButton,
        mock_api_client: AsyncMock,
    ) -> None:
        """Test API error when pressing flower button."""
        from custom_components.anio.api import AnioApiError

        mock_api_client.send_flower.side_effect = AnioApiError("API Error")
        with pytest.raises(AnioApiError):
            await flower_button.async_press()
