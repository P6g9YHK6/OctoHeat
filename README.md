# OctoHeat

An OctoPrint plugin that controls a heater via Home Assistant based on temperature sensor readings.

## Features

- **Multiple trigger modes**: Control when the heater activates based on:
  - Bed temperature being set
  - Print job running
  - Thermostat mode (always active when needed)

- **Temperature control strategies**:
  - Direct target temperature
  - Bed temperature with offset (raw value or percentage)

- **Home Assistant Integration**:
  - Reads chamber temperature from HA sensors
  - Controls heater via HA switches
  - Simple API-based communication

- **Safety Features**:
  - Automatic heater shutdown on OctoPrint shutdown/reboot
  - Thermal runaway protection with manual reset
  - Temperature sensor timeout protection
  - Configurable hysteresis for thermostat mode

## Installation

Install via the [OctoPrint Plugin Manager](https://docs.octoprint.org/en/master/bundled/plugins/pluginmanager.html) using this URL:

```
https://github.com/P6g9YHK6/OctoHeat/archive/refs/heads/main.zip
```

Or manually:

```bash
cd ~/.octoprint/plugins
git clone https://github.com/P6g9YHK6/OctoHeat.git
```

## Configuration

### Home Assistant Settings

1. **HA URL**: URL of your Home Assistant instance (e.g., `http://homeassistant:8123`)
2. **HA Token**: Long-lived access token from Home Assistant (Profile → Long-lived access tokens)
3. **Temperature Sensor**: HA entity ID for the chamber temperature sensor (e.g., `sensor.chamber_temp`)
4. **Heater Switch**: HA entity ID for the heater switch (e.g., `switch.heater`)

### Control Mode

Choose how the heater is triggered:

| Trigger | Description |
|---------|-------------|
| When bed temperature is set | Heater turns on when bed heater has a target temperature set |
| When print is running | Heater turns on when a print job is actively printing |
| Thermostat mode | Heater turns on based on chamber temperature vs target |

### Temperature Mode

| Mode | Description |
|------|-------------|
| Direct target | Set a fixed target temperature (°C) |
| Bed with offset | Target = bed temperature + offset |

Offset can be a raw value (°C) or percentage of bed temperature.

## Supported Home Assistant API Calls

- `GET /api/states/{entity_id}` - Read sensor state
- `POST /api/services/switch/turn_on` - Turn on heater switch
- `POST /api/services/switch/turn_off` - Turn off heater switch

## Requirements

- OctoPrint 1.9.0+
- Python 3.7+
- Home Assistant instance with API access

## License

AGPLv3 - see [LICENSE](LICENSE) for details.