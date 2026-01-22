# ANIO Smartwatch Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/hackwell/homeassistant-anio.svg)](https://github.com/hackwell/homeassistant-anio/releases)
[![License](https://img.shields.io/github/license/hackwell/homeassistant-anio.svg)](LICENSE)

A Home Assistant custom integration for ANIO children's smartwatches. Monitor your child's watch status, location, and communicate directly through Home Assistant.

## Features

- **Status Monitoring** - Battery level, online status, last seen timestamp
- **Step Counter** - Daily step count with progress towards daily goal
- **Location Tracking** - Real-time GPS location displayed on the Home Assistant map
- **Geofence Sensors** - Binary sensors showing when the watch enters/leaves defined zones
- **Messaging** - Send text messages (up to 95 characters) and emoji messages to the watch
- **Message Events** - Receive Home Assistant events when messages arrive from the watch
- **Device Control** - Locate button to request immediate location update, Power Off button

## Supported Devices

- ANIO 5 Smartwatch
- ANIO 6 Smartwatch (Generation 6)

## Requirements

- Home Assistant 2024.1.0 or newer
- ANIO account (same credentials used in the ANIO mobile app)
- HACS (Home Assistant Community Store) for easy installation

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add `https://github.com/hackwell/homeassistant-anio` as a custom repository (Category: Integration)
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/hackwell/homeassistant-anio/releases)
2. Extract and copy the `custom_components/anio` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "ANIO Smartwatch"
4. Enter your ANIO account email and password
5. If two-factor authentication is enabled, enter the verification code sent to your email/phone
6. The integration will automatically discover all watches linked to your account

### Options

After setup, you can configure the following options:

| Option | Default | Description |
|--------|---------|-------------|
| Scan Interval | 300s | How often to poll the ANIO API (60-300 seconds) |

## Entities

For each watch, the integration creates the following entities:

### Sensors

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.<name>_battery` | Sensor | Battery percentage (0-100%) |
| `sensor.<name>_steps` | Sensor | Daily step count |
| `sensor.<name>_last_seen` | Sensor | Timestamp of last communication |

### Binary Sensors

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.<name>_online` | Binary Sensor | Whether watch is currently online |
| `binary_sensor.<name>_at_<geofence>` | Binary Sensor | One per geofence, shows presence |

### Device Tracker

| Entity | Type | Description |
|--------|------|-------------|
| `device_tracker.<name>_location` | Device Tracker | GPS location for map display |

### Buttons

| Entity | Type | Description |
|--------|------|-------------|
| `button.<name>_locate` | Button | Request immediate location update |
| `button.<name>_power_off` | Button | Remotely power off the watch |

### Notify

| Entity | Type | Description |
|--------|------|-------------|
| `notify.<name>_message` | Notify | Send messages to the watch |

## Services

### Send Message

Send a text or emoji message to the watch.

```yaml
service: notify.<watch_name>_message
data:
  message: "Hello from Home Assistant!"
```

#### Service Data

| Parameter | Required | Description |
|-----------|----------|-------------|
| `message` | Yes | Text message (max 95 chars) or emoji code (E01-E12) |
| `data.message_type` | No | `text` (default) or `emoji` |
| `data.username` | No | Custom sender name shown on watch |

#### Emoji Codes

| Code | Emoji | Code | Emoji |
|------|-------|------|-------|
| E01 | Happy | E07 | Sleepy |
| E02 | Love | E08 | Hungry |
| E03 | Laugh | E09 | Cool |
| E04 | Wink | E10 | Confused |
| E05 | Sad | E11 | Sick |
| E06 | Angry | E12 | Celebrate |

## Events

### Message Received

When a message arrives from the watch, the integration fires an `anio_message_received` event:

```yaml
event_type: anio_message_received
data:
  device_id: "abc123def456"
  device_name: "Kids Watch"
  message_id: "msg789"
  content: "Hello!"
  sender: "WATCH"
  message_type: "TEXT"
  timestamp: "2024-01-15T10:30:00+00:00"
```

## Example Automations

### Low Battery Notification

```yaml
automation:
  - alias: "ANIO Watch Low Battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.kids_watch_battery
        below: 20
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Watch Battery Low"
          message: "{{ state_attr('sensor.kids_watch_battery', 'friendly_name') }} is at {{ states('sensor.kids_watch_battery') }}%"
```

### Send Message When Leaving Home

```yaml
automation:
  - alias: "Send Goodbye to Watch"
    trigger:
      - platform: state
        entity_id: person.parent
        from: "home"
    action:
      - service: notify.kids_watch_message
        data:
          message: "Bye! Have a great day!"
          data:
            username: "Mom"
```

### Notify When Watch Goes Offline

```yaml
automation:
  - alias: "Watch Offline Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.kids_watch_online
        to: "off"
        for:
          minutes: 10
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Watch Offline"
          message: "Kids watch has been offline for 10 minutes"
```

### Geofence Arrival Notification

```yaml
automation:
  - alias: "Arrived at School"
    trigger:
      - platform: state
        entity_id: binary_sensor.kids_watch_at_school
        to: "on"
    action:
      - service: notify.mobile_app_phone
        data:
          message: "Kids arrived at school safely!"
```

### React to Incoming Messages

```yaml
automation:
  - alias: "Forward Watch Messages"
    trigger:
      - platform: event
        event_type: anio_message_received
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Message from {{ trigger.event.data.device_name }}"
          message: "{{ trigger.event.data.content }}"
```

## Troubleshooting

### Authentication Failed

- Verify your email and password are correct
- Check if your account requires two-factor authentication
- Try logging into the ANIO mobile app to confirm your credentials work

### Watch Not Appearing

- Ensure the watch is properly set up in the ANIO mobile app
- Check that the watch is powered on and has network connectivity
- Wait for the next polling interval or restart the integration

### Location Not Updating

- The watch only reports location periodically to save battery
- Use the "Locate" button to request an immediate location update
- Check if "Locating" is enabled in the watch settings via the ANIO app

### Rate Limiting

The ANIO API has rate limits. If you receive rate limit errors:
- Increase the scan interval in the integration options
- Avoid pressing the Locate button too frequently

## Privacy & Security

- All communication uses HTTPS encryption
- Credentials are stored securely in Home Assistant
- No data is sent to third parties
- The integration only accesses data for watches linked to your account

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration and is not affiliated with, endorsed by, or connected to ANIO in any way. Use at your own risk.

## Support

- [GitHub Issues](https://github.com/hackwell/homeassistant-anio/issues) - Bug reports and feature requests
- [Home Assistant Community](https://community.home-assistant.io/) - General questions and discussions
