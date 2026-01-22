"""Config flow for ANIO Smartwatch integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnioAuth, AnioAuthError, AnioOtpRequiredError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_APP_UUID,
    CONF_REFRESH_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_OTP_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("otp_code"): str,
    }
)


class AnioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ANIO Smartwatch."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._email: str | None = None
        self._password: str | None = None
        self._auth: AnioAuth | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Args:
            user_input: User input from the form.

        Returns:
            Config flow result.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]

            # Check if already configured
            await self.async_set_unique_id(self._email.lower())
            self._abort_if_unique_id_configured()

            try:
                session = async_get_clientsession(self.hass)
                self._auth = AnioAuth(
                    session=session,
                    email=self._email,
                    password=self._password,
                )

                tokens = await self._auth.login()

                if tokens.is_otp_required:
                    return await self.async_step_2fa()

                return self._create_entry()

            except AnioOtpRequiredError:
                return await self.async_step_2fa()

            except AnioAuthError as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"

            except aiohttp.ClientError as err:
                _LOGGER.error("Connection failed: %s", err)
                errors["base"] = "cannot_connect"

            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_2fa(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the 2FA step.

        Args:
            user_input: User input from the form.

        Returns:
            Config flow result.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            otp_code = user_input.get("otp_code")

            if not self._auth:
                return self.async_abort(reason="auth_error")

            try:
                await self._auth.login(otp_code=otp_code)
                return self._create_entry()

            except AnioAuthError as err:
                _LOGGER.error("2FA authentication failed: %s", err)
                errors["base"] = "invalid_otp"

            except aiohttp.ClientError as err:
                _LOGGER.error("Connection failed: %s", err)
                errors["base"] = "cannot_connect"

            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="2fa",
            data_schema=STEP_OTP_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"email": self._email or ""},
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry.

        Returns:
            Config flow result.
        """
        if not self._auth or not self._email:
            return self.async_abort(reason="auth_error")

        return self.async_create_entry(
            title=self._email,
            data={
                CONF_EMAIL: self._email,
                CONF_ACCESS_TOKEN: self._auth.access_token,
                CONF_REFRESH_TOKEN: self._auth.refresh_token,
                CONF_APP_UUID: self._auth.app_uuid,
            },
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Handle re-authentication.

        Args:
            entry_data: Data from the existing config entry.

        Returns:
            Config flow result.
        """
        self._email = entry_data.get(CONF_EMAIL)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle re-authentication confirmation.

        Args:
            user_input: User input from the form.

        Returns:
            Config flow result.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self._password = user_input[CONF_PASSWORD]

            try:
                session = async_get_clientsession(self.hass)
                self._auth = AnioAuth(
                    session=session,
                    email=self._email,
                    password=self._password,
                )

                tokens = await self._auth.login()

                if tokens.is_otp_required:
                    return await self.async_step_2fa()

                # Update the existing entry
                existing_entry = await self.async_set_unique_id(
                    self._email.lower() if self._email else ""
                )

                if existing_entry:
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data={
                            CONF_EMAIL: self._email,
                            CONF_ACCESS_TOKEN: self._auth.access_token,
                            CONF_REFRESH_TOKEN: self._auth.refresh_token,
                            CONF_APP_UUID: self._auth.app_uuid,
                        },
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

                return self._create_entry()

            except AnioOtpRequiredError:
                return await self.async_step_2fa()

            except AnioAuthError:
                errors["base"] = "invalid_auth"

            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"

            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"email": self._email or ""},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: Any,
    ) -> OptionsFlow:
        """Get the options flow for this handler.

        Args:
            config_entry: The config entry.

        Returns:
            Options flow handler.
        """
        return AnioOptionsFlow(config_entry)


class AnioOptionsFlow(OptionsFlow):
    """Handle options flow for ANIO integration."""

    def __init__(self, config_entry: Any) -> None:
        """Initialize options flow.

        Args:
            config_entry: The config entry.
        """
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle options flow.

        Args:
            user_input: User input from the form.

        Returns:
            Config flow result.
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            "scan_interval", DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "scan_interval",
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
