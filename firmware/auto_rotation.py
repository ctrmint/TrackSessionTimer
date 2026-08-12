"""Filtered, four-way automatic display orientation."""

import time

from hardware import PeripheralError
from orientation import validate_rotation


AUTO_ROTATION = "auto"
FILTER_ALPHA = 0.30
MIN_PLANE_G = 0.55
MIN_TOTAL_G = 0.70
MAX_TOTAL_G = 1.35
DOMINANCE_RATIO = 1.25
STABLE_MS = 300
SAMPLE_INTERVAL_MS = 100
PRIME_SAMPLES = 5


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


def classify_rotation(
    sample,
    minimum_plane_g=MIN_PLANE_G,
    minimum_total_g=MIN_TOTAL_G,
    maximum_total_g=MAX_TOTAL_G,
    dominance_ratio=DOMINANCE_RATIO,
):
    """Return a stable quarter-turn candidate, or ``None`` if ambiguous."""
    x_axis, y_axis, z_axis = _axes(sample)
    x_abs = abs(x_axis)
    y_abs = abs(y_axis)
    plane_squared = (x_axis * x_axis) + (y_axis * y_axis)
    total_squared = plane_squared + (z_axis * z_axis)

    if plane_squared < float(minimum_plane_g) ** 2:
        return None
    if total_squared < float(minimum_total_g) ** 2:
        return None
    if total_squared > float(maximum_total_g) ** 2:
        return None

    ratio = float(dominance_ratio)
    if x_abs >= y_abs * ratio:
        # The board silkscreen has +X toward native screen down. A stationary
        # accelerometer reports specific force toward physical screen up.
        return 0 if x_axis < 0 else 180
    if y_abs >= x_abs * ratio:
        # +Y points toward native screen right.
        return 90 if y_axis < 0 else 270
    return None


class AutoOrientationDetector:
    """Low-pass and debounce gravity into a retained mount rotation."""

    def __init__(
        self,
        initial_rotation=0,
        filter_alpha=FILTER_ALPHA,
        stable_ms=STABLE_MS,
        clock=time,
    ):
        alpha = float(filter_alpha)
        if alpha <= 0 or alpha > 1:
            raise ValueError("filter_alpha must be greater than 0 and at most 1")
        if int(stable_ms) < 0:
            raise ValueError("stable_ms cannot be negative")
        self.filter_alpha = alpha
        self.stable_ms = int(stable_ms)
        self.clock = clock
        self.current_rotation = validate_rotation(initial_rotation)
        self.filtered = None
        self.candidate_rotation = None
        self.candidate_since = None
        self.reliable = False

    def reset(self, current_rotation=None):
        if current_rotation is not None:
            self.current_rotation = validate_rotation(current_rotation)
        self.filtered = None
        self.candidate_rotation = None
        self.candidate_since = None
        self.reliable = False

    def update(self, sample, now_ms=None):
        axes = _axes(sample)
        if self.filtered is None:
            self.filtered = axes
        else:
            alpha = self.filter_alpha
            self.filtered = tuple(
                previous + alpha * (value - previous)
                for previous, value in zip(self.filtered, axes)
            )

        candidate = classify_rotation(self.filtered)
        if candidate is None:
            self.reliable = False
            self.candidate_rotation = None
            self.candidate_since = None
            return None

        self.reliable = True
        if candidate == self.current_rotation:
            self.candidate_rotation = None
            self.candidate_since = None
            return None

        if now_ms is None:
            now_ms = _ticks_ms(self.clock)
        if candidate != self.candidate_rotation:
            self.candidate_rotation = candidate
            self.candidate_since = now_ms
            return None

        if _ticks_diff(self.clock, now_ms, self.candidate_since) < self.stable_ms:
            return None

        self.current_rotation = candidate
        self.candidate_rotation = None
        self.candidate_since = None
        return candidate


class AutoRotationController:
    """Coordinate sensor detection, LCD rotation, and touch mapping."""

    def __init__(
        self,
        sensor,
        lcd,
        touch,
        initial_rotation=0,
        sensor_factory=None,
        sensor_error=None,
        detector=None,
        clock=time,
        sample_interval_ms=SAMPLE_INTERVAL_MS,
        logger=print,
    ):
        if int(sample_interval_ms) < 0:
            raise ValueError("sample_interval_ms cannot be negative")
        self.sensor = sensor
        self.lcd = lcd
        self.touch = touch
        self.sensor_factory = sensor_factory
        self.error = sensor_error
        self.detector = detector or AutoOrientationDetector(
            initial_rotation=initial_rotation,
            clock=clock,
        )
        self.clock = clock
        self.sample_interval_ms = int(sample_interval_ms)
        self.logger = logger
        self.enabled = False
        self.last_sample_ms = None
        self.initialization_attempted = sensor is not None or sensor_error is not None

    @property
    def current_rotation(self):
        return self.detector.current_rotation

    @property
    def available(self):
        return self.sensor is not None and self.error is None

    def set_sensor(self, sensor, error=None):
        self.sensor = sensor
        self.error = error
        self.initialization_attempted = sensor is not None or error is not None
        self.last_sample_ms = None
        self.detector.reset(self.current_rotation)

    def _initialize_sensor(self):
        if self.sensor_factory is None or self.initialization_attempted:
            return self.available
        self.initialization_attempted = True
        result = self.sensor_factory()
        if isinstance(result, tuple):
            sensor, error = result
        else:
            sensor, error = result, None
        self.set_sensor(sensor, error)
        return self.available

    def enable(self, initialize=True):
        self.enabled = True
        if self.sensor is None and initialize:
            self._initialize_sensor()
        return self.available

    def disable(self, current_rotation=None):
        self.enabled = False
        if current_rotation is not None:
            self.detector.reset(current_rotation)

    def status_text(self):
        if not self.available:
            return "IMU unavailable"
        if not self.detector.reliable:
            return "Hold device upright"
        return "Detected: {} deg".format(self.current_rotation)

    def update(self, force=False, redraw=True):
        if not self.enabled or not self.available:
            return False

        now_ms = _ticks_ms(self.clock)
        if (
            not force
            and self.last_sample_ms is not None
            and _ticks_diff(self.clock, now_ms, self.last_sample_ms)
            < self.sample_interval_ms
        ):
            return False
        self.last_sample_ms = now_ms

        try:
            sample = self.sensor.Read_XYZ()
        except (PeripheralError, OSError) as error:
            self.sensor = None
            self.error = error
            self.logger("Auto rotation paused: {}".format(error))
            return False

        rotation = self.detector.update(sample, now_ms=now_ms)
        if rotation is None:
            return False

        self.lcd.set_rotation(rotation)
        self.touch.Set_Rotation(rotation)
        if redraw:
            self.lcd.show()
        return True

    def prime(self, samples=PRIME_SAMPLES):
        """Collect enough startup samples to resolve a stable first angle."""
        count = max(0, int(samples))
        for index in range(count):
            self.update(force=True, redraw=False)
            if index < count - 1:
                _sleep_ms(self.clock, self.sample_interval_ms)
        return self.current_rotation
