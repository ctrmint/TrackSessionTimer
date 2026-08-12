"""On-device operating-mode and settings menus."""

from auto_rotation import AUTO_ROTATION
from settings import (
    BRIGHTNESS_VALUES,
    DEFAULT_USER_PARAMS,
    DISPLAY_ROTATION_VALUES,
    MAX_AVG_LAP_TIME_SECONDS,
    OPERATING_MODES,
    TRACK_LOWER_DISPLAY_VALUES,
    persist_setting,
    persist_settings,
    restore_user_defaults,
)


MODE_TIMER = "timer"
MODE_G = "g"
MENU_SETTINGS = "settings"

MODE_CHOICES = (
    ("Timer Mode", MODE_TIMER),
    ("G Mode", MODE_G),
    ("Settings", MENU_SETTINGS),
)

SETTINGS_CHOICES = (
    ("Brightness", "brightness"),
    ("Rotation", "rotation"),
    ("Auto-Dim", "auto_dim"),
    ("Avg Lap Time", "avg_lap_time"),
    ("Lower Display", "lower_display"),
    ("Restore defaults", "restore"),
    ("Back", "back"),
)


def brightness_duty(percent):
    """Convert a validated percentage to the display PWM duty range."""
    value = max(0, min(100, int(percent)))
    return int(round(65535 * value / 100))


def apply_brightness(lcd, percent):
    lcd.set_bl_pwm(brightness_duty(percent))


def _choice_index(choices, value):
    for index, choice in enumerate(choices):
        if choice[1] == value:
            return index
    return 0


def _selection_lines(title, label, position, label_size=3):
    return [
        [title, None, 30, 2, "white"],
        [label, None, 92, label_size, "white"],
        [position, None, 145, 1, "white"],
        ["L/R: choose", None, 180, 1, "white"],
        ["UP: select", None, 202, 1, "white"],
        ["DOWN: cancel", None, 220, 1, "white"],
    ]


def mode_menu_lines(index):
    label = MODE_CHOICES[index][0]
    position = "{} / {}".format(index + 1, len(MODE_CHOICES))
    return _selection_lines("Operating Mode", label, position)


def available_settings_choices(avg_lap_time_seconds):
    """Hide the lap-dependent display choice until lap time is configured."""
    if (
        isinstance(avg_lap_time_seconds, int)
        and not isinstance(avg_lap_time_seconds, bool)
        and avg_lap_time_seconds > 0
    ):
        return SETTINGS_CHOICES
    return tuple(
        choice for choice in SETTINGS_CHOICES if choice[1] != "lower_display"
    )


def settings_menu_lines(index, choices=SETTINGS_CHOICES):
    label = choices[index][0]
    position = "{} / {}".format(index + 1, len(choices))
    return _selection_lines("Settings", label, position, label_size=2)


def _select_choice(touch, lcd, choices, lines_builder, current=None):
    index = _choice_index(choices, current)

    def draw():
        touch.ControlScreen(
            lcd,
            text_array=lines_builder(index),
            back_colour="black",
        )

    draw()
    while True:
        gesture = touch.GetGesture(lcd)
        if gesture == "left":
            index = (index - 1) % len(choices)
            draw()
        elif gesture == "right":
            index = (index + 1) % len(choices)
            draw()
        elif gesture == "up":
            return choices[index][1]
        elif gesture == "down":
            return None


def select_operating_mode(touch, lcd, current_mode):
    return _select_choice(
        touch,
        lcd,
        MODE_CHOICES,
        mode_menu_lines,
        current=current_mode,
    )


def select_settings_action(touch, lcd, avg_lap_time_seconds=0):
    choices = available_settings_choices(avg_lap_time_seconds)
    return _select_choice(
        touch,
        lcd,
        choices,
        lambda index: settings_menu_lines(index, choices),
    )


def brightness_lines(percent):
    return [
        ["Brightness", None, 35, 2, "white"],
        ["{}%".format(percent), None, 88, 5, "white"],
        ["L/R: change", None, 180, 1, "white"],
        ["UP: save", None, 202, 1, "white"],
        ["DOWN: cancel", None, 220, 1, "white"],
    ]


