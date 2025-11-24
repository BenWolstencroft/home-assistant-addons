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
            'boiler_entity': '',
            'boiler_mode': 'thermostat',
            'manual_on_temperature': 21,
            'manual_off_temperature': 14,
            'check_valve_state': True,
            'use_dynamic_temperature': True,
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


def set_entity_state(entity_id, state, attributes=None):
    """Set entity state in Home Assistant."""
    headers = {
        'Authorization': f'Bearer {SUPERVISOR_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    data = {
        'state': state,
        'attributes': attributes or {}
    }
    
    try:
        url = f'{HA_API_URL}/states/{entity_id}'
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        logger.debug(f"Successfully set state for {entity_id} to {state}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to set state for {entity_id}: {e}")
        return False


def set_manual_temperature_thermostat(entity_id, target_temperature):
    """Set thermostat to manual mode with high temperature to trigger heating."""
    # Round to nearest 0.5°C (whole or half degrees)
    target_temperature = round(target_temperature * 2) / 2
    logger.info(f"Setting thermostat {entity_id} to manual mode with temperature {target_temperature}°C")
    
    # First, set to manual/away/none preset to enable manual temperature control
    state_data = get_entity_state(entity_id)
    if state_data:
        attributes = state_data.get('attributes', {})
        current_preset = attributes.get('preset_mode', 'none')
        current_temp = attributes.get('temperature', 0)
        
        # If already at target temperature in a non-schedule mode, no action needed
        if current_temp == target_temperature and current_preset != 'schedule':
            logger.info(f"Already at target temperature {target_temperature}°C")
            return True
        
        # Try to set preset to manual/none to allow temperature override
        for preset in ['none', 'manual', 'away']:
            if call_service('climate', 'set_preset_mode', entity_id, {'preset_mode': preset}):
                logger.info(f"Set preset to '{preset}'")
                break
    
    # Set the target temperature
    return call_service('climate', 'set_temperature', entity_id, {'temperature': target_temperature})


def set_manual_off_temperature_thermostat(entity_id, off_temperature):
    """Set thermostat to manual mode with low temperature when no heating demand."""
    # Round to nearest 0.5°C (whole or half degrees)
    off_temperature = round(off_temperature * 2) / 2
    logger.info(f"Setting thermostat {entity_id} to manual mode with off temperature {off_temperature}°C")
    
    # First, set to manual/none preset to enable manual temperature control
    state_data = get_entity_state(entity_id)
    if state_data:
        attributes = state_data.get('attributes', {})
        current_preset = attributes.get('preset_mode', 'none')
        current_temp = attributes.get('temperature', 0)
        
        # If already at off temperature in a non-schedule mode, no action needed
        if current_temp == off_temperature and current_preset != 'schedule':
            logger.info(f"Already at off temperature {off_temperature}°C")
            return True
        
        # Try to set preset to manual/none to allow temperature override
        for preset in ['none', 'manual']:
            if call_service('climate', 'set_preset_mode', entity_id, {'preset_mode': preset}):
                logger.info(f"Set preset to '{preset}'")
                break
    
    # Set the off temperature
    return call_service('climate', 'set_temperature', entity_id, {'temperature': off_temperature})


def turn_on_boiler_toggle(entity_id):
    """Turn on the boiler toggle switch."""
    logger.info(f"Turning on boiler toggle {entity_id}")
    
    # Check current state first
    state_data = get_entity_state(entity_id)
    if state_data:
        current_state = state_data.get('state', 'unknown')
        if current_state == 'on':
            logger.info(f"Toggle already on, no action needed")
            return True
        else:
            logger.info(f"Toggle is {current_state}, turning on...")
    
    # Determine domain from entity_id
    domain = entity_id.split('.')[0] if '.' in entity_id else 'switch'
    return call_service(domain, 'turn_on', entity_id)


def turn_off_boiler_toggle(entity_id):
    """Turn off the boiler toggle switch."""
    logger.info(f"Turning off boiler toggle {entity_id}")
    
    # Check current state first
    state_data = get_entity_state(entity_id)
    if state_data:
        current_state = state_data.get('state', 'unknown')
        if current_state == 'off':
            logger.info(f"Toggle already off, no action needed")
            return True
        else:
            logger.info(f"Toggle is {current_state}, turning off...")
    
    # Determine domain from entity_id
    domain = entity_id.split('.')[0] if '.' in entity_id else 'switch'
    return call_service(domain, 'turn_off', entity_id)


