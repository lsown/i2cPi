from RPi import GPIO as GPIO
GPIO.setmode(GPIO.BCM)

from smbus2 import SMBus
import logging
import time

class i2cPi:
    def __init__(self):

        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG, datefmt="%H:%M:%S")

        self.pinsIn = {
            'displayFlag' : {'name' : 'displayFlag', 'pinType':'interface','state':0,'priorState':0, 'pin': 22},
            'adtFlag' : {'name' : 'adtFlag', 'pinType':'interface','state':0,'priorState':0, 'pin': 14},
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

        self.bus = SMBus(1)

    def piSetup(self): #Sets up GPIO pins, can also add to GPIO.in <pull_up_down=GPIO.PUD_UP>

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

    def displayFlag(self, channel):
        if GPIO.input(channel) == 1:
            self.updateState(channel, 1)
            #self.motorControl(name='drv0', speed=0, direction = 'brake')
        if GPIO.input(channel) == 0:
            self.updateState(channel, 0)

    def tunnel(self):
        try:
            self.bus.read_byte_data(0x77, 0x00) #check config register of mux layer-0 
            self.bus.write_byte(0x77, 0x01) #open channel 0
            self.bus.read_byte_data(0x77, 0x00) #confirm channel 0 opened
            try:
                self.bus.read_byte_data(0x41, 0x03)  #read PCA9536 configuration register, expect 0x0F - configured inputs
                self.bus.write_byte_data_data(0x41, 0x03, 0x00) #Set register 3 to 0b0, configures all to output
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

    def adtConfig(self):    
        try:
            self.bus.write_byte(0x2c, 0x74)  #lets try to read from AD7T740.
            self.bus.read_byte(0x2c, 0x74) #check assignment
        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 77 - layer 1 - ADT7470')