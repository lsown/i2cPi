from RPi import GPIO as GPIO
GPIO.setmode(GPIO.BCM)

class i2cPi:
    def __init__(self):
        self.pinsIn = {
            'displayFlag' : {'name' : 'displayFlag', 'pinType':'interface','state':0,'priorState':0, 'pin': 22},
            'displayFlag' : {'name' : 'displayFlag', 'pinType':'interface','state':0,'priorState':0, 'pin': 22},
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
            'aPWRen': {'name':'aPWRen', 'pin': 4, 'state': 0, 'priorState': 0, 'pinType': 'PWR'},
            'dPWRen': {'name':'dPWRen', 'pin': 24, 'state': 0, 'priorState': 0, 'pinType': 'PWR'},
        }

        self.pinsIn_FanCon = {
            'adtFlag' : {'name' : 'adtFlag', 'pinType':'interface','state':0,'priorState':0, 'pin': 14},
            'maxFlag' : {'name' : 'maxFlag', 'pinType':'interface','state':0,'priorState':0, 'pin': 25},
        }

    def piSetup(self): #Sets up GPIO pins, can also add to GPIO.in <pull_up_down=GPIO.PUD_UP>

        for i in self.pinsOut:
            GPIO.setup(self.pinsOut[i]['pin'], GPIO.OUT, initial = self.pinsOut[i]['state']) #set GPIO as OUT, configure initial value
            logging.info('%s pin %s configured as OUTPUT %s' %(self.pinsOut[i]['name'], str(self.pinsOut[i]['pin']), self.pinsOut[i]['state']))

        for i in self.pinsIn:
            GPIO.setup(self.pinsIn[i]['pin'], GPIO.IN) #set GPIO as INPUT
            logging.info('%s pin %s configured as INPUT' %(self.pinsIn[i]['name'], str(self.pinsIn[i]['pin'])))

            self.pinsIn[i]['state'] = GPIO.input(self.pinsIn[i]['pin'])
            logging.info('%s initial state is %s' %(self.pinsIn[i]['name'], str(self.pinsIn[i]['state'])))

            #configure event detections for pinType levelSensor & interface
            if self.pinsIn[i]['pinType'] == 'displayFlag':
                GPIO.add_event_detect(self.pinsIn[i]['pin'], GPIO.BOTH, callback=self.displayFlag, bouncetime=500) 
                logging.info('%s set as displayFlag callback' %(str(self.pinsIn[i]['name'])))
            elif self.pinsIn[i]['pinType'] == 'interface':
                GPIO.add_event_detect(self.pinsIn[i]['pin'], GPIO.RISING, callback=self.buttonPress, bouncetime=500) 
                logging.info('%s set as button callback' %(str(self.pinsIn[i]['name'])))

    def updateState(self, channel, value):
    for i in self.pinsIn:
        if channel == self.pinsIn[i]['pin']:
            self.pinsIn[i]['state'] = value
            print('%s pin triggered, %s configured state to %s' %(str(channel), self.pinsIn[i]['name'], self.pinsIn[i]['state'])) # debug

    def displayFlag(self, channel):
    if GPIO.input(channel) == 1:
        self.updateState(channel, 1)
        #self.motorControl(name='drv0', speed=0, direction = 'brake')
    if GPIO.input(channel) == 0:
        self.updateState(channel, 0)


        