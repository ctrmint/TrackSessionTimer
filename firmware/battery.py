"""Battery voltage estimation and external USB-power detection."""

BATTERY_ADC_PIN = 29
ADC_MAX_VALUE = 65535
ADC_REFERENCE_VOLTS = 3.3
VOLTAGE_DIVIDER_RATIO = 3.0

# RP2040 USBCTRL_REGS.SIE_STATUS.VBUS_DETECTED. The Waveshare schematic
# connects USB VBUS to the RP2040 USB PHY, while BAT_ADC measures divided VSYS.
USB_SIE_STATUS_ADDRESS = 0x50110050
USB_VBUS_DETECTED_MASK = 0x00000001

DEFAULT_SAMPLE_COUNT = 8
ADC_SETTLE_READS = 1
EXTERNAL_POWER_FALLBACK_PERCENT = 100

# Approximate unloaded 3.7 V Li-ion discharge curve. Voltage under load varies
# with the cell and temperature, so this is intentionally presented as an
# estimate rather than laboratory state-of-charge measurement.
LI_ION_PERCENTAGE_CURVE = (
    (3.20, 0),
    (3.50, 10),
    (3.65, 20),
    (3.72, 30),
    (3.77, 40),
    (3.82, 50),
    (3.87, 60),
    (3.92, 70),
    (3.98, 80),
    (4.08, 90),
    (4.20, 100),
)


class BatteryStatus:
    """One display-ready power reading."""

    def __init__(self, percentage, external_power, voltage=None, estimated=True):
        self.percentage = percentage
        self.external_power = bool(external_power)
        self.voltage = voltage
        self.estimated = bool(estimated)


def raw_adc_to_voltage(raw_value):
    """Convert a 16-bit GP29 reading through the board's 200k/100k divider."""
    raw_value = max(0, min(ADC_MAX_VALUE, int(raw_value)))
    return (
        raw_value
        * ADC_REFERENCE_VOLTS
        * VOLTAGE_DIVIDER_RATIO
        / ADC_MAX_VALUE
    )


def voltage_to_percentage(voltage):
    """Map battery voltage to a bounded percentage using linear interpolation."""
    voltage = float(voltage)
    if voltage <= LI_ION_PERCENTAGE_CURVE[0][0]:
        return 0
    if voltage >= LI_ION_PERCENTAGE_CURVE[-1][0]:
        return 100

    for index in range(1, len(LI_ION_PERCENTAGE_CURVE)):
        upper_voltage, upper_percentage = LI_ION_PERCENTAGE_CURVE[index]
        if voltage <= upper_voltage:
            lower_voltage, lower_percentage = LI_ION_PERCENTAGE_CURVE[index - 1]
            position = (voltage - lower_voltage) / (
                upper_voltage - lower_voltage
            )
            percentage = lower_percentage + position * (
                upper_percentage - lower_percentage
            )
            return int(round(percentage))

    return 100


class BatteryMonitor:
    """Read a stable Ready-screen battery status without making boot fragile."""

    def __init__(
        self,
        adc=None,
        register_reader=None,
        sample_count=DEFAULT_SAMPLE_COUNT,
        external_fallback=EXTERNAL_POWER_FALLBACK_PERCENT,
    ):
        if int(sample_count) <= 0:
            raise ValueError("sample_count must be positive")

        self.sample_count = int(sample_count)
        self.external_fallback = max(0, min(100, int(external_fallback)))
        self.last_battery_percentage = None

        if adc is None:
            try:
                from machine import ADC, Pin

                adc = ADC(Pin(BATTERY_ADC_PIN))
            except Exception:
                adc = None
        self.adc = adc

        if register_reader is None:
            try:
                from machine import mem32

                register_reader = lambda address: mem32[address]
            except Exception:
                register_reader = None
        self.register_reader = register_reader

    def _external_power(self):
        if self.register_reader is None:
            return None
        try:
            status = self.register_reader(USB_SIE_STATUS_ADDRESS)
            return bool(status & USB_VBUS_DETECTED_MASK)
        except Exception:
            return None

    def _battery_voltage(self):
        if self.adc is None:
            return None
        try:
            # The RP2040 ADC mux can return a stale first conversion after the
            # channel is opened. Discard it before averaging the visible value.
            for _ in range(ADC_SETTLE_READS):
                self.adc.read_u16()
            total = 0
            for _ in range(self.sample_count):
                total += self.adc.read_u16()
            return raw_adc_to_voltage(total / self.sample_count)
        except Exception:
            return None

    def read_status(self):
        """Return the best honest status available for the current power path."""
        external_power = self._external_power()

        if external_power is True:
            percentage = self.last_battery_percentage
            if percentage is None:
                percentage = self.external_fallback
            return BatteryStatus(
                percentage,
                external_power=True,
                voltage=None,
                estimated=True,
            )

        voltage = self._battery_voltage()
        if voltage is None:
            return BatteryStatus(
                self.last_battery_percentage,
                external_power=False,
                voltage=None,
                estimated=True,
            )

        percentage = voltage_to_percentage(voltage)
        if external_power is False:
            self.last_battery_percentage = percentage

        return BatteryStatus(
            percentage,
            external_power=False,
            voltage=voltage,
            estimated=True,
        )
