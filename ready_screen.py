"""Ready-screen settings summary independent of display hardware."""


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
        ["Ready", None, 38, 4, "white"],
        ["Track {}m".format(track_minutes), None, 100, 2, "black"],
        ["Rest {}m".format(rest_minutes), None, 130, 2, "black"],
        [launch_status(sensitivity, imu_available), None, 160, 2, "black"],
        ["Swipe DOWN to start", None, 205, 1, "black"],
    ]
