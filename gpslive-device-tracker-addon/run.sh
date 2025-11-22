#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: GPSLive Device Tracker
# Runs the GPSLive device tracker service
# ==============================================================================

bashio::log.info "Starting GPSLive Device Tracker Add-on..."

# Parse configuration
DEBUG_LOGGING=$(bashio::config 'debug_logging')

# Log configuration
bashio::log.info "Debug logging: ${DEBUG_LOGGING}"

# Export configuration as environment variables
export DEBUG_LOGGING

# Start the main Python script
bashio::log.info "Starting GPSLive tracker service..."
exec python3 /gpslive_tracker.py
