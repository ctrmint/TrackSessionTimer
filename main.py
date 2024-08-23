# Mark Rodman
# Session Timer for track days and racing.
# V3.2-
# 1) Accelerometer enable launch,
# 2) User params
# 3) System params
# 4) Persistence between reboots
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
import json
from timing import *
from lcd_1inch28 import *
from touch_drive import *
from qmi8658 import *

PARAMS_FILE = "params.json"
USER_FILE = "user.json"

PIT_SESSION_MSG = ['Cool down!', 'Rest in pits']
TRACK_SESSION_MSG = ['Ready', 'Swipe DOWN to start']
CLINE1 = [TRACK_SESSION_MSG[0], 20, 96, 5, "white" ]
CLINE2 = [TRACK_SESSION_MSG[1],  44, 195, 1, "black"]
CLINE3 = ["message",  50, 35, 3, "black"]
PLINE1 = [PIT_SESSION_MSG[0], 4, 96, 3, "white"]
PLINE2 = [PIT_SESSION_MSG[1], 23, 150, 2, "red"]


def secs_to_mins_secs(seconds):
    """
    Converts seconds to minutes and remaining seconds.
    :param seconds: the number of seconds to convert
    :return: a formatted string representing the minutes and remaining seconds
    """
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02}:{remaining_seconds:02}"


def set_sensitivity(LCD=None, Touch=None, sensitivity_values=None, sensitivity=0, operation='Config', back_colour='palegreen'):
    """
    Function sets the sensitivity level of the accelerometer used to detect launch
    Operation is completed through the supplied LCD and Touch objects.
    :param LCD: The LCD object for controlling the display.
    :param Touch: The Touch object for interacting with the touch screen.
    :param sensitivity_values: A list of possible sensitivity values for the touch screen.
    :param sensitivity: The current sensitivity level of the touch screen.
    :param operation: The current operation being performed.
    :param back_colour: The background color of the display.
    :return: The updated sensitivity level of the touch screen.
    """
    index = 0
    exit_cmd = False
    CL_X = 60
    CLINE1 = [str(sensitivity_values[index]), CL_X, 80, 5, "white"]
    CLINE2 = ["Launch", 75, 150, 2, "black"]
    CLINE2A = ["Sensitivitiy", 20, 180, 2, "black"]
    CLINE3 = [operation, 75, 35, 2, "black"]
    c1 = [CLINE1, CLINE2, CLINE3]
    Touch.ControlScreen(LCD, text_array=c1, back_colour=back_colour)
    while not exit_cmd:
        gesture = Touch.GetGesture(LCD)
        if gesture == 'up':
            exit_cmd = True
        if gesture == 'left':
            if index == 0:
                index = len(sensitivity_values) - 1
            else:
                index -= 1
        if gesture == 'right':
            index += 1
            if index == len(sensitivity_values):
                index = 0
        
        CLINE1 = [str(sensitivity_values[index]), CL_X, 80, 5, "white"]
        c1 = [CLINE1, CLINE2, CLINE3, CLINE2A]
        Touch.ControlScreen(LCD, text_array=c1, back_colour=back_colour)
        sensitivity = sensitivity_values[index]
    return sensitivity


def set_session(LCD=None, Touch=None, session=None, session_values=None, session_name=None, operation='Config', back_colour='palegreen'):
    """
    Function sets the session duration for the declared session instance.
    The function updates the session object with the selected value from the session_values list.
    It displays the session information on the LCD screen using the Touch.ControlScreen() method.
    It allows the user to navigate through the session_values list using touch gestures.
    The user can exit the operation by swiping up, go to the previous value by swiping left, and go to the next 
    value by swiping right.
    :param LCD: A reference to the LCD object.
    :param Touch: A reference to the Touch object.
    :param session: The session object to be updated.
    :param session_values: A list of values for the session.
    :param session_name: The name of the session.
    :param operation: The operation to be performed.
    :param back_colour: The background color for the display.
    :return: None
    """
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
    return session.duration_mins


def accel_launch(qmi8658, sensitivity=0):
    """
    Continuously reads the accelerometer values from the qmi8658 sensor until the acceleration values exceed the 
    specified sensitivity.
    :param qmi8658: an object representing the qmi8658 sensor
    :param sensitivity: the minimum acceleration threshold in each axis (default is 0)
    :return: True if the acceleration values exceed the sensitivity, False otherwise
    """
    ac_x = 0
    ac_y = 0
    ac_z = 0
    
    while ac_x < sensitivity or ac_y < sensitivity or ac_z < sensitivity:
        xyz=qmi8658.Read_XYZ()
        ac_x = xyz[0]
        ac_y = xyz[1]
        ac_z = xyz[2]
        #print("sensitivity", sensitivity, "x", ac_x, "y", ac_y, "z", ac_z)
    return True


def file_out(file=None, data=None, mode='w', debug=True):
    """
    Write JSON data to a file.
    :param file: The path to the file where the JSON data will be written. Default is None.
    :param data: The data to write to the file in JSON format. Default is None.
    :param mode: The opening mode for the file. Default mode is 'w'.
    :param debug: If True, prints the error messages. Default is True.
    :return: True if write was successful, otherwise False.
    """
    if file is None:
        if debug:
            print("No file specified.")
        return False

    if data is None:
        if debug:
            print("No data provided to write.")
        return False

    try:
        with open(file, mode) as target_file:
            json.dump(data, target_file)
            return True
    except Exception as e:
        if debug:
            print(f"Error occurred: {e}")
        return False



