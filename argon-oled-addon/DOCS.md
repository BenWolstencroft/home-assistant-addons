# Argon ONE OLED Home Assistant Add-on

This is a Home Assistant add-on for the Argon ONE case OLED display.

## Development

### Building locally

```bash
docker build -t argon-oled-test .
```

### Testing

```bash
docker run --rm -it \
  --device /dev/i2c-1 \
  -e TEMP_UNIT=C \
  -e SWITCH_DURATION=30 \
  -e SCREEN_LIST="logo clock cpu ram" \
  argon-oled-test
```

### Debugging

To debug the Python script:

```bash
python3 argon_oled.py
```

Make sure to set environment variables before running:

```bash
export TEMP_UNIT=C
export SWITCH_DURATION=30
export SCREEN_LIST="logo clock cpu ram"
export DEBUG_LOGGING=true
export SHOW_CREDITS=true
export ADDON_VERSION=1.15.0
export SUPERVISOR_TOKEN=your_token_here
python3 argon_oled.py
```

For unit testing without hardware:

```bash
# Test a specific module
python -m unittest tests.test_system_info -v

# Test all modules
python -m unittest discover -s tests -v
```

## Project Structure

```
.
├── argon_oled.py          # Main orchestrator (538 lines)
├── system_info.py         # System metrics collection module
├── supervisor_api.py      # Home Assistant Supervisor API client
├── screens.py             # Screen rendering module (all draw methods)
├── run.sh                 # Entry point script
├── Dockerfile             # Docker build configuration
├── config.yaml            # Add-on configuration
├── build.yaml             # Build configuration for multiple architectures
├── apparmor.txt           # AppArmor security profile
├── README.md              # User documentation
├── CHANGELOG.md           # Version history
├── DOCS.md                # This file
├── LICENSE                # License information
└── tests/                 # Unit test suite
    ├── test_system_info.py
    ├── test_supervisor_api.py
    ├── test_screens.py
    ├── run_tests.sh
    └── README_TESTING.md
```

## Modular Architecture

The addon uses a modular design:

- **argon_oled.py** - Main entry point, handles:
  - Screen rotation logic
  - Button monitoring (GPIO)
  - Power management (reboot/shutdown)
  - Credits splash screen on startup
  
- **system_info.py** - System metrics:
  - CPU usage and temperature
  - Memory usage (used, total, percentage)
  - Disk usage (used, total, percentage)
  
- **supervisor_api.py** - HA integration:
  - IP address detection
  - Home Assistant URL
  - System status (updates, backups)
  - Host reboot/shutdown commands
  
- **screens.py** - All rendering logic:
  - 10 different screen types
  - Progress bar rendering with custom units
  - 7-segment digit drawing
  - QR code generation

## Testing

The addon includes comprehensive unit tests:

```bash
# Run all tests
cd tests
./run_tests.sh

# Or use Python directly
cd argon-oled-addon
python -m unittest discover -s tests -v
```

Tests cover:
- System information collection
- Supervisor API interactions
- Screen rendering logic
- Error handling and edge cases

Tests are hardware-independent using mocks, allowing development on Windows, Linux, or Mac without physical Raspberry Pi or OLED display.

## Configuration Options

See README.md for detailed configuration options.

## Development Workflow

1. Make code changes
2. Run unit tests: `python -m unittest discover -s tests -v`
3. Test locally with Docker (optional)
4. Update CHANGELOG.md and version in config.yaml
5. Commit and push changes

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add/update unit tests for your changes
4. Ensure all tests pass
5. Update documentation (README.md, CHANGELOG.md)
6. Submit a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use descriptive variable names
- Add docstrings to functions and classes
- Keep functions focused and modular
- Write unit tests for new features
