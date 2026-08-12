import json
import unittest
from pathlib import Path

from hardware_splash import run_startup_screens
from settings import DEFAULT_SYSTEM_PARAMS


RELEASE_VERSION = "4.4.0"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class FakeTouch:
    def __init__(self):
        self.boot_version = None
        self.hardware_lines = None

    def BootScreen(self, _lcd, version_number):
        self.boot_version = version_number

    def ControlScreen(self, _lcd, text_array, back_colour):
        self.hardware_lines = text_array
        self.hardware_background = back_colour


class ReleaseVersionTests(unittest.TestCase):
    def test_build_defaults_docs_and_both_startup_screens_report_release(self):
        with (REPOSITORY_ROOT / "firmware" / "params.json").open(
            encoding="utf-8"
        ) as source:
            params = json.load(source)
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        user_guide = (REPOSITORY_ROOT / "docs" / "USER_GUIDE.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(RELEASE_VERSION, params["VERSION"])
        self.assertEqual(RELEASE_VERSION, DEFAULT_SYSTEM_PARAMS["VERSION"])
        self.assertTrue(readme.startswith("# Track Session Timer - v" + RELEASE_VERSION))
        self.assertTrue(user_guide.startswith("# User Guide - v" + RELEASE_VERSION))

        touch = FakeTouch()
        run_startup_screens(
            touch,
            object(),
            firmware_version=params["VERSION"],
            startup_duration_sec=0,
            hardware_duration_sec=0,
            wait=lambda _lcd, _duration: None,
        )

        self.assertEqual(RELEASE_VERSION, touch.boot_version)
        self.assertIn(
            "Firmware v" + RELEASE_VERSION,
            [line[0] for line in touch.hardware_lines],
        )


if __name__ == "__main__":
    unittest.main()
