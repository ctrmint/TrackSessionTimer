import importlib
import sys
import types
import unittest

from hardware import (
    PeripheralIOError,
    PeripheralIdentityError,
    initialize_with_retry,
)


class FakePin:
    IN = 0
    OUT = 1
    PULL_UP = 2
    IRQ_FALLING = 4

    def __init__(self, number, mode=None, pull=None):
        self.number = number
        self.mode = mode
        self.pull = pull
        self.value = None
        self.irq_args = None

    def __call__(self, value=None):
        if value is None:
            return self.value
        self.value = value

    def irq(self, **kwargs):
        self.irq_args = kwargs


class FakeTimer:
    pass


class FakeClock:
    def __init__(self):
        self.sleeps = []

    def sleep_ms(self, milliseconds):
        self.sleeps.append(milliseconds)


class FakeBus:
    def __init__(self, registers=None, read_error=None):
        self.registers = registers or {}
        self.read_error = read_error
        self.writes = []

    def readfrom_mem(self, address, register, length):
        if self.read_error is not None:
            raise self.read_error
        value = self.registers.get(register, bytes(length))
        if isinstance(value, int):
            value = bytes([value])
        return value[:length]

    def writeto_mem(self, address, register, value):
        self.writes.append((address, register, value))


def import_drivers():
    machine = types.ModuleType("machine")
    machine.Pin = FakePin
    machine.I2C = object
    machine.Timer = FakeTimer

    previous_machine = sys.modules.get("machine")
    sys.modules["machine"] = machine
    try:
        return (
            importlib.import_module("qmi8658"),
            importlib.import_module("touch_drive"),
        )
    finally:
        if previous_machine is None:
            del sys.modules["machine"]
        else:
            sys.modules["machine"] = previous_machine


qmi8658, touch_drive = import_drivers()


class PeripheralDriverTests(unittest.TestCase):
    def make_touch(self, bus, clock=None):
        if clock is None:
            clock = FakeClock()
        return touch_drive.Touch_CST816T(
            bus=bus,
            pin_factory=FakePin,
            timer_factory=FakeTimer,
            clock=clock,
        )

    def test_qmi_wrong_chip_id_is_incompatible_hardware(self):
        with self.assertRaises(PeripheralIdentityError) as raised:
            qmi8658.QMI8658(bus=FakeBus({0x00: 0xFF}))

        self.assertEqual(0x05, raised.exception.expected)
        self.assertEqual(0xFF, raised.exception.actual)

    def test_touch_wrong_chip_id_is_incompatible_hardware(self):
        with self.assertRaises(PeripheralIdentityError) as raised:
            self.make_touch(FakeBus({0xA7: 0x00}))

        self.assertEqual(0xB5, raised.exception.expected)
        self.assertEqual(0x00, raised.exception.actual)

    def test_touch_reports_current_physical_press_state(self):
        released = self.make_touch(FakeBus({0xA7: 0xB5, 0xA9: 1, 0x02: 0}))
        pressed = self.make_touch(FakeBus({0xA7: 0xB5, 0xA9: 1, 0x02: 1}))

        self.assertFalse(released.IsPressed())
        self.assertTrue(pressed.IsPressed())

    def test_pending_touch_input_can_be_cleared(self):
        touch = self.make_touch(FakeBus({0xA7: 0xB5, 0xA9: 1}))
        touch.Gestures = 12
        touch.Flag = 1

        touch.ClearPendingInput()

        self.assertEqual(0, touch.Gestures)
        self.assertEqual(0, touch.Flag)

    def test_timed_screens_continue_auto_rotation_polling(self):
        class FakeAutoRotation:
            def __init__(self):
                self.calls = []

            def update(self, redraw=True):
                self.calls.append(redraw)
                return False

        clock = FakeClock()
        touch = self.make_touch(
            FakeBus({0xA7: 0xB5, 0xA9: 1}),
            clock=clock,
        )
        clock.sleeps = []
        auto_rotation = FakeAutoRotation()
        touch.Set_Auto_Rotation(auto_rotation)

        touch.Wait(object(), 0.25, poll_interval_ms=100)

        self.assertEqual([True, True, True], auto_rotation.calls)
        self.assertEqual([100, 100, 50], clock.sleeps)

    def test_absent_qmi_is_a_retryable_io_failure(self):
        with self.assertRaises(PeripheralIOError) as raised:
            qmi8658.QMI8658(bus=FakeBus(read_error=OSError("no device")))

        self.assertTrue(raised.exception.retryable)
        self.assertEqual("chip ID read", raised.exception.operation)

    def test_absent_touch_is_a_retryable_io_failure(self):
        with self.assertRaises(PeripheralIOError) as raised:
            self.make_touch(FakeBus(read_error=OSError("no device")))

        self.assertTrue(raised.exception.retryable)
        self.assertEqual("chip ID read", raised.exception.operation)

    def test_transient_qmi_detection_error_recovers_on_retry(self):
        attempts = []
        clock = FakeClock()

        def factory():
            attempts.append(True)
            if len(attempts) < 3:
                bus = FakeBus(read_error=OSError("bus busy"))
            else:
                bus = FakeBus({0x00: 0x05, 0x01: 0x42})
            return qmi8658.QMI8658(bus=bus)

        sensor = initialize_with_retry(
            factory,
            "QMI8658",
            clock=clock,
            logger=lambda message: None,
        )

        self.assertIsInstance(sensor, qmi8658.QMI8658)
        self.assertEqual(3, len(attempts))

    def test_runtime_qmi_read_error_is_classified(self):
        bus = FakeBus({0x00: 0x05, 0x01: 0x42})
        sensor = qmi8658.QMI8658(bus=bus)
        bus.read_error = OSError("bus disconnected")

        with self.assertRaises(PeripheralIOError) as raised:
            sensor.Read_XYZ()

        self.assertEqual("sample read", raised.exception.operation)


if __name__ == "__main__":
    unittest.main()
