# Changelog

## [0.7.2] - 2025-11-24

### Fixed
- Dynamic temperature calculation for valve positions 0-25%
- Now correctly scales from current boiler temp (0%) to current + 0.5°C (25%)
- Previous version incorrectly scaled from manual_off_temp, causing unnecessarily low target temperatures
- Example: At 12.5% with 19.8°C current temp, now targets 20.0°C instead of 17.0°C

## [0.7.1] - 2025-11-24

### Improved
- Enhanced debug logging for dynamic temperature calculation
- Step-by-step interpolation calculations now logged with actual values
- Better visibility into boiler thermostat current temperature usage
- Detailed logging of bounds checking and rounding operations
- Easier troubleshooting and verification of temperature calculations

## [0.7.0] - 2025-11-24

### Added
- Home Assistant sensor entities for monitoring heating status:
  - `sensor.active_heating_manager_status` - Overall status (heating/idle)
  - `sensor.active_heating_manager_trvs_heating` - Count of TRVs currently heating
  - `sensor.active_heating_manager_avg_valve_position` - Average valve position percentage
  - `sensor.active_heating_manager_target_temp` - Current boiler target temperature
- Real-time statistics published every polling interval
- Integration with Home Assistant dashboards, automations, and history

### Improved
- Better visibility into heating system operation
- Enable advanced automations based on heating demand metrics
- Enhanced monitoring and diagnostics capabilities

## [0.6.0] - 2025-11-24

### Added
- Dynamic temperature calculation based on average valve position percentage
- `use_dynamic_temperature` configuration option (default: true)
- Automatic detection of valve position sensors (e.g., sensor.xxx_position)
- Proportional heating control: boiler temperature adjusts based on heating demand intensity
- Smart temperature scaling:
  - 0% valve position → manual_off_temperature
  - 25% valve position → current boiler temp + 0.5°C
  - 25-100% → scales linearly to manual_on_temperature

### Changed
- All boiler thermostat temperatures now rounded to nearest 0.5°C (whole or half degrees)
- Temperature calculation considers current boiler temperature for more efficient control

### Improved
- More granular heating control based on actual valve demand
- Prevents overshooting by adjusting boiler temperature proportionally
- Better energy efficiency through demand-responsive temperature control

## [0.5.0] - 2025-11-24

### Added
- Valve state checking: Optional filtering of heating demand based on valve position
- `check_valve_state` configuration option (default: true)
- Automatic detection of valve state sensors using common naming patterns
- Support for multiple valve sensor formats (binary_sensor/sensor)
- Intelligent handling when valve sensors are not available (safe default behavior)

### Improved
- TRVs demanding heat with closed valves are now ignored (prevents unnecessary boiler activation)
- Enhanced logging to show valve state for each TRV
- Better debug information for valve sensor detection

## [0.4.0] - 2025-11-24

### Changed
- **Breaking**: Removed boost mode functionality - addon now always uses manual temperature control for thermostats
- **Breaking**: Renamed `boiler_thermostat_entity` to `boiler_entity` for better flexibility
- **Breaking**: Replaced single `manual_temperature` with separate `manual_on_temperature` and `manual_off_temperature`
- Default manual temperatures changed to 21°C (on) and 14°C (off) for better real-world usage

### Added
- Toggle mode: Support for simple switch/input_boolean boiler control
- `boiler_mode` configuration option to choose between thermostat and toggle control
- `manual_on_temperature` config (default 21°C, range 15-35°C)
- `manual_off_temperature` config (default 14°C, range 5-20°C)
- Comprehensive documentation in DOCS.md explaining all configuration options
- Example configurations for both thermostat and toggle modes
- Logo/icon for addon visibility

### Improved
- Enhanced logging to show which mode and temperatures are being used
- Better state checking to avoid unnecessary service calls
- Backwards compatibility support for old `boiler_thermostat_entity` config
- Clearer documentation about TRV-based scheduling approach

## [0.3.0] - 2025-11-23

### Added
- Boiler thermostat management based on TRV heating demand
- Configuration option for boiler thermostat entity
- Automatic boost triggering when any TRV is actively heating
- Boost extension every polling interval (keeps 15 minutes ahead)
- Automatic boost cancellation when no TRVs are heating
- Entity selector dropdowns with climate entity filtering
- Smart preset mode detection and restoration

### Changed
- Enhanced logging for heating demand detection
- Improved service call error handling

## [0.2.0] - 2025-11-21

### Added
- Configuration option for TRV entities (climate thermostats)
- Configurable polling interval (default 5 minutes)
- Home Assistant API integration to retrieve entity states
- Automatic polling of TRV states and attributes
- Logging of current temperature, target temperature, and HVAC action

## [0.1.0] - 2025-11-21

### Added
- Initial project structure
- Basic addon configuration
- Placeholder implementation
