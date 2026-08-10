import unittest

from battery import (
    ADC_MAX_VALUE,
    BatteryMonitor,
    raw_adc_to_voltage,
    voltage_to_percentage,
)


def raw_for_voltage(voltage):
    return int(round(voltage * ADC_MAX_VALUE / (3.3 * 3.0)))


class FakeADC:
    def __init__(self, values=None, error=None):
        self.values = list(values or [])
        self.error = error
        self.index = 0
        self.read_count = 0

    def read_u16(self):
        self.read_count += 1
        if self.error is not None:
            raise self.error
        value = self.values[self.index % len(self.values)]
        self.index += 1
        return value


class MutableRegister:
    def __init__(self, value=0, error=None):
        self.value = value
        self.error = error
        self.addresses = []

    def __call__(self, address):
        self.addresses.append(address)
        if self.error is not None:
            raise self.error
        return self.value


class BatteryTests(unittest.TestCase):
    def test_adc_conversion_uses_board_voltage_divider(self):
        self.assertEqual(0, raw_adc_to_voltage(0))
        self.assertAlmostEqual(9.9, raw_adc_to_voltage(ADC_MAX_VALUE))
        self.assertAlmostEqual(
            3.8,
            raw_adc_to_voltage(raw_for_voltage(3.8)),
            places=3,
        )

    def test_voltage_curve_is_bounded_and_interpolated(self):
        self.assertEqual(0, voltage_to_percentage(2.5))
        self.assertEqual(0, voltage_to_percentage(3.2))
        self.assertEqual(50, voltage_to_percentage(3.82))
        self.assertEqual(100, voltage_to_percentage(4.2))
        self.assertEqual(100, voltage_to_percentage(5.0))
        self.assertLess(
            voltage_to_percentage(3.90),
            voltage_to_percentage(4.00),
        )

    def test_battery_samples_are_averaged_before_estimating_percentage(self):
        adc = FakeADC(
            [raw_for_voltage(3.72), raw_for_voltage(3.92)]
        )
        monitor = BatteryMonitor(
            adc=adc,
            register_reader=MutableRegister(0),
            sample_count=2,
        )

        status = monitor.read_status()

        self.assertFalse(status.external_power)
        self.assertAlmostEqual(3.82, status.voltage, places=2)
        self.assertEqual(50, status.percentage)
        self.assertEqual(3, adc.read_count)

    def test_external_power_uses_fallback_without_sampling_vsys(self):
        adc = FakeADC(error=OSError("ADC should not be sampled"))
        monitor = BatteryMonitor(
            adc=adc,
            register_reader=MutableRegister(1),
        )

        status = monitor.read_status()

        self.assertTrue(status.external_power)
        self.assertEqual(100, status.percentage)
        self.assertIsNone(status.voltage)
        self.assertEqual(0, adc.read_count)

    def test_external_power_preserves_last_battery_only_estimate(self):
        power_register = MutableRegister(0)
        adc = FakeADC([raw_for_voltage(3.87)])
        monitor = BatteryMonitor(
            adc=adc,
            register_reader=power_register,
            sample_count=1,
        )

        battery_status = monitor.read_status()
        power_register.value = 1
        powered_status = monitor.read_status()

        self.assertEqual(60, battery_status.percentage)
        self.assertEqual(60, powered_status.percentage)
        self.assertTrue(powered_status.external_power)
        self.assertEqual(2, adc.read_count)

    def test_read_failures_return_an_unknown_gauge_without_raising(self):
        monitor = BatteryMonitor(
            adc=FakeADC(error=OSError("unavailable")),
            register_reader=MutableRegister(error=OSError("unavailable")),
            sample_count=1,
        )

        status = monitor.read_status()

        self.assertIsNone(status.percentage)
        self.assertFalse(status.external_power)
        self.assertIsNone(status.voltage)

    def test_sample_count_must_be_positive(self):
        with self.assertRaises(ValueError):
            BatteryMonitor(adc=FakeADC([0]), register_reader=lambda _: 0, sample_count=0)


if __name__ == "__main__":
    unittest.main()
