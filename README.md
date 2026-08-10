# Track Session Timer - v4.2.0
Trackday or race session timer.

# Change log
## Version 4.2
### v4.2.0 [current]
* Added continuous automatic orientation using the onboard IMU, with display rendering and touch gestures rotating together.
* Kept Auto rotation safe during active timing and retained normal Timer operation if the IMU is unavailable.
* Replaced abrupt track-session warning backgrounds with a smooth, duration-proportional green, yellow, amber, and red gradient.
* Added a distinct deep-purple overrun background and automatic black-or-white timer text chosen for maximum contrast.
* Expanded hardware-independent regression coverage to 143 tests.

## Version 4.1
### v4.1.0
* Added persistent 0°, 90°, 180°, and 270° clockwise mounting orientations.
* Kept display rendering and directional touch gestures aligned at every orientation.
* Added live rotation preview with explicit save and safe cancellation in Settings.
* Expanded hardware-independent regression coverage to 125 tests.
## Version 4.0
### v4.0.0
* Added a hold-to-open operating-mode menu with persistent Timer and G modes.
* Added a responsive graphical live/peak G meter with a high-visibility peak arc.
* Added saved display-brightness control and confirmed restoration of defaults.
* Expanded hardware-independent regression coverage to 116 tests.
## Version 3.0
### v3.5
* Added the Caterham startup splash with a safe text fallback.
* Made Launch Mode orientation-independent, filtered, cancellable, and timeout-safe.
* Added controlled touch/IMU failure handling and normal-timer degraded operation.
* Reduced live-display transfers to visible changes while retaining responsive input polling.
* Added configuration prompts and a complete Ready-screen settings summary.
* Increased the countdown font and added fixed-width timer digits to prevent movement.
* Added a Ready-screen battery gauge with an external-power lightning indicator.
* Expanded hardware-independent regression coverage to 89 tests.
### v3.3
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

The code provided here offers a solution by creating a timer that is easy to read with clear digits. The track-session background continuously communicates progress: green at the start, yellow at one-third, amber at two-thirds, and red as scheduled time expires. Overrun is shown in deep purple with white text. Black or white timer text is selected automatically for the strongest contrast against every intermediate colour.

The timer is designed to support common session lengths, making it quick and easy to set up without the need to scroll through unnecessary minute intervals.

The timer utilizes the Waveshare 1.28-inch round touch display, allowing for configuration and operation through intuitive swipe gestures.

## Display font

The firmware includes a compact proportional bitmap font rendered directly at the display's native resolution. It replaces enlargement of MicroPython's 8x8 framebuffer font, so large countdown digits and labels retain smooth shapes instead of scaling into square pixels.

The running track and rest countdown uses the 74-pixel native font, the closest available pre-rendered size to a 10% increase from the previous 64-pixel countdown. Timer digits use equal-width cells, so changing figures do not move the centered countdown, maximum-G, or elapsed-time positions.

`font_data.py` and its flash-backed `font_data*.bin` glyph assets are generated from Montserrat SemiBold. The assets contain pre-rasterized native UI sizes, allowing the Pico to use its fast framebuffer blitter without holding the complete font in RAM. To regenerate them, install Pillow and run:

```sh
python tools/generate_font.py /path/to/Montserrat-SemiBold.otf font_data.py
```

The generated font data is distributed under the SIL Open Font License 1.1 in `FONT_LICENSE.txt`.

## Live display refresh

Track and rest sessions poll stop gestures every 50 ms while comparing the complete visible frame (remaining time, elapsed time, maximum G, font size, background, and text colour) with the previous frame. Track colour is interpolated from whole elapsed seconds, making the blend proportional to the selected duration while retaining a maximum of one normal full-screen transfer per displayed second. Maximum G is sampled at that same bounded polling rate but its visible value is latched to the displayed second, so sensing does not add framebuffer transfers. Touch-controller mode changes are also cached, so an unchanged gesture mode does not generate repeated I2C writes.

On the supported Waveshare board running MicroPython 1.21.0, five full live-screen redraws measured 56.2–65.4 ms. Input is therefore checked within 50 ms between redraws and within approximately 115 ms in the worst case when a gesture arrives immediately before a redraw. Five consecutive frames produced only the two register writes needed for the initial gesture-mode configuration and no rewrites on later frames.

## Startup splash

Startup now has two consecutive screens. First, the timer displays the supplied Caterham artwork on a black background sized for the 240x240 round display. The image is stored as a native `startup_splash.rgb565` framebuffer and loaded directly into the LCD's existing buffer, avoiding a second full-screen allocation on the RP2040. If the asset is absent or has the wrong size, the original text splash is shown instead.