def select_brightness(touch, lcd, current):
    """Preview brightness choices and return ``(value, should_save)``."""
    values = list(BRIGHTNESS_VALUES)
    try:
        index = values.index(current)
    except ValueError:
        index = values.index(DEFAULT_USER_PARAMS["BRIGHTNESS_PERCENT"])
    original = values[index]

    def draw():
        apply_brightness(lcd, values[index])
        touch.ControlScreen(
            lcd,
            text_array=brightness_lines(values[index]),
            back_colour="black",
        )

    draw()
    while True:
        gesture = touch.GetGesture(lcd)
        if gesture == "left":
            index = (index - 1) % len(values)
            draw()
        elif gesture == "right":
            index = (index + 1) % len(values)
            draw()
        elif gesture == "up":
            return values[index], True
        elif gesture == "down":
            apply_brightness(lcd, original)
            return original, False


def auto_dim_lines(enabled):
    return [
        ["Auto-Dim", None, 35, 2, "white"],
        ["ON" if enabled else "OFF", None, 88, 5, "white"],
        ["Ready screen only", None, 153, 1, "white"],
        ["L/R: change", None, 180, 1, "white"],
        ["UP: save", None, 202, 1, "white"],
        ["DOWN: cancel", None, 220, 1, "white"],
    ]


def select_auto_dim(touch, lcd, current):
    """Select persistent Ready-screen Auto-Dim state."""
    values = (False, True)
    index = values.index(current) if isinstance(current, bool) else 0
    original = values[index]

    def draw():
        touch.ControlScreen(
            lcd,
            text_array=auto_dim_lines(values[index]),
            back_colour="black",
        )

    draw()
    while True:
        gesture = touch.GetGesture(lcd)
        if gesture in ("left", "right"):
            index = 1 - index
            draw()
        elif gesture == "up":
            return values[index], True
        elif gesture == "down":
            return original, False


def format_avg_lap_time(total_seconds):
    """Format a validated canonical duration for the settings display."""
    bounded = max(0, min(MAX_AVG_LAP_TIME_SECONDS, int(total_seconds)))
    minutes, seconds = divmod(bounded, 60)
    return "{:02d}:{:02d}".format(minutes, seconds)


def avg_lap_time_lines(total_seconds, component):
    """Build the two-stage average-lap-time editor."""
    setting_minutes = component == "minutes"
    return [
        ["Avg Lap Time", None, 30, 2, "white"],
        [format_avg_lap_time(total_seconds), None, 78, 4, "white"],
        [
            "Set minutes" if setting_minutes else "Set seconds",
            None,
            143,
            1,
            "white",
        ],
        ["L/R: change", None, 180, 1, "white"],
        ["UP: next" if setting_minutes else "UP: save", None, 202, 1, "white"],
        ["DOWN: cancel", None, 220, 1, "white"],
    ]


def select_avg_lap_time(touch, lcd, current):
    """Edit minutes then seconds and return ``(total_seconds, save)``."""
    if (
        not isinstance(current, int)
        or isinstance(current, bool)
        or current < 0
        or current > MAX_AVG_LAP_TIME_SECONDS
    ):
        current = DEFAULT_USER_PARAMS["AVG_LAP_TIME_SECONDS"]
    original = current
    minutes, seconds = divmod(current, 60)
    component = "minutes"

    def value():
        return (minutes * 60) + seconds

    def draw():
        touch.ControlScreen(
            lcd,
            text_array=avg_lap_time_lines(value(), component),
            back_colour="black",
        )

    draw()
    while True:
        gesture = touch.GetGesture(lcd)
        if gesture in ("left", "right"):
            delta = -1 if gesture == "left" else 1
            if component == "minutes":
                minutes = (minutes + delta) % 60
            else:
                seconds = (seconds + delta) % 60
            draw()
        elif gesture == "up":
            if component == "minutes":
                component = "seconds"
                draw()
            else:
                return value(), True
        elif gesture == "down":
            return original, False


def lower_display_lines(value):
    label = "LAPS LEFT" if value == "laps_remaining" else "COUNT UP"
    return [
        ["Lower Display", None, 35, 2, "white"],
        [label, None, 88, 3, "white"],
        ["Track sessions", None, 150, 1, "white"],
        ["L/R: change", None, 180, 1, "white"],
        ["UP: save", None, 202, 1, "white"],
        ["DOWN: cancel", None, 220, 1, "white"],
    ]


