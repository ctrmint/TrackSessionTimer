# TrackSessionTimer
Trackday or race session timer.

## Background
Managing time on the track can be challenging, whether it's during a track day or a race. Many competitors in the Seven category use kitchen timers mounted on their dashboards. However, these timers can be large, awkward, and difficult to read, requiring drivers to interpret small digits mid-race.

The code provided here offers a solution by creating a timer that is easy to read with clear digits. Additionally, it features background colors that change to indicate key moments during the session, such as when 85% and 95% of the session time has elapsed.

The timer is designed to support common session lengths, making it quick and easy to set up without the need to scroll through unnecessary minute intervals.

The timer utilizes the Waveshare 1.28-inch round touch display, allowing for configuration and operation through intuitive swipe gestures.

## Hardware Requirements 
* Raspberry Pico
* Waveshare 1.28-inch round touch display

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
