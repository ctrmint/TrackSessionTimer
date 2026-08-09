"""Touch-driven configuration editors with injected display dependencies."""


CONFIGURATION_PROMPTS = (
    ("Swipe L/R to change", None, 205, 1, "black"),
    ("Swipe UP: save", None, 222, 1, "black"),
)


def _with_prompts(text_array):
    return text_array + list(CONFIGURATION_PROMPTS)


def _selected_index(values, current):
    if not values:
        raise ValueError("At least one selectable value is required")
    try:
        return values.index(current)
    except ValueError:
        return 0


def set_sensitivity(LCD=None, Touch=None, sensitivity_values=None, sensitivity=0,
                    operation="Config", back_colour="palegreen"):
    """Select launch sensitivity, starting from the current saved value."""
    values = list(sensitivity_values or [])
    index = _selected_index(values, sensitivity)

    def draw():
        text_array = _with_prompts(
            [
                [str(values[index]), None, 80, 5, "white"],
                ["Launch", None, 145, 2, "black"],
                ["Sensitivity", None, 175, 2, "black"],
                [operation, None, 35, 2, "black"],
            ]
        )
        Touch.ControlScreen(LCD, text_array=text_array, back_colour=back_colour)

    draw()
    while True:
        gesture = Touch.GetGesture(LCD)
        if gesture == "up":
            return values[index]
        if gesture == "left":
            index = (index - 1) % len(values)
            draw()
        elif gesture == "right":
            index = (index + 1) % len(values)
            draw()


def set_session(LCD=None, Touch=None, session=None, session_values=None,
                session_name=None, operation="Config", back_colour="palegreen"):
    """Select a session duration, starting from the session's current value."""
    values = list(session_values or [])
    current = getattr(session, "duration_mins", None)
    index = _selected_index(values, current)

    def draw():
        text_array = _with_prompts(
            [
                [str(values[index]), None, 90, 5, "white"],
                [session_name, None, 180, 2, "black"],
                [operation, None, 35, 2, "black"],
            ]
        )
        Touch.ControlScreen(LCD, text_array=text_array, back_colour=back_colour)

    draw()
    while True:
        gesture = Touch.GetGesture(LCD)
        if gesture == "up":
            session.duration_mins = values[index]
            return session.duration_mins
        if gesture == "left":
            index = (index - 1) % len(values)
            draw()
        elif gesture == "right":
            index = (index + 1) % len(values)
            draw()
