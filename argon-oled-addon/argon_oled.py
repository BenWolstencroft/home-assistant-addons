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

# Configuration
I2C_BUS = 1
I2C_ADDRESS = 0x3C
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
        
        # Try to load fonts
        try:
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            self.font_small = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
        
        # Try to load logo image
        self.logo_image = None
        logo_paths = [
            '/data/logo.png',
            '/data/logo.jpg',
            '/data/logo.bmp',
            '/config/argon_logo.png',
            '/config/argon_logo.jpg',
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
                    print(f"Loaded logo image from: {logo_path}")
                    break
            except Exception as e:
                print(f"Could not load logo from {logo_path}: {e}")
        
        if not self.logo_image:
            print("No logo image found, using text-based logo")
            print("Tip: Place logo.png in /data/ or /config/ directory")
    
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
    
    def get_ha_url(self):
        """Get Home Assistant URL"""
        try:
            # Try to get the URL from the supervisor API
            headers = {'Authorization': f'Bearer {SUPERVISOR_TOKEN}'}
            response = requests.get('http://supervisor/core/api/config', headers=headers, timeout=5)
            if response.status_code == 200:
                config = response.json()
                external_url = config.get('external_url')
                internal_url = config.get('internal_url')
                # Prefer external URL if available
                return external_url or internal_url
        except Exception as e:
            print(f"Could not get HA URL from API: {e}")
        
        # Fallback to IP-based URL
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
            self.draw_header(draw, "QR Code")
            draw.text((10, 25), "No URL", font=self.font_small, fill=255)
            draw.text((10, 38), "Available", font=self.font_small, fill=255)
            return
        
        try:
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,  # Smallest version
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            qr.add_data(ha_url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="white", back_color="black")
            
            # Convert to 1-bit and resize to fit screen (leaving space for header)
            qr_img = qr_img.convert('1')
            
            # Calculate size to fit (max 50x50 to leave room for header and text)
            max_qr_size = 50
            qr_img.thumbnail((max_qr_size, max_qr_size), Image.Resampling.NEAREST)
            
            # Header
            self.draw_header(draw, "Home Assistant")
            
            # Center the QR code
            qr_width, qr_height = qr_img.size
            x = (SCREEN_WIDTH - qr_width) // 2
            y = 16 + ((SCREEN_HEIGHT - 16 - qr_height) // 2) - 2  # Center in remaining space
            
            # Paste QR code
            if hasattr(draw, '_image'):
                draw._image.paste(qr_img, (x, y))
            
            # Add small text below QR code (if there's space)
            # Truncate URL if too long
            url_display = ha_url
            if len(url_display) > 20:
                url_display = url_display[:20] + "..."
            
        except Exception as e:
            print(f"Error generating QR code: {e}")
            self.draw_header(draw, "QR Code")
            draw.text((10, 25), "QR Error", font=self.font_small, fill=255)
            draw.text((10, 38), str(e)[:15], font=self.font_small, fill=255)
    
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
