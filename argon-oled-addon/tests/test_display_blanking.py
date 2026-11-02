"""Tests for blank-until-button mode.

Hardware is not required. The panel object is a mock, and the button
monitor is driven with a scripted GPIO line and a fake clock.
"""

import os
import threading
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

try:
    import argon_oled
    ARGON_AVAILABLE = True
except ImportError:
    ARGON_AVAILABLE = False
    argon_oled = None


if ARGON_AVAILABLE and argon_oled.Value is None:
    class _Value:
        ACTIVE = 1
        INACTIVE = 0

    argon_oled.Value = _Value


@contextmanager
def _fake_canvas(device):
    yield MagicMock()


def make_oled(**overrides):
    """Build an ArgonOLED without touching I2C or GPIO hardware."""
    oled = argon_oled.ArgonOLED.__new__(argon_oled.ArgonOLED)
    oled.screen_list = ["logo", "clock", "cpu"]
    oled.switch_duration = 30
    oled.temp_unit = "C"
    oled.screen_off_until_button = False
    oled.idle_dim_timeout = 60
    oled.display_blanked = False
    oled.button_held = False
    oled.button_in_power_hold = False
    oled.button_action = None
    oled.current_screen = 0
    oled.last_switch = 0
    oled.last_activity = 0
    oled.debug_logging = False
    oled.power_management_enabled = True
    oled.show_credits = True
    oled.credits_shown = False
    oled.version = "1.17.0"
    oled.button_source = "gpio"
    oled._power_key = None
    oled._panel_lock = threading.Lock()
    oled._refresh = threading.Event()
    oled.device = MagicMock()
    oled.device.bounding_box = (0, 0, 127, 63)
    oled.font_small = MagicMock()
    oled.font_medium = MagicMock()
    oled.font_large = MagicMock()
    oled.gpio_line = MagicMock()
    oled.renderer = MagicMock()
    for key, value in overrides.items():
        setattr(oled, key, value)
    return oled


