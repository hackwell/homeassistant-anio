# Implementation Plan: ANIO Smartwatch Home Assistant Integration

**Branch**: `001-anio-integration` | **Date**: 2026-01-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-anio-integration/spec.md`

## Summary

Eine HACS-kompatible Home Assistant Integration für ANIO Kinder-Smartwatches. Die Integration ermöglicht Statusüberwachung (Batterie, Standort, Online-Status, Schritte), bidirektionale Messaging-Funktionen, Standortverfolgung via Device Tracker und Gerätesteuerung. Technisch basierend auf der ANIO Cloud REST API mit JWT-Authentifizierung und dem Home Assistant DataUpdateCoordinator-Pattern für effizientes Polling.

## Technical Context

**Language/Version**: Python 3.11+ (Home Assistant Minimum)
**Primary Dependencies**: aiohttp (async HTTP), homeassistant (core), pydantic (models)
**Storage**: Home Assistant Config Entries (keine externe Datenbank)
**Testing**: pytest, pytest-homeassistant-custom-component, pytest-aiohttp
**Target Platform**: Home Assistant 2024.1+ (alle HA-unterstützten Plattformen)
**Project Type**: Custom Integration (HACS)
**Performance Goals**: 5-Minuten-Polling (konfigurierbar), <50MB RAM bei 5 Uhren, <5s Startup
**Constraints**: Max 300s Polling-Intervall, proaktives Token-Refresh, Exponential Backoff bei 429
**Scale/Scope**: Bis zu 10 Uhren pro Account, ~20 Entities pro Uhr

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Quality ✅

| Requirement | Implementation |
|-------------|----------------|
| `ruff` linting | CI/pre-commit mit HA-Konfiguration |
| `mypy` strict | Alle Funktionen mit Type Hints |
| async/await | aiohttp für alle API-Calls |
| Separated API client | `custom_components/anio/api/` Modul |
| Config Flow | `config_flow.py` mit 2FA-Support |
| Translatable strings | `strings.json` + `translations/` |

### II. Testing Standards ✅

| Requirement | Implementation |
|-------------|----------------|
| ≥80% coverage | pytest-cov Enforcement |
| Mocked API calls | aioresponses für alle Tests |
| HA test fixtures | `hass`, `mock_config_entry` |
| Error path tests | Auth-Fehler, Netzwerk, Rate-Limit |
| Config flow tests | Alle Pfade inkl. 2FA |

### III. User Experience Consistency ✅

| Requirement | Implementation |
|-------------|----------------|
| Entity naming | `sensor.anio_{name}_battery` etc. |
| Device info | Manufacturer: ANIO, Model: Gen X, FW: version |
| 2FA handling | Separater Config Flow Step mit OTP-Input |
| Friendly errors | `strings.json` Fehlermeldungen |
| 60s update max | DataUpdateCoordinator mit 60-300s |

### IV. Performance Requirements ✅

| Requirement | Implementation |
|-------------|----------------|
| Configurable polling | Options Flow: 60-300s |
| Exponential backoff | `aiohttp` retry mit 2^n |
| Proactive token refresh | Refresh bei <5min vor Ablauf |
| Coordinator pattern | Single `AnioDataUpdateCoordinator` |
| Memory stable | Keine Speicherlecks, geprüft via Tests |
| <10s startup | Async setup, kein blocking I/O |

**Gate Status**: ✅ PASSED - Keine Violations

## Project Structure

### Documentation (this feature)

```text
specs/001-anio-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
custom_components/anio/
├── __init__.py          # Integration setup, coordinator init
├── config_flow.py       # UI configuration with 2FA
├── const.py             # Constants, configuration keys
├── coordinator.py       # AnioDataUpdateCoordinator
├── entity.py            # AnioEntity base class
├── sensor.py            # Battery, steps, last_seen sensors
├── binary_sensor.py     # Online status, geofence sensors
├── device_tracker.py    # GPS location tracking
├── button.py            # Locate, power off buttons
├── notify.py            # Send messages service
├── manifest.json        # Integration metadata
├── strings.json         # English strings
├── services.yaml        # Service definitions
├── translations/
│   └── de.json          # German translations
└── api/
    ├── __init__.py      # Public exports
    ├── client.py        # AnioApiClient class
    ├── auth.py          # Token management, refresh
    ├── models.py        # Pydantic response models
    └── exceptions.py    # AnioApiError, AuthError, etc.

tests/
├── conftest.py          # Shared fixtures
├── test_config_flow.py  # Config flow tests
├── test_coordinator.py  # Coordinator tests
├── test_sensor.py       # Sensor entity tests
├── test_binary_sensor.py
├── test_device_tracker.py
├── test_button.py
├── test_notify.py
└── api/
    ├── test_client.py   # API client tests
    ├── test_auth.py     # Auth/token tests
    └── test_models.py   # Model validation tests
```

**Structure Decision**: Home Assistant Custom Integration Struktur nach HACS-Standard. API-Client als separates Submodul für Testbarkeit und potenzielle Wiederverwendung. Tests spiegeln die Modulstruktur.

## Complexity Tracking

> Keine Violations - Complexity Tracking nicht erforderlich.

## Phase 0: Research Completed

Siehe [research.md](./research.md) für Details zu:
- Home Assistant Integration Patterns (Config Flow, Coordinator, Entities)
- ANIO API Authentication (JWT, 2FA, Token Refresh)
- HACS Requirements und Best Practices

## Phase 1: Design Artifacts

- [data-model.md](./data-model.md) - Entity-Definitionen und Datenstrukturen
- [contracts/](./contracts/) - API-Contracts basierend auf ANIO Cloud API
- [quickstart.md](./quickstart.md) - Schnellstart für Entwickler
