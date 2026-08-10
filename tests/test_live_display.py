import math
import unittest

from font_renderer import measure_text, pixel_height
from live_display import (
    COUNTDOWN_TEXT_SIZE,
    TRACK_AMBER_RGB,
    TRACK_GREEN_RGB,
    TRACK_OVERRUN_PURPLE_RGB,
    TRACK_RED_RGB,
    TRACK_YELLOW_RGB,
    high_contrast_text_colour,
    interpolate_rgb,
    rest_live_frame,
    rgb_to_display565,
    run_live_display,
    scheduled_track_rgb,
    track_live_frame,
)
from timing import SessionTracker


class FakeClock:
    def __init__(self, now=0):
        self.now = now
        self.sleep_calls = []

    def time(self):
        return self.now

    def sleep(self, delay):
        self.sleep_calls.append(delay)
        self.now += delay


class FakeLCD:
    red = 1
    black = 2
    salmon = 3
    lilac = 4
    blue = 5
    white = 6


class LiveDisplayTests(unittest.TestCase):
    def test_countdown_uses_nearest_native_size_to_ten_percent_larger(self):
        previous_height = pixel_height(6)
        target_height = previous_height * 1.10
        selected_height = pixel_height(COUNTDOWN_TEXT_SIZE)

        self.assertEqual(7, COUNTDOWN_TEXT_SIZE)
        self.assertEqual(74, selected_height)
        self.assertLess(
            abs(selected_height - target_height),
            abs(previous_height - target_height),
        )

    def test_maximum_countdown_width_fits_the_live_screen_position(self):
        display_radius = 120
        y_position = 82
        text_height = pixel_height(COUNTDOWN_TEXT_SIZE)
        text_width = measure_text(
            "60:00",
            COUNTDOWN_TEXT_SIZE,
            tabular_digits=True,
        )

        for edge_y in (y_position, y_position + text_height - 1):
            distance_from_center = edge_y - display_radius
            visible_width = 2 * math.sqrt(
                (display_radius ** 2) - (distance_from_center ** 2)
            )
            self.assertLessEqual(text_width, visible_width)

    def test_maximum_g_readout_fits_round_screen_safe_area(self):
        display_radius = 120
        y_position = 40
        text_height = pixel_height(2)
        text_width = measure_text("MAX  99.99  g", 2, tabular_digits=True)

        for edge_y in (y_position, y_position + text_height - 1):
            distance_from_center = edge_y - display_radius
            visible_width = 2 * math.sqrt(
                (display_radius ** 2) - (distance_from_center ** 2)
            )
            self.assertLessEqual(text_width, visible_width)

        self.assertLess(y_position + text_height, 82)

    def test_simulated_session_redraws_at_most_once_per_visible_second(self):
        clock = FakeClock()
        lcd = FakeLCD()
        session = SessionTracker(duration_mins=0.1, clock=clock.time)
        session.start_session()
        frames = []
        input_checks = {"count": 0}

        def stop_check():
            input_checks["count"] += 1
            return False

        redraws = run_live_display(
            session,
            frame_builder=lambda now: rest_live_frame(session, now, lcd),
            draw_frame=frames.append,
            stop_check=stop_check,
            clock=clock,
        )

        self.assertEqual(int(session.duration_secs), redraws)
        self.assertEqual(redraws, len(frames))
        self.assertGreaterEqual(input_checks["count"], 100)
        self.assertTrue(all(delay == 0.05 for delay in clock.sleep_calls))
        self.assertFalse(session.live)

    def test_input_is_checked_between_unchanged_frames(self):
        clock = FakeClock()
        session = SessionTracker(duration_mins=1, clock=clock.time)
        session.start_session()
        frames = []
        input_checks = {"count": 0}

        def stop_check():
            input_checks["count"] += 1
            return input_checks["count"] == 4

        redraws = run_live_display(
            session,
            frame_builder=lambda now: ("same", "same", 1, 1, 1),
            draw_frame=frames.append,
            stop_check=stop_check,
            clock=clock,
        )

        self.assertEqual(1, redraws)
        self.assertEqual(4, input_checks["count"])
        self.assertAlmostEqual(0.15, clock.now)
        self.assertFalse(session.live)

    def test_warning_state_change_redraws_even_when_text_is_unchanged(self):
        clock = FakeClock()
        session = SessionTracker(duration_mins=1, clock=clock.time)
        session.start_session()
        frames = []

        def frame_builder(now):
            colour = "green" if now < 0.1 else "warning"
            return ("00:59", "00:00", 6, colour, "white")

        def stop_check():
            return clock.now >= 0.2

        redraws = run_live_display(
            session,
            frame_builder=frame_builder,
            draw_frame=frames.append,
            stop_check=stop_check,
            clock=clock,
        )

        self.assertEqual(2, redraws)
        self.assertEqual("green", frames[0][3])
        self.assertEqual("warning", frames[1][3])

    def test_sampling_runs_between_frames_without_forcing_redraws(self):
        clock = FakeClock()
        session = SessionTracker(duration_mins=1, clock=clock.time)
        session.start_session()
        samples = []

        def stop_check():
            return len(samples) == 4

        redraws = run_live_display(
            session,
            frame_builder=lambda now: ("same",),
            draw_frame=lambda frame: None,
            stop_check=stop_check,
            sample_update=samples.append,
            clock=clock,
        )

        self.assertEqual(1, redraws)
        self.assertEqual(4, len(samples))
        for actual, expected in zip(samples, (0, 0.05, 0.1, 0.15)):
            self.assertAlmostEqual(expected, actual)

    def test_rgb_conversion_matches_native_primary_colour_constants(self):
        self.assertEqual(0x00F8, rgb_to_display565((255, 0, 0)))
        self.assertEqual(0xE007, rgb_to_display565((0, 255, 0)))
        self.assertEqual(0x1F00, rgb_to_display565((0, 0, 255)))
        self.assertEqual(0xFFFF, rgb_to_display565((255, 255, 255)))

    def test_scheduled_gradient_has_exact_proportional_anchors(self):
        duration = 600

        self.assertEqual(TRACK_GREEN_RGB, scheduled_track_rgb(0, duration))
        self.assertEqual(TRACK_YELLOW_RGB, scheduled_track_rgb(200, duration))
        self.assertEqual(TRACK_AMBER_RGB, scheduled_track_rgb(400, duration))
        self.assertEqual(TRACK_RED_RGB, scheduled_track_rgb(600, duration))

    def test_scheduled_gradient_interpolates_between_anchors(self):
        duration = 600

        green_yellow = scheduled_track_rgb(100, duration)
        yellow_amber = scheduled_track_rgb(300, duration)
        amber_red = scheduled_track_rgb(500, duration)

        self.assertEqual((128, 255, 0), green_yellow)
        self.assertEqual((255, 223, 0), yellow_amber)
        self.assertEqual((255, 96, 0), amber_red)
        self.assertNotIn(
            green_yellow,
            (TRACK_GREEN_RGB, TRACK_YELLOW_RGB),
        )

    def test_scheduled_gradient_scales_with_total_duration(self):
        self.assertEqual(
            scheduled_track_rgb(30, 60),
            scheduled_track_rgb(300, 600),
        )

    def test_scheduled_gradient_clamps_progress_and_rejects_zero_duration(self):
        self.assertEqual(TRACK_GREEN_RGB, scheduled_track_rgb(-1, 60))
        self.assertEqual(TRACK_RED_RGB, scheduled_track_rgb(61, 60))
        with self.assertRaises(ValueError):
            scheduled_track_rgb(0, 0)

    def test_rgb_interpolation_clamps_to_endpoints(self):
        self.assertEqual((0, 0, 0), interpolate_rgb((0, 0, 0), (9, 9, 9), -1, 3))
        self.assertEqual((9, 9, 9), interpolate_rgb((0, 0, 0), (9, 9, 9), 4, 3))
        with self.assertRaises(ValueError):
            interpolate_rgb((0, 0, 0), (9, 9, 9), 1, 0)

    def test_text_colour_always_selects_the_higher_contrast_option(self):
        lcd = FakeLCD()

        self.assertEqual(
            lcd.white,
            high_contrast_text_colour((0, 0, 0), lcd.black, lcd.white),
        )
        for background in (
            TRACK_GREEN_RGB,
            TRACK_YELLOW_RGB,
            TRACK_AMBER_RGB,
            TRACK_RED_RGB,
            scheduled_track_rgb(100, 600),
            scheduled_track_rgb(300, 600),
            scheduled_track_rgb(500, 600),
        ):
            self.assertEqual(
                lcd.black,
                high_contrast_text_colour(background, lcd.black, lcd.white),
            )
        self.assertEqual(
            lcd.white,
            high_contrast_text_colour(
                TRACK_OVERRUN_PURPLE_RGB,
                lcd.black,
                lcd.white,
            ),
        )

    def test_track_frames_follow_gradient_and_use_deep_purple_for_overrun(self):
        lcd = FakeLCD()
        session = SessionTracker(duration_mins=10, clock=lambda: 100)
        session.start_session()

        start = track_live_frame(
            session,
            100,
            lcd,
            maximum_g="MAX  0.00  g",
        )
        one_third = track_live_frame(session, 300, lcd)
        two_thirds = track_live_frame(session, 500, lcd)
        near_expiry = track_live_frame(session, 699, lcd)
        overrun = track_live_frame(
            session,
            700,
            lcd,
            maximum_g="MAX  2.34  g",
        )

        self.assertTrue(
            all(
                frame[2] == COUNTDOWN_TEXT_SIZE
                for frame in (
                    start,
                    one_third,
                    two_thirds,
                    near_expiry,
                    overrun,
                )
            )
        )
        self.assertEqual(
            (rgb_to_display565(TRACK_GREEN_RGB), lcd.black),
            start[3:5],
        )
        self.assertEqual(
            (rgb_to_display565(TRACK_YELLOW_RGB), lcd.black),
            one_third[3:5],
        )
        self.assertEqual(
            (rgb_to_display565(TRACK_AMBER_RGB), lcd.black),
            two_thirds[3:5],
        )
        self.assertNotEqual(two_thirds[3], near_expiry[3])
        self.assertEqual("00:00", overrun[0])
        self.assertEqual(
            (rgb_to_display565(TRACK_OVERRUN_PURPLE_RGB), lcd.white),
            overrun[3:5],
        )
        self.assertEqual("MAX  0.00  g", start[5])
        self.assertEqual("MAX  2.34  g", overrun[5])

    def test_rest_frame_uses_larger_countdown_size(self):
        lcd = FakeLCD()
        session = SessionTracker(duration_mins=10, clock=lambda: 100)
        session.start_session()

        frame = rest_live_frame(session, 100, lcd)

        self.assertEqual(COUNTDOWN_TEXT_SIZE, frame[2])
        self.assertIsNone(frame[5])

    def test_loop_delay_must_be_bounded(self):
        session = SessionTracker(duration_mins=1, live=True)
        with self.assertRaises(ValueError):
            run_live_display(
                session,
                frame_builder=lambda now: None,
                draw_frame=lambda frame: None,
                stop_check=lambda: False,
                loop_delay_sec=0,
            )


if __name__ == "__main__":
    unittest.main()
