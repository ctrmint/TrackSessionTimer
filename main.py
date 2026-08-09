# Mark Rodman
# Session Timer for track days and racing.
# V3.3

import time

from configuration import set_sensitivity, set_session
from hardware import (
    PeripheralError,
    initialize_optional_imu,
    initialize_with_retry,
    show_hardware_message,
)
from launch import accel_launch
from lcd_1inch28 import LCD_1inch28
from live_display import (
    draw_live_frame,
    rest_live_frame,
    run_live_display,
    track_live_frame,
)
from qmi8658 import QMI8658
from settings import load_configuration, persist_setting
from timing import SessionTracker
from touch_drive import Touch_CST816T


PARAMS_FILE = "params.json"
USER_FILE = "user.json"

PIT_SESSION_MSG = ["Cool down!", "Rest in pits"]
TRACK_SESSION_MSG = ["Ready", "Swipe DOWN to start"]
CLINE1 = [TRACK_SESSION_MSG[0], None, 90, 5, "white"]
CLINE2 = [TRACK_SESSION_MSG[1], None, 185, 1, "black"]
CLINE3 = ["message", None, 35, 3, "black"]
PLINE1 = [PIT_SESSION_MSG[0], None, 88, 3, "white"]
PLINE2 = [PIT_SESSION_MSG[1], None, 145, 2, "red"]


def _show_touch_failure(lcd, error):
    print("Timer stopped: {}".format(error))
    show_hardware_message(
        lcd,
        "Touch error",
        ["Touch not detected", "Check board / I2C", "Restart timer"],
    )


def _show_imu_degraded(lcd, error):
    print("Normal timing remains available: {}".format(error))
    show_hardware_message(
        lcd,
        "Launch disabled",
        ["IMU not available", "Normal timer works", "Check board / I2C"],
        background=lcd.brown,
    )


def _initialize_imu(sensitivity):
    return initialize_optional_imu(sensitivity, QMI8658)


def main():
    system_params, user_params = load_configuration(PARAMS_FILE, USER_FILE)
    duration_values = system_params["DURATION_VALUES"]
    launch_sense_values = system_params["LAUNCH_SENSE_VALUES"]
    version = system_params["VERSION"]
    boot_delay_sec = system_params["BOOT_DELAY_SEC"]
    display_delay_rest = system_params["DISPLAY_DELAY_REST"]
    display_delay_rest_colour = system_params["DISPLAY_DELAY_REST_COLOUR"]

    print("User Parameters: " + str(user_params))

    # Display and touchscreen
    lcd = LCD_1inch28()
    lcd.set_bl_pwm(65535)
    try:
        touch = initialize_with_retry(
            lambda: Touch_CST816T(mode=1, LCD=lcd),
            "CST816T",
        )
        touch.BootScreen(lcd, version_number=version)
    except PeripheralError as error:
        _show_touch_failure(lcd, error)
        return False

    time.sleep(boot_delay_sec)

    qmi8658, imu_error = _initialize_imu(user_params["SENSITIVITY"])
    if imu_error is not None:
        _show_imu_degraded(lcd, imu_error)
        time.sleep(2)

    while True:
        configured_sensitivity = user_params["SENSITIVITY"]
        sensitivity = configured_sensitivity if qmi8658 is not None else 0
        race_length = user_params["RACE_LENGTH"]
        rest_length = user_params["REST_LENGTH"]

        launch = False
        track_session = SessionTracker(duration_mins=race_length, stype="track")
        rest_session = SessionTracker(duration_mins=rest_length, stype="rest", debug=True)

        while not launch:
            CLINE3[0] = str(track_session.duration_mins) + "mins"
            touch.ControlScreen(lcd, text_array=[CLINE1, CLINE2, CLINE3], back_colour="green")
            gesture = touch.GetGesture(lcd)

            if gesture == "left":
                race_length = set_session(
                    LCD=lcd,
                    Touch=touch,
                    session=track_session,
                    session_values=duration_values,
                    session_name="Track",
                    back_colour="palegreen",
                )
                user_params, _ = persist_setting(USER_FILE, user_params, "RACE_LENGTH", race_length)
            elif gesture == "right":
                rest_length = set_session(
                    LCD=lcd,
                    Touch=touch,
                    session=rest_session,
                    session_values=duration_values,
                    session_name="Rest",
                    back_colour="paleblue",
                )
                user_params, _ = persist_setting(USER_FILE, user_params, "REST_LENGTH", rest_length)
            elif gesture == "up":
                configured_sensitivity = set_sensitivity(
                    LCD=lcd,
                    Touch=touch,
                    sensitivity_values=launch_sense_values,
                    sensitivity=configured_sensitivity,
                    operation="Config",
                    back_colour="palegreen",
                )
                user_params, _ = persist_setting(
                    USER_FILE,
                    user_params,
                    "SENSITIVITY",
                    configured_sensitivity,
                )
                if configured_sensitivity > 0 and qmi8658 is None:
                    qmi8658, imu_error = _initialize_imu(configured_sensitivity)
                    if imu_error is not None:
                        _show_imu_degraded(lcd, imu_error)
                        time.sleep(2)
                sensitivity = (
                    configured_sensitivity if qmi8658 is not None else 0
                )
            elif gesture == "down":
                print("Timer go!")
                launch = True

            time.sleep(0.5)

        if sensitivity > 0:
            touch.GoScreen(
                lcd,
                text="lights!",
                subtitle="Double tap to cancel",
            )
        else:
            touch.GoScreen(lcd)

        try:
            launch_detected = accel_launch(
                qmi8658,
                sensitivity=sensitivity,
                cancel_check=lambda: touch.StopGesture(lcd),
            )
        except PeripheralError as error:
            qmi8658 = None
            _show_imu_degraded(lcd, error)
            time.sleep(2)
            continue
        if not launch_detected:
            print("Launch mode cancelled or timed out.")
            continue

        track_session.start_session()

        run_live_display(
            track_session,
            frame_builder=lambda now: track_live_frame(track_session, now, lcd),
            draw_frame=lambda frame: draw_live_frame(touch, lcd, frame),
            stop_check=lambda: touch.StopGesture(lcd),
        )

        touch.ControlScreen(
            lcd,
            text_array=[PLINE1, PLINE2],
            back_colour=display_delay_rest_colour,
        )
        time.sleep(display_delay_rest)

        rest_session.start_session(debug=True)
        run_live_display(
            rest_session,
            frame_builder=lambda now: rest_live_frame(rest_session, now, lcd),
            draw_frame=lambda frame: draw_live_frame(touch, lcd, frame),
            stop_check=lambda: touch.ClearGesture(lcd),
        )


if __name__ == "__main__":
    main()
