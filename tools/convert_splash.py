#!/usr/bin/env python3
"""Convert the supplied transparent artwork into the device splash format."""

import argparse
from pathlib import Path

DISPLAY_SIZE = 240
ARTWORK_MAX_WIDTH = 224
ARTWORK_MAX_HEIGHT = 150
ARTWORK_CENTER_Y = 115
BACKGROUND = (0, 0, 0, 255)


def compose_splash(source):
    """Center the source artwork inside the round display's safe area."""
    from PIL import Image

    artwork = source.convert("RGBA")
    scale = min(
        ARTWORK_MAX_WIDTH / artwork.width,
        ARTWORK_MAX_HEIGHT / artwork.height,
    )
    dimensions = (
        max(1, round(artwork.width * scale)),
        max(1, round(artwork.height * scale)),
    )
    artwork = artwork.resize(dimensions, Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (DISPLAY_SIZE, DISPLAY_SIZE), BACKGROUND)
    position = (
        (DISPLAY_SIZE - artwork.width) // 2,
        ARTWORK_CENTER_Y - (artwork.height // 2),
    )
    canvas.alpha_composite(artwork, position)
    return canvas.convert("RGB")


def to_framebuffer_bytes(image):
    """Encode the big-endian RGB565 byte stream expected by the GC9A01."""
    output = bytearray(image.width * image.height * 2)
    offset = 0
    for red, green, blue in image.getdata():
        value = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
        # FrameBuffer stores 16-bit values little-endian, while show() sends
        # the bytes directly over SPI. Writing the high byte first therefore
        # matches the byte-swapped values used by MicroPython's RGB565 API.
        output[offset] = value >> 8
        output[offset + 1] = value & 0xFF
        offset += 2
    return output


def main():
    from PIL import Image

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="source GIF, PNG, or JPEG")
    parser.add_argument("output", type=Path, help="output RGB565 framebuffer file")
    parser.add_argument(
        "--preview",
        type=Path,
        help="optional PNG preview of the composed 240x240 splash",
    )
    args = parser.parse_args()

    with Image.open(args.source) as source:
        splash = compose_splash(source)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(to_framebuffer_bytes(splash))
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        splash.save(args.preview)


if __name__ == "__main__":
    main()
