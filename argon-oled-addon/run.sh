#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Argon ONE OLED Display
# Runs the Argon ONE OLED display service
# ==============================================================================

bashio::log.info "Starting Argon ONE OLED Display Add-on..."

# Parse configuration
TEMP_UNIT=$(bashio::config 'temp_unit')
SWITCH_DURATION=$(bashio::config 'switch_duration')
SCREEN_LIST=$(bashio::config 'screen_list')
DEBUG_LOGGING=$(bashio::config 'debug_logging')

# Log configuration
bashio::log.info "Temperature unit: ${TEMP_UNIT}"
bashio::log.info "Screen switch duration: ${SWITCH_DURATION}s"
bashio::log.info "Screen list: ${SCREEN_LIST}"
bashio::log.info "Debug logging: ${DEBUG_LOGGING}"

# Check if I2C device is available
if [ ! -c /dev/i2c-1 ]; then
    bashio::log.warning "I2C device not found at /dev/i2c-1"
    bashio::log.warning "Make sure I2C is enabled on your Raspberry Pi"
    bashio::log.warning "Trying to detect available I2C devices..."
    ls -la /dev/i2c-* 2>/dev/null || bashio::log.error "No I2C devices found!"
fi

# Export configuration as environment variables for Python script
export TEMP_UNIT="${TEMP_UNIT}"
export SWITCH_DURATION="${SWITCH_DURATION}"
export SCREEN_LIST="${SCREEN_LIST}"
export DEBUG_LOGGING="${DEBUG_LOGGING}"

# Run the OLED display script
bashio::log.info "Starting OLED display service..."
python3 /argon_oled.py
