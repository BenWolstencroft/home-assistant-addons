# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2025-11-20

### Fixed
- Fixed Docker build error with pip installation in Python 3.12+ by adding `--break-system-packages` flag
- Resolved PEP 668 externally-managed-environment error during addon installation

## [1.0.0] - 2025-11-20

### Added
- Initial release of Argon ONE Active Cooling add-on
- Automatic temperature-based fan control via I2C
- Configurable temperature thresholds and fan speeds
- Support for Celsius and Fahrenheit temperature units
- Adjustable check interval (10-300 seconds)
- Debug logging mode for troubleshooting
- Smooth fan speed transitions with 30-second delay on reduction
- Graceful shutdown handling
- Support for armhf, armv7, and aarch64 architectures
- I2C device detection and validation
- Comprehensive error handling and logging

### Features
- Based on Jeff Curless's enhanced argoneon scripts
- Compatible with Argon ONE v5 case
- Integration with Home Assistant's configuration system
- Real-time CPU temperature monitoring
- Automatic fan control with no manual intervention required

### Technical Details
- Communication via I2C bus at address 0x1a
- Temperature reading from thermal_zone0 or vcgencmd
- Spin-up sequence for reliable fan operation
- Configuration via Home Assistant UI
