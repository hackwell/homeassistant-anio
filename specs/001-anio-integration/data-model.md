# Data Model: ANIO Smartwatch Home Assistant Integration

**Date**: 2026-01-22
**Branch**: `001-anio-integration`

## Core Entities

### AnioDevice

Repräsentiert eine einzelne ANIO Kinder-Smartwatch.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| id | string | API `device.id` | Eindeutige Geräte-ID (z.B. "4645a84ad7") |
| imei | string | API `device.imei` | IMEI der SIM-Karte |
| name | string | API `device.settings.name` | Benutzerdefinierter Name (z.B. "Marla") |
| generation | string | API `device.config.generation` | Hardware-Generation (z.B. "6") |
| firmware_version | string | API `device.config.firmwareVersion` | Firmware (z.B. "ANIO6_Kids_V2.00.12.B") |
| hex_color | string | API `device.settings.hexColor` | Zugewiesene Farbe (z.B. "#E7451B") |
| phone_number | string | API `device.settings.phoneNr` | SIM-Telefonnummer |

**Validation Rules**:
- `id` MUST be non-empty string
- `generation` MUST be parseable as integer
- `hex_color` MUST be valid hex color code

**State**: Immutable during session (nur Config-Daten)

---

### AnioDeviceState

Aktueller Status einer Uhr (wird bei jedem Polling aktualisiert).

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| device_id | string | Reference | Referenz auf AnioDevice.id |
| battery_level | int | API `device.settings.battery` | Batteriestand in % (0-100) |
| is_online | bool | Derived | Abgeleitet aus letzter Aktivität |
| step_count | int | API `device.settings.stepCount` | Tägliche Schritte |
| last_seen | datetime | API `activity.timestamp` | Letzter bekannter Kontakt |
| latitude | float | API `location.lat` | GPS Breitengrad |
| longitude | float | API `location.lng` | GPS Längengrad |
| location_accuracy | int | API `location.accuracy` | GPS Genauigkeit in Metern |
| location_timestamp | datetime | API `location.timestamp` | Zeitpunkt der Ortung |

**Validation Rules**:
- `battery_level` MUST be 0-100
- `step_count` MUST be >= 0
- `latitude` MUST be -90 to 90
- `longitude` MUST be -180 to 180

**State Transitions**:
- `is_online`: true → false wenn last_seen > 10 Minuten alt
- `battery_level`: Kann nur sinken oder bei Laden steigen
- `step_count`: Wird täglich zurückgesetzt (Mitternacht Gerätezeit)

---

### AnioGeofence

Ein in der ANIO-App konfigurierter Geofence.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| id | string | API `geofence.id` | Eindeutige Geofence-ID |
| name | string | API `geofence.name` | Benutzerfreundlicher Name |
| latitude | float | API `geofence.lat` | Mittelpunkt Breitengrad |
| longitude | float | API `geofence.lng` | Mittelpunkt Längengrad |
| radius | int | API `geofence.radius` | Radius in Metern |
| is_device_inside | bool | Derived | Ob Gerät aktuell in Zone |

**State Transitions**:
- `is_device_inside`: Berechnet aus Distanz Gerät ↔ Geofence-Mittelpunkt

---

### AnioChatMessage

Eine Chat-Nachricht (eingehend oder ausgehend).

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| id | string | API `message.id` | Eindeutige Nachrichten-ID |
| device_id | string | API `message.deviceId` | Ziel/Quell-Gerät |
| message_type | enum | API `message.type` | TEXT, EMOJI, VOICE |
| sender | enum | API `message.sender` | APP oder WATCH |
| content | string | API `message.text` | Nachrichteninhalt |
| username | string | API `message.username` | Absendername |
| is_received | bool | API `message.isReceived` | Uhr hat empfangen |
| is_read | bool | API `message.isRead` | Auf Uhr gelesen |
| created_at | datetime | API `message.createdAt` | Erstellungszeitpunkt |

**Validation Rules**:
- `content` max length: 95 Zeichen (device-abhängig)
- `message_type` MUST be one of: TEXT, EMOJI, VOICE
- `sender` MUST be one of: APP, WATCH

