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
            {"SENSITIVITY": 0.5, "RACE_LENGTH": 10, "REST_LENGTH": 15},
            normalized,
        )

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
