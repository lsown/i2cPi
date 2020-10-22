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
        self.piSetup()
        self.tunnel()

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
        if GPIO.input(channel) == 0:
            self.updateState(channel, 0)

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

    def adtConfig(self):    
        """ This block configures the system frequency """
        try:
            self.bus.write_byte(0x2c, 0x74)  #lets try to read from AD7T740.
            self.bus.read_byte(0x2c, 0x74) #check assignment, should be 0x00.
            self.bus.write_byte_data(0x2c, 0x40, 0x41)  #configure to low frequency mode by setting config reg 1 0x40[6] bit to 1, fan now @ 11 hz.
            self.bus.write_byte_data(0x2c, 0x74, 0x70)  #configure from 11 Hz to 88.2Hz by setting config reg 2 0x74[6:4] bits to 111 - MAKE SURE IN LOW FREQ MODE 0x40 register
        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 77 - layer 1 - ADT7470')

    def fanConfig(self, freqRange=0, freq=7):
        try:
            self.bus.write_byte_data(0x2c, 0x74, 0x80)
            print('Temp Register 0x20 is %s' %self.bus.read_byte(0x2c, 0x20))
        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 0x2c while configuring fans')

    '''fan is fan #[1-3], duty cycle is 0 to 100%'''
    def fanPWM(self, fan=1, dutyCycle=100):
        try:
            dutyCycle_conv = int(dutyCycle/0.39)
            if dutyCycle_conv > 255:
                dutyCycle_conv = 255
                print(dutyCycle_conv)
            if fan == 1:
                self.bus.write_byte_data(0x2c, 0x32, dutyCycle_conv) #set PWM for fan 1
                print('Test register is %s' %self.bus.read_byte(0x2c, 0x00))
                print('PWM1 Register 0x32 is set to %s' %self.bus.read_byte(0x2c, 0x00)*0.39)
            elif fan == 2:
                self.bus.write_byte_data(0x2c, 0x33, dutyCycle_conv) #set PWM for fan 2
            elif fan == 3:
                self.bus.write_byte_data(0x2c, 0x34, dutyCycle_conv) #set PWM for fan 3
            elif fan == 4:
                self.bus.write_byte_data(0x2c, 0x35, dutyCycle_conv) #set PWM for fan 4
            elif (fan > 1 or fan > 4):
                print("Non-valid input, please select fan value 1,2,3, or 4.")
        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 0x2c while writing fanPWM')

    def tempPoll(self):
        try:
            self.bus.write_byte(0x2c, 0x40, 0xC1)   #set TMP daisy, set low frequency mode,  set monitoring.
            print('Waiting for 1 seconds to gather TMP05 data')
            time.sleep(1)   #wait 200 mS per TMP sensor, in tester board we have 4. Max of 10, so prob ~2 sec max.
            self.bus.write_byte(0x2c, 0x40, 0x41)    #stop TMP daisy, set low frequency mode, set monitoring.

            '''Let's poll each 4 and print them out'''
            self.bus.write_byte(0x2c, 0x78) #poll max-temp register
            print('Max Temp Register 0x78 is %s from all temp sensors' %self.bus.read_byte(0x2c, 0x78))
            self.bus.write_byte(0x2c, 0x20) #poll 1
            print('Temp Register 0x20 is %s' %self.bus.read_byte(0x2c, 0x20))
            self.bus.write_byte(0x2c, 0x21) #poll 2
            print('Temp Register 0x21 is %s' %self.bus.read_byte(0x2c, 0x21))
            self.bus.write_byte(0x2c, 0x22) #poll 3
            print('Temp Register 0x22 is %s' %self.bus.read_byte(0x2c, 0x22))
            self.bus.write_byte(0x2c, 0x23) #poll 4
            print('Temp Register 0x23 is %s' %self.bus.read_byte(0x2c, 0x23))

        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 0x2c - failed on temp config poll') 

    def shtdown(self):
        self.bus.write_byte(0x2c, 0x74)
        self.bus.write_byte_data(0x2c, 0x74, (self.bus.read_byte(0x2c, 0x74) | 0x80))    #keep all prior bits, flip [7] to 1.
    
    def enable(self):
        self.bus.write_byte_data(0x2c, 0x40, (self.bus.read_byte(0x2c, 0x40) | 0x20))   #Set low frequency fan drive
        self.bus.write_byte(0x2c, 0x74, 0x70)   #re-enable, set to 88.2 Hz fan speed

    def autofan(self):
        self.bus.write_byte_data(0x2c, 0x68, 0xC0)  #set to automatic fan control mode PWM 1 & 2
        self.bus.write_byte_data(0x2c, 0x69, 0xC0)  #set to automatic fan control mode PWM 3 & 4
        self.bus.write_byte_data(0x2c, 0x7C, 0x12)  #set 0x20 TMP to Fan1, 0x21 TMP to Fan2
        self.bus.write_byte_data(0x2c, 0x7D, 0x12)  #set 0x22 TMP to Fan3, 0x23 TMP to Fan4
        self.bus.write_byte_data(0x2c, 0x6E, )  #Temp Tmin