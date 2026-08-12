import json
import os
import tempfile
import unittest
from unittest.mock import patch

import settings as settings_module
from settings import (
    DEFAULT_SYSTEM_PARAMS,
    DEFAULT_USER_PARAMS,
    file_in,
    file_out,
    load_configuration,
    normalize_user_params,
    persist_setting,
    persist_settings,
    restore_user_defaults,
    update_json,
    validate_system_params,
)


class SettingsTests(unittest.TestCase):
    def test_update_json_accepts_zero_without_mutating_source(self):
        original = {"SENSITIVITY": 2, "RACE_LENGTH": 20, "REST_LENGTH": 20}
        updated = update_json(original, "SENSITIVITY", 0)
        self.assertEqual(0, updated["SENSITIVITY"])
        self.assertEqual(2, original["SENSITIVITY"])
        self.assertEqual({"SENSITIVITY": 0}, update_json({}, "SENSITIVITY", 0))

    def test_enable_disable_and_reload_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            settings = dict(DEFAULT_USER_PARAMS)
            settings, saved = persist_setting(path, settings, "SENSITIVITY", 2, debug=False)
            self.assertTrue(saved)
            settings, saved = persist_setting(path, settings, "SENSITIVITY", 0, debug=False)
            self.assertTrue(saved)
            self.assertEqual(0, file_in(path, debug=False)["SENSITIVITY"])

    def test_failed_persist_retains_known_good_dictionary(self):
        settings = dict(DEFAULT_USER_PARAMS)
        updated, saved = persist_setting(
            "/path/that/does/not/exist/user.json",
            settings,
            "SENSITIVITY",
            2,
            debug=False,
        )
        self.assertFalse(saved)
        self.assertIs(settings, updated)

    def test_multiple_settings_are_persisted_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            settings = dict(DEFAULT_USER_PARAMS)

            updated, saved = persist_settings(
                path,
                settings,
                {
                    "AVG_LAP_TIME_SECONDS": 90,
                    "TRACK_LOWER_DISPLAY": "laps_remaining",
                },
                debug=False,
            )

            self.assertTrue(saved)
            self.assertEqual(90, updated["AVG_LAP_TIME_SECONDS"])
            self.assertEqual(
                "laps_remaining",
                file_in(path, debug=False)["TRACK_LOWER_DISPLAY"],
            )

    def test_serialization_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            self.assertTrue(file_out(path, DEFAULT_USER_PARAMS, debug=False))
            self.assertFalse(file_out(path, {"invalid": object()}, debug=False))
            self.assertEqual(DEFAULT_USER_PARAMS, file_in(path, debug=False))
            self.assertFalse(os.path.exists(path + ".tmp"))

    def test_backup_rename_fallback_replaces_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            self.assertTrue(file_out(path, DEFAULT_USER_PARAMS, debug=False))
            updated = dict(DEFAULT_USER_PARAMS)
            updated["RACE_LENGTH"] = 10
            with patch.object(settings_module.os, "replace", None):
                self.assertTrue(file_out(path, updated, debug=False))
            self.assertEqual(updated, file_in(path, debug=False))
            self.assertFalse(os.path.exists(path + ".bak"))

    def test_malformed_primary_recovers_from_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            with open(path, "w", encoding="utf-8") as target:
                target.write("{")
            with open(path + ".bak", "w", encoding="utf-8") as target:
                json.dump(DEFAULT_USER_PARAMS, target)
            self.assertEqual(DEFAULT_USER_PARAMS, file_in(path, debug=False))
            os.remove(path + ".bak")
            self.assertEqual(DEFAULT_USER_PARAMS, file_in(path, debug=False))

    def test_missing_and_truncated_user_files_are_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            params_path = os.path.join(directory, "params.json")
            user_path = os.path.join(directory, "user.json")
            self.assertTrue(file_out(params_path, DEFAULT_SYSTEM_PARAMS, debug=False))

            _, user = load_configuration(params_path, user_path, debug=False)
            self.assertEqual(DEFAULT_USER_PARAMS, user)
            self.assertEqual(DEFAULT_USER_PARAMS, file_in(user_path, debug=False))

            with open(user_path, "w", encoding="utf-8") as target:
                target.write("{")
            _, user = load_configuration(params_path, user_path, debug=False)
            self.assertEqual(DEFAULT_USER_PARAMS, user)
            self.assertEqual(DEFAULT_USER_PARAMS, file_in(user_path, debug=False))

    def test_invalid_system_params_use_known_defaults(self):
        params, valid = validate_system_params({"DURATION_VALUES": []})
        self.assertFalse(valid)
        self.assertEqual(DEFAULT_SYSTEM_PARAMS, params)

        invalid_colour = dict(DEFAULT_SYSTEM_PARAMS)
        invalid_colour["DISPLAY_DELAY_REST_COLOUR"] = "not-a-colour"
        params, valid = validate_system_params(invalid_colour)
        self.assertFalse(valid)
        self.assertEqual(DEFAULT_SYSTEM_PARAMS, params)

        invalid_hold = dict(DEFAULT_SYSTEM_PARAMS)
        invalid_hold["MODE_MENU_HOLD_SEC"] = 0
        params, valid = validate_system_params(invalid_hold)
        self.assertFalse(valid)
        self.assertEqual(DEFAULT_SYSTEM_PARAMS, params)

        for duration_key in (
            "STARTUP_SPLASH_DURATION_SEC",
            "HARDWARE_SPLASH_DURATION_SEC",
        ):
            with self.subTest(duration_key=duration_key):
                invalid_duration = dict(DEFAULT_SYSTEM_PARAMS)
                invalid_duration[duration_key] = -1
                params, valid = validate_system_params(invalid_duration)
                self.assertFalse(valid)
                self.assertEqual(DEFAULT_SYSTEM_PARAMS, params)

    def test_splash_durations_default_to_two_seconds(self):
        self.assertEqual(2, DEFAULT_SYSTEM_PARAMS["STARTUP_SPLASH_DURATION_SEC"])
        self.assertEqual(2, DEFAULT_SYSTEM_PARAMS["HARDWARE_SPLASH_DURATION_SEC"])

    def test_existing_system_file_gains_default_mode_hold_duration(self):
        legacy = dict(DEFAULT_SYSTEM_PARAMS)
        del legacy["MODE_MENU_HOLD_SEC"]

        params, valid = validate_system_params(legacy)

        self.assertTrue(valid)
        self.assertEqual(5, params["MODE_MENU_HOLD_SEC"])

    def test_existing_system_file_gains_default_auto_dim_percentage(self):
        legacy = dict(DEFAULT_SYSTEM_PARAMS)
        del legacy["AUTO_DIM_PERCENT"]

        params, valid = validate_system_params(legacy)

        self.assertTrue(valid)
        self.assertEqual(25, params["AUTO_DIM_PERCENT"])

    def test_auto_dim_percentage_must_be_an_integer_from_one_to_one_hundred(self):
        for percentage in (1, 25, 100):
            with self.subTest(percentage=percentage):
                configured = dict(DEFAULT_SYSTEM_PARAMS)
                configured["AUTO_DIM_PERCENT"] = percentage
                params, valid = validate_system_params(configured)
                self.assertTrue(valid)
                self.assertEqual(percentage, params["AUTO_DIM_PERCENT"])

        for invalid in (0, 101, 25.0, True, "25", None):
            with self.subTest(invalid=invalid):
                configured = dict(DEFAULT_SYSTEM_PARAMS)
                configured["AUTO_DIM_PERCENT"] = invalid
                params, valid = validate_system_params(configured)
                self.assertFalse(valid)
                self.assertEqual(DEFAULT_SYSTEM_PARAMS, params)

    def test_legacy_boot_delay_is_migrated(self):
        legacy = dict(DEFAULT_SYSTEM_PARAMS)
        del legacy["STARTUP_SPLASH_DURATION_SEC"]
        del legacy["HARDWARE_SPLASH_DURATION_SEC"]
        legacy["BOOT_DELAY_SEC"] = 1.5

        params, valid = validate_system_params(legacy)

        self.assertTrue(valid)
        self.assertEqual(1.5, params["STARTUP_SPLASH_DURATION_SEC"])
        self.assertEqual(2, params["HARDWARE_SPLASH_DURATION_SEC"])
        self.assertNotIn("BOOT_DELAY_SEC", params)

    def test_missing_and_out_of_range_user_values_use_defaults(self):
        normalized, changed = normalize_user_params(None, DEFAULT_SYSTEM_PARAMS)
        self.assertTrue(changed)
        self.assertEqual(DEFAULT_USER_PARAMS, normalized)

        normalized, changed = normalize_user_params(
            {"SENSITIVITY": False, "RACE_LENGTH": True, "REST_LENGTH": 20.0},
            DEFAULT_SYSTEM_PARAMS,
        )
        self.assertTrue(changed)
        self.assertEqual(DEFAULT_USER_PARAMS, normalized)

        normalized, changed = normalize_user_params(
            {"SENSITIVITY": 99, "RACE_LENGTH": -1, "REST_LENGTH": "20"},
            DEFAULT_SYSTEM_PARAMS,
        )
        self.assertTrue(changed)
        self.assertEqual(DEFAULT_USER_PARAMS, normalized)

    def test_legacy_user_keys_are_migrated_and_removed(self):
        normalized, changed = normalize_user_params(
            {"SENSITIVITY": 0.5, "TRACK_LENGTH": 10, "REST_SESSION_LENGTH": 15},
            DEFAULT_SYSTEM_PARAMS,
        )
        self.assertTrue(changed)
        self.assertEqual(
            {
                "SENSITIVITY": 0.5,
                "RACE_LENGTH": 10,
                "REST_LENGTH": 15,
                "OPERATING_MODE": "timer",
                "BRIGHTNESS_PERCENT": 100,
                "DISPLAY_ROTATION_DEG": 0,
                "AUTO_DIM_ENABLED": False,
                "AVG_LAP_TIME_SECONDS": 0,
                "TRACK_LOWER_DISPLAY": "elapsed",
            },
            normalized,
        )

    def test_existing_user_file_gains_all_new_setting_defaults(self):
        normalized, changed = normalize_user_params(
            {"SENSITIVITY": 0, "RACE_LENGTH": 10, "REST_LENGTH": 15},
            DEFAULT_SYSTEM_PARAMS,
        )

        self.assertTrue(changed)
        self.assertEqual("timer", normalized["OPERATING_MODE"])
        self.assertEqual(100, normalized["BRIGHTNESS_PERCENT"])
        self.assertEqual(0, normalized["DISPLAY_ROTATION_DEG"])
        self.assertFalse(normalized["AUTO_DIM_ENABLED"])
        self.assertEqual(0, normalized["AVG_LAP_TIME_SECONDS"])
        self.assertEqual("elapsed", normalized["TRACK_LOWER_DISPLAY"])

    def test_invalid_mode_and_brightness_use_defaults(self):
        invalid = dict(DEFAULT_USER_PARAMS)
        invalid["OPERATING_MODE"] = "unsupported"
        invalid["BRIGHTNESS_PERCENT"] = 42

        normalized, changed = normalize_user_params(
            invalid,
            DEFAULT_SYSTEM_PARAMS,
        )

        self.assertTrue(changed)
        self.assertEqual("timer", normalized["OPERATING_MODE"])
        self.assertEqual(100, normalized["BRIGHTNESS_PERCENT"])

    def test_auto_dim_accepts_only_boolean_values(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                user = dict(DEFAULT_USER_PARAMS)
                user["AUTO_DIM_ENABLED"] = enabled
                normalized, changed = normalize_user_params(
                    user,
                    DEFAULT_SYSTEM_PARAMS,
                )
                self.assertFalse(changed)
                self.assertIs(enabled, normalized["AUTO_DIM_ENABLED"])

        for invalid in (0, 1, "on", None):
            with self.subTest(invalid=invalid):
                user = dict(DEFAULT_USER_PARAMS)
                user["AUTO_DIM_ENABLED"] = invalid
                normalized, changed = normalize_user_params(
                    user,
                    DEFAULT_SYSTEM_PARAMS,
                )
                self.assertTrue(changed)
                self.assertFalse(normalized["AUTO_DIM_ENABLED"])

    def test_average_lap_time_accepts_only_bounded_integer_seconds(self):
        for seconds in (0, 1, 62, 3599):
            with self.subTest(seconds=seconds):
                user = dict(DEFAULT_USER_PARAMS)
                user["AVG_LAP_TIME_SECONDS"] = seconds
                normalized, changed = normalize_user_params(
                    user,
                    DEFAULT_SYSTEM_PARAMS,
                )
                self.assertFalse(changed)
                self.assertEqual(seconds, normalized["AVG_LAP_TIME_SECONDS"])

        for invalid in (-1, 3600, True, 90.0, "90", None):
            with self.subTest(invalid=invalid):
                user = dict(DEFAULT_USER_PARAMS)
                user["AVG_LAP_TIME_SECONDS"] = invalid
                normalized, changed = normalize_user_params(
                    user,
                    DEFAULT_SYSTEM_PARAMS,
                )
                self.assertTrue(changed)
                self.assertEqual(0, normalized["AVG_LAP_TIME_SECONDS"])

    def test_laps_remaining_display_requires_a_configured_average(self):
        user = dict(DEFAULT_USER_PARAMS)
        user["AVG_LAP_TIME_SECONDS"] = 90
        user["TRACK_LOWER_DISPLAY"] = "laps_remaining"

        normalized, changed = normalize_user_params(
            user,
            DEFAULT_SYSTEM_PARAMS,
        )

        self.assertFalse(changed)
        self.assertEqual(
            "laps_remaining",
            normalized["TRACK_LOWER_DISPLAY"],
        )

        for average in (0, -1):
            with self.subTest(average=average):
                user["AVG_LAP_TIME_SECONDS"] = average
                normalized, changed = normalize_user_params(
                    user,
                    DEFAULT_SYSTEM_PARAMS,
                )
                self.assertTrue(changed)
                self.assertEqual("elapsed", normalized["TRACK_LOWER_DISPLAY"])

    def test_invalid_lower_display_values_use_elapsed_default(self):
        for invalid in (None, True, "laps", "count_up", 1):
            with self.subTest(invalid=invalid):
                user = dict(DEFAULT_USER_PARAMS)
                user["AVG_LAP_TIME_SECONDS"] = 90
                user["TRACK_LOWER_DISPLAY"] = invalid
                normalized, changed = normalize_user_params(
                    user,
                    DEFAULT_SYSTEM_PARAMS,
                )
                self.assertTrue(changed)
                self.assertEqual("elapsed", normalized["TRACK_LOWER_DISPLAY"])

    def test_rotation_accepts_auto_and_four_angles(self):
        for rotation in (0, 90, 180, 270, "auto"):
            with self.subTest(rotation=rotation):
                user = dict(DEFAULT_USER_PARAMS)
                user["DISPLAY_ROTATION_DEG"] = rotation
                normalized, changed = normalize_user_params(
                    user,
                    DEFAULT_SYSTEM_PARAMS,
                )
                self.assertFalse(changed)
                self.assertEqual(rotation, normalized["DISPLAY_ROTATION_DEG"])

        for invalid in (True, 45, 360, "90", "automatic"):
            with self.subTest(invalid=invalid):
                user = dict(DEFAULT_USER_PARAMS)
                user["DISPLAY_ROTATION_DEG"] = invalid
                normalized, changed = normalize_user_params(
                    user,
                    DEFAULT_SYSTEM_PARAMS,
                )
                self.assertTrue(changed)
                self.assertEqual(0, normalized["DISPLAY_ROTATION_DEG"])

    def test_restore_user_defaults_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "user.json")
            changed = dict(DEFAULT_USER_PARAMS)
            changed["OPERATING_MODE"] = "g"
            changed["BRIGHTNESS_PERCENT"] = 25
            self.assertTrue(file_out(path, changed, debug=False))

            defaults, saved = restore_user_defaults(path, debug=False)

            self.assertTrue(saved)
            self.assertEqual(DEFAULT_USER_PARAMS, defaults)
            self.assertEqual(DEFAULT_USER_PARAMS, file_in(path, debug=False))

    def test_documented_configuration_loads_and_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            params_path = os.path.join(directory, "params.json")
            user_path = os.path.join(directory, "user.json")
            self.assertTrue(file_out(params_path, DEFAULT_SYSTEM_PARAMS, debug=False))
            self.assertTrue(file_out(user_path, DEFAULT_USER_PARAMS, debug=False))
            system, user = load_configuration(params_path, user_path, debug=False)
            self.assertEqual(DEFAULT_SYSTEM_PARAMS, system)
            self.assertEqual(DEFAULT_USER_PARAMS, user)


if __name__ == "__main__":
    unittest.main()
