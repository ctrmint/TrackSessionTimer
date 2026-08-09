import unittest

from timing import SessionTracker, secs_to_mins_secs


class FakeClock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


class TimingTests(unittest.TestCase):
    def test_session_thresholds_and_overrun_phase(self):
        clock = FakeClock(100)
        session = SessionTracker(duration_mins=10, stype="track", clock=clock)
        session.start_session()

        self.assertEqual(100, session.start_time)
        self.assertEqual(700, session.end_time)
        self.assertEqual(610, session.last_15)
        self.assertEqual(670, session.last_5)
        self.assertEqual("running", session.phase(609))
        self.assertEqual("last_15", session.phase(610))
        self.assertEqual("last_5", session.phase(670))
        self.assertEqual("overrun", session.phase(700))
        self.assertTrue(session.live)

    def test_ready_phase_before_session_start(self):
        self.assertEqual("ready", SessionTracker(duration_mins=10).phase())

    def test_time_formatting_uses_whole_seconds(self):
        self.assertEqual("00:00", secs_to_mins_secs(0))
        self.assertEqual("01:01", secs_to_mins_secs(61))
        self.assertEqual("01:01", secs_to_mins_secs(61.9))

    def test_string_representation_is_complete(self):
        self.assertEqual(
            "SessionTracker(stype=rest, duration_mins=5)",
            str(SessionTracker(duration_mins=5, stype="rest")),
        )


if __name__ == "__main__":
    unittest.main()
