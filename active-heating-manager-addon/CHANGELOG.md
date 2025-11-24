# Changelog

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
