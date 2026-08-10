"""Graphical, baseline-corrected live G meter for the round display."""

import math
import time

from hold_detector import HoldDetector


DISPLAY_CENTER_X = 120
DISPLAY_CENTER_Y = 110
PLOT_RADIUS = 72
PEAK_ARC_RADIUS = 82
PEAK_ARC_DOT_RADIUS = 2
VISUAL_SCALE_G = 4.0
FILTER_ALPHA = 0.60
TRAIL_LENGTH = 6
CALIBRATION_SAMPLES = 20
CALIBRATION_INTERVAL_MS = 20
FRAME_PERIOD_MS = 60


def _sleep_ms(clock, milliseconds):
    sleep_ms = getattr(clock, "sleep_ms", None)
    if sleep_ms is not None:
        sleep_ms(milliseconds)
    else:
        clock.sleep(milliseconds / 1000)


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


def remaining_frame_delay_ms(clock, frame_started, period_ms=FRAME_PERIOD_MS):
    """Return only the delay needed to complete the target frame period."""
    elapsed = _ticks_diff(clock, _ticks_ms(clock), frame_started)
    return max(0, int(period_ms) - elapsed)


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


def vector_point(
    vector,
    scale_g=VISUAL_SCALE_G,
    center_x=DISPLAY_CENTER_X,
    center_y=DISPLAY_CENTER_Y,
    radius=PLOT_RADIUS,
):
    """Map a G vector to a clamped display point inside the meter."""
    scale = float(scale_g)
    if scale <= 0:
        raise ValueError("Visual scale must be greater than zero")
    x_value = float(vector[0])
    y_value = float(vector[1])
    magnitude = math.sqrt((x_value * x_value) + (y_value * y_value))
    if magnitude > scale:
        factor = scale / magnitude
        x_value *= factor
        y_value *= factor
    return (
        int(round(center_x + ((x_value / scale) * radius))),
        int(round(center_y - ((y_value / scale) * radius))),
    )


class GMeterState:
    """Bounded filtered live/peak state independent of display hardware."""

    def __init__(
        self,
        baseline=(0.0, 0.0, 0.0),
        filter_alpha=FILTER_ALPHA,
        visual_scale_g=VISUAL_SCALE_G,
        trail_length=TRAIL_LENGTH,
    ):
        alpha = float(filter_alpha)
        if alpha <= 0 or alpha > 1:
            raise ValueError("Filter alpha must be greater than 0 and at most 1")
        if float(visual_scale_g) <= 0:
            raise ValueError("Visual scale must be greater than zero")
        if trail_length < 1:
            raise ValueError("Trail length must be positive")
        self.baseline = tuple(float(value) for value in baseline[:3])
        if len(self.baseline) != 3:
            raise ValueError("Baseline must contain x, y, and z axes")
        self.filter_alpha = alpha
        self.visual_scale_g = float(visual_scale_g)
        self.trail_length = int(trail_length)
        self.current = (0.0, 0.0)
        self.peak = (0.0, 0.0)
        self.peak_magnitude = 0.0
        self.trail = []

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
        self.trail.append(self.current)
        if len(self.trail) > self.trail_length:
            del self.trail[0]
        return self.current

    def reset_peak(self):
        self.peak = (0.0, 0.0)
        self.peak_magnitude = 0.0
        self.trail = []


def _draw_peak_arc(lcd, peak_magnitude, scale_g):
    segment_count = 60
    proportion = min(1.0, max(0.0, peak_magnitude / scale_g))
    active_segments = int(round(segment_count * proportion))
    for index in range(active_segments):
        angle = (-math.pi / 2) + (2 * math.pi * index / segment_count)
        x_position = DISPLAY_CENTER_X + int(
            round(math.cos(angle) * PEAK_ARC_RADIUS)
        )
        y_position = DISPLAY_CENTER_Y + int(
            round(math.sin(angle) * PEAK_ARC_RADIUS)
        )
        lcd.ellipse(
            x_position,
            y_position,
            PEAK_ARC_DOT_RADIUS,
            PEAK_ARC_DOT_RADIUS,
            lcd.red,
            True,
        )


