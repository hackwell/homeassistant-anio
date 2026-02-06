"""ANIO API client package."""

from .auth import AnioAuth
from .client import AnioApiClient
from .exceptions import (
    AnioApiError,
    AnioAuthError,
    AnioConnectionError,
    AnioDeviceNotFoundError,
    AnioMessageTooLongError,
    AnioOtpRequiredError,
    AnioRateLimitError,
)
from .models import (
    ActivityItem,
    AnioDeviceState,
    AuthTokens,
    ChatMessage,
    Device,
    DeviceConfig,
    DeviceLocation,
    DeviceSettings,
    Geofence,
    LocationInfo,
    UserInfo,
)

__all__ = [
    # Auth
    "AnioAuth",
    # Client
    "AnioApiClient",
    # Exceptions
    "AnioApiError",
    "AnioAuthError",
    "AnioConnectionError",
    "AnioDeviceNotFoundError",
    "AnioMessageTooLongError",
    "AnioOtpRequiredError",
    "AnioRateLimitError",
    # Models
    "ActivityItem",
    "AnioDeviceState",
    "AuthTokens",
    "ChatMessage",
    "Device",
    "DeviceConfig",
    "DeviceLocation",
    "DeviceSettings",
    "Geofence",
    "LocationInfo",
    "UserInfo",
]
