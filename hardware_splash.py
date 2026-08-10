"""Configurable startup sequence and compact hardware-information screen."""

import time


BOARD_VENDOR = "Waveshare"
BOARD_MODEL = "Touch LCD 1.28"
UNKNOWN_VALUE = "Unknown"

HARDWARE_SPLASH_BACKGROUND = "black"
HARDWARE_SPLASH_TEXT_COLOUR = "white"


class DeviceDetails:
    """Display-safe device metadata collected without requiring hardware."""

    def __init__(
        self,
        firmware,
        cpu,
        os_name,
        os_version,
        platform,
        vendor=BOARD_VENDOR,
        model=BOARD_MODEL,
    ):
        self.vendor = vendor
        self.model = model
        self.firmware = firmware
        self.cpu = cpu
        self.os_name = os_name
        self.os_version = os_version
        self.platform = platform


def _runtime_value(source, attribute):
    try:
        value = getattr(source, attribute)
    except Exception:
        return UNKNOWN_VALUE
    if value is None:
        return UNKNOWN_VALUE
    value = str(value).strip()
    return value if value else UNKNOWN_VALUE


def _short_value(value, maximum=18):
    value = str(value)
    if len(value) <= maximum:
        return value
    return value[: maximum - 1] + "."


def _runtime_name(implementation):
    name = _runtime_value(implementation, "name")
    known_names = {
        "micropython": "MicroPython",
        "cpython": "CPython",
    }
    return known_names.get(name.lower(), _short_value(name))


def _cpu_name(uname_info):
    machine = _runtime_value(uname_info, "machine")
    if "RP2040" in machine.upper():
        return "RP2040"
    return _short_value(machine, maximum=12)


def collect_device_details(firmware_version, uname_info=None, implementation=None):
    """Collect normalized details with safe fallbacks for missing fields."""
    if uname_info is None:
        try:
            try:
                import uos as os
            except ImportError:
                import os
            uname_info = os.uname()
        except Exception:
            uname_info = object()

    if implementation is None:
        try:
            import sys
            implementation = sys.implementation
        except Exception:
            implementation = object()

    return DeviceDetails(
        firmware=_short_value(firmware_version, maximum=10),
        cpu=_cpu_name(uname_info),
        os_name=_runtime_name(implementation),
        os_version=_short_value(
            _runtime_value(uname_info, "release"),
            maximum=10,
        ),
        platform=_short_value(
            _runtime_value(uname_info, "sysname"),
            maximum=12,
        ),
    )


def hardware_splash_lines(details):
    """Build a circular-display-safe hardware summary."""
    return [
        ["Hardware", None, 24, 3, HARDWARE_SPLASH_TEXT_COLOUR],
        ["Board " + details.vendor, None, 70, 1, HARDWARE_SPLASH_TEXT_COLOUR],
        ["Model " + details.model, None, 94, 1, HARDWARE_SPLASH_TEXT_COLOUR],
        ["Type " + details.cpu, None, 118, 1, HARDWARE_SPLASH_TEXT_COLOUR],
        ["Firmware v" + details.firmware, None, 142, 1, HARDWARE_SPLASH_TEXT_COLOUR],
        [
            "OS " + details.os_name + " " + details.os_version,
            None,
            166,
            1,
            HARDWARE_SPLASH_TEXT_COLOUR,
        ],
        ["Platform " + details.platform, None, 190, 1, HARDWARE_SPLASH_TEXT_COLOUR],
    ]


def run_startup_screens(
    touch,
    lcd,
    firmware_version,
    startup_duration_sec,
    hardware_duration_sec,
    clock=time,
    details=None,
):
    """Show artwork, then hardware details, for their configured durations."""
    touch.BootScreen(lcd, version_number=firmware_version)
    clock.sleep(startup_duration_sec)

    if details is None:
        details = collect_device_details(firmware_version)
    touch.ControlScreen(
        lcd,
        text_array=hardware_splash_lines(details),
        back_colour=HARDWARE_SPLASH_BACKGROUND,
    )
    clock.sleep(hardware_duration_sec)
    return details
