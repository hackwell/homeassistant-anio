"""Pydantic models for the ANIO API responses."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthTokens(BaseModel):
    """Authentication tokens from the ANIO API."""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    is_otp_required: bool = Field(default=False, alias="isOtpCodeRequired")


class DeviceConfig(BaseModel):
    """Device configuration from the ANIO API."""

    model_config = ConfigDict(populate_by_name=True)

    generation: str
    # Not used by the integration; a plain string so new device types don't
    # make the whole device list fail validation.
    type: str = "WATCH"
    firmware_version: str = Field(alias="firmwareVersion")
    max_chat_message_length: int = Field(default=95, alias="maxChatMessageLength")
    max_phonebook_entries: int = Field(default=20, alias="maxPhonebookEntries")
    max_geofences: int = Field(default=5, alias="maxGeofences")
    has_text_chat: bool = Field(default=True, alias="hasTextChat")
    has_voice_chat: bool = Field(default=True, alias="hasVoiceChat")
    has_emojis: bool = Field(default=True, alias="hasEmojis")
    has_step_counter: bool = Field(default=True, alias="hasStepCounter")
    has_locating_switch: bool = Field(default=True, alias="hasLocatingSwitch")
    # Reward hearts, which the flower button adds (false on the ANIO 6)
    has_hearts: bool = Field(default=True, alias="hasHearts")


class DeviceSettings(BaseModel):
    """Device settings from the ANIO API."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    hex_color: str = Field(alias="hexColor")
    phone_nr: str | None = Field(default=None, alias="phoneNr")
    # Not used by the integration; see DeviceConfig.type
    gender: str | None = None
    step_target: int = Field(default=10000, alias="stepTarget")
    step_count: int = Field(default=0, alias="stepCount")
    battery: int = Field(default=0)
    is_locating_active: bool = Field(default=True, alias="isLocatingActive")
    ring_profile: str = Field(default="RING_AND_VIBRATE", alias="ringProfile")

    @field_validator("battery")
    @classmethod
    def validate_battery(cls, v: int) -> int:
        """Validate battery level is between 0 and 100."""
        return max(0, min(100, v))

    @field_validator("step_count")
    @classmethod
    def validate_step_count(cls, v: int) -> int:
        """Validate step count is non-negative."""
        return max(0, v)


class UserInfo(BaseModel):
    """User information from the ANIO API."""

    id: str
    username: str | None = None


class Device(BaseModel):
    """Device from the ANIO API."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    imei: str
    config: DeviceConfig
    settings: DeviceSettings
    user: UserInfo | None = None


class ChatMessage(BaseModel):
    """Chat message from the ANIO API."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    device_id: str = Field(alias="deviceId")
    text: str | None = None
    username: str | None = None
    type: Literal["TEXT", "EMOJI", "VOICE"]
    sender: Literal["APP", "WATCH", "DEVICE"]
    is_received: bool = Field(default=False, alias="isReceived")
    is_read: bool = Field(default=False, alias="isRead")
    created_at: datetime = Field(alias="createdAt")


class Geofence(BaseModel):
    """Geofence from GET /v1/geofence/{deviceId}."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    # Center as [latitude, longitude], like DeviceLocation.position
    location: list[float]
    radius_km: float = Field(alias="radiusInKm")
    # Time window in which ANIO monitors the geofence ("HH:MM")
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    is_enabled: bool = Field(default=True, alias="isEnabled")
    device_id: str = Field(default="", alias="deviceId")

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: list[float]) -> list[float]:
        """Validate the center is a valid [latitude, longitude] pair."""
        if len(v) != 2:
            raise ValueError("Location must be [latitude, longitude]")
        if not -90 <= v[0] <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= v[1] <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v

    @property
    def latitude(self) -> float:
        """Get the latitude of the center."""
        return self.location[0]

    @property
    def longitude(self) -> float:
        """Get the longitude of the center."""
        return self.location[1]

    @property
    def radius(self) -> int:
        """Get the radius in meters."""
        return round(self.radius_km * 1000)


class DeviceLocation(BaseModel):
    """Location entry from /v1/location/{deviceId}."""

    model_config = ConfigDict(populate_by_name=True)

    position: list[float]
    battery_level: int = Field(alias="batteryLevel")
    signal_strength: int = Field(alias="signalStrength")
    position_determined_by: str = Field(alias="positionDeterminedBy")
    date: datetime
    last_response: datetime = Field(alias="lastResponse")
    speed: int = 0
    direction: int = 0
    device_id: str = Field(alias="deviceId")
    # The location reports the current tracking mode (e.g. NORMAL)
    tracking_mode: str | None = Field(default=None, alias="trackingMode")

    @property
    def latitude(self) -> float:
        """Get latitude from position array."""
        return self.position[0]

    @property
    def longitude(self) -> float:
        """Get longitude from position array."""
        return self.position[1]


class LocationInfo(BaseModel):
    """Location information from the ANIO API."""

    model_config = ConfigDict(populate_by_name=True)

    latitude: float = Field(alias="lat")
    longitude: float = Field(alias="lng")
    accuracy: int = Field(default=0)
    timestamp: datetime | None = None
    # How the watch determined the position (positionDeterminedBy)
    source: str | None = None


class ActivityItem(BaseModel):
    """Alert from GET /v1/activity, e.g. GEOFENCE_ENTERED or LOW_BATTERY."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    device_id: str = Field(alias="deviceId")
    type: str
    # Human-readable text from ANIO (as shown in the app)
    text: str | None = None
    created_at: datetime = Field(alias="createdAt")
    # Set for geofence alerts; kept as dict so a format change doesn't drop
    # the whole alert
    geofence: dict | None = None

    @property
    def geofence_id(self) -> str | None:
        """Get the ID of the geofence of a geofence alert."""
        return self.geofence.get("id") if self.geofence else None

    @property
    def geofence_name(self) -> str | None:
        """Get the name of the geofence of a geofence alert."""
        return self.geofence.get("name") if self.geofence else None


