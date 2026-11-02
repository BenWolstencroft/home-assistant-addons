#!/usr/bin/env python3
"""
Argon ONE OLED Display Service for Home Assistant
Displays system information on the Argon ONE OLED screen
"""

import time
import os
import sys
import struct
import select
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

# Linux input event values. KEY_POWER is what the Argon ONE V5 case button
# emits through the kernel gpio-keys driver (device name "pwr_button").
EV_KEY = 0x01
KEY_POWER = 116
POWER_BUTTON_NAME = "pwr_button"
POWER_BUTTON_BY_PATH = "/dev/input/by-path/platform-pwr_button-event"
INPUT_DEVICES_PROC = "/proc/bus/input/devices"

# Reading the evdev node is not exclusive. EVIOCGRAB is intentionally not used:
# HAOS logind keeps seeing the key. HandlePowerKey=ignore, so a short press
# does not shut the host down. HandlePowerKeyLongPress=poweroff fires at about
# 5 seconds, which is before this add-on's 10s/15s prompts.
POWER_KEY_SOURCE_WARNING = (
    "WARNING: button_source is 'power_key' but the pwr_button input device "
    "could not be opened. The case button will do nothing. Change the add-on "
    "option button_source to 'gpio' if this case exposes the button as GPIO "
    "line 4, and check that the add-on is allowed to read /dev/input."
)
GPIO_SOURCE_WARNING = (
    "WARNING: button_source is 'gpio' but GPIO line 4 is not available. "
    "The case button will do nothing. Change the add-on option button_source "
    "to 'power_key' on an Argon ONE V5 running Home Assistant OS, where the "
    "button is the kernel pwr_button input device."
)
LOGIND_POWER_KEY_NOTE = (
    "NOTE: button_source 'power_key' does not grab the device (no EVIOCGRAB), "
    "so systemd-logind still receives KEY_POWER. On HAOS a short press is "
    "ignored and does not shut down. A hold of about 5 seconds is "
    "HandlePowerKeyLongPress=poweroff and will power off the host before this "
    "add-on's 10s reboot or 15s shutdown prompt. Set "
    "HandlePowerKeyLongPress=ignore on the host to use those hold gestures."
)


def input_event_format():
    """struct input_event layout for this process's word size."""
    if struct.calcsize("l") == 8:
        return "llHHi"
    return "iiHHi"


def unpack_input_events(buffer, fmt=None):
    """Split a byte buffer into (type, code, value) events.

    Returns the events and any incomplete trailing bytes.
    """
    fmt = fmt or input_event_format()
    size = struct.calcsize(fmt)
    events = []
    offset = 0
    while offset + size <= len(buffer):
        _sec, _usec, ev_type, code, value = struct.unpack_from(fmt, buffer, offset)
        events.append((ev_type, code, value))
        offset += size
    return events, buffer[offset:]


def discover_power_button_paths(proc_text, by_path=POWER_BUTTON_BY_PATH):
    """Find /dev/input/eventN for the pwr_button device.

    The event index is not stable, so it is taken from Handlers= rather than
    hardcoded. The by-path symlink is appended as a second candidate; udev
    names it from the platform device, which stays platform-pwr_button-event.
    """
    paths = []
    name = None
    handlers = ""

    def finish():
        nonlocal name, handlers
        if name == POWER_BUTTON_NAME:
            for token in handlers.split():
                if token.startswith("event") and token[5:].isdigit():
                    candidate = f"/dev/input/{token}"
                    if candidate not in paths:
                        paths.append(candidate)
        name = None
        handlers = ""

    for line in proc_text.splitlines():
        if line.strip() == "":
            finish()
            continue
        if line.startswith("N: Name="):
            raw = line.split("=", 1)[1].strip()
            if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
                raw = raw[1:-1]
            name = raw
        elif line.startswith("H: Handlers="):
            handlers = line.split("=", 1)[1].strip()
    finish()
    if by_path and by_path not in paths:
        paths.append(by_path)
    return paths


