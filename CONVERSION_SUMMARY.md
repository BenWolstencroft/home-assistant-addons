# Conversion Summary: Argon ONE OLED to Home Assistant Add-on

## What Was Done

The original Raspberry Pi OS installation script (`original-script.sh`) has been converted into a proper Home Assistant add-on. Here's what changed:

### 1. Core Functionality Extracted
From the 806-line installation script, we extracted the essential OLED display functionality and created a clean, focused Python application.

### 2. Files Created/Modified

#### New Files:
- **argon_oled.py** - Main Python script that handles OLED display
  - Displays system stats (CPU, RAM, storage, temperature, IP, clock)
  - Rotates between screens at configurable intervals
  - Uses luma.oled library for display control

- **run.sh** - Entry point script
  - Reads configuration from Home Assistant
  - Sets up environment variables
  - Starts the Python service

- **README.md** - User documentation
- **DOCS.md** - Developer documentation
- **CHANGELOG.md** - Version history
- **LICENSE** - MIT license
- **addon.json** - Add-on metadata
- **repository.json** - Repository configuration
- **.gitignore** - Git ignore rules

#### Modified Files:
- **Dockerfile** - Updated to:
  - Use Home Assistant base images
  - Install Python 3 and required packages (smbus2, luma.oled, Pillow)
  - Copy the necessary scripts

- **config.yaml** - Simplified to:
  - Remove fan control options (not part of OLED functionality)
  - Add OLED-specific options (temp_unit, switch_duration, screen_list)
  - Proper schema validation

#### Existing Files (kept):
- **build.yaml** - Already correct for multi-arch builds
- **apparmor.txt** - Security profile for I2C access

## Key Differences from Original Script

### Original Script (original-script.sh):
- 806 lines of bash
- Installs system packages
- Configures hardware (I2C, UART, EEPROM)
- Sets up systemd services
- Handles fan control, IR, RTC, and OLED
- Downloads additional scripts from Argon40 servers
- Creates desktop shortcuts

### New Add-on:
- Focused only on OLED display functionality
- Self-contained Python application
- No system modifications required
- Configuration through Home Assistant UI
- Runs in Docker container
- No external dependencies on Argon40 servers

## Configuration Options

The add-on offers three simple configuration options:

1. **temp_unit** - Display temperature in Celsius or Fahrenheit
2. **switch_duration** - Seconds between screen changes (5-300)
3. **screen_list** - Which screens to display and in what order

## What's NOT Included

The following features from the original script are NOT in this add-on:
- Fan control (requires different approach in Home Assistant)
- IR receiver configuration
- RTC (Real-time clock) setup
- Power button functionality
- EEPROM configuration
- System-level Raspberry Pi configuration

These could be added as separate add-ons or features in the future.

## How to Use

1. Enable I2C on your Raspberry Pi
2. Install the add-on in Home Assistant
3. Configure the options
4. Start the add-on
5. Enjoy your OLED display showing system stats!

## Next Steps

To use this add-on:

1. **Enable I2C** on your Raspberry Pi (if not already done)
2. **Push to GitHub** - Create a new repository and push these files
3. **Add to Home Assistant** - Add your repository to the Add-on Store
4. **Install** - Install the add-on from the store
5. **Configure** - Adjust settings to your preference
6. **Start** - Start the add-on and watch your OLED come to life!

## Testing Locally

Before publishing, you can test the add-on locally:

```bash
# Build the Docker image
docker build -t argon-oled-test .

# Run it with your configuration
docker run --rm -it \
  --device /dev/i2c-1 \
  -e TEMP_UNIT=C \
  -e SWITCH_DURATION=30 \
  -e SCREEN_LIST="logo clock cpu ram temp ip" \
  argon-oled-test
```

## Troubleshooting

If the display doesn't work:
1. Check I2C is enabled: `ls /dev/i2c-*`
2. Detect OLED: `i2cdetect -y 1` (should show device at 0x3C)
3. Check add-on logs in Home Assistant
4. Verify screen_list contains valid screen names

## Architecture

The add-on supports:
- armhf (32-bit ARM)
- armv7 (32-bit ARM v7)
- aarch64 (64-bit ARM)

All common Raspberry Pi models are supported.
