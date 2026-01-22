"""Pydantic models for the ANIO API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AuthTokens(BaseModel):
    """Authentication tokens from the ANIO API."""

    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    is_otp_required: bool = Field(default=False, alias="isOtpCodeRequired")


class DeviceConfig(BaseModel):
    """Device configuration from the ANIO API."""

    generation: str
    type: Literal["WATCH"] = "WATCH"
    firmware_version: str = Field(alias="firmwareVersion")
    max_chat_message_length: int = Field(default=95, alias="maxChatMessageLength")
    max_phonebook_entries: int = Field(default=20, alias="maxPhonebookEntries")
    max_geofences: int = Field(default=5, alias="maxGeofences")
    has_text_chat: bool = Field(default=True, alias="hasTextChat")
    has_voice_chat: bool = Field(default=True, alias="hasVoiceChat")
    has_emojis: bool = Field(default=True, alias="hasEmojis")
    has_step_counter: bool = Field(default=True, alias="hasStepCounter")
    has_locating_switch: bool = Field(default=True, alias="hasLocatingSwitch")


class DeviceSettings(BaseModel):
    """Device settings from the ANIO API."""

    name: str
    hex_color: str = Field(alias="hexColor")
    phone_nr: str | None = Field(default=None, alias="phoneNr")
    gender: Literal["MALE", "FEMALE"] | None = None
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

    id: str
    imei: str
    config: DeviceConfig
    settings: DeviceSettings
    user: UserInfo | None = None


class ChatMessage(BaseModel):
    """Chat message from the ANIO API."""

    id: str
    device_id: str = Field(alias="deviceId")
    text: str
    username: str | None = None
    type: Literal["TEXT", "EMOJI", "VOICE"]
    sender: Literal["APP", "WATCH"]
    is_received: bool = Field(default=False, alias="isReceived")
    is_read: bool = Field(default=False, alias="isRead")
    created_at: datetime = Field(alias="createdAt")


class Geofence(BaseModel):
    """Geofence from the ANIO API."""

    id: str
    name: str
    latitude: float = Field(alias="lat")
    longitude: float = Field(alias="lng")
    radius: int

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        """Validate latitude is between -90 and 90."""
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        """Validate longitude is between -180 and 180."""
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


class LocationInfo(BaseModel):
    """Location information from the ANIO API."""

    latitude: float = Field(alias="lat")
    longitude: float = Field(alias="lng")
    accuracy: int = Field(default=0)
    timestamp: datetime | None = None


class ActivityItem(BaseModel):
    """Activity item from the ANIO API feed."""

    id: str
    device_id: str = Field(alias="deviceId")
    type: str
    timestamp: datetime
    data: dict | None = None


class AnioDeviceState(BaseModel):
    """Combined state for an ANIO device."""

    device: Device
    location: LocationInfo | None = None
    geofences: list[Geofence] = Field(default_factory=list)
    last_seen: datetime | None = None
    is_online: bool = False

    @property
    def battery_level(self) -> int:
        """Get battery level."""
        return self.device.settings.battery

    @property
    def step_count(self) -> int:
        """Get step count."""
        return self.device.settings.step_count

    @property
    def name(self) -> str:
        """Get device name."""
        return self.device.settings.name
