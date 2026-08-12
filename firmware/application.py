"""Memory-aware operating-mode dispatcher loaded after LCD allocation."""

import gc
import sys


PARAMS_FILE = "params.json"
USER_FILE = "user.json"
MODE_TIMER = "timer"
MODE_G = "g"

TIMER_MODULES = (
    "timer_mode",
    "auto_dim",
    "configuration",
    "hold_detector",
    "launch",
    "live_display",
    "g_force",
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


def _show_auto_rotation_degraded(lcd, error, launch_disabled=False):
    from hardware import show_hardware_message

    print("Automatic orientation unavailable: {}".format(error))
    middle_line = (
        "Launch also disabled" if launch_disabled else "Normal timer works"
    )
    show_hardware_message(
        lcd,
        "Auto rotate paused",
        ["IMU not available", middle_line, "Use fixed rotation"],
        background=lcd.brown,
    )


def _show_auto_dim_degraded(lcd, error, launch_disabled=False):
    from hardware import show_hardware_message

    print("Ready Auto-Dim unavailable: {}".format(error))
    middle_line = (
        "Launch also disabled" if launch_disabled else "Normal timer works"
    )
    show_hardware_message(
        lcd,
        "Auto-Dim paused",
        ["IMU not available", middle_line, "Normal brightness"],
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


def required_imu_sensitivity(user_params, active_mode, rotation_setting):
    """Return effective initialization demand for all IMU-backed features."""
    requirement = user_params["SENSITIVITY"]
    if (
        active_mode == MODE_G
        or rotation_setting == "auto"
        or user_params["AUTO_DIM_ENABLED"]
    ) and requirement <= 0:
        return 1
    return requirement


def _open_mode_menu(touch, lcd, user_params, auto_rotation):
    from operating_modes import configure_operating_mode

    result = configure_operating_mode(
        touch,
        lcd,
        user_params,
        USER_FILE,
        auto_rotation=auto_rotation,
    )
    del configure_operating_mode
    _unload_modules(("operating_modes",))
    return result[0], result[1], auto_rotation.sensor


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
    from auto_rotation import AUTO_ROTATION, AutoRotationController
    from hardware import PeripheralError, initialize_with_retry
    from hardware_splash import run_startup_screens
    from settings import load_configuration
    from touch_drive import Touch_CST816T

    # Import this small Timer dependency before automatic orientation begins
    # producing filtered sample objects. Its module allocation otherwise lands
    # in the RP2040 heap's most fragmented startup phase.
    from battery import BatteryMonitor
    del BatteryMonitor

    system_params, user_params = load_configuration(PARAMS_FILE, USER_FILE)
    print("User Parameters: " + str(user_params))
    rotation_setting = user_params["DISPLAY_ROTATION_DEG"]
    initial_rotation = 0 if rotation_setting == AUTO_ROTATION else rotation_setting
    lcd.set_rotation(initial_rotation)
    _apply_brightness(lcd, user_params["BRIGHTNESS_PERCENT"])

    try:
        touch = initialize_with_retry(
            lambda: Touch_CST816T(
                mode=1,
                LCD=lcd,
                rotation=initial_rotation,
            ),
            "CST816T",
        )

        active_mode = user_params["OPERATING_MODE"]
        imu_requirement = required_imu_sensitivity(
            user_params,
            active_mode,
            rotation_setting,
        )
        qmi8658, imu_error = _initialize_imu(imu_requirement)

        auto_rotation = AutoRotationController(
            qmi8658,
            lcd,
            touch,
            initial_rotation=initial_rotation,
            sensor_factory=lambda: _initialize_imu(1),
            sensor_error=imu_error,
        )
        touch.Set_Auto_Rotation(auto_rotation)
        if rotation_setting == AUTO_ROTATION:
            auto_rotation.enable(initialize=False)
            auto_rotation.prime()
            if not auto_rotation.available:
                qmi8658 = None
                imu_error = auto_rotation.error

        run_startup_screens(
            touch,
            lcd,
            firmware_version=system_params["VERSION"],
            startup_duration_sec=system_params["STARTUP_SPLASH_DURATION_SEC"],
            hardware_duration_sec=system_params["HARDWARE_SPLASH_DURATION_SEC"],
            wait=touch.Wait,
        )
    except PeripheralError as error:
        _show_touch_failure(lcd, error)
        return False

    del run_startup_screens
    _unload_modules(("hardware_splash", "splash"))

    # Release one-time startup imports before Timer Mode loads its dependency
    # set. On the RP2040 these references are enough to decide whether the next
    # small module allocation can fit beside the framebuffer.
    del AutoRotationController
    del AUTO_ROTATION
    del initialize_with_retry
    del load_configuration
    del Touch_CST816T
    del initial_rotation
    del imu_requirement
    gc.collect()

    if imu_error is not None:
        if active_mode == MODE_G:
            _show_g_mode_unavailable(lcd, imu_error)
            user_params = _persist_timer_fallback(user_params)
            active_mode = MODE_TIMER
        elif rotation_setting == AUTO_ROTATION:
            _show_auto_rotation_degraded(
                lcd,
                imu_error,
                launch_disabled=user_params["SENSITIVITY"] > 0,
            )
        elif user_params["AUTO_DIM_ENABLED"]:
            _show_auto_dim_degraded(
                lcd,
                imu_error,
                launch_disabled=user_params["SENSITIVITY"] > 0,
            )
        else:
            _show_imu_degraded(lcd, imu_error)
        touch.Wait(lcd, 2)

    del rotation_setting
    del imu_error
    gc.collect()

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
                    _show_auto_dim_degraded,
                    auto_rotation,
                )
            except PeripheralError as error:
                _show_touch_failure(lcd, error)
                return False
            del run_timer_mode
            _unload_modules(TIMER_MODULES)
            user_params, active_mode, qmi8658 = _open_mode_menu(
                touch,
                lcd,
                user_params,
                auto_rotation,
            )
            continue

        if qmi8658 is None:
            qmi8658, imu_error = _initialize_imu(1)
            if imu_error is not None:
                auto_rotation.set_sensor(None, imu_error)
                _show_g_mode_unavailable(lcd, imu_error)
                touch.Wait(lcd, 2)
                user_params = _persist_timer_fallback(user_params)
                active_mode = MODE_TIMER
                continue
            auto_rotation.set_sensor(qmi8658)

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
            _unload_modules(("g_meter", "g_force", "hold_detector"))
            if error.peripheral == "CST816T":
                _show_touch_failure(lcd, error)
                return False
            qmi8658 = None
            auto_rotation.set_sensor(None, error)
            _show_g_mode_unavailable(lcd, error)
            touch.Wait(lcd, 2)
            user_params = _persist_timer_fallback(user_params)
            active_mode = MODE_TIMER
            continue

        del run_g_mode
        _unload_modules(("g_meter", "g_force", "hold_detector"))
        user_params, active_mode, qmi8658 = _open_mode_menu(
            touch,
            lcd,
            user_params,
            auto_rotation,
        )
