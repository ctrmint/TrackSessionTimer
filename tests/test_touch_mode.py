import importlib
import sys
import types
import unittest


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


if __name__ == "__main__":
    unittest.main()
