#!/usr/bin/env python3
"""
Argon ONE OLED Display Service for Home Assistant
Displays system information on the Argon ONE OLED screen
"""

import time
import os
import sys
import threading
from datetime import datetime
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import qrcode
import requests

# Import our modules
from system_info import SystemInfo
from supervisor_api import SupervisorAPI
from screens import ScreenRenderer

try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False

try:
    import gpiod
    from gpiod.line import Direction, Value
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    Direction = None
    Value = None

# Configuration
I2C_BUS = 1
I2C_ADDRESS = 0x3C
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
SWITCH_DURATION = 30  # seconds between screens
PIN_BUTTON = 4  # BCM Pin 4 for button

# Home Assistant API
SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN', '')
HA_API_URL = 'http://supervisor/core/api'


class ArgonOLED:
    """Argon ONE OLED Display Manager"""
    
    def __init__(self, screen_list, switch_duration=30, temp_unit='C', debug_logging=False, show_credits=True, version="1.0.0"):
        """Initialize the OLED display"""
        try:
            self.serial = i2c(port=I2C_BUS, address=I2C_ADDRESS)
            self.device = ssd1306(self.serial, width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
            self.device.clear()
        except Exception as e:
            print(f"Error initializing OLED: {e}")
            sys.exit(1)
        
        self.screen_list = screen_list
        self.switch_duration = switch_duration
        self.temp_unit = temp_unit
        self.debug_logging = debug_logging
        self.show_credits = show_credits
        self.version = version
        self.credits_shown = False
        self.current_screen = 0
        self.last_switch = time.time()
        self.button_action = None  # For button press communication
        self.power_management_enabled = False  # Will be set after permission check
        self.button_in_power_hold = False  # Track when button is held for reboot/shutdown
        
        # Initialize our modules
        self.system_info = SystemInfo(temp_unit=temp_unit)
        self.supervisor_api = SupervisorAPI(debug_callback=self.debug_log)
        
        # Check if we have permissions for host power management
        self.check_power_permissions()
        
        # Initialize GPIO for button if available
        self.gpio_chip = None
        self.gpio_line = None
        if GPIO_AVAILABLE:
            # First, list available GPIO chips
            print("Checking for available GPIO chips...")
            import glob
            gpio_chips = sorted(glob.glob('/dev/gpiochip*'))
            if gpio_chips:
                print(f"Found GPIO chips: {', '.join(gpio_chips)}")
            else:
                print("No /dev/gpiochip* devices found")
            
            # Try each available GPIO chip
            for chip_path in gpio_chips:
                try:
                    print(f"Trying to request line {PIN_BUTTON} on {chip_path}...")
                    
                    # Use gpiod.request_lines() with LineSettings
                    self.gpio_line = gpiod.request_lines(
                        chip_path,
                        consumer="argon_oled",
                        config={
                            PIN_BUTTON: gpiod.LineSettings(
                                direction=Direction.INPUT,
                                bias=gpiod.line.Bias.PULL_UP
                            )
                        },
                    )
                    print(f"GPIO initialized successfully on {chip_path} pin {PIN_BUTTON}")
                    
                    # Test reading the line
                    val = self.gpio_line.get_value(PIN_BUTTON)
                    print(f"Button initial state: {val}")
                    break
                        
                except Exception as e:
                    print(f"Failed to request line on {chip_path}: {e}")
                    self.gpio_line = None
            
            if not self.gpio_line:
                print("Button functionality will be disabled - no compatible GPIO chip found")
        else:
            print("gpiod library not available - button functionality disabled")
        
        # Load fonts
        try:
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font_small = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_large = ImageFont.load_default()
        
        # Store fonts as instance variables for confirmation methods
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        
        fonts = {
            'small': font_small,
            'medium': font_medium,
            'large': font_large
        }
        
        # Load logo image
        from PIL import Image
        logo_image = None
        logo_paths = [
            '/data/logo.png',
            '/data/logo.jpg',
            '/data/logo.bmp',
            '/config/argon_logo.png',
            '/config/argon_logo.jpg',
            '/logo.png',  # Default logo bundled with addon
        ]
        
        for logo_path in logo_paths:
            try:
                if os.path.exists(logo_path):
                    img = Image.open(logo_path)
                    # Convert to monochrome
                    img = img.convert('1')
                    # Resize to fit screen (max 128x64)
                    img.thumbnail((SCREEN_WIDTH, SCREEN_HEIGHT), Image.Resampling.LANCZOS)
                    logo_image = img
                    self.debug_log(f"Loaded logo image from: {logo_path}")
                    break
            except Exception as e:
                self.debug_log(f"Could not load logo from {logo_path}: {e}")
        
        if not logo_image:
            self.debug_log("No logo image could be loaded")
            self.debug_log("Tip: Place logo.png in /data/ or /config/ directory")
        
        # Initialize screen renderer
        self.renderer = ScreenRenderer(
            device=self.device,
            fonts=fonts,
            temp_unit=temp_unit,
            logo_image=logo_image
        )
    
    def debug_log(self, message):
        """Print debug message if debug logging is enabled"""
        if self.debug_logging:
            print(message)
            sys.stdout.flush()
    
    def _draw_confirmation_countdown(self, action_name):
        """Draw and handle confirmation countdown for power actions
        Returns: True if cancelled, False if confirmed
        """
        cancelled = False
        button_was_released = False
        
        self.debug_log(f"Starting {action_name} confirmation countdown...")
        
        for countdown in range(5, 0, -1):
            # Draw countdown with progress bar
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                draw.text((10 if action_name == "SHUTDOWN" else 15, 10), f"{action_name}?", fill="white", font=self.font_large)
                draw.text((5, 35), f"Confirm in {countdown}s", fill="white", font=self.font_small)
                draw.text((5, 48), "Press to cancel", fill="white", font=self.font_small)
                
                # Progress bar
                bar_width = int((countdown / 5.0) * 118)
                draw.rectangle((5, 57, 122, 62), outline=255)
                draw.rectangle((5, 57, 5 + bar_width, 62), fill=255)
            
            # Check for button press to cancel
            for i in range(10):  # Check 10 times per second
                try:
                    if self.gpio_line:
                        button_state = self.gpio_line.get_value(PIN_BUTTON)
                        
                        # Debug first few iterations
                        if countdown == 5 and i < 3:
                            self.debug_log(f"Button state: {button_state}, released: {button_was_released}")
                        
                        # Track when button is released (Value.ACTIVE = released)
                        if button_state == Value.ACTIVE:
                            if not button_was_released:
                                self.debug_log("Button released, ready to detect cancel press")
                            button_was_released = True
                        # Detect new press after release (Value.INACTIVE = pressed)
                        elif button_state == Value.INACTIVE and button_was_released:
                            self.debug_log(f"{action_name} cancelled by button press")
                            cancelled = True
                            self.button_in_power_hold = False  # Resume screen rotation
                            with canvas(self.device) as draw:
                                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                draw.text((20, 20), "CANCELLED", fill="white", font=self.font_large)
                            time.sleep(2)
                            break
                except Exception as e:
                    self.debug_log(f"Button check error: {e}")
                time.sleep(0.1)
            
            if cancelled:
                break
        
        return cancelled
    
    def _execute_power_command(self, command, display_name):
        """Execute a power command (reboot or shutdown) via Supervisor API"""
        self.debug_log(f"{display_name.upper()}: Executing {command} command")
        
        # Display executing message
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="white", fill="black")
            draw.text((10 if command == "shutdown" else 15, 20), display_name, fill="white", font=self.font_large)
            draw.text((20, 45), "Please wait...", fill="white", font=self.font_small)
        time.sleep(1)
        
        # Use Supervisor API
        response = self.supervisor_api.request(f'host/{command}', method='POST', timeout=10)
        
        if response:
            self.debug_log(f"{display_name} response status: {response.status_code}")
            self.debug_log(f"{display_name} response body: {response.text}")
            
            if response.status_code not in [200, 202]:
                self.debug_log(f"WARNING: Unexpected status code: {response.status_code}")
        
        # Clear screen immediately after command
        self.device.clear()
        time.sleep(2)
        sys.exit(0)
    
    def check_power_permissions(self):
        """Check if we have permissions to reboot/shutdown the host"""
        if not SUPERVISOR_TOKEN:
            print("WARNING: No supervisor token available - power management disabled")
            self.power_management_enabled = False
            return
        
        # Try to get supervisor info to check our permissions
        response = self.supervisor_api.request('supervisor/info')
        
        if response and response.status_code == 200:
            # We have at least some API access
            # Now test if we can access host endpoints (requires manager role)
            test_response = self.supervisor_api.request('host/info')
            
            if test_response and test_response.status_code == 200:
                print("✓ Power management enabled - addon has host control permissions")
                self.power_management_enabled = True
            elif test_response and test_response.status_code == 403:
                print("⚠ Power management disabled - addon lacks 'manager' role permissions")
                print("  To enable reboot/shutdown via button, set 'hassio_role: manager' in config.yaml")
                self.power_management_enabled = False
            else:
                print(f"⚠ Power management disabled - unexpected response")
                self.power_management_enabled = False
        else:
            print(f"⚠ Power management disabled - cannot access supervisor API")
            self.power_management_enabled = False
    
    def display_screen(self, screen_name):
        """Display a specific screen"""
        # Delegate to renderer with system_info and supervisor_api
        if screen_name == "clock":
            self.renderer.draw_clock()
        elif screen_name == "cpu":
            self.renderer.draw_cpu(self.system_info)
        elif screen_name == "ram":
            self.renderer.draw_ram(self.system_info)
        elif screen_name == "storage":
            self.renderer.draw_storage(self.system_info)
        elif screen_name == "temp":
            self.renderer.draw_temp(self.system_info)
        elif screen_name == "ip":
            self.renderer.draw_ip(self.supervisor_api)
        elif screen_name == "qr":
            self.renderer.draw_qr(self.supervisor_api)
        elif screen_name == "hastatus" or screen_name == "status":
            self.renderer.draw_ha_status(self.supervisor_api)
        elif screen_name == "logo" or screen_name == "logo1v5":
            self.renderer.draw_logo()
        else:
            # Handle unknown screen locally
            img = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT))
            draw = ImageDraw.Draw(img)
            draw.text((5, 25), f"Unknown: {screen_name}", font=self.font_small, fill=255)
            self.device.display(img)
    
    def button_monitor(self):
        """Monitor button presses in separate thread"""
        if not self.gpio_line:
            return
        
        self.debug_log("Button monitor thread started")
        last_press_time = 0
        press_count = 0
        
        try:
            while True:
                # Poll for button state changes
                try:
                    # Read the current value
                    current_val = self.gpio_line.get_value(PIN_BUTTON)
                    
                    # Detect press (Value.ACTIVE = 1, Value.INACTIVE = 0 with pull-up, so pressed = 0)
                    if current_val == Value.INACTIVE:  # Button pressed (active low)
                        press_start = time.time()
                        reboot_displayed = False
                        shutdown_displayed = False
                        
                        # Wait for release and display messages for long holds
                        while True:
                            if self.gpio_line.get_value(PIN_BUTTON) == Value.ACTIVE:  # Released
                                break
                            
                            # Check how long button has been held
                            hold_time = time.time() - press_start
                            
                            # Display shutdown message if held for 15+ seconds
                            if hold_time >= 15.0 and not shutdown_displayed:
                                self.debug_log("Button: 15 seconds - will shutdown on release")
                                with canvas(self.device) as draw:
                                    draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                    draw.text((10, 15), "SHUTDOWN", fill="white", font=self.font_large)
                                    draw.text((5, 40), "Release to confirm", fill="white", font=self.font_small)
                                shutdown_displayed = True
                            
                            # Display reboot message if held for 10+ seconds (but less than 15)
                            elif hold_time >= 10.0 and not reboot_displayed and not shutdown_displayed:
                                self.debug_log("Button: 10 seconds - will reboot on release")
                                self.button_in_power_hold = True
                                with canvas(self.device) as draw:
                                    draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                    draw.text((15, 15), "REBOOTING", fill="white", font=self.font_large)
                                    draw.text((5, 40), "Release to confirm", fill="white", font=self.font_small)
                                reboot_displayed = True
                            
                            time.sleep(0.1)
                        
                        press_end = time.time()
                        total_hold = press_end - press_start
                        pulsetime = int(total_hold * 10)
                        
                        # Keep power hold flag set during confirmation to prevent screen rotation
                        # It will be cleared after cancel or execution
                        
                        # Execute action based on total hold time (only if power management is enabled)
                        if total_hold >= 15.0 and self.power_management_enabled:
                            self.debug_log("Button released after 15+ seconds - shutdown selected")
                            cancelled = self._draw_confirmation_countdown("SHUTDOWN")
                            if not cancelled:
                                self._execute_power_command("shutdown", "SHUTDOWN")
                        
                        elif total_hold >= 15.0 and not self.power_management_enabled:
                            # User tried to shutdown but we don't have permissions
                            self.debug_log("Button held for shutdown but power management is disabled")
                            with canvas(self.device) as draw:
                                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                draw.text((15, 15), "NO PERMISSION", fill="white", font=self.font_medium)
                                draw.text((5, 35), "Need manager role", fill="white", font=self.font_small)
                            time.sleep(3)
                        
                        elif total_hold >= 10.0 and self.power_management_enabled:
                            self.debug_log("Button released after 10+ seconds - reboot selected")
                            cancelled = self._draw_confirmation_countdown("REBOOT")
                            if not cancelled:
                                self._execute_power_command("reboot", "REBOOTING")
                        
                        elif total_hold >= 10.0 and not self.power_management_enabled:
                            # User tried to reboot but we don't have permissions
                            self.debug_log("Button held for reboot but power management is disabled")
                            with canvas(self.device) as draw:
                                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                draw.text((15, 15), "NO PERMISSION", fill="white", font=self.font_medium)
                                draw.text((5, 35), "Need manager role", fill="white", font=self.font_small)
                            time.sleep(3)
                    else:
                        time.sleep(0.1)
                        continue
                    
                except Exception as read_error:
                    self.debug_log(f"Error reading GPIO: {read_error}")
                    time.sleep(1)
                    continue
                
                # Check if this is part of a double press (within 0.5 seconds)
                if press_end - last_press_time < 0.5:
                    press_count += 1
                else:
                    press_count = 1
                
                last_press_time = press_end
                
                # Wait a bit to see if another press comes
                time.sleep(0.3)
                
                # Determine action based on pulse time and press count
                if press_count >= 2:
                    # Double press - go back
                    self.debug_log("Button: Double press detected - previous screen")
                    self.button_action = "prev"
                    press_count = 0
                elif pulsetime >= 6:
                    # Long press - go to first screen
                    self.debug_log("Button: Long press detected - first screen")
                    self.button_action = "first"
                    press_count = 0
                elif press_count == 1:
                    # Single press - next screen
                    self.debug_log("Button: Single press detected - next screen")
                    self.button_action = "next"
                    press_count = 0
                
        except Exception as e:
            self.debug_log(f"Button monitor error: {e}")
    
    def cleanup(self):
        """Clean up and clear display"""
        try:
            self.device.clear()
            self.device.cleanup()
        except:
            pass
    
    def run(self):
        """Main loop"""
        self.debug_log(f"Starting Argon OLED Display")
        self.debug_log(f"Screen rotation: {' -> '.join(self.screen_list)}")
        self.debug_log(f"Switch duration: {self.switch_duration}s")
        self.debug_log(f"Temperature unit: {self.temp_unit}")
        
        # Show credits splash screen if enabled
        if self.show_credits and not self.credits_shown:
            self.debug_log("Displaying credits splash screen")
            self.renderer.draw_credits(version=self.version)
            self.credits_shown = True
            time.sleep(5)  # Show for 5 seconds
        
        # Start button monitoring thread if GPIO is available
        if GPIO_AVAILABLE:
            button_thread = threading.Thread(target=self.button_monitor, daemon=True)
            button_thread.start()
            self.debug_log("Button monitoring thread started")
        
        loop_count = 0
        try:
            while True:
                # Log heartbeat for first 10 loops
                if loop_count < 10:
                    self.debug_log(f"[MAIN LOOP] Iteration {loop_count}")
                
                loop_count += 1
                current_time = time.time()
                
                # Check for button actions
                if self.button_action:
                    if self.button_action == "next":
                        self.current_screen = (self.current_screen + 1) % len(self.screen_list)
                    elif self.button_action == "prev":
                        self.current_screen = (self.current_screen - 1) % len(self.screen_list)
                    elif self.button_action == "first":
                        self.current_screen = 0
                    self.button_action = None
                    self.last_switch = current_time
                
                # Switch screen if needed (auto-rotation) - but not during power hold
                elif current_time - self.last_switch >= self.switch_duration and not self.button_in_power_hold:
                    self.current_screen = (self.current_screen + 1) % len(self.screen_list)
                    self.last_switch = current_time
                
                # Display current screen - but not during power hold
                if not self.button_in_power_hold:
                    screen_name = self.screen_list[self.current_screen]
                    self.display_screen(screen_name)
                
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            self.cleanup()


def main():
    """Main entry point"""
    # Get configuration from environment variables
    screen_list_str = os.environ.get('SCREEN_LIST', 'logo clock cpu storage ram temp ip')
    screen_list = screen_list_str.split()
    
    switch_duration = int(os.environ.get('SWITCH_DURATION', '30'))
    temp_unit = os.environ.get('TEMP_UNIT', 'C')
    debug_logging = os.environ.get('DEBUG_LOGGING', 'false').lower() in ('true', '1', 'yes')
    show_credits = os.environ.get('SHOW_CREDITS', 'true').lower() in ('true', '1', 'yes')
    
    # Get version from environment (set by run.sh from config.yaml)
    version = os.environ.get('ADDON_VERSION', '1.0.0')
    
    # Create and run the OLED display
    oled = ArgonOLED(screen_list, switch_duration, temp_unit, debug_logging, show_credits, version)
    oled.run()


if __name__ == '__main__':
    main()
