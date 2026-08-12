"""Small non-blocking continuous-touch hold detector."""

import time


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


class HoldDetector:
    """Return True once when a continuous physical touch reaches a threshold."""

    def __init__(self, duration_sec=5, clock=time):
        duration = float(duration_sec)
        if duration <= 0:
            raise ValueError("Hold duration must be greater than zero")
        self.duration_ms = int(duration * 1000)
        self.clock = clock
        self.started_at = None
        self.triggered = False

    def reset(self):
        self.started_at = None
        self.triggered = False

    def update(self, pressed):
        if not pressed:
            self.reset()
            return False

        now = _ticks_ms(self.clock)
        if self.started_at is None:
            self.started_at = now
            return False
        if self.triggered:
            return False
        if _ticks_diff(self.clock, now, self.started_at) >= self.duration_ms:
            self.triggered = True
            return True
        return False
