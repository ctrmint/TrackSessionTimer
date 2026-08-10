import math
import unittest

from font_renderer import measure_text, pixel_height
from ready_screen import launch_status, ready_screen_lines


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
            ],
            [line[0] for line in lines],
        )

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


if __name__ == "__main__":
    unittest.main()
