"""Peripheral startup policy shared by the firmware and host-side tests."""

import time


class PeripheralError(Exception):
    """Base error for a peripheral that cannot be used safely."""

    def __init__(self, peripheral, operation, detail, retryable=False):
        self.peripheral = peripheral
        self.operation = operation
        self.detail = str(detail)
        self.retryable = retryable
        message = "{} {} failed: {}".format(peripheral, operation, self.detail)
        super().__init__(message)


class PeripheralIOError(PeripheralError):
    """A potentially transient bus or register access failure."""

    def __init__(self, peripheral, operation, detail):
        super().__init__(peripheral, operation, detail, retryable=True)


class PeripheralIdentityError(PeripheralError):
    """A responding device does not have the expected chip identity."""

    def __init__(self, peripheral, expected, actual):
        self.expected = expected
        self.actual = actual
        detail = "expected chip ID 0x{:02X}, received 0x{:02X}".format(
            expected, actual
        )
        super().__init__(peripheral, "detection", detail, retryable=False)


def _sleep_ms(clock, milliseconds):
    sleep_ms = getattr(clock, "sleep_ms", None)
    if sleep_ms is not None:
        sleep_ms(milliseconds)
    else:
        clock.sleep(milliseconds / 1000)


def initialize_with_retry(
    factory,
    peripheral,
    attempts=3,
    retry_delay_ms=100,
    clock=time,
    logger=print,
):
    """Build a complete peripheral, retrying only transient I/O failures."""
    if attempts < 1:
        raise ValueError("attempts must be positive")

    for attempt in range(1, attempts + 1):
        try:
            return factory()
        except OSError as error:
            failure = PeripheralIOError(peripheral, "initialization", error)
        except PeripheralError as error:
            failure = error

        if not failure.retryable or attempt == attempts:
            logger("Hardware error: {}".format(failure))
            raise failure

        logger(
            "Hardware retry {}/{}: {}".format(attempt, attempts, failure)
        )
        _sleep_ms(clock, retry_delay_ms)


def initialize_optional_imu(sensitivity, factory, **retry_options):
    """Initialize the IMU only when a feature requires it, degrading safely."""
    if float(sensitivity) <= 0:
        return None, None

    logger = retry_options.get("logger", print)
    try:
        sensor = initialize_with_retry(factory, "QMI8658", **retry_options)
        return sensor, None
    except PeripheralError as error:
        logger("IMU unavailable: {}".format(error))
        return None, error


def show_hardware_message(lcd, title, lines, background=None):
    """Display a short, actionable hardware status message."""
    if background is None:
        background = lcd.red
    lcd.fill(background)
    lcd.write_centered(title, 48, 2, lcd.white)
    y_position = 105
    for line in lines:
        lcd.write_centered(line, y_position, 1, lcd.white)
        y_position += 30
    lcd.show()
