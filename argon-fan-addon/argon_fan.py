#!/usr/bin/env python3
"""
Argon ONE Fan Control for Home Assistant
Based on argononed.py from Jeff Curless (https://github.com/JeffCurless/argoneon)
and Adam Outler's HassOS Argon One Addon (https://github.com/adamoutler/HassOSArgonOneAddon)

This script controls the fan speed based on CPU temperature via I2C communication.
Fan Speed is set by sending 0 to 100 to the MCU (Micro Controller Unit)
The values are interpreted as percentage of fan speed, 100% being maximum.
"""

import sys
import os
import time
import json
import logging
import subprocess
from pathlib import Path

try:
    from smbus2 import SMBus
    SMBUS_MODULE = 'smbus2'
except ImportError:
    try:
        from smbus import SMBus
        SMBUS_MODULE = 'smbus'
    except ImportError:
        print("ERROR: No smbus library available")
        sys.exit(1)

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
        self.bus_num = None
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
        logger.info("Scanning I2C buses for Argon ONE device...")
        detected_bus = None
        
        # Scan common I2C buses to find the Argon ONE device
        for bus_num in [1, 0, 13, 14, 3, 10, 11, 22]:
            if not os.path.exists(f'/dev/i2c-{bus_num}'):
                continue
                
            try:
                logger.debug(f"Checking I2C bus {bus_num}...")
                # Use i2cdetect to check if device is present
                result = subprocess.run(
                    ['i2cdetect', '-y', str(bus_num)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and ' 1a ' in result.stdout:
                    logger.info(f"✓ Found Argon ONE device on I2C bus {bus_num} at address 0x1a")
                    detected_bus = bus_num
                    break
            except Exception as e:
                logger.debug(f"Error scanning bus {bus_num}: {e}")
        
        if detected_bus is None:
            logger.error("Failed to detect Argon ONE device on any I2C bus")
            logger.error("Possible issues:")
            logger.error("  1. I2C is not enabled on your Raspberry Pi")
            logger.error("  2. Argon ONE case is not properly connected")
            logger.error("  3. Wrong I2C address (expected 0x1a)")
            logger.error("")
            logger.error("Available I2C devices:")
            i2c_devs = sorted([d for d in os.listdir('/dev') if d.startswith('i2c-')])
            for dev in i2c_devs:
                logger.error(f"  /dev/{dev}")
            logger.error("")
            logger.error("Please enable I2C and verify device is connected.")
            sys.exit(1)
        
        # Open the detected I2C bus
        try:
            self.bus = SMBus(detected_bus)
            self.bus_num = detected_bus
            logger.info(f"✓ I2C bus {detected_bus} initialized successfully using {SMBUS_MODULE}")
        except Exception as e:
            logger.error(f"Failed to open I2C bus {detected_bus}: {e}")
            sys.exit(1)
    
    def get_cpu_temp(self):
        """Read CPU temperature from the system"""
        try:
            # Try thermal_zone method (standard Linux method)
            temp_file = '/sys/class/thermal/thermal_zone0/temp'
            if os.path.exists(temp_file):
                with open(temp_file, 'r') as f:
                    # Temperature is in millidegrees Celsius
                    temp = float(f.read().strip()) / 1000.0
                    if self.debug:
                        logger.debug(f"CPU temperature: {temp}°C")
                    return temp
            
            # Fallback to vcgencmd (Raspberry Pi specific)
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                # Parse output like "temp=45.0'C"
                temp_str = result.stdout.strip()
                temp = float(temp_str.replace("temp=", "").replace("'C", ""))
                if self.debug:
                    logger.debug(f"CPU temperature (vcgencmd): {temp}°C")
                return temp
            
            logger.error("Unable to read CPU temperature from any source")
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
        speed = max(0, min(100, int(speed)))
        
        # If reducing speed and not instantaneous, wait to prevent fluctuations
        if speed < self.current_speed and not instantaneous:
            if self.debug:
                logger.debug("Delaying fan speed reduction by 30 seconds to prevent fluctuations")
            time.sleep(30)
        
        # Only update if speed has changed
        if speed != self.current_speed:
            try:
                if speed > 0:
                    # Spin up to 100% first to prevent issues on older units
                    # This is critical for Argon ONE hardware
                    if self.debug:
                        logger.debug("Spinning up fan to 100% before setting target speed")
                    self.bus.write_byte(ADDR_FAN, 100)
                    time.sleep(1)
                
                # Set actual speed
                self.bus.write_byte(ADDR_FAN, speed)
                logger.info(f"Fan speed set to {speed}%")
                self.current_speed = speed
                
            except IOError as e:
                logger.error(f"I2C communication error: {e}")
                logger.error(f"Failed to communicate with device at 0x{ADDR_FAN:02x} on bus {self.bus_num}")
                logger.error("Possible causes:")
                logger.error("  - Device disconnected or powered off")
                logger.error("  - I2C bus issue")
                logger.error("  - Insufficient permissions")
                # Don't exit, just skip this update
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
        """Signal shutdown to MCU - sends 0xFF to trigger shutdown"""
        logger.info("Sending shutdown signal to MCU")
        try:
            # First turn off the fan
            self.bus.write_byte(ADDR_FAN, 0)
            time.sleep(0.1)
            # Then send shutdown signal
            self.bus.write_byte(ADDR_FAN, 0xFF)
            logger.info("Shutdown signal sent successfully")
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
