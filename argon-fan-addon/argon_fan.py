#!/usr/bin/env python3
"""
Argon ONE v5 Fan Control for Home Assistant
Based on argononed.py from Jeff Curless (https://github.com/JeffCurless/argoneon)
and Argon40's official scripts

This script controls the fan speed based on CPU temperature via I2C communication.
Fan Speed is set by sending 0 to 100 to the MCU (Micro Controller Unit)
The values are interpreted as percentage of fan speed, 100% being maximum.
"""

import sys
import os
import time
import json
import logging
from pathlib import Path

try:
    import smbus2 as smbus
except ImportError:
    import smbus

# I2C Configuration
ADDR_FAN = 0x1a
I2C_BUS = 1

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArgonFanController:
    """Controls the Argon ONE v5 fan via I2C"""
    
    def __init__(self, config_file='/data/options.json'):
        """Initialize the fan controller with configuration"""
        self.bus = None
        self.config = self.load_config(config_file)
        self.current_speed = 0
        self.temp_unit = self.config.get('temp_unit', 'C')
        self.check_interval = self.config.get('check_interval', 60)
        self.debug = self.config.get('debug_logging', False)
        
        # Parse fan temperature thresholds
        self.fan_config = {}
        cpu_fan_temps = self.config.get('cpu_fan_temps', [])
        for entry in cpu_fan_temps:
            temp = float(entry['temp'])
            speed = int(entry['speed'])
            self.fan_config[temp] = speed
        
        # Sort by temperature for proper lookup
        self.fan_config = dict(sorted(self.fan_config.items()))
        
        if self.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug(f"Fan configuration loaded: {self.fan_config}")
        
        self.init_i2c()
    
    def load_config(self, config_file):
        """Load configuration from Home Assistant options"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                logger.info("Configuration loaded successfully")
                return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return {
                'temp_unit': 'C',
                'cpu_fan_temps': [
                    {'temp': 55, 'speed': 30},
                    {'temp': 60, 'speed': 55},
                    {'temp': 65, 'speed': 100}
                ],
                'check_interval': 60,
                'debug_logging': False
            }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def init_i2c(self):
        """Initialize I2C bus communication"""
        try:
            self.bus = smbus.SMBus(I2C_BUS)
            logger.info(f"I2C bus {I2C_BUS} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize I2C bus: {e}")
            logger.error("Make sure I2C is enabled on your Raspberry Pi")
            sys.exit(1)
    
    def get_cpu_temp(self):
        """Read CPU temperature from the system"""
        try:
            # Try thermal_zone method first (most common)
            temp_file = '/sys/class/thermal/thermal_zone0/temp'
            if os.path.exists(temp_file):
                with open(temp_file, 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
                    if self.debug:
                        logger.debug(f"CPU temperature: {temp}°C")
                    return temp
            
            # Fallback to vcgencmd
            import subprocess
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                temp = float(temp_str.replace("temp=", "").replace("'C", ""))
                if self.debug:
                    logger.debug(f"CPU temperature (vcgencmd): {temp}°C")
                return temp
            
            logger.error("Unable to read CPU temperature")
            return 0.0
            
        except Exception as e:
            logger.error(f"Error reading CPU temperature: {e}")
            return 0.0
    
    def get_fan_speed(self, temp):
        """
        Calculate appropriate fan speed for given temperature.
        Uses stepped configuration from user settings.
        """
        speed = 0
        
        if len(self.fan_config) > 0:
            for threshold_temp in self.fan_config.keys():
                if temp >= threshold_temp:
                    speed = self.fan_config[threshold_temp]
                    if self.debug:
                        logger.debug(
                            f"Temperature ({temp}°C) >= {threshold_temp}°C, "
                            f"setting speed to {speed}%"
                        )
        
        if self.debug:
            logger.debug(f"Final fan speed: {speed}%")
        
        return speed
    
    def set_fan_speed(self, speed, instantaneous=True):
        """
        Set the fan speed via I2C.
        
        Args:
            speed: Fan speed percentage (0-100)
            instantaneous: If False, delay speed reduction by 30s to prevent fluctuations
        """
        # Validate speed range
        speed = max(0, min(100, speed))
        
        # If reducing speed and not instantaneous, wait to prevent fluctuations
        if speed < self.current_speed and not instantaneous:
            logger.debug("Delaying fan speed reduction by 30 seconds")
            time.sleep(30)
        
        # Only update if speed has changed
        if speed != self.current_speed:
            try:
                if speed > 0:
                    # Spin up to 100% first to prevent issues on older units
                    self.bus.write_byte(ADDR_FAN, 100)
                    time.sleep(1)
                
                # Set actual speed
                self.bus.write_byte(ADDR_FAN, int(speed))
                logger.info(f"Fan speed set to {speed}%")
                self.current_speed = speed
                
            except IOError as e:
                logger.error(f"I2C communication error while setting fan speed: {e}")
                logger.error("Check I2C connection and Argon ONE case")
            except Exception as e:
                logger.error(f"Unexpected error setting fan speed: {e}")
        else:
            if self.debug:
                logger.debug(f"Fan speed unchanged at {speed}%")
    
    def fan_off(self):
        """Turn the fan off"""
        logger.info("Turning fan off")
        self.set_fan_speed(0, instantaneous=True)
    
    def shutdown(self):
        """Signal shutdown to MCU"""
        logger.info("Sending shutdown signal to MCU")
        try:
            self.fan_off()
            self.bus.write_byte(ADDR_FAN, 0xFF)
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def run(self):
        """Main loop - monitor temperature and adjust fan speed"""
        logger.info("Starting Argon ONE fan control service")
        logger.info(f"Temperature unit: {self.temp_unit}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        logger.info(f"Fan configuration: {self.fan_config}")
        
        # Start with fan off
        self.fan_off()
        
        try:
            while True:
                # Get current CPU temperature
                cpu_temp = self.get_cpu_temp()
                
                if cpu_temp > 0:
                    # Calculate required fan speed
                    target_speed = self.get_fan_speed(cpu_temp)
                    
                    # Set fan speed (with delay for speed reduction)
                    self.set_fan_speed(target_speed, instantaneous=False)
                else:
                    logger.warning("Invalid temperature reading, skipping this cycle")
                
                # Wait before next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            self.fan_off()
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            self.fan_off()
            raise


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].upper()
        
        if cmd == "SHUTDOWN":
            logger.info("Shutdown command received")
            controller = ArgonFanController()
            controller.shutdown()
            return
        
        elif cmd == "FANOFF":
            logger.info("Fan off command received")
            controller = ArgonFanController()
            controller.fan_off()
            return
        
        elif cmd == "TEST":
            logger.info("Running fan test sequence")
            controller = ArgonFanController()
            
            logger.info("Testing fan at 30%...")
            controller.set_fan_speed(30)
            time.sleep(5)
            
            logger.info("Testing fan at 60%...")
            controller.set_fan_speed(60)
            time.sleep(5)
            
            logger.info("Testing fan at 100%...")
            controller.set_fan_speed(100)
            time.sleep(5)
            
            logger.info("Turning fan off...")
            controller.fan_off()
            return
    
    # Default: run the service
    controller = ArgonFanController()
    controller.run()


if __name__ == "__main__":
    main()
