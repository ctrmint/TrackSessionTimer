# Hardware Bill of Materials

This BOM documents the physical reference build used by Track Session Timer. It deliberately identifies the complete cased product, because several visually similar Waveshare boards and display modules are not the same hardware.

## Correct integrated hardware variant

> **Order `RP2040-Touch-LCD-1.28-B`, Waveshare SKU `26371`.**

The `-B` suffix identifies the version supplied as one assembled unit with the Raspberry Pi-designed RP2040 hardware, round touch display, **CNC metal case**, and acrylic dull-polish bottom plate. A separate Raspberry Pi Pico, display module, or enclosure is not required and must not be added as another core BOM item.

The uncased `RP2040-Touch-LCD-1.28` is from the same electronics family, but it is not the exact physical reference build documented here. The product named `RP2040-LCD-1.28-B` omits **Touch** from its part number and is a different, non-touch variant.

## Core BOM

| Ref | Qty | Requirement | Manufacturer / part | Purpose and notes |
| --- | ---: | --- | --- | --- |
| H1 | 1 | Required | Waveshare [`RP2040-Touch-LCD-1.28-B`](https://www.waveshare.com/RP2040-Touch-LCD-1.28-B.htm), SKU 26371 | Complete processor, touch display, motion sensor, power-management board and case assembly. This is the exact reference variant. |
| H2 | 1 | Required for installation and USB operation | USB data-and-power cable, USB Type-C at the timer end | Must carry data, not charge only. Select the host-end connector to suit the setup computer or regulated USB supply. Not listed in the Waveshare package contents. |
| M1 | 1 set | Required for vehicle installation | Application-specific dashboard mount, fasteners and strain relief | Must securely retain the complete cased H1 unit under vibration without obscuring controls, instruments or visibility. No universal mount is specified by this repository. |
| P1 | 1 | Required when vehicle-powered | Fused, automotive-rated, regulated 5 V USB supply | Converts vehicle power to a stable USB supply for H1. Select and fuse it for the vehicle installation. Never connect nominal 12 V vehicle power directly to USB or the battery header. |

For bench installation and firmware updates, P1 may be replaced by a computer USB port or other suitable regulated USB source.

## Optional battery power

| Ref | Qty | Requirement | Specification | Purpose and notes |
| --- | ---: | --- | --- | --- |
| P2 | 1 | Optional | Protected, single-cell 3.7 V Li-ion battery with an MX1.25 2-pin lead | H1 provides an onboard charge/discharge manager and MX1.25 battery header. Confirm connector polarity against the Waveshare documentation and the actual battery before connection. Battery capacity, mounting and enclosure clearance are installation-specific. |

A battery is not required when the timer is continuously USB-powered. The firmware's lightning symbol indicates external USB power; it cannot determine an isolated battery's exact charge while USB is present.

## What H1 already contains

The following are integrated into `RP2040-Touch-LCD-1.28-B` and are **not separate purchases**:

| Integrated subsystem | Reference specification |
| --- | --- |
| Processor | Raspberry Pi-designed RP2040, dual-core Arm Cortex-M0+, up to 133 MHz, with 264 KB SRAM |
| Program storage | 16 MB W25Q128JVSIQ NOR flash |
| Display | 1.28-inch round IPS LCD, 240 × 240 pixels, 65K colour, GC9A01A controller over SPI |
| Touch input | CST816S capacitive touch controller over I2C |
| Motion sensing | QMI8658 6-axis IMU: 3-axis accelerometer and 3-axis gyroscope |
| USB and controls | USB Type-C, BOOT button and RESET button |
| Battery support | ETA6096 Li-ion charge/discharge manager and MX1.25 2-pin header for a 3.7 V cell |
| Regulation | RT9013-33GB 500 mA low-dropout regulator |
| Enclosure | CNC metal case with acrylic dull-polish bottom plate |

The manufacturer's package listing includes one `RP2040-Touch-LCD-1.28-B` and one SH1.0 12-pin cable. The current Track Session Timer build does not require the SH1.0 cable because its display, touch controller and IMU are already wired internally.

## Variant check before ordering

| Product | Use for this reference build? | Reason |
| --- | --- | --- |
| `RP2040-Touch-LCD-1.28-B` | **Yes** | Exact cased, touch-enabled RP2040 assembly; SKU 26371. |
| `RP2040-Touch-LCD-1.28` | No for an exact replica | Closely related but supplied without the integrated CNC case. |
| `RP2040-LCD-1.28-B` | **No** | Different non-touch product; the firmware requires touch input for safe operation. |
| `1.28inch Touch LCD` | **No** | Display module only. It needs a separate controller board and uses a different wiring arrangement. |
| RP2350 or ESP32 1.28-inch variants | **No** | Different processor platform and firmware target. |

When checking a listing, require all three identifiers: **RP2040**, **Touch**, and the **`-B` cased suffix**.

## Authoritative references

- [Waveshare RP2040-Touch-LCD-1.28-B product page](https://www.waveshare.com/RP2040-Touch-LCD-1.28-B.htm) — exact part number, SKU, case, onboard hardware and package contents.
- [Waveshare RP2040-Touch-LCD-1.28 wiki](https://www.waveshare.com/wiki/RP2040-Touch-LCD-1.28) — shared electronics specifications, display/touch controllers, IMU and battery connector requirements.
- [Track Session Timer supported hardware and pin map](../README.md#supported-hardware) — firmware-specific compatibility and fixed internal connections.

Manufacturer details were last checked on 12 August 2026. Product listings can change; verify the part number and SKU before purchasing.
