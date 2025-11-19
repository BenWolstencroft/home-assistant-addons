#!/usr/bin/env python3
"""
Argon ONE OLED Display Service for Home Assistant
Displays system information on the Argon ONE OLED screen
"""

import time
import os
import sys
import requests
import threading
from datetime import datetime
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False
    print("Warning: smbus2 not available, button support disabled")

# Configuration
I2C_BUS = 1
I2C_ADDRESS = 0x3C
BUTTON_I2C_ADDRESS = 0x01  # Argon ONE I2C address for buttons
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
SWITCH_DURATION = 30  # seconds between screens

# Home Assistant API
SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN', '')
HA_API_URL = 'http://supervisor/core/api'


class ArgonOLED:
    """Argon ONE OLED Display Manager"""
    
    def __init__(self, screen_list, switch_duration=30, temp_unit='C'):
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
        self.current_screen = 0
        self.last_switch = time.time()
        self.button_pressed = False
        
        # Try to load fonts
        try:
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            self.font_small = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
        
        # Initialize buttons
        self.setup_buttons()
    
    def get_cpu_temp(self):
        """Get CPU temperature"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_c = float(f.read()) / 1000.0
                if self.temp_unit == 'F':
                    return (temp_c * 9/5) + 32
                return temp_c
        except:
            return 0
    
    def get_cpu_usage(self):
        """Get CPU usage percentage"""
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                fields = line.split()
                idle = float(fields[4])
                total = sum(float(x) for x in fields[1:])
                
                if not hasattr(self, 'prev_idle'):
                    self.prev_idle = idle
                    self.prev_total = total
                    return 0
                
                diff_idle = idle - self.prev_idle
                diff_total = total - self.prev_total
                self.prev_idle = idle
                self.prev_total = total
                
                if diff_total == 0:
                    return 0
                return 100.0 * (diff_total - diff_idle) / diff_total
        except:
            return 0
    
    def get_memory_usage(self):
        """Get memory usage"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                mem_total = 0
                mem_available = 0
                for line in lines:
                    if 'MemTotal' in line:
                        mem_total = float(line.split()[1])
                    elif 'MemAvailable' in line:
                        mem_available = float(line.split()[1])
                
                if mem_total > 0:
                    used_pct = ((mem_total - mem_available) / mem_total) * 100
                    return used_pct, mem_total / 1024 / 1024  # Convert to GB
        except:
            pass
        return 0, 0
    
    def get_disk_usage(self):
        """Get disk usage"""
        try:
            st = os.statvfs('/')
            total = (st.f_blocks * st.f_frsize) / (1024**3)
            free = (st.f_bavail * st.f_frsize) / (1024**3)
            used = total - free
            used_pct = (used / total) * 100 if total > 0 else 0
            return used_pct, total
        except:
            return 0, 0
    
    def get_ip_address(self):
        """Get IP address"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "No Network"
    
    def draw_clock(self, draw):
        """Draw clock screen"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        draw.text((10, 15), date_str, font=self.font_medium, fill=255)
        draw.text((20, 35), time_str, font=self.font_large, fill=255)
    
    def draw_cpu(self, draw):
        """Draw CPU information"""
        cpu_usage = self.get_cpu_usage()
        cpu_temp = self.get_cpu_temp()
        temp_symbol = '°F' if self.temp_unit == 'F' else '°C'
        
        draw.text((5, 5), "CPU", font=self.font_medium, fill=255)
        draw.text((5, 25), f"Usage: {cpu_usage:.1f}%", font=self.font_small, fill=255)
        draw.text((5, 40), f"Temp: {cpu_temp:.1f}{temp_symbol}", font=self.font_small, fill=255)
        
        # Progress bar
        bar_width = int((cpu_usage / 100) * 100)
        draw.rectangle((10, 55, 110, 60), outline=255, fill=0)
        draw.rectangle((10, 55, 10 + bar_width, 60), outline=255, fill=255)
    
    def draw_ram(self, draw):
        """Draw RAM information"""
        mem_pct, mem_total = self.get_memory_usage()
        
        draw.text((5, 5), "Memory", font=self.font_medium, fill=255)
        draw.text((5, 25), f"Usage: {mem_pct:.1f}%", font=self.font_small, fill=255)
        draw.text((5, 40), f"Total: {mem_total:.2f} GB", font=self.font_small, fill=255)
        
        # Progress bar
        bar_width = int((mem_pct / 100) * 100)
        draw.rectangle((10, 55, 110, 60), outline=255, fill=0)
        draw.rectangle((10, 55, 10 + bar_width, 60), outline=255, fill=255)
    
    def draw_storage(self, draw):
        """Draw storage information"""
        disk_pct, disk_total = self.get_disk_usage()
        
        draw.text((5, 5), "Storage", font=self.font_medium, fill=255)
        draw.text((5, 25), f"Usage: {disk_pct:.1f}%", font=self.font_small, fill=255)
        draw.text((5, 40), f"Total: {disk_total:.2f} GB", font=self.font_small, fill=255)
        
        # Progress bar
        bar_width = int((disk_pct / 100) * 100)
        draw.rectangle((10, 55, 110, 60), outline=255, fill=0)
        draw.rectangle((10, 55, 10 + bar_width, 60), outline=255, fill=255)
    
    def draw_temp(self, draw):
        """Draw temperature information"""
        cpu_temp = self.get_cpu_temp()
        temp_symbol = '°F' if self.temp_unit == 'F' else '°C'
        
        draw.text((5, 5), "Temperature", font=self.font_medium, fill=255)
        draw.text((20, 30), f"{cpu_temp:.1f}{temp_symbol}", font=self.font_large, fill=255)
    
    def draw_ip(self, draw):
        """Draw IP address"""
        ip = self.get_ip_address()
        
        draw.text((5, 5), "IP Address", font=self.font_medium, fill=255)
        draw.text((10, 30), ip, font=self.font_medium, fill=255)
    
    def draw_logo(self, draw):
        """Draw Argon ONE logo"""
        draw.text((20, 20), "ARGON ONE", font=self.font_large, fill=255)
        draw.text((15, 45), "Home Assistant", font=self.font_small, fill=255)
    
    def setup_buttons(self):
        """Setup I2C button polling for Argon ONE case"""
        self.bus = None
        self.last_button_state = 0
        self.button_debug = os.environ.get('BUTTON_DEBUG', 'false').lower() == 'true'
        
        if not SMBUS_AVAILABLE:
            print("SMBus not available, buttons disabled")
            return
        
        try:
            # Initialize I2C bus for button reading
            self.bus = smbus2.SMBus(I2C_BUS)
            print(f"Button support enabled via I2C bus {I2C_BUS}")
            sys.stdout.flush()
            
            # Scan for I2C devices
            print("\n=== I2C Device Scan ===")
            sys.stdout.flush()
            found_devices = []
            for addr in range(0x03, 0x78):
                try:
                    self.bus.read_byte(addr)
                    found_devices.append(addr)
                    print(f"Found I2C device at address: 0x{addr:02X}")
                    sys.stdout.flush()
                except:
                    pass
            
            if not found_devices:
                print("No I2C devices found (besides OLED)")
            else:
                print(f"Total I2C devices found: {len(found_devices)} - {', '.join([f'0x{a:02X}' for a in found_devices])}")
            print("======================\n")
            sys.stdout.flush()
            
            # Store found devices for button polling
            self.found_i2c_devices = found_devices
            
            if self.button_debug:
                print("*** BUTTON DEBUG MODE ENABLED ***")
                print(f"Will monitor I2C address 0x{BUTTON_I2C_ADDRESS:02X} for button presses")
            
            # Start button monitoring thread
            self.button_thread = threading.Thread(target=self.monitor_buttons, daemon=True)
            self.button_thread.start()
            print(f"Button monitoring thread started: {self.button_thread.is_alive()}")
            print(f"Thread name: {self.button_thread.name}")
            sys.stdout.flush()
            
        except Exception as e:
            print(f"Warning: Could not setup buttons: {e}")
            import traceback
            traceback.print_exc()
            self.bus = None
    
    def monitor_buttons(self):
        """Monitor button presses via I2C in background thread"""
        print("[BUTTON THREAD] Starting button monitoring thread...")
        print(f"[BUTTON THREAD] Debug mode: {self.button_debug}")
        print(f"[BUTTON THREAD] I2C Bus: {I2C_BUS}")
        sys.stdout.flush()
        
        # Use discovered I2C devices, excluding OLED (0x3C)
        addresses_to_monitor = [addr for addr in getattr(self, 'found_i2c_devices', []) if addr != I2C_ADDRESS]
        if not addresses_to_monitor:
            # Fallback to common addresses if scan failed
            addresses_to_monitor = [0x1A, 0x20, 0x21, 0x30, 0x40]
        
        print(f"[BUTTON THREAD] Will monitor addresses: {', '.join([f'0x{a:02X}' for a in addresses_to_monitor])}")
        sys.stdout.flush()
        
        poll_count = 0
        last_error = None
        working_address = None
        
        while True:
            try:
                if self.bus:
                    # Try addresses
                    addresses_to_try = [working_address] if working_address else addresses_to_monitor
                    
                    for addr in addresses_to_try:
                        try:
                            button_state = self.bus.read_byte(addr)
                            
                            # Remember this address works
                            if not working_address:
                                working_address = addr
                                print(f"[BUTTON THREAD] Found working I2C address: 0x{addr:02X}")
                                sys.stdout.flush()
                            
                            # Debug output every 50 polls (5 seconds)
                            # Force output for first 10 polls to verify thread is working
                            if (poll_count < 10) or (self.button_debug and poll_count % 50 == 0):
                                print(f"[DEBUG Poll {poll_count}] I2C 0x{addr:02X}: state=0x{button_state:02X} (binary={bin(button_state)}), last=0x{self.last_button_state:02X}")
                                sys.stdout.flush()
                            
                            # Detect new button press (state changed from 0)
                            if button_state != 0 and button_state != self.last_button_state:
                                print(f"[BUTTON] Raw state detected: 0x{button_state:02X} at address 0x{addr:02X}")
                                sys.stdout.flush()
                                self.handle_button_press(button_state)
                                self.last_button_state = button_state
                            elif button_state == 0:
                                self.last_button_state = 0
                            
                            break  # Successfully read, no need to try other addresses
                            
                        except OSError as e:
                            # I2C read failed for this address
                            if poll_count < 3 and str(e) != last_error:
                                print(f"[DEBUG] Cannot read I2C address 0x{addr:02X}: {e}")
                                sys.stdout.flush()
                                last_error = str(e)
                            continue
                    
                    poll_count += 1
                    
                time.sleep(0.1)  # Poll every 100ms
            except Exception as e:
                print(f"Button monitoring error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)
    
    def handle_button_press(self, button_state):
        """Handle button press event"""
        print(f"\n[BUTTON EVENT] Handling button state: 0x{button_state:02X} (binary: {bin(button_state)})")
        sys.stdout.flush()
        
        # Try different bit patterns
        # Common patterns: bit 0=0x01, bit 1=0x02, bit 2=0x04, bit 3=0x08
        if button_state & 0x01:  # Bit 0
            print(f"[BUTTON] Bit 0 pressed (0x01)")
        if button_state & 0x02:  # Bit 1 - Try as Next
            print(f"[BUTTON] Bit 1 pressed (0x02) - Next screen")
            self.current_screen = (self.current_screen + 1) % len(self.screen_list)
            self.last_switch = time.time()
            print(f"Button: Next screen -> {self.screen_list[self.current_screen]}")
        if button_state & 0x04:  # Bit 2 - Try as Previous
            print(f"[BUTTON] Bit 2 pressed (0x04) - Previous screen")
            self.current_screen = (self.current_screen - 1) % len(self.screen_list)
            self.last_switch = time.time()
            print(f"Button: Previous screen -> {self.screen_list[self.current_screen]}")
        if button_state & 0x08:  # Bit 3
            print(f"[BUTTON] Bit 3 pressed (0x08)")
        
        # Also try treating the whole value as a button ID
        if button_state not in [0x01, 0x02, 0x04, 0x08]:
            print(f"[BUTTON] Unknown button pattern, treating as button ID: {button_state}")
            if button_state == 0x10:  # Try 0x10 as next
                self.current_screen = (self.current_screen + 1) % len(self.screen_list)
                self.last_switch = time.time()
                print(f"Button ID 0x10: Next screen -> {self.screen_list[self.current_screen]}")
            elif button_state == 0x20:  # Try 0x20 as previous  
                self.current_screen = (self.current_screen - 1) % len(self.screen_list)
                self.last_switch = time.time()
                print(f"Button ID 0x20: Previous screen -> {self.screen_list[self.current_screen]}")
    
    def display_screen(self, screen_name):
        """Display a specific screen"""
        img = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = ImageDraw.Draw(img)
        
        if screen_name == "clock":
            self.draw_clock(draw)
        elif screen_name == "cpu":
            self.draw_cpu(draw)
        elif screen_name == "ram":
            self.draw_ram(draw)
        elif screen_name == "storage":
            self.draw_storage(draw)
        elif screen_name == "temp":
            self.draw_temp(draw)
        elif screen_name == "ip":
            self.draw_ip(draw)
        elif screen_name == "logo" or screen_name == "logo1v5":
            self.draw_logo(draw)
        else:
            draw.text((5, 25), f"Unknown: {screen_name}", font=self.font_small, fill=255)
        
        self.device.display(img)
    
    def run(self):
        """Main loop"""
        print(f"Starting Argon OLED Display")
        print(f"Screen rotation: {' -> '.join(self.screen_list)}")
        print(f"Switch duration: {self.switch_duration}s")
        print(f"Temperature unit: {self.temp_unit}")
        sys.stdout.flush()
        
        loop_count = 0
        try:
            while True:
                # Log heartbeat for first 10 loops
                if loop_count < 10:
                    print(f"[MAIN LOOP] Iteration {loop_count}")
                    sys.stdout.flush()
                
                loop_count += 1
                current_time = time.time()
                
                # Switch screen if needed (auto-rotation)
                if current_time - self.last_switch >= self.switch_duration:
                    self.current_screen = (self.current_screen + 1) % len(self.screen_list)
                    self.last_switch = current_time
                
                # Display current screen
                screen_name = self.screen_list[self.current_screen]
                self.display_screen(screen_name)
                
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            # Cleanup I2C bus
            if self.bus:
                try:
                    self.bus.close()
                except:
                    pass
            self.device.clear()
            self.device.cleanup()


def main():
    """Main entry point"""
    # Get configuration from environment variables
    screen_list_str = os.environ.get('SCREEN_LIST', 'logo clock cpu storage ram temp ip')
    screen_list = screen_list_str.split()
    
    switch_duration = int(os.environ.get('SWITCH_DURATION', '30'))
    temp_unit = os.environ.get('TEMP_UNIT', 'C')
    
    # Create and run the OLED display
    oled = ArgonOLED(screen_list, switch_duration, temp_unit)
    oled.run()


if __name__ == '__main__':
    main()
