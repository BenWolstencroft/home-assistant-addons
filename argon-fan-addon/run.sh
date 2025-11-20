#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Argon ONE Active Cooling
# Runs the Argon ONE v5 fan control service
# ==============================================================================

bashio::log.info "Starting Argon ONE Active Cooling Add-on..."

# Parse configuration
TEMP_UNIT=$(bashio::config 'temp_unit')
CHECK_INTERVAL=$(bashio::config 'check_interval')
DEBUG_LOGGING=$(bashio::config 'debug_logging')

# Log configuration
bashio::log.info "Temperature unit: ${TEMP_UNIT}"
bashio::log.info "Check interval: ${CHECK_INTERVAL}s"
bashio::log.info "Debug logging: ${DEBUG_LOGGING}"

# Display fan temperature configuration
bashio::log.info "Fan temperature thresholds:"
CONFIG_JSON=$(bashio::config 'cpu_fan_temps')
echo "${CONFIG_JSON}" | jq -r '.[] | "  " + (.temp|tostring) + "°C -> " + (.speed|tostring) + "% fan speed"' 2>/dev/null || bashio::log.info "  (using default configuration)"

# Check if I2C device is available
if [ ! -c /dev/i2c-1 ]; then
    bashio::log.warning "I2C device not found at /dev/i2c-1"
    bashio::log.warning "Make sure I2C is enabled on your Raspberry Pi"
    bashio::log.warning "Trying to detect available I2C devices..."
    ls -la /dev/i2c-* 2>/dev/null || bashio::log.error "No I2C devices found!"
fi

# Test I2C communication
if command -v i2cdetect &> /dev/null; then
    bashio::log.info "Scanning I2C bus for Argon ONE device (0x1a)..."
    if i2cdetect -y 1 2>/dev/null | grep -q " 1a "; then
        bashio::log.info "✓ Argon ONE device detected at address 0x1a"
    else
        bashio::log.warning "⚠ Argon ONE device not detected at expected address 0x1a"
        bashio::log.warning "The addon will still attempt to communicate with the device"
    fi
fi

# Ensure configuration file exists in /data
if [ ! -f /data/options.json ]; then
    bashio::log.info "Creating options.json in /data directory..."
    cp /data/options.json /data/options.json.bak 2>/dev/null || true
fi

# Handle shutdown signals gracefully
trap 'bashio::log.info "Received shutdown signal, turning off fan..."; python3 /argon_fan.py FANOFF; exit 0' SIGTERM SIGINT

# Run the fan control script
bashio::log.info "Starting fan control service..."
python3 /argon_fan.py