---

## API Response Models (Pydantic)

### AuthTokens

```python
class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    is_otp_required: bool = False
    token_expiry: datetime | None = None  # Parsed from JWT
```

### DeviceConfig

```python
class DeviceConfig(BaseModel):
    generation: str
    type: Literal["WATCH"]
    firmware_version: str
    max_chat_message_length: int = 95
    max_phonebook_entries: int = 20
    max_geofences: int = 5
    has_text_chat: bool = True
    has_voice_chat: bool = True
    has_emojis: bool = True
    has_step_counter: bool = True
    has_locating_switch: bool = True
```

### DeviceSettings

```python
class DeviceSettings(BaseModel):
    name: str
    hex_color: str
    phone_nr: str | None = None
    gender: Literal["MALE", "FEMALE"] | None = None
    step_target: int = 10000
    is_locating_active: bool = True
    ring_profile: str = "RING_AND_VIBRATE"
```

### Device

```python
class Device(BaseModel):
    id: str
    imei: str
    config: DeviceConfig
    settings: DeviceSettings
    user: UserInfo
```

### ChatMessage

```python
class ChatMessage(BaseModel):
    id: str
    device_id: str
    text: str
    username: str | None = None
    type: Literal["TEXT", "EMOJI", "VOICE"]
    sender: Literal["APP", "WATCH"]
    is_received: bool = False
    is_read: bool = False
    created_at: datetime
```

### Geofence

```python
class Geofence(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    radius: int  # meters
```

---

## Home Assistant Entity Mapping

### Device Registry

```python
device_info = DeviceInfo(
    identifiers={(DOMAIN, device.id)},
    name=device.settings.name,
    manufacturer="ANIO",
    model=f"Generation {device.config.generation}",
    sw_version=device.config.firmware_version,
)
```

### Sensor Entities

| Entity | Device Class | Unit | State Class | Value Source |
|--------|--------------|------|-------------|--------------|
| Battery | battery | % | measurement | device_state.battery_level |
| Steps | None | steps | total_increasing | device_state.step_count |
| Last Seen | timestamp | None | None | device_state.last_seen |

### Binary Sensor Entities

| Entity | Device Class | On Meaning | Value Source |
|--------|--------------|------------|--------------|
| Online | connectivity | Connected | device_state.is_online |
| Geofence {name} | presence | In Zone | geofence.is_device_inside |

### Device Tracker

| Attribute | Value Source |
|-----------|--------------|
| latitude | device_state.latitude |
| longitude | device_state.longitude |
| gps_accuracy | device_state.location_accuracy |
| source_type | gps |

### Button Entities

| Entity | Action | Confirmation |
|--------|--------|--------------|
| Locate | POST /v1/device/{id}/find | None |
| Power Off | POST /v1/device/{id}/poweroff | Warning in description |

### Notify Service

```yaml
service: notify.anio_{device_name}
data:
  message: "Hello World"
  data:
    message_type: text  # or emoji
    emoji_code: E01     # only for emoji type
```

### Event

```yaml
event_type: anio_message_received
event_data:
  device_id: "4645a84ad7"
  device_name: "Marla"
  message_type: "TEXT"
  content: "Hallo Mama!"
  sender: "WATCH"
  timestamp: "2026-01-22T15:30:00Z"
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Home Assistant                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              AnioDataUpdateCoordinator                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │ Device List │  │ Activity    │  │ Geofences       │   │  │
│  │  │ Polling     │  │ Polling     │  │ Polling         │   │  │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘   │  │
│  │         │                │                   │            │  │
│  │         └────────────────┼───────────────────┘            │  │
│  │                          │                                 │  │
│  │                    ┌─────▼─────┐                          │  │
│  │                    │ AnioApi   │                          │  │
│  │                    │ Client    │                          │  │
│  │                    └─────┬─────┘                          │  │
│  └──────────────────────────┼────────────────────────────────┘  │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │ HTTPS
                              ▼
                    ┌─────────────────┐
                    │ api.anio.cloud  │
                    │ (REST API v1)   │
                    └─────────────────┘
```
