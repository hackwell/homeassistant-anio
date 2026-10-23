"""Tests for ANIO config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anio.api import (
    AnioApiError,
    AnioAuthError,
    AnioConnectionError,
    AnioOtpRequiredError,
    AuthTokens,
)
from custom_components.anio.const import DOMAIN

from .conftest import (
    TEST_ACCESS_TOKEN,
    TEST_APP_UUID,
    TEST_EMAIL,
    TEST_PASSWORD,
    TEST_REFRESH_TOKEN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load the anio custom integration."""


class TestConfigFlow:
    """Tests for config flow."""

    @pytest.fixture
    def mock_auth_success(self) -> AsyncMock:
        """Create a mock auth that succeeds."""
        auth = AsyncMock()
        auth.login = AsyncMock(
            return_value=AuthTokens(
                accessToken=TEST_ACCESS_TOKEN,
                refreshToken=TEST_REFRESH_TOKEN,
                isOtpCodeRequired=False,
            )
        )
        auth.access_token = TEST_ACCESS_TOKEN
        auth.refresh_token = TEST_REFRESH_TOKEN
        auth.app_uuid = TEST_APP_UUID
        return auth

    @pytest.mark.asyncio
    async def test_form_shows_on_init(self, hass: HomeAssistant) -> None:
        """Test that the form is shown on init."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    @pytest.mark.asyncio
    async def test_full_flow_success(
        self,
        hass: HomeAssistant,
        mock_auth_success: AsyncMock,
        mock_setup_entry: AsyncMock,
    ) -> None:
        """Test successful config flow."""
        with patch(
            "custom_components.anio.config_flow.AnioAuth",
            return_value=mock_auth_success,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_EMAIL: TEST_EMAIL,
                    CONF_PASSWORD: TEST_PASSWORD,
                },
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == TEST_EMAIL
        assert result["data"][CONF_EMAIL] == TEST_EMAIL
        assert result["data"]["access_token"] == TEST_ACCESS_TOKEN
        assert result["data"]["refresh_token"] == TEST_REFRESH_TOKEN

    @pytest.mark.asyncio
    async def test_flow_invalid_credentials(self, hass: HomeAssistant) -> None:
        """Test flow with invalid credentials."""
        with patch(
            "custom_components.anio.config_flow.AnioAuth",
        ) as mock_auth_class:
            mock_auth = mock_auth_class.return_value
            mock_auth.login = AsyncMock(
                side_effect=AnioAuthError("Invalid credentials")
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_EMAIL: TEST_EMAIL,
                    CONF_PASSWORD: "wrong_password",
                },
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_auth"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [AnioConnectionError(), AnioApiError("Service Unavailable", 503)],
        ids=["network", "server_error"],
    )
    async def test_flow_cannot_connect(
        self, hass: HomeAssistant, error: Exception
    ) -> None:
        """Test network and server problems show "cannot connect"."""
        with patch(
            "custom_components.anio.config_flow.AnioAuth",
        ) as mock_auth_class:
            mock_auth_class.return_value.login = AsyncMock(side_effect=error)

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_EMAIL: TEST_EMAIL, CONF_PASSWORD: TEST_PASSWORD},
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_flow_2fa_required(
        self,
        hass: HomeAssistant,
        mock_auth_success: AsyncMock,
        mock_setup_entry: AsyncMock,
    ) -> None:
        """Test flow when 2FA is required."""
        # First call raises OtpRequired, second succeeds
        mock_auth_success.login = AsyncMock(
            side_effect=[
                AnioOtpRequiredError(),
                AuthTokens(
                    accessToken=TEST_ACCESS_TOKEN,
                    refreshToken=TEST_REFRESH_TOKEN,
                    isOtpCodeRequired=False,
                ),
            ]
        )

        with patch(
            "custom_components.anio.config_flow.AnioAuth",
            return_value=mock_auth_success,
        ):
            # Start flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Enter credentials
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_EMAIL: TEST_EMAIL,
                    CONF_PASSWORD: TEST_PASSWORD,
                },
            )

            # Should show 2FA form
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "2fa"

            # Enter OTP
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"otp_code": "123456"},
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == TEST_EMAIL

    @pytest.mark.asyncio
    async def test_flow_2fa_invalid_code(
        self, hass: HomeAssistant, mock_auth_success: AsyncMock
    ) -> None:
        """Test flow with invalid 2FA code."""
        # First call raises OtpRequired, second fails with auth error
        mock_auth_success.login = AsyncMock(
            side_effect=[
                AnioOtpRequiredError(),
                AnioAuthError("Invalid OTP"),
            ]
        )

        with patch(
            "custom_components.anio.config_flow.AnioAuth",
            return_value=mock_auth_success,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_EMAIL: TEST_EMAIL,
                    CONF_PASSWORD: TEST_PASSWORD,
                },
            )

            # Enter invalid OTP
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"otp_code": "000000"},
            )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "2fa"
        assert result["errors"]["base"] == "invalid_otp"

    @pytest.mark.asyncio
    async def test_flow_already_configured(
        self, hass: HomeAssistant, mock_auth_success: AsyncMock
    ) -> None:
        """Test flow when already configured."""
        # Create an existing entry
        MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_EMAIL.lower(),
            data={CONF_EMAIL: TEST_EMAIL},
        ).add_to_hass(hass)

        with patch(
            "custom_components.anio.config_flow.AnioAuth",
            return_value=mock_auth_success,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_EMAIL: TEST_EMAIL,
                    CONF_PASSWORD: TEST_PASSWORD,
                },
            )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    @pytest.mark.asyncio
    async def test_reauth_flow_success(
        self,
        hass: HomeAssistant,
        mock_auth_success: AsyncMock,
        mock_setup_entry: AsyncMock,
    ) -> None:
        """Test reauth flow success."""
        # Create existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_EMAIL.lower(),
            data={CONF_EMAIL: TEST_EMAIL},
        )
        existing_entry.add_to_hass(hass)

        with patch(
            "custom_components.anio.config_flow.AnioAuth",
            return_value=mock_auth_success,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_REAUTH,
                    "entry_id": existing_entry.entry_id,
                },
                data=existing_entry.data,
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "reauth_confirm"

            # Re-enter password
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_PASSWORD: TEST_PASSWORD},
            )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert existing_entry.data["access_token"] == TEST_ACCESS_TOKEN
        assert existing_entry.data["refresh_token"] == TEST_REFRESH_TOKEN

    @pytest.mark.asyncio
    async def test_reauth_flow_with_2fa(
        self,
        hass: HomeAssistant,
        mock_auth_success: AsyncMock,
        mock_setup_entry: AsyncMock,
    ) -> None:
        """Test reauth that asks for a 2FA code updates the existing entry."""
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_EMAIL.lower(),
            data={CONF_EMAIL: TEST_EMAIL},
        )
        existing_entry.add_to_hass(hass)

        mock_auth_success.login = AsyncMock(
            side_effect=[
                AnioOtpRequiredError(),
                AuthTokens(
                    accessToken=TEST_ACCESS_TOKEN,
                    refreshToken=TEST_REFRESH_TOKEN,
                    isOtpCodeRequired=False,
                ),
            ]
        )

        with patch(
            "custom_components.anio.config_flow.AnioAuth",
            return_value=mock_auth_success,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_REAUTH,
                    "entry_id": existing_entry.entry_id,
                },
                data=existing_entry.data,
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_PASSWORD: TEST_PASSWORD},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "2fa"

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"otp_code": "123456"},
            )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert existing_entry.data["access_token"] == TEST_ACCESS_TOKEN
        assert existing_entry.data["refresh_token"] == TEST_REFRESH_TOKEN
        # No second entry for the same account
        assert len(hass.config_entries.async_entries(DOMAIN)) == 1


class TestOptionsFlow:
    """Tests for options flow."""

    @pytest.mark.asyncio
    async def test_options_flow(self, hass: HomeAssistant) -> None:
        """Test options flow."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=TEST_EMAIL.lower(),
            data={CONF_EMAIL: TEST_EMAIL},
            options={},
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"scan_interval": 120},
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["scan_interval"] == 120
        assert entry.options == {"scan_interval": 120}
