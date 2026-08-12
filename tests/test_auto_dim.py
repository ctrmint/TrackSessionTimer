import unittest

from auto_dim import DEFAULT_AUTO_DIM_PERCENT, ReadyAutoDim, brightness_duty
from hardware import PeripheralIOError


class FakeClock:
    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, current, previous):
        return current - previous


class FakeLCD:
    def __init__(self):
        self.duties = []

    def set_bl_pwm(self, duty):
        self.duties.append(duty)


class FakeSensor:
    def __init__(self, samples=None, error=None):
        self.samples = iter(samples or [])
        self.error = error
        self.read_count = 0

    def Read_XYZ(self):
        self.read_count += 1
        if self.error is not None:
            raise self.error
        return next(self.samples)


class AutoDimTests(unittest.TestCase):
    def make_monitor(self, enabled=True, normal_percent=100, sensor=None):
        clock = FakeClock()
        lcd = FakeLCD()
        monitor = ReadyAutoDim(
            lcd,
            sensor=sensor,
            enabled=enabled,
            normal_percent=normal_percent,
            clock=clock,
            filter_alpha=1,
        )
        return monitor, lcd, clock

    def test_enabled_monitor_dims_after_ten_continuous_stationary_seconds(self):
        monitor, lcd, clock = self.make_monitor(sensor=object())
        monitor.enter_ready()

        monitor.update(sample=(0, 0, 1, 0, 0, 0), now_ms=0, force=True)
        clock.now = 9_999
        monitor.update(
            sample=(0.01, -0.01, 1, 0.2, 0, 0),
            now_ms=clock.now,
            force=True,
        )
        self.assertFalse(monitor.dimmed)

        clock.now = 10_000
        changed = monitor.update(
            sample=(0, 0, 1, 0, 0, 0),
            now_ms=clock.now,
            force=True,
        )

        self.assertTrue(changed)
        self.assertTrue(monitor.dimmed)
        self.assertEqual(
            brightness_duty(DEFAULT_AUTO_DIM_PERCENT),
            lcd.duties[-1],
        )

    def test_configured_dim_percentage_controls_backlight_duty(self):
        clock = FakeClock()
        lcd = FakeLCD()
        monitor = ReadyAutoDim(
            lcd,
            sensor=object(),
            enabled=True,
            normal_percent=100,
            dim_percent=40,
            clock=clock,
            filter_alpha=1,
        )
        monitor.enter_ready()
        monitor.update(sample=(0, 0, 1), now_ms=0, force=True)

        monitor.update(sample=(0, 0, 1), now_ms=10_000, force=True)

        self.assertTrue(monitor.dimmed)
        self.assertEqual(brightness_duty(40), lcd.duties[-1])

    def test_motion_wakes_immediately_and_restarts_inactivity_interval(self):
        monitor, lcd, clock = self.make_monitor(sensor=object())
        monitor.enter_ready()
        monitor.update(sample=(0, 0, 1), now_ms=0, force=True)
        monitor.update(sample=(0, 0, 1), now_ms=10_000, force=True)
        self.assertTrue(monitor.dimmed)

        changed = monitor.update(sample=(0.5, 0, 1), now_ms=10_100, force=True)

        self.assertTrue(changed)
        self.assertFalse(monitor.dimmed)
        self.assertEqual(brightness_duty(100), lcd.duties[-1])
        monitor.update(sample=(0.5, 0, 1), now_ms=20_099, force=True)
        self.assertFalse(monitor.dimmed)
        monitor.update(sample=(0.5, 0, 1), now_ms=20_100, force=True)
        self.assertTrue(monitor.dimmed)

    def test_inactivity_starts_when_a_large_orientation_change_stops(self):
        monitor, _lcd, _clock = self.make_monitor(sensor=object())
        monitor.filter_alpha = 0.1
        monitor.enter_ready()
        monitor.update(sample=(0, 0, 1), now_ms=0, force=True)

        monitor.update(sample=(1, 0, 0), now_ms=5_000, force=True)
        monitor.update(sample=(1, 0, 0), now_ms=14_999, force=True)
        self.assertFalse(monitor.dimmed)
        monitor.update(sample=(1, 0, 0), now_ms=15_000, force=True)

        self.assertTrue(monitor.dimmed)

    def test_gyroscope_motion_prevents_dimming_without_axis_change(self):
        monitor, _lcd, _clock = self.make_monitor(sensor=object())
        monitor.enter_ready()
        monitor.update(sample=(0, 0, 1, 0, 0, 0), now_ms=0, force=True)

        monitor.update(sample=(0, 0, 1, 0, 4, 0), now_ms=9_000, force=True)
        monitor.update(sample=(0, 0, 1, 0, 0, 0), now_ms=18_999, force=True)

        self.assertFalse(monitor.dimmed)

    def test_stationary_gyroscope_bias_does_not_prevent_dimming(self):
        monitor, _lcd, _clock = self.make_monitor(sensor=object())
        biased_stationary = (0, 0, 1, 3.2, 4.6, 0.25)
        monitor.enter_ready()
        monitor.update(sample=biased_stationary, now_ms=0, force=True)

        monitor.update(sample=biased_stationary, now_ms=10_000, force=True)

        self.assertTrue(monitor.dimmed)

    def test_stationary_noise_does_not_reset_inactivity(self):
        monitor, _lcd, _clock = self.make_monitor(sensor=object())
        monitor.enter_ready()
        monitor.update(sample=(0, 0, 1), now_ms=0, force=True)
        for now_ms, sample in (
            (2_000, (0.01, -0.01, 1.01)),
            (4_000, (-0.01, 0.01, 0.99)),
            (6_000, (0.01, 0, 1.01)),
            (8_000, (0, -0.01, 0.99)),
            (10_000, (0, 0, 1)),
        ):
            monitor.update(sample=sample, now_ms=now_ms, force=True)

        self.assertTrue(monitor.dimmed)

    def test_disabled_or_unavailable_monitor_never_dims(self):
        disabled, disabled_lcd, _ = self.make_monitor(enabled=False, sensor=object())
        disabled.enter_ready()
        disabled.update(sample=(0, 0, 1), now_ms=20_000, force=True)

        unavailable, unavailable_lcd, _ = self.make_monitor(sensor=None)
        unavailable.enter_ready()
        unavailable.update(sample=(0, 0, 1), now_ms=20_000, force=True)

        self.assertFalse(disabled.dimmed)
        self.assertFalse(unavailable.dimmed)
        self.assertEqual([brightness_duty(100)], disabled_lcd.duties)
        self.assertEqual([brightness_duty(100)], unavailable_lcd.duties)

    def test_sampling_is_bounded_to_ten_hz(self):
        sensor = FakeSensor([(0, 0, 1)] * 2)
        monitor, _lcd, clock = self.make_monitor(sensor=sensor)
        monitor.enter_ready()

        monitor.update()
        clock.now = 99
        monitor.update()
        clock.now = 100
        monitor.update()

        self.assertEqual(2, sensor.read_count)

    def test_leaving_ready_always_restores_saved_brightness(self):
        monitor, lcd, _clock = self.make_monitor(normal_percent=75, sensor=object())
        monitor.enter_ready()
        monitor.update(sample=(0, 0, 1), now_ms=0, force=True)
        monitor.update(sample=(0, 0, 1), now_ms=10_000, force=True)
        self.assertTrue(monitor.dimmed)

        monitor.leave_ready()

        self.assertFalse(monitor.active)
        self.assertFalse(monitor.dimmed)
        self.assertEqual(brightness_duty(75), lcd.duties[-1])

    def test_sensor_failure_can_degrade_to_normal_brightness(self):
        failure = PeripheralIOError("QMI8658", "sample read", "disconnected")
        sensor = FakeSensor(error=failure)
        monitor, lcd, _clock = self.make_monitor(normal_percent=75, sensor=sensor)
        monitor.enter_ready()

        with self.assertRaises(PeripheralIOError):
            monitor.update(force=True)
        monitor.disable_sensor()

        self.assertFalse(monitor.available)
        self.assertFalse(monitor.dimmed)
        self.assertEqual(brightness_duty(75), lcd.duties[-1])

    def test_invalid_timing_and_filter_configuration_is_rejected(self):
        invalid_options = (
            {"inactivity_timeout_sec": 0},
            {"sample_interval_ms": 0},
            {"acceleration_threshold_g": 0},
            {"gyro_threshold_dps": 0},
            {"filter_alpha": 0},
            {"filter_alpha": 1.1},
            {"dim_percent": 0},
            {"dim_percent": 101},
            {"dim_percent": 25.0},
            {"dim_percent": True},
        )
        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    ReadyAutoDim(FakeLCD(), **options)


if __name__ == "__main__":
    unittest.main()
