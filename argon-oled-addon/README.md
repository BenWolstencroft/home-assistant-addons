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
- 🔘 Physical button support, from the kernel power key or from GPIO 4:
  - Single press: Next screen
  - Double press: Previous screen
  - Long press (about 0.6 seconds): Jump to first screen
  - Hold 10 seconds: Reboot system (with confirmation)
  - Hold 15 seconds: Shutdown system (with confirmation)
- 🌙 Optional blank-until-button mode: the panel stays fully off until the case button is pressed, then turns off again after an idle timeout. Button actions are the same in that mode.
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
screen_off_until_button: false
idle_dim_timeout: 60
button_source: power_key
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

### Option: `screen_off_until_button`

Keep the OLED off until the case button is pressed. This uses the SSD1306 display-off command (not a black image), so the panel has no residual glow while it is idle.

- **false** - Normal behaviour: the panel is on and rotates screens (default)
- **true** - Boot with the panel off. A button press turns it on and the usual rotation resumes. After `idle_dim_timeout` seconds without a button press, the panel turns off again.

The press that wakes the panel is still a normal press. Single press moves to the next screen, double press to the previous screen, a long press jumps to the first screen, and holding for 10 or 15 seconds still opens the reboot or shutdown confirmation. The confirmation (and its 5-second cancel countdown) is drawn after the panel is switched back on, including when the hold starts with the display dark. Cancelling the confirmation leaves the panel on and restarts the idle timer.

The startup credits splash is skipped in this mode so the screen does not light during boot. The button keeps working the whole time the panel is off, including the reboot and shutdown holds.

Default: `false`

### Option: `idle_dim_timeout`

How long, in seconds, the panel stays on after the last button press when `screen_off_until_button` is enabled. The timer restarts on every press. This option has no effect when `screen_off_until_button` is `false`.

Range: 5-3600 seconds

Default: `60`

### Option: `button_source`

Which input the case button is read from. The gestures are the same either way: single press next screen, double press (second click within 0.5s) previous screen, long press (about 0.6s) first screen, hold 10s reboot confirmation, hold 15s shutdown confirmation.

- **power_key** - Read `KEY_POWER` events from the kernel `pwr_button` input device (default). This is the correct choice for an Argon ONE V5 on Home Assistant OS. On that hardware GPIO line 4 stays high and never reports a press; the kernel gpio-keys driver already publishes the button as an input device. The event number is discovered from `/proc/bus/input/devices` (it is not hardcoded). The device is not exclusively grabbed, so systemd-logind still sees the key.
- **gpio** - Poll GPIO line 4, active-low, as in v1.17.0 and earlier. Use this on a board where that line really is the case button.

If the selected source cannot be opened, the add-on log prints a warning that names `button_source` and the value to switch to. It does not silently change source, and the button does nothing until the option matches the hardware.

On Home Assistant OS, logind is configured with `HandlePowerKey=ignore` and `HandlePowerKeyLongPress=poweroff`. A short press does not shut the Pi down (that matches a short press, a double press, and the ~0.6s "first screen" hold). A hold of about 5 seconds powers the host off before this add-on's 10 second reboot and 15 second shutdown prompts can finish. To use those two holds, set `HandlePowerKeyLongPress=ignore` in the host's `/etc/systemd/logind.conf` and restart logind. This add-on does not take the key away from logind.

Default: `power_key`

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

The physical button provides multiple functions. On an Argon ONE V5 running Home Assistant OS, set `button_source: power_key` (the default). Set `button_source: gpio` only when the button is actually GPIO line 4.

| Action | Function |
|--------|----------|
| Single press | Next screen |
| Double press (within 0.5s) | Previous screen |
| Long press (about 0.6s) | Jump to first screen |
| Hold 10s | Reboot system* |
| Hold 15s | Shutdown system* |

*Requires `hassio_role: manager` permission. A 5-second confirmation countdown is displayed before executing power commands. With `screen_off_until_button` enabled, the press turns the display on first, including when a hold starts while the panel is dark.

On HAOS the host still receives the power key. A short press does not shut down. A hold of about 5 seconds does (`HandlePowerKeyLongPress=poweroff`) unless that host setting is changed to `ignore`. See `button_source` above.

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
