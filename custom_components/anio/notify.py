"""Notify platform for ANIO integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AnioApiClient
from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import AnioEntity

_LOGGER = logging.getLogger(__name__)

# notify.send_message only accepts message and title, so the ANIO specific
# options (emoji, sender name) are offered through anio.send_message.
SERVICE_SEND_MESSAGE = "send_message"
ATTR_MESSAGE_TYPE = "message_type"
ATTR_USERNAME = "username"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ANIO notify entities from a config entry."""
    coordinator: AnioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    client: AnioApiClient = hass.data[DOMAIN][entry.entry_id]["client"]

    entities: list[NotifyEntity] = []

    for device_id in coordinator.data:
        entities.append(
            AnioNotifyEntity(coordinator, client, device_id)
        )

    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SEND_MESSAGE,
        {
            vol.Required("message"): cv.string,
            vol.Optional(ATTR_MESSAGE_TYPE, default="text"): vol.In(
                ["text", "emoji"]
            ),
            vol.Optional(ATTR_USERNAME): cv.string,
        },
        "async_send_anio_message",
    )


class AnioNotifyEntity(AnioEntity, NotifyEntity):
    """Notify entity for sending messages to ANIO watch."""

    def __init__(
        self,
        coordinator: AnioDataUpdateCoordinator,
        client: AnioApiClient,
        device_id: str,
    ) -> None:
        """Initialize the notify entity.

        Args:
            coordinator: The data update coordinator.
            client: The ANIO API client.
            device_id: The ANIO device ID.
        """
        super().__init__(coordinator, device_id)
        self._client = client
        self._attr_unique_id = f"{device_id}_notify"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Message"

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        """Send a text message to the ANIO watch (notify.send_message).

        Args:
            message: The message text.
            title: Not used for ANIO.
        """
        await self.async_send_anio_message(message)

    async def async_send_anio_message(
        self,
        message: str,
        message_type: str = "text",
        username: str | None = None,
    ) -> None:
        """Send a text or emoji message to the ANIO watch (anio.send_message).

        Args:
            message: The message content (text or emoji code).
            message_type: "text" (default) or "emoji".
            username: Custom sender name for text messages.
        """
        if not message or not message.strip():
            _LOGGER.debug("Skipping empty message")
            return

        message_type = message_type.lower()

        _LOGGER.debug(
            "Sending %s message to device %s: %s",
            message_type,
            self._device_id,
            message[:20] + "..." if len(message) > 20 else message,
        )

        if message_type == "emoji":
            await self._client.send_emoji_message(
                self._device_id,
                message,
            )
        else:
            await self._client.send_text_message(
                self._device_id,
                message,
                username=username,
            )

        _LOGGER.info(
            "Message sent to device %s",
            self._device_id,
        )
