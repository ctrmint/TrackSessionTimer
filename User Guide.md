# User Guide - v4.2.0

## General / Sessions Use
The following describes general operation of both the ``Track Session`` and ``Rest in Pits Session`` timer.

* Upon startup, the Caterham boot artwork is followed by a hardware-information screen showing the board, processor, firmware, operating system, and platform. Each screen is shown for two seconds by default. Maintainers can tune the waits independently with `STARTUP_SPLASH_DURATION_SEC` and `HARDWARE_SPLASH_DURATION_SEC` in `params.json`.
* The ``Primary Screen`` will then show ``Ready`` together with the saved track duration, rest duration, and effective Launch Mode state. A battery icon above `Ready` fills from left to right with estimated remaining charge. A lightning bolt through the battery means USB/external power is present. When the timer starts while connected to USB, the initial full fill represents powered status because this board cannot read the isolated battery cell until it runs from battery. ``Launch unavailable`` means the saved non-zero sensitivity could not be used because the IMU is unavailable; normal swipe-down timing still works. To start the ``Track Session`` or race, ``Swipe Down``. Hold the screen continuously for five seconds to open the operating-mode menu.
* After swiping down, keep the device still for the brief ``SESSION G - Calibrating`` screen. This establishes the acceleration baseline for both the session peak and Launch Mode. ``Go`` will then display briefly. If ``Launch Mode`` has been activated, ``Lights`` will be displayed while the timer waits for sufficient acceleration.
* While waiting in ``Launch Mode``, double-tap to cancel and return to the ``Primary Screen``. The wait also cancels automatically after 30 seconds.
* Upon starting, the ``Track Session`` timer count down will be displayed, and immediately commence.
* During a ``Track Session``, the background blends continuously from green at the start, through yellow at one-third and amber at two-thirds, towards red at scheduled expiry. The blend is proportional to the selected session length rather than using fixed times.
* The clearly spaced line such as ``MAX  1.23  g`` above the countdown shows the largest filtered planar acceleration recorded during the current track session. It is positioned with a clear gap from the countdown, resets at each new track session, and remains visible during overrun. ``MAX --`` means the IMU is unavailable; normal timing and the double-tap stop gesture continue. Rest sessions do not show this value.
* Timer text automatically uses whichever of black or white has the greater contrast against the current background colour.
* Once the ``Track Session`` has completed, i.e. >100%, the background becomes deep purple with white text and the timer remains running to provide visibility of any overrun. ``Double Tap`` to complete/exit. A ``Double Tap`` can be used to terminate any running timer.
* Following termination, an eight-page post-session review begins. Actual run time, overrun, total maximum G, maximum acceleration, maximum braking, maximum left G, maximum right G, and the stop reason each have a separate high-visibility screen. Swipe ``Left`` to advance and ``Right`` to return to the previous result. The first page cannot be bypassed backwards, and cool-down starts only after swiping ``Left`` from the eighth and final page. ``--`` and ``IMU UNAVAILABLE`` mean the session completed without usable sensor data; ``IMU DATA PARTIAL`` means peaks captured before a sensor fault were retained. The review is for immediate inspection only and is not saved to flash.
* Directional labels assume a dashboard installation with the screen upright and facing the driver. The firmware corrects left/right for the selected quarter-turn display rotation. A screen mounted facing away from the driver reverses the acceleration/braking convention.
* After the summary, a ``Rest in Pits`` splash will display, followed by commencement of the ``Rest in Pits Session`` timer.
* Once the ``Rest in Pits Session`` is complete, the timer will return to the ``Primary screen``.  The ``Rest in Pits  Session``  can be terminated with a ``Double Tap``.

## Configuration / Setup
Track duration, rest duration, launch sensitivity, operating mode, brightness, and display rotation are saved to `user.json` when changed. These settings persist across restarts and power loss. If the file is missing, damaged, or contains unsupported values, the timer restores safe defaults and rewrites the file using the canonical setting names.

### Operating Mode Menu

From the Timer ``Ready`` screen or G Mode, press and continuously hold the touchscreen for five seconds. Releasing before five seconds cancels entry. The menu is intentionally unavailable during track/rest timing or the Launch Mode wait.

* Swipe ``Left`` or ``Right`` to choose ``Timer Mode``, ``G Mode``, or ``Settings``.
* Swipe ``UP`` to select the displayed choice.
* Swipe ``DOWN`` to cancel and return to the previously active mode.
* Timer Mode and G Mode selections are saved and used on the next restart. Settings returns to the menu rather than becoming an operating mode.

#### G Mode

Keep the device still while ``Calibrating`` is displayed. The screen then becomes a graphical G meter:

