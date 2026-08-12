import unittest

from launch import accel_launch


class FakeAccelerometer:
    def __init__(self, samples):
        self._samples = iter(samples)
        self.read_count = 0

    def Read_XYZ(self):
        self.read_count += 1
        return next(self._samples)


class FakeClock:
    def __init__(self):
        self.milliseconds = 0

    def ticks_ms(self):
        return self.milliseconds

    def ticks_diff(self, current, previous):
        return current - previous

    def sleep_ms(self, milliseconds):
        self.milliseconds += milliseconds


def sample(x, y, z):
    return [x, y, z, 0, 0, 0]


class LaunchLoopTests(unittest.TestCase):
    def run_detector(self, samples, sensitivity=0.5, **overrides):
        sensor = FakeAccelerometer(samples)
        clock = FakeClock()
        options = {
            "clock": clock,
            "calibration_samples": 4,
            "sample_interval_ms": 20,
            "filter_alpha": 0.5,
            "trigger_samples": 3,
            "timeout_sec": 1,
        }
        options.update(overrides)
        result = accel_launch(sensor, sensitivity=sensitivity, **options)
        return result, sensor, clock

    def test_zero_sensitivity_bypasses_sensor_and_cancel_check(self):
        sensor = FakeAccelerometer([])

        self.assertTrue(
            accel_launch(sensor, sensitivity=0, cancel_check=lambda: True)
        )

        self.assertEqual(0, sensor.read_count)

    def test_stationary_gravity_and_noise_do_not_trigger(self):
        baseline = [sample(0.02, -0.06, -1.04)] * 4
        stationary = [
            sample(0.01, -0.05, -1.03),
            sample(0.03, -0.07, -1.05),
        ] * 20

        result, sensor, _ = self.run_detector(
            baseline + stationary,
            timeout_sec=0.3,
        )

        self.assertFalse(result)
        self.assertGreater(sensor.read_count, 4)

    def test_sustained_forward_axis_delta_triggers_after_debounce(self):
        baseline = [sample(0.2, -0.3, -0.9)] * 4
        launch = [sample(1.7, -0.3, -0.9)] * 4

        result, sensor, _ = self.run_detector(baseline + launch)

        self.assertTrue(result)
        self.assertEqual(7, sensor.read_count)

    def test_sustained_reverse_axis_delta_also_triggers(self):
        baseline = [sample(0, 0, 1)] * 4
        reverse_launch = [sample(-1.5, 0, 1)] * 4

        result, _, _ = self.run_detector(baseline + reverse_launch)

        self.assertTrue(result)

    def test_precalibrated_baseline_is_reused_without_extra_sensor_reads(self):
        launch = [sample(1.5, 0, 1)] * 3

        result, sensor, _ = self.run_detector(
            launch,
            baseline=(0, 0, 1),
            filter_alpha=1,
        )

        self.assertTrue(result)
        self.assertEqual(3, sensor.read_count)

    def test_launch_samples_can_feed_session_metrics_without_extra_reads(self):
        launch = [sample(0, 0, 1.5)] * 3
        observed = []

        result, sensor, _ = self.run_detector(
            launch,
            baseline=(0, 0, 0),
            filter_alpha=1,
            sample_update=observed.append,
        )

        self.assertTrue(result)
        self.assertEqual(3, sensor.read_count)
        self.assertEqual(3, len(observed))
        self.assertEqual((0.0, 0.0, 1.5), observed[-1])

    def test_isolated_vibration_spikes_do_not_trigger(self):
        baseline = [sample(0, 0, 1)] * 4
        vibration_pattern = [
            sample(2, 0, 1),
            sample(0, 0, 1),
            sample(0, 0, 1),
            sample(0, 0, 1),
            sample(-2, 0, 1),
            sample(0, 0, 1),
            sample(0, 0, 1),
            sample(0, 0, 1),
        ]

        result, _, _ = self.run_detector(
            baseline + (vibration_pattern * 4),
            timeout_sec=0.4,
            filter_alpha=0.35,
        )

        self.assertFalse(result)

    def test_cancel_check_exits_safely(self):
        sensor = FakeAccelerometer([sample(0, 0, 1)] * 20)
        clock = FakeClock()
        checks = {"count": 0}

        def cancel():
            checks["count"] += 1
            return checks["count"] == 7

        result = accel_launch(
            sensor,
            sensitivity=0.5,
            cancel_check=cancel,
            clock=clock,
            calibration_samples=4,
            sample_interval_ms=20,
        )

        self.assertFalse(result)
        self.assertEqual(6, sensor.read_count)

    def test_timeout_exits_safely(self):
        samples = [sample(0, 0, 1)] * 20

        result, _, clock = self.run_detector(samples, timeout_sec=0.2)

        self.assertFalse(result)
        self.assertEqual(200, clock.milliseconds)

    def test_invalid_filter_configuration_is_rejected(self):
        sensor = FakeAccelerometer([])
        invalid_options = (
            {"calibration_samples": 0},
            {"trigger_samples": 0},
            {"sample_interval_ms": -1},
            {"filter_alpha": 0},
            {"filter_alpha": 1.1},
        )
        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    accel_launch(sensor, sensitivity=0.5, **options)


if __name__ == "__main__":
    unittest.main()
