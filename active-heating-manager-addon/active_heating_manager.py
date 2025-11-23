#!/usr/bin/env python3
"""
Active Heating Manager for Home Assistant
"""
import os
import sys
import time
import json
import logging
import requests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG_LOGGING', 'false').lower() == 'true' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Home Assistant supervisor token for API access
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN', '')
HA_API_URL = 'http://supervisor/core/api'


def load_config():
    """Load configuration from options.json."""
    try:
        with open('/data/options.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return {
            'debug_logging': False,
            'trv_entities': [],
            'boiler_thermostat_entity': '',
            'polling_interval': 300
        }


def get_entity_state(entity_id):
    """Get entity state and attributes from Home Assistant."""
    headers = {
        'Authorization': f'Bearer {SUPERVISOR_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    try:
        url = f'{HA_API_URL}/states/{entity_id}'
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get state for {entity_id}: {e}")
        return None


def call_service(domain, service, entity_id, service_data=None):
    """Call a Home Assistant service."""
    headers = {
        'Authorization': f'Bearer {SUPERVISOR_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    data = {'entity_id': entity_id}
    if service_data:
        data.update(service_data)
    
    try:
        url = f'{HA_API_URL}/services/{domain}/{service}'
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully called {domain}.{service} on {entity_id}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call {domain}.{service} on {entity_id}: {e}")
        return False


def boost_boiler_thermostat(entity_id, duration_minutes=15):
    """Boost the boiler thermostat for specified duration."""
    logger.info(f"Boosting boiler thermostat {entity_id} for {duration_minutes} minutes")
    
    # Call the climate.set_preset_mode service with 'boost' preset
    # Most thermostats use this, but we'll also try a generic approach
    success = call_service('climate', 'set_preset_mode', entity_id, {'preset_mode': 'boost'})
    
    if success:
        # If the thermostat supports boost duration, set it
        # This varies by thermostat model, so we try common methods
        call_service('number', 'set_value', entity_id.replace('climate.', 'number.') + '_boost_time', 
                    {'value': duration_minutes})
    
    return success


def cancel_boost_boiler_thermostat(entity_id):
    """Cancel boost on the boiler thermostat by returning it to schedule/auto mode."""
    logger.info(f"Cancelling boost on boiler thermostat {entity_id}")
    
    # First, check the current preset mode
    state_data = get_entity_state(entity_id)
    if state_data:
        attributes = state_data.get('attributes', {})
        current_preset = attributes.get('preset_mode', 'none')
        
        # Only cancel if currently in boost mode
        if current_preset == 'boost':
            logger.info(f"Thermostat is in boost mode, cancelling...")
            # Try common preset modes to return to normal operation
            # Try 'schedule' first (most common), then 'auto', then 'none'
            for preset in ['schedule', 'auto', 'none']:
                if call_service('climate', 'set_preset_mode', entity_id, {'preset_mode': preset}):
                    logger.info(f"Successfully set preset to '{preset}'")
                    return True
            return False
        else:
            logger.info(f"Thermostat not in boost mode (current: {current_preset}), no action needed")
            return True
    else:
        logger.warning(f"Could not get state for {entity_id}, cannot cancel boost")
        return False


def poll_trv_entities(trv_entities, boiler_thermostat_entity=None):
    """Poll all configured TRV entities and manage boiler based on heating demand."""
    logger.info(f"Polling {len(trv_entities)} TRV entities...")
    
    any_trv_heating = False
    
    for entity_id in trv_entities:
        state_data = get_entity_state(entity_id)
        
        if state_data:
            state = state_data.get('state', 'unknown')
            attributes = state_data.get('attributes', {})
            
            logger.info(f"TRV {entity_id}:")
            logger.info(f"  State: {state}")
            logger.debug(f"  Attributes: {json.dumps(attributes, indent=2)}")
            
            # Log key attributes if available
            if 'current_temperature' in attributes:
                logger.info(f"  Current temp: {attributes['current_temperature']}")
            if 'temperature' in attributes:
                logger.info(f"  Target temp: {attributes['temperature']}")
            if 'hvac_action' in attributes:
                hvac_action = attributes['hvac_action']
                logger.info(f"  HVAC action: {hvac_action}")
                
                # Check if this TRV is actively heating
                if hvac_action == 'heating':
                    any_trv_heating = True
                    logger.info(f"  -> TRV is heating!")
        else:
            logger.warning(f"Could not retrieve state for {entity_id}")
    
    # If any TRV is heating and we have a boiler thermostat configured, boost it
    if boiler_thermostat_entity:
        if any_trv_heating:
            logger.info("At least one TRV is heating - triggering/extending boiler boost")
            boost_boiler_thermostat(boiler_thermostat_entity, duration_minutes=15)
        else:
            logger.info("No TRVs currently heating - cancelling any active boost")
            cancel_boost_boiler_thermostat(boiler_thermostat_entity)
    elif any_trv_heating:
        logger.warning("TRVs are heating but no boiler thermostat entity configured")
    
    return any_trv_heating


def main():
    """Main entry point for the Active Heating Manager."""
    logger.info("Active Heating Manager starting...")
    
    # Load configuration
    config = load_config()
    
    # Update logging level if debug enabled
    if config.get('debug_logging', False):
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    trv_entities = config.get('trv_entities', [])
    boiler_thermostat_entity = config.get('boiler_thermostat_entity', '')
    polling_interval = config.get('polling_interval', 300)
    
    logger.info(f"Configured with {len(trv_entities)} TRV entities")
    logger.info(f"Boiler thermostat entity: {boiler_thermostat_entity or 'Not configured'}")
    logger.info(f"Polling interval: {polling_interval} seconds")
    
    if not trv_entities:
        logger.warning("No TRV entities configured!")
    
    if not boiler_thermostat_entity:
        logger.warning("No boiler thermostat entity configured - boiler control disabled")
    
    try:
        # Main loop
        while True:
            poll_trv_entities(trv_entities, boiler_thermostat_entity)
            logger.debug(f"Sleeping for {polling_interval} seconds...")
            time.sleep(polling_interval)
            
    except KeyboardInterrupt:
        logger.info("Shutting down Active Heating Manager...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