* The green filled marker is the current filtered acceleration vector; its short trail shows recent direction of travel.
* The red hollow marker is the maximum vector since G Mode began or was reset.
* The red outer arc represents maximum magnitude against the meter's 4 g visual scale.
* ``Double Tap`` clears the peak and trail.
* Hold the screen for five seconds to reopen the operating-mode menu.

The graph removes the stationary gravity/mounting baseline and does not rely on small numeric telemetry. If the IMU is unavailable, the timer shows an error and returns safely to Timer Mode.

#### Device Settings

Choose ``Settings`` from the operating-mode menu.

* ``Brightness`` offers 25%, 50%, 75%, and 100%. Left/right previews each level immediately, ``Swipe UP`` saves, and ``Swipe DOWN`` cancels and restores the previous level.
* ``Rotation`` offers ``Auto`` followed by fixed 0°, 90°, 180°, and 270° choices. Fixed values are the physical device rotation clockwise from its original 0° position. ``Auto`` uses the QMI8658 gravity reading to keep the screen upright and shows the currently detected angle during preview. Left/right previews immediately; text and directional gestures rotate together, so swipes stay relative to the displayed instructions. ``Swipe UP`` saves, while ``Swipe DOWN`` safely restores the previous orientation.
* ``Restore defaults`` requires an explicit confirmation. Confirming restores Timer Mode, 100% brightness, 0° rotation, 20-minute track and rest sessions, and disabled Launch Mode. Cancelling changes nothing.
* Choose ``Back`` or swipe down to return to the operating-mode menu, then select or cancel back to an operating mode.

Auto rotation continues through Ready, configuration, active track/rest timing, Launch Mode, G Mode, menus, and timed information screens. A turn must remain clear and stable for about 0.3 seconds before the display changes, which prevents flicker from road vibration or positions near a diagonal. Changing orientation does not reset or pause a session, and detected angles are not written repeatedly to flash.

When the display is nearly horizontal, gravity points mostly through the screen and cannot identify which edge is physically upward. Auto therefore keeps the last reliable orientation until the display is upright enough again. If the IMU is unavailable, the preview reports ``IMU unavailable`` and Auto retains a safe fixed angle; Timer Mode and all four manual rotation choices continue to work.

### Session Duration
It is possible to change the duration of both the ``Track Session`` and the ``Rest in Pits``.

* From the ``Primary Screen``, ``Swipe Left`` to edit the ``Track Session`` and ``Swipe Right`` to edit the ``Rest in Pits  Session``.
* Once in either edit mode, follow the on-screen prompts: ``Swipe Right`` to increment the duration and ``Swipe Left`` to decrement the value. Note duration values are predefined as [1, 5, 10, 15, 20, 25, 30, 40, 50, 60] minutes.
* When the desired duration value is shown, follow the ``Swipe UP: save`` prompt to save and return to the ``Primary Screen``.

### Launch Mode
``Launch mode`` is disabled by default.
``Launch mode`` can be enabled by defining a ``Launch Sensitivity`` value above zero.
* From the ``Primary Screen``, ``Swipe Up`` to edit ``Launch Sensitivity``.
* Follow the on-screen prompts and swipe ``Left`` or ``Right`` to select an appropriate value greater than zero.
* Swipe ``UP`` to save and enable ``Launch mode``.
* Select `0` and swipe ``UP`` to save and disable ``Launch mode``.

Keep the timer stationary while ``SESSION G - Calibrating`` appears. The firmware averages 20 samples over 0.4 seconds to remove gravity and the device's mounting orientation, then reuses that baseline for Launch Mode. It measures the filtered change in the three-axis acceleration vector, so forward or reverse acceleration can trigger regardless of which way the display is mounted. A launch must remain above the threshold for three consecutive 20 ms samples; isolated vibration and bumps are ignored.

Sensitivity values are acceleration changes in **g**, where approximately 1 g is Earth's gravitational acceleration. Lower non-zero values trigger more easily:

| Value | Practical meaning |
| ---: | --- |
| `0` | Launch Mode disabled; timer starts immediately. |
| `0.5` | Very sensitive; suitable for moderate road-car launches. |
| `1` | Strong launch acceleration. |
| `1.25` | Aggressive launch. |
| `1.5` | Very aggressive launch. |
| `1.75` | Motorsport-level acceleration or a strong jolt. |
| `2` | High threshold; unlikely in normal road use. |
| `2.5` | Very high threshold; mainly abrupt impacts. |
| `3.5` | Extreme impact-level acceleration. |
| `4` | Maximum configured threshold; specialist use only. |
