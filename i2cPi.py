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
        self.setFreq()  #configure low frequency mode, monitoring, & 88.2 Hz
        self.setPulsesPerRev()

    def setFreq(self, freqRange='low', freqBits=0b111): 
        if freqRange =='low':
            self.reg1_defaultConfig()   #set low freq + monitoring + temp - range now 11-88.2 hz.
            self.checkRegister(0x40, 0x41)
            print('Configured for low frequency PWM, monitoring enabled')
        elif freqRange =='hi':
            self.bus.write_byte(0x2c, 0x40, 0x81)   #set high freq + monitoring + temp
            self.checkRegister(0x40, 0x41)
            print('Configured for high frequency PWM, monitoring enabled')
        else:
            print('Nonvalid entry for freq range, enter low or hi')
        self.bus.write_byte(0x2c, 0x74)
        currentVal = self.bus.read_byte(0x2c, 0x74)
        freqBits = freqBits << 3 | currentVal    #freqBits pos [6:4], bitshift 3 to left, insert into current register values
        self.bus.write_byte_data(0x2c, 0x74, freqBits)  #hard set 88.2Hz if freq=7 by setting config reg 2 0x74[6:4] bits to 111 - MAKE SURE IN register 0x40 is in LOW FREQ MODE before changing to avoid fan damage.
        self.checkRegister(0x74, 0x70)

    def setPulsesPerRev(self, fan=1, pulseRev = 2):
        '''!!!INCOMPLETE!!!! Want this function to allow configuration per fan, currently hardsets all 4 to 2 pulsese / revolution'''
        # bits assignment for each pulse per rev: 00=1, 01=2, 10=3, 11=4
        self.bus.write_byte_data(0x2c, 0x43, 0x55)  #!!!HARDSET!!! - 2 pulses / rev
        self.checkRegister(0x43, 0x55)
        print("Configured Fan1-4 for 2 pulses per revolution")

    def setPWM(self, fan=1, dutyCycle=100): #selects fan and controls duty cycle from 0-100%
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
                print('PWM%s Register %s is set to %s hex, aka %s percent' %(fan, hex(fanRegister), hex(readByte), (readByte*0.39)))
            else:
                print('Fan out of range, specify fan #1, 2, 3, or 4')
        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 0x2c while writing fanPWM')

    '''tmin range: 0-255 degrees, pmin & pmax: 0-255 for 0-100% - reference pg.26 of ADT740 for instructions'''

    def setAutoMonitor(self, 
    tmin1=25, tmin2=25, tmin3=25, tmin4=25, 
    pmin1=0xF, pmin2=0xF, pmin3=0xF, pmin4=0xF,
    pmax1=0xFF, pmax2=0xFF, pmax3=0xFF, pmax4=0xFF):
        '''Configure to automatic fan control in PWM1/2 & PWM3/4 registers'''
        self.bus.write_byte_data(0x2c, 0x68, 0xC0)  #set to automatic fan control mode PWM 1 & 2
        self.bus.write_byte_data(0x2c, 0x69, 0xC0)  #set to automatic fan control mode PWM 3 & 4
        logging.info('Configuring to automatic fan control behavior for PWM1-4')
        '''Assign tmp sensors to each fan'''
        self.bus.write_byte_data(0x2c, 0x7C, 0x12)  #Assign 0x20 TMP sensor to Fan1, 0x21 TMP to Fan2
        self.bus.write_byte_data(0x2c, 0x7D, 0x34)  #Assign 0x22 TMP sensor to Fan3, 0x23 TMP to Fan4
        '''When temp exceeds Tmin, fan runs at PWMin. Increases to max speed PWMax at Tmin + 20C'''
        self.bus.write_byte_data(0x2c, 0x6E, tmin1)  #Temp Tmin1 register
        self.bus.write_byte_data(0x2c, 0x6F, tmin2)  #Temp Tmin2 register
        self.bus.write_byte_data(0x2c, 0x70, tmin3)  #Temp Tmin3 register
        self.bus.write_byte_data(0x2c, 0x71, tmin4)  #Temp Tmin4 register
        logging.info('Setting min. temp to %s, %s, %s, & %s' %(tmin1, tmin2, tmin3, tmin4))
        '''Sets PWM min duty cycle - will start running @ this duty cycle when Tmin exceeded'''
        self.bus.write_byte_data(0x2c, 0x6A, pmin1)  #PWM1 min speed register
        self.bus.write_byte_data(0x2c, 0x6B, pmin2)  #PWM2 min speed register
        self.bus.write_byte_data(0x2c, 0x6C, pmin3)  #PWM3 min speed register
        self.bus.write_byte_data(0x2c, 0x6D, pmin4)  #PWM4 min speed register
        logging.info('Setting min pwm to %s, %s, %s, & %s' 
            %((pmin1*.39), (pmin2*.39), (pmin3*.39), (pmin4*.39)))
        '''Sets PWM max duty cycle - will start running @ this duty cycle when Tmin exceeded'''
        self.bus.write_byte_data(0x2c, 0x6A, pmax1)  #PWM1 max speed register
        self.bus.write_byte_data(0x2c, 0x6B, pmax2)  #PWM2 max speed register
        self.bus.write_byte_data(0x2c, 0x6C, pmax3)  #PWM3 max speed register
        self.bus.write_byte_data(0x2c, 0x6D, pmax4)  #PWM4 max speed register
        logging.info('Setting max pwm to %s, %s, %s, & %s' 
            %((pmax1*.39), (pmax2*.39), (pmax3*.39), (pmax4*.39)))
        '''Sets PWM max duty cycle - will start running @ this duty cycle when Tmin exceeded'''
        self.reg1_defaultConfig(STRT=0, HF_LF=1, T05_STB=1) #config to run monitoring, low freq, & TMPstartpulse

    def setTempLimits(self, tempLow = 0x4, tempHigh = 0x50, sensors = 4):
        '''default power-on values is -127C (0x81) & 127C (0x7F)'''
        '''MSB signifies negative temp, ADC - 256'''
        '''register 0x44 - 0x57'''
        count = 1
        try:
            while count < (sensors + 1):
                hexAddLow = 0x44+(2*(count-1))
                hexAddHigh = 0x45+(2*(count-1))
                self.bus.write_byte_data(0x2c, hexAddLow, tempLow)   #write tempLow for all 10
                logging.info('Address %s applied value %s' %(hex(hexAddLow), hex(tempLow)))
                self.bus.write_byte_data(0x2c, hexAddHigh, tempHigh)   #write tempHigh for all 10
                logging.info('Address %s applied value %s' %(hex(hexAddHigh), hex(tempHigh)))
                count += 1
        except:
            logging.info('Failed to set')

    def setTachLimits(self, tachMinLowB, tachMinHighB, tachMaxLowB, tachMaxHighB):
        #Default value sets min and max at furthest range, so does not trigger SMBALERT
        '''!INCOMPLETE! - register is 0x58 - 0x67. This register is a bit nasty, as we have to know map the relationship between normal PWM duty cycle, frequency, and tachometer readback and adjust this TachLimit as the automatic fan controller adjusts PWM up and down in response to temperature. Otherwise, I think these registers will Flag.'''

    def rbPWM(self):
        for fanRegister in [0x32, 0x33, 0x34, 0x35]:
            self.bus.write_byte(0x2c, fanRegister)
            readByte=self.bus.read_byte(0x2c, 0x00)
            print('PWM Register %s is set to %s hex, aka %s percent' %(hex(fanRegister), hex(readByte), (readByte*0.39)))

    def rbRPM(self, fan=1):
        hexAddLow = 0x2a+(2*(fan-1))
        hexAddHigh = 0x2b+(2*(fan-1))
        '''Read order is low byte, then high byte. A low byte read will FREEZE the high byte register value until both low and high byte are read'''
        self.bus.write_byte(0x2c, hexAddLow)    
        lowbyte = self.bus.read_byte(0x2c, hexAddLow)
        self.bus.write_byte(0x2c, hexAddHigh)
        highbyte = self.bus.read_byte(0x2c, hexAddHigh) << 8
        highlowbyte = highbyte | lowbyte    #let's concatenate these bits
        if highlowbyte == 0xFFFF:
            print('Fan Error! PWM @ 0%, stalled, blocked, failed, or unpopulated')
        else:
            rpm = 5400000 / highlowbyte   #5400000 is from 90kHz clock * 60 sec
            print("Fan #%s is read at rpm %s" %(fan, rpm))

    def rbTempN(self, sensorNumber = 4): #polls max temp and N sensors (up to 10)
        self.reg1_defaultConfig()   #set TMP daisy, set low frequency mode,  set monitoring.
        print('Waiting for %s seconds to gather TMP05 data' %(sensorNumber * 2))
        time.sleep(sensorNumber * 0.2)  #wait 200 mS per TMP sensor, in tester board we have 4. Max of 10, so prob ~2 sec max.
        self.bus.write_byte(0x2c, 0x40, 0x41)   #stop TMP daisy, set low freq, en monitoring.
        print('Max Temp Register 0x78 is %s from all temp sensors' %self.writeRead(0x78))   #poll max temp
        count = 1
        try:
            while count < (sensorNumber + 1):
                hexAddTemp = 0x20 + count - 1
                logging.info('Temp Register %s is at temp value %s C' %(hex(hexAddTemp), self.writeRead(hexAddTemp)))
                count+=1        
        except:
            logging.info('Failed temperature polling')
        self.reg1_defaultConfig()   #restart monitoring & prior configurations


    def rbInterrupts(self):
        print('Interrupt Status Register 1: %s' %bin(self.writeRead(0x41)))
        print('Interrupt Status Register 2: %s' %bin(self.writeRead(0x42)))
    
    def reg1_defaultConfig(self, STRT=0, HF_LF=1, T05_STB=1):
        '''!-INCOMPLETE-! - change to dynamically take in values instead of hard-set values'''
        self.bus.write_byte_data(0x2c, 0x40, 0xc1)  #config to run monitoring (0), low freq (1), & TMPstartpulse (1)
        self.checkRegister(0x40, 0xc1)
        print('Config Register 1 bits set - STRT: %s HF_LF: %s T05_STB: %s' %(STRT, HF_LF, T05_STB))

    def checkRegister(self, wantedReg, wantedVal):  #assumes a prior write has been performed so pointer address previously set
        readback = self.bus.read_byte(0x2c, 0x00)
        if wantedVal == readback:
            print('Register %s value check: (%s, %s, 0d%s)' %(hex(wantedReg), hex(wantedVal), bin(wantedVal), wantedVal))
        else:
            print('Register value is %s, not %s wanted' %(readback, wantedVal))

    def writeRead(self, pointerAddress):
        self.bus.write_byte(0x2c, pointerAddress)
        return self.bus.read_byte(0x2c, pointerAddress)

    def adtEn(self):
        self.bus.write_byte_data(0x2c, 0x74, (self.bus.read_byte(0x2c, 0x74) | 0x80))    #keep all prior bits, flip [7] to 1.
    
    def enable(self):
        self.bus.write_byte_data(0x2c, 0x40, (self.bus.read_byte(0x2c, 0x40) | 0x20))   #Set low frequency fan drive
        self.bus.write_byte(0x2c, 0x74, 0x70)   #re-enable, set to 88.2 Hz fan speed