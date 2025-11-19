# Quick Start Guide

## Installation Steps

### 1. Enable I2C on Raspberry Pi

For Home Assistant OS:
```bash
# SSH into Home Assistant
# Access host
login

# Enable I2C
ha os config i2c true

# Reboot
reboot
```

### 2. Add Repository to Home Assistant

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** menu (three dots) in the top right
3. Select **Repositories**
4. Add: `https://github.com/yourusername/argon-oled-ha-addon`
5. Click **Add**

### 3. Install the Add-on

1. Find "Argon ONE OLED Display" in the add-on store
2. Click on it
3. Click **Install**
4. Wait for installation to complete

### 4. Configure

1. Go to the **Configuration** tab
2. Adjust settings:
   - **temp_unit**: `C` or `F`
   - **switch_duration**: `30` (seconds)
   - **screen_list**: `"logo clock cpu ram temp ip"`
3. Click **Save**

### 5. Start

1. Go to the **Info** tab
2. Toggle **Start on boot** (recommended)
3. Click **Start**

### 6. Check Logs

1. Go to the **Log** tab
2. Verify no errors
3. Should see: "Starting Argon OLED Display"

## Verify I2C is Working

Before installation, verify your I2C setup:

```bash
# List I2C devices
ls -la /dev/i2c-*

# Should see: /dev/i2c-1

# Detect OLED display
i2cdetect -y 1

# Should show:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
# 40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 70: -- -- -- -- -- -- -- --
```

## Default Configuration

```yaml
temp_unit: C
switch_duration: 30
screen_list: "logo clock cpu storage ram temp ip"
```

## Available Screens

- `logo` or `logo1v5` - Argon ONE logo
- `clock` - Date and time
- `cpu` - CPU usage and temperature
- `ram` - Memory usage
- `storage` - Disk usage
- `temp` - Temperature (large)
- `ip` - IP address

## Customizing Screen List

Show only specific screens:
```yaml
screen_list: "clock cpu temp"
```

Change order:
```yaml
screen_list: "logo ip clock"
```

## Troubleshooting

### Display not working?

1. Check I2C is enabled
2. Check logs for errors
3. Restart add-on
4. Reboot Raspberry Pi

### Wrong temperature?

Change temp_unit from C to F (or vice versa)

### Screens changing too fast/slow?

Adjust switch_duration (5-300 seconds)

## Support

- Check README.md for detailed documentation
- Check DOCS.md for development information
- Review logs in Home Assistant
- GitHub Issues: [Your Repository URL]

## Next Steps

- Customize screen_list to your preference
- Adjust switch_duration for optimal viewing
- Enable "Start on boot" for automatic startup
- Consider creating a dashboard card to control settings
