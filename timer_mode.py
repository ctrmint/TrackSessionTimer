"""Existing track/rest timer workflow, loaded only while Timer Mode is active."""

import time

from battery import BatteryMonitor
from configuration import set_sensitivity, set_session
from hardware import PeripheralError
from hold_detector import HoldDetector
from launch import accel_launch
from live_display import (
    draw_live_frame,
    rest_live_frame,
    run_live_display,
    track_live_frame,
)
from ready_screen import draw_ready_screen
from settings import persist_setting
from timing import SessionTracker


USER_FILE = "user.json"
PIT_SESSION_MSG = ["Cool down!", "Rest in pits"]
PLINE1 = [PIT_SESSION_MSG[0], None, 88, 3, "white"]
PLINE2 = [PIT_SESSION_MSG[1], None, 145, 2, "red"]


def run_timer_mode(
    lcd,
    touch,
    user_params,
    system_params,
    qmi8658,
    initialize_imu,
    show_imu_degraded,
):
    """Run complete timer sessions until a safe Ready-screen hold requests menu."""
    duration_values = system_params["DURATION_VALUES"]
    launch_sense_values = system_params["LAUNCH_SENSE_VALUES"]
    mode_menu_hold_sec = system_params["MODE_MENU_HOLD_SEC"]
    display_delay_rest = system_params["DISPLAY_DELAY_REST"]
    display_delay_rest_colour = system_params["DISPLAY_DELAY_REST_COLOUR"]
    battery_monitor = BatteryMonitor()

    while True:
        configured_sensitivity = user_params["SENSITIVITY"]
        sensitivity = configured_sensitivity if qmi8658 is not None else 0
        race_length = user_params["RACE_LENGTH"]
        rest_length = user_params["REST_LENGTH"]

        launch = False
        ready_screen_dirty = True
        hold_detector = HoldDetector(mode_menu_hold_sec)
        track_session = SessionTracker(duration_mins=race_length, stype="track")
        rest_session = SessionTracker(
            duration_mins=rest_length,
            stype="rest",
            debug=True,
        )

        while not launch:
            if ready_screen_dirty:
                draw_ready_screen(
                    touch=touch,
                    lcd=lcd,
                    track_minutes=track_session.duration_mins,
                    rest_minutes=rest_session.duration_mins,
                    sensitivity=configured_sensitivity,
                    imu_available=qmi8658 is not None,
                    battery_status=battery_monitor.read_status(),
                    mode_hold_seconds=mode_menu_hold_sec,
                )
                ready_screen_dirty = False

            if hold_detector.update(touch.IsPressed()):
                touch.ClearPendingInput()
                return user_params, qmi8658

            gesture = touch.GetGesture(lcd, debounce_time=0.05)

            if gesture == "left":
                race_length = set_session(
                    LCD=lcd,
                    Touch=touch,
                    session=track_session,
                    session_values=duration_values,
                    session_name="Track",
                    back_colour="palegreen",
                )
                user_params, _ = persist_setting(
                    USER_FILE,
                    user_params,
                    "RACE_LENGTH",
                    race_length,
                )
                ready_screen_dirty = True
                hold_detector.reset()
            elif gesture == "right":
                rest_length = set_session(
                    LCD=lcd,
                    Touch=touch,
                    session=rest_session,
                    session_values=duration_values,
                    session_name="Rest",
                    back_colour="paleblue",
                )
                user_params, _ = persist_setting(
                    USER_FILE,
                    user_params,
                    "REST_LENGTH",
                    rest_length,
                )
                ready_screen_dirty = True
                hold_detector.reset()
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
                    qmi8658, imu_error = initialize_imu(configured_sensitivity)
                    if imu_error is not None:
                        show_imu_degraded(lcd, imu_error)
                        time.sleep(2)
                sensitivity = (
                    configured_sensitivity if qmi8658 is not None else 0
                )
                ready_screen_dirty = True
                hold_detector.reset()
            elif gesture == "down":
                print("Timer go!")
                launch = True

            time.sleep(0.05)

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
            show_imu_degraded(lcd, error)
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
