# Track Session Timer - v3.3
Trackday or race session timer.

# Change log
## Version 3.0
### v3.3 [current]
* Smooth proportional font rendering at native display resolution.
* Centered typography and improved layout across timer, configuration, and diagnostic screens.
* Hardware-verified framebuffer rendering, touchscreen startup, and QMI8658 initialization on the supported Waveshare board.
### v3.2
* User settings stored between reboots, [track session length, rest session length, launch mode]
* Introduction of system params and user params files.
### v3.1 
* Accelerometer based timer activation or launch mode
* Configurable sensitivity for accelerometer
* Code refactoring improvements, including dedicated include for accelerometer
### v3.0 
* No Release
## Version 2.0
* Faster UI and more responsive touch screen.
* Greater control over session settings, includes ability to define track session length and rest session length.
* Improved UI colours for 85% and 95% session expiry.

See user guide.

### Fixes
* Incorrect pin out. 

## Background
Managing time on the track can be challenging, whether it's during a track day or a race. Many competitors in the Seven category use kitchen timers mounted on their dashboards. However, these timers can be large, awkward, and difficult to read, requiring drivers to interpret small digits mid-race.

The code provided here offers a solution by creating a timer that is easy to read with clear digits. Additionally, it features background colors that change to indicate key moments during the session, such as when 85% and 95% of the session time has elapsed.

The timer is designed to support common session lengths, making it quick and easy to set up without the need to scroll through unnecessary minute intervals.

The timer utilizes the Waveshare 1.28-inch round touch display, allowing for configuration and operation through intuitive swipe gestures.

## Display font

The firmware includes a compact proportional bitmap font rendered directly at the display's native resolution. It replaces enlargement of MicroPython's 8x8 framebuffer font, so large countdown digits and labels retain smooth shapes instead of scaling into square pixels.

The running track and rest countdown uses the 74-pixel native font, the closest available pre-rendered size to a 10% increase from the previous 64-pixel countdown. Timer digits use equal-width cells, so changing figures do not move the centered countdown or elapsed-time positions.

`font_data.py` and its flash-backed `font_data*.bin` glyph assets are generated from Montserrat SemiBold. The assets contain pre-rasterized native UI sizes, allowing the Pico to use its fast framebuffer blitter without holding the complete font in RAM. To regenerate them, install Pillow and run:

```sh
python tools/generate_font.py /path/to/Montserrat-SemiBold.otf font_data.py
```

The generated font data is distributed under the SIL Open Font License 1.1 in `FONT_LICENSE.txt`.

## Live display refresh

Track and rest sessions poll stop gestures every 50 ms while comparing the complete visible frame (remaining time, elapsed time, font size, background, and text colour) with the previous frame. The 115,200-byte framebuffer is transferred only when a displayed second or warning state changes, normally reducing continuous redraws to one per second. Touch-controller mode changes are also cached, so an unchanged gesture mode does not generate repeated I2C writes.

On the supported Waveshare board running MicroPython 1.21.0, five full live-screen redraws measured 56.2–65.4 ms. Input is therefore checked within 50 ms between redraws and within approximately 115 ms in the worst case when a gesture arrives immediately before a redraw. Five consecutive frames produced only the two register writes needed for the initial gesture-mode configuration and no rewrites on later frames.

## Startup splash

At startup, the timer displays the supplied Caterham artwork on a black background sized for the 240x240 round display. The image is stored as a native `startup_splash.rgb565` framebuffer and loaded directly into the LCD's existing buffer, avoiding a second full-screen allocation on the RP2040. If the asset is absent or has the wrong size, the original text splash is shown instead.

The original artwork and a device-layout preview are kept under `assets/`. To regenerate the runtime asset after changing the source image, install Pillow and run:

```sh
python tools/convert_splash.py assets/startup_splash.gif startup_splash.rgb565 \
  --preview assets/startup_splash_preview.png
```

## Supported hardware

