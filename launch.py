"""Orientation-independent, cancellable vehicle launch detection."""

import math
import time


CALIBRATION_SAMPLES = 20
SAMPLE_INTERVAL_MS = 20
FILTER_ALPHA = 0.35
TRIGGER_SAMPLES = 3
DEFAULT_TIMEOUT_SEC = 30


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


def _timed_out(clock, started_at, timeout_sec):
    if timeout_sec is None:
        return False
    elapsed_ms = _ticks_diff(clock, _ticks_ms(clock), started_at)
    return elapsed_ms >= int(timeout_sec * 1000)


def _should_exit(cancel_check, clock, started_at, timeout_sec):
    return (
        (cancel_check is not None and cancel_check())
        or _timed_out(clock, started_at, timeout_sec)
    )


def _acceleration(sample):
    if len(sample) < 3:
        raise ValueError("Accelerometer sample must contain x, y, and z axes")
    return float(sample[0]), float(sample[1]), float(sample[2])


def accel_launch(
    qmi8658,
    sensitivity=0,
    cancel_check=None,
    timeout_sec=DEFAULT_TIMEOUT_SEC,
    clock=time,
    calibration_samples=CALIBRATION_SAMPLES,
    sample_interval_ms=SAMPLE_INTERVAL_MS,
    filter_alpha=FILTER_ALPHA,
    trigger_samples=TRIGGER_SAMPLES,
):
    """Wait for a sustained acceleration-vector change and return its outcome.

    ``sensitivity`` is a threshold in g relative to a stationary baseline. The
    baseline removes gravity and device mounting orientation. Both positive and
    negative acceleration are detected because the filtered vector magnitude is
    used. ``False`` means the wait was cancelled or timed out.
    """
    threshold = float(sensitivity)
    if threshold <= 0:
        return True
    if calibration_samples < 1:
        raise ValueError("calibration_samples must be positive")
    if trigger_samples < 1:
        raise ValueError("trigger_samples must be positive")
    if sample_interval_ms < 0:
        raise ValueError("sample_interval_ms cannot be negative")
    if filter_alpha <= 0 or filter_alpha > 1:
        raise ValueError("filter_alpha must be greater than 0 and at most 1")

    started_at = _ticks_ms(clock)
    baseline = [0.0, 0.0, 0.0]
    for _ in range(calibration_samples):
        if _should_exit(cancel_check, clock, started_at, timeout_sec):
            return False
        axes = _acceleration(qmi8658.Read_XYZ())
        baseline[0] += axes[0]
        baseline[1] += axes[1]
        baseline[2] += axes[2]
        _sleep_ms(clock, sample_interval_ms)

    baseline[0] /= calibration_samples
    baseline[1] /= calibration_samples
    baseline[2] /= calibration_samples

    filtered = [0.0, 0.0, 0.0]
    consecutive = 0
    while True:
        if _should_exit(cancel_check, clock, started_at, timeout_sec):
            return False

        axes = _acceleration(qmi8658.Read_XYZ())
        for index in range(3):
            delta = axes[index] - baseline[index]
            filtered[index] += filter_alpha * (delta - filtered[index])

        magnitude = math.sqrt(
            (filtered[0] * filtered[0])
            + (filtered[1] * filtered[1])
            + (filtered[2] * filtered[2])
        )
        if magnitude >= threshold:
            consecutive += 1
            if consecutive >= trigger_samples:
                return True
        else:
            consecutive = 0

        _sleep_ms(clock, sample_interval_ms)