The second screen uses high-contrast white text on black and identifies the hardware and runtime: board vendor and model, processor type, timer firmware, MicroPython version, and platform. Both screens default to two seconds. Their durations can be tuned independently in `params.json` with `STARTUP_SPLASH_DURATION_SEC` and `HARDWARE_SPLASH_DURATION_SEC`; zero skips the wait while still drawing that screen. Existing installations using `BOOT_DELAY_SEC` automatically apply that value to the first screen and use two seconds for the new hardware screen.

The original artwork and a device-layout preview are kept under `assets/`. To regenerate the runtime asset after changing the source image, install Pillow and run:

```sh
python tools/convert_splash.py assets/startup_splash.gif startup_splash.rgb565 \
  --preview assets/startup_splash_preview.png
```

## Operating modes and settings

Press and continuously hold the touchscreen for five seconds from the Timer Ready screen or G Mode to open the operating-mode menu. Releasing early cancels the hold. For safety, the menu cannot interrupt a running track/rest session or the Launch Mode wait. In menus, swipe left/right to choose, swipe up to select, and swipe down to cancel. The selected operating mode persists across restarts.

* **Timer Mode** retains the existing track, rest, and Launch Mode workflow. During a track session, a baseline-corrected value such as `MAX  1.23  g` appears in a compact, clearly spaced line above the countdown. The peak resets for each track session and remains visible through overrun. `MAX --` indicates that acceleration data is unavailable; timing and the stop gesture continue normally. Rest sessions do not show maximum G.
* **G Mode** calibrates the stationary QMI8658 baseline, then presents a responsive graphical round G meter rather than numeric telemetry. The green filled marker and short trail show the current filtered acceleration vector at the LCD's display-limited refresh rate. The red hollow marker records the maximum vector, while the red perimeter arc shows peak magnitude relative to the 4 g visual scale. Double-tap resets the trail and peak. Hold for five seconds to return to the mode menu.
* **Settings** provides 25%, 50%, 75%, and 100% brightness choices with immediate preview. Rotation offers **Auto** plus fixed 0°, 90°, 180°, and 270° clockwise mounting angles. Auto uses the onboard IMU to keep the display upright as the device turns; fixed choices continue to work without the IMU. In every case, touch gestures remain relative to the text on screen. Swipe up saves a preview; swipe down cancels and restores the previous brightness or orientation. **Restore defaults** requires confirmation, then restores Timer Mode, 100% brightness, fixed 0° rotation, 20-minute track/rest sessions, and disabled Launch Mode.

If the IMU is unavailable in G Mode, the firmware shows an actionable message and safely returns to Timer Mode. The timer remains usable.

### Automatic orientation

Auto rotation samples the QMI8658 at a bounded 10 Hz and filters the gravity vector before selecting one of the four display orientations. A new angle must remain stable for 300 ms and clearly dominate the adjacent axis, preventing rapid changes near 45° boundaries or during short acceleration spikes. The LCD controller and touch-direction mapping change together, and the current framebuffer is redrawn without allocating another 240×240 buffer. Active track/rest timing is neither reset nor paused.

An accelerometer cannot determine rotation around gravity when the screen is nearly horizontal. In that position Auto deliberately retains the last reliable angle until the device is upright enough to resolve again. Detected angles remain in RAM to avoid flash wear; `user.json` stores only the `auto` selection. If the IMU is missing or later fails, Auto freezes safely at its last angle and Timer Mode remains available. Choose a fixed angle to operate without automatic sensing.

## Supported hardware

