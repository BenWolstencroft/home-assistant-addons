# Argon ONE Home Assistant Add-ons

Home Assistant add-ons for Argon ONE cases.

## Add-ons

### [Argon ONE OLED Display](argon-oled-addon/)

Display system information on your Argon ONE case's OLED screen.

**Features:**
- 🖥️ Display system stats on 128x64 OLED
- 📊 Multiple screens: Logo, Clock, CPU, RAM, Storage, Temperature, IP
- 🔄 Automatic screen rotation
- 🌡️ Temperature in Celsius or Fahrenheit
- ⚡ Real-time monitoring

[View Documentation →](argon-oled-addon/README.md)

## Installation

### Method 1: Add Repository to Home Assistant

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** menu (three dots) in the top right
3. Select **Repositories**
4. Add: `https://github.com/yourusername/argon_oled`
5. Click **Add**
6. Install the add-on from the store

### Method 2: Manual Installation

1. Copy the addon folder to your Home Assistant `addons` directory
2. Restart Home Assistant
3. Install from the local add-ons section

## Requirements

- Argon ONE case with OLED display
- Raspberry Pi (any model supported by Argon ONE)
- Home Assistant OS or Supervised installation
- I2C enabled

## Support

- 🐛 [Report Issues](https://github.com/yourusername/argon_oled/issues)
- 💬 [Community Forum](https://community.home-assistant.io/)
- 📖 [Documentation](argon-oled-addon/README.md)

## Repository Structure

```
argon_oled/
├── argon-oled-addon/          # OLED Display Add-on
│   ├── argon_oled.py          # Main Python script
│   ├── run.sh                 # Entry point
│   ├── Dockerfile             # Docker configuration
│   ├── config.yaml            # Add-on configuration
│   ├── README.md              # Add-on documentation
│   └── ...                    # Other add-on files
├── original-script.sh         # Original Raspberry Pi OS script
├── CONVERSION_SUMMARY.md      # Conversion details
└── repository.json            # Repository configuration
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - See [LICENSE](argon-oled-addon/LICENSE) for details

## Credits

Based on the Argon ONE setup scripts from [Argon40](https://www.argon40.com/).
