"""Ready-screen-only motion inactivity dimming."""

import math
import time


DEFAULT_AUTO_DIM_PERCENT = 25
INACTIVITY_TIMEOUT_SEC = 10
SAMPLE_INTERVAL_MS = 100
ACCELERATION_MOTION_THRESHOLD_G = 0.06
GYRO_MOTION_THRESHOLD_DPS = 3.0
FILTER_ALPHA = 0.10


def _ticks_ms(clock):
    ticks_ms = getattr(clock, "ticks_ms", None)
    if ticks_ms is not None:
        return ticks_ms()
    monotonic = getattr(clock, "monotonic", None)
    if monotonic is not None:
        return int(monotonic() * 1000)
    return int(clock.time() * 1000)


def _ticks_diff(clock, current, previous):
    ticks_diff = getattr(clock, "ticks_diff", None)
    if ticks_diff is not None:
        return ticks_diff(current, previous)
    return current - previous


def _axes(sample):
    if len(sample) < 3:
        raise ValueError("Motion sample must contain x, y, and z acceleration")
    acceleration = tuple(float(value) for value in sample[:3])
    gyroscope = (
        tuple(float(value) for value in sample[3:6])
        if len(sample) >= 6
        else (0.0, 0.0, 0.0)
    )
    return acceleration, gyroscope


def brightness_duty(percent):
    """Convert a bounded percentage to the display PWM duty range."""
    value = max(0, min(100, int(percent)))
    return int(round(65535 * value / 100))


