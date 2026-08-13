# Touch drive
# v4.1.0
from machine import I2C, Pin, Timer
import time

from hardware import PeripheralIOError, PeripheralIdentityError
from orientation import map_gesture_direction, validate_rotation

#Guesture Hex values
G_UP = 0x01
G_DOWN = 0x02
G_LEFT = 0x03
G_RIGHT = 0x04
G_LONG_PRESS = 0x0C
G_DOUBLE_CLIC = 0x0B
LAP_LABEL_Y = 160
LAP_LABEL_TEXT_SIZE = 1
LAP_VALUE_Y = 176
LAP_VALUE_TEXT_SIZE = 4
def _sleep_ms(clock, milliseconds):
    sleep_ms = getattr(clock, "sleep_ms", None)
    if sleep_ms is not None:
        sleep_ms(milliseconds)
    else:
        clock.sleep(milliseconds / 1000)


class Touch_CST816T(object):
    #Initialize the touch chip
    def __init__(
        self,
        address=0x15,
        mode=0,
        i2c_num=1,
        i2c_sda=6,
        i2c_scl=7,
        int_pin=21,
        rst_pin=22,
        LCD=None,
        bus=None,
        pin_factory=Pin,
        timer_factory=Timer,
        clock=time,
        rotation=0,
    ):
        self._address = address #Set slave address 
        self._clock = clock
        self._configured_mode = None
        self._auto_rotation = None
        self.Set_Rotation(rotation)
        try:
            self._bus = bus
            if self._bus is None:
                self._bus = I2C(
                    id=i2c_num,
                    scl=pin_factory(i2c_scl),
                    sda=pin_factory(i2c_sda),
                    freq=400_000,
                )
            self.int=pin_factory(int_pin,pin_factory.IN, pin_factory.PULL_UP)
            self.tim = timer_factory()
            self.rst=pin_factory(rst_pin,pin_factory.OUT)
            self.Reset()
            chip_id = self._read_byte(0xA7)
        except PeripheralIOError as error:
            raise PeripheralIOError("CST816T", "chip ID read", error.detail)
        except OSError as error:
            raise PeripheralIOError("CST816T", "chip ID read", error)

        if chip_id != 0xB5:
            raise PeripheralIdentityError("CST816T", 0xB5, chip_id)

        try:
            self.revision = self.Read_Revision()
            self.Stop_Sleep()
            self.Mode = mode
            self.Gestures = 0
            self.Flag = self.Flgh =self.l = 0
            self.X_point = self.Y_point = 0
            self.int.irq(
                handler=self.Int_Callback,
                trigger=pin_factory.IRQ_FALLING,
            )
        except PeripheralIOError as error:
            raise PeripheralIOError("CST816T", "configuration", error.detail)
        except OSError as error:
            raise PeripheralIOError("CST816T", "configuration", error)

        print("Success: Detected CST816T.")
        print("CST816T Revision = {}".format(self.revision))
      
    def _read_byte(self,cmd):
        try:
            rec=self._bus.readfrom_mem(int(self._address),int(cmd),1)
        except OSError as error:
            raise PeripheralIOError("CST816T", "register read", error)
        if len(rec) != 1:
            raise PeripheralIOError("CST816T", "register read", "short I2C read")
        return rec[0]
    
    def _read_block(self, reg, length=1):
        try:
            rec=self._bus.readfrom_mem(int(self._address),int(reg),length)
        except OSError as error:
            raise PeripheralIOError("CST816T", "register read", error)
        if len(rec) != length:
            raise PeripheralIOError("CST816T", "register read", "short I2C read")
        return rec
    
    def _write_byte(self,cmd,val):
        try:
            self._bus.writeto_mem(int(self._address),int(cmd),bytes([int(val)]))
        except OSError as error:
            raise PeripheralIOError("CST816T", "register write", error)

    def WhoAmI(self):
        if (0xB5) != self._read_byte(0xA7):
            return False
        return True
    
    def Read_Revision(self):
        return self._read_byte(0xA9)
      
    #Stop sleeping
    def Stop_Sleep(self):
        self._write_byte(0xFE,0x01)
    
    #Reset   
    def Reset(self):
        self.rst(0)
        _sleep_ms(self._clock, 1)
        self.rst(1)
        _sleep_ms(self._clock, 50)
        self._configured_mode = None
    
    #Set mode 
    def Set_Mode(self,mode,callback_time=10,rest_time=5): 
        # mode = 0 gestures mode 
        # mode = 1 point mode 
        # mode = 2 mixed mode 
        self.Mode = mode
        if self._configured_mode == mode:
            return False

        if (mode == 1):      
            self._write_byte(0xFA,0X41)
            
        elif (mode == 2) :
            self._write_byte(0xFA,0X71)
            
        else:
            self._write_byte(0xFA,0X11)
            self._write_byte(0xEC,0X01)
        self._configured_mode = mode
        return True
     
    #Get the coordinates of the touch
    def get_point(self):
        xy_point = self._read_block(0x03,4)
        
        x_point= ((xy_point[0]&0x0f)<<8)+xy_point[1]
        y_point= ((xy_point[2]&0x0f)<<8)+xy_point[3]
        
        self.X_point=x_point
        self.Y_point=y_point

    def IsPressed(self, LCD=None):
        """Return whether the controller currently reports a physical touch."""
        self._update_auto_rotation(LCD)
        return bool(self._read_byte(0x02) & 0x0F)

    def ClearPendingInput(self):
        """Discard input that completed a hold before opening another screen."""
        self.Gestures = 0
        self.Flag = 0

    def Set_Rotation(self, rotation):
        """Keep directional gestures intuitive at the selected mount angle."""
        self.rotation = validate_rotation(rotation)

    def Set_Auto_Rotation(self, controller):
        """Attach the optional automatic-orientation controller."""
        self._auto_rotation = controller

    def _update_auto_rotation(self, LCD, redraw=True):
        controller = getattr(self, "_auto_rotation", None)
        if controller is None or LCD is None:
            return False
        return controller.update(redraw=redraw)

    def Wait(self, LCD, seconds, poll_interval_ms=100):
        """Wait while continuing bounded automatic-orientation polling."""
        remaining_ms = max(0, int(float(seconds) * 1000))
        interval_ms = max(1, int(poll_interval_ms))
        while remaining_ms > 0:
            self._update_auto_rotation(LCD)
            delay_ms = min(interval_ms, remaining_ms)
            _sleep_ms(self._clock, delay_ms)
            remaining_ms -= delay_ms

    def _gesture_name(self, gesture):
        direction = {
            G_UP: "up",
            G_DOWN: "down",
            G_LEFT: "left",
            G_RIGHT: "right",
        }.get(gesture)
        return map_gesture_direction(direction, self.rotation)
        
    def Int_Callback(self,pin):
        if self.Mode == 0 :
            self.Gestures = self._read_byte(0x01)

        elif self.Mode == 1:           
            self.Flag = 1
            self.get_point()

    def Timer_callback(self,t):
        self.l += 1
        if self.l > 100:
            self.l = 50

    def BootScreen(self, LCD, sleep=4, version_number="0.0"):
        self._update_auto_rotation(LCD, redraw=False)
        self.Set_Mode(self.Mode)

        splash_loaded = False
        try:
            # Import after LCD construction so the 115,200-byte framebuffer is
            # allocated before this optional startup feature uses any heap.
            from splash import load_splash
            splash_loaded = load_splash(LCD)
        except (ImportError, OSError):
            pass

        if splash_loaded:
            LCD.write_centered(('Version ' + version_number),205,1,LCD.white)
        else:
            LCD.fill(LCD.red)
            LCD.write_centered('Track',55,3,LCD.green)
            LCD.write_centered('Session',90,3,LCD.green)
            LCD.write_centered('Timer',125,3,LCD.green)
            LCD.write_centered(('Version ' + version_number),195,1,LCD.green)
        LCD.show()
        return splash_loaded
        
    def SetBackColour(self, LCD, backColour):
        if backColour == 'green':
            return LCD.fill(LCD.green)
        if backColour == 'palegreen':
            return LCD.fill(LCD.palegreen)
        if backColour == 'blue':
            return LCD.fill(LCD.blue)
        if backColour == 'paleblue':
            return LCD.fill(LCD.paleblue)
        if backColour == 'red':
            return LCD.fill(LCD.red)
        if backColour == 'conf_red':
            return LCD.fill(LCD.conf_red)
        if backColour == 'white':
            return LCD.fill(LCD.white)
        if backColour == 'brown':
            return LCD.fill(LCD.brown)
        if backColour == 'black':
            return LCD.fill(LCD.black)
        if backColour == 'lilac':
            return LCD.fill(LCD.lilac)
        if backColour == 'testcolour':
            return LCD.fill(LCD.testcolour)
    
    def SetTextColour(self, LCD, TextColour):
        if TextColour == 'green':
            return LCD.green
        if TextColour == 'blue':
            return LCD.blue
        if TextColour == 'red':
            return LCD.red
        if TextColour == 'white':
            return LCD.white
        if TextColour == 'brown':
            return LCD.brown
        if TextColour == 'black':
            return LCD.black 


    def ControlScreen(self, LCD, text_array=None, back_colour=None, refresh=True):
        """
        Outputs text to screen using an array of arrays, where each inner array contains the following structure:
        [string_val, x, y, size, color].
        
        Parameters:
        - LCD: The LCD object responsible for displaying the text.
        - text_array: A list of lists, each containing [string_val, x, y, size, color].
        - back_colour: Optional background color for the screen.
        - refresh: Show immediately, or allow the caller to add graphics first.
        """      
        self._update_auto_rotation(LCD, redraw=False)
        # Set the background color if provided
        if back_colour is not None:
            self.SetBackColour(LCD, backColour=back_colour)
        else:
            self.SetBackColour(LCD, backColour="black")
        
        if text_array is not None:
            for text in text_array:
                if len(text) != 5:
                    raise ValueError(f"Each text array must contain exactly 5 elements: {text}")
                string_val, x, y, size, color = text
                text_color = self.SetTextColour(LCD, color)
                if x is None:
                    LCD.write_centered(string_val, y, size, text_color)
                else:
                    LCD.write_text(string_val, x, y, size, text_color)
        # Refresh the LCD unless the caller still needs to add graphics.
        if refresh:
            LCD.show()
        
        
    def GoScreen(self, LCD, text='..GO!', subtitle=None):
        self._update_auto_rotation(LCD, redraw=False)
        #self.mode = 0
        #self.Set_Mode(self.Mode)
        LCD.fill(LCD.green)
        LCD.write_centered(text,92,4,LCD.white)
        if subtitle is not None:
            LCD.write_centered(subtitle,170,1,LCD.black)
        LCD.show()
        self.Wait(LCD, 1)


    def LiveScreen(
        self,
        LCD,
        textsize_rem=None,
        backColour=None,
        textColour=None,
        elapsed=None,
        remaining=None,
        maximum_g=None,
        progress_segments=None,
        phase_label=None,
    ):
        self._update_auto_rotation(LCD, redraw=False)
        if remaining is None:
            remaining = "blank!"
        if elapsed is None:
            elapsed = "blank!"
        if textColour is None:
            textColour = LCD.white
        if backColour is None:
            backColour = LCD.green
        if textsize_rem is None:
            textsize_rem = 5
        self.Set_Mode(0)
        LCD.fill(backColour)
        if (
            progress_segments is not None
            or phase_label is not None
            or maximum_g is not None
        ):
            from live_screen_graphics import draw_live_overlays

            draw_live_overlays(
                LCD,
                textColour,
                progress_segments=progress_segments,
                phase_label=phase_label,
                maximum_g=maximum_g,
            )
            del draw_live_overlays
        LCD.write_time_centered(remaining, 82, textsize_rem, textColour)
        if isinstance(elapsed, tuple) and len(elapsed) == 2:
            LCD.write_time_centered(
                elapsed[0],
                LAP_LABEL_Y,
                LAP_LABEL_TEXT_SIZE,
                textColour,
            )
            LCD.write_time_centered(
                elapsed[1],
                LAP_VALUE_Y,
                LAP_VALUE_TEXT_SIZE,
                textColour,
            )
        else:
            LCD.write_time_centered(elapsed, 180, 3, textColour)
        LCD.show()
    
    
    def ClearGesture(self, LCD):
        """
        Check for up gesture.
        """
        self._update_auto_rotation(LCD)
        if (
            self._gesture_name(self.Gestures) == "up"
            or self.Gestures == G_DOUBLE_CLIC
        ):
            self.Gestures = 0
            return True  # up gesture, returns True
        else:
            return False # else no gesture, returns False
    
    def StopGesture(self, LCD):
        """
        Check for a double tap stop gesture.
        """
        self._update_auto_rotation(LCD)
        if self.Gestures == 0x0B:
            self.Gestures = 0
            return True  # double tap stop gesture, returns True
        else:
            return False # else no stop gesture, returns False
    
    #Gesture
    def GetGesture(self, LCD, debounce_time=0.2):
        return_type = None     
        self._update_auto_rotation(LCD)
        self.Set_Mode(0)
         
        return_type = self._gesture_name(self.Gestures)
            
        self.Gestures = 0  # clear for next gesture, very important
        time.sleep(debounce_time)
        return return_type  
    
     
    #Gesture
    def SetDurationGesture(self, LCD, duration, duration_values=None):
        got_input = False
        return_type = None
        
        if duration_values is None:
            duration_values = [5, 10, 15, 20, 25]
        index_value = 0
        
        self.Mode = 0
        self.Set_Mode(self.Mode)
    
        # set default duration
        if duration is None:
            duration = duration_values[0]

        while got_input is False:
            
            gesture = self._gesture_name(self.Gestures)
            if gesture == "up":
                got_input = True
                return_type = "up"
            
            if gesture == "down":
                got_input = True
                return_type = "down"
            
            if gesture == "left":
                index_value += 1
                if index_value == len(duration_values):
                    index_value = 0 
                duration = duration_values[index_value]
                
                # Plot the revised duration on the screen
                LCD.fill(LCD.green)
                dur_str = f"{duration:02}"
                LCD.write_centered(str(dur_str),75,8,LCD.white)
                LCD.write_centered('minutes',185,2,LCD.black)
                LCD.show()
                
                # Delay to stop interface bounce, and flying through all of the array values.
                # This is a bit hacky and needs to be improved. 
                time.sleep(1)
        return duration, return_type  
        

