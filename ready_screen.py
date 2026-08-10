"""Ready-screen settings summary independent of display hardware."""


DISPLAY_SIZE = 240
BATTERY_BODY_WIDTH = 31
BATTERY_BODY_HEIGHT = 16
BATTERY_TERMINAL_WIDTH = 4
BATTERY_TERMINAL_HEIGHT = 6
BATTERY_ICON_WIDTH = BATTERY_BODY_WIDTH + BATTERY_TERMINAL_WIDTH
BATTERY_ICON_X = (DISPLAY_SIZE - BATTERY_ICON_WIDTH) // 2
BATTERY_ICON_Y = 10
BATTERY_INNER_WIDTH = BATTERY_BODY_WIDTH - 4
READY_TITLE_Y = 38


def _format_sensitivity(sensitivity):
    numeric = float(sensitivity)
    if numeric == int(numeric):
        return str(int(numeric))
    return str(numeric)


def launch_status(sensitivity, imu_available):
    """Return the effective Launch Mode state shown before a session."""
    if float(sensitivity) <= 0:
        return "Launch OFF"
    if not imu_available:
        return "Launch unavailable"
    return "Launch {}g".format(_format_sensitivity(sensitivity))


def ready_screen_lines(
    track_minutes,
    rest_minutes,
    sensitivity,
    imu_available,
):
    """Build the complete Ready screen text layout."""
    return [
        ["Ready", None, READY_TITLE_Y, 4, "white"],
        ["Track {}m".format(track_minutes), None, 100, 2, "black"],
        ["Rest {}m".format(rest_minutes), None, 130, 2, "black"],
        [launch_status(sensitivity, imu_available), None, 160, 2, "black"],
        ["Swipe DOWN to start", None, 205, 1, "black"],
    ]


def battery_icon_bounds():
    """Return the complete icon bounds, including the positive terminal."""
    return (
        BATTERY_ICON_X,
        BATTERY_ICON_Y,
        BATTERY_ICON_WIDTH,
        BATTERY_BODY_HEIGHT,
    )


def _bounded_percentage(value):
    if value is None:
        return None
    return max(0, min(100, int(value)))


def _draw_lightning_bolt(lcd, x, y, color):
    """Draw a compact, high-contrast lightning bolt through the battery."""
    points = (
        (x + 19, y + 2, x + 14, y + 7),
        (x + 14, y + 7, x + 18, y + 7),
        (x + 18, y + 7, x + 14, y + 14),
    )
    for x1, y1, x2, y2 in points:
        lcd.line(x1, y1, x2, y2, color)
        lcd.line(x1 + 1, y1, x2 + 1, y2, color)


def draw_battery_icon(lcd, status):
    """Draw a standard battery gauge without refreshing the framebuffer."""
    x = BATTERY_ICON_X
    y = BATTERY_ICON_Y
    percentage = _bounded_percentage(getattr(status, "percentage", None))
    external_power = bool(getattr(status, "external_power", False))

    lcd.rect(x, y, BATTERY_BODY_WIDTH, BATTERY_BODY_HEIGHT, lcd.black)
    terminal_y = y + ((BATTERY_BODY_HEIGHT - BATTERY_TERMINAL_HEIGHT) // 2)
    lcd.fill_rect(
        x + BATTERY_BODY_WIDTH,
        terminal_y,
        BATTERY_TERMINAL_WIDTH,
        BATTERY_TERMINAL_HEIGHT,
        lcd.black,
    )

    if percentage is not None:
        fill_width = int(round(BATTERY_INNER_WIDTH * percentage / 100))
        if fill_width > 0:
            lcd.fill_rect(
                x + 2,
                y + 2,
                fill_width,
                BATTERY_BODY_HEIGHT - 4,
                lcd.black,
            )

    if external_power:
        _draw_lightning_bolt(lcd, x, y, lcd.white)


def draw_ready_screen(
    touch,
    lcd,
    track_minutes,
    rest_minutes,
    sensitivity,
    imu_available,
    battery_status,
):
    """Render the Ready text and battery graphic in one framebuffer update."""
    touch.ControlScreen(
        lcd,
        text_array=ready_screen_lines(
            track_minutes,
            rest_minutes,
            sensitivity,
            imu_available,
        ),
        back_colour="green",
        refresh=False,
    )
    draw_battery_icon(lcd, battery_status)
    lcd.show()
