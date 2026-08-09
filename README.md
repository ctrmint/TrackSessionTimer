# Track Session Timer - v3.2
Trackday or race session timer.

# Change log
## Version 3.0
### v3.2 [current]
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

## Hardware Requirements 
* Raspberry Pico
* Waveshare 1.28-inch round touch display (https://www.waveshare.com/1.28inch-touch-lcd.htm)

Following setup instructions for the display, connecting it to the required pins on the pico, these should be as follows although may vary depending on implementation.

### Hardware Connections
* VCC    	->    	3.3V
* GND    	->    	GND
* MISO    ->    	12
* MOSI    ->    	11
* SCLK    ->    	10
* LCD_CS  ->    	9
* LCD_DC  ->    	14
* LCD_RST ->    	8
* LCD_BL  ->    	15
* TP_SDA  ->      6
* TP_SCL  ->      7
* TP_INT  ->      16
* TP_RST  ->      17

## Setup
The instructions enable the software on the required hardware.   These instructions do not cover the physical installation or support for the hardware. 
### Pico
* Ensure you rcomputer has the Python (.py) files and also the latest uf2 file (soure from Raspberry foundation)
* Press and hold the BOOTSEL button 
* Connect the Pico to your computer via the appropriate USB cable, after connecting release the BOOTSEL button, the PICO should be mounted to your filesystem.
* Copy the .py files
* Copy the uf2 file, the Pico should restart, and the timer automatically starts.

## Configuration files

Version 3.2 uses two separate configuration scopes:

* `params.json` contains system-owned choices and display behavior: `DURATION_VALUES`, `LAUNCH_SENSE_VALUES`, `VERSION`, `DISPLAY_DELAY_REST`, `DISPLAY_DELAY_REST_COLOUR`, and `BOOT_DELAY_SEC`.
* `user.json` contains the current user selections: `RACE_LENGTH` (track-session minutes), `REST_LENGTH` (pit-rest minutes), and `SENSITIVITY` (launch threshold; `0` disables Launch Mode).

The firmware has built-in system and user defaults. Missing, malformed, or unsupported user values are replaced with safe defaults and saved using the canonical keys above. Existing `TRACK_LENGTH`, `TRACK_SESSION_LENGTH`, and `REST_SESSION_LENGTH` user keys are migrated automatically.

## Host-side tests

Run the hardware-independent regression suite with:

```sh
python -m unittest discover -s tests -v
```

The suite uses fakes for time, touch gestures, display calls, filesystem operations, and accelerometer samples. It does not validate physical SPI/I2C wiring, LCD rendering, touchscreen recognition, QMI8658 readings, or real-world launch thresholds; those behaviors still require the selected target hardware.

