import math
import unittest

from battery import BatteryStatus
from font_renderer import measure_text, pixel_height
from ready_screen import (
    BATTERY_BODY_HEIGHT,
    BATTERY_INNER_WIDTH,
    READY_TITLE_Y,
    battery_icon_bounds,
    draw_battery_icon,
    draw_ready_screen,
    launch_status,
    ready_screen_lines,
)


class FakeLCD:
    black = 1
    white = 2

    def __init__(self):
        self.calls = []

    def rect(self, *args):
        self.calls.append(("rect",) + args)

    def fill_rect(self, *args):
        self.calls.append(("fill_rect",) + args)

    def line(self, *args):
        self.calls.append(("line",) + args)

    def show(self):
        self.calls.append(("show",))


class FakeTouch:
    def __init__(self):
        self.calls = []

    def ControlScreen(
        self,
        lcd,
        text_array=None,
        back_colour=None,
        refresh=True,
    ):
        self.calls.append((text_array, back_colour, refresh))
        if refresh:
            lcd.show()


class ReadyScreenTests(unittest.TestCase):
    def test_summary_contains_all_saved_settings_and_start_action(self):
        lines = ready_screen_lines(20, 15, 0.5, True)

        self.assertEqual(
            [
                "Ready",
                "Track 20m",
                "Rest 15m",
                "Launch 0.5g",
                "Swipe DOWN to start",
                "Hold 5s: modes",
            ],
            [line[0] for line in lines],
        )

    def test_hold_hint_reflects_configured_threshold(self):
        lines = ready_screen_lines(20, 15, 0, True, mode_hold_seconds=3.5)

        self.assertEqual("Hold 3.5s: modes", lines[-1][0])

    def test_launch_status_reflects_effective_mode(self):
        self.assertEqual("Launch OFF", launch_status(0, False))
        self.assertEqual("Launch 1g", launch_status(1, True))
        self.assertEqual("Launch unavailable", launch_status(1.25, False))

    def test_every_line_fits_inside_the_round_display(self):
        display_radius = 120
        widest_values = ready_screen_lines(60, 60, 1.75, False)

        for text, _, y_position, size, _ in widest_values:
            text_center_y = y_position + (pixel_height(size) / 2)
            distance_from_center = text_center_y - display_radius
            visible_width = 2 * math.sqrt(
                (display_radius ** 2) - (distance_from_center ** 2)
            )
            self.assertLessEqual(measure_text(text, size), visible_width)

    def test_battery_icon_fits_circle_and_clears_ready_heading(self):
        display_radius = 120
        x, y, width, height = battery_icon_bounds()

        self.assertLess(y + height, READY_TITLE_Y)
        for edge_y in (y, y + height - 1):
            distance_from_center = edge_y - display_radius
            visible_width = 2 * math.sqrt(
                (display_radius ** 2) - (distance_from_center ** 2)
            )
            self.assertLessEqual(width, visible_width)
        self.assertEqual((240 - width) // 2, x)

    def test_battery_fill_tracks_percentage(self):
        lcd = FakeLCD()

        draw_battery_icon(lcd, BatteryStatus(50, False))

        fills = [call for call in lcd.calls if call[0] == "fill_rect"]
        terminal, charge_fill = fills
        self.assertEqual(4, terminal[3])
        self.assertEqual(
            int(round(BATTERY_INNER_WIDTH * 0.5)),
            charge_fill[3],
        )
        self.assertEqual(BATTERY_BODY_HEIGHT - 4, charge_fill[4])
        self.assertFalse(any(call[0] == "line" for call in lcd.calls))

    def test_external_power_draws_lightning_bolt(self):
        lcd = FakeLCD()

        draw_battery_icon(lcd, BatteryStatus(100, True))

        bolt_lines = [call for call in lcd.calls if call[0] == "line"]
        self.assertEqual(6, len(bolt_lines))
        self.assertTrue(all(call[-1] == lcd.white for call in bolt_lines))

    def test_ready_screen_adds_icon_before_single_refresh(self):
        lcd = FakeLCD()
        touch = FakeTouch()

        draw_ready_screen(
            touch,
            lcd,
            track_minutes=20,
            rest_minutes=15,
            sensitivity=0.5,
            imu_available=True,
            battery_status=BatteryStatus(75, True),
        )

        lines, background, refresh = touch.calls[0]
        self.assertEqual("Ready", lines[0][0])
        self.assertEqual("green", background)
        self.assertFalse(refresh)
        self.assertEqual(("show",), lcd.calls[-1])
        self.assertEqual(1, sum(call == ("show",) for call in lcd.calls))


if __name__ == "__main__":
    unittest.main()