def _hold_label(seconds):
    value = float(seconds)
    if value == int(value):
        return str(int(value))
    return str(value)


def draw_g_meter_frame(lcd, state, mode_hold_seconds=5):
    """Draw live vector, trail, peak marker, and peak-magnitude arc."""
    lcd.fill(lcd.black)
    lcd.write_centered("G MODE", 5, 2, lcd.white)

    for radius in (24, 48, PLOT_RADIUS):
        lcd.ellipse(
            DISPLAY_CENTER_X,
            DISPLAY_CENTER_Y,
            radius,
            radius,
            lcd.blue,
        )
    lcd.hline(
        DISPLAY_CENTER_X - PLOT_RADIUS,
        DISPLAY_CENTER_Y,
        (PLOT_RADIUS * 2) + 1,
        lcd.blue,
    )
    lcd.vline(
        DISPLAY_CENTER_X,
        DISPLAY_CENTER_Y - PLOT_RADIUS,
        (PLOT_RADIUS * 2) + 1,
        lcd.blue,
    )

    for index, vector in enumerate(state.trail):
        x_position, y_position = vector_point(
            vector,
            scale_g=state.visual_scale_g,
        )
        marker_radius = 1 if index < len(state.trail) - 2 else 2
        lcd.ellipse(
            x_position,
            y_position,
            marker_radius,
            marker_radius,
            lcd.palegreen,
            True,
        )

    if state.peak_magnitude > 0:
        peak_x, peak_y = vector_point(
            state.peak,
            scale_g=state.visual_scale_g,
        )
        lcd.ellipse(peak_x, peak_y, 7, 7, lcd.red)
        lcd.line(peak_x - 4, peak_y, peak_x + 4, peak_y, lcd.red)
        lcd.line(peak_x, peak_y - 4, peak_x, peak_y + 4, lcd.red)

    current_x, current_y = vector_point(
        state.current,
        scale_g=state.visual_scale_g,
    )
    lcd.ellipse(current_x, current_y, 5, 5, lcd.palegreen, True)
    _draw_peak_arc(lcd, state.peak_magnitude, state.visual_scale_g)

    lcd.write_text("LIVE", 43, 178, 1, lcd.palegreen)
    lcd.write_text("MAX", 169, 178, 1, lcd.red)
    lcd.write_centered("Tap x2: reset", 201, 1, lcd.white)
    lcd.write_centered(
        "Hold {}s: menu".format(_hold_label(mode_hold_seconds)),
        220,
        1,
        lcd.white,
    )
    lcd.show()


def run_g_mode(sensor, touch, lcd, hold_seconds, clock=time):
    """Run the live graphical meter until the configured hold opens the menu."""
    touch.Set_Mode(0)
    touch.ControlScreen(
        lcd,
        text_array=[
            ["G MODE", None, 45, 3, "white"],
            ["Calibrating", None, 110, 2, "white"],
            ["Keep device still", None, 155, 1, "white"],
        ],
        back_colour="black",
    )
    baseline = calibrate_baseline(sensor, clock=clock)
    state = GMeterState(baseline=baseline)
    hold_detector = HoldDetector(hold_seconds, clock=clock)

    while True:
        frame_started = _ticks_ms(clock)
        state.update(sensor.Read_XYZ())
        if touch.StopGesture(lcd):
            state.reset_peak()
        draw_g_meter_frame(lcd, state, mode_hold_seconds=hold_seconds)

        if hold_detector.update(touch.IsPressed(lcd)):
            touch.ClearPendingInput()
            return state
        delay_ms = remaining_frame_delay_ms(clock, frame_started)
        if delay_ms > 0:
            _sleep_ms(clock, delay_ms)
