import math
import os
import tempfile
import unittest

from font_renderer import measure_text, pixel_height
from hold_detector import HoldDetector
from operating_modes import (
    SETTINGS_CHOICES,
    apply_brightness,
    brightness_duty,
    brightness_lines,
    confirm_restore_defaults,
    configure_operating_mode,
    mode_menu_lines,
    restore_confirmation_lines,
    rotation_lines,
    select_brightness,
    select_operating_mode,
    select_rotation,
    settings_menu_lines,
)
from settings import DEFAULT_USER_PARAMS, file_in


class FakeClock:
    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, current, previous):
        return current - previous


class FakeLCD:
    def __init__(self):
        self.duties = []
        self.rotations = []

    def set_bl_pwm(self, duty):
        self.duties.append(duty)

    def set_rotation(self, degrees):
        self.rotations.append(degrees)


class FakeTouch:
    def __init__(self, gestures):
        self.gestures = iter(gestures)
        self.screens = []
        self.rotations = []

    def ControlScreen(self, lcd, text_array=None, back_colour=None):
        self.screens.append((text_array, back_colour))

    def GetGesture(self, lcd):
        return next(self.gestures)

    def Set_Rotation(self, degrees):
        self.rotations.append(degrees)


class OperatingModeTests(unittest.TestCase):
    def assert_round_fit(self, lines):
        radius = 120
        for text, _x, y_position, size, _colour in lines:
            text_center_y = y_position + (pixel_height(size) / 2)
            distance = text_center_y - radius
            visible_width = 2 * math.sqrt(
                (radius * radius) - (distance * distance)
            )
            self.assertLessEqual(measure_text(text, size), visible_width)

    def test_hold_triggers_once_at_five_continuous_seconds(self):
        clock = FakeClock()
        detector = HoldDetector(5, clock=clock)

        self.assertFalse(detector.update(True))
        clock.now = 4_999
        self.assertFalse(detector.update(True))
        clock.now = 5_000
        self.assertTrue(detector.update(True))
        clock.now = 7_000
        self.assertFalse(detector.update(True))

    def test_release_before_threshold_resets_hold_progress(self):
        clock = FakeClock()
        detector = HoldDetector(5, clock=clock)

        self.assertFalse(detector.update(True))
        clock.now = 4_000
        self.assertFalse(detector.update(False))
        clock.now = 10_000
        self.assertFalse(detector.update(True))
        clock.now = 14_999
        self.assertFalse(detector.update(True))
        clock.now = 15_000
        self.assertTrue(detector.update(True))

    def test_hold_duration_must_be_positive(self):
        for invalid in (0, -1):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    HoldDetector(invalid)

    def test_brightness_maps_to_pwm_range(self):
        self.assertEqual(0, brightness_duty(0))
        self.assertEqual(65535, brightness_duty(100))
        self.assertEqual(int(round(65535 * 0.25)), brightness_duty(25))

        lcd = FakeLCD()
        apply_brightness(lcd, 50)
        self.assertEqual(brightness_duty(50), lcd.duties[-1])

    def test_mode_navigation_selects_and_cancels(self):
        selected = select_operating_mode(
            FakeTouch(["right", "up"]),
            object(),
            "timer",
        )
        cancelled = select_operating_mode(
            FakeTouch(["left", "down"]),
            object(),
            "timer",
        )

        self.assertEqual("g", selected)
        self.assertIsNone(cancelled)

    def test_all_menu_text_fits_round_display_at_every_rotation(self):
        for rotation in (0, 90, 180, 270):
            for index in range(len(SETTINGS_CHOICES)):
                self.assert_round_fit(settings_menu_lines(index))
            for index in range(3):
                self.assert_round_fit(mode_menu_lines(index))
            for brightness in (25, 50, 75, 100):
                self.assert_round_fit(brightness_lines(brightness))
            self.assert_round_fit(rotation_lines(rotation))
            for selected in ("Cancel", "RESTORE"):
                self.assert_round_fit(restore_confirmation_lines(selected))

    def test_brightness_cancel_restores_previous_preview(self):
        lcd = FakeLCD()
        selected, should_save = select_brightness(
            FakeTouch(["left", "down"]),
            lcd,
            100,
        )

        self.assertEqual(100, selected)
        self.assertFalse(should_save)
        self.assertIn(brightness_duty(75), lcd.duties)
        self.assertEqual(brightness_duty(100), lcd.duties[-1])

    def test_rotation_cancel_restores_display_and_touch_preview(self):
        lcd = FakeLCD()
        touch = FakeTouch(["right", "down"])

        selected, should_save = select_rotation(touch, lcd, 0)

        self.assertEqual(0, selected)
        self.assertFalse(should_save)
        self.assertEqual([0, 90, 0], lcd.rotations)
        self.assertEqual([0, 90, 0], touch.rotations)

    def test_rotation_setting_is_previewed_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            lcd = FakeLCD()
            touch = FakeTouch(
                [
                    "left", "up",       # Settings
                    "right", "up",      # Rotation
                    "right", "up",      # 90 degrees, save
                    "down",              # leave Settings
                    "down",              # cancel mode menu
                ]
            )

            updated, mode = configure_operating_mode(
                touch,
                lcd,
                dict(DEFAULT_USER_PARAMS),
                path,
            )

            self.assertEqual("timer", mode)
            self.assertEqual(90, updated["DISPLAY_ROTATION_DEG"])
            self.assertEqual(
                90,
                file_in(path, debug=False)["DISPLAY_ROTATION_DEG"],
            )
            self.assertEqual(90, lcd.rotations[-1])
            self.assertEqual(90, touch.rotations[-1])

    def test_selected_mode_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            user_params = dict(DEFAULT_USER_PARAMS)

            updated, mode = configure_operating_mode(
                FakeTouch(["right", "up"]),
                FakeLCD(),
                user_params,
                path,
            )

            self.assertEqual("g", mode)
            self.assertEqual("g", updated["OPERATING_MODE"])
            self.assertEqual("g", file_in(path, debug=False)["OPERATING_MODE"])

    def test_brightness_setting_is_previewed_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            lcd = FakeLCD()

            updated, mode = configure_operating_mode(
                FakeTouch(
                    [
                        "left", "up",       # Settings
                        "up",               # Brightness
                        "left", "up",       # 75%, save
                        "down",             # leave Settings
                        "down",             # cancel mode menu
                    ]
                ),
                lcd,
                dict(DEFAULT_USER_PARAMS),
                path,
            )

            self.assertEqual("timer", mode)
            self.assertEqual(75, updated["BRIGHTNESS_PERCENT"])
            self.assertEqual(75, file_in(path, debug=False)["BRIGHTNESS_PERCENT"])
            self.assertIn(brightness_duty(75), lcd.duties)

    def test_restore_defaults_requires_confirmation_and_returns_timer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            changed = dict(DEFAULT_USER_PARAMS)
            changed["OPERATING_MODE"] = "g"
            changed["BRIGHTNESS_PERCENT"] = 25
            changed["DISPLAY_ROTATION_DEG"] = 180
            changed["RACE_LENGTH"] = 60
            lcd = FakeLCD()
            touch = FakeTouch(
                [
                    "right", "up",      # Settings from G Mode
                    "right", "right", "up",  # Restore defaults
                    "right", "up",      # Confirm RESTORE
                ]
            )

            updated, mode = configure_operating_mode(
                touch,
                lcd,
                changed,
                path,
            )

            self.assertEqual("timer", mode)
            self.assertEqual(DEFAULT_USER_PARAMS, updated)
            self.assertEqual(DEFAULT_USER_PARAMS, file_in(path, debug=False))
            self.assertEqual(0, lcd.rotations[-1])
            self.assertEqual(0, touch.rotations[-1])

    def test_restore_defaults_can_be_cancelled_after_viewing_restore(self):
        confirmed = confirm_restore_defaults(
            FakeTouch(["right", "down"]),
            object(),
        )

        self.assertFalse(confirmed)


if __name__ == "__main__":
    unittest.main()
