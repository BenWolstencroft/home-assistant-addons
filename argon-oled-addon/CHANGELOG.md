# Changelog

All notable changes to this project will be documented in this file.

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
