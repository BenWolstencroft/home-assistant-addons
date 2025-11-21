"""
Screen rendering module
Contains all draw methods for different display screens
"""

from datetime import datetime
from luma.core.render import canvas
from PIL import Image
import qrcode


class ScreenRenderer:
    """Handles rendering of different screens to the OLED display"""
    
    def __init__(self, device, fonts, temp_unit='C', logo_image=None):
        self.device = device
        self.font_small = fonts['small']
        self.font_medium = fonts['medium']
        self.font_large = fonts['large']
        self.temp_unit = temp_unit
        self.logo_image = logo_image
    
    def draw_header(self, draw, text, icon=""):
        """Draw inverted header with optional icon"""
        draw.rectangle((0, 0, 127, 14), fill=255)
        full_text = f"{icon} {text}" if icon else text
        draw.text((5, 2), full_text, font=self.font_medium, fill=0)
    
    def draw_progress_bar(self, draw, x, y, width, height, percentage, font=None, unit="%", style="solid"):
        """Draw styled progress bar with value text to the right"""
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
        
        # Draw value text to the right of the bar
        if font:
            text_x = x + width + 8
            draw.text((text_x, y), f"{percentage:.0f}{unit}", font=font, fill=255)
    
    def _draw_segment_digit(self, draw, x, y, digit, scale=1.0):
        """Draw a 7-segment style digit"""
        # Base segment size
        seg_w = int(8 * scale)  # Width of horizontal segment
        seg_h = int(2 * scale)  # Thickness of segments
        seg_v = int(10 * scale)  # Height of vertical segment
        
        # Segment positions relative to x, y
        # Segments: a=top, b=top-right, c=bottom-right, d=bottom, e=bottom-left, f=top-left, g=middle
        segments = {
            0: [1, 1, 1, 1, 1, 1, 0],
            1: [0, 1, 1, 0, 0, 0, 0],
            2: [1, 1, 0, 1, 1, 0, 1],
            3: [1, 1, 1, 1, 0, 0, 1],
            4: [0, 1, 1, 0, 0, 1, 1],
            5: [1, 0, 1, 1, 0, 1, 1],
            6: [1, 0, 1, 1, 1, 1, 1],
            7: [1, 1, 1, 0, 0, 0, 0],
            8: [1, 1, 1, 1, 1, 1, 1],
            9: [1, 1, 1, 1, 0, 1, 1],
        }
        
        if digit not in segments:
            return
        
        segs = segments[digit]
        
        # Draw each segment if active
        # a - top
        if segs[0]:
            draw.rectangle((x + seg_h, y, x + seg_h + seg_w, y + seg_h), fill=255)
        
        # b - top right
        if segs[1]:
            draw.rectangle((x + seg_h + seg_w, y + seg_h, x + seg_h + seg_w + seg_h, y + seg_h + seg_v), fill=255)
        
        # c - bottom right
        if segs[2]:
            draw.rectangle((x + seg_h + seg_w, y + seg_h + seg_v + seg_h, x + seg_h + seg_w + seg_h, y + seg_h + seg_v + seg_h + seg_v), fill=255)
        
        # d - bottom
        if segs[3]:
            draw.rectangle((x + seg_h, y + seg_h + seg_v + seg_h + seg_v, x + seg_h + seg_w, y + seg_h + seg_v + seg_h + seg_v + seg_h), fill=255)
        
        # e - bottom left
        if segs[4]:
            draw.rectangle((x, y + seg_h + seg_v + seg_h, x + seg_h, y + seg_h + seg_v + seg_h + seg_v), fill=255)
        
        # f - top left
        if segs[5]:
            draw.rectangle((x, y + seg_h, x + seg_h, y + seg_h + seg_v), fill=255)
        
        # g - middle
        if segs[6]:
            draw.rectangle((x + seg_h, y + seg_h + seg_v, x + seg_h + seg_w, y + seg_h + seg_v + seg_h), fill=255)
    
    def draw_clock(self):
        """Draw clock screen with digital segmented display"""
        with canvas(self.device) as draw:
            now = datetime.now()
            date_str = now.strftime("%b %d, %Y")
            
            # Draw header with date
            self.draw_header(draw, date_str, "🕐")
            
            # Get time components
            hour = now.strftime("%H")
            minute = now.strftime("%M")
            second = now.strftime("%S")
            
            # Draw HH:MM:SS in segmented style with slightly smaller digits to fit all 6
            x_offset = 2
            scale = 1.5
            # Calculate actual digit width: seg_h + seg_w + seg_h = thickness + width + thickness
            digit_width = int(2 * scale) + int(8 * scale) + int(2 * scale)  # 18 pixels
            digit_spacing = 2  # Gap between digits
            colon_spacing = 5  # Space for colon dots
            
            # Draw HH
            self._draw_segment_digit(draw, x_offset, 22, int(hour[0]), scale)
            x_offset += digit_width + digit_spacing
            self._draw_segment_digit(draw, x_offset, 22, int(hour[1]), scale)
            x_offset += digit_width + digit_spacing
            
            # Draw first colon (two dots)
            draw.rectangle((x_offset + 1, 30, x_offset + 3, 32), fill=255)
            draw.rectangle((x_offset + 1, 40, x_offset + 3, 42), fill=255)
            x_offset += colon_spacing
            
            # Draw MM
            self._draw_segment_digit(draw, x_offset, 22, int(minute[0]), scale)
            x_offset += digit_width + digit_spacing
            self._draw_segment_digit(draw, x_offset, 22, int(minute[1]), scale)
            x_offset += digit_width + digit_spacing
            
            # Draw second colon (two dots)
            draw.rectangle((x_offset + 1, 30, x_offset + 3, 32), fill=255)
            draw.rectangle((x_offset + 1, 40, x_offset + 3, 42), fill=255)
            x_offset += colon_spacing
            
            # Draw SS
            self._draw_segment_digit(draw, x_offset, 22, int(second[0]), scale)
            x_offset += digit_width + digit_spacing
            self._draw_segment_digit(draw, x_offset, 22, int(second[1]), scale)
    
    def draw_cpu(self, system_info):
        """Draw CPU information"""
        with canvas(self.device) as draw:
            cpu_usage = system_info.get_cpu_usage()
            cpu_temp = system_info.get_cpu_temp()
            
            # Header
            self.draw_header(draw, "CPU")
            
            # CPU Usage
            draw.text((5, 20), "Usage:", font=self.font_small, fill=255)
            self.draw_progress_bar(draw, 5, 32, 90, 8, cpu_usage, font=self.font_small)
            
            # CPU Temperature
            temp_unit = "°F" if self.temp_unit == 'F' else "°C"
            draw.text((5, 45), "Temp:", font=self.font_small, fill=255)
            
            # Temperature progress bar (assume 20-80°C range)
            max_temp = 80 if self.temp_unit == 'C' else 176
            min_temp = 20 if self.temp_unit == 'C' else 68
            temp_percent = max(0, min(100, ((cpu_temp - min_temp) / (max_temp - min_temp)) * 100))
            self.draw_progress_bar(draw, 5, 57, 90, 6, cpu_temp, font=self.font_small, unit=temp_unit)
    
    def draw_ram(self, system_info):
        """Draw RAM information"""
        with canvas(self.device) as draw:
            mem_used, mem_total, mem_percent = system_info.get_memory_usage()
            mem_used_mb = mem_used
            mem_total_mb = mem_total
            
            self.draw_header(draw, "Memory")
            
            draw.text((5, 20), f"Used: {mem_used_mb:.0f} MB", font=self.font_small, fill=255)
            draw.text((5, 32), f"Total: {mem_total_mb:.0f} MB", font=self.font_small, fill=255)
            self.draw_progress_bar(draw, 5, 45, 90, 8, mem_percent, font=self.font_small)
    
    def draw_storage(self, system_info):
        """Draw storage information"""
        with canvas(self.device) as draw:
            disk_used, disk_total, disk_percent = system_info.get_disk_usage()
            
            self.draw_header(draw, "Storage")
            
            draw.text((5, 20), f"Used: {disk_used:.1f} GB", font=self.font_small, fill=255)
            draw.text((5, 32), f"Total: {disk_total:.1f} GB", font=self.font_small, fill=255)
            self.draw_progress_bar(draw, 5, 45, 90, 8, disk_percent, font=self.font_small)
    
    def draw_temp(self, system_info):
        """Draw temperature screen with large display"""
        with canvas(self.device) as draw:
            cpu_temp = system_info.get_cpu_temp()
            temp_unit = "°F" if self.temp_unit == 'F' else "°C"
            
            self.draw_header(draw, "Temperature")
            
            # Large temperature display
            temp_str = f"{cpu_temp:.1f}{temp_unit}"
            draw.text((25, 30), temp_str, font=self.font_large, fill=255)
            
            # Temperature classification
            if self.temp_unit == 'C':
                if cpu_temp < 50:
                    status = "NORMAL"
                elif cpu_temp < 70:
                    status = "WARM"
                else:
                    status = "HOT"
            else:
                if cpu_temp < 122:
                    status = "NORMAL"
                elif cpu_temp < 158:
                    status = "WARM"
                else:
                    status = "HOT"
            
            draw.text((40, 52), status, font=self.font_small, fill=255)
    
    def draw_ip(self, supervisor_api):
        """Draw IP address"""
        with canvas(self.device) as draw:
            ip_address = supervisor_api.get_ip_address()
            
            # Header
            self.draw_header(draw, "Network")
            
            # IP display with border
            draw.rectangle((5, 22, 122, 50), outline=255)
            
            # Center the IP address (approximate centering)
            ip_display = ip_address if len(ip_address) <= 15 else ip_address[:15]
            # Approximate: each char is ~8px wide for medium font
            text_width = len(ip_display) * 8
            x_pos = max(10, (128 - text_width) // 2)
            
            draw.text((x_pos, 30), ip_display, font=self.font_medium, fill=255)
            
            # Connection status indicator
            status_text = "CONNECTED" if ip_address != "No Network" else "DISCONNECTED"
            draw.text((35, 54), status_text, font=self.font_small, fill=255)
    
    def draw_logo(self):
        """Draw Argon ONE logo (image or text)"""
        with canvas(self.device) as draw:
            if self.logo_image:
                # Display custom logo image, centered
                img_width, img_height = self.logo_image.size
                x = (128 - img_width) // 2
                y = (64 - img_height) // 2
                
                # Create a new image and paste the logo
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
    
    def draw_qr(self, supervisor_api):
        """Draw QR code for Home Assistant URL"""
        with canvas(self.device) as draw:
            ha_url = supervisor_api.get_ha_url()
            
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
                
                # Create QR code image
                qr_img = qr.make_image(fill_color="white", back_color="black")
                
                # Resize to fit on screen (leave room for label)
                qr_size = min(55, 55)
                qr_img = qr_img.resize((qr_size, qr_size))
                
                # Position QR code
                x = (128 - qr_size) // 2
                y = 5
                
                # Paste QR code onto display
                if hasattr(draw, '_image'):
                    draw._image.paste(qr_img, (x, y))
                
            except Exception as e:
                draw.text((10, 25), "QR Error", font=self.font_small, fill=255)
    
    def draw_ha_status(self, supervisor_api):
        """Draw Home Assistant system status"""
        with canvas(self.device) as draw:
            status_info = supervisor_api.get_ha_system_status()
            
            # Header
            self.draw_header(draw, "HA Status")
            
            # Updates available
            updates_text = f"Updates: {status_info['updates']}"
            draw.text((5, 20), updates_text, font=self.font_small, fill=255)
            
            # Update indicator
            if status_info['updates'] > 0:
                draw.rectangle((95, 20, 122, 31), outline=255, fill=255)
                draw.text((100, 20), "!", font=self.font_small, fill=0)
            else:
                draw.rectangle((95, 20, 122, 31), outline=255, fill=0)
                draw.text((100, 20), "OK", font=self.font_small, fill=255)
            
            # Last backup
            if status_info['last_backup'] and status_info['last_backup'] != 'Unknown':
                try:
                    # Parse ISO format: 2025-11-19T10:30:00.000000+00:00
                    backup_dt = datetime.fromisoformat(status_info['last_backup'].replace('Z', '+00:00'))
                    backup_str = backup_dt.strftime("%d/%m/%y")
                    draw.text((5, 33), f"Backup: {backup_str}", font=self.font_small, fill=255)
                except Exception:
                    draw.text((5, 33), "Backup: Parse Err", font=self.font_small, fill=255)
            else:
                draw.text((5, 33), f"Backup: {status_info['backup_state']}", font=self.font_small, fill=255)
            
            # Backup indicator
            if status_info['backup_state'] == 'OK':
                draw.rectangle((95, 33, 122, 44), outline=255, fill=0)
                draw.text((100, 33), "OK", font=self.font_small, fill=255)
            else:
                draw.rectangle((95, 33, 122, 44), outline=255, fill=255)
                draw.text((100, 33), "!", font=self.font_small, fill=0)
