import unittest

from hardware import (
    PeripheralIOError,
    PeripheralIdentityError,
    initialize_optional_imu,
    initialize_with_retry,
    show_hardware_message,
)


class FakeClock:
    def __init__(self):
        self.sleeps = []

    def sleep_ms(self, milliseconds):
        self.sleeps.append(milliseconds)


class FakeLCD:
    red = 1
    white = 2

    def __init__(self):
        self.calls = []

    def fill(self, colour):
        self.calls.append(("fill", colour))

    def write_centered(self, text, y_position, size, colour):
        self.calls.append(("text", text, y_position, size, colour))

    def show(self):
        self.calls.append(("show",))


class HardwarePolicyTests(unittest.TestCase):
    def test_transient_io_failures_are_retried_then_succeed(self):
        attempts = []
        clock = FakeClock()
        logs = []

        def factory():
            attempts.append(True)
            if len(attempts) < 3:
                raise PeripheralIOError("QMI8658", "chip ID read", "busy")
            return "sensor"

        result = initialize_with_retry(
            factory,
            "QMI8658",
            clock=clock,
            logger=logs.append,
        )

        self.assertEqual("sensor", result)
        self.assertEqual(3, len(attempts))
        self.assertEqual([100, 100], clock.sleeps)
        self.assertEqual(2, len(logs))

    def test_wrong_identity_is_not_retried(self):
        attempts = []

        def factory():
            attempts.append(True)
            raise PeripheralIdentityError("CST816T", 0xB5, 0x00)

        with self.assertRaises(PeripheralIdentityError):
            initialize_with_retry(factory, "CST816T", logger=lambda message: None)

        self.assertEqual(1, len(attempts))

    def test_disabled_launch_mode_does_not_initialize_imu(self):
        calls = []

        sensor, error = initialize_optional_imu(
            0,
            lambda: calls.append(True),
        )

        self.assertIsNone(sensor)
        self.assertIsNone(error)
        self.assertEqual([], calls)

    def test_optional_imu_failure_returns_degraded_mode(self):
        failure = PeripheralIOError("QMI8658", "chip ID read", "no device")

        def factory():
            raise failure

        sensor, error = initialize_optional_imu(
            0.5,
            factory,
            attempts=1,
            logger=lambda message: None,
        )

        self.assertIsNone(sensor)
        self.assertIs(error, failure)

    def test_hardware_message_is_visible_and_actionable(self):
        lcd = FakeLCD()

        show_hardware_message(
            lcd,
            "Touch error",
            ["Touch not detected", "Restart timer"],
        )

        self.assertEqual(("fill", lcd.red), lcd.calls[0])
        displayed_text = [call[1] for call in lcd.calls if call[0] == "text"]
        self.assertEqual(
            ["Touch error", "Touch not detected", "Restart timer"],
            displayed_text,
        )
        self.assertEqual(("show",), lcd.calls[-1])


if __name__ == "__main__":
    unittest.main()
