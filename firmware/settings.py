"""Configuration loading, validation, migration, and persistence helpers."""

import json

try:
    import uos as os
except ImportError:  # CPython
    import os


DEFAULT_SYSTEM_PARAMS = {
    "DURATION_VALUES": [1, 5, 10, 15, 20, 25, 30, 40, 50, 60],
    "DISPLAY_DELAY_REST": 5,
    "LAUNCH_SENSE_VALUES": [0, 0.5, 1, 1.25, 1.5, 1.75, 2, 2.5, 3.5, 4],
    "VERSION": "4.3.0",
    "DISPLAY_DELAY_REST_COLOUR": "blue",
    "STARTUP_SPLASH_DURATION_SEC": 2,
    "HARDWARE_SPLASH_DURATION_SEC": 2,
    "MODE_MENU_HOLD_SEC": 5,
    "AUTO_DIM_PERCENT": 25,
}

DEFAULT_USER_PARAMS = {
    "SENSITIVITY": 0,
    "RACE_LENGTH": 20,
    "REST_LENGTH": 20,
    "OPERATING_MODE": "timer",
    "BRIGHTNESS_PERCENT": 100,
    "DISPLAY_ROTATION_DEG": 0,
    "AUTO_DIM_ENABLED": False,
    "AVG_LAP_TIME_SECONDS": 0,
}

OPERATING_MODES = ("timer", "g")
BRIGHTNESS_VALUES = (25, 50, 75, 100)
DISPLAY_ROTATION_VALUES = (0, 90, 180, 270, "auto")
MAX_AVG_LAP_TIME_SECONDS = (60 * 60) - 1

LEGACY_USER_KEYS = {
    "TRACK_LENGTH": "RACE_LENGTH",
    "TRACK_SESSION_LENGTH": "RACE_LENGTH",
    "REST_SESSION_LENGTH": "REST_LENGTH",
}

DISPLAY_COLOURS = (
    "green",
    "palegreen",
    "blue",
    "paleblue",
    "red",
    "white",
    "brown",
    "black",
    "lilac",
    "testcolour",
)


def _copy_params(params):
    copied = {}
    for key, value in params.items():
        copied[key] = list(value) if isinstance(value, list) else value
    return copied


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _positive_int_list(value):
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(
            isinstance(item, int) and not isinstance(item, bool) and item > 0
            for item in value
        )
    )


def _non_negative_number_list(value):
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(_is_number(item) and item >= 0 for item in value)
    )


def validate_system_params(data):
    """Return ``(params, valid)`` using built-in defaults for invalid input."""
    if not isinstance(data, dict):
        return _copy_params(DEFAULT_SYSTEM_PARAMS), False

    source = dict(data)
    if (
        "STARTUP_SPLASH_DURATION_SEC" not in source
        and "BOOT_DELAY_SEC" in source
    ):
        source["STARTUP_SPLASH_DURATION_SEC"] = source["BOOT_DELAY_SEC"]
    if "HARDWARE_SPLASH_DURATION_SEC" not in source:
        source["HARDWARE_SPLASH_DURATION_SEC"] = DEFAULT_SYSTEM_PARAMS[
            "HARDWARE_SPLASH_DURATION_SEC"
        ]
    if "MODE_MENU_HOLD_SEC" not in source:
        source["MODE_MENU_HOLD_SEC"] = DEFAULT_SYSTEM_PARAMS[
            "MODE_MENU_HOLD_SEC"
        ]
    if "AUTO_DIM_PERCENT" not in source:
        source["AUTO_DIM_PERCENT"] = DEFAULT_SYSTEM_PARAMS[
            "AUTO_DIM_PERCENT"
        ]

    valid = (
        _positive_int_list(source.get("DURATION_VALUES"))
        and _non_negative_number_list(source.get("LAUNCH_SENSE_VALUES"))
        and _is_number(source.get("DISPLAY_DELAY_REST"))
        and source.get("DISPLAY_DELAY_REST") >= 0
        and _is_number(source.get("STARTUP_SPLASH_DURATION_SEC"))
        and source.get("STARTUP_SPLASH_DURATION_SEC") >= 0
        and _is_number(source.get("HARDWARE_SPLASH_DURATION_SEC"))
        and source.get("HARDWARE_SPLASH_DURATION_SEC") >= 0
        and _is_number(source.get("MODE_MENU_HOLD_SEC"))
        and source.get("MODE_MENU_HOLD_SEC") > 0
        and isinstance(source.get("AUTO_DIM_PERCENT"), int)
        and not isinstance(source.get("AUTO_DIM_PERCENT"), bool)
        and 1 <= source.get("AUTO_DIM_PERCENT") <= 100
        and isinstance(source.get("VERSION"), str)
        and len(source.get("VERSION")) > 0
        and source.get("DISPLAY_DELAY_REST_COLOUR") in DISPLAY_COLOURS
    )
    if not valid:
        return _copy_params(DEFAULT_SYSTEM_PARAMS), False

    params = {}
    for key in DEFAULT_SYSTEM_PARAMS:
        value = source[key]
        params[key] = list(value) if isinstance(value, list) else value
    return params, True


