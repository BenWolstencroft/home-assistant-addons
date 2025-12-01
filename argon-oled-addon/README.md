# Argon ONE OLED Display Add-on for Home Assistant

Display system information on your Argon ONE case's OLED screen.

This add-on brings the functionality of the Argon ONE OLED display to Home Assistant, allowing you to monitor your system's vital statistics directly on the 128x64 OLED screen.

## Features

### Display Screens
- 🖥️ **Logo Screen** - Argon ONE branding with decorative borders
- 🕐 **Clock Screen** - Digital 7-segment style time display with date
- 💻 **CPU Screen** - Usage percentage and temperature with progress bars
- 🧠 **RAM Screen** - Memory usage with detailed statistics
- 💾 **Storage Screen** - Disk space usage and availability
- 🌡️ **Temperature Screen** - Large temperature display with status indicator
- 🌀 **Fan Screen** - RPM speed and PWM duty cycle (Raspberry Pi 5 native fan)
- 🌐 **IP Screen** - Network IP address and connection status
- 📱 **QR Code Screen** - Scannable QR code for quick HA access
- 🏠 **HA Status Screen** - Updates available and last backup date
- 🎉 **Credits Screen** - Startup splash with GitHub QR code and version

### Core Features
- 🔄 Automatic screen rotation with configurable duration
- 🌡️ Temperature display in Celsius or Fahrenheit
- ⚡ Real-time system monitoring with modular architecture
- 📊 Progress bars with customizable units (%, °C, °F)
- 🔘 Physical button support (GPIO 4):
  - Single press: Next screen
  - Double press: Previous screen
  - Long press (6+ seconds): Jump to first screen
  - Hold 10 seconds: Reboot system (with confirmation)
  - Hold 15 seconds: Shutdown system (with confirmation)
- 🧪 Comprehensive unit test suite (100+ tests)
- 🐛 Debug logging option for troubleshooting

## Installation

1. Add this repository to your Home Assistant Add-on Store
2. Click "Install" on the Argon ONE OLED Display add-on
3. Enable I2C on your Raspberry Pi if not already enabled
4. Configure the add-on (see Configuration section below)
5. Start the add-on

## Enabling I2C on Raspberry Pi

Before using this add-on, you need to enable I2C on your Raspberry Pi.

