# Argon ONE OLED Display Add-on for Home Assistant

Display system information on your Argon ONE case's OLED screen.

This add-on brings the functionality of the Argon ONE OLED display to Home Assistant, allowing you to monitor your system's vital statistics directly on the 128x64 OLED screen.

## Features

- 🖥️ Display system information on Argon ONE OLED screen
- 📊 Multiple screens: Logo, Clock, CPU, RAM, Storage, Temperature, IP
- 🔄 Automatic screen rotation with configurable duration
- 🌡️ Temperature display in Celsius or Fahrenheit
- ⚡ Real-time system monitoring
- 🔘 Physical button support (GPIO 4) to manually cycle through screens

## Supported Screens

The add-on can display the following screens:

- **logo** / **logo1v5** - Argon ONE logo screen
- **clock** - Current date and time
- **cpu** - CPU usage percentage and temperature
- **ram** - Memory usage and total memory
- **storage** - Disk usage and total storage
- **temp** - CPU temperature (large display)
- **ip** - Network IP address

## Installation

1. Add this repository to your Home Assistant Add-on Store
2. Click "Install" on the Argon ONE OLED Display add-on
3. Enable I2C on your Raspberry Pi if not already enabled
4. Configure the add-on (see Configuration section below)
5. Start the add-on

## Enabling I2C on Raspberry Pi

Before using this add-on, you need to enable I2C on your Raspberry Pi:

### For Home Assistant OS:

The I2C interface should be enabled by default. If you experience issues, you can enable it by:

1. SSH into your Home Assistant instance
2. Access the host: `login`
3. Run: `ha os config i2c true`
4. Reboot your system

### For manual installations:

1. SSH into your Raspberry Pi
2. Run: `sudo raspi-config`
3. Navigate to: Interface Options → I2C → Enable
4. Reboot your system

## Configuration

Example configuration:

```yaml
temp_unit: C
switch_duration: 30
screen_list: "logo clock cpu storage ram temp ip"
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
- `logo` or `logo1v5` - Argon ONE logo
- `clock` - Date and time
- `cpu` - CPU information
- `ram` - Memory information
- `storage` - Disk information
- `temp` - Temperature display
- `ip` - IP address

Example: `"logo clock cpu ram"`

Default: `"logo clock cpu storage ram temp ip"`

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
- GitHub Issues: [Your Repository URL]
- Home Assistant Community: [Forum Thread URL]

## Credits

Based on the Argon ONE setup script from Argon40.
Converted to Home Assistant add-on format.

## License

MIT License - See LICENSE file for details
