#Touch drive
from machine import Pin,I2C,SPI,PWM,Timer,ADC
import framebuf
import time
Vbat_Pin = 29

#Guesture Hex values
G_UP = 0x01
G_DOWN = 0x02
G_LEFT = 0x03
G_RIGHT = 0x04
G_LONG_PRESS = 0x0C
G_DOUBLE_CLIC = 0x0B


class Touch_CST816T(object):
    #Initialize the touch chip
    def __init__(self,address=0x15,mode=0,i2c_num=1,i2c_sda=6,i2c_scl=7,int_pin=21,rst_pin=22,LCD=None):
        self._bus = I2C(id=i2c_num,scl=Pin(i2c_scl),sda=Pin(i2c_sda),freq=400_000) #Initialize I2C 
        self._address = address #Set slave address 
        self.int=Pin(int_pin,Pin.IN, Pin.PULL_UP)     
        self.tim = Timer()     
        self.rst=Pin(rst_pin,Pin.OUT)
        self.Reset()
        bRet=self.WhoAmI()
        if bRet :
            print("Success:Detected CST816T.")
            Rev= self.Read_Revision()
            print("CST816T Revision = {}".format(Rev))
            self.Stop_Sleep()
        else    :
            print("Error: Not Detected CST816T.")
            return None
        self.Mode = mode
        self.Gestures="None"
        self.Flag = self.Flgh =self.l = 0
        self.X_point = self.Y_point = 0
        self.int.irq(handler=self.Int_Callback,trigger=Pin.IRQ_FALLING)
      
    def _read_byte(self,cmd):
        rec=self._bus.readfrom_mem(int(self._address),int(cmd),1)
        return rec[0]
    
    def _read_block(self, reg, length=1):
        rec=self._bus.readfrom_mem(int(self._address),int(reg),length)
        return rec
    
    def _write_byte(self,cmd,val):
        self._bus.writeto_mem(int(self._address),int(cmd),bytes([int(val)]))

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
        time.sleep_ms(1)
        self.rst(1)
        time.sleep_ms(50)
    
    #Set mode 
    def Set_Mode(self,mode,callback_time=10,rest_time=5): 
        # mode = 0 gestures mode 
        # mode = 1 point mode 
        # mode = 2 mixed mode 
        if (mode == 1):      
            self._write_byte(0xFA,0X41)
            
        elif (mode == 2) :
            self._write_byte(0xFA,0X71)
            
        else:
            self._write_byte(0xFA,0X11)
            self._write_byte(0xEC,0X01)
     
    #Get the coordinates of the touch
    def get_point(self):
        xy_point = self._read_block(0x03,4)
        
        x_point= ((xy_point[0]&0x0f)<<8)+xy_point[1]
        y_point= ((xy_point[2]&0x0f)<<8)+xy_point[3]
        
        self.X_point=x_point
        self.Y_point=y_point
        
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
        self.mode = 0
        self.Set_Mode(self.Mode)
        LCD.fill(LCD.red)
        LCD.write_text('Track',30,66,3,LCD.green)
        LCD.write_text('Session',44,96,3,LCD.green)
        LCD.write_text('Timer',65,126,3,LCD.green)
        LCD.write_text(('Version:' + version_number),65,197,1,LCD.green)
        LCD.show()
        
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


    def ControlScreen(self, LCD, text_array=None, back_colour=None):
        """
        Outputs text to screen using an array of arrays, where each inner array contains the following structure:
        [string_val, x, y, size, color].
        
        Parameters:
        - LCD: The LCD object responsible for displaying the text.
        - text_array: A list of lists, each containing [string_val, x, y, size, color].
        - back_colour: Optional background color for the screen.
        """      
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
                # Validate each parameter (e.g., ensure x, y are within screen bounds)
                LCD.write_text(string_val, x, y, size, self.SetTextColour(LCD, color))
        # Refresh the LCD to display the changes
        LCD.show()
        
        
    def GoScreen(self, LCD):
        #self.mode = 0
        #self.Set_Mode(self.Mode)
        LCD.fill(LCD.green)
        LCD.write_text('..GO!',15,96,5,LCD.white)
        LCD.show()
        time.sleep(1)


    def LiveScreen(self, LCD, textsize_rem=None, backColour=None, textColour=None, elapsed=None, remaining=None):
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
        self.mode = 0
        self.Set_Mode(self.Mode)
        LCD.fill(backColour)
        LCD.write_text(remaining,1,96,textsize_rem,textColour)
        LCD.write_text(elapsed,62,185,3,textColour)
        LCD.show()
    
    
    def ClearGesture(self, LCD):
        """
        Check for up gesture.
        """
        if self.Gestures == G_UP or self.Gestures == G_DOUBLE_CLIC:
            self.Gestures = 0
            return True  # up gesture, returns True
        else:
            return False # else no gesture, returns False
    
    def StopGesture(self, LCD):
        """
        Check for a double tap stop gesture.
        """
        if self.Gestures == 0x0B:
            self.Gestures = 0
            return True  # double tap stop gesture, returns True
        else:
            return False # else no stop gesture, returns False
    
    #Gesture
    def GetGesture(self, LCD, debounce_time=0.2):
        return_type = None     
        self.Mode = 0
        self.Set_Mode(self.Mode)
         
        if self.Gestures == G_UP:
            return_type = "up"
            
        
        if self.Gestures == G_DOWN:
            return_type = "down"
            
        if self.Gestures == G_LEFT:
            return_type = "left"
        
        if self.Gestures == G_RIGHT:
            return_type = "right"
            
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
            
            if self.Gestures == G_UP:
                got_input = True
                return_type = "up"
            
            if self.Gestures == G_DOWN:
                got_input = True
                return_type = "down"
            
            if self.Gestures == G_LEFT:
                index_value += 1
                if index_value == len(duration_values):
                    index_value = 0 
                duration = duration_values[index_value]
                
                # Plot the revised duration on the screen
                LCD.fill(LCD.green)
                dur_str = f"{duration:02}"
                LCD.write_text(str(dur_str),55,90,8,LCD.white)
                LCD.write_text('minutes',67,190,2,LCD.black)
                LCD.show()
                
                # Delay to stop interface bounce, and flying through all of the array values.
                # This is a bit hacky and needs to be improved. 
                time.sleep(1)
        return duration, return_type  
        

