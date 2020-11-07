from RPi import GPIO as GPIO
GPIO.setmode(GPIO.BCM)


from smbus2 import SMBus
import time
import logging

#I2C display library
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

#threading
import threading




class OledDisplay:
    def __init__(self, i2cAddress=0x3c):
        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG)
        self.i2cAddress= i2cAddress
        self.textfield = 'Initial Screen'
        self.oled_reset = 24
        self.WIDTH = 128
        self.HEIGHT = 32
        self.BORDER = 1
        self.i2c = board.I2C()
        self.oled = adafruit_ssd1306.SSD1306_I2C(self.WIDTH, self.HEIGHT, self.i2c, addr=self.i2cAddress) #reset taken out
        self.currentImage = Image.new('1', (self.oled.width, self.oled.height))
        self.drawObj = ImageDraw.Draw(self.currentImage)
        self.font = ImageFont.load_default()
        #self.font = ImageFont.truetype('arial.ttf', 14)    #commented out, default gives better position accuracy
        self.oled.fill(0)   #start with a screen wipe to black
        self.oled.show()

    '''Note Image draw is defined from 0, so max coordinates is actually 0 - 127 & 0 - 32. Line weight adds +. Use only if you want to create a new image object.'''
    def newImage(self):
        image = Image.new('1', (self.oled.width, self.oled.height)) #mode '1' for 1-bit color, creating a fresh image.
        self.currentImage = image   #re-assign current image object to the new image object
        self.drawObj = ImageDraw.Draw(self.currentImage)    #assign new drawing object

    '''Class method prefix display will directly impact OLED'''
    def displayWipe(self):
        self.drawObj.rectangle([(0,0), (self.WIDTH, self.HEIGHT)], 0)   #black out canvas
        self.oled.fill(0)   #fill oled with 0
        self.oled.show()    #show oled
        
    def displayImage(self):
        self.oled.image(self.currentImage)
        self.oled.show()

    def displayArrows(self):    #draws arrows on current existing image
        self.drawArrows()
        self.displayImage()

    '''Class method prefix "draw" will only act on self.drawObj'''

    def drawText2(self, text1, text2):
        # Draw Some Text
        (font_width, font_height) = self.font.getsize(text1)
        self.drawObj.text((self.oled.width//4 - font_width//2, self.oled.height//2 - font_height//2), text1, font=self.font, fill=255)

        (font_width, font_height) = self.font.getsize(text2)
        self.drawObj.text((self.oled.width//4 - font_width//2, self.oled.height//4 - font_height//2), text2, font=self.font, fill=255)
        # Display image

    def drawArrows(self):
        self.drawObj.polygon([(5,24), (0, 16), (5, 8)], fill=1, outline=1)  #left arrow
        self.drawObj.polygon([(122,24), (127, 16), (122, 8)], fill=1, outline=1)  #right arrow - up to pixel position 128-1 = 127.

    def drawBorder(self):
        #self.drawObj.rectangle((0,0, self.oled.width - 1, self.oled.height - 1), 0, 1) #fills in with 0
        self.drawObj.line([(0,0), (self.oled.width-1, 0)], 1, 1)
        self.drawObj.line([(0,self.oled.height-1), (self.oled.width-1, self.oled.height-1)], 1, 1)
        self.drawObj.line([(0,0), (0, self.oled.height-1)], 1, 1)
        self.drawObj.line([(self.oled.width-1, 0), (self.oled.width-1, self.oled.height-1)], 1, 1)

    def drawGrid(self, xDiv = 8, yDiv = 2):
        '''Helper drawing to visualize the grid spacing available for the OLED display. Default setting divides X into equal 8 blocks & Y in 1/2. Each is divided with OLED '''
        self.drawBorder()
        for i in range (1, xDiv+1):
            xCoordinate = ((self.oled.width//xDiv)*i) - 1
            logging.info('xCoordianate is: %s' %xCoordinate)
            self.drawObj.line([(xCoordinate,0), (xCoordinate, self.oled.height - 1)], fill=1, width=2)  #lets give it 2-weight to represent end & beginning of the next grid box
        self.drawObj.line([(0, self.oled.height // yDiv - 1), (self.oled.width - 1, self.oled.height // yDiv - 1)], 1, 2)

    def drawTextCentered(self, text, position='bottom'):
        # Draw Some Text horizontally centered, can be adjusted to top, center, or bot 16 px
        (font_width, font_height) = self.font.getsize(text)
        if position == 'middle':
            self.drawObj.text((self.oled.width//2 - font_width//2, self.oled.height//2 - font_height//2), text, font=self.font, fill=255)
        elif position =='top':
            self.drawObj.text((self.oled.width//2 - font_width//2, 3), text, font=self.font, fill=255)
        elif position =='bottom':
            self.drawObj.text((self.oled.width//2 - font_width//2, self.oled.height//2 + 3), text, font=self.font, fill=255)

    def drawWifi(self, x=0, y=2, status='ok'):
        '''Draws wifi symbol. If status error, cuts it out and adds exclamation point.'''
        '''x,y positioned @ (3,2) centers in a 0x16 box, add (16,16) to (3,2).'''
        if status == 'error' or status =='ok':
            self.drawObj.rectangle([(x,y), (x+12, y+12)], 0, 0, 1)  #black out area
            #wifi symbol
            self.drawObj.arc([(x, y), (16+x, 8+y)], 200, 340, 1, 1)    #top arc
            self.drawObj.arc([(x, y+4), (16+x, 16+y)], 230, 310, 1, 1)   #mid arc
            self.drawObj.line([(x+6,y+8), (x+10,y+8)],1,1)  #bottom arc
            self.drawObj.line([(x+7,y+9), (x+9,y+9)],1,1)   #bottom arc
        else:
            logging.info('drawWiFi: invalid status parameter - status must be "ok" or "error".')
            return
        if status == 'error':
            self.drawObj.line([(x+5, y), (x+5, y+8)], 0, 2) #cut left side
            self.drawObj.line([(x+10, y), (x+10, y+8)], 0,2)    #cut right side
            self.drawObj.line([(x+8, y), (x+8, y+5)], 1, 3)   #draw straight line for exclamation point
        logging.info('Wifi status icon "%s" drawn.' %status)

    def drawBluetooth(self, x=2, y=1, status='ok'):
        if status == 'error' or status =='ok':
            self.drawObj.line([(x+4,y+0), (x+4,y+12)], 1, 1)    #draw vertical line
            self.drawObj.line([(x+4,y+0), (x+8,y+4)], 1, 1)     #draw -45 degree line top
            self.drawObj.line([(x+8,y+4), (x+0,y+8)], 1, 1)     #draw +45 degree mid top cross
            self.drawObj.line([(x+0,y+4), (x+8,y+8)], 1, 1)     #draw -45 degree mid bot cross
            self.drawObj.line([(x+4,y+12), (x+8,y+8)], 1, 1)    #draw +45 degree line bot
        else:
            logging.info('drawBluetooth: invalid status parameter - status must be "ok" or "error".')
            return
        if status == 'error':
            self.drawObj.line([(x+10,y+0),(x+10,y+8)], 1,2)
            self.drawObj.line([(x+10,y+11),(x+10,y+12)], 1,2)
        logging.info('Bluetooth status icon "%s" drawn.' %status)
        '''#old version with a circle box and x in right corner
        self.drawObj.line([(x+4,y+12), (x+8,y+8)], 0, 1)    #erase bottom line
        self.drawObj.arc([(x+3,y+6), (x+11,y+14)],0,360,1,1)   #draw arc
        self.drawObj.line([(x+4,y+7), (x+10,y+13)],1,1)        #draw -45 degree cross line
        self.drawObj.line([(x+10,y+7), (x+4,y+13)],1,1)        #draw +45 degree cross line
        logging.info('Drew error variant of bluetooth.')'''

    def drawEthernet(self, x=1, y=1, status='ok'):
        if status == 'error' or status =='ok':
            self.drawObj.rectangle([(x,y), (x+13, y+12)], 0, 0, 1)  #black out area 
            #drawing out ethernet icon
            self.drawObj.rectangle([(x+0,y+0), (x+10, y+12)], fill=0, outline=1, width=1)   #outside ethernet
            self.drawObj.polygon(
                [(x+2,y+2), (x+8,y+2), (x+8, y+8), 
                (x+7, y+8), (x+7, y+10), (x+7, y+10), 
                (x+3, y+10), (x+3, y+8), (x+2, y+8)], 
                fill=0, outline=1)  #inside ethernet symbol
        else:
            logging.info('drawEthernet: invalid status parameter - status must be "ok" or "error".')
            return
        if status == 'error':
            self.drawObj.line([(x+12,y+0),(x+12,y+8)], 1,2) #exclamation line
            self.drawObj.line([(x+12,y+11),(x+12,y+12)], 1,2)   #xclamation point
        logging.info('Ethernet status icon "%s" drawn.' %status)

    def drawPanel(self):
        self.drawBluetooth(x=108)    #24 + 2
        self.drawWifi(8)            #5 + 2
        self.drawArrows()

class OledButtons:
    def __init__(self):
        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG)
        self.address = 0x49
        self.input_register_pointer = 0x00  #Expected State: 0b11110011
        self.output_register_pointer = 0x01 #Expected State: 0b11111111
        self.polarityinv_register_pointer = 0x02    #Expected State: 0b11111111
        self.config_register_pointer = 0x03 #Expected State: 0b00000000
        self.bus = SMBus(1)
        self.bus.read_byte_data(0x49, 0x00)  #Read once on init, just in case to pull INT flag up.
        logging.info('OledButtons class initialized.')

    def read_input_register(self):
        '''Because we are using POGOS, we can occasionally get a momentary disconnect when we are pushing on the buttons. To prevent this, we need to (1) catch this exception - OSError & (2) try a refresh, say 2-3 times.'''
        try:
            input_register_value = self.bus.read_byte_data(self.address, self.input_register_pointer)
            logging.info('queryButton: Input register read value is %s.' %bin(input_register_value))
            time.sleep(0.1) #Lets give a small timeout and then re-read register to cleanup and pull ALERT back up in case it failed to go back up. 
            logging.info('queryButton: Clean-up register - just in case ALERT is pulled low. Value read is %s' %bin(self.bus.read_byte_data(0x49, 0x00)))
            return input_register_value
            #global exit_loop
            #exit_loop = True
        except OSError:
            logging.info('<!---EXCEPTION--!>Remote - OSError... wait 100 mS and re-initialize a trial read.')
            time.sleep(0.1)
            self.bus.read_byte_data(self.address, self.input_register_pointer)  #read register just in case to reset INT

class VoxaDisplay:
    def __init__(self, interruptPin = 22):
        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG)
        self.oledText = ["",""] #holder for text
        self.oledTestResponse = None
        self.interruptPin = interruptPin    #BCM GPIO pin # on RPi, default on MCU's is 22
        try:
            self.oled = OledDisplay()       #create instance of display
            self.buttons = OledButtons()    #create instance of buttons
        except IOError:
            logging.info('Failed to bringup OledDisplay or OLEDButton - IO Error')
        try:
            GPIO.add_event_detect(self.interruptPin, GPIO.FALLING, 
            callback=self.buttonPress, 
            bouncetime=10)
            logging.info('Added event detection on pin %s with callback to .buttonPress' %self.interruptPin)
        except:
            logging.info('!-ERROR-! Failed to add event detection on pin %s with callback to .buttonPress' %self.interruptPin)
        self.monitorThread()    #start auto-monitoring thread in case a latch-state occurs on the INT pin.

    def buttonPress(self, channel):
        logging.info('<!-------------Button INTERRUPT Detected-------------!>')
        logging.info('INT pin state is %s' %GPIO.input(channel))
        input_register_value = self.buttons.read_input_register()   #Queries button class register, returns a string indicating direction
        self.drawTestResponse(input_register_value)
        logging.info('Finished queryButtonReg - ALERT pin state is %s' %GPIO.input(channel))

    def drawTestResponse(self, buttonState):
        if buttonState == 0b11110000:
            logging.info('queryButton: Both pressed - register read s0&1, i.e. 0b11110000.')
            self.oledText[0] = 'Double-press'
        elif buttonState == 0b11110010:
            logging.info('queryButton: Going left - register read s0, i.e. 0b11110010')
            self.oledText[0] = 'Left-click'
        elif buttonState == 0b11110001:
            logging.info('queryButton: Going right - register read s1, i.e. 0b11110001')
            self.oledText[0] = 'Right-click'
        elif buttonState == 0b11110011:
            logging.info('queryButton: Button back at default state')    #we do not draw for this occurence. Note that button release triggers an event detect!
            return None
        else:
            logging.info('queryButton: Unexpected combo read: %s' %(bin(buttonState)))
            return None
        self.oledText[1] = str(bin(buttonState))
        try:
            self.oled.displayWipe()
            self.oled.drawArrows()
            self.oled.drawTextCentered(text=self.oledText[0], position="top")   #Lets draw the text at top position centered
            self.oled.drawTextCentered(text=self.oledText[1], position="bottom")   #Lets draw the text at bottom position centered
            self.oled.displayImage()
        except IOError:
            logging.error('<!-- ERROR --!> Failed to draw test response, IO Error.')
            #global exit_loop
            #exit_loop = True
            #!--INCOMPLETE--! We need to change this to pick up where it left off instead of a fresh reboot of display menu.

    def monitor(self, pin = 22):
        '''monitor functions are designed to prevent INT pin erroring into a forever LOW state.'''
        while True:
            currentVal = GPIO.input(22)
            time.sleep(2)
            newVal = GPIO.input(22)
            if (newVal == 0 and newVal == currentVal):
                self.buttons.bus.read_byte_data(0x49, 0x00)
                logging.info('<!--THREAD ALERT--!> Tracked low for extended period of time.')
            else:
                logging.info('<!--Thread--!> Passing')

    def monitorThread(self):
        x = threading.Thread(target=self.monitor(), args=(1,), daemon=True)
        x.start()
        logging.info('Thread started.')

class MCUSetup:
    def __init__(self):
        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG)
        self.pinsIn = {
            'displayFlag' : {'name' : 'displayFlag', 'pinType':'buttonInterface','state':0,'priorState':0, 'pin': 22},
            'adtFlag' : {'name' : 'adtFlag', 'pinType':'interface','state': 0,'priorState':0, 'pin': 14},
            'maxFlag' : {'name' : 'maxFlag', 'pinType':'interface','state':0,'priorState':0, 'pin': 25}
        }

        self.pinsOut = {
            'mcu_adcCS': {'name':'mcu_adcCS', 'pin': 5, 'state': 0, 'priorState': 0, 'pinType': 'SPI'},
            'adc0CS': {'name':'adc0CS', 'pin': 6, 'state': 0, 'priorState': 0, 'pinType': 'SPI'},
            'adc1CS': {'name':'adc1CS', 'pin': 13, 'state': 0, 'priorState': 0, 'pinType': 'SPI'},
            'adc2CS': {'name':'adc2CS', 'pin': 19, 'state': 0, 'priorState': 0, 'pinType': 'SPI'},
            'adc3CS': {'name':'adc3CS', 'pin': 26, 'state': 0, 'priorState': 0, 'pinType': 'SPI'},
            'adc4CS': {'name':'adc4CS', 'pin': 21, 'state': 0, 'priorState': 0, 'pinType': 'SPI'},
            'dacCS': {'name':'dacCS', 'pin': 17, 'state': 0, 'priorState': 0, 'pinType': 'SPI'},
            'dacLDAC': {'name':'dacLDAC', 'pin': 27, 'state': 0, 'priorState': 0, 'pinType': 'SPI'},
            'dPWRen': {'name':'dPWRen', 'pin': 24, 'state': 1, 'priorState': 0, 'pinType': 'PWR'},
            'aPWRen': {'name':'aPWRen', 'pin': 4, 'state': 1, 'priorState': 0, 'pinType': 'PWR'}
        }

        logging.info('Initializing Voxa Display Module Test Code')
        self.bus = SMBus(1)
        self.piSetup()
        self.tunnel()

    def piSetup(self): #Sets up GPIO pins from the MCU DAQ, can also add to GPIO.in <pull_up_down=GPIO.PUD_UP>

        for i in self.pinsOut:
            GPIO.setup(self.pinsOut[i]['pin'], GPIO.OUT, initial = self.pinsOut[i]['state']) #set GPIO as OUT, configure initial value
            logging.info('%s pin %s configured as OUTPUT %s' %(self.pinsOut[i]['name'], str(self.pinsOut[i]['pin']), self.pinsOut[i]['state']))

        for i in self.pinsIn:
            GPIO.setup(self.pinsIn[i]['pin'], GPIO.IN) #set GPIO as INPUT
            logging.info('%s pin %s configured as INPUT' %(self.pinsIn[i]['name'], str(self.pinsIn[i]['pin'])))

            self.pinsIn[i]['state'] = GPIO.input(self.pinsIn[i]['pin'])
            logging.info('%s initial state is %s' %(self.pinsIn[i]['name'], str(self.pinsIn[i]['state'])))

    def updateState(self, channel, value):
        for i in self.pinsIn:
            if channel == self.pinsIn[i]['pin']:
                self.pinsIn[i]['state'] = value
                print('%s pin triggered, %s configured state to %s' %(str(channel), self.pinsIn[i]['name'], self.pinsIn[i]['state'])) # debug

    def getPinState(self, pin):
        return GPIO.input(pin)

    def tunnel(self):
        try:
            self.bus.read_byte_data(0x77, 0x00) #check config register of mux layer-0 
            self.bus.write_byte(0x77, 0x01) #open channel 0
            self.bus.read_byte_data(0x77, 0x00) #confirm channel 0 opened
            try:
                self.bus.read_byte_data(0x41, 0x03)  #read PCA9536 configuration register, expect 0x0F - configured inputs
                self.bus.write_byte_data(0x41, 0x03, 0x00) #Set register 3 to 0b0, configures all to output
                self.bus.read_byte_data(0x41, 0x03)    #Check that its configured as output
                self.bus.read_byte_data(0x41, 0x01)  #check output register, default is 1 - 3.3V
                self.bus.write_byte_data(0x41, 0x01, 0x00)   #write output register to 0 - change all to 0V
                self.bus.read_byte_data(0x41, 0x01)  #confirm that output register is 0.
            except OSError:
                logging.info('Error 121 - Remote I/O Error on address 41 - PCA9536')
            try:
                self.bus.read_byte(0x70, 0x00)  #check that mux has been reconfigured to address 70.
                self.bus.write_byte(0x70, 0x82) #close mux-70 layer-0 channel 0, open ch1 & 7
            except OSError:
                logging.info('Error 121 - Remote I/O Error on address 70 - TCA9548')
            
            try:
                self.bus.read_byte(0x77, 0x00)  #check that mux-77 layer-1 channel 0 is present.
                self.bus.write_byte(0x77, 0x81) #close mux-70 layer-0 channel 0, open ch1 & 7
            except OSError:
                logging.info('Error 121 - Remote I/O Error on address 77 - layer 1 - TCA9548')

        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 77 - TCA9548')

MCUSetup()
OledDisplay()