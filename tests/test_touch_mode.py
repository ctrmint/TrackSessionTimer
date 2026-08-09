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


if __name__ == "__main__":
    unittest.main()
