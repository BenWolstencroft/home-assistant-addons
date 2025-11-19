# Changelog

All notable changes to this project will be documented in this file.

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
