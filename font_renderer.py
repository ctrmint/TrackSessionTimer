"""Memory-efficient proportional font rendering for MicroPython framebuffers."""

from font_data import (
    BITMAP_FILES,
    FIRST_CODE_POINT,
    LAST_CODE_POINT,
    OFFSETS,
    PIXEL_HEIGHTS,
    WIDTHS,
)

try:
    import framebuf
except ImportError:  # Host-side tests use a small scanline surface.
    framebuf = None


FALLBACK_INDEX = ord("?") - FIRST_CODE_POINT


def _size_index(size):
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size < 1
        or size > len(PIXEL_HEIGHTS)
    ):
        raise ValueError("Font size must be between 1 and {}".format(len(PIXEL_HEIGHTS)))
    return size - 1


def pixel_height(size):
    """Return the native pixel height represented by a UI font size."""
    return PIXEL_HEIGHTS[_size_index(size)]


def _glyph_index(character):
    code_point = ord(character)
    if code_point < FIRST_CODE_POINT or code_point > LAST_CODE_POINT:
        return FALLBACK_INDEX
    return code_point - FIRST_CODE_POINT


def measure_text(text, size):
    """Measure proportional text width without loading glyph pixels."""
    widths = WIDTHS[_size_index(size)]
    return sum(widths[_glyph_index(character)] for character in str(text))


def _glyph_offset(offsets, index):
    packed_index = index * 2
    return (offsets[packed_index] << 8) | offsets[packed_index + 1]


def _draw_scanlines(surface, bitmap, width, height, x, y, color):
    """Portable renderer used by host tests and non-framebuffer surfaces."""
    stride = (width + 7) // 8
    for row in range(height):
        row_offset = row * stride
        run_start = -1
        for column in range(width):
            source_byte = bitmap[row_offset + (column >> 3)]
            painted = source_byte & (0x80 >> (column & 7))
            if painted and run_start < 0:
                run_start = column
            elif not painted and run_start >= 0:
                surface.hline(x + run_start, y + row, column - run_start, color)
                run_start = -1
        if run_start >= 0:
            surface.hline(x + run_start, y + row, width - run_start, color)


def _blit_glyph(
    surface,
    bitmap,
    width,
    height,
    x,
    y,
    palette,
    transparent_key,
):
    glyph_buffer = bytearray(bitmap)
    # Generated rows are padded to whole bytes and store the left-most pixel in
    # bit 7. MicroPython needs an explicit padded stride and MONO_HLSB for that
    # memory layout (the format naming is counter-intuitive in modframebuf.c).
    stride = ((width + 7) // 8) * 8
    glyph = framebuf.FrameBuffer(
        glyph_buffer, width, height, framebuf.MONO_HLSB, stride,
    )
    surface.blit(glyph, x, y, transparent_key, palette)


def draw_text(surface, text, x, y, size, color):
    """Draw a pre-rasterized native-resolution font and return its width."""
    size_index = _size_index(size)
    height = PIXEL_HEIGHTS[size_index]
    widths = WIDTHS[size_index]
    offsets = OFFSETS[size_index]
    cursor = int(x)
    use_blitter = framebuf is not None and hasattr(surface, "blit")

    palette = None
    palette_buffer = None
    transparent_key = None
    if use_blitter:
        # A distinct palette value is required for transparency. Using black
        # as the key also discards black foreground glyphs after palette
        # mapping, which made configuration labels and prompts invisible.
        transparent_key = 1 if color != 1 else 2
        palette_buffer = bytearray(4)
        palette = framebuf.FrameBuffer(palette_buffer, 2, 1, framebuf.RGB565)
        palette.pixel(0, 0, transparent_key)
        palette.pixel(1, 0, color)

    with open(BITMAP_FILES[size_index], "rb") as bitmap_file:
        for character in str(text):
            index = _glyph_index(character)
            width = widths[index]
            glyph_size = ((width + 7) // 8) * height
            bitmap_file.seek(_glyph_offset(offsets, index))
            bitmap = bitmap_file.read(glyph_size)
            if len(bitmap) != glyph_size:
                raise OSError("Font bitmap is missing or truncated")

            if use_blitter:
                _blit_glyph(
                    surface,
                    bitmap,
                    width,
                    height,
                    cursor,
                    int(y),
                    palette,
                    transparent_key,
                )
            else:
                _draw_scanlines(surface, bitmap, width, height, cursor, int(y), color)
            cursor += width

    return cursor - int(x)


def draw_centered(surface, text, y, size, color):
    """Draw text horizontally centered within the framebuffer."""
    width = measure_text(text, size)
    x = (surface.width - width) // 2
    draw_text(surface, text, x, y, size, color)
    return x, width
