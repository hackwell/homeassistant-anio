# Tasks: ANIO Smartwatch Home Assistant Integration

**Input**: Design documents from `/specs/001-anio-integration/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/

**Tests**: Tests are included following the Constitution requirement of ≥80% coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Custom Component**: `custom_components/anio/`
- **API Module**: `custom_components/anio/api/`
- **Tests**: `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md (`custom_components/anio/`, `tests/`)
- [x] T002 [P] Create `custom_components/anio/manifest.json` with HACS-compatible metadata
- [x] T003 [P] Create `custom_components/anio/const.py` with DOMAIN, API_URL, DEFAULT_SCAN_INTERVAL
- [x] T004 [P] Create `pyproject.toml` with dev dependencies (pytest, pytest-homeassistant-custom-component, ruff, mypy)
- [x] T005 [P] Create `hacs.json` in repository root for HACS compatibility
- [x] T006 [P] Create `.github/workflows/tests.yml` for CI/CD pipeline

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### API Client Layer

- [x] T007 Create `custom_components/anio/api/exceptions.py` with AnioApiError, AnioAuthError, AnioRateLimitError
- [x] T008 Create `custom_components/anio/api/models.py` with Pydantic models (AuthTokens, DeviceConfig, DeviceSettings, Device, ChatMessage, Geofence)
- [x] T009 Create `custom_components/anio/api/auth.py` with AnioAuth class (login, refresh, JWT parsing)
- [x] T010 Create `custom_components/anio/api/client.py` with AnioApiClient (get_devices, get_device, find_device, power_off_device, send_text_message, send_emoji_message, get_activity, get_geofences)
- [x] T011 [P] Create `custom_components/anio/api/__init__.py` with exports

### Home Assistant Integration Core

- [x] T012 Create `custom_components/anio/coordinator.py` with AnioDataUpdateCoordinator (DataUpdateCoordinator pattern)
- [x] T013 Create `custom_components/anio/config_flow.py` with multi-step flow (user → 2fa → complete)
- [x] T014 Create `custom_components/anio/entity.py` with base AnioEntity class (CoordinatorEntity)
- [x] T015 Create `custom_components/anio/__init__.py` with async_setup_entry, async_unload_entry

### Test Infrastructure

- [x] T016 [P] Create `tests/conftest.py` with HA fixtures, mock API client, mock config entry
- [x] T017 [P] Create `tests/api/test_auth.py` with auth tests (login, refresh, 2FA)
- [x] T018 [P] Create `tests/api/test_client.py` with API client tests (mocked responses)
- [x] T019 [P] Create `tests/test_config_flow.py` with config flow tests (success, 2FA, errors)
- [x] T020 Create `tests/test_coordinator.py` with coordinator tests (polling, error handling)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Uhr einrichten und Status sehen (Priority: P1) 🎯 MVP

**Goal**: Users can add their ANIO watch to Home Assistant and see battery, online status, and last seen

**Independent Test**: Add integration via UI, verify all status sensors show correct values

### Tests for User Story 1

- [x] T021 [P] [US1] Create `tests/test_sensor.py` with battery and last_seen sensor tests
- [x] T022 [P] [US1] Create `tests/test_binary_sensor.py` with online status sensor tests
- [x] T023 [P] [US1] Create `tests/test_init.py` with integration setup/unload tests

### Implementation for User Story 1

- [x] T024 [P] [US1] Create `custom_components/anio/sensor.py` with AnioBatterySensor (device_class=battery, unit=%)
- [x] T025 [P] [US1] Create `custom_components/anio/sensor.py` add AnioLastSeenSensor (device_class=timestamp)
- [x] T026 [US1] Create `custom_components/anio/binary_sensor.py` with AnioOnlineSensor (device_class=connectivity)
- [x] T027 [US1] Update `custom_components/anio/__init__.py` to register sensor and binary_sensor platforms
- [x] T028 [US1] Create `custom_components/anio/strings.json` with config_flow strings and error messages

**Checkpoint**: User Story 1 complete - watch setup and status monitoring works

---

## Phase 4: User Story 2 - Nachrichten an die Uhr senden (Priority: P2)

**Goal**: Users can send text and emoji messages to the watch, and receive messages as HA events

**Independent Test**: Send message via service call, verify arrival on watch; send message from watch, verify HA event fires

### Tests for User Story 2

- [x] T029 [P] [US2] Create `tests/test_notify.py` with notify service tests (text, emoji, validation)
- [x] T030 [P] [US2] Add event firing tests to `tests/test_coordinator.py`

### Implementation for User Story 2