@unittest.skipUnless(ARGON_AVAILABLE, "argon_oled module required")
class TestBlankingHelpers(unittest.TestCase):
    """Idle blank, wake, and power-prompt panel state."""

    def test_mode_off_never_hides_or_shows(self):
        oled = make_oled(screen_off_until_button=False, display_blanked=False)
        oled.last_activity = 0
        with patch("argon_oled.time.time", return_value=100000):
            self.assertFalse(oled._maybe_blank())
            oled._on_button_activity()
        oled.device.hide.assert_not_called()
        oled.device.show.assert_not_called()
        self.assertFalse(oled.display_blanked)

    def test_idle_timeout_hides_at_and_not_before_boundary(self):
        oled = make_oled(screen_off_until_button=True, idle_dim_timeout=60)
        oled.last_activity = 940.1
        with patch("argon_oled.time.time", return_value=1000.0):
            self.assertFalse(oled._maybe_blank())
        oled.device.hide.assert_not_called()

        oled.last_activity = 940.0
        with patch("argon_oled.time.time", return_value=1000.0):
            self.assertTrue(oled._maybe_blank())
        oled.device.hide.assert_called_once()
        self.assertTrue(oled.display_blanked)

    def test_hold_and_power_prompt_block_blanking(self):
        oled = make_oled(
            screen_off_until_button=True,
            idle_dim_timeout=5,
            button_held=True,
        )
        with patch("argon_oled.time.time", return_value=10000):
            self.assertFalse(oled._maybe_blank())
        oled.button_held = False
        oled.button_in_power_hold = True
        with patch("argon_oled.time.time", return_value=10000):
            self.assertFalse(oled._maybe_blank())
        oled.device.hide.assert_not_called()

    def test_wake_shows_panel_without_setting_a_gesture(self):
        oled = make_oled(screen_off_until_button=True, display_blanked=True)
        oled.last_switch = 0
        oled.button_action = None
        with patch("argon_oled.time.time", return_value=5000.0):
            oled._on_button_activity()
        oled.device.show.assert_called_once()
        oled.device.hide.assert_not_called()
        self.assertFalse(oled.display_blanked)
        self.assertIsNone(oled.button_action)
        self.assertEqual(oled.last_activity, 5000.0)
        # Stale rotation interval must not fire on the waking pass.
        self.assertEqual(oled.last_switch, 5000.0)
        self.assertTrue(oled._refresh.is_set())

    def test_wake_while_already_on_only_resets_timer(self):
        oled = make_oled(screen_off_until_button=True, display_blanked=False)
        oled.last_switch = 10
        with patch("argon_oled.time.time", return_value=80.0):
            oled._on_button_activity()
        oled.device.show.assert_not_called()
        self.assertEqual(oled.last_activity, 80.0)
        self.assertEqual(oled.last_switch, 10)

    def test_failed_show_stays_blank_so_frames_are_not_drawn(self):
        oled = make_oled(screen_off_until_button=True, display_blanked=True)
        oled.device.show.side_effect = OSError("i2c")
        oled._on_button_activity()
        self.assertTrue(oled.display_blanked)

    def test_power_ui_turns_panel_on_before_drawing(self):
        oled = make_oled(screen_off_until_button=True, display_blanked=True)
        oled._ensure_panel_on_for_power_ui()
        oled.device.show.assert_called_once()
        self.assertFalse(oled.display_blanked)
        self.assertTrue(oled.button_in_power_hold)

    def test_power_ui_flag_when_mode_is_off_does_not_touch_display_power(self):
        oled = make_oled(screen_off_until_button=False, display_blanked=False)
        oled._ensure_panel_on_for_power_ui()
        self.assertTrue(oled.button_in_power_hold)
        oled.device.show.assert_not_called()
        oled.device.hide.assert_not_called()

    def test_cancel_restores_awake_state_and_idle_timer(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=True,
            button_in_power_hold=True,
        )
        with patch("argon_oled.time.time", return_value=42.0):
            oled._restore_after_power_ui()
        self.assertFalse(oled.display_blanked)
        self.assertFalse(oled.button_in_power_hold)
        self.assertEqual(oled.last_activity, 42.0)
        oled.device.show.assert_called_once()

    def test_cancel_when_mode_off_only_clears_the_hold_flag(self):
        oled = make_oled(screen_off_until_button=False, button_in_power_hold=True)
        oled._restore_after_power_ui()
        self.assertFalse(oled.button_in_power_hold)
        oled.device.show.assert_not_called()


