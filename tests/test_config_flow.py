"""Tests for ANIO config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.anio.api import AnioAuthError, AnioOtpRequiredError, AuthTokens
from custom_components.anio.const import DOMAIN

from .conftest import (
    TEST_ACCESS_TOKEN,
    TEST_APP_UUID,
    TEST_EMAIL,
    TEST_PASSWORD,
    TEST_REFRESH_TOKEN,
)


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
        self, hass: HomeAssistant, mock_auth_success: AsyncMock
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
    async def test_flow_2fa_required(
        self, hass: HomeAssistant, mock_auth_success: AsyncMock
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
        existing_entry = MagicMock()
        existing_entry.domain = DOMAIN
        existing_entry.unique_id = TEST_EMAIL.lower()

        hass.config_entries._entries = {existing_entry.entry_id: existing_entry}

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
        self, hass: HomeAssistant, mock_auth_success: AsyncMock
    ) -> None:
        """Test reauth flow success."""
        # Create existing entry
        existing_entry = MagicMock()
        existing_entry.entry_id = "test_entry"
        existing_entry.domain = DOMAIN
        existing_entry.unique_id = TEST_EMAIL.lower()
        existing_entry.data = {CONF_EMAIL: TEST_EMAIL}

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

        # Should either create entry or abort with success
        assert result["type"] in [FlowResultType.CREATE_ENTRY, FlowResultType.ABORT]


class TestOptionsFlow:
    """Tests for options flow."""

    @pytest.mark.asyncio
    async def test_options_flow(
        self, hass: HomeAssistant, mock_config_entry: MagicMock
    ) -> None:
        """Test options flow."""
        mock_config_entry.add_update_listener = MagicMock()

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            result = await hass.config_entries.options.async_init(
                mock_config_entry.entry_id
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "init"

            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {"scan_interval": 120},
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["data"]["scan_interval"] == 120
