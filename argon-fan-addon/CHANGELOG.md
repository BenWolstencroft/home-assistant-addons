# Changelog

All notable changes to this project will be documented in this file.

## [1.0.9] - 2025-12-01

### Added
- **AppArmor profile** (`apparmor.txt`) with explicit I2C device permissions matching OLED addon
- `hassio_role: default` in config.yaml (matching working OLED addon structure)

### Changed
- Enabled AppArmor (`apparmor: true`) to use proper permission profile
- I2C devices now have explicit `rwk` (read/write/lock) permissions in AppArmor
- Added thermal sensor read permissions for temperature monitoring

### Purpose
- Match configuration with working argon-oled-addon
- Ensure proper I2C device permissions via AppArmor
- Rule out permission issues preventing I2C communication

## [1.0.8] - 2025-12-01

### Added
- **Enhanced Diagnostics**: Method 6 using raw ioctl to bypass SMBus abstraction
- Device permission checking and reporting
- Full i2cdetect output logging for all buses
- Detection of multiple I2C addresses on same bus
- Read access verification during initialization
- File permission details for /dev/i2c-* devices

### Changed
- More detailed logging during I2C bus detection
- Reports all detected I2C addresses, not just 0x1a
- Better error context when all communication methods fail

### Purpose
- Diagnose why device at 0x1a is detected but not responding to writes
- Rule out permission issues, wrong addressing, or SMBus driver problems

## [1.0.7] - 2025-12-01

### Added
- **Investigative Mode**: Tests 5 different I2C communication methods to identify Argon ONE V5 protocol
  - Method 1: V1/Classic write_byte (single byte)
  - Method 2: V3 write_byte_data with 0x80 register
  - Method 3: Block write (write_i2c_block_data)
  - Method 4: write_byte_data with 0x00 register
  - Method 5: Direct write without spin-up sequence
- Detailed logging showing which method succeeds/fails for V5 hardware identification
- Enhanced TEST mode to run full diagnostic sequence

### Changed
- set_fan_speed now tests all communication methods and reports results
- Each speed change attempt shows detailed success/failure for each protocol
- Helps identify the correct protocol for Argon ONE V5 hardware

### Note
- This is a diagnostic version to identify V5 communication protocol
- Will be replaced with optimized single-method implementation once protocol is confirmed

## [1.0.6] - 2025-12-01

### Fixed - Major Overhaul
- **Complete rewrite based on verified reference implementations**
- Fixed I2C bus detection to use `i2cdetect` command first (matches adamoutler's approach)
- Fixed fan spin-up sequence: now properly spins to 100% before setting target speed
- Simplified I2C initialization - no longer attempts unsafe read operations during detection
- Fixed error handling to not exit on I2C communication errors (just logs and continues)
- Improved shutdown sequence to match reference implementation

### Changed
- I2C detection now uses `i2cdetect` output parsing (like bash reference scripts)
- Fan control now properly implements spin-up sequence from argononed.py
- Removed complex bus testing logic in favor of simple, proven approach
- Better error messages that match reference implementations
- Added subprocess import for temperature fallback support

### Verified Against
- Jeff Curless's argoneon project (argononed.py)
- Adam Outler's HassOS Argon One Addon (bash scripts)

### Documentation
- Added IMPLEMENTATION_NOTES.md with detailed technical documentation
- Documented hardware differences between Argon ONE v1/Classic and v3
- Added manual testing commands and troubleshooting guide

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
