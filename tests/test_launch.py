import unittest

from launch import accel_launch


class FakeAccelerometer:
    def __init__(self, samples):
        self._samples = iter(samples)
        self.read_count = 0

    def Read_XYZ(self):
        self.read_count += 1
        return next(self._samples)


class LaunchLoopTests(unittest.TestCase):
    def test_zero_sensitivity_bypasses_sensor_reads(self):
        sensor = FakeAccelerometer([])
        self.assertTrue(accel_launch(sensor, sensitivity=0))
        self.assertEqual(0, sensor.read_count)

    def test_existing_all_axis_condition_is_deterministic(self):
        # The threshold algorithm is intentionally unchanged here; see issue #3.
        sensor = FakeAccelerometer([
            [2, 0, 0, 0, 0, 0],
            [2, 2, 2, 0, 0, 0],
        ])
        self.assertTrue(accel_launch(sensor, sensitivity=1))
        self.assertEqual(2, sensor.read_count)


if __name__ == "__main__":
    unittest.main()
