import math
import unittest

from g_meter import (
    DISPLAY_CENTER_X,
    DISPLAY_CENTER_Y,
    GMeterState,
    PEAK_ARC_DOT_RADIUS,
    PLOT_RADIUS,
    calibrate_baseline,
    draw_g_meter_frame,
    remaining_frame_delay_ms,
    vector_point,
)
from hardware import PeripheralIOError


class FakeClock:
    def __init__(self):
        self.sleeps = []
        self.now = 0

    def sleep_ms(self, milliseconds):
        self.sleeps.append(milliseconds)

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, current, previous):
        return current - previous


class FakeSensor:
    def __init__(self, samples=None, error=None):
        self.samples = list(samples or [])
        self.error = error
        self.index = 0

    def Read_XYZ(self):
        if self.error is not None:
            raise self.error
        sample = self.samples[min(self.index, len(self.samples) - 1)]
        self.index += 1
        return sample


class FakeLCD:
    black = 0
    white = 1
    blue = 2
    palegreen = 3
    red = 4

    def __init__(self):
        self.calls = []

    def fill(self, *args):
        self.calls.append(("fill",) + args)

    def write_centered(self, *args):
        self.calls.append(("write_centered",) + args)

    def write_text(self, *args):
        self.calls.append(("write_text",) + args)

    def ellipse(self, *args):
        self.calls.append(("ellipse",) + args)

    def hline(self, *args):
        self.calls.append(("hline",) + args)

    def vline(self, *args):
        self.calls.append(("vline",) + args)

    def line(self, *args):
        self.calls.append(("line",) + args)

    def pixel(self, *args):
        self.calls.append(("pixel",) + args)

    def show(self):
        self.calls.append(("show",))


class GMeterTests(unittest.TestCase):
    def test_stationary_calibration_averages_all_axes(self):
        clock = FakeClock()
        sensor = FakeSensor(
            [
                (1.0, 2.0, 3.0, 0, 0, 0),
                (3.0, 4.0, 5.0, 0, 0, 0),
            ]
        )

        baseline = calibrate_baseline(
            sensor,
            samples=2,
            interval_ms=10,
            clock=clock,
        )

        self.assertEqual((2.0, 3.0, 4.0), baseline)
        self.assertEqual([10, 10], clock.sleeps)

    def test_filter_removes_baseline_and_preserves_peak(self):
        state = GMeterState(
            baseline=(1.0, 2.0, 3.0),
            filter_alpha=1,
            trail_length=2,
        )

        state.update((3.0, 1.0, 3.0))
        self.assertEqual((2.0, -1.0), state.current)
        expected_peak = math.sqrt(5)
        self.assertAlmostEqual(expected_peak, state.peak_magnitude)

        state.update((1.5, 2.0, 3.0))
        state.update((1.25, 2.0, 3.0))
        self.assertAlmostEqual(expected_peak, state.peak_magnitude)
        self.assertEqual((2.0, -1.0), state.peak)
        self.assertEqual(2, len(state.trail))

    def test_default_filter_responds_immediately_without_excessive_lag(self):
        state = GMeterState()

        state.update((1.0, 0.0, 0.0))

        self.assertGreaterEqual(state.current[0], 0.5)

    def test_frame_delay_accounts_for_render_time(self):
        clock = FakeClock()
        frame_started = clock.ticks_ms()

        clock.now = 20
        self.assertEqual(40, remaining_frame_delay_ms(clock, frame_started, 60))
        clock.now = 65
        self.assertEqual(0, remaining_frame_delay_ms(clock, frame_started, 60))

    def test_peak_and_trail_can_be_reset(self):
        state = GMeterState(filter_alpha=1)
        state.update((2.0, 0.0, 0.0))

        state.reset_peak()

        self.assertEqual(0, state.peak_magnitude)
        self.assertEqual((0.0, 0.0), state.peak)
        self.assertEqual([], state.trail)

    def test_vectors_are_clamped_to_graphical_plot_radius(self):
        edge = vector_point((4.0, 0.0))
        beyond = vector_point((40.0, 0.0))
        diagonal = vector_point((40.0, 40.0))

        self.assertEqual((DISPLAY_CENTER_X + PLOT_RADIUS, DISPLAY_CENTER_Y), edge)
        self.assertEqual(edge, beyond)
        distance = math.sqrt(
            ((diagonal[0] - DISPLAY_CENTER_X) ** 2)
            + ((diagonal[1] - DISPLAY_CENTER_Y) ** 2)
        )
        self.assertLessEqual(distance, PLOT_RADIUS + 1)

    def test_graphic_contains_live_trail_peak_marker_and_peak_arc(self):
        state = GMeterState(filter_alpha=1)
        state.update((1.0, 0.5, 0.0))
        state.update((2.0, -1.0, 0.0))
        lcd = FakeLCD()

        draw_g_meter_frame(lcd, state)

        ellipses = [call for call in lcd.calls if call[0] == "ellipse"]
        peak_arc_dots = [
            call
            for call in lcd.calls
            if call[0] == "ellipse"
            and call[3:5] == (PEAK_ARC_DOT_RADIUS, PEAK_ARC_DOT_RADIUS)
            and call[-2:] == (lcd.red, True)
        ]
        labels = [
            call[1]
            for call in lcd.calls
            if call[0] in ("write_centered", "write_text")
        ]
        self.assertGreaterEqual(len(ellipses), 7)
        self.assertTrue(
            any(len(call) == 6 and call[-1] == lcd.red for call in ellipses)
        )
        self.assertTrue(
            any(len(call) == 7 and call[-1] is True for call in ellipses)
        )
        self.assertTrue(peak_arc_dots)
        self.assertIn("LIVE", labels)
        self.assertIn("MAX", labels)
        self.assertFalse(any("0.0g" in label for label in labels))
        self.assertEqual(("show",), lcd.calls[-1])

    def test_every_graphical_primitive_stays_inside_framebuffer(self):
        state = GMeterState(filter_alpha=1)
        state.update((100.0, -100.0, 0.0))
        lcd = FakeLCD()
        draw_g_meter_frame(lcd, state)

        for call in lcd.calls:
            if call[0] == "pixel":
                self.assertTrue(0 <= call[1] < 240)
                self.assertTrue(0 <= call[2] < 240)
            elif call[0] == "ellipse":
                _name, x, y, x_radius, y_radius, *_rest = call
                self.assertGreaterEqual(x - x_radius, 0)
                self.assertLess(x + x_radius, 240)
                self.assertGreaterEqual(y - y_radius, 0)
                self.assertLess(y + y_radius, 240)
            elif call[0] == "line":
                _name, x1, y1, x2, y2, _colour = call
                self.assertTrue(0 <= x1 < 240 and 0 <= x2 < 240)
                self.assertTrue(0 <= y1 < 240 and 0 <= y2 < 240)

    def test_sensor_failure_propagates_for_safe_mode_fallback(self):
        failure = PeripheralIOError("QMI8658", "sample read", "disconnected")
        sensor = FakeSensor(error=failure)

        with self.assertRaises(PeripheralIOError):
            calibrate_baseline(sensor, samples=1, clock=FakeClock())


if __name__ == "__main__":
    unittest.main()