class PowerKeyDevice:
    """Non-exclusive reader for KEY_POWER press and release events."""

    def __init__(self, fd, fmt=None):
        self.fd = fd
        self.fmt = fmt or input_event_format()
        self._pending = []
        self._buffer = b""
        self.held = False

    def close(self):
        try:
            os.close(self.fd)
        except OSError:
            pass

    def _read_more(self, block):
        if not block:
            readable, _, _ = select.select([self.fd], [], [], 0)
            if not readable:
                return
        try:
            chunk = os.read(self.fd, 1024)
        except BlockingIOError:
            return
        if not chunk:
            raise OSError("power button input device closed")
        self._buffer += chunk
        events, self._buffer = unpack_input_events(self._buffer, self.fmt)
        self._pending.extend(events)

    def _apply(self, event):
        ev_type, code, value = event
        if ev_type != EV_KEY or code != KEY_POWER:
            return
        if value == 1:
            self.held = True
        elif value == 0:
            self.held = False
        # value 2 is autorepeat; the key is still down, so leave held as-is.

    def wait_until_pressed(self):
        """Block until a KEY_POWER press is seen. Do not consume past it."""
        while not self.held:
            if not self._pending:
                self._read_more(block=True)
            if not self._pending:
                continue
            self._apply(self._pending.pop(0))

    def is_down(self):
        """True while the key is held.

        When the key is up, queued events are applied only until the next
        press so a following release stays buffered. When it is already
        down, events are applied until that hold ends.
        """
        self._read_more(block=False)
        if not self.held:
            while self._pending and not self.held:
                self._apply(self._pending.pop(0))
                if self.held:
                    break
            return self.held
        while self._pending and self.held:
            self._apply(self._pending.pop(0))
            if not self.held:
                break
        return self.held


def open_power_button(proc_path=INPUT_DEVICES_PROC):
    """Open the pwr_button evdev node. Returns (path, device) or (None, reason)."""
    try:
        with open(proc_path, "r", encoding="utf-8", errors="replace") as handle:
            proc_text = handle.read()
    except OSError as exc:
        proc_text = ""
        proc_error = str(exc)
    else:
        proc_error = ""
    paths = discover_power_button_paths(proc_text)
    errors = []
    if proc_error:
        errors.append(f"{proc_path}: {proc_error}")
    if not paths:
        errors.append("no pwr_button device listed")
    for path in paths:
        try:
            fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            continue
        return path, PowerKeyDevice(fd), ""
    return None, None, "; ".join(errors)

# Home Assistant API
SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN', '')
HA_API_URL = 'http://supervisor/core/api'


