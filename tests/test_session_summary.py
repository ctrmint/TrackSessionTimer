import unittest

from font_renderer import measure_text, pixel_height
from session_summary import (
    COMPLETION_DRIVER_STOP,
    REVIEW_PAGE_COUNT,
    build_session_summary,
    draw_summary_page,
    review_session_summary,
    summary_page_lines,
)


class FakeSession:
    start_time = 100
    duration_secs = 120


class FakeGPeak:
    metrics_available = True
    available = True
    total_peak_magnitude = 1.75
    max_acceleration_g = 0.81
    max_braking_g = 1.12
    max_left_g = 1.03
    max_right_g = 0.94


class FakeTouch:
    def __init__(self, gestures=None):
        self.calls = []
        self.gestures = iter(gestures or [])

    def ControlScreen(self, lcd, text_array=None, back_colour=None):
        self.calls.append((lcd, text_array, back_colour))

    def GetGesture(self, lcd, debounce_time=0.05):
        return next(self.gestures)


class SessionSummaryTests(unittest.TestCase):
    def test_summary_records_actual_time_overrun_reason_and_g_peaks(self):
        summary = build_session_summary(
            FakeSession(),
            stopped_at=225.9,
            g_peak=FakeGPeak(),
        )

        self.assertEqual(125, summary.actual_seconds)
        self.assertEqual(5, summary.overrun_seconds)
        self.assertEqual(COMPLETION_DRIVER_STOP, summary.completion_reason)
        self.assertEqual(1.75, summary.maximum_g)
        self.assertEqual(0.81, summary.acceleration_g)
        self.assertEqual(1.12, summary.braking_g)
        self.assertEqual(1.03, summary.left_g)
        self.assertEqual(0.94, summary.right_g)

    def test_on_time_summary_and_missing_imu_are_explicit(self):
        summary = build_session_summary(
            FakeSession(),
            stopped_at=160,
            g_peak=None,
        )
        overrun_labels = [line[0] for line in summary_page_lines(summary, 1)]
        maximum_labels = [line[0] for line in summary_page_lines(summary, 2)]

        self.assertEqual(60, summary.actual_seconds)
        self.assertEqual(0, summary.overrun_seconds)
        self.assertFalse(summary.has_g_metrics)
        self.assertIn("ON TIME", overrun_labels)
        self.assertIn("--", maximum_labels)
        self.assertIn("IMU UNAVAILABLE", maximum_labels)

    def test_late_imu_failure_marks_retained_values_as_partial(self):
        peak = FakeGPeak()
        peak.available = False

        summary = build_session_summary(FakeSession(), 225, peak)
        labels = [line[0] for line in summary_page_lines(summary, 2)]

        self.assertTrue(summary.has_g_metrics)
        self.assertFalse(summary.imu_complete)
        self.assertIn("IMU DATA PARTIAL", labels)

    def test_each_data_element_has_its_own_review_page(self):
        summary = build_session_summary(FakeSession(), 225, FakeGPeak())
        titles = []
        values = []

        for page_index in range(REVIEW_PAGE_COUNT):
            lines = summary_page_lines(summary, page_index)
            titles.append(lines[1][0])
            values.append(lines[2][0])

        self.assertEqual(
            [
                "SESSION TIME",
                "OVERRUN",
                "MAXIMUM G",
                "ACCELERATION",
                "BRAKING",
                "LEFT G",
                "RIGHT G",
                "SESSION END",
            ],
            titles,
        )
        self.assertEqual(
            [
                "02:05",
                "00:05",
                "1.75 g",
                "0.81 g",
                "1.12 g",
                "1.03 g",
                "0.94 g",
                "DRIVER STOP",
            ],
            values,
        )

    def test_every_review_page_fits_the_round_display(self):
        summaries = (
            build_session_summary(FakeSession(), 225, FakeGPeak()),
            build_session_summary(FakeSession(), 160, None),
        )
        for summary in summaries:
            for page_index in range(REVIEW_PAGE_COUNT):
                for text, _x, y_position, size, _colour in summary_page_lines(
                    summary,
                    page_index,
                ):
                    text_width = measure_text(text, size)
                    text_height = pixel_height(size)
                    for edge_y in (y_position, y_position + text_height - 1):
                        distance_from_center = edge_y - 120
                        visible_width = 2 * (
                            (120 ** 2) - (distance_from_center ** 2)
                        ) ** 0.5
                        self.assertLessEqual(text_width, visible_width, text)

    def test_draw_uses_one_high_visibility_control_screen(self):
        touch = FakeTouch()
        lcd = object()
        summary = build_session_summary(FakeSession(), 225, FakeGPeak())

        draw_summary_page(touch, lcd, summary, 3)

        self.assertEqual(1, len(touch.calls))
        self.assertIs(lcd, touch.calls[0][0])
        self.assertEqual("black", touch.calls[0][2])
        self.assertEqual("ACCELERATION", touch.calls[0][1][1][0])
        self.assertEqual(6, touch.calls[0][1][2][3])

    def test_left_advances_right_returns_and_final_left_exits(self):
        gestures = (
            "left",
            "left",
            "right",
            "left",
            "left",
            "left",
            "left",
            "left",
            "left",
            "left",
        )
        touch = FakeTouch(gestures)
        summary = build_session_summary(FakeSession(), 225, FakeGPeak())

        review_session_summary(touch, object(), summary)

        self.assertEqual(
            [
                "REVIEW 1/8",
                "REVIEW 2/8",
                "REVIEW 3/8",
                "REVIEW 2/8",
                "REVIEW 3/8",
                "REVIEW 4/8",
                "REVIEW 5/8",
                "REVIEW 6/8",
                "REVIEW 7/8",
                "REVIEW 8/8",
            ],
            [call[1][0][0] for call in touch.calls],
        )

    def test_right_on_first_page_cannot_skip_review(self):
        touch = FakeTouch(("right",) + (("left",) * REVIEW_PAGE_COUNT))
        summary = build_session_summary(FakeSession(), 225, FakeGPeak())

        review_session_summary(touch, object(), summary)

        self.assertEqual(REVIEW_PAGE_COUNT, len(touch.calls))
        self.assertEqual("REVIEW 1/8", touch.calls[0][1][0][0])
        self.assertEqual("REVIEW 8/8", touch.calls[-1][1][0][0])

    def test_page_index_must_be_in_range(self):
        summary = build_session_summary(FakeSession(), 225, FakeGPeak())
        for page_index in (-1, REVIEW_PAGE_COUNT):
            with self.subTest(page_index=page_index):
                with self.assertRaises(ValueError):
                    summary_page_lines(summary, page_index)


if __name__ == "__main__":
    unittest.main()
