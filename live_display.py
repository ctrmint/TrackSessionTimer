"""Throttled live-session display updates with responsive input polling."""

import time

from timing import secs_to_mins_secs


LIVE_LOOP_DELAY_SEC = 0.05
# Native font size 7 is 74 px: the nearest available size to 10% above the
# previous 64 px countdown (target 70.4 px).
COUNTDOWN_TEXT_SIZE = 7


def _visible_times(session, now):
    elapsed_seconds = max(0, int(now - session.start_time))
    remaining_seconds = max(0, int(session.duration_secs) - elapsed_seconds)
    return (
        secs_to_mins_secs(remaining_seconds),
        secs_to_mins_secs(elapsed_seconds),
    )


def track_live_frame(session, now, lcd):
    """Return all values visible on the track-session screen."""
    remaining, elapsed = _visible_times(session, now)
    if now >= session.end_time:
        return ("00:00", elapsed, COUNTDOWN_TEXT_SIZE, lcd.red, lcd.black)

    if now < session.last_15:
        return (remaining, elapsed, COUNTDOWN_TEXT_SIZE, None, None)
    if now < session.last_5:
        return (remaining, elapsed, COUNTDOWN_TEXT_SIZE, lcd.salmon, lcd.black)
    return (remaining, elapsed, COUNTDOWN_TEXT_SIZE, lcd.lilac, None)


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
    )


def draw_live_frame(touch, lcd, frame):
    """Render one frame tuple produced by a live-frame builder."""
    remaining, elapsed, text_size, background, text_colour = frame
    touch.LiveScreen(
        lcd,
        textsize_rem=text_size,
        backColour=background,
        textColour=text_colour,
        elapsed=elapsed,
        remaining=remaining,
    )


def run_live_display(
    session,
    frame_builder,
    draw_frame,
    stop_check,
    clock=time,
    loop_delay_sec=LIVE_LOOP_DELAY_SEC,
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

        frame = frame_builder(clock.time())
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