class ArgonOLED:
    """Argon ONE OLED Display Manager"""
    
    def __init__(self, screen_list, switch_duration=30, temp_unit='C', debug_logging=False, show_credits=True, version="1.0.0", screen_off_until_button=False, idle_dim_timeout=60, button_source="power_key"):
        """Initialize the OLED display"""
        self.screen_off_until_button = screen_off_until_button
        self.idle_dim_timeout = idle_dim_timeout
        if button_source not in ("gpio", "power_key"):
            print(f"WARNING: button_source '{button_source}' is not gpio or power_key; using power_key")
            button_source = "power_key"
        self.button_source = button_source
        self._power_key = None
        # True only after a successful SSD1306 display-off (device.hide()).
        self.display_blanked = False
        self.button_held = False  # Physical press in progress; do not blank mid-gesture
        self._panel_lock = threading.Lock()
        self._refresh = threading.Event()
        self.last_activity = time.time()

        try:
            self.serial = i2c(port=I2C_BUS, address=I2C_ADDRESS)
            self.device = ssd1306(self.serial, width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
            self.device.clear()
            # luma's init leaves the panel on (DISPLAYON). hide() sends
            # DISPLAYOFF so a dark boot has no residual OLED glow.
            if self.screen_off_until_button:
                self.device.hide()
                self.display_blanked = True
                print(f"OLED panel off until button press (idle {self.idle_dim_timeout}s)")
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
        
        # Initialize GPIO only when that source is selected. On Argon ONE V5
        # the case button is not this line; requesting it anyway stays high
        # and never reports a press.
        self.gpio_chip = None
        self.gpio_line = None
        if self.button_source == "gpio":
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
                    print(GPIO_SOURCE_WARNING)
            else:
                print("gpiod library not available")
                print(GPIO_SOURCE_WARNING)
        else:
            print("Button source is power_key; GPIO line 4 will not be requested")
        
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

    def _on_button_activity(self, end_hold=False):
        """Reset the idle timer and wake a blanked panel.

        Called on the leading edge of a press and again when it is released.
        This is not a gesture. press_count, pulsetime and last_press_time
        stay entirely inside button_monitor, so the press that lights the
        panel is still classified afterwards as next, previous, first
        screen, or a 10s/15s power hold, including the first click of a
        double press.

        end_hold clears the physical-hold flag in the same critical section
        as the timer update. Otherwise a hold longer than idle_dim_timeout
        could hide() in the gap before the release was recorded.
        """
        if not end_hold and not self.screen_off_until_button:
            return
        with self._panel_lock:
            if end_hold:
                self.button_held = False
            if not self.screen_off_until_button:
                return
            self.last_activity = time.time()
            if not self.display_blanked:
                return
            try:
                self.device.show()
            except Exception as e:
                self.debug_log(f"Error waking display: {e}")
                return
            self.display_blanked = False
            # The panel may have been dark longer than switch_duration.
            # Restart the interval so auto-rotation does not also advance
            # the screen on top of whatever this press classifies as.
            self.last_switch = time.time()
            self.debug_log("Panel woken by button")
            self._refresh.set()

    def _maybe_blank(self):
        """Turn the panel off with display-off after the idle timeout.

        Does nothing when the mode is disabled, the button is held, or a
        power confirmation is on screen. Safe to call from the main loop;
        the button thread is not waited on.
        """
        if not self.screen_off_until_button:
            return False
        with self._panel_lock:
            if self.display_blanked or self.button_held or self.button_in_power_hold:
                return False
            if time.time() - self.last_activity < self.idle_dim_timeout:
                return False
            try:
                self.device.hide()
            except Exception as e:
                self.debug_log(f"Error blanking display: {e}")
                return False
            self.display_blanked = True
            self.debug_log("Panel blanked after idle timeout")
            return True

    def _ensure_panel_on_for_power_ui(self):
        """Wake the panel and pause rotation before reboot/shutdown UI.

        A hold that started while the panel was dark must still draw its
        "release to confirm" message and the 5-second countdown on a panel
        that is actually on. Does not change gesture timing or classification.
        """
        with self._panel_lock:
            self.button_in_power_hold = True
            if not self.screen_off_until_button:
                return
            self.last_activity = time.time()
            if not self.display_blanked:
                return
            try:
                self.device.show()
            except Exception as e:
                self.debug_log(f"Error waking display for power prompt: {e}")
                return
            self.display_blanked = False
            self.last_switch = time.time()
            self.debug_log("Panel woken for power confirmation")
            self._refresh.set()

    def _restore_after_power_ui(self):
        """Leave the panel awake with a fresh idle timer after a power prompt ends."""
        with self._panel_lock:
            if self.screen_off_until_button:
                self.last_activity = time.time()
                if self.display_blanked:
                    try:
                        self.device.show()
                    except Exception as e:
                        self.debug_log(f"Error waking display: {e}")
                    else:
                        self.display_blanked = False
                        self.last_switch = time.time()
                        self._refresh.set()
            # Same point the confirmation path used to clear this flag,
            # so screen rotation resumes when the prompt is finished.
            self.button_in_power_hold = False

    def _button_is_down(self):
        """Whether the selected button source is currently held.

        Returns None when that source is not open. GPIO is active-low.
        """
        if self.button_source == "power_key" and self._power_key is not None:
            return self._power_key.is_down()
        if self.gpio_line and Value is not None:
            return self.gpio_line.get_value(PIN_BUTTON) == Value.INACTIVE
        return None
    
    def _draw_confirmation_countdown(self, action_name):
        """Draw and handle confirmation countdown for power actions
        Returns: True if cancelled, False if confirmed
        """
        cancelled = False
        button_was_released = False
        
        self.debug_log(f"Starting {action_name} confirmation countdown...")
        # Countdown pixels must not be written while the panel is off.
        self._ensure_panel_on_for_power_ui()
        
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
            
            # Check for button press to cancel. Require a release first so the
            # tail of the hold that opened this prompt is not itself a cancel.
            for i in range(10):  # Check 10 times per second
                try:
                    held = self._button_is_down()
                    if held is None:
                        pass
                    else:
                        if countdown == 5 and i < 3:
                            self.debug_log(f"Button held: {held}, released: {button_was_released}")
                        if not held:
                            if not button_was_released:
                                self.debug_log("Button released, ready to detect cancel press")
                            button_was_released = True
                        elif button_was_released:
                            self.debug_log(f"{action_name} cancelled by button press")
                            cancelled = True
                            # Awake, idle timer restarted, then the flag drops
                            # so the main loop may draw again.
                            self._restore_after_power_ui()
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
        self._ensure_panel_on_for_power_ui()
        
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
        # device.display() updates SSD1306 RAM without sending DISPLAYON,
        # but a frame must not be composed while the panel is meant to be off.
        if self.display_blanked:
            return
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
        elif screen_name == "fan":
            self.renderer.draw_fan(self.system_info)
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
    
    def _await_release(self, press_start, is_down):
        """Block until the button is released, drawing power prompts on the way.

        Wake/idle handling runs here and does not touch press_count, pulsetime,
        or last_press_time. is_down() is true while the button is held.
        """
        reboot_displayed = False
        shutdown_displayed = False
        # Wake is a side effect of this press, not a new gesture.
        self.button_held = True
        try:
            self._on_button_activity()
            while is_down():
                hold_time = time.time() - press_start
                
                # Display shutdown message if held for 15+ seconds
                if hold_time >= 15.0 and not shutdown_displayed:
                    self.debug_log("Button: 15 seconds - will shutdown on release")
                    self._ensure_panel_on_for_power_ui()
                    with canvas(self.device) as draw:
                        draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                        draw.text((10, 15), "SHUTDOWN", fill="white", font=self.font_large)
                        draw.text((5, 40), "Release to confirm", fill="white", font=self.font_small)
                    shutdown_displayed = True
                
                # Display reboot message if held for 10+ seconds (but less than 15)
                elif hold_time >= 10.0 and not reboot_displayed and not shutdown_displayed:
                    self.debug_log("Button: 10 seconds - will reboot on release")
                    self._ensure_panel_on_for_power_ui()
                    with canvas(self.device) as draw:
                        draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                        draw.text((15, 15), "REBOOTING", fill="white", font=self.font_large)
                        draw.text((5, 40), "Release to confirm", fill="white", font=self.font_small)
                    reboot_displayed = True
                
                time.sleep(0.1)
        finally:
            # Cover the whole physical hold, then start the idle timeout
            # from the release rather than from the press.
            self._on_button_activity(end_hold=True)

    def _sample_second_click(self, last_press_time, press_count, is_down):
        """Watch until 0.5s after the previous release for a second click.

        The old code slept 0.3s here without reading the button, so a second
        press could not increment press_count. A click that is still held
        when that window closes is left for the next gesture.
        """
        deadline = last_press_time + 0.5
        while time.time() < deadline:
            if is_down():
                while is_down() and time.time() < deadline:
                    time.sleep(0.05)
                if not is_down() and time.time() < deadline:
                    press_count += 1
                break
            time.sleep(0.05)
        return press_count

    def _handle_completed_press(self, press_start, press_end, last_press_time, press_count, is_down):
        """Power prompts and the single/double/long classifier. Same for both sources."""
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
            self._ensure_panel_on_for_power_ui()
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                draw.text((15, 15), "NO PERMISSION", fill="white", font=self.font_medium)
                draw.text((5, 35), "Need manager role", fill="white", font=self.font_small)
            time.sleep(3)
            if self.screen_off_until_button:
                # The power-hold flag would otherwise stay set and
                # the idle blanker would never run again. When the
                # mode is off, leave the flag as the previous code did.
                self._restore_after_power_ui()
        
        elif total_hold >= 10.0 and self.power_management_enabled:
            self.debug_log("Button released after 10+ seconds - reboot selected")
            cancelled = self._draw_confirmation_countdown("REBOOT")
            if not cancelled:
                self._execute_power_command("reboot", "REBOOTING")
        
        elif total_hold >= 10.0 and not self.power_management_enabled:
            # User tried to reboot but we don't have permissions
            self.debug_log("Button held for reboot but power management is disabled")
            self._ensure_panel_on_for_power_ui()
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
                draw.text((15, 15), "NO PERMISSION", fill="white", font=self.font_medium)
                draw.text((5, 35), "Need manager role", fill="white", font=self.font_small)
            time.sleep(3)
            if self.screen_off_until_button:
                self._restore_after_power_ui()
        
        # A press that woke the panel falls through to here. Do not clear
        # press_count before this comparison: that would turn a double press
        # into a single "next".
        if press_end - last_press_time < 0.5:
            press_count += 1
        else:
            press_count = 1
        
        last_press_time = press_end
        press_count = self._sample_second_click(last_press_time, press_count, is_down)
        
        if press_count >= 2:
            # Double press - go back
            self.debug_log("Button: Double press detected - previous screen")
            self.button_action = "prev"
            press_count = 0
        elif pulsetime >= 6:
            # Long press - go to first screen (~0.6s)
            self.debug_log("Button: Long press detected - first screen")
            self.button_action = "first"
            press_count = 0
        elif press_count == 1:
            # Single press - next screen
            self.debug_log("Button: Single press detected - next screen")
            self.button_action = "next"
            press_count = 0
        return last_press_time, press_count

    def _monitor_level(self, is_down, source_name):
        """Shared press loop. is_down() is true while the chosen source is held."""
        self.debug_log(f"Button monitor thread started ({source_name})")
        last_press_time = 0
        press_count = 0
        try:
            while True:
                try:
                    if not is_down():
                        time.sleep(0.1)
                        continue
                    press_start = time.time()
                    self._await_release(press_start, is_down)
                    press_end = time.time()
                except Exception as read_error:
                    self.debug_log(f"Error reading {source_name} button: {read_error}")
                    time.sleep(1)
                    continue
                last_press_time, press_count = self._handle_completed_press(
                    press_start, press_end, last_press_time, press_count, is_down
                )
        except Exception as e:
            self.debug_log(f"Button monitor error: {e}")

    def button_monitor(self):
        """Monitor button presses in separate thread"""
        if self.button_source == "power_key":
            path, device, reason = open_power_button()
            if device is None:
                detail = f" ({reason})" if reason else ""
                print(f"{POWER_KEY_SOURCE_WARNING}{detail}")
                return
            self._power_key = device
            print(f"Button source power_key: reading KEY_POWER from {path}")
            print(LOGIND_POWER_KEY_NOTE)
            self._monitor_power_key(device)
            return
        
        if not self.gpio_line:
            print(GPIO_SOURCE_WARNING)
            return
        # GPIO line is active-low: INACTIVE (0) while held, ACTIVE when released.
        self._monitor_level(
            lambda: self.gpio_line.get_value(PIN_BUTTON) == Value.INACTIVE,
            "gpio",
        )

    def _monitor_power_key(self, device):
        """Block on KEY_POWER edges, then use the same gesture handler as GPIO."""
        self.debug_log("Button monitor thread started (power_key)")
        last_press_time = 0
        press_count = 0
        try:
            while True:
                try:
                    device.wait_until_pressed()
                    press_start = time.time()
                    self._await_release(press_start, device.is_down)
                    press_end = time.time()
                except Exception as read_error:
                    self.debug_log(f"Error reading power_key button: {read_error}")
                    time.sleep(1)
                    continue
                last_press_time, press_count = self._handle_completed_press(
                    press_start, press_end, last_press_time, press_count, device.is_down
                )
        except Exception as e:
            self.debug_log(f"Button monitor error: {e}")
        finally:
            device.close()
            self._power_key = None
    
    def cleanup(self):
        """Clean up and clear display"""
        try:
            if self._power_key:
                self._power_key.close()
                self._power_key = None
        except Exception:
            pass
        try:
            self.device.clear()
            self.device.cleanup()
        except:
            pass
    
    def _service_once(self, current_time):
        """One pass of blanking, button actions, rotation and drawing.

        Auto-rotation and screen draws are skipped while the panel is off
        so a stale switch interval cannot paint a frame after hide().
        """
        if self.screen_off_until_button:
            self._maybe_blank()

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
        # and not while the panel is hardware-off.
        elif current_time - self.last_switch >= self.switch_duration and not self.button_in_power_hold and not self.display_blanked:
            self.current_screen = (self.current_screen + 1) % len(self.screen_list)
            self.last_switch = current_time

        # Display current screen - but not during power hold or while blanked.
        # Blank again immediately before the draw so this pass cannot both
        # turn the panel off and then paint a screen.
        if not self.button_in_power_hold and not self.display_blanked:
            if self.screen_off_until_button:
                self._maybe_blank()
            if not self.button_in_power_hold and not self.display_blanked:
                screen_name = self.screen_list[self.current_screen]
                self.display_screen(screen_name)

    def run(self):
        """Main loop"""
        self.debug_log(f"Starting Argon OLED Display")
        self.debug_log(f"Screen rotation: {' -> '.join(self.screen_list)}")
        self.debug_log(f"Switch duration: {self.switch_duration}s")
        self.debug_log(f"Temperature unit: {self.temp_unit}")
        self.debug_log(f"Screen off until button: {self.screen_off_until_button}")
        if self.screen_off_until_button:
            self.debug_log(f"Idle dim timeout: {self.idle_dim_timeout}s")
        self.debug_log(f"Button source: {self.button_source}")
        
        # Show credits splash screen if enabled. Skip it when the panel
        # is configured to boot dark, otherwise the splash would light it.
        if self.show_credits and not self.credits_shown and not self.display_blanked:
            self.debug_log("Displaying credits splash screen")
            self.renderer.draw_credits(version=self.version)
            self.credits_shown = True
            time.sleep(5)  # Show for 5 seconds
        elif self.show_credits and not self.credits_shown and self.display_blanked:
            self.debug_log("Skipping credits splash so the panel stays off")
            self.credits_shown = True
        
        # Always start the monitor. It warns and returns if the chosen
        # source cannot be opened, instead of quietly doing nothing.
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
                self._service_once(current_time)

                if self.screen_off_until_button and self.display_blanked:
                    # Return as soon as the button thread turns the panel on.
                    self._refresh.wait(timeout=1.0)
                    self._refresh.clear()
                else:
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
    screen_list_str = os.environ.get('SCREEN_LIST', 'logo clock cpu storage ram temp fan ip')
    screen_list = screen_list_str.split()
    
    switch_duration = int(os.environ.get('SWITCH_DURATION', '30'))
    temp_unit = os.environ.get('TEMP_UNIT', 'C')
    debug_logging = os.environ.get('DEBUG_LOGGING', 'false').lower() in ('true', '1', 'yes')
    show_credits = os.environ.get('SHOW_CREDITS', 'true').lower() in ('true', '1', 'yes')
    screen_off_until_button = os.environ.get('SCREEN_OFF_UNTIL_BUTTON', 'false').lower() in ('true', '1', 'yes')
    idle_dim_timeout = int(os.environ.get('IDLE_DIM_TIMEOUT', '60'))
    button_source = os.environ.get('BUTTON_SOURCE', 'power_key').strip().lower()
    
    # Get version from environment (set by run.sh from config.yaml)
    version = os.environ.get('ADDON_VERSION', '1.0.0')
    
    # Create and run the OLED display
    oled = ArgonOLED(
        screen_list,
        switch_duration,
        temp_unit,
        debug_logging,
        show_credits,
        version,
        screen_off_until_button,
        idle_dim_timeout,
        button_source,
    )
    oled.run()


if __name__ == '__main__':
    main()