class ReadyAutoDim:
    """Track motion and brightness while, and only while, Ready is active."""

    def __init__(
        self,
        lcd,
        sensor=None,
        enabled=False,
        normal_percent=100,
        dim_percent=DEFAULT_AUTO_DIM_PERCENT,
        clock=time,
        inactivity_timeout_sec=INACTIVITY_TIMEOUT_SEC,
        sample_interval_ms=SAMPLE_INTERVAL_MS,
        acceleration_threshold_g=ACCELERATION_MOTION_THRESHOLD_G,
        gyro_threshold_dps=GYRO_MOTION_THRESHOLD_DPS,
        filter_alpha=FILTER_ALPHA,
    ):
        if float(inactivity_timeout_sec) <= 0:
            raise ValueError("Auto-Dim inactivity timeout must be positive")
        if int(sample_interval_ms) <= 0:
            raise ValueError("Auto-Dim sample interval must be positive")
        if float(acceleration_threshold_g) <= 0:
            raise ValueError("Acceleration motion threshold must be positive")
        if float(gyro_threshold_dps) <= 0:
            raise ValueError("Gyroscope motion threshold must be positive")
        if float(filter_alpha) <= 0 or float(filter_alpha) > 1:
            raise ValueError("Filter alpha must be greater than 0 and at most 1")
        if (
            not isinstance(dim_percent, int)
            or isinstance(dim_percent, bool)
            or not 1 <= dim_percent <= 100
        ):
            raise ValueError("Auto-Dim percentage must be an integer from 1 to 100")

        self.lcd = lcd
        self.sensor = sensor
        self.enabled = bool(enabled)
        self.normal_percent = max(0, min(100, int(normal_percent)))
        self.dim_percent = dim_percent
        self.clock = clock
        self.inactivity_timeout_ms = int(float(inactivity_timeout_sec) * 1000)
        self.sample_interval_ms = int(sample_interval_ms)
        self.acceleration_threshold_g = float(acceleration_threshold_g)
        self.gyro_threshold_dps = float(gyro_threshold_dps)
        self.filter_alpha = float(filter_alpha)
        self.active = False
        self.dimmed = False
        self.filtered_acceleration = None
        self.filtered_gyroscope = None
        self.last_sample_ms = None
        self.last_motion_ms = None
        self._applied_percent = None

    @property
    def available(self):
        return self.sensor is not None

    def _apply_brightness(self, percent, force=False):
        value = max(0, min(100, int(percent)))
        if force or value != self._applied_percent:
            self.lcd.set_bl_pwm(brightness_duty(value))
            self._applied_percent = value

    def _reset_motion_state(self, now_ms=None):
        if now_ms is None:
            now_ms = _ticks_ms(self.clock)
        self.filtered_acceleration = None
        self.filtered_gyroscope = None
        self.last_sample_ms = None
        self.last_motion_ms = now_ms

    def set_sensor(self, sensor):
        """Replace the shared IMU and restart the inactivity interval."""
        self.sensor = sensor
        if self.active:
            self._reset_motion_state()

    def enter_ready(self):
        """Wake at saved brightness and begin a fresh Ready interval."""
        self.active = True
        self.dimmed = False
        self._apply_brightness(self.normal_percent, force=True)
        self._reset_motion_state()

    def leave_ready(self):
        """Restore saved brightness before any non-Ready screen is drawn."""
        self.active = False
        self.dimmed = False
        self._apply_brightness(self.normal_percent, force=True)
        self.filtered_acceleration = None
        self.filtered_gyroscope = None
        self.last_sample_ms = None
        self.last_motion_ms = None

    def disable_sensor(self):
        """Degrade safely to normal brightness after an IMU failure."""
        self.sensor = None
        self.dimmed = False
        self._apply_brightness(self.normal_percent, force=True)
        self._reset_motion_state()

    def _motion_detected(self, sample):
        acceleration, gyroscope = _axes(sample)
        if self.filtered_acceleration is None:
            self.filtered_acceleration = acceleration
            acceleration_delta = 0.0
        else:
            acceleration_delta = math.sqrt(
                sum(
                    (value - reference) * (value - reference)
                    for value, reference in zip(
                        acceleration,
                        self.filtered_acceleration,
                    )
                )
            )
            alpha = self.filter_alpha
            if acceleration_delta >= self.acceleration_threshold_g:
                # A real movement becomes the new reference immediately so
                # the inactivity interval starts when that movement stops,
                # rather than waiting for a slow filter to catch up.
                self.filtered_acceleration = acceleration
            else:
                self.filtered_acceleration = tuple(
                    reference + alpha * (value - reference)
                    for value, reference in zip(
                        acceleration,
                        self.filtered_acceleration,
                    )
                )
        if self.filtered_gyroscope is None:
            self.filtered_gyroscope = gyroscope
            gyro_delta = 0.0
        else:
            gyro_delta = math.sqrt(
                sum(
                    (value - reference) * (value - reference)
                    for value, reference in zip(
                        gyroscope,
                        self.filtered_gyroscope,
                    )
                )
            )
            if gyro_delta < self.gyro_threshold_dps:
                alpha = self.filter_alpha
                self.filtered_gyroscope = tuple(
                    reference + alpha * (value - reference)
                    for value, reference in zip(
                        gyroscope,
                        self.filtered_gyroscope,
                    )
                )
        return (
            acceleration_delta >= self.acceleration_threshold_g
            or gyro_delta >= self.gyro_threshold_dps
        )

    def update(self, sample=None, now_ms=None, force=False):
        """Poll at a bounded rate and return whether brightness changed."""
        if not self.active or not self.enabled or not self.available:
            return False
        if now_ms is None:
            now_ms = _ticks_ms(self.clock)
        if (
            not force
            and self.last_sample_ms is not None
            and _ticks_diff(self.clock, now_ms, self.last_sample_ms)
            < self.sample_interval_ms
        ):
            return False
        self.last_sample_ms = now_ms

        if sample is None:
            sample = self.sensor.Read_XYZ()
        if self._motion_detected(sample):
            self.last_motion_ms = now_ms
            if self.dimmed:
                self.dimmed = False
                self._apply_brightness(self.normal_percent)
                return True
            return False

        if (
            not self.dimmed
            and _ticks_diff(self.clock, now_ms, self.last_motion_ms)
            >= self.inactivity_timeout_ms
        ):
            self.dimmed = True
            self._apply_brightness(self.dim_percent)
            return True
        return False
