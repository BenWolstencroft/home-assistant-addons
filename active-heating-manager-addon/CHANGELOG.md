# Changelog

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
