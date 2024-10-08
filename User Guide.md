# User Guide -v3.1

## General / Sessions Use
The following describes general operation of both the ``Track Session`` and ``Rest in Pits Session`` timer.

* Upon start up a boot splash will be shown for 2 seconds.
* After which the ``Primary Screen`` will be shown, detailing the current track session duration in minutes, and the statement ``Ready``.  This indicates the timer is ready to start.  To start the ``Track Session`` or race, ``Swipe Down``.
* After swiping down,``Go`` will display briefly.  If ``Launch Mode`` has been activited, ``Lights`` will be displayed.  The timer will commence upon sufficient acceleration.
* Upon starting, the ``Track Session`` timer count down will be displayed, and immediately commence.
* At 85% completion of the ``Track Session`` the timer display colours will change to highlight progression.
* At 95% completion of the ``Track Session`` the timer display colours will again change, further highlighting progression and final expiry warning.
* At 100% completion the ``Track Session`` timer display colours will change again.
* Once the ``Track Session`` has completed, i.e. >100%, the timer will remain running.  The session continues to run to provide visibility of any overrunning.  ``Double Tap`` to complete/exit.  A ``Double Tap`` can be used to terminate any running timer.
* Following termination, a ``Rest in Pits`` splash will display, followed by commencement of the ``Rest in Pits Session`` timer.
* Once the ``Rest in Pits Session`` is complete, the timer will return to the ``Primary screen``.  The ``Rest in Pits  Session``  can be terminated with a ``Double Tap``.

## Configuration / Setup 
All settings are stored from session to session while the timer has power.  Settings are wiped if power is lost.

### Session Duration
It is possible to change the duration of both the ``Track Session`` and the ``Rest in Pits``.

* From the ``Primary Screen``, ``Swipe Left`` to edit the ``Track Session`` and ``Swipe Right`` to edit the ``Rest in Pits  Session``.
* Once in either edit modes, use a ``Swipe Right`` to increment the duration and a ``Swipe Left`` to decrement the value.  Note duration values are predefined as [1, 5, 10, 15, 20, 25, 30, 40, 50, 60] minutes.
* When the desired duration value is shown ``Swipe Up`` to save and return to the ``Primary Screen``

### Launch Mode
``Launch mode`` is disabled by default.
``Launch mode`` can be enabled by defining a ``Launch Sensitivity`` value above zero.
* From the ``Primary Screen``, ``Swipe Up`` to edit ``Launch Sensitivity``.
* Swipe ``Left`` or ``Right`` to select an appropriate value greater than zero.
* Swip ``UP`` to save and enable ``Launch mode``