def normalize_user_params(data, system_params=None):
    """Migrate and validate user data, returning canonical keys and a changed flag."""
    if system_params is None:
        system_params = _copy_params(DEFAULT_SYSTEM_PARAMS)

    source = dict(data) if isinstance(data, dict) else {}
    migrated = dict(source)
    for legacy_key, canonical_key in LEGACY_USER_KEYS.items():
        if canonical_key not in migrated and legacy_key in migrated:
            migrated[canonical_key] = migrated[legacy_key]

    duration_values = system_params["DURATION_VALUES"]
    sensitivity_values = system_params["LAUNCH_SENSE_VALUES"]
    default_race = DEFAULT_USER_PARAMS["RACE_LENGTH"]
    default_rest = DEFAULT_USER_PARAMS["REST_LENGTH"]
    default_sensitivity = DEFAULT_USER_PARAMS["SENSITIVITY"]

    if default_race not in duration_values:
        default_race = duration_values[0]
    if default_rest not in duration_values:
        default_rest = duration_values[0]
    if default_sensitivity not in sensitivity_values:
        default_sensitivity = sensitivity_values[0]

    race_length = migrated.get("RACE_LENGTH", default_race)
    rest_length = migrated.get("REST_LENGTH", default_rest)
    sensitivity = migrated.get("SENSITIVITY", default_sensitivity)
    operating_mode = migrated.get(
        "OPERATING_MODE",
        DEFAULT_USER_PARAMS["OPERATING_MODE"],
    )
    brightness_percent = migrated.get(
        "BRIGHTNESS_PERCENT",
        DEFAULT_USER_PARAMS["BRIGHTNESS_PERCENT"],
    )
    display_rotation = migrated.get(
        "DISPLAY_ROTATION_DEG",
        DEFAULT_USER_PARAMS["DISPLAY_ROTATION_DEG"],
    )
    auto_dim_enabled = migrated.get(
        "AUTO_DIM_ENABLED",
        DEFAULT_USER_PARAMS["AUTO_DIM_ENABLED"],
    )
    auto_dim_invalid = not isinstance(auto_dim_enabled, bool)
    avg_lap_time_seconds = migrated.get(
        "AVG_LAP_TIME_SECONDS",
        DEFAULT_USER_PARAMS["AVG_LAP_TIME_SECONDS"],
    )
    avg_lap_time_invalid = (
        not isinstance(avg_lap_time_seconds, int)
        or isinstance(avg_lap_time_seconds, bool)
        or avg_lap_time_seconds < 0
        or avg_lap_time_seconds > MAX_AVG_LAP_TIME_SECONDS
    )

    if (
        not isinstance(race_length, int)
        or isinstance(race_length, bool)
        or race_length not in duration_values
    ):
        race_length = default_race
    if (
        not isinstance(rest_length, int)
        or isinstance(rest_length, bool)
        or rest_length not in duration_values
    ):
        rest_length = default_rest
    if not _is_number(sensitivity) or sensitivity not in sensitivity_values:
        sensitivity = default_sensitivity
    if operating_mode not in OPERATING_MODES:
        operating_mode = DEFAULT_USER_PARAMS["OPERATING_MODE"]
    if (
        not isinstance(brightness_percent, int)
        or isinstance(brightness_percent, bool)
        or brightness_percent not in BRIGHTNESS_VALUES
    ):
        brightness_percent = DEFAULT_USER_PARAMS["BRIGHTNESS_PERCENT"]
    if (
        isinstance(display_rotation, bool)
        or display_rotation not in DISPLAY_ROTATION_VALUES
    ):
        display_rotation = DEFAULT_USER_PARAMS["DISPLAY_ROTATION_DEG"]
    if auto_dim_invalid:
        auto_dim_enabled = DEFAULT_USER_PARAMS["AUTO_DIM_ENABLED"]
    if avg_lap_time_invalid:
        avg_lap_time_seconds = DEFAULT_USER_PARAMS["AVG_LAP_TIME_SECONDS"]

    normalized = {
        "SENSITIVITY": sensitivity,
        "RACE_LENGTH": race_length,
        "REST_LENGTH": rest_length,
        "OPERATING_MODE": operating_mode,
        "BRIGHTNESS_PERCENT": brightness_percent,
        "DISPLAY_ROTATION_DEG": display_rotation,
        "AUTO_DIM_ENABLED": auto_dim_enabled,
        "AVG_LAP_TIME_SECONDS": avg_lap_time_seconds,
    }
    return (
        normalized,
        auto_dim_invalid or avg_lap_time_invalid or normalized != source,
    )