#######



#Draw line and show 
def Touch_HandWriting():
    x = y = data = 0
    color = 0
    Touch.Flgh = 0
    Touch.Flag = 0
    Touch.Mode = 1
    Touch.Set_Mode(Touch.Mode)
    
    LCD.fill(LCD.white)
    LCD.rect(0, 0, 35, 208,LCD.red,True)
    LCD.rect(0, 0, 208, 35,LCD.green,True)
    LCD.rect(205, 0, 240, 240,LCD.blue,True)
    LCD.rect(0, 205, 240, 240,LCD.brown,True)
    LCD.show()
    
    Touch.tim.init(period=1, callback=Touch.Timer_callback)
    try:
        while True:
            if Touch.Flgh == 0 and Touch.X_point != 0:
                Touch.Flgh = 1
                x = Touch.X_point
                y = Touch.Y_point
                
            if Touch.Flag == 1:
                if (Touch.X_point > 34 and Touch.X_point < 205) and (Touch.Y_point > 34 and Touch.Y_point < 205):
                    Touch.Flgh = 3
                else:
                    if (Touch.X_point > 0 and Touch.X_point < 33) and (Touch.Y_point > 0 and Touch.Y_point < 208):
                        color = LCD.red
                        
                    if (Touch.X_point > 0 and Touch.X_point < 208) and (Touch.Y_point > 0 and Touch.Y_point < 33):
                        color = LCD.green
                        
                    if (Touch.X_point > 208 and Touch.X_point < 240) and (Touch.Y_point > 0 and Touch.Y_point < 240):
                        color = LCD.blue
                        
                    if (Touch.X_point > 0 and Touch.X_point < 240) and (Touch.Y_point > 208 and Touch.Y_point < 240):
                        LCD.fill(LCD.white)
                        LCD.rect(0, 0, 35, 208,LCD.red,True)
                        LCD.rect(0, 0, 208, 35,LCD.green,True)
                        LCD.rect(205, 0, 240, 240,LCD.blue,True)
                        LCD.rect(0, 205, 240, 240,LCD.brown,True)
                        LCD.show()
                    Touch.Flgh = 4
                    
                if Touch.Flgh == 3:
                    time.sleep(0.001) #Prevent disconnection  防止断触
                    if Touch.l < 25:           
                        Touch.Flag = 0
                        LCD.line(x,y,Touch.X_point,Touch.Y_point,color)
                        LCD.Windows_show(x,y,Touch.X_point,Touch.Y_point)
                        Touch.l=0
                    else:
                        Touch.Flag = 0
                        LCD.pixel(Touch.X_point,Touch.Y_point,color)
                        LCD.Windows_show(x,y,Touch.X_point,Touch.Y_point)
                        Touch.l=0
                        
                    x = Touch.X_point
                    y = Touch.Y_point
    except KeyboardInterrupt:
        pass