@unittest.skipUnless(ARGON_AVAILABLE, "argon_oled module required")
class TestRotationDoesNotRaceBlanking(unittest.TestCase):
    """A stale auto-rotation timer must not draw while the panel is off."""

    def test_blanked_panel_does_not_rotate_or_draw(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=True,
            current_screen=1,
        )
        oled.last_switch = 0
        oled.display_screen = MagicMock()
        oled._service_once(100000)
        self.assertEqual(oled.current_screen, 1)
        oled.display_screen.assert_not_called()

    def test_same_pass_cannot_hide_and_then_draw(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=False,
            idle_dim_timeout=60,
            current_screen=0,
        )
        oled.last_activity = 0
        oled.last_switch = 0
        oled.display_screen = MagicMock()
        with patch("argon_oled.time.time", return_value=1000.0):
            oled._service_once(1000.0)
        self.assertTrue(oled.display_blanked)
        self.assertEqual(oled.current_screen, 0)
        oled.display_screen.assert_not_called()
        oled.device.hide.assert_called()

    def test_blank_immediately_before_draw_still_skips_the_frame(self):
        """Timeout can elapse after the rotation check and before the draw."""
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=False,
            idle_dim_timeout=60,
        )
        oled.last_activity = 950.0  # 50s idle at t=1000, 1050s at t=2000
        oled.last_switch = 1000.0
        oled.display_screen = MagicMock()
        calls = {"n": 0}

        def now():
            calls["n"] += 1
            return 1000.0 if calls["n"] == 1 else 2000.0

        with patch("argon_oled.time.time", side_effect=now):
            oled._service_once(1000.0)
        self.assertTrue(oled.display_blanked)
        oled.display_screen.assert_not_called()

    def test_wake_resumes_current_screen_then_gesture_steps_once(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=True,
            current_screen=1,
        )
        oled.last_switch = 0
        oled.display_screen = MagicMock()
        with patch("argon_oled.time.time", return_value=8000.0):
            oled._on_button_activity()
            oled._service_once(8000.0)
        # Waking must not also apply the stale rotation interval.
        self.assertEqual(oled.current_screen, 1)
        oled.display_screen.assert_called_once_with("clock")

        oled.button_action = "next"
        oled.last_activity = 8001.0
        oled.display_screen.reset_mock()
        with patch("argon_oled.time.time", return_value=8001.0):
            oled._service_once(8001.0)
        self.assertEqual(oled.current_screen, 2)
        oled.display_screen.assert_called_once_with("cpu")
        self.assertIsNone(oled.button_action)

    def test_mode_off_still_rotates_and_draws(self):
        oled = make_oled(screen_off_until_button=False, current_screen=0)
        oled.last_switch = 0
        oled.last_activity = 0
        oled.display_screen = MagicMock()
        oled._service_once(1000)
        self.assertEqual(oled.current_screen, 1)
        oled.display_screen.assert_called_once_with("clock")
        oled.device.hide.assert_not_called()

    def test_button_action_is_not_combined_with_auto_rotation(self):
        oled = make_oled(screen_off_until_button=False, current_screen=0)
        oled.last_switch = 0
        oled.button_action = "next"
        oled.display_screen = MagicMock()
        oled._service_once(1000)
        # One step from the press, not a second step from the stale timer.
        self.assertEqual(oled.current_screen, 1)

    def test_display_screen_refuses_to_draw_while_blanked(self):
        oled = make_oled(display_blanked=True)
        oled.display_screen("clock")
        oled.renderer.draw_clock.assert_not_called()

    def test_credits_skipped_when_booting_dark(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=True,
            show_credits=True,
            credits_shown=False,
        )

        def stop(_current_time):
            raise KeyboardInterrupt

        oled._service_once = stop
        oled.gpio_line = None
        with patch.object(argon_oled, "GPIO_AVAILABLE", False):
            oled.run()
        oled.renderer.draw_credits.assert_not_called()
        self.assertTrue(oled.credits_shown)

    def test_credits_still_shown_when_mode_is_off(self):
        oled = make_oled(
            screen_off_until_button=False,
            display_blanked=False,
            show_credits=True,
            credits_shown=False,
        )

        def stop(_current_time):
            raise KeyboardInterrupt

        oled._service_once = stop
        oled.gpio_line = None
        with patch.object(argon_oled, "GPIO_AVAILABLE", False), \
                patch("argon_oled.time.sleep", lambda _dt: None):
            oled.run()
        oled.renderer.draw_credits.assert_called_once()


