<!--
Sync Impact Report
==================
Version change: 0.0.0 → 1.0.0 (MAJOR - initial constitution)
Modified principles: N/A (new document)
Added sections:
  - Core Principles (4 principles)
  - Home Assistant Integration Standards
  - Development Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ Compatible (Constitution Check section exists)
  - .specify/templates/spec-template.md: ✅ Compatible (Requirements section aligns)
  - .specify/templates/tasks-template.md: ✅ Compatible (Phase structure supports principles)
Follow-up TODOs: None
-->

# ANIO Home Assistant Integration Constitution

## Core Principles

### I. Code Quality

All code MUST adhere to Home Assistant development standards and Python best practices.

**Non-Negotiable Rules**:
- Code MUST pass `ruff` linting with Home Assistant configuration
- Code MUST pass `mypy` strict type checking - all functions require type hints
- All async operations MUST use `async`/`await` patterns correctly
- API client code MUST be separated from Home Assistant entity logic
- Configuration MUST use Home Assistant's config flow (no YAML-only setup)
- All strings visible to users MUST be translatable via `strings.json`

**Rationale**: Home Assistant has strict quality gates for core integrations. Following these standards from the start ensures potential future inclusion in HA core and maintains consistency with the ecosystem.

### II. Testing Standards

Every feature MUST have corresponding tests before implementation begins.

**Non-Negotiable Rules**:
- Test coverage MUST be ≥80% for all modules
- Unit tests MUST mock all external API calls - no real network requests
- Integration tests MUST use Home Assistant's test fixtures (`hass`, `mock_config_entry`)
- Tests MUST verify error handling paths (auth failures, network errors, API changes)
- Config flow MUST have complete test coverage including edge cases
- All tests MUST pass in CI before merge

**Rationale**: The ANIO API handles children's safety devices. Reliability is paramount - untested code paths could result in missed alerts or communication failures.

### III. User Experience Consistency

The integration MUST feel native to Home Assistant users.

**Non-Negotiable Rules**:
- Entity naming MUST follow HA conventions: `{domain}.anio_{device_name}_{entity_type}`
- Device info MUST populate manufacturer, model, firmware version from API
- Config flow MUST handle 2FA gracefully with clear user guidance
- All errors MUST display user-friendly messages (no raw API errors)
- Entity states MUST update within 60 seconds of real-world changes
- Services MUST use standard HA service call patterns with proper validation

**Rationale**: Users expect integrations to behave consistently. Non-standard patterns create confusion and support burden.

### IV. Performance Requirements

The integration MUST be resource-efficient and responsive.

**Non-Negotiable Rules**:
- Polling interval MUST be configurable (minimum 60 seconds, default 300 seconds)
- API calls MUST implement exponential backoff on rate limits (429 responses)
- Token refresh MUST happen proactively before expiry, not on failure
- Coordinator pattern MUST be used for data updates (single API call per interval)
- Memory footprint MUST remain stable over time (no leaks in long-running instances)
- Startup MUST NOT block Home Assistant boot for more than 10 seconds

**Rationale**: Home Assistant runs 24/7, often on low-power devices. Inefficient integrations degrade the entire system.

## Home Assistant Integration Standards

### Required Components

| Component | Purpose | Required |
|-----------|---------|----------|
| `__init__.py` | Integration setup, coordinator | Yes |
| `config_flow.py` | UI-based configuration | Yes |
| `const.py` | Constants and configuration keys | Yes |
| `coordinator.py` | Data update coordination | Yes |
| `entity.py` | Base entity class | Yes |
| `sensor.py` | Sensor entities (battery, location, etc.) | Yes |
| `manifest.json` | Integration metadata | Yes |
| `strings.json` | Translatable strings | Yes |
| `services.yaml` | Service definitions | If services provided |
| `device_tracker.py` | Location tracking | If location used |
| `notify.py` | Notification/messaging | If chat used |

### Entity Types

Based on ANIO API capabilities, the integration SHOULD expose:

- **Device Tracker**: Watch location (GPS coordinates)
- **Sensor**: Battery level, step count, last seen timestamp
- **Binary Sensor**: Online/offline status, geofence state
- **Notify**: Send text/emoji messages to watch
- **Button**: Locate device, power off (with confirmation)

### API Client Architecture

```
anio_api/
├── __init__.py      # Public exports
├── client.py        # AnioApiClient class
├── auth.py          # Token management
├── models.py        # Pydantic models for API responses
└── exceptions.py    # Custom exceptions
```

The API client MUST be usable independently of Home Assistant for testing and potential reuse.

## Development Workflow

### Quality Gates

Before any PR can be merged:

1. **Lint Check**: `ruff check .` passes with zero errors
2. **Type Check**: `mypy .` passes with zero errors
3. **Test Suite**: `pytest` passes with ≥80% coverage
4. **Config Flow Test**: All config flow paths tested
5. **Translation Check**: All user-facing strings in `strings.json`

### Branch Strategy

- `main`: Stable, release-ready code
- `develop`: Integration branch for features
- `feature/*`: Individual feature branches
- `fix/*`: Bug fix branches

### Commit Messages

Follow Conventional Commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

## Governance

This constitution establishes the foundational principles for the ANIO Home Assistant Integration project. All development decisions MUST align with these principles.

### Amendment Process

1. Propose amendment via pull request to this document
2. Document rationale for change
3. Update affected templates if principles change
4. Version bump follows semantic versioning:
   - MAJOR: Principle removal or fundamental redefinition
   - MINOR: New principle or significant expansion
   - PATCH: Clarification or typo fixes

### Compliance

- All PRs MUST pass quality gates defined in this constitution
- Code reviews MUST verify principle adherence
- Exceptions require documented justification in PR description

**Version**: 1.0.0 | **Ratified**: 2026-01-22 | **Last Amended**: 2026-01-22
