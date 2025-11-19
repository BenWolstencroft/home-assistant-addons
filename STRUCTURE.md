# Project Structure

This repository contains Home Assistant add-ons for Argon ONE cases.

## Directory Structure

```
argon_oled/
│
├── argon-oled-addon/              # The Home Assistant Add-on
│   ├── argon_oled.py              # Main Python application
│   ├── run.sh                     # Entry point script
│   ├── Dockerfile                 # Docker build file
│   ├── config.yaml                # Add-on configuration
│   ├── build.yaml                 # Multi-arch build config
│   ├── apparmor.txt               # Security profile
│   ├── addon.json                 # Add-on metadata
│   ├── README.md                  # Add-on documentation
│   ├── QUICKSTART.md              # Installation guide
│   ├── DOCS.md                    # Developer docs
│   ├── CHANGELOG.md               # Version history
│   ├── LICENSE                    # MIT license
│   └── ICON_README.txt            # Icon instructions
│
├── original-script.sh             # Original Raspberry Pi OS script (reference)
├── CONVERSION_SUMMARY.md          # Details of conversion process
├── repository.json                # HA repository configuration
├── README.md                      # This repository's README
└── .gitignore                     # Git ignore rules
```

## Add-ons Included

### 1. Argon ONE OLED Display (`argon-oled-addon/`)

Displays system information on the Argon ONE OLED screen.

**Status:** ✅ Ready for use

**See:** [argon-oled-addon/README.md](argon-oled-addon/README.md)

## Future Add-ons

Potential future additions:
- Fan control add-on
- Power button handler
- Combined Argon ONE suite

## Installation

Add this repository to Home Assistant:

```
https://github.com/yourusername/argon_oled
```

Then install individual add-ons from the Add-on Store.

## Development

Each add-on is self-contained in its own directory with all necessary files.

To test an add-on locally:
```bash
cd argon-oled-addon
docker build -t test-addon .
```

## Contributing

Contributions welcome! Each add-on should:
- Be in its own directory
- Include complete documentation
- Follow Home Assistant add-on best practices
- Include proper licensing

## License

MIT License - See individual add-on LICENSE files for details.