@unittest.skipUnless(ARGON_AVAILABLE, "argon_oled module required")
class TestButtonGesturesWhileBlanked(unittest.TestCase):
    """The waking press still runs through the original classifier."""

    def setUp(self):
        self.clock = {"t": 1000.0}

    def _now(self):
        return self.clock["t"]

    def _sleep(self, dt):
        self.clock["t"] += dt

    def _run_monitor(self, oled, pressed_until, countdown=None):
        """Run button_monitor until it has classified one gesture."""

        def get_value(_pin):
            if oled.button_action:
                raise KeyboardInterrupt
            if self.clock["t"] < pressed_until:
                return argon_oled.Value.INACTIVE
            return argon_oled.Value.ACTIVE

        oled.gpio_line.get_value.side_effect = get_value
        if countdown is not None:
            oled._draw_confirmation_countdown = countdown
        with patch("argon_oled.time.time", self._now), \
                patch("argon_oled.time.sleep", self._sleep), \
                patch("argon_oled.canvas", _fake_canvas):
            with self.assertRaises(KeyboardInterrupt):
                oled.button_monitor()

    def test_single_press_from_blank_wakes_and_is_still_next(self):
        oled = make_oled(screen_off_until_button=True, display_blanked=True)
        # 100ms press. pulsetime stays below the long-press threshold.
        self._run_monitor(oled, pressed_until=1000.05)
        oled.device.show.assert_called()
        oled.device.hide.assert_not_called()
        self.assertFalse(oled.display_blanked)
        self.assertEqual(oled.button_action, "next")
        self.assertFalse(oled.button_held)

    def test_single_press_when_mode_off_does_not_call_show_or_hide(self):
        oled = make_oled(screen_off_until_button=False, display_blanked=False)
        self._run_monitor(oled, pressed_until=1000.05)
        oled.device.show.assert_not_called()
        oled.device.hide.assert_not_called()
        self.assertEqual(oled.button_action, "next")

    def test_long_press_is_still_first_screen(self):
        oled = make_oled(screen_off_until_button=True, display_blanked=True)
        # About one second: pulsetime >= 6 and well under the 10s power hold.
        self._run_monitor(oled, pressed_until=1000.8)
        self.assertEqual(oled.button_action, "first")
        self.assertFalse(oled.display_blanked)
        oled.device.show.assert_called()

    def test_ten_second_hold_from_blank_confirms_reboot_on_a_lit_panel(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=True,
            power_management_enabled=True,
        )
        seen = {}

        def countdown(action_name):
            seen["action"] = action_name
            seen["blanked"] = oled.display_blanked
            seen["hold"] = oled.button_in_power_hold
            seen["show_called"] = oled.device.show.called
            oled._restore_after_power_ui()
            return True

        self._run_monitor(oled, pressed_until=1010.25, countdown=countdown)
        self.assertEqual(seen["action"], "REBOOT")
        self.assertFalse(seen["blanked"])
        self.assertTrue(seen["hold"])
        self.assertTrue(seen["show_called"])
        self.assertFalse(oled.display_blanked)
        self.assertFalse(oled.button_in_power_hold)
        # Cancel restarts the idle timer at the end of the prompt.
        self.assertGreaterEqual(oled.last_activity, 1010.0)
        oled.device.hide.assert_not_called()

    def test_fifteen_second_hold_from_blank_confirms_shutdown(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=True,
            power_management_enabled=True,
        )
        seen = {}

        def countdown(action_name):
            seen["action"] = action_name
            seen["blanked"] = oled.display_blanked
            oled._restore_after_power_ui()
            return True

        self._run_monitor(oled, pressed_until=1015.25, countdown=countdown)
        self.assertEqual(seen["action"], "SHUTDOWN")
        self.assertFalse(seen["blanked"])
        self.assertFalse(oled.display_blanked)

    def test_power_hold_when_mode_off_does_not_call_show(self):
        oled = make_oled(screen_off_until_button=False, display_blanked=False)
        seen = {}

        def countdown(action_name):
            seen["action"] = action_name
            seen["hold"] = oled.button_in_power_hold
            return True

        self._run_monitor(oled, pressed_until=1010.25, countdown=countdown)
        self.assertEqual(seen["action"], "REBOOT")
        self.assertTrue(seen["hold"])
        oled.device.show.assert_not_called()
        oled.device.hide.assert_not_called()

    def test_permission_denied_hold_resumes_blanking_only_in_new_mode(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=True,
            power_management_enabled=False,
        )
        # No countdown in this branch; stop once the permission message has
        # cleared the power-hold flag (that is the end of the gesture).
        def get_value(_pin):
            if not oled.button_in_power_hold and self.clock["t"] > 1010.0:
                raise KeyboardInterrupt
            if self.clock["t"] < 1010.25:
                return argon_oled.Value.INACTIVE
            return argon_oled.Value.ACTIVE

        oled.gpio_line.get_value.side_effect = get_value
        with patch("argon_oled.time.time", self._now), \
                patch("argon_oled.time.sleep", self._sleep), \
                patch("argon_oled.canvas", _fake_canvas):
            with self.assertRaises(KeyboardInterrupt):
                oled.button_monitor()
        self.assertFalse(oled.button_in_power_hold)
        self.assertFalse(oled.display_blanked)
        oled.device.show.assert_called()

    def test_permission_denied_hold_leaves_flag_when_mode_is_off(self):
        oled = make_oled(
            screen_off_until_button=False,
            display_blanked=False,
            power_management_enabled=False,
        )

        def get_value(_pin):
            # The legacy path leaves button_in_power_hold set. Stop on the
            # idle poll after the 3s permission message.
            if self.clock["t"] > 1014.0:
                raise KeyboardInterrupt
            if self.clock["t"] < 1010.25:
                return argon_oled.Value.INACTIVE
            return argon_oled.Value.ACTIVE

        oled.gpio_line.get_value.side_effect = get_value
        with patch("argon_oled.time.time", self._now), \
                patch("argon_oled.time.sleep", self._sleep), \
                patch("argon_oled.canvas", _fake_canvas):
            with self.assertRaises(KeyboardInterrupt):
                oled.button_monitor()
        self.assertTrue(oled.button_in_power_hold)
        oled.device.show.assert_not_called()

    def test_countdown_cancel_draws_only_after_the_panel_is_on(self):
        oled = make_oled(
            screen_off_until_button=True,
            display_blanked=True,
            button_in_power_hold=True,
            last_activity=0,
        )
        states = [argon_oled.Value.ACTIVE, argon_oled.Value.INACTIVE]

        def get_value(_pin):
            if states:
                return states.pop(0)
            return argon_oled.Value.INACTIVE

        oled.gpio_line.get_value.side_effect = get_value
        shown_before_draw = []

        @contextmanager
        def canvas(device):
            shown_before_draw.append(oled.display_blanked)
            yield MagicMock()

        with patch("argon_oled.time.sleep", lambda _dt: None), \
                patch("argon_oled.canvas", canvas):
            cancelled = oled._draw_confirmation_countdown("REBOOT")
        self.assertTrue(cancelled)
        self.assertFalse(oled.display_blanked)
        self.assertFalse(oled.button_in_power_hold)
        self.assertGreater(oled.last_activity, 0)
        # Every frame, including CANCELLED, was drawn with the panel on.
        self.assertTrue(shown_before_draw)
        self.assertTrue(all(blanked is False for blanked in shown_before_draw))
        oled.device.show.assert_called()


