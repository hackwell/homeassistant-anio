"""Constants for the ANIO Smartwatch integration."""

from typing import Final

# Integration domain
DOMAIN: Final = "anio"

# API configuration
API_URL: Final = "https://api.anio.cloud"
CLIENT_ID: Final = "anio"

# Polling configuration
DEFAULT_SCAN_INTERVAL: Final = 300  # 5 minutes in seconds
MIN_SCAN_INTERVAL: Final = 60  # 1 minute minimum
MAX_SCAN_INTERVAL: Final = 300  # 5 minutes maximum

# Token refresh configuration
TOKEN_REFRESH_BUFFER: Final = 300  # Refresh 5 minutes before expiry

# Rate limiting
RATE_LIMIT_BACKOFF_BASE: Final = 2  # Exponential backoff base
RATE_LIMIT_MAX_RETRIES: Final = 5
# Longer Retry-After waits fail the request instead of blocking the update
RATE_LIMIT_MAX_WAIT: Final = 60

# Configuration keys
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_APP_UUID: Final = "app_uuid"

# Entity attribute keys
ATTR_DEVICE_ID: Final = "device_id"
ATTR_DEVICE_NAME: Final = "device_name"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"
ATTR_GENERATION: Final = "generation"
ATTR_IMEI: Final = "imei"
ATTR_PHONE_NUMBER: Final = "phone_number"

# Message types
MESSAGE_TYPE_TEXT: Final = "TEXT"
MESSAGE_TYPE_EMOJI: Final = "EMOJI"
MESSAGE_TYPE_VOICE: Final = "VOICE"

# Message sender types
SENDER_APP: Final = "APP"
SENDER_WATCH: Final = "WATCH"
SENDER_DEVICE: Final = "DEVICE"

# Emoji codes
# Emoji codes in the order of the ANIO app's emoji bar:
# E01 🙂, E02 😘, E03 😎, E04 🙁, E05 😁, E06 😛, E07 👎, E08 👍, E09 ❤️
VALID_EMOJI_CODES: Final = [f"E{i:02d}" for i in range(1, 10)]

# The watch can't display messages without a sender name: text arrives as a
# digit code and emojis as a heart. The ANIO app always sends one.
DEFAULT_SENDER_NAME: Final = "Home Assistant"

# Event types
EVENT_MESSAGE_RECEIVED: Final = f"{DOMAIN}_message_received"
# ANIO's own alerts: GEOFENCE_ENTERED, GEOFENCE_LEFT, LOW_BATTERY, ...
EVENT_ACTIVITY: Final = f"{DOMAIN}_activity"

# Ring profiles
RING_PROFILES: Final = ["RING_AND_VIBRATE", "VIBRATE_ONLY", "SILENT"]

# Platforms
PLATFORMS: Final = [
    "sensor",
    "binary_sensor",
    "device_tracker",
    "button",
    "notify",
    "switch",
    "select",
]
