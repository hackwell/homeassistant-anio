# Quickstart: ANIO Home Assistant Integration Development

## Prerequisites

- Python 3.11+
- Home Assistant Core development environment
- ANIO Cloud account with at least one registered watch
- Git

## 1. Clone and Setup

```bash
# Clone repository
git clone <repo-url>
cd anio-ha-integration

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

## 2. Project Structure

```
custom_components/anio/
├── __init__.py          # async_setup_entry, async_unload_entry
├── config_flow.py       # UI configuration
├── coordinator.py       # DataUpdateCoordinator
├── entity.py            # Base AnioEntity
├── sensor.py            # Battery, steps, last_seen
├── binary_sensor.py     # Online, geofence
├── device_tracker.py    # Location
├── button.py            # Locate, power off
├── notify.py            # Messaging
├── manifest.json
├── strings.json
└── api/
    ├── client.py        # AnioApiClient
    ├── auth.py          # Token management
    ├── models.py        # Pydantic models
    └── exceptions.py    # Error classes
```

## 3. Run Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=custom_components/anio --cov-report=html

# Specific test file
pytest tests/test_config_flow.py -v
```

## 4. Local Development with Home Assistant

```bash
# Option A: Use container
docker run -d \
  --name hass \
  -v $(pwd)/custom_components:/config/custom_components \
  -p 8123:8123 \
  homeassistant/home-assistant

# Option B: Use HA Core dev container
# See: https://developers.home-assistant.io/docs/development_environment
```

## 5. Lint and Type Check

```bash
# Lint with ruff
ruff check custom_components/anio

# Type check with mypy
mypy custom_components/anio
```

## 6. Key Implementation Steps

### Step 1: API Client

```python
# api/client.py
class AnioApiClient:
    def __init__(self, session: aiohttp.ClientSession, auth: AnioAuth):
        self._session = session
        self._auth = auth

    async def get_devices(self) -> list[Device]:
        token = await self._auth.ensure_valid_token()
        async with self._session.get(
            f"{API_URL}/v1/device/list",
            headers={"Authorization": f"Bearer {token}"}
        ) as resp:
            data = await resp.json()
            return [Device.model_validate(d) for d in data]
```

### Step 2: Coordinator

```python
# coordinator.py
class AnioDataUpdateCoordinator(DataUpdateCoordinator[dict[str, AnioDeviceState]]):
    def __init__(self, hass: HomeAssistant, client: AnioApiClient):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, AnioDeviceState]:
        try:
            devices = await self.client.get_devices()
            return {d.id: self._to_state(d) for d in devices}
        except AnioAuthError as err:
            raise ConfigEntryAuthFailed from err
        except AnioApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
```

### Step 3: Config Flow

```python
# config_flow.py
class AnioConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            try:
                result = await self._try_login(user_input)
                if result.is_otp_required:
                    self._credentials = user_input
                    return await self.async_step_2fa()
                return self.async_create_entry(...)
            except AnioAuthError:
                errors["base"] = "invalid_auth"
        return self.async_show_form(step_id="user", errors=errors)

    async def async_step_2fa(self, user_input=None):
        # Handle OTP input
        ...
```

### Step 4: Entities

```python
# sensor.py
class AnioBatterySensor(AnioEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int | None:
        return self.device_state.battery_level
```

## 7. Testing Strategy

### Unit Tests (api/)

```python
# tests/api/test_client.py
async def test_get_devices(mock_anio_api):
    client = AnioApiClient(...)
    devices = await client.get_devices()
    assert len(devices) == 1
    assert devices[0].id == "4645a84ad7"
```

### Integration Tests (entities)

```python
# tests/test_sensor.py
async def test_battery_sensor(hass, mock_config_entry):
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.anio_marla_battery")
    assert state.state == "85"
```

### Config Flow Tests

```python
# tests/test_config_flow.py
async def test_config_flow_success(hass, mock_anio_api):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"email": "test@example.com", "password": "secret"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
```

## 8. HACS Publishing

1. Create GitHub repository
2. Add `hacs.json` to repo root:
   ```json
   {
     "name": "ANIO Smartwatch",
     "render_readme": true,
     "homeassistant": "2024.1.0"
   }
   ```
3. Add topics to repo: `hacs`, `home-assistant`, `home-assistant-custom-component`
4. Create release with semantic version tag (e.g., `v1.0.0`)
5. Submit to HACS default repository (optional)

## 9. Useful Links

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [HACS Developer Docs](https://hacs.xyz/docs/developer/start)
- [ANIO API Swagger](https://api.anio.cloud/api)
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamworthy/pytest-homeassistant-custom-component)
