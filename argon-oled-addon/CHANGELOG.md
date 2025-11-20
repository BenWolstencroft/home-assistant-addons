# Changelog

All notable changes to this project will be documented in this file.

## [1.7.0] - 2025-11-20

### Changed
- Disabled AppArmor protection mode (apparmor: false) to allow GPIO device access
- Required for button functionality to work properly in containerized environment

## [1.6.9] - 2025-11-20

### Added
- Enhanced GPIO debugging to list available /dev/gpiochip* devices
- More detailed error messages for GPIO initialization attempts
- Extended chip search to include gpiochip0-4

## [1.6.8] - 2025-11-20

### Fixed
- Critical bug: font and logo loading code was mistakenly inside debug_log() method
- This caused logo to reload on every debug message, creating infinite loop spam
- Moved font and logo loading back to __init__() where it belongs

## [1.6.7] - 2025-11-20

### Fixed
- GPIO initialization now tries multiple gpiochip devices (gpiochip0, gpiochip4, gpiochip1)
- Removed duplicate logo loading code that was causing infinite loop log spam
- Logo loading now only happens once in load_logo() method

## [1.6.6] - 2025-11-20

### Changed
- Switched from RPi.GPIO to libgpiod for container compatibility
- RPi.GPIO doesn't work in Docker containers; libgpiod provides proper containerized GPIO access
- Button functionality now fully supported in Home Assistant addon environment

## [1.6.5] - 2025-11-20

### Changed
- Updated base images from 9.1.7 to 19.0.0 (latest)
- Will retry RPi.GPIO compilation with newer base image

## [1.6.4] - 2025-11-20

### Changed
- Temporarily disabled button functionality due to RPi.GPIO compilation issues with musl in base image
- All display features continue to work normally with auto-rotation
- Button support will be re-enabled when compatible build environment is available

## [1.6.3] - 2025-11-20

### Fixed
- Docker build issue: added musl upgrade step before installing build dependencies to resolve version conflicts

## [1.6.2] - 2025-11-20

### Fixed
- Docker build issue: restructured build process to use virtual packages, avoiding musl version conflicts
- Build dependencies are now installed temporarily and removed after RPi.GPIO compilation

## [1.6.1] - 2025-11-20

### Fixed
- Docker build issue: added required build dependencies (gcc, python3-dev, musl-dev) for RPi.GPIO compilation

## [1.6.0] - 2025-11-20

### Added
- Physical button support on GPIO pin 4
- Single press: advance to next screen
- Double press: go back to previous screen
- Long press: return to first screen
- Button presses reset auto-rotation timer

### Dependencies
- Added RPi.GPIO for button monitoring
- Enabled GPIO access in addon configuration

## [1.5.3] - 2025-11-20

### Added
- Support links to GitHub repository and Home Assistant Community forum

### Changed
- Updated README to reference I2C Configurator community add-on for easier setup
- Removed "Supported Screens" section from README (consolidated into Configuration)
- Cleaned up screen name references (removed `logo1v5` and `status` aliases)

## [1.5.2] - 2025-11-20

### Added
- Default logo image bundled with addon
- Logo screen now shows graphical logo by default instead of text
- Users can still override with custom logo in /data/ or /config/ directories

### Changed
- Logo fallback order: /data/ → /config/ → bundled default → text-based

## [1.5.1] - 2025-11-19

### Added
- Debug logging configuration option (defaults to off)
- All verbose logging now controlled by `debug_logging` setting
- Cleaner logs by default with option to enable detailed debugging

### Changed
- Refactored debug logging to use centralized `debug_log()` method
- Reduced default log verbosity significantly

## [1.5.0] - 2025-11-19

### Added
- Home Assistant system status screen ("hastatus" or "status")
- Displays number of available updates (supervisor, core, and addons)
- Shows last backup date and time
- Visual indicators for system health (OK/Action Needed)
- Status summary showing if system is healthy or needs attention

## [1.4.2] - 2025-11-19

### Fixed
- IP address now correctly shows host IP instead of container IP
- QR code URL now uses host IP address, making it accessible from network
- Both features now query Supervisor network and Home Assistant info APIs

## [1.4.1] - 2025-11-19

### Changed
- QR code screen now uses full display area without header for maximum size
- Improved QR code drawing using direct matrix rendering for better compatibility

### Fixed
- Resolved PIL.image compatibility issues with QR code generation

## [1.4.0] - 2025-11-19

### Added
- QR code screen displaying Home Assistant URL
- New "qr" screen type that generates a scannable QR code
- Auto-detection of Home Assistant URL from Supervisor API
- Fallback to IP-based URL if API is unavailable
- QR code added to default screen rotation

### Dependencies
- Added qrcode Python package

## [1.3.6] - 2025-11-19

### Fixed
- Replaced `textbbox()` with approximate text centering for older Pillow compatibility
- IP address now displays correctly on all Pillow versions

## [1.3.4] - 2025-11-19

### Fixed
- Removed emoji icons causing Latin-1 encoding errors
- Replaced emoji decorations with text-only headers
- Improved font compatibility

## [1.3.3] - 2025-11-19

