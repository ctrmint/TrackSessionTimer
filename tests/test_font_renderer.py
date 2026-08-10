import unittest
from pathlib import Path

import font_data
import font_renderer
from font_renderer import draw_centered, draw_text, measure_text, pixel_height


class FakeSurface:
    width = 240

    def __init__(self):
        self.lines = []

    def hline(self, x, y, width, color):
        self.lines.append((x, y, width, color))


class FakeFrameBufferModule:
    MONO_HLSB = 3
    RGB565 = 1

    def __init__(self):
        self.calls = []
        module = self

        class FrameBuffer:
            def __init__(self, *args):
                module.calls.append(args)

            def pixel(self, *args):
                pass

        self.FrameBuffer = FrameBuffer


class FakeBlitSurface(FakeSurface):
    def __init__(self):
        super().__init__()
        self.blits = []

    def blit(self, *args):
        self.blits.append(args)


class FontRendererTests(unittest.TestCase):
    def test_font_metadata_covers_printable_ascii(self):
        glyph_count = font_data.LAST_CODE_POINT - font_data.FIRST_CODE_POINT + 1
        self.assertEqual(95, glyph_count)
        self.assertEqual(len(font_data.PIXEL_HEIGHTS), len(font_data.WIDTHS))
        self.assertEqual(len(font_data.PIXEL_HEIGHTS), len(font_data.OFFSETS))

        for height, widths, offsets, bitmap_file, bitmap_size in zip(
            font_data.PIXEL_HEIGHTS,
            font_data.WIDTHS,
            font_data.OFFSETS,
            font_data.BITMAP_FILES,
            font_data.BITMAP_SIZES,
        ):
            with self.subTest(height=height):
                self.assertEqual(glyph_count, len(widths))
                self.assertEqual(glyph_count * 2, len(offsets))
                last_offset = (offsets[-2] << 8) | offsets[-1]
                last_stride = (widths[-1] + 7) // 8
                self.assertEqual(bitmap_size, last_offset + (last_stride * height))
                self.assertEqual(bitmap_size, Path(bitmap_file).stat().st_size)

    def test_sizes_are_native_pixel_heights(self):
        self.assertEqual(12, pixel_height(1))
        self.assertEqual(64, pixel_height(6))
        self.assertEqual(84, pixel_height(8))
        for invalid in (0, -1, 1.5, True, 9):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    pixel_height(invalid)

    def test_proportional_measurement_and_scaling(self):
        self.assertLess(measure_text("III", 3), measure_text("WWW", 3))
        self.assertLess(measure_text("Timer", 2), measure_text("Timer", 4))
        self.assertGreater(measure_text(" ", 2), 0)

    def test_tabular_times_keep_the_same_width_for_every_digit(self):
        widths = {
            measure_text(value, 7, tabular_digits=True)
            for value in ("00:00", "11:11", "24:57", "60:00", "88:88")
        }

        self.assertEqual(1, len(widths))
        self.assertNotEqual(measure_text("11:11", 7), measure_text("88:88", 7))

    def test_tabular_centering_keeps_time_origin_fixed(self):
        surface = FakeSurface()

        narrow = draw_centered(
            surface,
            "11:11",
            20,
            7,
            1,
            tabular_digits=True,
        )
        wide = draw_centered(
            surface,
            "88:88",
            20,
            7,
            1,
            tabular_digits=True,
        )

        self.assertEqual(narrow, wide)

    def test_draw_uses_single_pixel_scanlines(self):
        surface = FakeSurface()
        width = draw_text(surface, "8:15", 4, 7, 5, 0xFFFF)

        self.assertEqual(measure_text("8:15", 5), width)
        self.assertTrue(surface.lines)
        self.assertTrue(all(line[2] > 0 for line in surface.lines))
        self.assertGreaterEqual(min(line[1] for line in surface.lines), 7)
        self.assertLess(max(line[1] for line in surface.lines), 7 + pixel_height(5))

    def test_hardware_blit_uses_msb_first_bits_and_padded_stride(self):
        fake_framebuf = FakeFrameBufferModule()
        surface = FakeBlitSurface()
        original_framebuf = font_renderer.framebuf
        font_renderer.framebuf = fake_framebuf
        try:
            draw_text(surface, "A", 3, 4, 1, 0xFFFF)
        finally:
            font_renderer.framebuf = original_framebuf

        glyph_call = fake_framebuf.calls[-1]
        glyph_width = font_data.WIDTHS[0][ord("A") - font_data.FIRST_CODE_POINT]
        self.assertEqual(fake_framebuf.MONO_HLSB, glyph_call[3])
        self.assertEqual(((glyph_width + 7) // 8) * 8, glyph_call[4])
        self.assertEqual(1, len(surface.blits))

    def test_hardware_blit_does_not_treat_black_text_as_transparent(self):
        fake_framebuf = FakeFrameBufferModule()
        surface = FakeBlitSurface()
        original_framebuf = font_renderer.framebuf
        font_renderer.framebuf = fake_framebuf
        try:
            draw_text(surface, "Config", 3, 4, 1, 0)
        finally:
            font_renderer.framebuf = original_framebuf

        self.assertTrue(surface.blits)
        self.assertTrue(all(blit[3] != 0 for blit in surface.blits))

    def test_centering_uses_measured_width(self):
        surface = FakeSurface()
        x, width = draw_centered(surface, "Ready", 20, 5, 1)
        self.assertEqual((surface.width - width) // 2, x)
        self.assertEqual(measure_text("Ready", 5), width)

    def test_unknown_characters_use_fallback_glyph(self):
        self.assertEqual(measure_text("?", 2), measure_text("\u2603", 2))


if __name__ == "__main__":
    unittest.main()