def file_in(file=None, mode='r+', debug=True):
    """
    Open and read a JSON file.
    :param file: The path to the JSON file to be read. Default is None.
    :param mode: The opening mode for the file. Default mode is 'r+'.
    :return: The JSON data from the file, or None if an error occurs.
    """
    if file is None:
        if debug:
            print("No file specified.")
        return None

    try:
        with open(file, mode) as target_file:
            return json.load(target_file)
    except Exception as e:
        if debug:
            print(f"Error occurred: {e}")
        return None
    

def update_json(json_data=None, key=None, value=None):
    """
    Update the given JSON data with a new key-value pair or update an existing key-value pair.
    :param json_data: The JSON data to be updated. (type: dict)
    :param key: The key of the key-value pair to be updated. (type: str)
    :param value: The value to be associated with the key. (type: Any)
    :return: The updated JSON data if successful, None otherwise. (type: dict or None)
    """
    if json_data and key and value:
        # Update the key-value pair
        if key in json_data:
            json_data.update({key:value})
        else:
            json_data[key] = value
    else:
        return None
    return json_data


def main():   
    system_params = file_in(file=PARAMS_FILE)     # load system params file
    user_params = file_in(file=USER_FILE)         # load user params file
    if system_params:
        for key, value in system_params.items():  # declare globals from
            globals()[key] = value                #        from the file
    else:
        sys.exit()

    if user_params:
        for key, value in user_params.items():    # declare globals from
            globals()[key] = value                #        from the file
    else:
        # load some defaults!
        user_params = {"SENSITIVITY": 0, "TRACK_LENGTH": 20, "REST_LENGTH": 20 }
        print("Default User Params loaded")


    print("User Parameters: " + str(user_params))
    # Gyro and Accel
    qmi8658=QMI8658()
    Vbat= ADC(Pin(Vbat_Pin))  
    
    # Init screen
    LCD = LCD_1inch28()
    LCD.set_bl_pwm(65535)
    # Init touchscreen
    Touch = Touch_CST816T(mode=1, LCD=LCD)
    
    # Bootscreen
    Touch.BootScreen(LCD, version_number=VERSION)
    time.sleep(BOOT_DELAY_SEC)  

    while True:
        
        # Load accelerometer sensitivity
        if "SENSITIVITY" in user_params: sensitivity = user_params["SENSITIVITY"]
        else: sensitivity = 0 # fall back value
        
        if "RACE_LENGTH" in user_params: race_length = user_params["RACE_LENGTH"]
        else: race_length = 20 # fall back value
        
        if "REST_LENGTH" in user_params: rest_length = user_params["REST_LENGTH"]
        else: rest_length = 20 # fall back value
          
        launch = False
        return_type = "up"
        
        # Setup the session timers. 
        ts = SessionTracker(duration_mins=race_length, stype="track")  # on track session timer
        rest = SessionTracker(duration_mins=rest_length, stype="rest", debug=True)  # rest session timer

        while not launch:
            gesture = None
            CLINE3[0] = (str(ts.duration_mins) + "mins")
            c1 = [CLINE1, CLINE2, CLINE3]
            Touch.ControlScreen(LCD, text_array=c1, back_colour="green")
            
            gesture = Touch.GetGesture(LCD)
            
            if gesture: 
                if gesture == 'left':       # Race/Track Session Timer change
                    race_length = set_session(LCD=LCD, Touch=Touch, session=ts, session_values=DURATION_VALUES, session_name='Track', back_colour='palegreen')
                    # Update track_length within JSON
                    user_params = update_json(json_data=user_params, key="RACE_LENGTH", value=race_length)
                    # Write out JSON to file, for next boot
                    write_response = file_out(file=USER_FILE, data=user_params)
                if gesture == 'right':      # Pit Session Timer Timer change
                    rest_length = set_session(LCD=LCD, Touch=Touch, session=rest, session_values=DURATION_VALUES, session_name='Rest', back_colour='paleblue')
                    # Update rest_length within JSON
                    user_params = update_json(json_data=user_params, key="REST_LENGTH", value=rest_length)
                    # Write out JSON to file, for next boot
                    write_response = file_out(file=USER_FILE, data=user_params)
                if gesture == 'up':
                    sensitivity = set_sensitivity(LCD=LCD, Touch=Touch, sensitivity_values=LAUNCH_SENSE_VALUES, sensitivity=sensitivity, operation='Config', back_colour='palegreen')
                    # Update sensitivity within JSON
                    user_params = update_json(json_data=user_params, key="SENSITIVITY", value=sensitivity)
                    # Write out JSON to file, for next boot
                    write_response = file_out(file=USER_FILE, data=user_params)
                if gesture == 'down':
                    print("Timer go!")
                    launch = True
            
            time.sleep(0.5)

        # Go Screen
        if sensitivity > 0:
            Touch.GoScreen(LCD, text='lights!')
        else:
            Touch.GoScreen(LCD)

        # Detect launch, if not required sensitivity should be 0
        accel_launch(qmi8658, sensitivity=sensitivity)

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
    