# The API sends weekdays as a 7-character bitstring starting with Sunday,
# e.g. "0111110" for Monday to Friday.
WEEKDAYS = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")


def parse_weekdays(value: object) -> list[str]:
    """Convert the API's weekday bitstring into day names.

    Lists of day names (older format, tests) are passed through.

    Args:
        value: Bitstring like "0111110" or a list of day names.

    Returns:
        Day names, e.g. ["MON", "TUE", "WED", "THU", "FRI"].
    """
    if isinstance(value, str):
        if len(value) == len(WEEKDAYS) and set(value) <= {"0", "1"}:
            return [day for day, bit in zip(WEEKDAYS, value, strict=True) if bit == "1"]
        return []
    if isinstance(value, list):
        return [str(day) for day in value]
    return []


class AlarmClock(BaseModel):
    """Alarm clock entry from the ANIO API."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    device_id: str = Field(default="", alias="deviceId")
    time: str = Field(default="00:00")
    days: list[str] = Field(default_factory=list)
    enabled: bool = Field(default=True, alias="isEnabled")
    label: str | None = None

    @field_validator("days", mode="before")
    @classmethod
    def validate_days(cls, v: object) -> list[str]:
        """Accept the API's weekday bitstring."""
        return parse_weekdays(v)


class TimeWindow(BaseModel):
    """Weekly time window from the ANIO API (silence or school way time)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    device_id: str = Field(default="", alias="deviceId")
    start_time: str = Field(default="00:00", alias="startTime")
    end_time: str = Field(default="00:00", alias="endTime")
    days: list[str] = Field(default_factory=list)
    enabled: bool = Field(default=True, alias="isEnabled")

    @field_validator("days", mode="before")
    @classmethod
    def validate_days(cls, v: object) -> list[str]:
        """Accept the API's weekday bitstring."""
        return parse_weekdays(v)

    def is_active(self, now: datetime) -> bool:
        """Return True if the window is running at the given local time.

        Args:
            now: The current local time.

        Returns:
            True while an enabled window covers the current time.
        """
        if not self.enabled:
            return False
        try:
            start = time.fromisoformat(self.start_time)
            end = time.fromisoformat(self.end_time)
        except ValueError:
            return False

        def runs_on(day: datetime) -> bool:
            return WEEKDAYS[(day.weekday() + 1) % 7] in self.days

        current = now.time()
        if start <= end:
            return start <= current < end and runs_on(now)
        # Past midnight, the window started on the previous day
        if current >= start:
            return runs_on(now)
        return current < end and runs_on(now - timedelta(days=1))


class SilenceTime(TimeWindow):
    """Silence time entry from the ANIO API."""


class SchoolWayTime(TimeWindow):
    """School way time entry; the watch locates every minute meanwhile."""


class AnioDeviceState(BaseModel):
    """Combined state for an ANIO device."""

    model_config = ConfigDict(populate_by_name=True)

    device: Device
    location: LocationInfo | None = None
    geofences: list[Geofence] = Field(default_factory=list)
    last_seen: datetime | None = None
    is_online: bool = False
    # None (unknown) when the API has no last location for the device
    battery_level_value: int | None = None
    signal_strength: int | None = None
    last_message: ChatMessage | None = None
    alarms: list[AlarmClock] = Field(default_factory=list)
    silence_times: list[SilenceTime] = Field(default_factory=list)
    school_way_times: list[SchoolWayTime] = Field(default_factory=list)
    tracking_mode: str | None = None

    @property
    def battery_level(self) -> int | None:
        """Get battery level from location data."""
        return self.battery_level_value

    @property
    def name(self) -> str:
        """Get device name."""
        return self.device.settings.name
