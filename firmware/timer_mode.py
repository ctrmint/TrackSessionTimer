"""Existing track/rest timer workflow, loaded only while Timer Mode is active."""

import time

from auto_dim import ReadyAutoDim
from battery import BatteryMonitor
from configuration import set_sensitivity, set_session
from g_force import SessionGPeak, calibrate_baseline
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
from session_summary import build_session_summary, review_session_summary
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
    show_auto_dim_degraded,
    auto_rotation=None,
):
    """Run complete timer sessions until a safe Ready-screen hold requests menu."""
    duration_values = system_params["DURATION_VALUES"]
    launch_sense_values = system_params["LAUNCH_SENSE_VALUES"]
    mode_menu_hold_sec = system_params["MODE_MENU_HOLD_SEC"]
    display_delay_rest = system_params["DISPLAY_DELAY_REST"]
    display_delay_rest_colour = system_params["DISPLAY_DELAY_REST_COLOUR"]
    battery_monitor = BatteryMonitor()
    auto_dim_enabled = user_params["AUTO_DIM_ENABLED"]

    if auto_dim_enabled and qmi8658 is None:
        qmi8658, imu_error = initialize_imu(1)
        if auto_rotation is not None:
            auto_rotation.set_sensor(qmi8658, imu_error)
        if imu_error is not None:
            show_auto_dim_degraded(
                lcd,
                imu_error,
                launch_disabled=user_params["SENSITIVITY"] > 0,
            )
            touch.Wait(lcd, 2)

    ready_auto_dim = ReadyAutoDim(
        lcd,
        sensor=qmi8658,
        enabled=auto_dim_enabled,
        normal_percent=user_params["BRIGHTNESS_PERCENT"],
        dim_percent=system_params["AUTO_DIM_PERCENT"],
    )

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

        ready_auto_dim.set_sensor(qmi8658)
        ready_auto_dim.enter_ready()
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

            try:
                ready_auto_dim.update()
            except PeripheralError as error:
                print("Ready Auto-Dim paused: {}".format(error))
                ready_auto_dim.disable_sensor()
                qmi8658 = None
                sensitivity = 0
                if auto_rotation is not None:
                    auto_rotation.set_sensor(None, error)
                show_auto_dim_degraded(
                    lcd,
                    error,
                    launch_disabled=configured_sensitivity > 0,
                )
                touch.Wait(lcd, 2)
                ready_screen_dirty = True

            if hold_detector.update(touch.IsPressed(lcd)):
                ready_auto_dim.leave_ready()
                touch.ClearPendingInput()
                return user_params, qmi8658

            gesture = touch.GetGesture(lcd, debounce_time=0.05)

            if gesture == "left":
                ready_auto_dim.leave_ready()
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
                ready_auto_dim.enter_ready()
                hold_detector.reset()
            elif gesture == "right":
                ready_auto_dim.leave_ready()
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
                ready_auto_dim.enter_ready()
                hold_detector.reset()
            elif gesture == "up":
                ready_auto_dim.leave_ready()
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
                    if auto_rotation is not None:
                        auto_rotation.set_sensor(qmi8658, imu_error)
                    if imu_error is not None:
                        show_imu_degraded(lcd, imu_error)
                        touch.Wait(lcd, 2)
                sensitivity = (
                    configured_sensitivity if qmi8658 is not None else 0
                )
                ready_auto_dim.set_sensor(qmi8658)
                ready_screen_dirty = True
                ready_auto_dim.enter_ready()
                hold_detector.reset()
            elif gesture == "down":
                ready_auto_dim.leave_ready()
                print("Timer go!")
                launch = True

            time.sleep(0.05)

        if qmi8658 is None:
            qmi8658, imu_error = initialize_imu(1)
            if auto_rotation is not None:
                auto_rotation.set_sensor(qmi8658, imu_error)

        sensitivity = configured_sensitivity if qmi8658 is not None else 0
        session_baseline = None
        session_g_peak = SessionGPeak()
        if qmi8658 is not None:
            touch.ControlScreen(
                lcd,
                text_array=[
                    ["SESSION G", None, 52, 2, "white"],
                    ["Calibrating", None, 105, 2, "white"],
                    ["Keep device still", None, 150, 1, "white"],
                ],
                back_colour="black",
            )
            try:
                session_baseline = calibrate_baseline(qmi8658)
                session_g_peak = SessionGPeak(
                    qmi8658,
                    baseline=session_baseline,
                )
            except PeripheralError as error:
                print("Session maximum G unavailable: {}".format(error))
                qmi8658 = None
                sensitivity = 0
                if auto_rotation is not None:
                    auto_rotation.set_sensor(None, error)

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
                baseline=session_baseline,
                sample_update=lambda sample: session_g_peak.update(
                    sample,
                    rotation=getattr(lcd, "rotation", 0),
                ),
            )
        except PeripheralError as error:
            qmi8658 = None
            if auto_rotation is not None:
                auto_rotation.set_sensor(None, error)
            show_imu_degraded(lcd, error)
            touch.Wait(lcd, 2)
            continue
        if not launch_detected:
            print("Launch mode cancelled or timed out.")
            continue

        def sample_session_g(_now):
            nonlocal qmi8658
            try:
                session_g_peak.sample(rotation=getattr(lcd, "rotation", 0))
            except PeripheralError as error:
                print("Session maximum G paused: {}".format(error))
                session_g_peak.disable()
                qmi8658 = None
                if auto_rotation is not None:
                    auto_rotation.set_sensor(None, error)

        track_session.start_session()
        run_live_display(
            track_session,
            frame_builder=lambda now: track_live_frame(
                track_session,
                now,
                lcd,
                maximum_g=session_g_peak.display_label(
                    now - track_session.start_time
                ),
            ),
            draw_frame=lambda frame: draw_live_frame(touch, lcd, frame),
            stop_check=lambda: touch.StopGesture(lcd),
            sample_update=sample_session_g,
        )

        session_summary = build_session_summary(
            track_session,
            time.time(),
            g_peak=session_g_peak,
        )
        review_session_summary(touch, lcd, session_summary)

        touch.ControlScreen(
            lcd,
            text_array=[PLINE1, PLINE2],
            back_colour=display_delay_rest_colour,
        )
        touch.Wait(lcd, display_delay_rest)

        rest_session.start_session(debug=True)
        run_live_display(
            rest_session,
            frame_builder=lambda now: rest_live_frame(rest_session, now, lcd),
            draw_frame=lambda frame: draw_live_frame(touch, lcd, frame),
            stop_check=lambda: touch.ClearGesture(lcd),
        )
