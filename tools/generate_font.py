#!/usr/bin/env python3
"""Generate the compact 1-bit font module used by the Pico firmware."""

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FIRST_CODE_POINT = 32
LAST_CODE_POINT = 126
SOURCE_SIZE = 96
THRESHOLD = 96
PIXEL_HEIGHTS = (12, 20, 30, 44, 54, 64, 74, 84)


def _pack_bitmap(image):
    width, height = image.size
    stride = (width + 7) // 8
    bitmap = bytearray()
    for y in range(height):
        row = bytearray(stride)
        for x in range(width):
            if image.getpixel((x, y)) >= THRESHOLD:
                row[x >> 3] |= 0x80 >> (x & 7)
        bitmap.extend(row)
    return bitmap


def generate(font_path):
    font = ImageFont.truetype(str(font_path), SOURCE_SIZE)
    characters = [chr(code) for code in range(FIRST_CODE_POINT, LAST_CODE_POINT + 1)]
    bounds = [font.getbbox(character) for character in characters]
    top = min(bound[1] for bound in bounds)
    bottom = max(bound[3] for bound in bounds)
    source_height = bottom - top
    source_glyphs = []

    for character, bound in zip(characters, bounds):
        left = min(0, bound[0])
        right = max(float(bound[2]), font.getlength(character))
        width = max(1, int(math.ceil(right - left)))
        image = Image.new("L", (width, source_height), 0)
        draw = ImageDraw.Draw(image)
        draw.text((-left, -top), character, font=font, fill=255)
        source_glyphs.append(image)

    generated = []
    for target_height in PIXEL_HEIGHTS:
        widths = bytearray()
        offsets = bytearray()
        bitmaps = bytearray()

        for source_glyph in source_glyphs:
            target_width = max(
                1,
                int(round(source_glyph.width * target_height / source_height)),
            )
            glyph = source_glyph.resize(
                (target_width, target_height),
                Image.Resampling.LANCZOS,
            )
            widths.append(target_width)
            offset = len(bitmaps)
            offsets.extend((offset >> 8, offset & 0xFF))
            bitmaps.extend(_pack_bitmap(glyph))

        generated.append((target_height, bytes(widths), bytes(offsets), bytes(bitmaps)))

    return generated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("font", type=Path, help="source OpenType or TrueType font")
    parser.add_argument("output", type=Path, help="generated MicroPython module")
    args = parser.parse_args()

    generated = generate(args.font)
    bitmap_files = []
    bitmap_sizes = []
    widths = []
    offsets = []
    for height, size_widths, size_offsets, bitmaps in generated:
        if height == 64:
            bitmap_path = args.output.with_suffix(".bin")
        else:
            bitmap_path = args.output.with_name(
                "{}_{}.bin".format(args.output.stem, height),
            )
        bitmap_path.write_bytes(bitmaps)
        bitmap_files.append(bitmap_path.name)
        bitmap_sizes.append(len(bitmaps))
        widths.append(size_widths)
        offsets.append(size_offsets)

    module = '''"""Generated TrackTimer Sans metadata.

Derived from Montserrat SemiBold, Copyright 2024 The Montserrat.Git Project
Authors. Licensed under the SIL Open Font License 1.1; see
../FONT_LICENSE.txt in the source repository.
Regenerate with ``tools/generate_font.py`` rather than editing this file.
"""

FIRST_CODE_POINT = {first}
LAST_CODE_POINT = {last}
PIXEL_HEIGHTS = {pixel_heights!r}
WIDTHS = {widths!r}
OFFSETS = {offsets!r}
BITMAP_FILES = {bitmap_files!r}
BITMAP_SIZES = {bitmap_sizes!r}
'''.format(
        first=FIRST_CODE_POINT,
        last=LAST_CODE_POINT,
        pixel_heights=PIXEL_HEIGHTS,
        widths=tuple(widths),
        offsets=tuple(offsets),
        bitmap_files=tuple(bitmap_files),
        bitmap_sizes=tuple(bitmap_sizes),
    )
    args.output.write_text(module, encoding="utf-8")


if __name__ == "__main__":
    main()
