from RPi import GPIO as GPIO
GPIO.setmode(GPIO.BCM)

from smbus2 import SMBus
import logging
import time

class i2cPi:
    def __init__(self):

        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG, datefmt="%H:%M:%S")

        #general 038 MCU DAQ configurations
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

        self.fanTypes = {
            'EFB' : {'serial': 'EFB0612HHA-F00','rpm': 4800, 'pulseRev': 2, 'terminals':3, 'tachOut': 'openDrain', 'type': 'axial', 'life': 70000, 'cfm': 21.2, 'inH2O': 0.169, 'size': '60x60x10mm'},
            'AFB' : {'serial': 'AFB0412VHA-AF00','rpm': 8000, 'pulseRev': 2, 'terminals':3, 'tachOut': 'openDrain', 'type': 'axial', 'life': 70000, 'cfm': 9.3, 'inH2O': 0.242, 'size': '40x40x10mm'},
            'BFB' : {'serial': 'BFB0312MA-CF00','rpm': 6500, 'pulseRev': 2, 'terminals':3, 'tachOut': 'openDrain', 'type': 'blower', 'life': 30000, 'cfm': 1.2, 'inH2O': 0.206, 'size': '30x30x10mm'},
        }

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

    def fanConfig(self):    
        self.fanFreq('low', 7)  #configure low frequency mode, monitoring, & 88.2 Hz
        '''The register default is 2 pulses / rev, but explicitly setting it. 
        In the future we may want this to be a configurable function'''
        self.bus.write_byte_data(0x2c, 0x43, 0x55)  #set conversion to 2 pulses / rev
        self.checkRegister(0x43, 0x55)

    def fanFreq(self, freqRange='low', freq=7):
        if freqRange =='low':
            self.bus.write_byte_data(0x2c, 0x40, 0x41)  #configure to low frequency mode by setting config reg 1 0x40[6] bit to 1, fan now between 11-88.2 hz depending on prior 0x74 register values.
            self.checkRegister(0x40, 0x41)
            print('Configured for low frequency PWM, monitoring enabled')
        elif freqRange =='hi':
            self.bus.write_byte(0x2c, 0x40, 0x01)   #configure to high frequency mode, monitoring
            self.checkRegister(0x40, 0x41)
            print('Configured for high frequency PWM, monitoring enabled')
        else:
            print('Nonvalid entry for freq range, enter low or hi')
        self.bus.write_byte_data(0x2c, 0x74, freq)  #hard set 88.2Hz if freq=7 by setting config reg 2 0x74[6:4] bits to 111 - MAKE SURE IN register 0x40 is in LOW FREQ MODE before changing to avoid fan damage.
        self.checkRegister(0x74, 0x70)

    def fanPWM(self, fan=1, dutyCycle=100): #selects fan and controls duty cycle from 0-100%
        try:
            duty8bit = int(dutyCycle/0.39)  #0.39 is the conversion factor from % to bits.
            fanRegister = 0x32+fan-1 #selector for fan register 0x32-0x35
            if duty8bit > 255:
                duty8bit = 255
            if (fan >= 1 and fan <= 4):
                self.bus.write_byte_data(0x2c, fanRegister, duty8bit) #set PWM for fan
                time.sleep(0.1)    #some delay needed for the registry to refresh from stale.
                readByte = self.bus.read_byte(0x2c, 0x00)
                self.checkRegister(fanRegister, duty8bit)
                print('PWM%s Register %s is set to %s hex, aka %s percent' %(fan, fanRegister, hex(readByte), (readByte*0.39)))
            else:
                print('Fan out of range, specify fan #1, 2, 3, or 4')
        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 0x2c while writing fanPWM')

    def rbRPM(self, fan=1):
        self.bus.write_byte(0x2c, 0x2a)
        lowbyte = self.bus.read_byte(0x2c, 0x2a)
        self.bus.write_byte(0x2c, 0x2b)
        highbyte = self.bus.read_byte(0x2c, 0x2b) << 8
        rpm = 5400000 * 60 / (highbyte | lowbyte)   #5400000 is from 90kHz clock * 60 sec
        print(rpm)

    def checkRegister(self, askedregister, wanted):  #assumes a prior write has been performed so pointer address previously set
        readback = self.bus.read_byte(0x2c, 0x00)
        if wanted == readback:
            print('Register %s value %s, %s, 0d%s applied & verified' %(hex(askedregister), hex(wanted), bin(wanted), wanted))
        else:
            print('Register value is %s, not %s wanted' %(readback, wanted))

    def tempPoll(self, sensorNumber = 4): #polls max temp register and first 4 temp registers by default.
        try:
            self.bus.write_byte(0x2c, 0x40, 0xC1)   #set TMP daisy, set low frequency mode,  set monitoring.
            print('Waiting for 1 seconds to gather TMP05 data')
            time.sleep(sensorNumber * 0.2)   #wait 200 mS per TMP sensor, in tester board we have 4. Max of 10, so prob ~2 sec max.
            self.bus.write_byte(0x2c, 0x40, 0x41)    #stop TMP daisy, set low frequency mode, set monitoring.

            '''Let's poll max detected temp register, and the other 4 and print them out'''
            self.bus.write_byte(0x2c, 0x78) #poll max detected temp register
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

    def adtEn(self):
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