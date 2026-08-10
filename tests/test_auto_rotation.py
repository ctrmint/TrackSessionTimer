import unittest

from auto_rotation import (
    AutoOrientationDetector,
    AutoRotationController,
    classify_rotation,
)
from hardware import PeripheralIOError


class FakeClock:
    def __init__(self):
        self.now = 0
        self.sleeps = []

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, current, previous):
        return current - previous

    def sleep_ms(self, milliseconds):
        self.sleeps.append(milliseconds)
        self.now += milliseconds


class FakeSensor:
    def __init__(self, samples=None, error=None):
        self.samples = list(samples or [])
        self.error = error
        self.reads = 0

    def Read_XYZ(self):
        self.reads += 1
        if self.error is not None:
            raise self.error
        if len(self.samples) > 1:
            return self.samples.pop(0)
        return self.samples[0]


class FakeLCD:
    def __init__(self):
        self.rotations = []
        self.shows = 0

    def set_rotation(self, rotation):
        self.rotations.append(rotation)

    def show(self):
        self.shows += 1


class FakeTouch:
    def __init__(self):
        self.rotations = []

    def Set_Rotation(self, rotation):
        self.rotations.append(rotation)


class AutoRotationTests(unittest.TestCase):
    def test_board_axes_map_to_all_four_mount_rotations(self):
        expected = {
            (0.0, -1.0, 0.0): 90,
            (-1.0, 0.0, 0.0): 0,
            (0.0, 1.0, 0.0): 270,
            (1.0, 0.0, 0.0): 180,
        }
        for sample, rotation in expected.items():
            with self.subTest(sample=sample):
                self.assertEqual(rotation, classify_rotation(sample))

    def test_diagonal_flat_and_dynamic_samples_are_ambiguous(self):
        for sample in (
            (-0.70, -0.70, 0.0),
            (0.10, 0.10, 0.98),
            (2.0, 0.0, 0.0),
        ):
            with self.subTest(sample=sample):
                self.assertIsNone(classify_rotation(sample))

    def test_candidate_must_remain_stable_before_switching(self):
        clock = FakeClock()
        detector = AutoOrientationDetector(
            initial_rotation=0,
            filter_alpha=1,
            stable_ms=300,
            clock=clock,
        )

        self.assertIsNone(detector.update((0, -1, 0)))
        clock.now = 299
        self.assertIsNone(detector.update((0, -1, 0)))
        self.assertEqual(0, detector.current_rotation)
        clock.now = 300
        self.assertEqual(90, detector.update((0, -1, 0)))
        self.assertEqual(90, detector.current_rotation)

    def test_ambiguous_sample_cancels_pending_switch(self):
        clock = FakeClock()
        detector = AutoOrientationDetector(
            initial_rotation=0,
            filter_alpha=1,
            stable_ms=300,
            clock=clock,
        )

        detector.update((0, -1, 0))
        clock.now = 200
        detector.update((-0.70, -0.70, 0))
        clock.now = 500
        self.assertIsNone(detector.update((0, -1, 0)))
        self.assertEqual(0, detector.current_rotation)

    def test_unreliable_position_retains_last_stable_rotation(self):
        detector = AutoOrientationDetector(initial_rotation=180)

        self.assertIsNone(detector.update((0.1, 0.1, 0.98), now_ms=0))
        self.assertEqual(180, detector.current_rotation)
        self.assertFalse(detector.reliable)

    def test_controller_updates_lcd_touch_and_existing_frame_once(self):
        clock = FakeClock()
        sensor = FakeSensor([(0, -1, 0)])
        lcd = FakeLCD()
        touch = FakeTouch()
        detector = AutoOrientationDetector(
            initial_rotation=0,
            filter_alpha=1,
            stable_ms=100,
            clock=clock,
        )
        controller = AutoRotationController(
            sensor,
            lcd,
            touch,
            detector=detector,
            clock=clock,
            sample_interval_ms=100,
        )
        controller.enable()

        self.assertFalse(controller.update())
        self.assertFalse(controller.update())
        self.assertEqual(1, sensor.reads)
        clock.now = 100
        self.assertTrue(controller.update())

        self.assertEqual([90], lcd.rotations)
        self.assertEqual([90], touch.rotations)
        self.assertEqual(1, lcd.shows)

    def test_controller_freezes_safely_after_sensor_failure(self):
        error = PeripheralIOError("QMI8658", "sample read", "disconnected")
        controller = AutoRotationController(
            FakeSensor(error=error),
            FakeLCD(),
            FakeTouch(),
            logger=lambda _message: None,
        )
        controller.enable()

        self.assertFalse(controller.update(force=True))
        self.assertFalse(controller.available)
        self.assertEqual(0, controller.current_rotation)
        self.assertEqual("IMU unavailable", controller.status_text())

    def test_sensor_is_initialized_lazily_for_auto_preview(self):
        sensor = FakeSensor([(-1, 0, 0)])
        attempts = []

        def factory():
            attempts.append(True)
            return sensor, None

        controller = AutoRotationController(
            None,
            FakeLCD(),
            FakeTouch(),
            sensor_factory=factory,
        )

        self.assertTrue(controller.enable())
        self.assertEqual([True], attempts)
        self.assertIs(sensor, controller.sensor)


if __name__ == "__main__":
    unittest.main()
