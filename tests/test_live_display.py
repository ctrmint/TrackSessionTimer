import math
import unittest

from font_renderer import measure_text, pixel_height
from live_display import (
    COUNTDOWN_TEXT_SIZE,
    rest_live_frame,
    run_live_display,
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
        text_width = measure_text("60:00", COUNTDOWN_TEXT_SIZE)

        for edge_y in (y_position, y_position + text_height - 1):
            distance_from_center = edge_y - display_radius
            visible_width = 2 * math.sqrt(
                (display_radius ** 2) - (distance_from_center ** 2)
            )
            self.assertLessEqual(text_width, visible_width)

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

    def test_track_frames_include_warning_and_overrun_state(self):
        lcd = FakeLCD()
        session = SessionTracker(duration_mins=10, clock=lambda: 100)
        session.start_session()

        running = track_live_frame(session, 609, lcd)
        last_15 = track_live_frame(session, 610, lcd)
        last_5 = track_live_frame(session, 670, lcd)
        overrun = track_live_frame(session, 700, lcd)

        self.assertTrue(
            all(
                frame[2] == COUNTDOWN_TEXT_SIZE
                for frame in (running, last_15, last_5, overrun)
            )
        )
        self.assertEqual((None, None), running[3:])
        self.assertEqual((lcd.salmon, lcd.black), last_15[3:])
        self.assertEqual((lcd.lilac, None), last_5[3:])
        self.assertEqual("00:00", overrun[0])
        self.assertEqual((lcd.red, lcd.black), overrun[3:])

    def test_rest_frame_uses_larger_countdown_size(self):
        lcd = FakeLCD()
        session = SessionTracker(duration_mins=10, clock=lambda: 100)
        session.start_session()

        frame = rest_live_frame(session, 100, lcd)

        self.assertEqual(COUNTDOWN_TEXT_SIZE, frame[2])

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
