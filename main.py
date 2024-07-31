# Mark Rodman
# Session Timer for track days and racing.
# ----------------------------------------------------
# Description.
# This is an aid to monitoring the duration of a given
# session, not a lap counter!
# ----------------------------------------------------
# See readme for instruction
# ----------------------------------------------------

from machine import Pin,I2C,SPI,PWM,Timer
import framebuf
import time
import sys
from touch_LCD import *
from timing import *

DURATION_VALUES = [1, 5, 10, 15, 20, 25, 30]
DISPLAY_DELAY_REST = 5
DISPLAY_DELAY_REST_COLOUR = 'blue'
REST_SESSION_LENGTH = 20
TRACK_SESSION_LENGTH = 20
PIT_SESSION_MSG = ['Cool down!', 'Rest in pits']
TRACK_SESSION_MSG = ['Ready', 'Swipe DOWN to start']
BOOT_DELAY_SEC = 3

CLINE1 = [TRACK_SESSION_MSG[0], 20, 96, 5, "white" ]
CLINE2 = [TRACK_SESSION_MSG[1],  44, 195, 1, "black"]
CLINE3 = ["message",  50, 35, 3, "black"]

PLINE1 = [PIT_SESSION_MSG[0], 4, 96, 3, "white"]
PLINE2 = [PIT_SESSION_MSG[1], 23, 150, 2, "red"]

def secs_to_mins_secs(seconds):
    # Calculate the number of minutes and the remaining seconds
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02}:{remaining_seconds:02}"


def main():
    time.sleep(1)
    duration = None
    # Instantiate the screen
    LCD = LCD_1inch28()
    LCD.set_bl_pwm(65535)
    Touch = Touch_CST816T(mode=1, LCD=LCD)
    
    # Bootscreen
    Touch.BootScreen(LCD)
    time.sleep(BOOT_DELAY_SEC)
    
    while 1:
        launch = False
        return_type = "up"
        if duration is None:
            duration = TRACK_SESSION_LENGTH
        # Setup the timer 
        ts = SessionTracker(duration_mins=duration, stype="track")
        rest = SessionTracker(duration_mins=REST_SESSION_LENGTH, stype="rest", debug=True)

        while return_type != "down":
            CLINE3[0] = (str(duration) + "mins")
            c1 = [CLINE1, CLINE2, CLINE3]
            Touch.ControlScreen(LCD, text_array=c1, back_colour="green")
            duration, return_type = Touch.SetDurationGesture(LCD, duration, duration_values = DURATION_VALUES )
        
        # Go Screen 
        Touch.GoScreen(LCD)
        # Start session, using set duration
        ts.start_session(mins=duration)
        
        while ts.live is True:
            now = time.time()
            remaining = secs_to_mins_secs(int(ts.end_time - now))
            elapsed = secs_to_mins_secs((now - ts.start_time))

            # Capture input for cancel / pause here
            if Touch.StopGesture(LCD):
                ts.live = False
            # This is the running session 
            if now < ts.end_time:
                if now < ts.last_15:
                    Touch.LiveScreen(LCD, textsize_rem=6, backColour=None, textColour=None, elapsed=elapsed, remaining=remaining)
                elif ts.last_15 <= now < ts.last_5:  # Yellow
                    Touch.LiveScreen(LCD, textsize_rem=6, backColour=LCD.yellow, textColour=LCD.black, elapsed=elapsed, remaining=remaining)
                else:  # orange
                    Touch.LiveScreen(LCD, textsize_rem=6, backColour=LCD.orange, textColour=None, elapsed=elapsed, remaining=remaining)
            else:
                Touch.LiveScreen(LCD, textsize_rem=6, backColour=LCD.red, textColour=LCD.black, elapsed=elapsed, remaining="00:00")  
        
        # Ready rest in pits
        p1 = [PLINE1, PLINE2]
        Touch.ControlScreen(LCD, text_array=p1, back_colour=DISPLAY_DELAY_REST_COLOUR)       
        time.sleep(DISPLAY_DELAY_REST)  # Splash rest in pits
        
        # Start rest session
        rest.start_session(mins=REST_SESSION_LENGTH)
        while rest.live is True:
            now = time.time()
            remaining = secs_to_mins_secs(int(rest.end_time - now))
            elapsed = secs_to_mins_secs((now - rest.start_time))
            # Capture input for clear timer
            if Touch.ClearGesture(LCD):
                rest.live = False
            
            if now < rest.end_time:
                Touch.LiveScreen(LCD, textsize_rem=6, backColour=LCD.blue, textColour=None, elapsed=elapsed, remaining=remaining)
            else:
                rest.live = False
    return

if __name__=='__main__':
    main()