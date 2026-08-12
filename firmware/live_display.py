"""Throttled live-session display updates with responsive input polling."""

import time

from timing import secs_to_mins_secs


LIVE_LOOP_DELAY_SEC = 0.05
# Native font size 7 is 74 px: the nearest available size to 10% above the
# previous 64 px countdown (target 70.4 px).
COUNTDOWN_TEXT_SIZE = 7

# RGB888 is used for interpolation so named colours remain predictable.  The
# final value is converted to the byte-swapped RGB565 integer required when
# MicroPython's little-endian framebuffer is sent directly to the GC9A01.
TRACK_GREEN_RGB = (0, 255, 0)
TRACK_YELLOW_RGB = (255, 255, 0)
TRACK_AMBER_RGB = (255, 191, 0)
TRACK_RED_RGB = (255, 0, 0)
TRACK_OVERRUN_PURPLE_RGB = (96, 32, 128)
TRACK_GRADIENT_RGB = (
    TRACK_GREEN_RGB,
    TRACK_YELLOW_RGB,
    TRACK_AMBER_RGB,
    TRACK_RED_RGB,
)


def rgb_to_display565(rgb):
    """Convert RGB888 to the byte-swapped RGB565 framebuffer integer."""
    red, green, blue = rgb
    value = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
    return ((value & 0xFF) << 8) | (value >> 8)


def _interpolate_channel(start, end, numerator, denominator):
    """Interpolate one byte channel using rounded integer arithmetic."""
    return (
        (start * (denominator - numerator))
        + (end * numerator)
        + (denominator // 2)
    ) // denominator


def interpolate_rgb(start, end, numerator, denominator):
    """Return the clamped RGB colour between two endpoints."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator <= 0:
        return start
    if numerator >= denominator:
        return end
    return (
        _interpolate_channel(start[0], end[0], numerator, denominator),
        _interpolate_channel(start[1], end[1], numerator, denominator),
        _interpolate_channel(start[2], end[2], numerator, denominator),
    )


def scheduled_track_rgb(elapsed_seconds, duration_seconds):
    """Return the proportional green-yellow-amber-red session colour."""
    duration_seconds = int(duration_seconds)
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")

    elapsed_seconds = int(elapsed_seconds)
    if elapsed_seconds <= 0:
        return TRACK_GREEN_RGB
    if elapsed_seconds >= duration_seconds:
        return TRACK_RED_RGB

    segment_count = len(TRACK_GRADIENT_RGB) - 1
    scaled_elapsed = elapsed_seconds * segment_count
    segment = scaled_elapsed // duration_seconds
    segment_progress = scaled_elapsed - (segment * duration_seconds)
    return interpolate_rgb(
        TRACK_GRADIENT_RGB[segment],
        TRACK_GRADIENT_RGB[segment + 1],
        segment_progress,
        duration_seconds,
    )


def _linear_channel(channel):
    """Convert an sRGB byte channel to its linear-light value."""
    value = channel / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb):
    """Return WCAG relative luminance for an RGB888 colour."""
    return (
        (0.2126 * _linear_channel(rgb[0]))
        + (0.7152 * _linear_channel(rgb[1]))
        + (0.0722 * _linear_channel(rgb[2]))
    )


def high_contrast_text_colour(rgb, black, white):
    """Choose black or white, whichever has greater WCAG contrast."""
    luminance = relative_luminance(rgb)
    black_contrast = (luminance + 0.05) / 0.05
    white_contrast = 1.05 / (luminance + 0.05)
    return black if black_contrast >= white_contrast else white


def _visible_times(session, now):
    elapsed_seconds, remaining_seconds = _visible_seconds(session, now)
    return (
        secs_to_mins_secs(remaining_seconds),
        secs_to_mins_secs(elapsed_seconds),
    )


def _visible_seconds(session, now):
    elapsed_seconds = max(0, int(now - session.start_time))
    remaining_seconds = max(0, int(session.duration_secs) - elapsed_seconds)
    return elapsed_seconds, remaining_seconds


def estimated_laps_display(remaining_seconds, avg_lap_time_seconds):
    """Return separate lap label/value content, or ``None`` if unavailable."""
    if (
        not isinstance(avg_lap_time_seconds, int)
        or isinstance(avg_lap_time_seconds, bool)
        or avg_lap_time_seconds <= 0
    ):
        return None
    remaining = max(0, int(remaining_seconds))
    estimate = remaining / avg_lap_time_seconds
    if estimate < 100:
        value = "{:.1f}".format(estimate)
    else:
        value = str(int(estimate + 0.5))
    return "LAP", value


def track_live_frame(
    session,
    now,
    lcd,
    maximum_g=None,
    lower_display="elapsed",
    avg_lap_time_seconds=0,
):
    """Return the track timer with a smooth proportional colour gradient."""
    _, remaining_seconds = _visible_seconds(session, now)
    remaining, elapsed = _visible_times(session, now)
    if lower_display == "laps_remaining":
        laps_display = estimated_laps_display(
            remaining_seconds,
            avg_lap_time_seconds,
        )
        if laps_display is not None:
            elapsed = laps_display
    if now >= session.end_time:
        background_rgb = TRACK_OVERRUN_PURPLE_RGB
        remaining = "00:00"
    else:
        elapsed_seconds = max(0, int(now - session.start_time))
        background_rgb = scheduled_track_rgb(
            elapsed_seconds,
            session.duration_secs,
        )

    background = rgb_to_display565(background_rgb)
    text_colour = high_contrast_text_colour(
        background_rgb,
        lcd.black,
        lcd.white,
    )
    return (
        remaining,
        elapsed,
        COUNTDOWN_TEXT_SIZE,
        background,
        text_colour,
        maximum_g,
    )


def rest_live_frame(session, now, lcd):
    """Return visible rest-session values, or ``None`` when it is complete."""
    if now >= session.end_time:
        return None
    remaining, elapsed = _visible_times(session, now)
    return (
        remaining,
        elapsed,
        COUNTDOWN_TEXT_SIZE,
        lcd.blue,
        None,
        None,
    )


def draw_live_frame(touch, lcd, frame):
    """Render one frame tuple produced by a live-frame builder."""
    remaining, elapsed, text_size, background, text_colour, maximum_g = frame
    touch.LiveScreen(
        lcd,
        textsize_rem=text_size,
        backColour=background,
        textColour=text_colour,
        elapsed=elapsed,
        remaining=remaining,
        maximum_g=maximum_g,
    )


def run_live_display(
    session,
    frame_builder,
    draw_frame,
    stop_check,
    clock=time,
    loop_delay_sec=LIVE_LOOP_DELAY_SEC,
    sample_update=None,
):
    """Poll input at a bounded rate and redraw only when visible state changes."""
    if loop_delay_sec <= 0:
        raise ValueError("loop_delay_sec must be positive")

    previous_frame = None
    first_frame = True
    redraw_count = 0

    while session.live is True:
        if stop_check():
            session.live = False
            break

        now = clock.time()
        if sample_update is not None:
            sample_update(now)
        frame = frame_builder(now)
        if frame is None:
            session.live = False
            break

        if first_frame or frame != previous_frame:
            draw_frame(frame)
            previous_frame = frame
            first_frame = False
            redraw_count += 1

        clock.sleep(loop_delay_sec)

    return redraw_count