def get_valve_state(trv_entity_id):
    """Check if the valve for a TRV is open. Returns True if open/unknown, False if closed."""
    # Convert climate.xxx_trv to binary_sensor.xxx_trv_valve_state
    if '.' not in trv_entity_id:
        return True  # If invalid entity format, assume valve is open
    
    # Extract the name part
    domain, name = trv_entity_id.split('.', 1)
    
    # Try common valve state entity patterns
    valve_entity_patterns = [
        f'binary_sensor.{name}_valve_state',
        f'binary_sensor.{name.replace("_trv", "")}_valve_state',
        f'sensor.{name}_valve_state',
    ]
    
    for valve_entity_id in valve_entity_patterns:
        state_data = get_entity_state(valve_entity_id)
        if state_data:
            state = state_data.get('state', 'unknown').lower()
            logger.debug(f"Found valve sensor {valve_entity_id} with state: {state}")
            
            # Check for open states
            if state in ['open', 'opened', 'on', 'true']:
                return True
            elif state in ['closed', 'off', 'false']:
                return False
            else:
                logger.debug(f"Unknown valve state '{state}', assuming open")
                return True
    
    # No valve sensor found, assume valve is operational
    logger.debug(f"No valve sensor found for {trv_entity_id}, assuming valve is open")
    return True


def get_valve_position(trv_entity_id):
    """Get the valve position percentage for a TRV. Returns None if not available."""
    if '.' not in trv_entity_id:
        return None
    
    # Extract the name part
    domain, name = trv_entity_id.split('.', 1)
    
    # Try common valve position entity patterns
    position_entity_patterns = [
        f'sensor.{name}_position',
        f'sensor.{name.replace("_trv", "")}_position',
        f'number.{name}_position',
    ]
    
    for position_entity_id in position_entity_patterns:
        state_data = get_entity_state(position_entity_id)
        if state_data:
            state = state_data.get('state', 'unknown')
            try:
                position = float(state)
                logger.debug(f"Found valve position sensor {position_entity_id} with position: {position}%")
                return position
            except (ValueError, TypeError):
                logger.debug(f"Invalid position value '{state}' for {position_entity_id}")
                continue
    
    logger.debug(f"No valve position sensor found for {trv_entity_id}")
    return None


def publish_heating_stats(heating_active, trv_count_heating, avg_valve_position, target_temp, boiler_mode):
    """Publish heating statistics as sensor entities to Home Assistant."""
    
    # Main heating status sensor
    set_entity_state(
        'sensor.active_heating_manager_status',
        'heating' if heating_active else 'idle',
        {
            'friendly_name': 'Active Heating Manager Status',
            'icon': 'mdi:radiator' if heating_active else 'mdi:radiator-off',
            'trvs_heating': trv_count_heating,
            'mode': boiler_mode
        }
    )
    
    # TRVs heating count sensor
    set_entity_state(
        'sensor.active_heating_manager_trvs_heating',
        str(trv_count_heating),
        {
            'friendly_name': 'TRVs Heating',
            'icon': 'mdi:counter',
            'unit_of_measurement': 'TRVs'
        }
    )
    
    # Average valve position sensor (if available)
    if avg_valve_position is not None:
        set_entity_state(
            'sensor.active_heating_manager_avg_valve_position',
            str(round(avg_valve_position, 1)),
            {
                'friendly_name': 'Average Valve Position',
                'icon': 'mdi:valve',
                'unit_of_measurement': '%'
            }
        )
    
    # Target boiler temperature sensor (only in thermostat mode)
    if boiler_mode == 'thermostat' and target_temp is not None:
        set_entity_state(
            'sensor.active_heating_manager_target_temp',
            str(target_temp),
            {
                'friendly_name': 'Boiler Target Temperature',
                'icon': 'mdi:thermometer',
                'unit_of_measurement': '°C',
                'device_class': 'temperature'
            }
        )


