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


def poll_trv_entities(trv_entities):
    """Poll all configured TRV entities and log their states."""
    logger.info(f"Polling {len(trv_entities)} TRV entities...")
    
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
                logger.info(f"  HVAC action: {attributes['hvac_action']}")
        else:
            logger.warning(f"Could not retrieve state for {entity_id}")


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
    polling_interval = config.get('polling_interval', 300)
    
    logger.info(f"Configured with {len(trv_entities)} TRV entities")
    logger.info(f"Polling interval: {polling_interval} seconds")
    
    if not trv_entities:
        logger.warning("No TRV entities configured!")
    
    try:
        # Main loop
        while True:
            poll_trv_entities(trv_entities)
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