#Gesture
def Touch_Gesture():
    Touch.Mode = 0
    Touch.Set_Mode(Touch.Mode)
    LCD.fill(LCD.white)
#     LCD.show()
    LCD.write_centered('Gesture test',90,1,LCD.black)
    LCD.write_centered('Complete as prompted',120,1,LCD.black)
    LCD.show()
    time.sleep(1)
    LCD.fill(LCD.white)
    while Touch.Gestures != 0x01:
        LCD.fill(LCD.white)
        LCD.write_centered('UP',105,3,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x02:
        LCD.fill(LCD.white)
        LCD.write_centered('DOWN',105,3,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x03:
        LCD.fill(LCD.white)
        LCD.write_centered('LEFT',105,3,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x04:
        LCD.fill(LCD.white)
        LCD.write_centered('RIGHT',105,3,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x0C:
        LCD.fill(LCD.white)
        LCD.write_centered('Long Press',105,2,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x0B:
        LCD.fill(LCD.white)
        LCD.write_centered('Double Click',105,2,LCD.black)
        LCD.show() 
        time.sleep(0.1)

def DOF_READ():
    qmi8658=QMI8658()
    Vbat= ADC(Pin(Vbat_Pin))   
    Touch.Mode = 0
    Touch.Set_Mode(Touch.Mode)

    while(True):
        #read QMI8658
        xyz=qmi8658.Read_XYZ()
        
        LCD.fill(LCD.white)
        
        LCD.fill_rect(0,0,240,40,LCD.red)
        LCD.write_centered("Waveshare",18,1,LCD.white)
        
        LCD.fill_rect(0,40,240,40,LCD.blue)
        LCD.write_centered("Long Press to Quit",54,1,LCD.white)
        
        LCD.fill_rect(0,80,120,120,0x1805)
        LCD.write_text("ACC_X={:+.2f}".format(xyz[0]),5,94,1,LCD.white)
        LCD.write_text("ACC_Y={:+.2f}".format(xyz[1]),5,134,1,LCD.white)
        LCD.write_text("ACC_Z={:+.2f}".format(xyz[2]),5,174,1,LCD.white)

        LCD.fill_rect(120,80,120,120,0xF073)
        LCD.write_text("GYR_X={:+3.2f}".format(xyz[3]),125,94,1,LCD.white)
        LCD.write_text("GYR_Y={:+3.2f}".format(xyz[4]),125,134,1,LCD.white)
        LCD.write_text("GYR_Z={:+3.2f}".format(xyz[5]),125,174,1,LCD.white)
        
        LCD.fill_rect(0,200,240,40,0x180f)
        reading = Vbat.read_u16()*3.3/65535 * 3
        LCD.write_centered("Vbat={:.2f}".format(reading),212,1,LCD.white)
        
        LCD.show()
        if(Touch.Gestures == 0x0C):
            break
