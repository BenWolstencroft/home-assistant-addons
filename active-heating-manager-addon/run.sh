#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Active Heating Manager
# Runs the Active Heating Manager service
# ==============================================================================

bashio::log.info "Starting Active Heating Manager Add-on..."

# Parse configuration
DEBUG_LOGGING=$(bashio::config 'debug_logging')

# Log configuration
bashio::log.info "Debug logging: ${DEBUG_LOGGING}"

# Export configuration as environment variables
export DEBUG_LOGGING

# Start the main Python script
bashio::log.info "Starting heating manager service..."
exec python3 /active_heating_manager.py