def calculate_dynamic_temperature(avg_valve_position, boiler_entity, manual_on_temp, manual_off_temp):
    """Calculate target temperature based on average valve position.
    
    Args:
        avg_valve_position: Average valve position percentage (0-100)
        boiler_entity: Boiler thermostat entity ID
        manual_on_temp: Maximum temperature to set
        manual_off_temp: Minimum temperature to set
    
    Returns:
        Target temperature in degrees Celsius
    """
    logger.debug(f"=== Dynamic Temperature Calculation ===")
    logger.debug(f"Input: avg_valve_position={avg_valve_position}%, manual_off={manual_off_temp}°C, manual_on={manual_on_temp}°C")
    
    if avg_valve_position <= 0:
        logger.debug(f"Valve position is 0%, returning manual_off_temp: {manual_off_temp}°C")
        return manual_off_temp
    
    # Get current boiler temperature
    state_data = get_entity_state(boiler_entity)
    current_boiler_temp = manual_off_temp
    if state_data:
        attributes = state_data.get('attributes', {})
        current_temp = attributes.get('current_temperature')
        logger.debug(f"Boiler thermostat current_temperature attribute: {current_temp}")
        if current_temp is not None:
            try:
                current_boiler_temp = float(current_temp)
                logger.debug(f"Using boiler current temperature: {current_boiler_temp}°C")
            except (ValueError, TypeError):
                logger.warning(f"Invalid current temperature value: {current_temp}, using fallback: {manual_off_temp}°C")
    else:
        logger.debug(f"Could not get boiler state, using fallback temperature: {manual_off_temp}°C")
    
    # At 25%, set to current temp + 0.5°C
    # Between 25% and 100%, scale linearly to manual_on_temp
    if avg_valve_position <= 25:
        # Scale from manual_off_temp at 0% to current_temp + 0.5 at 25%
        target_at_25 = current_boiler_temp + 0.5
        logger.debug(f"Valve position <= 25%: scaling from {manual_off_temp}°C (0%) to {target_at_25}°C (25%)")
        # Linear interpolation between 0% and 25%
        target_temp = manual_off_temp + (target_at_25 - manual_off_temp) * (avg_valve_position / 25)
        logger.debug(f"Interpolation: {manual_off_temp} + ({target_at_25} - {manual_off_temp}) * ({avg_valve_position} / 25) = {target_temp}°C")
    else:
        # Scale from current_temp + 0.5 at 25% to manual_on_temp at 100%
        target_at_25 = current_boiler_temp + 0.5
        logger.debug(f"Valve position > 25%: scaling from {target_at_25}°C (25%) to {manual_on_temp}°C (100%)")
        # Linear interpolation between 25% and 100%
        target_temp = target_at_25 + (manual_on_temp - target_at_25) * ((avg_valve_position - 25) / 75)
        logger.debug(f"Interpolation: {target_at_25} + ({manual_on_temp} - {target_at_25}) * (({avg_valve_position} - 25) / 75) = {target_temp}°C")
    
    # Ensure we stay within bounds
    before_bounds = target_temp
    target_temp = max(manual_off_temp, min(manual_on_temp, target_temp))
    if before_bounds != target_temp:
        logger.debug(f"Applied bounds: {before_bounds}°C → {target_temp}°C")
    
    # Round to nearest 0.5°C (whole or half degrees)
    before_rounding = target_temp
    target_temp = round(target_temp * 2) / 2
    logger.debug(f"Rounded to nearest 0.5°C: {before_rounding}°C → {target_temp}°C")
    logger.debug(f"=== Final target temperature: {target_temp}°C ===")
    
    return target_temp


