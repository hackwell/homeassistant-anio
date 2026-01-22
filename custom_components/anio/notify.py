"""Notify platform for ANIO integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AnioApiClient
from .const import DOMAIN
from .coordinator import AnioDataUpdateCoordinator
from .entity import AnioEntity

_LOGGER = logging.getLogger(__name__)


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
        device_state = self.coordinator.data.get(self._device_id)
        if device_state:
            return f"{device_state.device.settings.name} Message"
        return "ANIO Message"

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Send a message to the ANIO watch.

        Args:
            message: The message content (text or emoji code).
            title: Not used for ANIO.
            data: Optional data containing:
                - message_type: "text" (default) or "emoji"
                - username: Custom sender name for text messages
        """
        if not message or not message.strip():
            _LOGGER.debug("Skipping empty message")
            return

        data = data or {}
        message_type = data.get("message_type", "text").lower()
        username = data.get("username")

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
