# ANIO Smartwatch Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/hackwell/homeassistant-anio.svg)](https://github.com/hackwell/homeassistant-anio/releases)
[![License](https://img.shields.io/github/license/hackwell/homeassistant-anio.svg)](LICENSE)

A Home Assistant custom integration for ANIO children's smartwatches. Monitor your child's watch status, location, and communicate directly through Home Assistant.

## Features

- **Status Monitoring** - Battery level, signal strength, online status, last seen timestamp
- **Location Tracking** - Watch location displayed on the Home Assistant map
- **Geofence Sensors** - Binary sensors showing whether the watch is inside the geofences defined in the ANIO app
- **Messaging** - Send text messages (up to 95 characters) and emoji messages to the watch
- **Message Events** - Receive Home Assistant events when messages arrive from the watch, plus a sensor with the last message
- **Watch Settings** - Ring profile, silence times on/off, tracking mode and next alarm
- **Device Control** - Ring button to find the watch, Power Off button

## Supported Devices

- ANIO 5 Smartwatch
- ANIO 6 Smartwatch (Generation 6)

## Requirements

- Home Assistant 2024.12.0 or newer
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

Location, battery, messages and ANIO's alerts are fetched at every scan. Alarms,
silence and school way times and geofences rarely change, so they are only fetched every 30
minutes (silence times right away after switching them in Home Assistant). A
geofence added in the ANIO app can therefore take up to 30 minutes to appear.

## Entities

For each watch, the integration creates the following entities. Their names are
translated (English and German). The entity IDs below are the English ones; a new
installation with Home Assistant set to German gets German IDs (e.g.
`sensor.<name>_akku`). Existing installations keep their entity IDs.

Watches added to the ANIO account and geofences created in the ANIO app get their
entities automatically with the next update. A geofence deleted in the app makes its
sensor unavailable; you can then delete the entity. A watch that is no longer in the
account can be deleted in Home Assistant (device page → ⋮ → Delete).

### Sensors

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.<name>_battery` | Sensor | Battery percentage (0-100%), unknown while no location is available |
| `sensor.<name>_signal_strength` | Sensor | Mobile signal strength (%) |
| `sensor.<name>_last_seen` | Sensor | Timestamp of last communication |
| `sensor.<name>_last_message` | Sensor | Text of the last message sent by the watch (attributes: sender, type, created_at, is_read) |
| `sensor.<name>_next_alarm` | Sensor | Earliest enabled alarm time (does not take weekdays into account yet) |
| `sensor.<name>_tracking_mode` | Sensor | Current tracking mode reported by the watch |

### Binary Sensors

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.<name>_online` | Binary Sensor | Whether watch is currently online |
| `binary_sensor.<name>_school_way` | Binary Sensor | On while one of the school way times set in the ANIO app is running (the watch then locates every minute). Attribute `periods`: start, end, days |
| `binary_sensor.<name>_silence_active` | Binary Sensor | "Silence Time Active": on while one of the enabled silence times is running, so the watch is silent. Attribute `periods`: start, end, days |
| `binary_sensor.<name>_at_<geofence>` | Binary Sensor | One per geofence set up in the ANIO app; on while the watch's last position is inside. Attributes: radius, ANIO's monitoring window (`active_from`/`active_until`) |

### Device Tracker

| Entity | Type | Description |
|--------|------|-------------|
| `device_tracker.<name>_location` | Device Tracker | GPS location for map display |

### Buttons

| Entity | Type | Description |
|--------|------|-------------|
| `button.<name>_locate` | Button | **Ring**: the watch rings and vibrates loudly ("Uhr finden" in the ANIO app). It does **not** request a new location |
| `button.<name>_power_off` | Button | Remotely power off the watch |
| `button.<name>_flower` | Button | Send a "flower" (reward heart) to the watch. Only works on watches with reward hearts; the ANIO 6 has none, so there the button is disabled by default and has no effect ([#5](https://github.com/hackwell/homeassistant-anio/issues/5)) |

### Switch

| Entity | Type | Description |
|--------|------|-------------|
| `switch.<name>_silence_time` | Switch | "Silence Times": whether the silence times configured in the ANIO app apply at all (on/off for all of them). It does not mean the watch is silent right now |

### Select

| Entity | Type | Description |
|--------|------|-------------|
| `select.<name>_ring_profile` | Select | Ring profile: `RING_AND_VIBRATE`, `VIBRATE_ONLY` or `SILENT` |

### Notify

| Entity | Type | Description |
|--------|------|-------------|
| `notify.<name>_message` | Notify | Send messages to the watch, see [Send Message](#send-message) |

## Services

### Send Message

Send a text message with the standard notify action:

```yaml
service: notify.send_message
target:
  entity_id: notify.<watch_name>_message
data:
  message: "Hello from Home Assistant!"
```

`notify.send_message` only supports plain text. To send an emoji or set the
sender name, use `anio.send_message`:

```yaml
service: anio.send_message
target:
  entity_id: notify.<watch_name>_message
data:
  message: "E01"
  message_type: emoji
```

#### `anio.send_message` Service Data

| Parameter | Required | Description |
|-----------|----------|-------------|
| `message` | Yes | Text message (max 95 chars) or emoji code (E01-E09) |
| `message_type` | No | `text` (default) or `emoji` |
| `username` | No | Sender name shown on the watch, default `Home Assistant` |

The watch needs a sender name to display a message: without one, text arrives as
a digit code and emojis as a heart. The integration therefore always sends one,
also for `notify.send_message` (`Home Assistant`).

#### Emoji Codes

The same emojis as in the ANIO app's emoji bar:

| Code | Emoji | Code | Emoji | Code | Emoji |
|------|-------|------|-------|------|-------|
| E01 | 🙂 | E04 | 🙁 | E07 | 👎 |
| E02 | 😘 | E05 | 😁 | E08 | 👍 |
| E03 | 😎 | E06 | 😛 | E09 | ❤️ |

## Events

### Message Received

When a message arrives from the watch, the integration fires an `anio_message_received` event.
Messages that already existed when Home Assistant started are not reported again.
`content` is the text, the emoji itself for emoji messages, or empty for voice messages:

```yaml
event_type: anio_message_received
data:
  device_id: "abc123def456"
  device_name: "Kids Watch"
  message_id: "msg789"
  content: "Hello!"
  sender: "DEVICE"  # WATCH or DEVICE, as reported by the ANIO API
  message_type: "TEXT"
  timestamp: "2024-01-15T10:30:00+00:00"
```

### ANIO Alerts

ANIO's own alerts, the ones the ANIO app shows as notifications, are fired as
`anio_activity` events. Geofence alerts come from ANIO itself, i.e. they follow the
geofence's monitoring window set in the app. Alerts that already existed when Home
Assistant started are not reported again.

```yaml
event_type: anio_activity
data:
  device_id: "abc123def456"
  device_name: "Kids Watch"
  activity_id: "act123"
  type: "GEOFENCE_ENTERED"  # also GEOFENCE_LEFT, LOW_BATTERY, ...
  text: "Kids Watch has arrived at School"  # as shown in the ANIO app
  geofence_id: "geo456"     # null for alerts without a geofence
  geofence_name: "School"
  timestamp: "2024-01-15T07:52:00+00:00"
```

## Example Automations

### Arrived at School (ANIO alert)

```yaml
automation:
  - alias: "Kids arrived at school"
    trigger:
      - platform: event
        event_type: anio_activity
        event_data:
          type: GEOFENCE_ENTERED
          geofence_name: School
    action:
      - service: notify.mobile_app_phone
        data:
          message: "{{ trigger.event.data.text }}"
```

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
      - service: anio.send_message
        target:
          entity_id: notify.kids_watch_message
        data:
          message: "Bye! Have a great day!"
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

### Diagnostics

When reporting a problem, please attach the diagnostics: **Settings** → **Devices & Services** →
**ANIO Smartwatch** → ⋮ → **Download diagnostics**. They contain firmware, capabilities,
timestamps and error messages; e-mail, tokens, names, phone numbers, coordinates and message
texts are removed.

### Authentication Failed

- Verify your email and password are correct
- Check if your account requires two-factor authentication
- Try logging into the ANIO mobile app to confirm your credentials work

### Watch Not Appearing

- Ensure the watch is properly set up in the ANIO mobile app
- Check that the watch is powered on and has network connectivity
- Wait for the next polling interval or restart the integration

### Location Not Updating

- The ANIO 6 reports its location every 60 minutes by default to save battery,
  so the position in Home Assistant can be up to an hour old
- For a fresh position, use "Einmalortung" (within about 60 seconds) or the
  explorer mode (every 5 minutes for an hour) in the ANIO app; school way times
  locate every minute. Opening the ANIO app also triggers a location update
- The Ring button only makes the watch ring; it does not locate it
- Check if "Locating" is enabled in the watch settings via the ANIO app

### Rate Limiting

The ANIO API has rate limits. If you receive rate limit errors:
- Increase the scan interval in the integration options
- Avoid pressing the Ring button too frequently

## Privacy & Security

- All communication uses HTTPS encryption
- Credentials are stored securely in Home Assistant
- No data is sent to third parties
- Message texts and locations are not written to the Home Assistant log
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

This integration is not meant for safety-critical use. Location, online status and geofence updates depend on the ANIO cloud and are only polled every few minutes, so they can be late or missing. In an emergency, don't rely on Home Assistant notifications alone; use the ANIO app and the watch's own SOS and call functions.

## Support

- [GitHub Issues](https://github.com/hackwell/homeassistant-anio/issues) - Bug reports and feature requests
- [Home Assistant Community](https://community.home-assistant.io/) - General questions and discussions
