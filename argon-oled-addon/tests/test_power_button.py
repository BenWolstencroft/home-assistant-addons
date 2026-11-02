"""Tests for the power-key button source and the shared gesture rules."""

import os
import struct
import unittest
from unittest.mock import patch

try:
    import argon_oled
    from argon_oled import (
        EV_KEY,
        KEY_POWER,
        POWER_KEY_SOURCE_WARNING,
        GPIO_SOURCE_WARNING,
        discover_power_button_paths,
        unpack_input_events,
        PowerKeyDevice,
    )
    from tests.test_display_blanking import make_oled, _fake_canvas
    ARGON_AVAILABLE = True
except ImportError:
    ARGON_AVAILABLE = False


PROC_SAMPLE = """
I: Bus=0019 Vendor=0001 Product=0001 Version=0100
N: Name="pwr_button"
P: Phys=gpio-keys/input0
S: Sysfs=/devices/platform/pwr_button/input/input1
U: Uniq=
H: Handlers=kbd event1
B: PROP=0
B: EV=3
B: KEY=10000000000000

I: Bus=0000 Vendor=0000 Product=0000 Version=0000
N: Name="other"
H: Handlers=event0
"""


def pack_events(events, fmt):
    chunks = []
    for ev_type, code, value in events:
        chunks.append(struct.pack(fmt, 0, 0, ev_type, code, value))
    return b"".join(chunks)


class ScriptedKey:
    """Level source driven by a fake clock. presses are (start, end) intervals."""

    def __init__(self, presses, clock, oled):
        self.presses = presses
        self.clock = clock
        self.oled = oled

    def _held(self):
        now = self.clock["t"]
        return any(start <= now < end for start, end in self.presses)

    def wait_until_pressed(self):
        while not self._held():
            if self.oled.button_action:
                raise KeyboardInterrupt
            self.clock["t"] += 0.05
            if self.clock["t"] > self.presses[-1][1] + 2:
                raise KeyboardInterrupt

    def is_down(self):
        if self.oled.button_action:
            raise KeyboardInterrupt
        return self._held()

    def close(self):
        pass


@unittest.skipUnless(ARGON_AVAILABLE, "argon_oled module required")
class TestPowerButtonDiscovery(unittest.TestCase):
    def test_discovers_event_node_from_handlers_not_a_hardcoded_index(self):
        paths = discover_power_button_paths(PROC_SAMPLE, by_path="/dev/input/by-path/platform-pwr_button-event")
        self.assertEqual(paths[0], "/dev/input/event1")
        self.assertNotIn("/dev/input/event0", paths[:1])
        self.assertIn("/dev/input/by-path/platform-pwr_button-event", paths)

    def test_quoted_name_must_match_exactly(self):
        text = 'N: Name="not_pwr_button"\nH: Handlers=event3\n\n'
        paths = discover_power_button_paths(text, by_path=None)
        self.assertEqual(paths, [])

    def test_unpack_both_word_sizes(self):
        for fmt in ("llHHi", "iiHHi"):
            raw = pack_events([(EV_KEY, KEY_POWER, 1), (0, 0, 0), (EV_KEY, KEY_POWER, 0)], fmt)
            # Split a byte off the end so the trailing partial event is kept.
            events, rest = unpack_input_events(raw + b"\x00", fmt)
            self.assertEqual(events, [(EV_KEY, KEY_POWER, 1), (0, 0, 0), (EV_KEY, KEY_POWER, 0)])
            self.assertEqual(rest, b"\x00")

    def test_device_sees_press_then_release_and_ignores_repeat(self):
        read_fd, write_fd = os.pipe()
        try:
            fmt = "llHHi"
            os.write(write_fd, pack_events([
                (EV_KEY, KEY_POWER, 1),
                (EV_KEY, KEY_POWER, 2),
                (0, 0, 0),
            ], fmt))
            device = PowerKeyDevice(read_fd, fmt=fmt)
            device.wait_until_pressed()
            self.assertTrue(device.held)
            os.write(write_fd, pack_events([(EV_KEY, KEY_POWER, 0)], fmt))
            self.assertFalse(device.is_down())
            device.close()
        finally:
            os.close(write_fd)

    def test_press_and_release_in_one_read_are_not_lost(self):
        read_fd, write_fd = os.pipe()
        try:
            fmt = "iiHHi"
            os.write(write_fd, pack_events([
                (EV_KEY, KEY_POWER, 1),
                (EV_KEY, KEY_POWER, 0),
            ], fmt))
            device = PowerKeyDevice(read_fd, fmt=fmt)
            device.wait_until_pressed()
            self.assertTrue(device.held)
            self.assertFalse(device.is_down())
        finally:
            os.close(write_fd)
            try:
                device.close()
            except Exception:
                os.close(read_fd)