def poll_trv_entities(trv_entities, boiler_entity=None, boiler_mode='thermostat', manual_on_temperature=21, manual_off_temperature=14, check_valve_state=True, use_dynamic_temperature=True):
    """Poll all configured TRV entities and manage boiler based on heating demand."""
    logger.info(f"Polling {len(trv_entities)} TRV entities...")
    
    any_trv_heating = False
    valve_positions = []  # Store positions of valves that are heating
    
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
                    # Check valve state if enabled
                    valve_open = True
                    if check_valve_state:
                        valve_open = get_valve_state(entity_id)
                        logger.info(f"  Valve state: {'open' if valve_open else 'closed'}")
                    
                    if valve_open:
                        any_trv_heating = True
                        logger.info(f"  -> TRV is heating with valve open!")
                        
                        # Get valve position for dynamic temperature calculation
                        if use_dynamic_temperature:
                            position = get_valve_position(entity_id)
                            if position is not None:
                                valve_positions.append(position)
                                logger.info(f"  Valve position: {position}%")
                    else:
                        logger.info(f"  -> TRV is heating but valve is closed, ignoring demand")
        else:
            logger.warning(f"Could not retrieve state for {entity_id}")
    
    # Calculate average valve position
    avg_valve_position = None
    trv_count_heating = sum(1 for _ in range(len([e for e in trv_entities if any_trv_heating])))
    if valve_positions:
        avg_valve_position = sum(valve_positions) / len(valve_positions)
        logger.info(f"Average valve position across {len(valve_positions)} heating TRVs: {avg_valve_position:.1f}%")
        trv_count_heating = len(valve_positions)  # More accurate count
    elif any_trv_heating:
        # Count TRVs that are heating even if no position sensors
        trv_count_heating = len([e for e in trv_entities if any_trv_heating])  # This is a simplified count
    
    target_temp = None
    
    # Manage boiler based on heating demand and configured mode
    if boiler_entity:
        if any_trv_heating:
            if boiler_mode == 'thermostat':
                # Calculate target temperature based on valve positions if dynamic mode enabled
                if use_dynamic_temperature and valve_positions:
                    target_temp = calculate_dynamic_temperature(
                        avg_valve_position, 
                        boiler_entity, 
                        manual_on_temperature, 
                        manual_off_temperature
                    )
                    logger.info(f"At least one TRV is heating - setting dynamic temperature to {target_temp}°C (based on {avg_valve_position:.1f}% avg valve position)")
                    set_manual_temperature_thermostat(boiler_entity, target_temp)
                else:
                    target_temp = manual_on_temperature
                    logger.info(f"At least one TRV is heating - setting manual temperature to {manual_on_temperature}°C")
                    set_manual_temperature_thermostat(boiler_entity, manual_on_temperature)
            else:  # toggle mode
                logger.info("At least one TRV is heating - turning on boiler toggle")
                turn_on_boiler_toggle(boiler_entity)
        else:
            if boiler_mode == 'thermostat':
                target_temp = manual_off_temperature
                logger.info(f"No TRVs currently heating - setting manual temperature to {manual_off_temperature}°C")
                set_manual_off_temperature_thermostat(boiler_entity, manual_off_temperature)
            else:  # toggle mode
                logger.info("No TRVs currently heating - turning off boiler toggle")
                turn_off_boiler_toggle(boiler_entity)
    elif any_trv_heating:
        logger.warning("TRVs are heating but no boiler entity configured")
    
    # Publish statistics to Home Assistant
    publish_heating_stats(any_trv_heating, trv_count_heating, avg_valve_position, target_temp, boiler_mode)
    
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
    boiler_entity = config.get('boiler_entity', config.get('boiler_thermostat_entity', ''))  # Backwards compatibility
    boiler_mode = config.get('boiler_mode', 'thermostat')
    manual_on_temperature = config.get('manual_on_temperature', 21)
    manual_off_temperature = config.get('manual_off_temperature', 14)
    check_valve_state = config.get('check_valve_state', True)
    use_dynamic_temperature = config.get('use_dynamic_temperature', True)
    polling_interval = config.get('polling_interval', 300)
    
    logger.info(f"Configured with {len(trv_entities)} TRV entities")
    logger.info(f"Boiler entity: {boiler_entity or 'Not configured'}")
    logger.info(f"Boiler mode: {boiler_mode}")
    if boiler_mode == 'thermostat':
        logger.info(f"Manual ON temperature: {manual_on_temperature}°C")
        logger.info(f"Manual OFF temperature: {manual_off_temperature}°C")
        logger.info(f"Use dynamic temperature: {use_dynamic_temperature}")
    logger.info(f"Check valve state: {check_valve_state}")
    logger.info(f"Polling interval: {polling_interval} seconds")
    
    if not trv_entities:
        logger.warning("No TRV entities configured!")
    
    if not boiler_entity:
        logger.warning("No boiler entity configured - boiler control disabled")
    
    try:
        # Main loop
        while True:
            poll_trv_entities(trv_entities, boiler_entity, boiler_mode, manual_on_temperature, manual_off_temperature, check_valve_state, use_dynamic_temperature)
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