def select_lower_display(touch, lcd, current):
    """Select the running track screen's lower-line content."""
    values = TRACK_LOWER_DISPLAY_VALUES
    try:
        index = values.index(current)
    except ValueError:
        index = values.index(DEFAULT_USER_PARAMS["TRACK_LOWER_DISPLAY"])
    original = values[index]

    def draw():
        touch.ControlScreen(
            lcd,
            text_array=lower_display_lines(values[index]),
            back_colour="black",
        )

    draw()
    while True:
        gesture = touch.GetGesture(lcd)
        if gesture in ("left", "right"):
            index = 1 - index
            draw()
        elif gesture == "up":
            return values[index], True
        elif gesture == "down":
            return original, False


def apply_rotation(lcd, touch, degrees, auto_rotation=None):
    """Apply one mount angle to rendering and directional gestures."""
    if degrees == AUTO_ROTATION:
        if auto_rotation is not None:
            auto_rotation.enable()
            auto_rotation.update(force=True, redraw=False)
        return
    if auto_rotation is not None:
        auto_rotation.disable(current_rotation=degrees)
    lcd.set_rotation(degrees)
    touch.Set_Rotation(degrees)


def rotation_lines(value, auto_rotation=None):
    if value == AUTO_ROTATION:
        status = (
            auto_rotation.status_text()
            if auto_rotation is not None
            else "IMU unavailable"
        )
        label = "AUTO"
        detail = status
    else:
        label = "{} deg".format(value)
        detail = "Device clockwise"
    return [
        ["Mount rotation", None, 35, 2, "white"],
        [label, None, 88, 4, "white"],
        [detail, None, 150, 1, "white"],
        ["L/R: rotate", None, 180, 1, "white"],
        ["UP: save", None, 202, 1, "white"],
        ["DOWN: cancel", None, 220, 1, "white"],
    ]


def select_rotation(touch, lcd, current, auto_rotation=None):
    """Preview mount rotations and return ``(value, should_save)``."""
    values = list(DISPLAY_ROTATION_VALUES)
    try:
        index = values.index(current)
    except ValueError:
        index = values.index(DEFAULT_USER_PARAMS["DISPLAY_ROTATION_DEG"])
    original = values[index]
    last_auto_state = [None]

    def auto_state():
        if values[index] != AUTO_ROTATION or auto_rotation is None:
            return None
        return (
            auto_rotation.current_rotation,
            auto_rotation.available,
            auto_rotation.detector.reliable,
        )

    def draw():
        apply_rotation(
            lcd,
            touch,
            values[index],
            auto_rotation=auto_rotation,
        )
        touch.ControlScreen(
            lcd,
            text_array=rotation_lines(values[index], auto_rotation),
            back_colour="black",
        )
        last_auto_state[0] = auto_state()

    draw()
    while True:
        gesture = touch.GetGesture(lcd)
        if auto_state() != last_auto_state[0]:
            draw()
        if gesture == "left":
            index = (index - 1) % len(values)
            draw()
        elif gesture == "right":
            index = (index + 1) % len(values)
            draw()
        elif gesture == "up":
            return values[index], True
        elif gesture == "down":
            apply_rotation(
                lcd,
                touch,
                original,
                auto_rotation=auto_rotation,
            )
            return original, False


def restore_confirmation_lines(selected):
    return [
        ["Restore defaults?", None, 35, 2, "white"],
        ["Erases saved choices", None, 82, 1, "white"],
        [selected, None, 125, 3, "white"],
        ["L/R: choose", None, 180, 1, "white"],
        ["UP: confirm", None, 202, 1, "white"],
        ["DOWN: cancel", None, 220, 1, "white"],
    ]


def confirm_restore_defaults(touch, lcd):
    choices = ("Cancel", "RESTORE")
    index = 0

    def draw():
        touch.ControlScreen(
            lcd,
            text_array=restore_confirmation_lines(choices[index]),
            back_colour="red",
        )

    draw()
    while True:
        gesture = touch.GetGesture(lcd)
        if gesture in ("left", "right"):
            index = 1 - index
            draw()
        elif gesture == "up":
            return index == 1
        elif gesture == "down":
            return False


