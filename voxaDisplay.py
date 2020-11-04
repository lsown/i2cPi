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

class oledDisplay:
    def __init__(self):
        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG)

        self.textfield = 'Initial Screen'
        self.oled_reset = 24
        self.WIDTH = 128
        self.HEIGHT = 32
        self.BORDER = 1
        self.i2c = board.I2C()
        self.oled = adafruit_ssd1306.SSD1306_I2C(self.WIDTH, self.HEIGHT, self.i2c, addr=0x3c) #reset taken out
        self.currentImage = Image.new('1', (self.oled.width, self.oled.height))
        self.drawObj = ImageDraw.Draw(self.currentImage)
        self.font = ImageFont.load_default()
        #self.font = ImageFont.truetype('arial.ttf', 14)    #commented out, default gives better position accuracy
        self.oled.fill(0)   #start with a screen wipe to black
        self.oled.show()

    '''Note Image draw is defined from 0, so max coordinates is actually 0 - 127 & 0 - 32. Line weight adds +'''
    def newImage(self):
        image = Image.new('1', (self.oled.width, self.oled.height)) #mode '1' for 1-bit color, creating a fresh image.
        self.currentImage = image   #re-assign current image object to the new image object
        self.drawObj = ImageDraw.Draw(self.currentImage)    #assign new drawing object

    '''Class method prefix display will directly impact OLED'''
    def displayWipe(self):
        self.oled.fill(0)
        self.oled.show()
        self.newImage()
        self.displayImage()
        
    def displayImage(self):
        self.oled.image(self.currentImage)
        self.oled.show()

    def displayArrows(self):    #draws arrows on current existing image
        self.drawArrows()
        self.displayImage()

    '''Class method prefix draw will only act on self.drawObj'''

    def drawText2(self, text1, text2):
        # Draw Some Text
        (font_width, font_height) = self.font.getsize(text1)
        self.drawObj.text((self.oled.width//4 - font_width//2, self.oled.height//2 - font_height//2), text1, font=self.font, fill=255)

        (font_width, font_height) = self.font.getsize(text2)
        self.drawObj.text((self.oled.width//4 - font_width//2, self.oled.height//4 - font_height//2), text2, font=self.font, fill=255)
        # Display image

    def drawArrows(self):
        self.drawObj.polygon([(8,24), (0, 16), (8, 8)], fill=1, outline=1)  #left arrow
        self.drawObj.polygon([(119,24), (127, 16), (119, 8)], fill=1, outline=1)  #right arrow - up to pixel position 128-1 = 127.

    def drawTextCenter2(self, text1, text2):
        '''This assumes size 14 font-height Arial, pre-calculated'''
        (font_width, font_height) = self.font.getsize(text1)
        #draw.text((self.oled.width//2 - font_width//2, 2), text1, font=self.font, fill=255)     #draw line 1
        #draw.text((self.oled.width//2 - font_width//2, 17), text2, font=self.font, fill=255)    #draw line 2
        self.drawObj.text((self.oled.width//2 - font_width//2, 2), text1, font=self.font, fill=255, align='center')     #draw line 1
        self.drawObj.text((self.oled.width//2 - font_width//2, 17), text2, font=self.font, fill=255, align ='center')    #draw line 2

    def drawBorder(self):
        #self.drawObj.rectangle((0,0, self.oled.width - 1, self.oled.height - 1), 0, 1) #fills in with 0
        self.drawObj.line([(0,0), (self.oled.width-1, 0)], 1, 1)
        self.drawObj.line([(0,self.oled.height-1), (self.oled.width-1, self.oled.height-1)], 1, 1)
        self.drawObj.line([(0,0), (0, self.oled.height-1)], 1, 1)
        self.drawObj.line([(self.oled.width-1, 0), (self.oled.width-1, self.oled.height-1)], 1, 1)

    def drawGrid(self, xDiv = 8, yDiv = 2):
        self.drawBorder()
        for i in range (1, xDiv+1):
            xCoordinate = ((self.oled.width//xDiv)*i) - 1
            logging.info('xCoordianate is: %s' %xCoordinate)
            self.drawObj.line([(xCoordinate,0), (xCoordinate, self.oled.height - 1)], fill=1, width=2)  #lets give it 2-weight to represent end & beginning of the next grid box
        self.drawObj.line([(0, self.oled.height // yDiv - 1), (self.oled.width - 1, self.oled.height // yDiv - 1)], 1, 2)

    '''def drawGrid(self):
        self.drawBorder()
        for i in range (1, 17):
            xCoordinate = (8*i) - 1
            logging.info('xCoordianate is: %s' %xCoordinate)
            self.drawObj.line([(xCoordinate,0), (xCoordinate, self.oled.height - 1)], fill=1, width=2)  #lets give it 2-weight to represent end & beginning of the next grid box
        self.drawObj.line([(0, self.oled.height // 2 - 1), (self.oled.width - 1, self.oled.height //2 - 1)], 1, 2)
    '''

    def drawTextCenter1(self, text):
        # Draw Some Text
        (font_width, font_height) = self.font.getsize(text)
        self.drawObj.text((self.oled.width//4 - font_width//2, self.oled.height//2 - font_height//2), text, font=self.font, fill=255)

    def drawWifi(self, x=0, y=0, status='ok'):
        '''Draws wifi symbol. If status error, cuts it out and adds exclamation point.'''
        if status == 'error' or status =='ok':
            self.drawObj.arc([(x, y), (16+x, 8+y)], 200, 340, 1, 1)    #draw top wifi arc
            self.drawObj.arc([(x, y+4), (16+x, 16+y)], 230, 310, 1, 1)   #draw mid wifi arc
            self.drawObj.arc([(x, y+8), (16+x, 24+y)], 260, 280, 1, 1)   #draw little bottom arc
            logging.info('Drew ok variant of wifi.')
        else:
            logging.info('invalid status. Nothing returned.')
            return
        if status == 'error':
            self.drawObj.line([(x+5, y), (x+5, y+8)], 0, 2) #cut left side
            self.drawObj.line([(x+10, y), (x+10, y+8)], 0,2)    #cut right side
            self.drawObj.line([(x+8, y), (x+8, y+5)], 1, 3)   #draw straight line for exclamation point
            logging.info('Drew error variant of wifi.')
                

    def drawBluetooth(self, x=3, y=2, status='ok', fill=1):
        '''default x,y positioned @3,2 so it is roughly center in a 0x16 box'''
        if status == 'error' or status =='ok':
            self.drawObj.line([(x+4,y+0), (x+4,y+12)], fill, 1)    #draw vertical line
            self.drawObj.line([(x+4,y+0), (x+8,y+4)], fill, 1)     #draw -45 degree line top
            self.drawObj.line([(x+8,y+4), (x+0,y+8)], fill, 1)     #draw +45 degree mid top cross
            self.drawObj.line([(x+0,y+4), (x+8,y+8)], fill, 1)     #draw -45 degree mid bot cross
            self.drawObj.line([(x+4,y+12), (x+8,y+8)], fill, 1)    #draw +45 degree line bot
        else:
            logging.info('invalid status, only "ok" or "error" accepted. Nothing returned.')
            return
        if status == 'error':
            self.drawObj.line([(x+4,y+12), (x+8,y+8)], 0, 1)    #erase bottom line
            self.drawObj.arc([(x+3,y+7), (x+11,y+15)],0,360,1,1)   #draw arc
            self.drawObj.line([(x+4,y+8), (x+10,y+14)],1,1)        #draw -45 degree cross line
            self.drawObj.line([(x+10,y+8), (x+4,y+14)],1,1)        #draw +45 degree cross line
            logging.info('Drew error variant of bluetooth.')




class voxaDisplay:
    def __init__(self):
        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG)
        self.oledDrawing = ["PlaceHolder1", "PlaceHolder2"]

        '''PCA9537 Registers: 1:Input Port Register | 2: Output Port Register | 3: Polarity Inversion Register | 4: Configuration Register'''

        pca9537 = {'registers':
            {0:{'description':'inputPort', 'bootupState': 0b11110011}, 
            1:{'description':'inputPort', 'bootupState': 0b11111111},
            2:{'description':'inputPort', 'bootupState': 0b11111111},
            3:{'description':'inputPort', 'bootupState': 0b00000000}}
            }

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
        self.display = oledDisplay() #create a display object from class oledDisplay()
        self.display.displayNew(text1='voxaDisplay', text2=('Ready to Go!'))
        self.bus.read_byte_data(0x49, 0x00)  #Just in case to pull up display ALERT pin
        self.monitorThread()

    def piSetup(self): #Sets up GPIO pins from the MCU DAQ, can also add to GPIO.in <pull_up_down=GPIO.PUD_UP>

        for i in self.pinsOut:
            GPIO.setup(self.pinsOut[i]['pin'], GPIO.OUT, initial = self.pinsOut[i]['state']) #set GPIO as OUT, configure initial value
            logging.info('%s pin %s configured as OUTPUT %s' %(self.pinsOut[i]['name'], str(self.pinsOut[i]['pin']), self.pinsOut[i]['state']))

        for i in self.pinsIn:
            GPIO.setup(self.pinsIn[i]['pin'], GPIO.IN) #set GPIO as INPUT
            logging.info('%s pin %s configured as INPUT' %(self.pinsIn[i]['name'], str(self.pinsIn[i]['pin'])))

            self.pinsIn[i]['state'] = GPIO.input(self.pinsIn[i]['pin'])
            logging.info('%s initial state is %s' %(self.pinsIn[i]['name'], str(self.pinsIn[i]['state'])))

            #configure event detections for pinType buttonInterface. INT LOW signals input change detected.
            if self.pinsIn[i]['pinType'] == 'buttonInterface':
                GPIO.add_event_detect(self.pinsIn[i]['pin'], GPIO.FALLING, callback=self.buttonPress, bouncetime=10) 

    def updateState(self, channel, value):
        for i in self.pinsIn:
            if channel == self.pinsIn[i]['pin']:
                self.pinsIn[i]['state'] = value
                print('%s pin triggered, %s configured state to %s' %(str(channel), self.pinsIn[i]['name'], self.pinsIn[i]['state'])) # debug

    def monitor(self, pin = 22):
        while True:
            currentVal = GPIO.input(22)
            time.sleep(2)
            newVal = GPIO.input(22)
            if (newVal == 0 and newVal == currentVal):
                self.bus.read_byte_data(0x49, 0x00)
                logging.info('<!--THREAD ALERT--!> Tracked low for extended period of time.')
                self.display.displayNew(text1=self.oledDrawing[0], text2=self.oledDrawing[1])   #re-draw what was last there in case it got nuked
            else:
                logging.info('<!--Thread--!> Passing')
            

    def monitorThread(self):
        x = threading.Thread(target=self.monitor(), args=(1,), daemon=True)
        x.start()
        logging.info('Thread started.')

    def buttonPress(self, channel):
        logging.info('<!-------------Button Press Detected-------------!>')
        logging.info('Display Flag Logged button callback - ALERT pin state is %s' %GPIO.input(22))
        self.queryButtonReg()
        logging.info('Finished queryButtonReg - ALERT pin state is %s' %GPIO.input(22))

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

    def queryButtonReg(self):
        '''Because we are using POGOS, we can occasionally get a momentary disconnect when we are pushing on the buttons. To prevent this, we need to (1) catch this exception - OSError & (2) try a refresh, say 2-3 times.'''

        try:
            
            buttonState = self.bus.read_byte_data(0x49, 0x00)
            if buttonState == 0b11110000:
                logging.info('Both pressed - register read s0&1, i.e. 0b11110000.')
                self.oledDrawing[0] = 'Double-press'
                self.oledDrawing[1] = '0b11110000'
                self.display.displayNew(text1=self.oledDrawing[0], text2=self.oledDrawing[1])
            if buttonState == 0b11110010:
                logging.info('Going left - register read s0, i.e. 0b11110010')
                self.oledDrawing[0] = 'Left-click'
                self.oledDrawing[1] = '0b11110010'
                self.display.displayNew(text1=self.oledDrawing[0], text2=self.oledDrawing[1])   #Lets draw the new one
            elif buttonState == 0b11110001:
                logging.info('Going right - register read s1, i.e. 0b11110001')
                self.oledDrawing[0] = 'Right-click'
                self.oledDrawing[1] = '0b11110001'
                self.display.displayNew(text1=self.oledDrawing[0], text2=self.oledDrawing[1])   #Lets draw the new one
            elif buttonState == 0b11110011:
                logging.info('Button back at default state')    #we do not draw for this occurence. Note that button release triggers an event detect!
            else:
                logging.info('Some other combination has been read')
            time.sleep(0.1) #Lets give a small timeout and then re-read register to cleanup and pull ALERT back up in case it failed to go back up. 
            logging.info('Clean-up register - just in case ALERT is pulled low. Value read is %s' %bin(self.bus.read_byte_data(0x49, 0x00)))
                #self.display.displayNew(text1='Neither button pushed state', text2=('0b11110011'))

                #logging.info('Spurious read %s read.' %bin(buttonState))
                #self.display.displayNew(text1='Spurious Read', text2=('?'))

            global exit_loop
            exit_loop = True
            
        except OSError:
            logging.info('<!---EXCEPTION--!>Remote - OSError... wait 100 mS and re-initialize a trial read.')
            time.sleep(0.1)
            buttonState = self.bus.read_byte_data(0x49, 0x00)
            self.display = oledDisplay() #creates a display object
            self.display.displayNew(text1=self.oledDrawing[0], text2='redraw occured')   
            #!--INCOMPLETE--! We need to change this to pick up where it left off instead of a fresh reboot of display menu.
        




