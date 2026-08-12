"""Shared display and touch orientation helpers."""


ROTATION_VALUES = (0, 90, 180, 270)

# The native Waveshare initialization uses MY, ML, and BGR (0x98).  The
# remaining values counter-rotate the display for a device mounted clockwise
# by the corresponding number of degrees while preserving ML and BGR.
MADCTL_BY_MOUNT_ROTATION = {
    0: 0x98,
    90: 0xF8,
    180: 0x58,
    270: 0x38,
}

_DIRECTIONS_CLOCKWISE = ("up", "right", "down", "left")


def validate_rotation(rotation):
    """Return a supported clockwise mount rotation or raise ``ValueError``."""
    if isinstance(rotation, bool) or rotation not in ROTATION_VALUES:
        raise ValueError("Rotation must be 0, 90, 180, or 270 degrees")
    return rotation


def madctl_for_rotation(rotation):
    """Return the GC9A01 MADCTL value for a clockwise mount rotation."""
    return MADCTL_BY_MOUNT_ROTATION[validate_rotation(rotation)]


def map_gesture_direction(direction, rotation):
    """Map a board-relative gesture to the viewer at ``rotation`` degrees."""
    validate_rotation(rotation)
    if direction not in _DIRECTIONS_CLOCKWISE:
        return direction
    index = _DIRECTIONS_CLOCKWISE.index(direction)
    steps = rotation // 90
    return _DIRECTIONS_CLOCKWISE[(index + steps) % 4]
