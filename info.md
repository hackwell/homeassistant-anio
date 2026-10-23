# ANIO Smartwatch Integration for Home Assistant

This custom integration allows you to monitor and interact with ANIO smartwatches through Home Assistant.

## Features

- **Status Monitoring**: Battery level, signal strength, online status, last seen timestamp
- **Location Tracking**: Watch location on the Home Assistant map
- **Geofence Sensors**: Know whether the watch is inside the geofences defined in the ANIO app
- **Messaging**: Send text and emoji messages to the watch
- **Message Events**: Receive events when messages arrive from the watch, plus a sensor with the last message
- **Watch Settings**: Ring profile, silence times on/off, tracking mode and next alarm
- **Device Control**: Ring button to find the watch and power off functionality

## Supported Devices

- ANIO 5 Smartwatch
- ANIO 6 Smartwatch (Generation 6)

## Requirements

- Home Assistant 2024.12.0 or newer
- ANIO account (same credentials as the ANIO app)

## Installation

1. Install via HACS (recommended) or manually copy to `custom_components/anio`
2. Restart Home Assistant
3. Add the integration via Settings → Devices & Services → Add Integration → ANIO Smartwatch
4. Enter your ANIO account credentials
5. If 2FA is enabled, enter the verification code

## Entities Created

For each watch, the integration creates:

| Entity | Type | Description |
|--------|------|-------------|
| Battery | Sensor | Battery percentage |
| Signal Strength | Sensor | Mobile signal strength |
| Last Seen | Sensor | Timestamp of last communication |
| Last Message | Sensor | Last message sent by the watch |
| Next Alarm | Sensor | Earliest enabled alarm time |
| Tracking Mode | Sensor | Current tracking mode |
| Online | Binary Sensor | Whether watch is currently online |
| At [Geofence] | Binary Sensor | One per geofence, shows presence |
| Location | Device Tracker | Watch location for map display |
| Ring | Button | Make the watch ring and vibrate (does not locate it) |
| Power Off | Button | Remotely power off the watch |
| Flower | Button | Send a "flower" (no visible effect on the ANIO 6) |
| Silence Time | Switch | Enable or disable the silence times |
| Ring Profile | Select | Ring, vibrate or silent |
| Message | Notify | Send messages to the watch |

## Events

The integration fires `anio_message_received` events when a message arrives from the watch:

```yaml
event_type: anio_message_received
data:
  device_id: "abc123"
  device_name: "Kids Watch"
  message_id: "msg456"
  content: "Hello!"
  sender: "DEVICE"  # WATCH or DEVICE, as reported by the ANIO API
  message_type: "TEXT"
  timestamp: "2024-01-15T10:30:00Z"
```

## Example Automations

### Notify when watch battery is low
```yaml
automation:
  - alias: "ANIO Battery Low"
    trigger:
      - platform: numeric_state
        entity_id: sensor.kids_watch_battery
        below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Kids watch battery is at {{ states('sensor.kids_watch_battery') }}%"
```

### Send a message when leaving home
```yaml
automation:
  - alias: "Send goodbye message"
    trigger:
      - platform: state
        entity_id: person.parent
        from: "home"
    action:
      - service: notify.send_message
        target:
          entity_id: notify.kids_watch_message
        data:
          message: "Bye! Be good!"
```

## Support

- [GitHub Issues](https://github.com/your-repo/anio-hass/issues)
- [Home Assistant Community Forum](https://community.home-assistant.io/)