The easiest way to enable I2C on Home Assistant OS is to install the **[I2C Configurator](https://github.com/adamoutler/HassOSConfigurator)** community add-on:

1. Add the repository: `https://github.com/adamoutler/HassOSConfigurator`
2. Install the "I2C Configurator" add-on
3. Start the add-on to enable I2C
4. Restart your system

The I2C interface should then be available for this add-on to use.

## Enabling the Raspberry Pi 5 Fan (Required for Fan Screen)

**Important:** For the Fan screen to work on Raspberry Pi 5, you must enable the native fan controller in Home Assistant OS.

Edit `/mnt/boot/config.txt` and add the following configuration in the `[all]` section:

```ini
[all]

# Fan configuration (Raspberry Pi 5)
dtparam=fan_temp0=35000
dtparam=fan_temp0_hyst=5000
dtparam=fan_temp0_speed=75

dtparam=fan_temp1=50000
dtparam=fan_temp1_hyst=5000
dtparam=fan_temp1_speed=125

dtparam=fan_temp2=60000
dtparam=fan_temp2_hyst=5000
dtparam=fan_temp2_speed=175

dtparam=fan_temp3=65000
dtparam=fan_temp3_hyst=5000
dtparam=fan_temp3_speed=250
```

**Configuration explanation:**
- `fan_temp0-3`: Temperature thresholds in millidegrees Celsius (35000 = 35°C)
- `fan_temp0-3_hyst`: Hysteresis (temperature drop before changing speed)
- `fan_temp0-3_speed`: PWM speed (0-255, where 255 = 100% speed)

This creates a 4-level fan curve:
- **35°C**: 30% speed (75/255)
- **50°C**: 49% speed (125/255)
- **60°C**: 69% speed (175/255)
- **65°C**: 98% speed (250/255)

After editing, reboot your system for the changes to take effect. The Fan screen will then display RPM and PWM percentage.

## Configuration

Example configuration:

```yaml
temp_unit: C
switch_duration: 30
screen_list: "logo clock cpu storage ram temp fan ip qr hastatus"
debug_logging: false
show_credits: true
```

### Option: `temp_unit`

Temperature display unit.

- **C** - Celsius (default)
- **F** - Fahrenheit

Default: `C`

### Option: `switch_duration`

Time in seconds to display each screen before switching to the next.

Range: 5-300 seconds

Default: `30`

### Option: `screen_list`

Space-separated list of screens to display in rotation.

Available screens:
- `logo` - Argon ONE logo with decorative borders
- `clock` - Date and time with 7-segment digits
- `cpu` - CPU usage and temperature with progress bars
- `ram` - Memory usage statistics with progress bar
- `storage` - Disk space information with progress bar
- `temp` - Large temperature display with status classification
- `fan` - Fan RPM and PWM duty cycle (Raspberry Pi 5 native fan)
- `ip` - Network IP address with connection status
- `qr` - QR code for Home Assistant URL
- `hastatus` - HA system status (updates, backups)

Example: `"logo clock cpu ram fan qr hastatus"`

Default: `"logo clock cpu storage ram temp fan ip"`

### Option: `debug_logging`

Enable detailed debug logging for troubleshooting.

- **true** - Enable debug logs
- **false** - Normal logging (default)

Default: `false`

### Option: `show_credits`

Show credits splash screen on startup with GitHub QR code and version number.

- **true** - Show credits screen once at startup (default)
- **false** - Skip credits screen

Default: `true`

## Hardware Requirements

- Argon ONE case with OLED display (128x64 SSD1306)
- Raspberry Pi (any model supported by Argon ONE)
- I2C enabled on the Raspberry Pi

## Troubleshooting

### OLED screen not working

1. **Check I2C is enabled:**
   ```bash
   ls /dev/i2c-*
   ```
   You should see at least `/dev/i2c-1`

2. **Check if OLED is detected:**
   ```bash
   i2cdetect -y 1
   ```
   You should see a device at address 0x3C (3c)

3. **Check add-on logs:**
   - Go to the add-on page in Home Assistant
   - Click on the "Log" tab
   - Look for error messages

### Screen displays wrong information

- Restart the add-on
- Check your configuration settings
- Verify the screen_list contains valid screen names

### Temperature showing incorrect values

- Make sure you've selected the correct temp_unit (C or F)
- The temperature sensor reads from the Raspberry Pi's CPU

## Architecture

This add-on uses a modular Python architecture:

- **argon_oled.py** - Main orchestrator (screen rotation, button monitoring, power management)
- **system_info.py** - System metrics collection (CPU, memory, disk, temperature)
- **supervisor_api.py** - Home Assistant Supervisor API client
- **screens.py** - OLED screen rendering logic (all draw methods)
- **tests/** - Comprehensive unit test suite (100+ tests, hardware-independent)

The modular design allows for:
- Easy testing without physical hardware
- Clean separation of concerns
- Simple addition of new screens
- Cross-platform development (Windows, Linux, Mac)

## Button Controls

The physical button on GPIO 4 provides multiple functions:

| Action | Function |
|--------|----------|
| Single press | Next screen |
| Double press | Previous screen |
| Long press (6s) | Jump to first screen |
| Hold 10s | Reboot system* |
| Hold 15s | Shutdown system* |

*Requires `hassio_role: manager` permission. A 5-second confirmation countdown is displayed before executing power commands.

## Support

For issues, questions, or contributions:
- GitHub Repository: [https://github.com/BenWolstencroft/home-assistant-addons](https://github.com/BenWolstencroft/home-assistant-addons)
- Home Assistant Community: [https://community.home-assistant.io/t/argon-indistria-oled-module-one-v5-addon/952927](https://community.home-assistant.io/t/argon-indistria-oled-module-one-v5-addon/952927)

## Credits

Developed by Ben Wolstencroft

Based on the Argon ONE setup script from Argon40.
Converted to Home Assistant add-on format with extensive enhancements.

## License

MIT License - See LICENSE file for details
