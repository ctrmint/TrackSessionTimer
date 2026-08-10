"""Memory-aware operating-mode dispatcher loaded after LCD allocation."""

import gc
import sys
import time


PARAMS_FILE = "params.json"
USER_FILE = "user.json"
MODE_TIMER = "timer"
MODE_G = "g"

TIMER_MODULES = (
    "timer_mode",
    "battery",
    "configuration",
    "hold_detector",
    "launch",
    "live_display",
    "ready_screen",
    "timing",
)


def _unload_modules(names):
    for name in names:
        sys.modules.pop(name, None)
    gc.collect()


def _apply_brightness(lcd, percent):
    lcd.set_bl_pwm(int(round(65535 * int(percent) / 100)))


def _show_touch_failure(lcd, error):
    from hardware import show_hardware_message

    print("Timer stopped: {}".format(error))
    show_hardware_message(
        lcd,
        "Touch error",
        ["Touch not detected", "Check board / I2C", "Restart timer"],
    )


def _show_imu_degraded(lcd, error):
    from hardware import show_hardware_message

    print("Normal timing remains available: {}".format(error))
    show_hardware_message(
        lcd,
        "Launch disabled",
        ["IMU not available", "Normal timer works", "Check board / I2C"],
        background=lcd.brown,
    )


def _show_g_mode_unavailable(lcd, error):
    from hardware import show_hardware_message

    print("G Mode unavailable: {}".format(error))
    show_hardware_message(
        lcd,
        "G Mode unavailable",
        ["IMU not available", "Returning to Timer", "Check board / I2C"],
        background=lcd.brown,
    )


def _initialize_imu(sensitivity):
    from hardware import initialize_optional_imu
    from qmi8658 import QMI8658

    return initialize_optional_imu(sensitivity, QMI8658)


def _open_mode_menu(touch, lcd, user_params):
    from operating_modes import configure_operating_mode

    result = configure_operating_mode(
        touch,
        lcd,
        user_params,
        USER_FILE,
    )
    del configure_operating_mode
    _unload_modules(("operating_modes",))
    return result


def _persist_timer_fallback(user_params):
    from settings import persist_setting

    return persist_setting(
        USER_FILE,
        user_params,
        "OPERATING_MODE",
        MODE_TIMER,
    )[0]


def run_application(lcd):
    """Initialize shared hardware and dispatch one active feature at a time."""
    from hardware import PeripheralError, initialize_with_retry
    from hardware_splash import run_startup_screens
    from settings import load_configuration
    from touch_drive import Touch_CST816T

    system_params, user_params = load_configuration(PARAMS_FILE, USER_FILE)
    print("User Parameters: " + str(user_params))
    lcd.set_rotation(user_params["DISPLAY_ROTATION_DEG"])
    _apply_brightness(lcd, user_params["BRIGHTNESS_PERCENT"])

    try:
        touch = initialize_with_retry(
            lambda: Touch_CST816T(
                mode=1,
                LCD=lcd,
                rotation=user_params["DISPLAY_ROTATION_DEG"],
            ),
            "CST816T",
        )
        run_startup_screens(
            touch,
            lcd,
            firmware_version=system_params["VERSION"],
            startup_duration_sec=system_params["STARTUP_SPLASH_DURATION_SEC"],
            hardware_duration_sec=system_params["HARDWARE_SPLASH_DURATION_SEC"],
        )
    except PeripheralError as error:
        _show_touch_failure(lcd, error)
        return False

    del run_startup_screens
    _unload_modules(("hardware_splash", "splash"))

    active_mode = user_params["OPERATING_MODE"]
    imu_requirement = user_params["SENSITIVITY"]
    if active_mode == MODE_G and imu_requirement <= 0:
        imu_requirement = 1
    qmi8658, imu_error = _initialize_imu(imu_requirement)
    if imu_error is not None:
        if active_mode == MODE_G:
            _show_g_mode_unavailable(lcd, imu_error)
            user_params = _persist_timer_fallback(user_params)
            active_mode = MODE_TIMER
        else:
            _show_imu_degraded(lcd, imu_error)
        time.sleep(2)

    while True:
        if active_mode == MODE_TIMER:
            from timer_mode import run_timer_mode

            try:
                user_params, qmi8658 = run_timer_mode(
                    lcd,
                    touch,
                    user_params,
                    system_params,
                    qmi8658,
                    _initialize_imu,
                    _show_imu_degraded,
                )
            except PeripheralError as error:
                _show_touch_failure(lcd, error)
                return False
            del run_timer_mode
            _unload_modules(TIMER_MODULES)
            user_params, active_mode = _open_mode_menu(
                touch,
                lcd,
                user_params,
            )
            continue

        if qmi8658 is None:
            qmi8658, imu_error = _initialize_imu(1)
            if imu_error is not None:
                _show_g_mode_unavailable(lcd, imu_error)
                time.sleep(2)
                user_params = _persist_timer_fallback(user_params)
                active_mode = MODE_TIMER
                continue

        from g_meter import run_g_mode

        try:
            run_g_mode(
                qmi8658,
                touch,
                lcd,
                hold_seconds=system_params["MODE_MENU_HOLD_SEC"],
            )
        except PeripheralError as error:
            del run_g_mode
            _unload_modules(("g_meter", "hold_detector"))
            if error.peripheral == "CST816T":
                _show_touch_failure(lcd, error)
                return False
            qmi8658 = None
            _show_g_mode_unavailable(lcd, error)
            time.sleep(2)
            user_params = _persist_timer_fallback(user_params)
            active_mode = MODE_TIMER
            continue

        del run_g_mode
        _unload_modules(("g_meter", "hold_detector"))
        user_params, active_mode = _open_mode_menu(
            touch,
            lcd,
            user_params,
        )
