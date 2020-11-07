class legacyDisplayCode:
    def __init__(self):
        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG)
        self.oledDrawing = ["PlaceHolder1", "PlaceHolder2"]

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
        self.display = OledDisplay() #create a display object from class oledDisplay()
        self.display.drawText2(text1='voxaDisplay', text2=('Ready to Go!'))
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
                self.display.drawText2(text1=self.oledDrawing[0], text2=self.oledDrawing[1])   #re-draw what was last there in case it got nuked
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
                self.display.drawText2(text1=self.oledDrawing[0], text2=self.oledDrawing[1])
            if buttonState == 0b11110010:
                logging.info('Going left - register read s0, i.e. 0b11110010')
                self.oledDrawing[0] = 'Left-click'
                self.oledDrawing[1] = '0b11110010'
                self.display.drawText2(text1=self.oledDrawing[0], text2=self.oledDrawing[1])   #Lets draw the new one
            elif buttonState == 0b11110001:
                logging.info('Going right - register read s1, i.e. 0b11110001')
                self.oledDrawing[0] = 'Right-click'
                self.oledDrawing[1] = '0b11110001'
                self.display.drawText2(text1=self.oledDrawing[0], text2=self.oledDrawing[1])   #Lets draw the new one
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
            self.display = OledDisplay() #creates a display object
            self.display.drawText2(text1=self.oledDrawing[0], text2='redraw occured')   
            #!--INCOMPLETE--! We need to change this to pick up where it left off instead of a fresh reboot of display menu.
        