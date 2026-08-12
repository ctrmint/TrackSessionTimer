import unittest

from application import required_imu_sensitivity
from settings import DEFAULT_USER_PARAMS


class ApplicationTests(unittest.TestCase):
    def test_auto_dim_requests_imu_when_launch_and_rotation_do_not(self):
        user = dict(DEFAULT_USER_PARAMS)
        user["AUTO_DIM_ENABLED"] = True

        self.assertEqual(1, required_imu_sensitivity(user, "timer", 0))

    def test_disabled_sensor_features_do_not_request_imu(self):
        user = dict(DEFAULT_USER_PARAMS)

        self.assertEqual(0, required_imu_sensitivity(user, "timer", 0))

    def test_existing_imu_features_keep_their_initialization_policy(self):
        user = dict(DEFAULT_USER_PARAMS)
        self.assertEqual(1, required_imu_sensitivity(user, "g", 0))
        self.assertEqual(1, required_imu_sensitivity(user, "timer", "auto"))
        user["SENSITIVITY"] = 1.75
        self.assertEqual(1.75, required_imu_sensitivity(user, "timer", 0))


if __name__ == "__main__":
    unittest.main()
