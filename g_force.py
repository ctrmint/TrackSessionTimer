"""Shared baseline-corrected G calculations for live operating modes."""

import math
import time


FILTER_ALPHA = 0.60
CALIBRATION_SAMPLES = 20
CALIBRATION_INTERVAL_MS = 20
MAX_G_UNAVAILABLE = "MAX --"


def _sleep_ms(clock, milliseconds):
    sleep_ms = getattr(clock, "sleep_ms", None)
    if sleep_ms is not None:
        sleep_ms(milliseconds)
    else:
        clock.sleep(milliseconds / 1000)


def _axes(sample):
    if len(sample) < 3:
        raise ValueError("Accelerometer sample must contain x, y, and z axes")
    return float(sample[0]), float(sample[1]), float(sample[2])


def calibrate_baseline(
    sensor,
    samples=CALIBRATION_SAMPLES,
    interval_ms=CALIBRATION_INTERVAL_MS,
    clock=time,
):
    """Average stationary samples so gravity/mounting bias can be removed."""
    if samples < 1:
        raise ValueError("Calibration samples must be positive")
    baseline = [0.0, 0.0, 0.0]
    for _ in range(samples):
        axes = _axes(sensor.Read_XYZ())
        baseline[0] += axes[0]
        baseline[1] += axes[1]
        baseline[2] += axes[2]
        _sleep_ms(clock, interval_ms)
    return tuple(value / samples for value in baseline)


class PlanarGState:
    """Filtered planar acceleration and peak independent of presentation."""

    def __init__(self, baseline=(0.0, 0.0, 0.0), filter_alpha=FILTER_ALPHA):
        alpha = float(filter_alpha)
        if alpha <= 0 or alpha > 1:
            raise ValueError("Filter alpha must be greater than 0 and at most 1")
        self.baseline = tuple(float(value) for value in baseline[:3])
        if len(self.baseline) != 3:
            raise ValueError("Baseline must contain x, y, and z axes")
        self.filter_alpha = alpha
        self.current = (0.0, 0.0)
        self.peak = (0.0, 0.0)
        self.peak_magnitude = 0.0

    def update(self, sample):
        x_axis, y_axis, _z_axis = _axes(sample)
        target_x = x_axis - self.baseline[0]
        target_y = y_axis - self.baseline[1]
        filtered_x = self.current[0] + self.filter_alpha * (
            target_x - self.current[0]
        )
        filtered_y = self.current[1] + self.filter_alpha * (
            target_y - self.current[1]
        )
        self.current = (filtered_x, filtered_y)
        magnitude = math.sqrt(
            (filtered_x * filtered_x) + (filtered_y * filtered_y)
        )
        if magnitude > self.peak_magnitude:
            self.peak_magnitude = magnitude
            self.peak = self.current
        return self.current

    def reset_peak(self):
        self.peak = (0.0, 0.0)
        self.peak_magnitude = 0.0


class SessionGPeak:
    """Bounded session sampler with a once-per-visible-second label."""

    def __init__(self, sensor=None, baseline=(0.0, 0.0, 0.0)):
        self.sensor = sensor
        self.state = PlanarGState(baseline=baseline) if sensor is not None else None
        self._display_second = None
        self._display_label = MAX_G_UNAVAILABLE

    @property
    def available(self):
        return self.state is not None

    @property
    def peak_magnitude(self):
        return 0.0 if self.state is None else self.state.peak_magnitude

    def sample(self):
        """Take one sample; the caller controls the bounded polling rate."""
        if self.state is not None:
            self.state.update(self.sensor.Read_XYZ())

    def disable(self):
        self.sensor = None
        self.state = None
        self._display_second = None
        self._display_label = MAX_G_UNAVAILABLE

    def display_label(self, elapsed_seconds):
        """Return a stable label so peak sampling does not add redraws."""
        if self.state is None:
            return MAX_G_UNAVAILABLE
        visible_second = max(0, int(elapsed_seconds))
        if visible_second != self._display_second:
            # The supported IMU cannot reach 100 g. Capping protects the round
            # display safe area if a corrupt sample reports an extreme value.
            visible_peak = min(99.99, self.state.peak_magnitude)
            self._display_label = "MAX  {:.2f}  g".format(visible_peak)
            self._display_second = visible_second
        return self._display_label
