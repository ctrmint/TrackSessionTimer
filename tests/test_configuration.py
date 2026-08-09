import unittest
from types import SimpleNamespace

from configuration import set_sensitivity, set_session


class FakeTouch:
    def __init__(self, gestures):
        self._gestures = iter(gestures)
        self.screens = []

    def ControlScreen(self, lcd, text_array=None, back_colour=None):
        self.screens.append((lcd, text_array, back_colour))

    def GetGesture(self, lcd):
        return next(self._gestures)


class ConfigurationEditorTests(unittest.TestCase):
    duration_values = [1, 5, 10, 15, 20, 25, 30, 40, 50, 60]
    sensitivity_values = [0, 0.5, 1, 1.25, 1.5, 1.75, 2, 2.5, 3.5, 4]

    def test_session_immediate_save_preserves_every_allowed_value(self):
        for current in self.duration_values:
            with self.subTest(current=current):
                session = SimpleNamespace(duration_mins=current)
                touch = FakeTouch(["up"])
                selected = set_session(
                    LCD=object(),
                    Touch=touch,
                    session=session,
                    session_values=self.duration_values,
                    session_name="Track",
                )
                self.assertEqual(current, selected)
                self.assertEqual(current, session.duration_mins)
                self.assertEqual(str(current), touch.screens[0][1][0][0])

    def test_sensitivity_immediate_save_preserves_every_allowed_value(self):
        for current in self.sensitivity_values:
            with self.subTest(current=current):
                touch = FakeTouch(["up"])
                selected = set_sensitivity(
                    LCD=object(),
                    Touch=touch,
                    sensitivity_values=self.sensitivity_values,
                    sensitivity=current,
                )
                self.assertEqual(current, selected)
                self.assertEqual(str(current), touch.screens[0][1][0][0])

    def test_session_navigation_wraps_in_both_directions(self):
        session = SimpleNamespace(duration_mins=self.duration_values[0])
        selected = set_session(
            LCD=object(),
            Touch=FakeTouch(["left", "up"]),
            session=session,
            session_values=self.duration_values,
            session_name="Track",
        )
        self.assertEqual(self.duration_values[-1], selected)

        session.duration_mins = self.duration_values[-1]
        selected = set_session(
            LCD=object(),
            Touch=FakeTouch(["right", "up"]),
            session=session,
            session_values=self.duration_values,
            session_name="Track",
        )
        self.assertEqual(self.duration_values[0], selected)

    def test_sensitivity_navigation_wraps_in_both_directions(self):
        selected = set_sensitivity(
            LCD=object(),
            Touch=FakeTouch(["left", "up"]),
            sensitivity_values=self.sensitivity_values,
            sensitivity=self.sensitivity_values[0],
        )
        self.assertEqual(self.sensitivity_values[-1], selected)

        selected = set_sensitivity(
            LCD=object(),
            Touch=FakeTouch(["right", "up"]),
            sensitivity_values=self.sensitivity_values,
            sensitivity=self.sensitivity_values[-1],
        )
        self.assertEqual(self.sensitivity_values[0], selected)

    def test_invalid_stored_values_fall_back_to_first_option(self):
        session = SimpleNamespace(duration_mins=999)
        self.assertEqual(
            self.duration_values[0],
            set_session(
                LCD=object(),
                Touch=FakeTouch(["up"]),
                session=session,
                session_values=self.duration_values,
                session_name="Track",
            ),
        )
        self.assertEqual(
            self.sensitivity_values[0],
            set_sensitivity(
                LCD=object(),
                Touch=FakeTouch(["up"]),
                sensitivity_values=self.sensitivity_values,
                sensitivity=999,
            ),
        )

    def test_empty_allowed_values_are_rejected(self):
        with self.assertRaises(ValueError):
            set_session(
                LCD=object(),
                Touch=FakeTouch(["up"]),
                session=SimpleNamespace(duration_mins=20),
                session_values=[],
                session_name="Track",
            )
        with self.assertRaises(ValueError):
            set_sensitivity(
                LCD=object(),
                Touch=FakeTouch(["up"]),
                sensitivity_values=[],
                sensitivity=0,
            )


if __name__ == "__main__":
    unittest.main()
