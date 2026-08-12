import math
import unittest

from g_force import (
    MAX_G_UNAVAILABLE,
    PlanarGState,
    SessionGPeak,
    screen_horizontal_g,
)


class FakeSensor:
    def __init__(self, samples):
        self.samples = iter(samples)
        self.read_count = 0

    def Read_XYZ(self):
        self.read_count += 1
        return next(self.samples)


class GForceTests(unittest.TestCase):
    def test_planar_filter_removes_baseline_and_retains_largest_peak(self):
        state = PlanarGState(
            baseline=(1.0, 2.0, 3.0),
            filter_alpha=1,
        )

        state.update((4.0, -2.0, 99.0))
        expected_peak = 5.0
        self.assertAlmostEqual(expected_peak, state.peak_magnitude)
        self.assertEqual((3.0, -4.0), state.peak)

        state.update((2.0, 2.0, -99.0))
        self.assertAlmostEqual(expected_peak, state.peak_magnitude)
        self.assertEqual((3.0, -4.0), state.peak)

    def test_session_peak_samples_live_sensor_and_resets_per_instance(self):
        sensor = FakeSensor([(1.0, 0.0, 0.0), (2.0, 0.0, 0.0)])
        peak = SessionGPeak(sensor)

        peak.sample()
        first_peak = peak.peak_magnitude
        peak.sample()

        self.assertEqual(2, sensor.read_count)
        self.assertGreater(peak.peak_magnitude, first_peak)
        self.assertEqual(0.0, SessionGPeak(sensor).peak_magnitude)

    def test_visible_peak_is_latched_to_timer_second(self):
        sensor = FakeSensor([(1.0, 0.0, 0.0), (2.0, 0.0, 0.0)])
        peak = SessionGPeak(sensor)

        peak.sample()
        first_label = peak.display_label(0.1)
        peak.sample()

        self.assertEqual("MAX  0.60  g", first_label)
        self.assertEqual(first_label, peak.display_label(0.9))
        self.assertEqual("MAX  1.44  g", peak.display_label(1.0))

    def test_unavailable_or_failed_session_uses_placeholder(self):
        peak = SessionGPeak()
        self.assertFalse(peak.available)
        self.assertEqual(MAX_G_UNAVAILABLE, peak.display_label(0))

        active = SessionGPeak(FakeSensor([(1.0, 1.0, 0.0)]))
        active.sample()
        active.disable()

        self.assertFalse(active.available)
        self.assertEqual(MAX_G_UNAVAILABLE, active.display_label(1))

    def test_peak_magnitude_is_planar_not_total_gravity(self):
        state = PlanarGState(filter_alpha=1)

        state.update((0.0, 0.0, 1.0))

        self.assertEqual(0.0, state.peak_magnitude)
        self.assertEqual(1.0, state.total_peak_magnitude)
        self.assertFalse(math.isnan(state.peak_magnitude))

    def test_session_retains_total_and_directional_peaks(self):
        sensor = FakeSensor(
            [
                (2.0, 0.0, 3.0),
                (-4.0, 0.0, -5.0),
            ]
        )
        peak = SessionGPeak(sensor)
        peak.state.filter_alpha = 1

        peak.sample(rotation=0)
        peak.sample(rotation=0)

        self.assertAlmostEqual(math.sqrt(41), peak.total_peak_magnitude)
        self.assertEqual(3.0, peak.max_acceleration_g)
        self.assertEqual(5.0, peak.max_braking_g)
        self.assertEqual(4.0, peak.max_left_g)
        self.assertEqual(2.0, peak.max_right_g)
        self.assertTrue(peak.metrics_available)

    def test_directional_peaks_survive_late_sensor_failure(self):
        peak = SessionGPeak(FakeSensor([(1.0, 0.0, 2.0)]))
        peak.state.filter_alpha = 1
        peak.sample()

        peak.disable()

        self.assertFalse(peak.available)
        self.assertTrue(peak.metrics_available)
        self.assertEqual(2.0, peak.max_acceleration_g)
        self.assertAlmostEqual(math.sqrt(5), peak.total_peak_magnitude)

    def test_screen_horizontal_axis_follows_mount_rotation(self):
        axes = (2.0, 3.0, 0.0)

        self.assertEqual(2.0, screen_horizontal_g(axes, 0))
        self.assertEqual(-3.0, screen_horizontal_g(axes, 90))
        self.assertEqual(-2.0, screen_horizontal_g(axes, 180))
        self.assertEqual(3.0, screen_horizontal_g(axes, 270))


if __name__ == "__main__":
    unittest.main()
