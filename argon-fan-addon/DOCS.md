# Configuration

The Argon ONE Active Cooling add-on allows you to control the fan in your Argon ONE v5 case based on CPU temperature.

## Temperature Unit

```yaml
temp_unit: C
```

Choose between Celsius (`C`) or Fahrenheit (`F`). This affects how you configure temperature thresholds.

## Fan Temperature Configuration

The `cpu_fan_temps` option allows you to define temperature thresholds and corresponding fan speeds.

```yaml
cpu_fan_temps:
  - temp: 55
    speed: 30
  - temp: 60
    speed: 55
  - temp: 65
    speed: 100
```

### How it works

- **temp**: Temperature threshold in your chosen unit (30-85°C or 86-185°F)
- **speed**: Fan speed percentage (0-100%)

The fan will run at the speed corresponding to the highest temperature threshold that has been reached.

**Example**: With the default configuration:
- Below 55°C: Fan off (0%)
- 55°C - 59°C: Fan at 30%
- 60°C - 64°C: Fan at 55%
- 65°C and above: Fan at 100%

### Recommended Profiles

#### Quiet Profile (Lower noise, higher temps)
```yaml
cpu_fan_temps:
  - temp: 60
    speed: 25
  - temp: 70
    speed: 50
  - temp: 75
    speed: 100
```

#### Balanced Profile (Default)
```yaml
cpu_fan_temps:
  - temp: 55
    speed: 30
  - temp: 60
    speed: 55
  - temp: 65
    speed: 100
```

#### Performance Profile (Lower temps, more noise)
```yaml
cpu_fan_temps:
  - temp: 50
    speed: 40
  - temp: 55
    speed: 60
  - temp: 60
    speed: 80
  - temp: 65
    speed: 100
```

#### Always On Profile
```yaml
cpu_fan_temps:
  - temp: 30
    speed: 30
  - temp: 60
    speed: 60
  - temp: 70
    speed: 100
```

## Check Interval

```yaml
check_interval: 60
```

How often (in seconds) the add-on checks the CPU temperature and adjusts the fan speed.

- **Minimum**: 10 seconds
- **Maximum**: 300 seconds (5 minutes)
- **Default**: 60 seconds (1 minute)

Lower values mean more responsive fan control but slightly higher CPU usage.

## Debug Logging

```yaml
debug_logging: false
```

Enable detailed logging to help troubleshoot issues.

When enabled, the add-on will log:
- CPU temperature readings
- Fan speed calculations
- I2C communication details
- Configuration details

Set to `true` if you're experiencing issues or want to verify the add-on is working correctly.

## Fan Behavior

### Speed Reduction Delay

When the temperature decreases, the add-on waits 30 seconds before reducing the fan speed. This prevents rapid fluctuations in fan speed due to brief temperature spikes.

### Spin-up Sequence

When setting a new fan speed greater than 0%, the fan is briefly spun up to 100% for 1 second before being set to the target speed. This helps ensure reliable operation, especially on older units.

## Example Configuration

```yaml
temp_unit: C
cpu_fan_temps:
  - temp: 50
    speed: 20
  - temp: 55
    speed: 30
  - temp: 60
    speed: 50
  - temp: 65
    speed: 70
  - temp: 70
    speed: 100
check_interval: 45
debug_logging: false
```

This configuration:
- Uses Celsius
- Has 5 temperature thresholds for fine-grained control
- Checks temperature every 45 seconds
- Starts the fan at 20% when reaching 50°C
- Ramps up gradually to 100% at 70°C

## Troubleshooting

If the fan isn't responding as expected:

1. Enable `debug_logging: true` to see detailed information
2. Check the add-on logs for I2C errors
3. Verify your temperature thresholds are appropriate for your system
4. Ensure the Argon ONE case is properly connected
5. Check that I2C is enabled on your Raspberry Pi

## Technical Details

- **I2C Address**: 0x1a
- **I2C Bus**: 1 (default on Raspberry Pi)
- **Fan Speed Range**: 0-100 (percentage)
- **Temperature Source**: `/sys/class/thermal/thermal_zone0/temp` or `vcgencmd measure_temp`
