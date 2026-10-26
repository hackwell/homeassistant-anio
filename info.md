# ANIO Smartwatch Integration for Home Assistant

This custom integration allows you to monitor and interact with ANIO smartwatches through Home Assistant.

## Features

- **Status Monitoring**: Battery level, signal strength, online status, last seen timestamp
- **Location Tracking**: Watch location on the map, **Locate Now** (fresh position within about a minute) and **Explorer Mode**
- **Geofences**: Presence per geofence defined in the ANIO app, plus a switch for ANIO's monitoring
- **School Way and Silence Times**: See when they are running, and pause single entries, e.g. during the school holidays
- **Messaging**: Send text and emoji messages to the watch
- **Events**: Messages from the watch and ANIO's alerts (geofence entered/left, low battery)
- **Alarms**: Next alarm sensor, create and delete alarms
- **Watch Settings**: Ring profile, all silence times on/off, tracking mode
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
| Next Alarm | Sensor | Time of the alarm that rings next (weekdays considered) |
| Tracking Mode | Sensor | Current tracking mode |
| Online | Binary Sensor | Whether watch is currently online |
| School Way | Binary Sensor | On while a school way time is running |
| Silence Time Active | Binary Sensor | On while a silence time is running |
| At [Geofence] | Binary Sensor | One per geofence, shows presence |
| Location | Device Tracker | Watch location for map display |
| Locate Now | Button | Ask the watch for its position now (arrives within about a minute) |
| Ring | Button | Make the watch ring and vibrate (does not locate it) |
| Power Off | Button | Remotely power off the watch |
| Flower | Button | Send a reward heart (only on watches with hearts, not the ANIO 6) |
| Explorer Mode | Switch | Locate every 5 minutes for an hour (uses more battery) |
| Silence Times | Switch | Whether the silence times apply at all |
| School way / Silence time … | Switch | One per entry, e.g. to pause them during school holidays |
| Monitor … | Switch | Whether ANIO monitors a geofence |
| Ring Profile | Select | Ring, vibrate or silent |
| Message | Notify | Send messages to the watch |

## Actions

- `anio.send_message`: text or emoji message with sender name
- `anio.create_alarm` / `anio.delete_alarm`: alarms on a watch

## Events

The integration fires `anio_activity` events for ANIO's alerts (geofence entered/left,
low battery) and `anio_message_received` events when a message arrives from the watch:

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

- [GitHub Issues](https://github.com/hackwell/homeassistant-anio/issues)
- [Home Assistant Community Forum](https://community.home-assistant.io/)
