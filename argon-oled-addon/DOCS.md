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
python3 argon_oled.py
```

## Project Structure

```
.
├── argon_oled.py       # Main Python script for OLED display
├── run.sh              # Entry point script
├── Dockerfile          # Docker build configuration
├── config.yaml         # Add-on configuration
├── build.yaml          # Build configuration for multiple architectures
├── apparmor.txt        # AppArmor security profile
├── README.md           # User documentation
├── CHANGELOG.md        # Version history
├── DOCS.md             # This file
└── LICENSE             # License information
```

## Configuration Options

See README.md for detailed configuration options.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