Version 4.2.0 supports the integrated [Waveshare RP2040-Touch-LCD-1.28](https://www.waveshare.com/product/rp2040-touch-lcd-1.28.htm). This board combines the RP2040, GC9A01A 240x240 LCD, CST816S touchscreen, and QMI8658 IMU used by the firmware. The standalone 1.28-inch Touch LCD connected to a separate Raspberry Pi Pico uses a different pin map and is not currently supported.

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
mpremote connect auto fs cp application.py auto_rotation.py battery.py configuration.py font_data.py font_renderer.py g_force.py g_meter.py hardware.py hardware_splash.py hold_detector.py launch.py lcd_1inch28.py live_display.py operating_modes.py orientation.py params.json qmi8658.py ready_screen.py settings.py splash.py timer_mode.py timing.py touch_drive.py font_data*.bin startup_splash.rgb565 :
mpremote connect auto fs cp main.py :
mpremote connect auto reset
```

On a fresh installation, the firmware creates `user.json` with safe defaults. To start with the example preferences in this repository, copy it before `main.py`:

```sh
mpremote connect auto fs cp user.json :
```

When upgrading an existing device, omit that command so all of its saved user settings are preserved. The firmware adds a safe 0° rotation automatically when upgrading an older `user.json`.

### 4. Verify first boot

The display should show the Caterham v4.2.0 splash, the hardware-information splash, and then the green **Ready** screen. The serial console should report the loaded user parameters, `Success:Detected CST816T.`, and the touchscreen revision without a traceback.

If first boot fails:

* `OSError: Font bitmap is missing or truncated` means one or more `font_data*.bin` files were not copied.
* The original text-only splash means `startup_splash.rgb565` is missing or has the wrong size; repeat the application upload command.
* An import error generally means a `.py` support module was omitted; repeat the upload command and keep `main.py` last.
* No serial device after flashing usually indicates a charge-only USB cable, an incorrect UF2, or a board still in BOOT mode.
* A touchscreen hardware error is a controlled stop: check that this is the supported integrated board, then restart it. The serial message includes the failed operation or unexpected chip ID.
* An IMU hardware error disables Launch Mode and the session maximum-G reading for the current run. Swipe down to use the normal timer; `MAX --` confirms that timing remains available without the IMU.

### Peripheral failure policy

The touchscreen is required for safe operation. A transient touchscreen I2C failure is retried three times at 100 ms intervals; an unexpected chip ID is not retried. If detection still fails, the firmware shows an actionable error, logs the detailed cause over serial, and stops before using an incomplete touch object.

The QMI8658 IMU is optional unless a non-zero Launch Mode sensitivity, G Mode, or Auto rotation is selected. It is not initialized when none of those features needs it. Transient initialization failures receive three attempts, while an unexpected chip ID fails immediately. If initialization or a runtime sample fails, sensor-dependent behavior degrades safely and the standard timer remains available. Auto retains its last reliable orientation, and manual rotation choices remain usable. Saved choices are retained so the firmware can retry after a restart.

## Configuration files

Version 4.2.0 uses two separate configuration scopes:

* `params.json` contains system-owned choices and display behavior: `DURATION_VALUES`, `LAUNCH_SENSE_VALUES`, `VERSION`, `DISPLAY_DELAY_REST`, `DISPLAY_DELAY_REST_COLOUR`, `STARTUP_SPLASH_DURATION_SEC`, `HARDWARE_SPLASH_DURATION_SEC`, and `MODE_MENU_HOLD_SEC`.
* `user.json` contains the current user selections: `RACE_LENGTH` (track-session minutes), `REST_LENGTH` (pit-rest minutes), `SENSITIVITY` (launch threshold; `0` disables Launch Mode), `OPERATING_MODE` (`timer` or `g`), `BRIGHTNESS_PERCENT`, and `DISPLAY_ROTATION_DEG` (`auto` or the fixed clockwise device mounting angle `0`, `90`, `180`, or `270`).

Launch sensitivity is the filtered change in acceleration-vector magnitude from a 0.4-second stationary baseline, measured in g. This removes gravity and mounting orientation and handles acceleration on either side of every axis. Lower non-zero values are more sensitive. Detection requires three consecutive samples above the threshold; double-tap cancels the wait, and a 30-second timeout returns to the Ready screen. See `User Guide.md` for the practical meaning of every configured value.

The firmware has built-in system and user defaults. Missing, malformed, or unsupported user values are replaced with safe defaults and saved using the canonical keys above. Existing `TRACK_LENGTH`, `TRACK_SESSION_LENGTH`, and `REST_SESSION_LENGTH` user keys are migrated automatically, while older files gain Timer Mode, 100% brightness, and 0° rotation defaults.

## Host-side tests

Run the hardware-independent regression suite with:

```sh
python -m unittest discover -s tests -v
```

The suite uses fakes for time, continuous holds, touch gestures, automatic and fixed display rotation, gravity filtering/hysteresis, mode/settings navigation, graphical G vectors, display calls, filesystem operations, accelerometer samples, battery readings, and USB power state. Version 4.0.0 was additionally validated on the supported Waveshare board for both startup screens, Timer and G Mode boots, native G-meter rendering, LCD/font rendering, CST816S touch-state detection, QMI8658 sampling, saved settings, launch behavior, and the Ready-screen battery indicator.
