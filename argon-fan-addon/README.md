# Argon ONE Active Cooling for Home Assistant

![Supports aarch64 Architecture][aarch64-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports armhf Architecture][armhf-shield]

Temperature-based fan control for the Argon ONE v5 case.

## About

This Home Assistant add-on provides automatic fan control for the Argon ONE v5 Raspberry Pi case. It monitors the CPU temperature and adjusts the fan speed accordingly via I2C communication.

The add-on is based on the excellent work by:
- [Jeff Curless's argoneon repository](https://github.com/JeffCurless/argoneon)
- Argon40's official scripts

## Features

- 🌡️ **Automatic Temperature Monitoring**: Continuously monitors CPU temperature
- 💨 **Smart Fan Control**: Adjusts fan speed based on configurable temperature thresholds
- ⚙️ **Fully Configurable**: Set your own temperature/speed curves
- 🔄 **Smooth Transitions**: Delays fan speed reduction to prevent fluctuations
- 🐛 **Debug Mode**: Optional detailed logging for troubleshooting
- 🛡️ **Safe Shutdown**: Properly turns off fan on addon stop

## Installation

1. Add this repository to your Home Assistant instance
2. Install the "Argon ONE Active Cooling" add-on
3. Configure the temperature thresholds (optional)
4. Start the add-on

## Configuration

### Default Configuration

```yaml
temp_unit: C
cpu_fan_temps:
  - temp: 55
    speed: 30
  - temp: 60
    speed: 55
  - temp: 65
    speed: 100
check_interval: 60
debug_logging: false
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `temp_unit` | string | `C` | Temperature unit (C or F) |
| `cpu_fan_temps` | list | See above | Temperature thresholds and corresponding fan speeds |
| `cpu_fan_temps[].temp` | int | - | Temperature threshold (30-85°C) |
| `cpu_fan_temps[].speed` | int | - | Fan speed percentage (0-100%) |
| `check_interval` | int | `60` | How often to check temperature (10-300 seconds) |
| `debug_logging` | bool | `false` | Enable detailed debug logging |

### Example: Quiet Profile

```yaml
temp_unit: C
cpu_fan_temps:
  - temp: 60
    speed: 25
  - temp: 70
    speed: 50
  - temp: 75
    speed: 100
check_interval: 60
debug_logging: false
```

### Example: Performance Profile

```yaml
temp_unit: C
cpu_fan_temps:
  - temp: 50
    speed: 40
  - temp: 55
    speed: 60
  - temp: 60
    speed: 80
  - temp: 65
    speed: 100
check_interval: 30
debug_logging: false
```

## Requirements

- Argon ONE v5 case (or compatible case)
- I2C must be enabled on your Raspberry Pi
- Home Assistant OS or Supervised installation

## How It Works

1. The add-on reads the CPU temperature every `check_interval` seconds
2. It compares the temperature against your configured thresholds
3. The fan speed is set to the highest speed for which the temperature threshold is met
4. When reducing fan speed, the add-on waits 30 seconds to prevent fluctuations
5. Fan speed changes are communicated to the Argon ONE case via I2C (address 0x1a)

## Troubleshooting

### Fan not responding

1. Check if I2C is enabled:
   - The add-on will warn if `/dev/i2c-1` is not found
   - Enable I2C in the Raspberry Pi configuration

2. Verify the Argon ONE case is properly connected

3. Check the add-on logs for I2C communication errors

4. Enable `debug_logging: true` for detailed information

### I2C Not Available

If you see "I2C device not found" warnings:

1. Make sure you're running on a Raspberry Pi with the Argon ONE case
2. Verify I2C is enabled in your system configuration
3. Check that the case's ribbon cable is properly connected

## Support

For issues and questions:
- Check the [GitHub repository](https://github.com/BenWolstencroft/home-assistant-addons)
- Review the add-on logs in Home Assistant
- Enable debug logging for more detailed information

## Credits

- [Argon40](https://www.argon40.com/) - Original hardware and scripts
- [Jeff Curless](https://github.com/JeffCurless/argoneon) - Enhanced Argon scripts

## License

MIT License - See LICENSE file for details

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
