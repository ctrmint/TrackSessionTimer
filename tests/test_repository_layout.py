import unittest
from pathlib import Path

from tools.deploy import (
    ENTRY_POINT,
    FIRMWARE_ROOT,
    REPOSITORY_ROOT,
    USER_CONFIG,
    deployment_commands,
    support_files,
)


class RepositoryLayoutTests(unittest.TestCase):
    def test_runtime_code_is_contained_in_firmware_directory(self):
        self.assertTrue(ENTRY_POINT.is_file())
        self.assertTrue((FIRMWARE_ROOT / "application.py").is_file())
        self.assertEqual([], sorted(REPOSITORY_ROOT.glob("*.py")))

    def test_deployment_payload_covers_runtime_assets_and_preserves_user(self):
        payload = set(support_files())
        expected = {
            path
            for path in FIRMWARE_ROOT.iterdir()
            if path.is_file()
            and path.suffix in {".py", ".json", ".bin", ".rgb565"}
            and path not in {ENTRY_POINT, USER_CONFIG}
        }

        self.assertEqual(expected, payload)
        self.assertNotIn(USER_CONFIG, payload)
        self.assertIn(USER_CONFIG, support_files(include_user=True))

    def test_deployment_copies_main_last_then_resets(self):
        support, entry_point, reset = deployment_commands(
            port="/dev/test",
            executable="python",
        )

        self.assertEqual(
            ["python", "-m", "mpremote", "connect", "/dev/test"],
            support[:5],
        )
        self.assertEqual(["fs", "cp"], support[5:7])
        self.assertEqual(":", support[-1])
        self.assertEqual(str(ENTRY_POINT), entry_point[-2])
        self.assertEqual(":", entry_point[-1])
        self.assertEqual("reset", reset[-1])


if __name__ == "__main__":
    unittest.main()
