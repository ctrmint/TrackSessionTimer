"""Compact, non-persistent summary shown after each track session."""

import gc

from timing import secs_to_mins_secs


COMPLETION_DRIVER_STOP = "Driver stop"
MAX_VISIBLE_G = 99.99
REVIEW_PAGE_COUNT = 8


def _visible_g(value):
    return min(MAX_VISIBLE_G, max(0.0, float(value)))


class SessionSummary:
    """Bounded values needed for one immediate post-session display."""

    def __init__(
        self,
        actual_seconds,
        scheduled_seconds,
        completion_reason,
        maximum_g=None,
        acceleration_g=None,
        braking_g=None,
        left_g=None,
        right_g=None,
        imu_complete=True,
    ):
        self.actual_seconds = max(0, int(actual_seconds))
        self.scheduled_seconds = max(0, int(scheduled_seconds))
        self.overrun_seconds = max(
            0,
            self.actual_seconds - self.scheduled_seconds,
        )
        self.completion_reason = str(completion_reason)
        self.maximum_g = maximum_g
        self.acceleration_g = acceleration_g
        self.braking_g = braking_g
        self.left_g = left_g
        self.right_g = right_g
        self.imu_complete = bool(imu_complete)

    @property
    def has_g_metrics(self):
        return self.maximum_g is not None


def build_session_summary(
    session,
    stopped_at,
    g_peak=None,
    completion_reason=COMPLETION_DRIVER_STOP,
):
    """Capture one summary from bounded in-memory timer and IMU state."""
    actual_seconds = max(0, int(stopped_at - session.start_time))
    if g_peak is None or not g_peak.metrics_available:
        return SessionSummary(
            actual_seconds,
            session.duration_secs,
            completion_reason,
            imu_complete=False,
        )

    return SessionSummary(
        actual_seconds,
        session.duration_secs,
        completion_reason,
        maximum_g=_visible_g(g_peak.total_peak_magnitude),
        acceleration_g=_visible_g(g_peak.max_acceleration_g),
        braking_g=_visible_g(g_peak.max_braking_g),
        left_g=_visible_g(g_peak.max_left_g),
        right_g=_visible_g(g_peak.max_right_g),
        imu_complete=g_peak.available,
    )


def _review_page_data(summary, page_index):
    if page_index == 0:
        return (
            "SESSION TIME",
            secs_to_mins_secs(summary.actual_seconds),
            None,
            6,
        )
    if page_index == 1:
        status = "ON TIME" if summary.overrun_seconds == 0 else None
        return (
            "OVERRUN",
            secs_to_mins_secs(summary.overrun_seconds),
            status,
            6,
        )

    metric_pages = (
        ("MAXIMUM G", summary.maximum_g),
        ("ACCELERATION", summary.acceleration_g),
        ("BRAKING", summary.braking_g),
        ("LEFT G", summary.left_g),
        ("RIGHT G", summary.right_g),
    )
    if page_index < REVIEW_PAGE_COUNT - 1:
        title, value = metric_pages[page_index - 2]
        if not summary.has_g_metrics:
            return title, "--", "IMU UNAVAILABLE", 6
        status = None if summary.imu_complete else "IMU DATA PARTIAL"
        return title, "{:.2f} g".format(value), status, 6

    return "SESSION END", summary.completion_reason.upper(), None, 3


def summary_page_lines(summary, page_index):
    """Return one high-visibility, round-screen-safe review page."""
    if page_index < 0 or page_index >= REVIEW_PAGE_COUNT:
        raise ValueError("Summary page is out of range")

    title, value, status, value_size = _review_page_data(summary, page_index)
    lines = [
        [
            "REVIEW {}/{}".format(page_index + 1, REVIEW_PAGE_COUNT),
            None,
            18,
            1,
            "white",
        ],
        [title, None, 44, 2, "green"],
        [
            value,
            None,
            105 if value_size == 3 else 90,
            value_size,
            "white",
        ],
    ]
    if status is not None:
        lines.append([status, None, 164, 1, "red"])

    left_prompt = (
        "LEFT: cool down"
        if page_index == REVIEW_PAGE_COUNT - 1
        else "LEFT: next"
    )
    lines.append([left_prompt, None, 181, 1, "green"])
    lines.append(
        [
            "RIGHT: back" if page_index > 0 else "Review each result",
            None,
            205,
            1,
            "white",
        ]
    )
    return lines


def draw_summary_page(touch, lcd, summary, page_index):
    """Render one review page without retaining or writing history."""
    # Each native-font page creates short-lived line and glyph objects.  Reclaim
    # the previous page before building the next one to protect the RP2040 heap.
    gc.collect()
    touch.ControlScreen(
        lcd,
        text_array=summary_page_lines(summary, page_index),
        back_colour="black",
    )


def review_session_summary(touch, lcd, summary):
    """Require ordered review before allowing the cool-down flow to begin."""
    page_index = 0
    while True:
        draw_summary_page(touch, lcd, summary, page_index)
        while True:
            gesture = touch.GetGesture(lcd, debounce_time=0.05)
            if gesture == "left":
                if page_index == REVIEW_PAGE_COUNT - 1:
                    return
                page_index += 1
                break
            if gesture == "right" and page_index > 0:
                page_index -= 1
                break