def _run_settings(
    touch,
    lcd,
    user_params,
    user_file,
    auto_rotation=None,
):
    while True:
        action = select_settings_action(
            touch,
            lcd,
            user_params["AVG_LAP_TIME_SECONDS"],
        )
        if action is None or action == "back":
            return user_params, False

        if action == "brightness":
            previous = user_params["BRIGHTNESS_PERCENT"]
            selected, should_save = select_brightness(touch, lcd, previous)
            if not should_save:
                continue
            updated, saved = persist_setting(
                user_file,
                user_params,
                "BRIGHTNESS_PERCENT",
                selected,
            )
            if saved:
                user_params = updated
            else:
                apply_brightness(lcd, previous)

        elif action == "rotation":
            previous = user_params["DISPLAY_ROTATION_DEG"]
            selected, should_save = select_rotation(
                touch,
                lcd,
                previous,
                auto_rotation=auto_rotation,
            )
            if not should_save:
                continue
            updated, saved = persist_setting(
                user_file,
                user_params,
                "DISPLAY_ROTATION_DEG",
                selected,
            )
            if saved:
                user_params = updated
            else:
                apply_rotation(
                    lcd,
                    touch,
                    previous,
                    auto_rotation=auto_rotation,
                )

        elif action == "auto_dim":
            previous = user_params["AUTO_DIM_ENABLED"]
            selected, should_save = select_auto_dim(touch, lcd, previous)
            if not should_save:
                continue
            updated, saved = persist_setting(
                user_file,
                user_params,
                "AUTO_DIM_ENABLED",
                selected,
            )
            if saved:
                user_params = updated

        elif action == "avg_lap_time":
            previous = user_params["AVG_LAP_TIME_SECONDS"]
            selected, should_save = select_avg_lap_time(
                touch,
                lcd,
                previous,
            )
            if not should_save:
                continue
            updates = {"AVG_LAP_TIME_SECONDS": selected}
            if selected == 0:
                updates["TRACK_LOWER_DISPLAY"] = DEFAULT_USER_PARAMS[
                    "TRACK_LOWER_DISPLAY"
                ]
            updated, saved = persist_settings(
                user_file,
                user_params,
                updates,
            )
            if saved:
                user_params = updated

        elif action == "lower_display":
            previous = user_params["TRACK_LOWER_DISPLAY"]
            selected, should_save = select_lower_display(
                touch,
                lcd,
                previous,
            )
            if not should_save:
                continue
            updated, saved = persist_setting(
                user_file,
                user_params,
                "TRACK_LOWER_DISPLAY",
                selected,
            )
            if saved:
                user_params = updated

        elif action == "restore" and confirm_restore_defaults(touch, lcd):
            defaults, saved = restore_user_defaults(user_file)
            if saved:
                apply_brightness(lcd, defaults["BRIGHTNESS_PERCENT"])
                apply_rotation(
                    lcd,
                    touch,
                    defaults["DISPLAY_ROTATION_DEG"],
                    auto_rotation=auto_rotation,
                )
                return defaults, True


def configure_operating_mode(
    touch,
    lcd,
    user_params,
    user_file,
    auto_rotation=None,
):
    """Run mode/settings UI and return ``(params, selected_mode)``."""
    previous_mode = user_params["OPERATING_MODE"]
    while True:
        choice = select_operating_mode(touch, lcd, previous_mode)
        if choice is None:
            return user_params, previous_mode

        if choice == MENU_SETTINGS:
            user_params, restored = _run_settings(
                touch,
                lcd,
                user_params,
                user_file,
                auto_rotation=auto_rotation,
            )
            if restored:
                return user_params, MODE_TIMER
            previous_mode = user_params["OPERATING_MODE"]
            continue

        if choice not in OPERATING_MODES:
            continue
        updated, saved = persist_setting(
            user_file,
            user_params,
            "OPERATING_MODE",
            choice,
        )
        if not saved:
            return user_params, previous_mode
        return updated, choice
