# Research: ANIO Smartwatch Home Assistant Integration

**Date**: 2026-01-22
**Branch**: `001-anio-integration`

## 1. Home Assistant Integration Patterns

### Decision: DataUpdateCoordinator Pattern

**Rationale**: Der DataUpdateCoordinator ist der empfohlene Ansatz für Integrationen, die Daten von einer API abrufen. Er bietet:
- Zentralisiertes Polling mit einem einzigen API-Call pro Intervall
- Automatisches Error-Handling und Retry-Logik
- Effiziente Entity-Updates nur bei Datenänderungen
- Native Integration mit Home Assistant's Event Loop

**Alternatives Considered**:
- Direct Entity Polling: Jede Entity pollt selbst → Abgelehnt wegen API-Rate-Limits
- Push-basiert via WebSocket: ANIO API bietet kein WebSocket → Nicht verfügbar

### Decision: Config Flow mit Options Flow

**Rationale**:
- Config Flow ermöglicht UI-basierte Einrichtung ohne YAML
- Options Flow erlaubt nachträgliche Anpassung des Polling-Intervalls
- 2FA-Unterstützung über separaten Config Flow Step

**Implementation**:
```python
class AnioConfigFlow(ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        # Email/Password Step

    async def async_step_2fa(self, user_input=None):
        # OTP Code Step (wenn isOtpCodeRequired=true)
```

### Decision: Entity Description Pattern

**Rationale**: EntityDescription-Klassen ermöglichen deklarative Entity-Definition mit weniger Boilerplate.

**Implementation**:
```python
SENSOR_DESCRIPTIONS = [
    AnioSensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.battery_level,
    ),
]
```

## 2. ANIO Cloud API Integration

### Decision: aiohttp für HTTP-Client

**Rationale**:
- Native async/await Unterstützung
- Bereits in Home Assistant Core verwendet
- Keine zusätzliche Dependency

**Alternatives Considered**:
- httpx: Bessere API, aber zusätzliche Dependency → Abgelehnt
- requests: Synchron, würde Event Loop blockieren → Abgelehnt

### Decision: JWT Token Management

**Rationale**: Die ANIO API verwendet JWT mit:
- Access Token: ~15 Minuten Gültigkeit
- Refresh Token: ~1 Jahr Gültigkeit

**Implementation**:
- Token-Expiry aus JWT-Payload parsen (ohne Verifizierung)
- Proaktiver Refresh 5 Minuten vor Ablauf
- Refresh Token in Home Assistant's `config_entry.data` speichern

```python
class AnioAuth:
    async def ensure_valid_token(self) -> str:
        if self._token_expires_soon():
            await self._refresh_token()
        return self._access_token
```

### Decision: App-UUID Generierung

**Rationale**: ANIO API erfordert eine eindeutige `app-uuid` pro Installation.

**Implementation**: UUID wird beim ersten Config Flow generiert und in `config_entry.data` gespeichert.

### Decision: Activity Polling für eingehende Nachrichten

**Rationale**: Die `/v1/activity` API liefert alle Aktivitäten inkl. Chat-Nachrichten.

**Implementation**:
- Polling zusammen mit Device-Daten im Coordinator
- Neue Nachrichten werden als Events gefeuert
- Letzte bekannte Nachricht-ID tracken um Duplikate zu vermeiden

## 3. HACS Requirements

### Decision: Repository Struktur

**Rationale**: HACS erfordert spezifische Struktur für Custom Integrations.

**Required Files**:
```
custom_components/anio/
├── manifest.json       # HACS/HA metadata
├── __init__.py         # Entry point
├── strings.json        # English strings
└── translations/       # Additional languages
```

### Decision: manifest.json

```json
{
  "domain": "anio",
  "name": "ANIO Smartwatch",
  "codeowners": ["@username"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/...",
  "integration_type": "hub",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/.../issues",
  "requirements": ["aiohttp>=3.8.0"],
  "version": "1.0.0"
}
```

### Decision: HACS hacs.json

```json
{
  "name": "ANIO Smartwatch",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
```

## 4. Entity Mapping

### Decision: Entity Types

| ANIO Data | HA Entity Type | Rationale |
|-----------|---------------|-----------|
| Battery % | sensor (battery) | Standard device class |
| Online Status | binary_sensor | On/Off state |
| Step Count | sensor | Numeric measurement |
| Last Seen | sensor (timestamp) | DateTime state |
| GPS Location | device_tracker | Standard location tracking |
| Geofence State | binary_sensor | In/Out of zone |
| Locate Button | button | One-shot action |
| Power Off Button | button | One-shot action (with warning) |
| Messages | notify | Service-based |
| Incoming Messages | event | For automations |

### Decision: Unique ID Format

**Format**: `anio_{device_id}_{entity_type}`

**Examples**:
- `anio_4645a84ad7_battery`
- `anio_4645a84ad7_location`
- `anio_4645a84ad7_online`

## 5. Error Handling

### Decision: Error Hierarchy

```python
class AnioApiError(Exception): pass
class AnioAuthError(AnioApiError): pass
class AnioRateLimitError(AnioApiError): pass
class AnioConnectionError(AnioApiError): pass
```

### Decision: Rate Limit Handling

**Implementation**:
- Bei HTTP 429: Exponential Backoff (2^n Sekunden, max 5 Minuten)
- Coordinator setzt `UpdateFailed` mit retry_after

### Decision: Auth Error Recovery

**Implementation**:
- Bei HTTP 401: ConfigEntryAuthFailed werfen
- Triggert automatischen Reauth-Flow in Home Assistant

## 6. Testing Strategy

### Decision: pytest-homeassistant-custom-component

**Rationale**: Offizielles Test-Framework für HA Custom Components mit:
- Vorkonfigurierte Fixtures (`hass`, `mock_config_entry`)
- Async Test Support
- Snapshot Testing für Entities

### Decision: aioresponses für API Mocking

**Rationale**: Ermöglicht Mocking von aiohttp-Requests ohne echte Netzwerkaufrufe.

```python
@pytest.fixture
def mock_anio_api():
    with aioresponses() as m:
        m.post(API_URL + "/v1/auth/login", payload={"accessToken": "...", "refreshToken": "..."})
        m.get(API_URL + "/v1/device/list", payload=[...])
        yield m
```
