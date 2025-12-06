# Active Heating Manager Documentation

## Overview

The Active Heating Manager is a Home Assistant add-on that automatically manages your boiler based on heating demand from TRV (Thermostatic Radiator Valve) entities. When any TRV is actively heating, the add-on ensures your boiler is running. When no TRVs need heating, it turns off or reduces the boiler demand.

**Important**: This add-on is designed for systems where each TRV manages its own individual room schedule and temperature settings. The add-on doesn't control TRV schedules or temperatures - it simply monitors when TRVs are calling for heat and ensures the boiler responds accordingly. Your TRVs remain in full control of their room-specific heating schedules.

## Features

- **Automatic Demand Detection**: Monitors TRV `hvac_action` states to detect when radiators need heating
- **Smart Boiler Control**: Two control modes for different boiler setups
- **MQTT Integration**: Entities have unique IDs and can be configured through the UI
- **Device Grouping**: All sensors appear under a single "Active Heating Manager" device
- **Flexible Configuration**: Customize temperatures and polling intervals
- **Continuous Monitoring**: Polling of TRV states with configurable intervals

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

### `check_valve_state` (optional)
- **Type**: boolean
- **Default**: `true`
- **Description**: Check physical valve state sensors before considering a TRV as heating. When enabled, the add-on looks for valve state sensors (e.g., `binary_sensor.xxx_valve_state`) and only counts a TRV as heating if both `hvac_action` is "heating" AND the valve is physically open. This prevents false heating detection when a valve is stuck closed. Only applies when `ignore_hvac_action` is `false`.

### `ignore_hvac_action` (optional)
- **Type**: boolean
- **Default**: `false`
- **Description**: When enabled, ignores the TRV's `hvac_action` attribute and relies purely on valve position sensors to determine heating demand. A TRV is considered heating if its valve position is greater than 0%. This is useful for TRVs that don't report accurate `hvac_action` states or for systems where you want direct valve position control. **Note**: Requires valve position sensors (e.g., `sensor.xxx_position`) for each TRV. When enabled, `check_valve_state` is ignored.

### `min_valve_position_threshold` (optional)
- **Type**: integer (0-100)
- **Default**: `0` (disabled)
- **Description**: Minimum valve position percentage required to consider a TRV as demanding heat. This prevents rooms with marginal heating demand (e.g., 0.5°C from target) from keeping the boiler running continuously. For example, setting this to `15` means a TRV's valve must be open at least 15% to trigger boiler activation. Recommended values: 10-20% for overnight efficiency. **Note**: Requires valve position sensors for each TRV.

### `min_trvs_heating` (optional)
- **Type**: integer (1-20)
- **Default**: `1`
- **Description**: Minimum number of TRVs that must be demanding heat before the boiler activates. Setting this to `2` or higher prevents a single room with marginal demand from keeping the boiler running. Works in combination with `min_valve_position_threshold` - boiler activates if either the minimum number of TRVs are heating OR if fewer TRVs are heating but with high valve positions. Useful for preventing overnight cycling.

### `use_dynamic_temperature` (optional)
- **Type**: boolean
- **Default**: `true`
- **Description**: When enabled (thermostat mode only), calculates dynamic boiler target temperatures based on average TRV valve positions instead of using fixed `manual_on_temperature`. This provides more efficient heating by adjusting boiler temperature to match actual demand. When disabled, uses fixed temperatures.

### `polling_interval` (optional)
- **Type**: integer (10-3600)
- **Default**: `300` (5 minutes)
- **Description**: How often (in seconds) to check TRV states. Lower values = more responsive but more resource intensive. Recommended: 60-300 seconds.

### `mqtt_host` (optional)
- **Type**: string
- **Default**: `core-mosquitto`
- **Description**: MQTT broker hostname. Used for proper entity registration with unique IDs. Default works with Home Assistant's Mosquitto add-on.

### `mqtt_port` (optional)
- **Type**: port
- **Default**: `1883`
- **Description**: MQTT broker port. Default is standard MQTT port.

### `mqtt_user` (optional)
- **Type**: string
- **Default**: `""`
- **Description**: MQTT username if authentication is required. Leave blank for anonymous connection.

