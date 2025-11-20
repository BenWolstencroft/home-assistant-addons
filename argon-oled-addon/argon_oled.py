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
import qrcode

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
    
    def __init__(self, screen_list, switch_duration=30, temp_unit='C', debug_logging=False):
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
        self.current_screen = 0
        self.last_switch = time.time()
        self.button_action = None  # For button press communication
        self.power_management_enabled = False  # Will be set after permission check
        self.button_in_power_hold = False  # Track when button is held for reboot/shutdown
        
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
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            self.font_small = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
        
        # Load logo image
        self.logo_image = None
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
                    self.logo_image = img
                    self.debug_log(f"Loaded logo image from: {logo_path}")
                    break
            except Exception as e:
                self.debug_log(f"Could not load logo from {logo_path}: {e}")
        
        if not self.logo_image:
            self.debug_log("No logo image could be loaded")
            self.debug_log("Tip: Place logo.png in /data/ or /config/ directory")
    
    def debug_log(self, message):
        """Print debug message if debug logging is enabled"""
        if self.debug_logging:
            print(message)
            sys.stdout.flush()
    
    def check_power_permissions(self):
        """Check if we have permissions to reboot/shutdown the host"""
        try:
            supervisor_token = os.environ.get('SUPERVISOR_TOKEN', '')
            if not supervisor_token:
                print("WARNING: No supervisor token available - power management disabled")
                self.power_management_enabled = False
                return
            
            # Try to get supervisor info to check our permissions
            headers = {
                'Authorization': f'Bearer {supervisor_token}',
                'Content-Type': 'application/json'
            }
            response = requests.get('http://supervisor/supervisor/info', headers=headers, timeout=5)
            
            if response.status_code == 200:
                # We have at least some API access
                # Now test if we can access host endpoints (requires manager role)
                test_response = requests.get('http://supervisor/host/info', headers=headers, timeout=5)
                
                if test_response.status_code == 200:
                    print("✓ Power management enabled - addon has host control permissions")
                    self.power_management_enabled = True
                elif test_response.status_code == 403:
                    print("⚠ Power management disabled - addon lacks 'manager' role permissions")
                    print("  To enable reboot/shutdown via button, set 'hassio_role: manager' in config.yaml")
                    self.power_management_enabled = False
                else:
                    print(f"⚠ Power management disabled - unexpected response: {test_response.status_code}")
                    self.power_management_enabled = False
            else:
                print(f"⚠ Power management disabled - cannot access supervisor API: {response.status_code}")
                self.power_management_enabled = False
                
        except Exception as e:
            print(f"⚠ Power management disabled - permission check failed: {e}")
            self.power_management_enabled = False
    
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
        """Get host IP address from Supervisor API"""
        try:
            # Get host IP from supervisor API
            headers = {'Authorization': f'Bearer {SUPERVISOR_TOKEN}'}
            response = requests.get('http://supervisor/network/info', headers=headers, timeout=5)
            if response.status_code == 200:
                network_info = response.json()
                data = network_info.get('data', {})
                # Try to get the primary interface IP
                interfaces = data.get('interfaces', [])
                for interface in interfaces:
                    if interface.get('primary', False):
                        ipv4 = interface.get('ipv4', {})
                        addresses = ipv4.get('address', [])
                        if addresses:
                            # Return the first address without CIDR notation
                            ip = addresses[0].split('/')[0]
                            return ip
                
                # Fallback: get any non-docker interface
                for interface in interfaces:
                    if not interface.get('interface', '').startswith('docker'):
                        ipv4 = interface.get('ipv4', {})
                        addresses = ipv4.get('address', [])
                        if addresses:
                            ip = addresses[0].split('/')[0]
                            return ip
        except Exception as e:
            self.debug_log(f"Could not get IP from Supervisor API: {e}")
        
        # Final fallback to socket method (will get container IP)
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "No Network"
    
    def get_ha_url(self):
        """Get Home Assistant URL"""
        try:
            # Try to get the URL from the supervisor API
            headers = {'Authorization': f'Bearer {SUPERVISOR_TOKEN}'}
            response = requests.get('http://supervisor/core/info', headers=headers, timeout=5)
            if response.status_code == 200:
                info = response.json()
                data = info.get('data', {})
                
                # Try to get configured URL from homeassistant
                ha_response = requests.get('http://supervisor/homeassistant/info', headers=headers, timeout=5)
                if ha_response.status_code == 200:
                    ha_info = ha_response.json()
                    ha_data = ha_info.get('data', {})
                    
                    # Check for external/internal URL in the config
                    external_url = ha_data.get('external_url')
                    internal_url = ha_data.get('internal_url')
                    
                    if external_url:
                        return external_url
                    if internal_url:
                        return internal_url
        except Exception as e:
            self.debug_log(f"Could not get HA URL from API: {e}")
        
        # Fallback to IP-based URL using host IP
        ip = self.get_ip_address()
        if ip != "No Network":
            return f"http://{ip}:8123"
        
        return None
    
    def draw_header(self, draw, text, icon=""):
        """Draw inverted header with optional icon"""
        draw.rectangle((0, 0, 127, 14), fill=255)
        full_text = f"{icon} {text}" if icon else text
        draw.text((5, 2), full_text, font=self.font_medium, fill=0)
    
    def draw_progress_bar(self, draw, x, y, width, height, percentage, style="solid"):
        """Draw styled progress bar"""
        # Draw outline
        draw.rectangle((x, y, x + width, y + height), outline=255, fill=0)
        
        # Calculate fill width
        bar_width = int((percentage / 100) * width)
        
        # Draw fill based on style
        if style == "solid":
            draw.rectangle((x, y, x + bar_width, y + height), fill=255)
        elif style == "striped":
            for i in range(x, x + bar_width, 3):
                draw.line((i, y, i, y + height), fill=255)
        elif style == "dotted":
            for i in range(x, x + bar_width, 2):
                for j in range(y, y + height, 2):
                    draw.point((i, j), fill=255)
        
        # Add warning indicator if > 80%
        if percentage > 80:
            draw.rectangle((x + width + 3, y, x + width + 6, y + height), fill=255)
    
    def draw_clock(self, draw):
        """Draw clock screen"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        # Draw decorative border
        draw.rectangle((0, 0, 127, 63), outline=255)
        draw.rectangle((2, 2, 125, 61), outline=255)
        
        draw.text((10, 12), date_str, font=self.font_medium, fill=255)
        draw.text((18, 40), time_str, font=self.font_large, fill=255)
    
    def draw_cpu(self, draw):
        """Draw CPU information"""
        cpu_usage = self.get_cpu_usage()
        cpu_temp = self.get_cpu_temp()
        temp_symbol = '°F' if self.temp_unit == 'F' else '°C'
        
        # Header
        self.draw_header(draw, "CPU")
        
        # Stats
        draw.text((5, 20), f"Usage: {cpu_usage:.1f}%", font=self.font_small, fill=255)
        draw.text((5, 33), f"Temp: {cpu_temp:.1f}{temp_symbol}", font=self.font_small, fill=255)
        
        # Striped progress bar
        self.draw_progress_bar(draw, 10, 48, 108, 8, cpu_usage, "striped")
    
    def draw_ram(self, draw):
        """Draw RAM information"""
        mem_pct, mem_total = self.get_memory_usage()
        
        # Header
        self.draw_header(draw, "Memory")
        
        # Stats
        draw.text((5, 20), f"Usage: {mem_pct:.1f}%", font=self.font_small, fill=255)
        draw.text((5, 33), f"Total: {mem_total:.2f} GB", font=self.font_small, fill=255)
        
        # Solid progress bar
        self.draw_progress_bar(draw, 10, 48, 108, 8, mem_pct, "solid")
    
    def draw_storage(self, draw):
        """Draw storage information"""
        disk_pct, disk_total = self.get_disk_usage()
        
        # Header
        self.draw_header(draw, "Storage")
        
        # Stats
        draw.text((5, 20), f"Usage: {disk_pct:.1f}%", font=self.font_small, fill=255)
        draw.text((5, 33), f"Total: {disk_total:.2f} GB", font=self.font_small, fill=255)
        
        # Dotted progress bar
        self.draw_progress_bar(draw, 10, 48, 108, 8, disk_pct, "dotted")
    
    def draw_temp(self, draw):
        """Draw temperature information"""
        cpu_temp = self.get_cpu_temp()
        temp_symbol = '°F' if self.temp_unit == 'F' else '°C'
        
        # Header
        self.draw_header(draw, "Temperature")
        
        # Large temperature display
        temp_text = f"{cpu_temp:.1f}{temp_symbol}"
        draw.text((25, 28), temp_text, font=self.font_large, fill=255)
        
        # Visual thermometer on right side
        therm_x = 105
        therm_y = 20
        therm_height = 40
        
        # Thermometer outline
        draw.rectangle((therm_x, therm_y, therm_x + 8, therm_y + therm_height), outline=255)
        draw.ellipse((therm_x - 2, therm_y + therm_height - 2, therm_x + 10, therm_y + therm_height + 10), outline=255, fill=0)
        
        # Fill based on temperature (assume 20-80°C range)
        max_temp = 80 if self.temp_unit == 'C' else 176
        min_temp = 20 if self.temp_unit == 'C' else 68
        temp_ratio = max(0, min(1, (cpu_temp - min_temp) / (max_temp - min_temp)))
        fill_height = int(therm_height * temp_ratio)
        
        if fill_height > 0:
            draw.rectangle((therm_x + 1, therm_y + therm_height - fill_height, therm_x + 7, therm_y + therm_height), fill=255)
        draw.ellipse((therm_x, therm_y + therm_height, therm_x + 8, therm_y + therm_height + 8), fill=255)
    
    def draw_ip(self, draw):
        """Draw IP address"""
        ip = self.get_ip_address()
        
        # Header
        self.draw_header(draw, "Network")
        
        # IP display with border
        draw.rectangle((5, 22, 122, 50), outline=255)
        
        # Center the IP address (approximate centering)
        ip_display = ip if len(ip) <= 15 else ip[:15]
        # Approximate: each char is ~8px wide for medium font
        text_width = len(ip_display) * 8
        x_pos = max(10, (128 - text_width) // 2)
        
        draw.text((x_pos, 30), ip_display, font=self.font_medium, fill=255)
        
        # Connection status indicator
        status_text = "CONNECTED" if ip != "No Network" else "DISCONNECTED"
        draw.text((35, 54), status_text, font=self.font_small, fill=255)
    
    def draw_logo(self, draw):
        """Draw Argon ONE logo (image or text)"""
        if self.logo_image:
            # Display custom logo image, centered
            img_width, img_height = self.logo_image.size
            x = (SCREEN_WIDTH - img_width) // 2
            y = (SCREEN_HEIGHT - img_height) // 2
            
            # Create a new image and paste the logo
            # Note: draw._image is the underlying PIL Image
            if hasattr(draw, '_image'):
                draw._image.paste(self.logo_image, (x, y))
        else:
            # Text-based logo with decorative borders
            # Decorative double border
            draw.rectangle((0, 0, 127, 63), outline=255)
            draw.rectangle((3, 3, 124, 60), outline=255)
            
            # Corner decorations
            draw.rectangle((0, 0, 6, 6), fill=255)
            draw.rectangle((121, 0, 127, 6), fill=255)
            draw.rectangle((0, 57, 6, 63), fill=255)
            draw.rectangle((121, 57, 127, 63), fill=255)
            
            # Logo text
            draw.text((18, 18), "ARGON ONE", font=self.font_large, fill=255)
            draw.text((12, 43), "Home Assistant", font=self.font_small, fill=255)
    
    def draw_qr(self, draw):
        """Draw QR code for Home Assistant URL"""
        ha_url = self.get_ha_url()
        
        if not ha_url:
            # If we can't get the URL, display an error message
            draw.text((10, 25), "No URL", font=self.font_small, fill=255)
            draw.text((10, 38), "Available", font=self.font_small, fill=255)
            return
        
        try:
            # Generate QR code using a simpler approach
            qr = qrcode.QRCode(
                version=1,  # Smallest version
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=2,
                border=1,
            )
            qr.add_data(ha_url)
            qr.make(fit=True)
            
            # Get the QR code matrix
            matrix = qr.get_matrix()
            
            # Calculate size and position
            module_count = len(matrix)
            box_size = 2
            qr_size = module_count * box_size
            
            # Center the QR code (use full screen height now)
            x_offset = (SCREEN_WIDTH - qr_size) // 2
            y_offset = (SCREEN_HEIGHT - qr_size) // 2
            
            # Draw QR code manually pixel by pixel
            for row in range(module_count):
                for col in range(module_count):
                    if matrix[row][col]:
                        # Draw a filled box for each black module
                        x1 = x_offset + col * box_size
                        y1 = y_offset + row * box_size
                        x2 = x1 + box_size - 1
                        y2 = y1 + box_size - 1
                        draw.rectangle((x1, y1, x2, y2), fill=255)
            
        except Exception as e:
            self.debug_log(f"Error generating QR code: {e}")
            if self.debug_logging:
                import traceback
                traceback.print_exc()
            self.draw_header(draw, "QR Code")
            draw.text((10, 25), "QR Error", font=self.font_small, fill=255)
            error_msg = str(e)[:15] if len(str(e)) > 0 else "Unknown"
            draw.text((10, 38), error_msg, font=self.font_small, fill=255)
    
    def get_ha_system_status(self):
        """Get Home Assistant system status information"""
        status_info = {
            'updates': 0,
            'repairs': 0,
            'last_backup': None,
            'backup_state': 'Unknown'
        }
        
        try:
            headers = {'Authorization': f'Bearer {SUPERVISOR_TOKEN}'}
            
            # Get supervisor updates
            try:
                response = requests.get('http://supervisor/supervisor/info', headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    if not data.get('update_available', False):
                        status_info['updates'] = 0
                    else:
                        status_info['updates'] = 1
            except Exception as e:
                self.debug_log(f"Could not get supervisor updates: {e}")
            
            # Get core updates
            try:
                response = requests.get('http://supervisor/core/info', headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    if data.get('update_available', False):
                        status_info['updates'] += 1
            except Exception as e:
                self.debug_log(f"Could not get core updates: {e}")
            
            # Get addon updates
            try:
                response = requests.get('http://supervisor/addons', headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    addons = data.get('addons', [])
                    for addon in addons:
                        if addon.get('update_available', False):
                            status_info['updates'] += 1
            except Exception as e:
                self.debug_log(f"Could not get addon updates: {e}")
            
            # Get backup info
            try:
                response = requests.get('http://supervisor/backups', headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    backups = data.get('backups', [])
                    self.debug_log(f"DEBUG: Found {len(backups)} backups")
                    if backups:
                        # Sort by date and get most recent
                        sorted_backups = sorted(backups, key=lambda x: x.get('date', ''), reverse=True)
                        latest = sorted_backups[0]
                        self.debug_log(f"DEBUG: Latest backup data: {latest}")
                        status_info['last_backup'] = latest.get('date', 'Unknown')
                        status_info['backup_state'] = 'OK'
                    else:
                        status_info['backup_state'] = 'None'
            except Exception as e:
                self.debug_log(f"Could not get backup info: {e}")
                if self.debug_logging:
                    import traceback
                    traceback.print_exc()
            
        except Exception as e:
            self.debug_log(f"Error getting HA system status: {e}")
        
        return status_info
    
    def draw_ha_status(self, draw):
        """Draw Home Assistant system status"""
        status = self.get_ha_system_status()
        
        # Header
        self.draw_header(draw, "HA Status")
        
        # Updates available
        updates_text = f"Updates: {status['updates']}"
        draw.text((5, 20), updates_text, font=self.font_small, fill=255)
        
        # Update indicator
        if status['updates'] > 0:
            draw.rectangle((95, 20, 122, 28), outline=255, fill=255)
            draw.text((100, 20), "!", font=self.font_small, fill=0)
        else:
            draw.rectangle((95, 20, 122, 28), outline=255, fill=0)
            draw.text((100, 20), "OK", font=self.font_small, fill=255)
        
        # Repairs (placeholder for now, HA doesn't expose this easily via API)
        # draw.text((5, 33), "Repairs: 0", font=self.font_small, fill=255)
        
        # Last backup
        if status['last_backup'] and status['last_backup'] != 'Unknown':
            try:
                # Parse ISO format: 2025-11-19T10:30:00.000000+00:00
                backup_dt = datetime.fromisoformat(status['last_backup'].replace('Z', '+00:00'))
                backup_str = backup_dt.strftime("%m/%d %H:%M")
                draw.text((5, 33), f"Backup: {backup_str}", font=self.font_small, fill=255)
            except Exception as e:
                self.debug_log(f"Error parsing backup date '{status['last_backup']}': {e}")
                draw.text((5, 33), "Backup: Parse Err", font=self.font_small, fill=255)
        else:
            draw.text((5, 33), f"Backup: {status['backup_state']}", font=self.font_small, fill=255)
        
        # Backup indicator
        if status['backup_state'] == 'OK':
            draw.rectangle((95, 33, 122, 41), outline=255, fill=0)
            draw.text((100, 33), "OK", font=self.font_small, fill=255)
        else:
            draw.rectangle((95, 33, 122, 41), outline=255, fill=255)
            draw.text((100, 33), "!", font=self.font_small, fill=0)
        
        # System status summary at bottom
        if status['updates'] == 0 and status['backup_state'] == 'OK':
            draw.text((25, 50), "System Healthy", font=self.font_small, fill=255)
        else:
            draw.text((20, 50), "Action Needed", font=self.font_small, fill=255)
    
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
        elif screen_name == "qr":
            self.draw_qr(draw)
        elif screen_name == "hastatus" or screen_name == "status":
            self.draw_ha_status(draw)
        elif screen_name == "logo" or screen_name == "logo1v5":
            self.draw_logo(draw)
        else:
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
                            
                            # Wait for button to be released first
                            self.debug_log("Waiting for button release before confirmation...")
                            while True:
                                try:
                                    if self.gpio_line and self.gpio_line.get_value(PIN_BUTTON) == 1:
                                        break
                                except:
                                    pass
                                time.sleep(0.05)
                            
                            time.sleep(0.2)  # Debounce
                            
                            # Confirmation countdown with cancel option
                            cancelled = False
                            for countdown in range(5, 0, -1):
                                # Draw countdown with progress bar
                                with canvas(self.device) as draw:
                                    draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                    draw.text((10, 10), "SHUTDOWN?", fill="white", font=self.font_large)
                                    draw.text((5, 35), f"Confirm in {countdown}s", fill="white", font=self.font_small)
                                    draw.text((5, 48), "Press to cancel", fill="white", font=self.font_small)
                                    
                                    # Progress bar
                                    bar_width = int((countdown / 5.0) * 118)
                                    draw.rectangle((5, 57, 122, 62), outline=255)
                                    draw.rectangle((5, 57, 5 + bar_width, 62), fill=255)
                                
                                # Check for button press to cancel
                                for _ in range(10):  # Check 10 times per second
                                    try:
                                        if self.gpio_line and self.gpio_line.get_value(PIN_BUTTON) == 0:
                                            self.debug_log("Shutdown cancelled by button press")
                                            cancelled = True
                                            self.button_in_power_hold = False  # Resume screen rotation
                                            with canvas(self.device) as draw:
                                                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                                draw.text((20, 20), "CANCELLED", fill="white", font=self.font_large)
                                            time.sleep(2)
                                            break
                                    except:
                                        pass
                                    time.sleep(0.1)
                                
                                if cancelled:
                                    break
                            
                            if not cancelled:
                                self.debug_log("SHUTDOWN: Executing shutdown command")
                                # Display executing message
                                with canvas(self.device) as draw:
                                    draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                    draw.text((10, 20), "SHUTDOWN", fill="white", font=self.font_large)
                                    draw.text((20, 45), "Please wait...", fill="white", font=self.font_small)
                                time.sleep(1)
                                # Use Supervisor API to shutdown
                                try:
                                    supervisor_token = os.environ.get('SUPERVISOR_TOKEN', '')
                                    self.debug_log(f"Supervisor token present: {bool(supervisor_token)}")
                                    self.debug_log("Sending shutdown request to supervisor...")
                                    
                                    response = requests.post(
                                        'http://supervisor/host/shutdown',
                                        headers={
                                            'Authorization': f'Bearer {supervisor_token}',
                                            'Content-Type': 'application/json'
                                        },
                                        timeout=10
                                    )
                                    self.debug_log(f"Shutdown response status: {response.status_code}")
                                    self.debug_log(f"Shutdown response body: {response.text}")
                                    
                                    if response.status_code not in [200, 202]:
                                        self.debug_log(f"WARNING: Unexpected status code: {response.status_code}")
                                        
                                except requests.exceptions.Timeout:
                                    self.debug_log("Shutdown request timed out (may still execute)")
                                except Exception as e:
                                    self.debug_log(f"Shutdown error: {type(e).__name__}: {e}")
                                    if self.debug_logging:
                                        import traceback
                                        traceback.print_exc()
                                
                                # Clear screen immediately after command
                                self.device.clear()
                                time.sleep(2)
                                sys.exit(0)
                        
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
                            
                            # Wait for button to be released first
                            self.debug_log("Waiting for button release before confirmation...")
                            while True:
                                try:
                                    if self.gpio_line and self.gpio_line.get_value(PIN_BUTTON) == 1:
                                        break
                                except:
                                    pass
                                time.sleep(0.05)
                            
                            time.sleep(0.2)  # Debounce
                            
                            # Confirmation countdown with cancel option
                            cancelled = False
                            for countdown in range(5, 0, -1):
                                # Draw countdown with progress bar
                                with canvas(self.device) as draw:
                                    draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                    draw.text((15, 10), "REBOOT?", fill="white", font=self.font_large)
                                    draw.text((5, 35), f"Confirm in {countdown}s", fill="white", font=self.font_small)
                                    draw.text((5, 48), "Press to cancel", fill="white", font=self.font_small)
                                    
                                    # Progress bar
                                    bar_width = int((countdown / 5.0) * 118)
                                    draw.rectangle((5, 57, 122, 62), outline=255)
                                    draw.rectangle((5, 57, 5 + bar_width, 62), fill=255)
                                
                                # Check for button press to cancel
                                for _ in range(10):  # Check 10 times per second
                                    try:
                                        if self.gpio_line and self.gpio_line.get_value(PIN_BUTTON) == 0:
                                            self.debug_log("Reboot cancelled by button press")
                                            cancelled = True
                                            self.button_in_power_hold = False  # Resume screen rotation
                                            with canvas(self.device) as draw:
                                                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                                draw.text((20, 20), "CANCELLED", fill="white", font=self.font_large)
                                            time.sleep(2)
                                            break
                                    except:
                                        pass
                                    time.sleep(0.1)
                                
                                if cancelled:
                                    break
                            
                            if not cancelled:
                                self.debug_log("REBOOT: Executing reboot command")
                                # Display executing message
                                with canvas(self.device) as draw:
                                    draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                                    draw.text((15, 20), "REBOOTING", fill="white", font=self.font_large)
                                    draw.text((20, 45), "Please wait...", fill="white", font=self.font_small)
                                time.sleep(1)
                                # Use Supervisor API to reboot
                                try:
                                    supervisor_token = os.environ.get('SUPERVISOR_TOKEN', '')
                                    self.debug_log(f"Supervisor token present: {bool(supervisor_token)}")
                                    self.debug_log("Sending reboot request to supervisor...")
                                    
                                    response = requests.post(
                                        'http://supervisor/host/reboot',
                                        headers={
                                            'Authorization': f'Bearer {supervisor_token}',
                                            'Content-Type': 'application/json'
                                        },
                                        timeout=10
                                    )
                                    self.debug_log(f"Reboot response status: {response.status_code}")
                                    self.debug_log(f"Reboot response body: {response.text}")
                                    
                                    if response.status_code not in [200, 202]:
                                        self.debug_log(f"WARNING: Unexpected status code: {response.status_code}")
                                        
                                except requests.exceptions.Timeout:
                                    self.debug_log("Reboot request timed out (may still execute)")
                                except Exception as e:
                                    self.debug_log(f"Reboot error: {type(e).__name__}: {e}")
                                    if self.debug_logging:
                                        import traceback
                                        traceback.print_exc()
                                
                                # Clear screen immediately after command
                                self.device.clear()
                                time.sleep(2)
                                sys.exit(0)
                        
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
    
    # Create and run the OLED display
    oled = ArgonOLED(screen_list, switch_duration, temp_unit, debug_logging)
    oled.run()


if __name__ == '__main__':
    main()
