import math
import unittest
from types import SimpleNamespace

from font_renderer import measure_text, pixel_height
from hardware_splash import (
    DeviceDetails,
    HARDWARE_SPLASH_BACKGROUND,
    HARDWARE_SPLASH_TEXT_COLOUR,
    UNKNOWN_VALUE,
    collect_device_details,
    hardware_splash_lines,
    run_startup_screens,
)


class FakeClock:
    def __init__(self, events):
        self.events = events

    def sleep(self, seconds):
        self.events.append(("sleep", seconds))


class FakeTouch:
    def __init__(self, events):
        self.events = events

    def BootScreen(self, lcd, version_number):
        self.events.append(("primary", lcd, version_number))

    def ControlScreen(self, lcd, text_array, back_colour):
        self.events.append(("hardware", lcd, text_array, back_colour))


class HardwareSplashTests(unittest.TestCase):
    def setUp(self):
        self.details = DeviceDetails(
            firmware="3.5",
            cpu="RP2040",
            os_name="MicroPython",
            os_version="1.21.0",
            platform="rp2",
        )

    def test_runtime_details_are_normalized_for_supported_hardware(self):
        uname_info = SimpleNamespace(
            machine="Raspberry Pi Pico with RP2040",
            release="1.21.0",
            sysname="rp2",
        )
        implementation = SimpleNamespace(name="micropython")

        details = collect_device_details(
            "3.5",
            uname_info=uname_info,
            implementation=implementation,
        )

        self.assertEqual("Waveshare", details.vendor)
        self.assertEqual("Touch LCD 1.28", details.model)
        self.assertEqual("RP2040", details.cpu)
        self.assertEqual("3.5", details.firmware)
        self.assertEqual("MicroPython", details.os_name)
        self.assertEqual("1.21.0", details.os_version)
        self.assertEqual("rp2", details.platform)

    def test_missing_runtime_details_use_safe_fallbacks(self):
        details = collect_device_details(
            "3.5",
            uname_info=object(),
            implementation=object(),
        )

        self.assertEqual(UNKNOWN_VALUE, details.cpu)
        self.assertEqual(UNKNOWN_VALUE, details.os_name)
        self.assertEqual(UNKNOWN_VALUE, details.os_version)
        self.assertEqual(UNKNOWN_VALUE, details.platform)

    def test_hardware_screen_contains_expected_details(self):
        lines = hardware_splash_lines(self.details)
        text = [line[0] for line in lines]

        self.assertEqual(
            [
                "Hardware",
                "Board Waveshare",
                "Model Touch LCD 1.28",
                "Type RP2040",
                "Firmware v3.5",
                "OS MicroPython 1.21.0",
                "Platform rp2",
            ],
            text,
        )
        self.assertEqual("black", HARDWARE_SPLASH_BACKGROUND)
        self.assertEqual("white", HARDWARE_SPLASH_TEXT_COLOUR)
        self.assertTrue(
            all(line[4] == HARDWARE_SPLASH_TEXT_COLOUR for line in lines)
        )

    def test_every_line_fits_inside_round_display(self):
        display_size = 240
        radius = display_size / 2

        for text, x, y, size, _colour in hardware_splash_lines(self.details):
            with self.subTest(text=text):
                height = pixel_height(size)
                centre_y = y + (height / 2)
                vertical_offset = abs(centre_y - radius)
                available_width = 2 * math.sqrt(
                    (radius * radius) - (vertical_offset * vertical_offset)
                )
                self.assertIsNone(x)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(y + height, display_size)
                self.assertLessEqual(measure_text(text, size), available_width)

    def test_startup_screens_run_in_order_for_configured_durations(self):
        events = []
        touch = FakeTouch(events)
        clock = FakeClock(events)
        lcd = object()

        returned = run_startup_screens(
            touch,
            lcd,
            firmware_version="3.5",
            startup_duration_sec=2.25,
            hardware_duration_sec=1.75,
            clock=clock,
            details=self.details,
        )

        self.assertIs(self.details, returned)
        self.assertEqual(("primary", lcd, "3.5"), events[0])
        self.assertEqual(("sleep", 2.25), events[1])
        self.assertEqual("hardware", events[2][0])
        self.assertIs(lcd, events[2][1])
        self.assertEqual(hardware_splash_lines(self.details), events[2][2])
        self.assertEqual(HARDWARE_SPLASH_BACKGROUND, events[2][3])
        self.assertEqual(("sleep", 1.75), events[3])


if __name__ == "__main__":
    unittest.main()