#######
class QMI8658(object):
    def __init__(self,address=0X6B):
        self._address = address
        self._bus = I2C(id=1,scl=Pin(I2C_SDL),sda=Pin(I2C_SDA),freq=100_000)
        bRet=self.WhoAmI()
        if bRet :
            self.Read_Revision()
        else    :
            return NULL
        self.Config_apply()

    def _read_byte(self,cmd):
        rec=self._bus.readfrom_mem(int(self._address),int(cmd),1)
        return rec[0]
    def _read_block(self, reg, length=1):
        rec=self._bus.readfrom_mem(int(self._address),int(reg),length)
        return rec
    def _read_u16(self,cmd):
        LSB = self._bus.readfrom_mem(int(self._address),int(cmd),1)
        MSB = self._bus.readfrom_mem(int(self._address),int(cmd)+1,1)
        return (MSB[0] << 8) + LSB[0]
    def _write_byte(self,cmd,val):
        self._bus.writeto_mem(int(self._address),int(cmd),bytes([int(val)]))
        
    def WhoAmI(self):
        bRet=False
        if (0x05) == self._read_byte(0x00):
            bRet = True
        return bRet
    def Read_Revision(self):
        return self._read_byte(0x01)
    def Config_apply(self):
        # REG CTRL1
        self._write_byte(0x02,0x60)
        # REG CTRL2 : QMI8658AccRange_8g  and QMI8658AccOdr_1000Hz
        self._write_byte(0x03,0x23)
        # REG CTRL3 : QMI8658GyrRange_512dps and QMI8658GyrOdr_1000Hz
        self._write_byte(0x04,0x53)
        # REG CTRL4 : No
        self._write_byte(0x05,0x00)
        # REG CTRL5 : Enable Gyroscope And Accelerometer Low-Pass Filter 
        self._write_byte(0x06,0x11)
        # REG CTRL6 : Disables Motion on Demand.
        self._write_byte(0x07,0x00)
        # REG CTRL7 : Enable Gyroscope And Accelerometer
        self._write_byte(0x08,0x03)

    def Read_Raw_XYZ(self):
        xyz=[0,0,0,0,0,0]
        raw_timestamp = self._read_block(0x30,3)
        raw_acc_xyz=self._read_block(0x35,6)
        raw_gyro_xyz=self._read_block(0x3b,6)
        raw_xyz=self._read_block(0x35,12)
        timestamp = (raw_timestamp[2]<<16)|(raw_timestamp[1]<<8)|(raw_timestamp[0])
        for i in range(6):
            # xyz[i]=(raw_acc_xyz[(i*2)+1]<<8)|(raw_acc_xyz[i*2])
            # xyz[i+3]=(raw_gyro_xyz[((i+3)*2)+1]<<8)|(raw_gyro_xyz[(i+3)*2])
            xyz[i] = (raw_xyz[(i*2)+1]<<8)|(raw_xyz[i*2])
            if xyz[i] >= 32767:
                xyz[i] = xyz[i]-65535
        return xyz
    def Read_XYZ(self):
        xyz=[0,0,0,0,0,0]
        raw_xyz=self.Read_Raw_XYZ()  
        #QMI8658AccRange_8g
        acc_lsb_div=(1<<12)
        #QMI8658GyrRange_512dps
        gyro_lsb_div = 64
        for i in range(3):
            xyz[i]=raw_xyz[i]/acc_lsb_div#(acc_lsb_div/1000.0)
            xyz[i+3]=raw_xyz[i+3]*1.0/gyro_lsb_div
        return xyz


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
    LCD.write_text('Gesture test',70,90,1,LCD.black)
    LCD.write_text('Complete as prompted',35,120,1,LCD.black)
    LCD.show()
    time.sleep(1)
    LCD.fill(LCD.white)
    while Touch.Gestures != 0x01:
        LCD.fill(LCD.white)
        LCD.write_text('UP',100,110,3,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x02:
        LCD.fill(LCD.white)
        LCD.write_text('DOWM',70,110,3,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x03:
        LCD.fill(LCD.white)
        LCD.write_text('LEFT',70,110,3,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x04:
        LCD.fill(LCD.white)
        LCD.write_text('RIGHT',60,110,3,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x0C:
        LCD.fill(LCD.white)
        LCD.write_text('Long Press',40,110,2,LCD.black)
        LCD.show()
        time.sleep(0.1)
        
    while Touch.Gestures != 0x0B:
        LCD.fill(LCD.white)
        LCD.write_text('Double Click',25,110,2,LCD.black)
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
        LCD.text("Waveshare",80,25,LCD.white)
        
        LCD.fill_rect(0,40,240,40,LCD.blue)
        # LCD.text("Long Press to Quit",20,57,LCD.white)
        LCD.write_text("Long Press to Quit",50,57,1,LCD.white)
        
        LCD.fill_rect(0,80,120,120,0x1805)
        LCD.text("ACC_X={:+.2f}".format(xyz[0]),20,100-3,LCD.white)
        LCD.text("ACC_Y={:+.2f}".format(xyz[1]),20,140-3,LCD.white)
        LCD.text("ACC_Z={:+.2f}".format(xyz[2]),20,180-3,LCD.white)

        LCD.fill_rect(120,80,120,120,0xF073)
        LCD.text("GYR_X={:+3.2f}".format(xyz[3]),125,100-3,LCD.white)
        LCD.text("GYR_Y={:+3.2f}".format(xyz[4]),125,140-3,LCD.white)
        LCD.text("GYR_Z={:+3.2f}".format(xyz[5]),125,180-3,LCD.white)
        
        LCD.fill_rect(0,200,240,40,0x180f)
        reading = Vbat.read_u16()*3.3/65535 * 3
        LCD.text("Vbat={:.2f}".format(reading),80,215,LCD.white)
        
        LCD.show()
        if(Touch.Gestures == 0x0C):
            break
