import importlib
import sys
import types
import unittest

from font_renderer import measure_text
import live_screen_graphics


def import_touch_driver():
    machine = types.ModuleType("machine")
    for name in ("Pin", "I2C", "SPI", "PWM", "Timer", "ADC"):
        setattr(machine, name, object)
    framebuf = types.ModuleType("framebuf")

    original_machine = sys.modules.get("machine")
    original_framebuf = sys.modules.get("framebuf")
    sys.modules["machine"] = machine
    sys.modules["framebuf"] = framebuf
    try:
        return importlib.import_module("touch_drive")
    finally:
        if original_machine is None:
            del sys.modules["machine"]
        else:
            sys.modules["machine"] = original_machine
        if original_framebuf is None:
            del sys.modules["framebuf"]
        else:
            sys.modules["framebuf"] = original_framebuf


touch_drive = import_touch_driver()


class TouchModeTests(unittest.TestCase):
    def make_touch(self):
        touch = touch_drive.Touch_CST816T.__new__(touch_drive.Touch_CST816T)
        touch.Mode = 1
        touch.rotation = 0
        touch._configured_mode = None
        touch.writes = []
        touch._write_byte = lambda command, value: touch.writes.append(
            (command, value)
        )
        return touch

    def test_unchanged_gesture_mode_is_not_rewritten(self):
        touch = self.make_touch()

        self.assertTrue(touch.Set_Mode(0))
        self.assertFalse(touch.Set_Mode(0))

        self.assertEqual(0, touch.Mode)
        self.assertEqual([(0xFA, 0x11), (0xEC, 0x01)], touch.writes)

    def test_changed_mode_is_written_once(self):
        touch = self.make_touch()
        touch.Set_Mode(0)

        self.assertTrue(touch.Set_Mode(1))
        self.assertFalse(touch.Set_Mode(1))

        self.assertEqual(1, touch.Mode)
        self.assertEqual((0xFA, 0x41), touch.writes[-1])
        self.assertEqual(3, len(touch.writes))

    def test_directional_gestures_follow_each_mount_rotation(self):
        touch = self.make_touch()
        gestures = (
            touch_drive.G_UP,
            touch_drive.G_RIGHT,
            touch_drive.G_DOWN,
            touch_drive.G_LEFT,
        )
        expected = {
            0: ("up", "right", "down", "left"),
            90: ("right", "down", "left", "up"),
            180: ("down", "left", "up", "right"),
            270: ("left", "up", "right", "down"),
        }

        for rotation, directions in expected.items():
            with self.subTest(rotation=rotation):
                touch.Set_Rotation(rotation)
                self.assertEqual(
                    directions,
                    tuple(touch._gesture_name(value) for value in gestures),
                )

    def test_clear_gesture_uses_viewer_relative_up(self):
        touch = self.make_touch()
        touch.Set_Rotation(90)
        touch.Gestures = touch_drive.G_LEFT
        self.assertTrue(touch.ClearGesture(None))

        touch.Gestures = touch_drive.G_UP
        self.assertFalse(touch.ClearGesture(None))

    def test_live_screen_places_smaller_maximum_g_clear_of_countdown(self):
        self.assertEqual(
            ("MAX", "1.23 g"),
            live_screen_graphics.maximum_g_parts("MAX  1.23  g"),
        )
        self.assertEqual(
            ("MAX", "--"),
            live_screen_graphics.maximum_g_parts("MAX --"),
        )

        class FakeLCD:
            green = 1
            white = 2
            width = 240

            def __init__(self):
                self.calls = []

            def fill(self, colour):
                self.calls.append(("fill", colour))

            def write_time_centered(self, *args):
                self.calls.append(("write_time_centered",) + args)

            def text_width(self, text, size, tabular_digits=False):
                return measure_text(
                    text,
                    size,
                    tabular_digits=tabular_digits,
                )

            def write_text(
                self,
                text,
                x_position,
                y_position,
                size,
                colour,
                tabular_digits=False,
            ):
                self.calls.append(
                    (
                        "write_text",
                        text,
                        x_position,
                        y_position,
                        size,
                        colour,
                        tabular_digits,
                    )
                )

            def show(self):
                self.calls.append(("show",))

        touch = self.make_touch()
        lcd = FakeLCD()

        touch.LiveScreen(
            lcd,
            textsize_rem=7,
            backColour=lcd.green,
            textColour=lcd.white,
            elapsed="00:12",
            remaining="19:48",
            maximum_g="MAX  1.23  g",
        )

        max_calls = [call for call in lcd.calls if call[0] == "write_text"]
        value = "1.23 g"
        label_width = measure_text("MAX", 1)
        value_width = measure_text(value, 3, tabular_digits=True)
        label_x = (lcd.width - label_width - 8 - value_width) // 2
        self.assertEqual(
            [
                ("write_text", "MAX", label_x, 45, 1, lcd.white, False),
                (
                    "write_text",
                    value,
                    label_x + label_width + 8,
                    36,
                    3,
                    lcd.white,
                    True,
                ),
            ],
            max_calls,
        )
        time_calls = [
            call for call in lcd.calls if call[0] == "write_time_centered"
        ]
        self.assertEqual(
            [
                ("write_time_centered", "19:48", 82, 7, lcd.white),
                ("write_time_centered", "00:12", 180, 3, lcd.white),
            ],
            time_calls,
        )
        self.assertEqual(("show",), lcd.calls[-1])

    def test_live_screen_uses_small_lap_label_and_larger_value(self):
        class FakeLCD:
            green = 1
            white = 2

            def __init__(self):
                self.calls = []

            def fill(self, colour):
                self.calls.append(("fill", colour))

            def write_time_centered(self, *args):
                self.calls.append(("write_time_centered",) + args)

            def show(self):
                self.calls.append(("show",))

        touch = self.make_touch()
        lcd = FakeLCD()

        touch.LiveScreen(
            lcd,
            textsize_rem=7,
            backColour=lcd.green,
            textColour=lcd.white,
            elapsed=("LAP", "6.7"),
            remaining="19:48",
        )

        text_calls = [
            call for call in lcd.calls if call[0] == "write_time_centered"
        ]
        self.assertEqual(
            [
                ("write_time_centered", "19:48", 82, 7, lcd.white),
                ("write_time_centered", "LAP", 160, 1, lcd.white),
                ("write_time_centered", "6.7", 176, 4, lcd.white),
            ],
            text_calls,
        )

    def test_live_screen_draws_bounded_progress_ring_and_phase_label(self):
        class FakeLCD:
            green = 1
            white = 2

            def __init__(self):
                self.calls = []

            def fill(self, colour):
                self.calls.append(("fill", colour))

            def line(self, *args):
                self.calls.append(("line",) + args)

            def write_time_centered(self, *args):
                self.calls.append(("write_time_centered",) + args)

            def show(self):
                self.calls.append(("show",))

        touch = self.make_touch()
        lcd = FakeLCD()

        packed_points = live_screen_graphics.PROGRESS_RING_POINTS
        self.assertEqual(74, len(packed_points))
        for offset in range(0, len(packed_points), 2):
            x_position = packed_points[offset]
            y_position = packed_points[offset + 1]
            self.assertTrue(0 <= x_position < 240)
            self.assertTrue(0 <= y_position < 240)
            radius = (
                ((x_position - 120) ** 2) + ((y_position - 120) ** 2)
            ) ** 0.5
            self.assertGreaterEqual(radius, 111)
            self.assertLessEqual(radius, 113)

        touch.LiveScreen(
            lcd,
            textsize_rem=7,
            backColour=lcd.green,
            textColour=lcd.white,
            elapsed="00:12",
            remaining="19:48",
            progress_segments=18,
            phase_label="WARNING",
        )

        ring_lines = [call for call in lcd.calls if call[0] == "line"]
        self.assertEqual(36, len(ring_lines))
        for _name, x1, y1, x2, y2, colour in ring_lines:
            self.assertTrue(
                all(0 <= value < 240 for value in (x1, y1, x2, y2))
            )
            self.assertEqual(lcd.white, colour)
        self.assertIn(
            (
                "write_time_centered",
                "WARNING",
                live_screen_graphics.PROGRESS_PHASE_Y,
                live_screen_graphics.PROGRESS_PHASE_TEXT_SIZE,
                lcd.white,
            ),
            lcd.calls,
        )
        self.assertEqual(("show",), lcd.calls[-1])


if __name__ == "__main__":
    unittest.main()
