import importlib
import sys
import types
import unittest

from orientation import madctl_for_rotation, map_gesture_direction


def import_lcd_driver():
    machine = types.ModuleType("machine")
    for name in ("Pin", "I2C", "SPI", "PWM", "Timer", "ADC"):
        setattr(machine, name, object)
    framebuf = types.ModuleType("framebuf")
    framebuf.FrameBuffer = object
    framebuf.RGB565 = 1

    original_machine = sys.modules.get("machine")
    original_framebuf = sys.modules.get("framebuf")
    sys.modules["machine"] = machine
    sys.modules["framebuf"] = framebuf
    try:
        return importlib.import_module("lcd_1inch28")
    finally:
        if original_machine is None:
            del sys.modules["machine"]
        else:
            sys.modules["machine"] = original_machine
        if original_framebuf is None:
            del sys.modules["framebuf"]
        else:
            sys.modules["framebuf"] = original_framebuf


lcd_driver = import_lcd_driver()


class DisplayRotationTests(unittest.TestCase):
    def test_all_mount_angles_have_expected_controller_values(self):
        self.assertEqual(
            {0: 0x98, 90: 0xF8, 180: 0x58, 270: 0x38},
            {
                rotation: madctl_for_rotation(rotation)
                for rotation in (0, 90, 180, 270)
            },
        )

    def test_controller_rotation_safely_toggles_tearing_output(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                lcd = lcd_driver.LCD_1inch28.__new__(
                    lcd_driver.LCD_1inch28
                )
                lcd.commands = []
                lcd.data = []
                lcd.write_cmd = lcd.commands.append
                lcd.write_data = lcd.data.append

                lcd.set_rotation(rotation)

                self.assertEqual([0x34, 0x36, 0x35], lcd.commands)
                self.assertEqual([madctl_for_rotation(rotation)], lcd.data)
                self.assertEqual(rotation, lcd.rotation)

    def test_invalid_rotation_is_rejected_before_hardware_write(self):
        lcd = lcd_driver.LCD_1inch28.__new__(lcd_driver.LCD_1inch28)
        lcd.commands = []
        lcd.write_cmd = lcd.commands.append
        lcd.write_data = lambda _value: None

        with self.assertRaises(ValueError):
            lcd.set_rotation(45)

        self.assertEqual([], lcd.commands)

    def test_unknown_gestures_remain_unmapped_at_every_rotation(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                self.assertIsNone(map_gesture_direction(None, rotation))
                self.assertEqual(
                    "double",
                    map_gesture_direction("double", rotation),
                )


if __name__ == "__main__":
    unittest.main()
