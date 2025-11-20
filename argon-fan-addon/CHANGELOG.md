# Changelog

All notable changes to this project will be documented in this file.

## [1.0.5] - 2025-11-20

### Fixed
- Fixed SMBus import to match OLED addon pattern (explicit SMBus class import)
- Removed unnecessary SYS_RAWIO privilege (OLED addon works without it)

### Changed
- Import SMBus class directly instead of importing module and aliasing
- Simplified I2C permissions to match working OLED addon configuration

## [1.0.4] - 2025-11-20

### Fixed
- Improved I2C device detection using i2cdetect command line tool first
- Changed from read operations to write operations for device detection (more reliable)
- Added detailed debug logging for each bus attempt
- Better error messages with troubleshooting steps

### Changed
- Now uses i2cdetect to scan buses before attempting communication
- Tests device communication with a safe write (fan off) instead of read
- More verbose debug output to help diagnose connection issues

## [1.0.3] - 2025-11-20

### Fixed
- Added I2C buses 13 and 14 to automatic detection list
- Improved I2C bus scanning to check all available buses (prioritizing 1, 0, 13, 14)
- Enhanced run.sh startup script to scan and report which bus has the Argon device

### Changed
- Bus detection order now: 1, 0, 13, 14, 3, 10, 11, 22 (most common first)
- Run script now scans all I2C buses and reports findings before starting service

## [1.0.2] - 2025-11-20

### Fixed
- Added SYS_RAWIO privilege for proper I2C device access
- Improved I2C bus detection - now automatically scans multiple buses to find Argon device
- Enhanced error messages for I2C communication failures with troubleshooting hints
- Added device detection at startup to verify Argon ONE case is connected
- Better handling of I2C errors - continues running instead of crashing

### Changed
- I2C initialization now tries multiple bus numbers (1, 0, 3, 10, 11, 22) automatically
- Added detailed logging of available I2C devices on startup failure

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
