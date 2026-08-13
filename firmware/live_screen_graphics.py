"""Timer-only graphics kept out of the memory-sensitive startup path."""


MAXIMUM_G_LABEL = "MAX"
MAXIMUM_G_LABEL_Y = 45
MAXIMUM_G_LABEL_TEXT_SIZE = 1
MAXIMUM_G_VALUE_Y = 36
MAXIMUM_G_VALUE_TEXT_SIZE = 3
MAXIMUM_G_GAP = 8
PROGRESS_PHASE_Y = 18
PROGRESS_PHASE_TEXT_SIZE = 1
PROGRESS_RING_CENTRE = 120

# Packed x/y bytes keep the 37 perimeter points to 74 bytes on MicroPython.
PROGRESS_RING_POINTS = (
    b"\x78\x08\x8b\x0a\x9e\x0f\xb0\x17\xc0\x22\xce\x30"
    b"\xd9\x40\xe1\x52\xe6\x65\xe8\x78\xe6\x8b\xe1\x9e"
    b"\xd9\xb0\xce\xc0\xc0\xce\xb0\xd9\x9e\xe1\x8b\xe6"
    b"\x78\xe8\x65\xe6\x52\xe1\x40\xd9\x30\xce\x22\xc0"
    b"\x17\xb0\x0f\x9e\x0a\x8b\x08\x78\x0a\x65\x0f\x52"
    b"\x17\x40\x22\x30\x30\x22\x40\x17\x52\x0f\x65\x0a"
    b"\x78\x08"
)


def _toward_ring_centre(value):
    if value < PROGRESS_RING_CENTRE:
        return value + 1
    if value > PROGRESS_RING_CENTRE:
        return value - 1
    return value


def draw_progress_ring(lcd, visible_segments, colour):
    """Draw a thin clockwise perimeter arc without touching the text layout."""
    segment_count = (len(PROGRESS_RING_POINTS) // 2) - 1
    visible_segments = max(0, min(int(visible_segments), segment_count))
    for index in range(visible_segments):
        point_offset = index * 2
        start_x = PROGRESS_RING_POINTS[point_offset]
        start_y = PROGRESS_RING_POINTS[point_offset + 1]
        end_x = PROGRESS_RING_POINTS[point_offset + 2]
        end_y = PROGRESS_RING_POINTS[point_offset + 3]
        lcd.line(start_x, start_y, end_x, end_y, colour)
        lcd.line(
            _toward_ring_centre(start_x),
            _toward_ring_centre(start_y),
            _toward_ring_centre(end_x),
            _toward_ring_centre(end_y),
            colour,
        )


def maximum_g_parts(maximum_g):
    """Return a compact label and normalized value/unit for mixed-size text."""
    value = str(maximum_g)
    if value.startswith(MAXIMUM_G_LABEL):
        value = value[len(MAXIMUM_G_LABEL):]
    value = value.strip()
    while "  " in value:
        value = value.replace("  ", " ")
    return MAXIMUM_G_LABEL, value


def draw_maximum_g(lcd, maximum_g, colour):
    """Draw a small MAX label beside a larger, fixed-digit peak value."""
    label, value = maximum_g_parts(maximum_g)
    label_width = lcd.text_width(label, MAXIMUM_G_LABEL_TEXT_SIZE)
    value_width = lcd.text_width(
        value,
        MAXIMUM_G_VALUE_TEXT_SIZE,
        tabular_digits=True,
    )
    total_width = label_width + MAXIMUM_G_GAP + value_width
    label_x = (lcd.width - total_width) // 2
    value_x = label_x + label_width + MAXIMUM_G_GAP
    lcd.write_text(
        label,
        label_x,
        MAXIMUM_G_LABEL_Y,
        MAXIMUM_G_LABEL_TEXT_SIZE,
        colour,
    )
    lcd.write_text(
        value,
        value_x,
        MAXIMUM_G_VALUE_Y,
        MAXIMUM_G_VALUE_TEXT_SIZE,
        colour,
        tabular_digits=True,
    )


def draw_live_overlays(
    lcd,
    colour,
    progress_segments=None,
    phase_label=None,
    maximum_g=None,
):
    """Draw optional session overlays after Timer Mode has been loaded."""
    if progress_segments is not None:
        draw_progress_ring(lcd, progress_segments, colour)
    if phase_label is not None:
        lcd.write_time_centered(
            phase_label,
            PROGRESS_PHASE_Y,
            PROGRESS_PHASE_TEXT_SIZE,
            colour,
        )
    if maximum_g is not None:
        draw_maximum_g(lcd, maximum_g, colour)