@unittest.skipUnless(ARGON_AVAILABLE, "argon_oled module required")
class TestOptionParsing(unittest.TestCase):
    """run.sh exports the new options; main() reads the same names."""

    def test_main_passes_enabled_options(self):
        env = {
            "SCREEN_LIST": "clock cpu",
            "SWITCH_DURATION": "12",
            "TEMP_UNIT": "F",
            "DEBUG_LOGGING": "false",
            "SHOW_CREDITS": "false",
            "SCREEN_OFF_UNTIL_BUTTON": "true",
            "IDLE_DIM_TIMEOUT": "15",
            "ADDON_VERSION": "1.17.0",
        }
        with patch.dict(os.environ, env, clear=False), \
                patch("argon_oled.ArgonOLED") as cls:
            argon_oled.main()
        args = cls.call_args[0]
        self.assertEqual(args[0], ["clock", "cpu"])
        self.assertEqual(args[1], 12)
        self.assertEqual(args[2], "F")
        self.assertFalse(args[3])
        self.assertFalse(args[4])
        self.assertEqual(args[5], "1.17.0")
        self.assertTrue(args[6])
        self.assertEqual(args[7], 15)
        cls.return_value.run.assert_called_once()

    def test_main_defaults_preserve_existing_behaviour(self):
        removed = {
            "SCREEN_OFF_UNTIL_BUTTON",
            "IDLE_DIM_TIMEOUT",
            "SHOW_CREDITS",
            "DEBUG_LOGGING",
            "BUTTON_SOURCE",
        }
        env = {key: os.environ[key] for key in removed if key in os.environ}
        with patch.dict(os.environ, env, clear=False):
            for key in removed:
                os.environ.pop(key, None)
            with patch("argon_oled.ArgonOLED") as cls:
                argon_oled.main()
        args = cls.call_args[0]
        self.assertFalse(args[6])
        self.assertEqual(args[7], 60)
        self.assertEqual(args[8], "power_key")


if __name__ == "__main__":
    unittest.main()