- [x] T031 [US2] Create `custom_components/anio/notify.py` with AnioNotifyEntity (send_message with text/emoji support)
- [x] T032 [US2] Create `custom_components/anio/services.yaml` with send_message service schema
- [x] T033 [US2] Update coordinator to poll activity feed and detect new incoming messages
- [x] T034 [US2] Implement `anio_message_received` event firing in coordinator (per ha-events.yaml contract)
- [x] T035 [US2] Update `custom_components/anio/__init__.py` to register notify platform
- [x] T036 [US2] Update `custom_components/anio/strings.json` with message-related strings

**Checkpoint**: User Story 2 complete - bidirectional messaging works

---

## Phase 5: User Story 3 - Standortverfolgung auf der Karte (Priority: P3)

**Goal**: Users can see watch location on map and trigger manual location request

**Independent Test**: Open HA map, verify watch location; press locate button, verify update

### Tests for User Story 3

- [x] T037 [P] [US3] Create `tests/test_device_tracker.py` with location tracker tests
- [x] T038 [P] [US3] Create `tests/test_button.py` with locate button tests

### Implementation for User Story 3

- [x] T039 [US3] Create `custom_components/anio/device_tracker.py` with AnioDeviceTracker (source_type=gps)
- [x] T040 [US3] Create `custom_components/anio/button.py` with AnioLocateButton (calls find_device API)
- [x] T041 [US3] Update `custom_components/anio/__init__.py` to register device_tracker and button platforms
- [x] T042 [US3] Update `custom_components/anio/strings.json` with location-related strings

**Checkpoint**: User Story 3 complete - location tracking and manual locate works

---

## Phase 6: User Story 4 - Schrittzähler und Aktivitätsdaten (Priority: P4)

**Goal**: Users can see daily step count, geofence status, and power off the watch

**Independent Test**: Verify step count sensor matches ANIO app; verify geofence sensors; test power off button

### Tests for User Story 4

- [x] T043 [P] [US4] Add step counter tests to `tests/test_sensor.py`
- [x] T044 [P] [US4] Add geofence sensor tests to `tests/test_binary_sensor.py`
- [x] T045 [P] [US4] Add power off button tests to `tests/test_button.py`

### Implementation for User Story 4

- [x] T046 [US4] Add AnioStepsSensor to `custom_components/anio/sensor.py` (state_class=total_increasing)
- [x] T047 [US4] Add AnioGeofenceSensor to `custom_components/anio/binary_sensor.py` (device_class=presence, one per geofence)
- [x] T048 [US4] Add AnioPowerOffButton to `custom_components/anio/button.py` with warning in entity description
- [x] T049 [US4] Update coordinator to fetch geofences and calculate is_device_inside
- [x] T050 [US4] Update `custom_components/anio/strings.json` with step and geofence strings

**Checkpoint**: User Story 4 complete - all sensors and controls work

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T051 [P] Create `custom_components/anio/translations/de.json` for German translations
- [x] T052 [P] Create `custom_components/anio/translations/en.json` for English translations
- [ ] T053 [P] Create `README.md` with installation instructions, features, and configuration guide
- [ ] T054 Run `ruff check custom_components/anio` and fix all linting issues
- [ ] T055 Run `mypy custom_components/anio` and fix all type errors
- [ ] T056 Run `pytest --cov=custom_components/anio` and ensure ≥80% coverage
- [x] T057 [P] Create `info.md` for HACS repository page
- [ ] T058 Validate integration using Home Assistant development container
- [ ] T059 Run quickstart.md validation (full developer workflow test)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Coordinator from US1 must exist but can develop in parallel
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Extends US1 sensors, can develop in parallel

### Within Each User Story

- Tests SHOULD be written first (TDD approach per Constitution)
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational API tasks (T007-T011) should be sequential (dependencies)
- Test infrastructure tasks (T016-T020) can run in parallel after coordinator
- Once Foundational phase completes, all user stories can start in parallel
- All tests within a story marked [P] can run in parallel
- Translation and documentation tasks in Polish phase can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test integration in HA development container
5. Deploy/demo if ready (basic integration works)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → MVP ready (status monitoring)
3. Add User Story 2 → Test independently → Messaging works
4. Add User Story 3 → Test independently → Location tracking works
5. Add User Story 4 → Test independently → Full feature set
6. Complete Polish → Production ready for HACS

### Task Count Summary

| Phase | Task Count | Parallelizable |
|-------|------------|----------------|
| Setup | 6 | 5 |
| Foundational | 14 | 6 |
| User Story 1 | 8 | 5 |
| User Story 2 | 8 | 2 |
| User Story 3 | 6 | 2 |
| User Story 4 | 8 | 3 |
| Polish | 9 | 5 |
| **Total** | **59** | **28** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Constitution requires: ruff + mypy clean, ≥80% test coverage
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