### `mqtt_password` (optional)
- **Type**: password
- **Default**: `""`
- **Description**: MQTT password if authentication is required. Leave blank for anonymous connection.

## Sensor Entities

The add-on creates the following sensor entities via MQTT discovery, all grouped under an "Active Heating Manager" device:

- **`sensor.active_heating_manager_status`**: Current status (heating/idle) - configurable via UI
- **`sensor.active_heating_manager_trvs_heating`**: Count of TRVs currently heating - configurable via UI
- **`sensor.active_heating_manager_avg_valve_position`**: Average valve position percentage - configurable via UI
- **`sensor.active_heating_manager_target_temp`**: Current boiler target temperature (thermostat mode only) - configurable via UI

All entities have unique IDs and can be customized (name, icon, area, etc.) through **Settings → Devices & Services → MQTT → Active Heating Manager**.

## How It Works

This add-on acts as a demand-based boiler controller. Your TRVs control individual room schedules and temperatures independently. The add-on simply aggregates their heating demand and manages the boiler accordingly.

**Workflow**:

1. **Polling**: The add-on polls all configured TRV entities at the specified interval
2. **Detection**: Determines if any TRV is calling for heat:
   - **Default mode** (`ignore_hvac_action` = `false`): Checks if `hvac_action` = `heating` (optionally with valve state verification)
   - **Position mode** (`ignore_hvac_action` = `true`): Checks if valve position > 0%
3. **Action**:
   - **If heating detected**: 
     - Thermostat mode: Sets boiler thermostat to manual mode at `manual_on_temperature`
     - Toggle mode: Turns boiler switch ON
   - **If no heating detected**:
     - Thermostat mode: Sets boiler thermostat to manual mode at `manual_off_temperature`
     - Toggle mode: Turns boiler switch OFF

**Key Point**: The add-on never changes TRV temperatures or schedules. Each TRV operates independently according to its own configuration. The add-on only ensures the boiler is available when any room needs heating.

## Example Configurations

### Example 1: Thermostat Mode with MQTT (Recommended)
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
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
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
mqtt_host: core-mosquitto
mqtt_port: 1883
```

### Example 3: Preventing Overnight Cycling with Thresholds
```yaml
debug_logging: false
trv_entities:
  - climate.living_room_trv
  - climate.bedroom_trv
  - climate.kitchen_trv
  - climate.bathroom_trv
boiler_entity: climate.boiler_thermostat
boiler_mode: thermostat
manual_on_temperature: 21
manual_off_temperature: 14
check_valve_state: true
ignore_hvac_action: false
min_valve_position_threshold: 15  # Ignore TRVs with valve < 15% open
min_trvs_heating: 2                # Require 2+ TRVs to activate boiler
use_dynamic_temperature: true
polling_interval: 120
mqtt_host: core-mosquitto
mqtt_port: 1883
```

This configuration prevents single rooms sitting 0.5°C from target from keeping the boiler running all night. The boiler only activates when:
- 2 or more TRVs are demanding heat (regardless of valve position), OR
- Any TRV has valve position above 15% (strong demand from one room)

## Getting Started

1. **Install MQTT broker** (if not already installed):
   - Install the Mosquitto broker add-on from the add-on store
   - Start the Mosquitto broker
2. Install the Active Heating Manager add-on from the add-on store
3. Configure your TRV entities in the Configuration tab
4. Configure your boiler entity and select the appropriate mode
5. Configure MQTT settings (default values work with Mosquitto add-on)
6. Adjust temperatures and polling interval if needed
7. Start the add-on
8. Check the logs to ensure TRVs are being detected correctly and MQTT is connected
9. Find your sensors under **Settings → Devices & Services → MQTT → Active Heating Manager**

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

### MQTT connection issues
- Ensure Mosquitto broker add-on is installed and running
- Check MQTT credentials if authentication is enabled
- Verify `mqtt_host` and `mqtt_port` settings
- Look for "Connected to MQTT broker" message in logs
- Without MQTT, entities will still work but won't have unique IDs for UI configuration

## Support

For help and support:
- GitHub Issues: https://github.com/BenWolstencroft/home-assistant-addons/issues
