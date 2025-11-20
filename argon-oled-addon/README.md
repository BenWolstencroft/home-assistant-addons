# Argon ONE OLED Display Add-on for Home Assistant

Display system information on your Argon ONE case's OLED screen.

This add-on brings the functionality of the Argon ONE OLED display to Home Assistant, allowing you to monitor your system's vital statistics directly on the 128x64 OLED screen.

## Features

- 🖥️ Display system information on Argon ONE OLED screen
- 📊 Multiple screens: Logo, Clock, CPU, RAM, Storage, Temperature, IP, QR Code, HA Status
- 🔄 Automatic screen rotation with configurable duration
- 🌡️ Temperature display in Celsius or Fahrenheit
- ⚡ Real-time system monitoring
- 📱 QR code for quick Home Assistant access from mobile devices
- 🏠 Home Assistant system status monitoring (updates, backups)
- 🔘 Physical button support (GPIO 4) to manually cycle through screens

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

## Configuration

Example configuration:

```yaml
temp_unit: C
switch_duration: 30
screen_list: "logo clock cpu storage ram temp ip qr hastatus"
```

### Option: `temp_unit`

Temperature display unit.

- **C** - Celsius
- **F** - Fahrenheit

Default: `C`

### Option: `switch_duration`

Time in seconds to display each screen before switching to the next.

Range: 5-300 seconds

Default: `30`

### Option: `screen_list`

Space-separated list of screens to display in rotation.

Available screens:
- `logo` - Argon ONE logo (supports custom images)
- `clock` - Date and time
- `cpu` - CPU information
- `ram` - Memory information
- `storage` - Disk information
- `temp` - Temperature display
- `ip` - IP address (host IP)
- `qr` - QR code for Home Assistant URL
- `hastatus` - Home Assistant system status

Example: `"logo clock cpu ram qr hastatus"`

Default: `"logo clock cpu storage ram temp ip qr hastatus"`

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

## Support

For issues, questions, or contributions:
- GitHub Issues: [https://github.com/BenWolstencroft/home-assistant-addons](https://github.com/BenWolstencroft/home-assistant-addons)
- Home Assistant Community: [https://community.home-assistant.io/t/argon-indistria-oled-module-one-v5-addon/952927](https://community.home-assistant.io/t/argon-indistria-oled-module-one-v5-addon/952927)

## Credits

Based on the Argon ONE setup script from Argon40.
Converted to Home Assistant add-on format.

## License

MIT License - See LICENSE file for details