Version 3.3 supports the integrated [Waveshare RP2040-Touch-LCD-1.28](https://www.waveshare.com/product/rp2040-touch-lcd-1.28.htm). This board combines the RP2040, GC9A01A 240x240 LCD, CST816S touchscreen, and QMI8658 IMU used by the firmware. The standalone 1.28-inch Touch LCD connected to a separate Raspberry Pi Pico uses a different pin map and is not currently supported.

### Onboard pin map

These are fixed internal board connections; no external display wiring is required.

| Function | RP2040 pin |
| --- | ---: |
| LCD SPI SCLK | GP10 |
| LCD SPI MOSI | GP11 |
| LCD CS | GP9 |
| LCD DC | GP8 |
| LCD reset | GP13 |
| LCD backlight | GP25 |
| Touch/IMU I2C SDA | GP6 |
| Touch/IMU I2C SCL | GP7 |
| Touch interrupt | GP21 |
| Touch reset | GP22 |
| Battery ADC | GP29 |

## Ready-screen battery indicator

The top of the Ready screen contains a standard horizontal battery gauge. Its
black fill is an estimated 0–100% state of charge derived from eight averaged
GP29 readings and the board's 200k/100k `VSYS` divider. A white lightning bolt
appears through the icon whenever the RP2040 USB controller detects external
VBUS power. The 35×16-pixel graphic is centered at the top of the round display
and ends 12 pixels before the `Ready` heading, so it does not obscure the title
or settings summary.

The gauge is an approximate 3.7 V Li-ion voltage estimate; cell temperature,
load, age, and chemistry affect accuracy. The board cannot measure isolated
battery voltage while USB supplies `VSYS`. In that state the bolt is exact, but
the fill retains the last battery-only estimate from the current boot. If the
device starts on USB, a full powered-state fill is shown until a battery-only
measurement becomes available. An unreadable ADC leaves an empty outline rather
than interrupting timer startup.

## Installation

The application runs on MicroPython. BOOT mode is used only to flash the MicroPython UF2; application files are transferred afterward through the MicroPython serial connection.

### 1. Flash MicroPython

1. Download a stable RP2040 UF2 from the [MicroPython Raspberry Pi Pico download page](https://micropython.org/download/RPI_PICO/) or the [Waveshare board wiki](https://www.waveshare.com/wiki/RP2040-Touch-LCD-1.28).
2. Connect the board with a USB data cable.
3. Hold **BOOT**, press and release **RESET**, then release **BOOT**. The `RPI-RP2` storage volume should appear.
4. Copy only the MicroPython `.uf2` file to `RPI-RP2`. The board restarts and exposes a serial device such as `/dev/ttyACM0` or a COM port.

### 2. Install the transfer tool

From a terminal on the computer:

```sh
python -m pip install mpremote
mpremote connect auto exec "import os; print(os.uname())"
```

The second command should identify an RP2040 MicroPython board.

### 3. Upload the application

Run these commands from the repository root. Supporting files and font assets are copied first; `main.py` is installed last as the automatic entry point.

```sh
mpremote connect auto fs cp battery.py configuration.py font_data.py font_renderer.py hardware.py launch.py lcd_1inch28.py live_display.py params.json qmi8658.py ready_screen.py settings.py splash.py timing.py touch_drive.py font_data*.bin startup_splash.rgb565 :
mpremote connect auto fs cp main.py :
mpremote connect auto reset
```

On a fresh installation, the firmware creates `user.json` with safe defaults. To start with the example preferences in this repository, copy it before `main.py`:

```sh
mpremote connect auto fs cp user.json :
```

When upgrading an existing device, omit that command so its saved track duration, rest duration, and launch sensitivity are preserved.

### 4. Verify first boot

The display should show the Caterham v3.3 splash and then the green **Ready** screen. The serial console should report the loaded user parameters, `Success:Detected CST816T.`, and the touchscreen revision without a traceback.

If first boot fails:

* `OSError: Font bitmap is missing or truncated` means one or more `font_data*.bin` files were not copied.
* The original text-only splash means `startup_splash.rgb565` is missing or has the wrong size; repeat the application upload command.
* An import error generally means a `.py` support module was omitted; repeat the upload command and keep `main.py` last.
* No serial device after flashing usually indicates a charge-only USB cable, an incorrect UF2, or a board still in BOOT mode.
* A touchscreen hardware error is a controlled stop: check that this is the supported integrated board, then restart it. The serial message includes the failed operation or unexpected chip ID.
* An IMU hardware error disables Launch Mode for the current run. Swipe down to use the normal timer, which remains available without the IMU.

### Peripheral failure policy

The touchscreen is required for safe operation. A transient touchscreen I2C failure is retried three times at 100 ms intervals; an unexpected chip ID is not retried. If detection still fails, the firmware shows an actionable error, logs the detailed cause over serial, and stops before using an incomplete touch object.

The QMI8658 IMU is optional unless a non-zero Launch Mode sensitivity is selected. It is not initialized when Launch Mode is off. Transient initialization failures receive the same three attempts, while an unexpected chip ID fails immediately. If initialization or a launch-time sample fails, Launch Mode is disabled for the current run and the standard swipe-down timer remains available. The saved sensitivity is retained so the firmware can retry after a restart or the next Launch Mode configuration change.

## Configuration files

Version 3.2 uses two separate configuration scopes:

* `params.json` contains system-owned choices and display behavior: `DURATION_VALUES`, `LAUNCH_SENSE_VALUES`, `VERSION`, `DISPLAY_DELAY_REST`, `DISPLAY_DELAY_REST_COLOUR`, and `BOOT_DELAY_SEC`.
* `user.json` contains the current user selections: `RACE_LENGTH` (track-session minutes), `REST_LENGTH` (pit-rest minutes), and `SENSITIVITY` (launch threshold; `0` disables Launch Mode).

Launch sensitivity is the filtered change in acceleration-vector magnitude from a 0.4-second stationary baseline, measured in g. This removes gravity and mounting orientation and handles acceleration on either side of every axis. Lower non-zero values are more sensitive. Detection requires three consecutive samples above the threshold; double-tap cancels the wait, and a 30-second timeout returns to the Ready screen. See `User Guide.md` for the practical meaning of every configured value.

The firmware has built-in system and user defaults. Missing, malformed, or unsupported user values are replaced with safe defaults and saved using the canonical keys above. Existing `TRACK_LENGTH`, `TRACK_SESSION_LENGTH`, and `REST_SESSION_LENGTH` user keys are migrated automatically.

## Host-side tests

Run the hardware-independent regression suite with:

```sh
python -m unittest discover -s tests -v
```

The suite uses fakes for time, touch gestures, display calls, filesystem operations, and accelerometer samples. Version 3.3 was additionally validated on the supported Waveshare board for boot, LCD/font rendering, CST816S touchscreen detection, QMI8658 initialization, saved settings, and launch behavior.
