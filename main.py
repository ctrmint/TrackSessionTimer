# Mark Rodman
# Session Timer for track days and racing.
# V2.0
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
#from touch_LCD import *   # retired and split dedicated imports
from timing import *
from lcd_1inch28 import *
from touch_drive import *

DURATION_VALUES = [1, 5, 10, 15, 20, 25, 30, 40, 50, 60]
DISPLAY_DELAY_REST = 5
DISPLAY_DELAY_REST_COLOUR = 'blue'
REST_SESSION_LENGTH = 20
TRACK_SESSION_LENGTH = 20
PIT_SESSION_MSG = ['Cool down!', 'Rest in pits']
TRACK_SESSION_MSG = ['Ready', 'Swipe DOWN to start']
BOOT_DELAY_SEC = 2

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



def set_session(LCD=None, Touch=None, session=None, session_values=None, session_name=None, operation='Config', back_colour='palegreen'):
    exit_cmd = False
    index = 0
    CLINE1 = [str(session_values[index]), 70, 96, 5, "white"]
    CLINE2 = [session_name, 75, 195, 2, "black"]
    CLINE3 = [operation, 75, 35, 2, "black"]
    c1 = [CLINE1, CLINE2, CLINE3]
    Touch.ControlScreen(LCD, text_array=c1, back_colour=back_colour)
    
    while not exit_cmd:
        gesture = Touch.GetGesture(LCD)
        if gesture == 'up':
            exit_cmd = True
        if gesture == 'left':
            if index == 0:
                index = len(session_values) - 1
            else:
                index -= 1
        if gesture == 'right':
            index += 1
            if index == len(session_values):
                index = 0  
        CLINE1 = [str(session_values[index]), 70, 96, 5, "white"]
        c1 = [CLINE1, CLINE2, CLINE3]
        Touch.ControlScreen(LCD, text_array=c1, back_colour=back_colour)
        session.duration_mins = session_values[index]
    return


def main():
    ts_duration = None
    rest_duration = None
    
    # Init screen
    LCD = LCD_1inch28()
    LCD.set_bl_pwm(65535)
    # Init touchscreen
    Touch = Touch_CST816T(mode=1, LCD=LCD)
    
    # Bootscreen
    Touch.BootScreen(LCD)
    time.sleep(BOOT_DELAY_SEC)

    while True:
        launch = False
        return_type = "up"
        
        # Setup the session timers. 
        ts = SessionTracker(duration_mins=ts_duration, stype="track")  # on track session timer
        rest = SessionTracker(duration_mins=rest_duration, stype="rest", debug=True)  # rest session timer

        while not launch:
            gesture = None
            CLINE3[0] = (str(ts.duration_mins) + "mins")
            c1 = [CLINE1, CLINE2, CLINE3]
            Touch.ControlScreen(LCD, text_array=c1, back_colour="green")
            
            gesture = Touch.GetGesture(LCD)
            
            if gesture: 
                if gesture == 'left':       # Race/Track Session Timer change
                    set_session(LCD=LCD, Touch=Touch, session=ts, session_values=DURATION_VALUES, session_name='Track', back_colour='palegreen')
                if gesture == 'right':      # Pit Session Timer Timer change
                    set_session(LCD=LCD, Touch=Touch, session=rest, session_values=DURATION_VALUES, session_name='Rest', back_colour='paleblue')
                if gesture == 'up':
                    print("Timer top other")
                if gesture == 'down':
                    print("Timer go!")
                    launch = True
            
            time.sleep(0.5)

        # Go Screen 
        Touch.GoScreen(LCD)
        
        # Start session, using set duration
        ts.start_session()
        ts_duration = ts.duration_mins
        
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
                elif ts.last_15 <= now < ts.last_5: 
                    Touch.LiveScreen(LCD, textsize_rem=6, backColour=LCD.salmon, textColour=LCD.black, elapsed=elapsed, remaining=remaining)
                else:  
                    Touch.LiveScreen(LCD, textsize_rem=6, backColour=LCD.lilac, textColour=None, elapsed=elapsed, remaining=remaining)
            else:
                Touch.LiveScreen(LCD, textsize_rem=6, backColour=LCD.red, textColour=LCD.black, elapsed=elapsed, remaining="00:00")

        # Ready rest in pits
        p1 = [PLINE1, PLINE2]
        Touch.ControlScreen(LCD, text_array=p1, back_colour=DISPLAY_DELAY_REST_COLOUR)       
        time.sleep(DISPLAY_DELAY_REST)  # Splash rest in pits
        
        # Start rest session
        rest.start_session(debug=True)
        rest_duration = rest.duration_mins
        
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
        

if __name__=='__main__':
    main()