@unittest.skipUnless(ARGON_AVAILABLE, "argon_oled module required")
class TestGesturesFromEitherSource(unittest.TestCase):
    def setUp(self):
        self.clock = {"t": 999.0}

    def _time(self):
        return self.clock["t"]

    def _sleep(self, dt):
        self.clock["t"] += dt

    def _run_power_key(self, oled, presses):
        device = ScriptedKey(presses, self.clock, oled)
        with patch("argon_oled.time.time", self._time), \
                patch("argon_oled.time.sleep", self._sleep), \
                patch("argon_oled.canvas", _fake_canvas):
            with self.assertRaises(KeyboardInterrupt):
                oled._monitor_power_key(device)

    def _run_gpio(self, oled, presses):
        def get_value(_pin):
            if oled.button_action:
                raise KeyboardInterrupt
            now = self.clock["t"]
            for start, end in presses:
                if start <= now < end:
                    return argon_oled.Value.INACTIVE
            return argon_oled.Value.ACTIVE

        oled.gpio_line.get_value.side_effect = get_value
        oled.button_source = "gpio"
        with patch("argon_oled.time.time", self._time), \
                patch("argon_oled.time.sleep", self._sleep), \
                patch("argon_oled.canvas", _fake_canvas):
            with self.assertRaises(KeyboardInterrupt):
                oled.button_monitor()

    def test_single_double_and_long_match_on_both_sources(self):
        cases = [
            ([(1000.0, 1000.1)], "next"),
            ([(1000.0, 1000.1), (1000.2, 1000.3)], "prev"),
            ([(1000.0, 1000.8)], "first"),
        ]
        for presses, action in cases:
            for source in ("power_key", "gpio"):
                with self.subTest(source=source, action=action):
                    self.clock["t"] = 999.0
                    oled = make_oled(button_source=source, screen_off_until_button=True, display_blanked=True)
                    if source == "power_key":
                        self._run_power_key(oled, presses)
                    else:
                        self._run_gpio(oled, presses)
                    self.assertEqual(oled.button_action, action)
                    self.assertFalse(oled.display_blanked)
                    oled.device.show.assert_called()
                    oled.device.hide.assert_not_called()

    def test_ten_second_hold_from_blank_confirms_reboot_on_power_key(self):
        oled = make_oled(
            button_source="power_key",
            screen_off_until_button=True,
            display_blanked=True,
            power_management_enabled=True,
        )
        seen = {}

        def countdown(name):
            seen["name"] = name
            seen["blanked"] = oled.display_blanked
            seen["hold"] = oled.button_in_power_hold
            oled._restore_after_power_ui()
            return True

        oled._draw_confirmation_countdown = countdown
        self._run_power_key(oled, [(1000.0, 1010.3)])
        self.assertEqual(seen["name"], "REBOOT")
        self.assertFalse(seen["blanked"])
        self.assertTrue(seen["hold"])
        self.assertFalse(oled.display_blanked)

    def test_missing_power_key_warns_and_does_not_fall_back_to_gpio(self):
        oled = make_oled(button_source="power_key")
        with patch("argon_oled.open_power_button", return_value=(None, None, "enoent")), \
                patch("sys.stdout") as stdout:
            oled.button_monitor()
        text = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("button_source", text)
        self.assertIn("power_key", text)
        self.assertIn(POWER_KEY_SOURCE_WARNING, text)
        oled.gpio_line.get_value.assert_not_called()

    def test_missing_gpio_warns_and_names_the_option(self):
        oled = make_oled(button_source="gpio", gpio_line=None)
        with patch("sys.stdout") as stdout:
            oled.button_monitor()
        text = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn(GPIO_SOURCE_WARNING, text)
        self.assertIn("power_key", text)

    def test_main_reads_button_source(self):
        env = {
            "SCREEN_LIST": "clock",
            "SWITCH_DURATION": "30",
            "TEMP_UNIT": "C",
            "DEBUG_LOGGING": "false",
            "SHOW_CREDITS": "true",
            "SCREEN_OFF_UNTIL_BUTTON": "false",
            "IDLE_DIM_TIMEOUT": "60",
            "BUTTON_SOURCE": "gpio",
            "ADDON_VERSION": "1.18.0",
        }
        with patch.dict(os.environ, env, clear=False), \
                patch("argon_oled.ArgonOLED") as cls:
            argon_oled.main()
        self.assertEqual(cls.call_args[0][8], "gpio")

    def test_power_key_cancels_countdown_after_release(self):
        oled = make_oled(
            button_source="power_key",
            gpio_line=None,
            screen_off_until_button=True,
            display_blanked=False,
            button_in_power_hold=True,
        )
        states = [False, True]

        class Seq:
            def is_down(self):
                if states:
                    return states.pop(0)
                return True

        oled._power_key = Seq()
        with patch("argon_oled.time.sleep", lambda _dt: None), \
                patch("argon_oled.canvas", _fake_canvas):
            cancelled = oled._draw_confirmation_countdown("REBOOT")
        self.assertTrue(cancelled)
        self.assertFalse(oled.button_in_power_hold)
        self.assertFalse(oled.display_blanked)


if __name__ == "__main__":
    unittest.main()
