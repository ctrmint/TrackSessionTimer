import tempfile
import unittest
from pathlib import Path

from splash import load_splash
from tools.convert_splash import to_framebuffer_bytes


class FakeSurface:
    def __init__(self, size=32, value=0):
        self.buffer = bytearray([value] * size)


class FakeImage:
    width = 3
    height = 1

    def getdata(self):
        return [(255, 0, 0), (0, 255, 0), (0, 0, 255)]


class SplashTests(unittest.TestCase):
    def test_converter_uses_gc9a01_rgb565_byte_order(self):
        self.assertEqual(
            bytes((0xF8, 0x00, 0x07, 0xE0, 0x00, 0x1F)),
            to_framebuffer_bytes(FakeImage()),
        )

    def test_loads_exact_asset_into_existing_buffer(self):
        expected = bytes(range(32))
        surface = FakeSurface()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "splash.rgb565"
            path.write_bytes(expected)

            self.assertTrue(load_splash(surface, str(path)))

        self.assertEqual(expected, surface.buffer)

    def test_missing_asset_returns_false_without_changing_buffer(self):
        surface = FakeSurface(value=7)

        self.assertFalse(load_splash(surface, "/missing/splash.rgb565"))

        self.assertEqual(bytes([7] * 32), surface.buffer)

    def test_wrong_sized_asset_returns_false_without_changing_buffer(self):
        surface = FakeSurface(value=9)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "splash.rgb565"
            path.write_bytes(bytes(range(31)))

            self.assertFalse(load_splash(surface, str(path)))

        self.assertEqual(bytes([9] * 32), surface.buffer)

    def test_generated_device_asset_matches_framebuffer_size(self):
        asset = Path(__file__).parents[1] / "firmware" / "startup_splash.rgb565"

        self.assertEqual(240 * 240 * 2, asset.stat().st_size)


if __name__ == "__main__":
    unittest.main()
