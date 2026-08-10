"""On-device operating-mode and settings menus."""

from settings import (
    BRIGHTNESS_VALUES,
    DEFAULT_USER_PARAMS,
    DISPLAY_ROTATION_VALUES,
    OPERATING_MODES,
    persist_setting,
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


def settings_menu_lines(index):
    label = SETTINGS_CHOICES[index][0]
    position = "{} / {}".format(index + 1, len(SETTINGS_CHOICES))
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


def select_settings_action(touch, lcd):
    return _select_choice(
        touch,
        lcd,
        SETTINGS_CHOICES,
        settings_menu_lines,
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


def apply_rotation(lcd, touch, degrees):
    """Apply one mount angle to rendering and directional gestures."""
    lcd.set_rotation(degrees)
    touch.Set_Rotation(degrees)


def rotation_lines(degrees):
    return [
        ["Mount rotation", None, 35, 2, "white"],
        ["{} deg".format(degrees), None, 88, 4, "white"],
        ["Device clockwise", None, 150, 1, "white"],
        ["L/R: rotate", None, 180, 1, "white"],
        ["UP: save", None, 202, 1, "white"],
        ["DOWN: cancel", None, 220, 1, "white"],
    ]


def select_rotation(touch, lcd, current):
    """Preview mount rotations and return ``(value, should_save)``."""
    values = list(DISPLAY_ROTATION_VALUES)
    try:
        index = values.index(current)
    except ValueError:
        index = values.index(DEFAULT_USER_PARAMS["DISPLAY_ROTATION_DEG"])
    original = values[index]

    def draw():
        apply_rotation(lcd, touch, values[index])
        touch.ControlScreen(
            lcd,
            text_array=rotation_lines(values[index]),
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
            apply_rotation(lcd, touch, original)
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


def _run_settings(touch, lcd, user_params, user_file):
    while True:
        action = select_settings_action(touch, lcd)
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
            selected, should_save = select_rotation(touch, lcd, previous)
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
                apply_rotation(lcd, touch, previous)

        elif action == "restore" and confirm_restore_defaults(touch, lcd):
            defaults, saved = restore_user_defaults(user_file)
            if saved:
                apply_brightness(lcd, defaults["BRIGHTNESS_PERCENT"])
                apply_rotation(
                    lcd,
                    touch,
                    defaults["DISPLAY_ROTATION_DEG"],
                )
                return defaults, True


def configure_operating_mode(touch, lcd, user_params, user_file):
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
