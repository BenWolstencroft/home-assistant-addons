# Active Heating Manager Documentation

## Overview

The Active Heating Manager is a Home Assistant add-on that automatically manages your boiler based on heating demand from TRV (Thermostatic Radiator Valve) entities. When any TRV is actively heating, the add-on ensures your boiler is running. When no TRVs need heating, it turns off or reduces the boiler demand.

**Important**: This add-on is designed for systems where each TRV manages its own individual room schedule and temperature settings. The add-on doesn't control TRV schedules or temperatures - it simply monitors when TRVs are calling for heat and ensures the boiler responds accordingly. Your TRVs remain in full control of their room-specific heating schedules.

## Features

- **Automatic Demand Detection**: Monitors TRV `hvac_action` states to detect when radiators need heating
- **Smart Boiler Control**: Two control modes for different boiler setups
- **Flexible Configuration**: Customize temperatures and polling intervals
- **Real-time Monitoring**: Continuous polling of TRV states with configurable intervals

## Configuration Options

### `debug_logging` (optional)
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable verbose debug logging for troubleshooting. Shows detailed information about entity states, service calls, and decision-making.

### `trv_entities` (required)
- **Type**: list of strings
- **Default**: `[]`
- **Description**: List of climate entity IDs for your TRVs/radiator thermostats. The add-on monitors these entities for heating demand. Example: `climate.living_room_trv`, `climate.bedroom_trv`

### `boiler_entity` (required)
- **Type**: string
- **Default**: `""`
- **Description**: Entity ID of your boiler controller. This can be:
  - A climate thermostat entity (e.g., `climate.boiler_thermostat`) when using thermostat mode
  - A switch or input_boolean entity (e.g., `switch.boiler`, `input_boolean.heating`) when using toggle mode

### `boiler_mode` (required)
- **Type**: list (thermostat|toggle)
- **Default**: `thermostat`
- **Description**: Control method for your boiler:
  - **`thermostat`**: Controls a climate entity by setting manual temperatures (recommended for boiler thermostats)
  - **`toggle`**: Controls a switch/input_boolean by turning it on/off (for simple relay switches)

### `manual_on_temperature` (optional)
- **Type**: integer (15-35)
- **Default**: `21`
- **Description**: Temperature (in °C) to set when TRVs are heating. Only applies in thermostat mode. This tells the boiler thermostat to heat when demand exists.

### `manual_off_temperature` (optional)
- **Type**: integer (5-20)
- **Default**: `14`
- **Description**: Temperature (in °C) to set when no TRVs are heating. Only applies in thermostat mode. This tells the boiler thermostat to stop heating when there's no demand.

### `polling_interval` (optional)
- **Type**: integer (10-3600)
- **Default**: `300` (5 minutes)
- **Description**: How often (in seconds) to check TRV states. Lower values = more responsive but more resource intensive. Recommended: 60-300 seconds.

## How It Works

This add-on acts as a demand-based boiler controller. Your TRVs control individual room schedules and temperatures independently. The add-on simply aggregates their heating demand and manages the boiler accordingly.

**Workflow**:

1. **Polling**: The add-on polls all configured TRV entities at the specified interval
2. **Detection**: Checks if any TRV has `hvac_action` = `heating` (meaning that TRV is calling for heat based on its own schedule and temperature settings)
3. **Action**:
   - **If heating detected**: 
     - Thermostat mode: Sets boiler thermostat to manual mode at `manual_on_temperature`
     - Toggle mode: Turns boiler switch ON
   - **If no heating detected**:
     - Thermostat mode: Sets boiler thermostat to manual mode at `manual_off_temperature`
     - Toggle mode: Turns boiler switch OFF

**Key Point**: The add-on never changes TRV temperatures or schedules. Each TRV operates independently according to its own configuration. The add-on only ensures the boiler is available when any room needs heating.

## Example Configurations

### Example 1: Thermostat Mode (Recommended)
```yaml
debug_logging: false
trv_entities:
  - climate.living_room_trv
  - climate.bedroom_trv
  - climate.kitchen_trv
boiler_entity: climate.boiler_thermostat
boiler_mode: thermostat
manual_on_temperature: 21
manual_off_temperature: 14
polling_interval: 120
```

### Example 2: Toggle Mode (Simple Switch)
```yaml
debug_logging: false
trv_entities:
  - climate.radiator_1
  - climate.radiator_2
boiler_entity: switch.boiler_relay
boiler_mode: toggle
polling_interval: 60
```

## Getting Started

1. Install the add-on from the add-on store
2. Configure your TRV entities in the Configuration tab
3. Configure your boiler entity and select the appropriate mode
4. Adjust temperatures and polling interval if needed
5. Start the add-on
6. Check the logs to ensure TRVs are being detected correctly

## Troubleshooting

### Add-on not detecting heating demand
- Enable `debug_logging` to see detailed entity states
- Check that your TRV entities have `hvac_action` attributes
- Verify entity IDs are correct
- Check logs for "HVAC action" messages

### Boiler not responding
- Verify the `boiler_entity` ID is correct
- Check if your thermostat supports manual temperature control
- Try toggle mode if thermostat mode doesn't work
- Enable debug logging to see service call results

### Too responsive or not responsive enough
- Adjust `polling_interval`: lower = more responsive, higher = less frequent checks
- Recommended range: 60-300 seconds

## Support

For help and support:
- GitHub Issues: https://github.com/BenWolstencroft/home-assistant-addons/issues