def _remove_if_exists(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _replace_file(source, target):
    replace = getattr(os, "replace", None)
    if replace is not None:
        replace(source, target)
        return

    backup = target + ".bak"
    _remove_if_exists(backup)
    backed_up = False
    try:
        os.rename(target, backup)
        backed_up = True
    except OSError:
        pass

    try:
        os.rename(source, target)
    except Exception:
        if backed_up:
            os.rename(backup, target)
        raise
    else:
        if backed_up:
            _remove_if_exists(backup)


def file_out(file=None, data=None, mode="w", debug=True):
    """Serialize JSON to a temporary file and replace the target safely."""
    if file is None:
        if debug:
            print("No file specified.")
        return False
    if data is None:
        if debug:
            print("No data provided to write.")
        return False

    temporary = file + ".tmp"
    try:
        with open(temporary, mode) as target_file:
            json.dump(data, target_file)
            target_file.flush()
        _replace_file(temporary, file)
        return True
    except Exception as error:
        _remove_if_exists(temporary)
        if debug:
            print("Error occurred: " + str(error))
        return False


def _read_json(path, mode):
    with open(path, mode) as target_file:
        return json.load(target_file)


def file_in(file=None, mode="r", debug=True):
    """Read JSON in read-only mode, falling back to a recoverable backup."""
    if file is None:
        if debug:
            print("No file specified.")
        return None

    try:
        return _read_json(file, mode)
    except Exception as error:
        backup = file + ".bak"
        try:
            data = _read_json(backup, "r")
            file_out(file, data, debug=False)
            if debug:
                print("Recovered configuration from " + backup)
            return data
        except Exception:
            if debug:
                print("Error occurred: " + str(error))
            return None


def update_json(json_data=None, key=None, value=None):
    """Return an updated copy of a settings dictionary."""
    if not isinstance(json_data, dict) or key is None or key == "" or value is None:
        return None
    updated = dict(json_data)
    updated[key] = value
    return updated


def persist_setting(file, json_data, key, value, debug=True):
    """Persist one setting and retain the known-good dictionary on failure."""
    updated = update_json(json_data, key, value)
    if updated is None or not file_out(file, updated, debug=debug):
        return json_data, False
    return updated, True


def restore_user_defaults(file, debug=True):
    """Atomically persist and return a fresh canonical default dictionary."""
    defaults = _copy_params(DEFAULT_USER_PARAMS)
    if not file_out(file, defaults, debug=debug):
        return None, False
    return defaults, True


def load_configuration(params_file, user_file, debug=True):
    """Load validated system and canonical user settings with safe defaults."""
    raw_system = file_in(params_file, debug=False)
    system_params, system_valid = validate_system_params(raw_system)
    if debug and not system_valid:
        print("Invalid or missing system parameters; using built-in defaults.")

    raw_user = file_in(user_file, debug=False)
    user_params, user_changed = normalize_user_params(raw_user, system_params)
    if user_changed:
        if debug:
            print("User parameters were missing, invalid, or migrated; saving canonical values.")
        file_out(user_file, user_params, debug=debug)

    return system_params, user_params