### Fixed
- Removed leftover `setup_buttons()` call that was causing startup crash
- Fixed run.sh script parsing error with screen_list configuration
- Removed duplicate configuration exports in run.sh

## [1.3.2] - 2025-11-19

### Removed
- Button support (not working with current hardware configuration)
- RPi.GPIO dependency
- GPIO button monitoring code
- button_debug configuration option

### Changed
- Simplified to automatic screen rotation only
- Reduced dependencies and complexity

## [1.3.1] - 2025-11-19

### Added
- Custom logo image support on logo screen
- Automatic image loading from `/data/` or `/config/` directories
- Support for PNG, JPG, and BMP image formats
- Automatic image conversion to monochrome
- Automatic image scaling to fit 128x64 display
- Fallback to text-based logo if no image found

### Changed
- Logo screen now displays custom image if available
- Image is automatically centered on screen

## [1.3.0] - 2025-11-19

### Added
- Inverted headers (white background, black text) for all screens
- Screen-specific icons (⚡ CPU, 💾 RAM, 💿 Storage, 🌡️ Temp, 🌐 Network, ⏰ Clock)
- Styled progress bars: striped (CPU), solid (RAM), dotted (Storage)
- Visual warning indicators when usage exceeds 80%
- Visual thermometer display on temperature screen
- Decorative borders and frames for logo and clock screens
- Connection status indicator on network screen
- Centered and bordered IP address display

### Changed
- Enhanced visual contrast and information hierarchy
- Improved layout spacing and positioning
- More dynamic and visually interesting displays

## [1.2.1] - 2025-11-19

### Fixed
- Corrected to use only GPIO 4 (the only available GPIO pin)
- Single button now cycles through all screens
- Simplified button handling for one button operation

## [1.2.0] - 2025-11-19

### Changed
- **MAJOR**: Switched from I2C to GPIO for button detection
- Using RPi.GPIO library for button handling
- Event-driven button detection with hardware debouncing (300ms)
- Immediate button response via GPIO callbacks

### Added
- RPi.GPIO dependency
- Pull-up resistors configuration for button
- Falling edge detection for button press

### Fixed
- Buttons now work correctly on Argon ONE OLED
- No more I2C polling errors

## [1.1.4] - 2025-11-19

### Fixed
- Button monitoring now uses discovered I2C addresses from device scan
- Excludes OLED address (0x3C) from button monitoring
- Remembers working I2C address to avoid repeated scanning
- Shows which I2C addresses will be monitored at startup
- Only logs I2C read errors for first 3 polls to reduce noise

### Changed
- Dynamic I2C address detection instead of hardcoded addresses
- Better thread startup logging

## [1.1.3] - 2025-11-19

### Fixed
- Added forced logging output with sys.stdout.flush() to ensure logs appear
- Button monitoring thread now logs first 10 polls regardless of debug setting
- Main loop logs first 10 iterations for troubleshooting
- Added thread alive status check
- Enhanced startup logging

## [1.1.2] - 2025-11-19

### Added
- I2C device scanning at startup to detect available devices
- Button debug mode configuration option
- Detailed logging of button press events with hex and binary values
- Multiple I2C address detection (tries 0x01, 0x1A, 0x20, 0x30)
- Enhanced button state detection with multiple bit pattern support

### Changed
- More verbose button press logging
- Better error reporting with stack traces
- Polls multiple I2C addresses to find buttons

## [1.1.1] - 2025-11-19

### Fixed
- Changed button implementation from GPIO to I2C polling
- Buttons now correctly read from I2C address 0x01
- Removed gpiod dependency (not needed)
- Button polling every 100ms for responsive input

## [1.1.0] - 2025-11-19

### Added
- Button support for manual screen navigation
- GPIO 4 button cycles to next screen
- GPIO 17 button cycles to previous screen
- Button presses reset auto-rotation timer
- Background thread for button monitoring

### Changed
- Using gpiod library for GPIO access
- Improved error handling for GPIO operations

## [1.0.3] - 2025-11-19

### Fixed
- Removed conflicting build dependencies (gcc, musl-dev) that caused package conflicts
- Simplified Dockerfile to only include necessary runtime dependencies
- Using system py3-pillow package to avoid compilation issues

## [1.0.2] - 2025-11-19

### Fixed
- Added gcc and build dependencies to prevent Pillow compilation errors
- Install luma.oled with --no-deps to use system Pillow package
- Added explicit luma.core installation to satisfy dependencies

## [1.0.1] - 2025-11-19

### Fixed
- Fixed Pillow build issues by using pre-built Alpine package instead of compiling from source
- Added necessary image library dependencies for OLED display

## [1.0.0] - 2025-11-19

### Added
- Initial release of Argon ONE OLED Display add-on for Home Assistant
- Support for multiple screen displays (logo, clock, cpu, ram, storage, temp, ip)
- Configurable screen rotation duration
- Temperature display in Celsius or Fahrenheit
- Real-time system monitoring
- Support for armhf, armv7, and aarch64 architectures

### Features
- Display current date and time
- CPU usage and temperature monitoring
- Memory usage statistics
- Disk usage information
- Network IP address display
- Argon ONE logo screen
