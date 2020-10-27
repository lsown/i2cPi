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

    def getPinState(self, pin):
        return GPIO.input(pin)

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

    def adtEN(self, wantedState = 'on'):
        #Bit value 0: ON, 1 OFF on bit7 of register 0x74
        if wantedState == 'on':
            payLoad = 0b0   
        elif wantedState == 'off':
            payLoad = 0b1   
        self.bus.write_byte_data(0x2c, 0x74, self.insertBits(0x74, 7, 7, payLoad))
        print('ADT7470 configured to %s , %s set on bit 7 of register 0x74' %(wantedState, bin(payLoad)))

    def configFansGlobal(self, 
    freqRange = "low", freqBits = 0b111, fanType='3-wire', fan_PPRev='all', pulseRev = 2,
    tempLow = 0x4, tempHigh = 0x50, sensors = 4,
    minRPM = 1000, maxRPM = 'max'
    ):    
        self.setFreq(freqRange, freqBits, fanType)  #configure low frequency mode, monitoring, & 88.2 Hz
        self.setPPRev(fan_PPRev, pulseRev) #configures pulses per RPM
        self.setTempLimitsGlobal(tempLow, tempHigh, sensors)    #configures all 4 temp limits
        self.setTachLimitsGlobal(minRPM, maxRPM)    #Calls .setTachLimits for each fan


    def setFreq(self, freqRange='low', freqBits=0b111, fanType = '3-wire'): 
        """Sets global frequency range for fans. Configures 2 registers, specifying low or hi frequency (0x40), and speed (0x74) in low frequency mode. Configures speed for lowest common denominator fan."""
        lowFreqDict = {0b000:11, 0b001: 14.7, 0b010: 22.1, 0b011: 29.4, 0b100:35.3, 0b101:44.1, 0b110:58.8, 0b111:88.2} #bit code for low frequency in Hz
        hiFreqDict = {0b000:1.4, 0b001: 22.5, 0b010: 22.5, 0b011: 22.5, 0b100:22.5, 0b101:22.5, 0b110:22.5, 0b111:22.5} #bit code for hi frequency in kHz
        '''Below prevents accidental setting of a 2- or 3-wire fan to > 1.4 kHz. This can potentially blow the fan internal circuitry in worst-case scenario.'''
        if (freqRange =='hi' and (freqBits > 0) and (fanType == '3-wire' or fanType == '2-wire')):
            print('Invalid configuration, can only run 4-wire at 22.5 kHz. Exiting.')
            return None
        elif freqRange =='low':
            newRegVal = self.insertBits(0x40, 6, 6, 0b1)
            self.bus.write_byte_data(0x2c, 0x40, newRegVal)
            self.validateRegister(0x40, newRegVal)
            print('Configured for low frequency PWM')
        elif freqRange =='hi':
            newRegVal = self.insertBits(0x40, 6, 6, 0b0)
            self.bus.write_byte_data(0x2c, 0x40, newRegVal)
            self.validateRegister(0x40, newRegVal)
            print('Configured for high frequency PWM')
        else:
            print('Nonvalid entry for freq range, enter low or hi')
            return None #escape out of function before setting the frequency registry
        newRegVal = self.insertBits(0x74, 6, 4, freqBits)
        self.bus.write_byte_data(0x2c, 0x74, newRegVal)
        self.validateRegister(0x74, newRegVal)
        if freqRange =='low':
            print('Configured %s Hz for %s frequency PWM' %(lowFreqDict[freqBits], freqRange))
        elif freqRange =='hi':
            print('Configured %s kHz for %s frequency PWM' %(hiFreqDict[freqBits], freqRange))

    def setPWM(self, fan=1, dutyCycle=100): 
        """Sets duty cycle from 0-100% for fan specified"""
        try:
            fanRegister = 0x32+fan-1 #selector for fan register 0x32-0x35
            duty8bit = int(dutyCycle/0.39)  #0.39 is the conversion factor from % to bits.
            if duty8bit > 255:
                duty8bit = 255
            if (fan >= 1 and fan <= 4):
                self.bus.write_byte_data(0x2c, fanRegister, duty8bit) #set PWM for fan
                time.sleep(0.1)    #some delay needed for the registry to refresh from stale.
                readByte = self.bus.read_byte(0x2c, 0x00)
                self.validateRegister(fanRegister, duty8bit)
                print('PWM%s Register %s is set to %s hex, i.e. %s percent' %(fan, hex(fanRegister), hex(readByte), (readByte*0.39)))
            else:
                print('Fan out of range, specify fan #1, 2, 3, or 4')
        except OSError:
            logging.info('Error 121 - Remote I/O Error on address 0x2c while writing fanPWM')

    def setPPRev(self, fan='all', pulseRev = 2):
        '''Configures IC calculator for each fan tach. Valid fan entries: 'all', 1, 2, 3, 4. Valid pulseRev entries: 1, 2, 3, 4.'''
        # bits assignment for each pulse per rev: 00=1, 01=2, 10=3, 11=4        
        pulseCodeList = [0b00, 0b01, 0b10, 0b11]    #1, 2, 3, or 4 pulses / rev
        pulseCode = pulseCodeList[pulseRev-1] #translate fan number to pulseRev code
        if fan == 'all':
            newRegVal = (pulseCode) | (pulseCode << 2) | (pulseCode << 4) | (pulseCode << 6)
        elif fan == 1:
            newRegVal = self.insertBits(0x43, 1, 0, pulseCode)
        elif fan == 2:
            newRegVal = self.insertBits(0x43, 3, 2, pulseCode)
        elif fan == 3:
            newRegVal = self.insertBits(0x43, 5, 4, pulseCode)
        elif fan == 4:
            newRegVal = self.insertBits(0x43, 7, 6, pulseCode)
        self.bus.write_byte_data(0x2c, 0x43, newRegVal) 
        self.validateRegister(0x43, newRegVal)
        print("Configured Fan %s for %s pulses per revolution" %(fan, pulseRev))        

    def setManualModeAll(self):
        self.bus.write_byte_data(0x2c, 0x68, self.insertBits(0x68, 7, 6, 0b00))  #set man fan control mode PWM 1 & 2
        self.validateRegister(0x68, 0x00)
        self.bus.write_byte_data(0x2c, 0x69, self.insertBits(0x69, 7, 6, 0b00))  #set man fan control mode PWM 1 & 2
        self.validateRegister(0x69, 0x00)
        logging.info('Configured to manual fan control behavior for PWM1-4. Method .setPWM can now be used to manually control fan speeds.')

    def setAutoMonitor(self, 
        tmin1=25, tmin2=25, tmin3=25, tmin4=25,
        pmin1=0x40, pmin2=0x40, pmin3=0x40, pmin4=0x40,
        pmax1=0xFF, pmax2=0xFF, pmax3=0xFF, pmax4=0xFF):
        '''tmin value range: 0-255 degrees, pmin & pmax: 0-255 for 0-100% - reference pg.26 of ADT740 for instructions'''
        '''!--ALERT--! Probably want to eventually separate min / max registers into their own configurable methods''' 
        #Configure to automatic fan control in PWM1/2 & PWM3/4 registers
        self.bus.write_byte_data(0x2c, 0x68, self.insertBits(0x68, 7, 6, 0b11))  #set auto fan control mode PWM 1 & 2
        self.bus.write_byte_data(0x2c, 0x69, self.insertBits(0x69, 7, 6, 0b11))  #set auto fan control mode PWM 3 & 4
        logging.info('Configured register 0x68 & 0x69 to automatic fan control mode for Fan 1-4')
        #Assign tmp sensors to each fan  
        self.bus.write_byte_data(0x2c, 0x7C, 0x12)  #Assign 0x20 TMP sensor to Fan1, 0x21 TMP to Fan2
        self.bus.write_byte_data(0x2c, 0x7D, 0x34)  #Assign 0x22 TMP sensor to Fan3, 0x23 TMP to Fan4
        logging.info('Hard-set assigned TMP01, 02, 03, 04 to Fan01, 02, 03, 04, respectively')
        #When temp exceeds Tmin, fan runs at PWMin. Increases to max speed PWMax at Tmin + 20C
        self.bus.write_byte_data(0x2c, 0x6E, tmin1)  #Temp Tmin1 register
        self.bus.write_byte_data(0x2c, 0x6F, tmin2)  #Temp Tmin2 register
        self.bus.write_byte_data(0x2c, 0x70, tmin3)  #Temp Tmin3 register
        self.bus.write_byte_data(0x2c, 0x71, tmin4)  #Temp Tmin4 register
        logging.info('Setting min. temp to %sC, %sC, %sC, & %sC' %(tmin1, tmin2, tmin3, tmin4))
        #Sets PWM min duty cycle - will start running @ this duty cycle when Tmin exceeded
        self.bus.write_byte_data(0x2c, 0x6A, pmin1)  #PWM1 min speed register
        self.bus.write_byte_data(0x2c, 0x6B, pmin2)  #PWM2 min speed register
        self.bus.write_byte_data(0x2c, 0x6C, pmin3)  #PWM3 min speed register
        self.bus.write_byte_data(0x2c, 0x6D, pmin4)  #PWM4 min speed register
        logging.info('Setting min pwm to %s%%, %s%%, %s%%, & %s%%' 
            %(int(pmin1*.39), int(pmin2*.39), int(pmin3*.39), int(pmin4*.39)))
        #Sets PWM max duty cycle - will start running @ this duty cycle when Tmin exceeded
        self.bus.write_byte_data(0x2c, 0x38, pmax1)  #PWM1 max speed register
        self.bus.write_byte_data(0x2c, 0x39, pmax2)  #PWM2 max speed register
        self.bus.write_byte_data(0x2c, 0x3A, pmax3)  #PWM3 max speed register
        self.bus.write_byte_data(0x2c, 0x3B, pmax4)  #PWM4 max speed register
        logging.info('Setting max pwm to %s%%, %s%%, %s%%, & %s%%' 
            %(int(pmax1*.39), int(pmax2*.39), int(pmax3*.39), int(pmax4*.39)))
        self.bus.write_byte_data(0x2c, 0x40, self.insertBits(0x40, 0, 0, 0b1))  #configure to STRT monitoring & auto fan control based on limits
        self.bus.write_byte_data(0x2c, 0x40, self.insertBits(0x40, 7, 7, 0b1))  #configure to initiate TMP pulse
        logging.info('Configured to start monitoring & TMP pulse')

    def setAutoFanTempZone(self, fan=1, sensor=1):
        '''!---PLACEHOLDER---! For individually assigning each fan to a temperature zone'''
        return None

    def setAutoTminLimits(self, tmin=25, zone = 1):
        '''!---PLACEHOLDER---! For individually setting temperature zones'''
        return None

    def setAutoPmin(self, fan=1, pmin=0x40):
        '''!---PLACEHOLDER---! For individually setting pmin / fan'''
        return None

    def setAutoPmax(self, fan=1, pmin=0xFF):
        '''!---PLACEHOLDER---! For individually setting pmax / fan'''
        return None

    def setTempLimitsGlobal(self, tempLow = 0x4, tempHigh = 0x50, sensors = 4):
        '''Method sets global tempLow & tempHigh for sensors 1-10 to same value.'''
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
            logging.info('Failed to set temp limits')

    def setTempLimits(self, tempLow = 0x4, tempHigh = 0x50, sensorNumber = 1):
        '''!---PLACEHOLDER---! For individually setting temperature zones'''
        return None

    def setTachLimitsGlobal(self, minRPM ='min', maxRPM='max'):
        self.setTachLimits(1, minRPM, maxRPM)
        self.setTachLimits(2, minRPM, maxRPM)
        self.setTachLimits(3, minRPM, maxRPM)
        self.setTachLimits(4, minRPM, maxRPM)

    def setTachLimits(self, fan = 1, minRPM = 'min', maxRPM = 'max'):
        #Default register sets min and max at furthest range, so does not trigger SMBALERT
        '''!ALERT! - register is 0x58 - 0x67. This register is a bit nasty. 
        We need to update this register as the fan controller monitor adjusts PWM up and down in response to temperature, otherwise... these registers may flag.
        
        We'll need to map the normal PWM duty cycle, frequency, and tachometer readback in a real use case
        to determine fan behavior @ various PWM cycles to control for when alert flags occur.'''

        hexMinAddLow = 0x58+(2*(fan-1))
        hexMinAddHigh = 0x59+(2*(fan-1))
        hexMaxAddLow = 0x60+(2*(fan-1))
        hexMaxAddHigh = 0x61+(2*(fan-1))
        if minRPM == 'min':
            tachMinLowB = 0xff
            tachMinHighB = 0xff
        else:
            minClock = int(5400000 / minRPM)    #5.4e6 derives from 90kHz clock * 60 sec/min
            tachMinLowB = minClock & 0xff    #mask off high byte register
            tachMinHighB = (minClock >> 8) & 0xff    #shift off low byte register & shift
        if maxRPM == 'max':
            tachMaxLowB = 0x00
            tachMaxHighB = 0x00
        else:
            maxClock = int(5400000 / maxRPM)    #5.4e6 derives from 90kHz clock * 60 sec/min
            tachMaxLowB = maxClock & 0xff    #mask off high byte register
            tachMaxHighB = (maxClock >> 8) & 0xff   #shift off low byte register & shift
        '''Read order is low byte, then high byte. A low byte read will FREEZE the high byte register value until both low and high byte are read'''
        self.bus.write_byte_data(0x2c, hexMinAddLow, tachMinLowB)
        self.bus.write_byte_data(0x2c, hexMinAddHigh, tachMinHighB)  
        self.bus.write_byte_data(0x2c, hexMaxAddLow, tachMaxLowB)  
        self.bus.write_byte_data(0x2c, hexMaxAddHigh, tachMaxHighB)      
        logging.info('Configured Fan %s - Min Low Byte Register %s value to expected: %s, got %s.' 
            %(fan, hex(hexMinAddLow), hex(tachMinLowB), hex(self.writeRead(hexMinAddLow))))
        logging.info('Configured Fan %s - Min High Byte Register %s value expected: %s, got %s.' 
            %(fan, hex(hexMinAddHigh), hex(tachMinHighB), hex(self.writeRead(hexMinAddHigh))))
        logging.info('Configured Fan %s - Max Low Byte Register %s value expected: %s, got %s.' 
            %(fan, hex(hexMaxAddLow), hex(tachMaxLowB), hex(self.writeRead(hexMaxAddLow))))
        logging.info('Configured Fan %s - Max High Byte Register %s value expected: %s, got %s.' 
            %(fan, hex(hexMaxAddHigh), hex(tachMaxHighB), hex(self.writeRead(hexMaxAddHigh))))
        logging.info('Configured tach range to %s - %s' %(minRPM, maxRPM))

    def setINTmask(self, pointerAddress, bitName, maskEN = 1):
        masks = {'R7T': {'pointer':0x72, 'bitPos': 6}, 'R6T': {'pointer':0x72, 'bitPos': 5}, 'R5T': {'pointer':0x72, 'bitPos': 4}, 'R4T': {'pointer':0x72, 'bitPos': 3}, 'R3T': {'pointer':0x72, 'bitPos': 2}, 'R2T': {'pointer':0x72, 'bitPos': 1}, 'R1T': {'pointer':0x72, 'bitPos': 0}, 'fan4': {'pointer':0x73, 'bitPos': 7}, 'fan3': {'pointer':0x73, 'bitPos': 6}, 'fan2': {'pointer':0x73, 'bitPos': 5}, 'fan1': {'pointer':0x73, 'bitPos': 4}, 'daisy': {'pointer':0x73, 'bitPos': 3}, 'R10T': {'pointer':0x73, 'bitPos': 2}, 'R9T': {'pointer':0x73, 'bitPos': 1}, 'R8T': {'pointer':0x73, 'bitPos': 0}}
        newRegVal = self.insertBits(masks[bitName]['pointer'], masks[bitName]['bitPos'], masks[bitName]['bitPos'], maskEN)
        self.bus.write_byte_data(0x2c, masks[bitName]['pointer'], newRegVal)
        self.validateRegister(masks[bitName]['pointer'], newRegVal)

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
            print("Fan #%s is read at rpm %s" %(fan, int(rpm)))

    def rbTempN(self, sensorNumber = 4): #polls max temp and N sensors (up to 10)
        self.configReg1_defaults()   #set TMP daisy, set low frequency mode,  set monitoring.
        waitTime = sensorNumber * 0.2   #200 mS / TMP sensor. Max of 10 sensors. 
        print('Waiting for %s seconds to gather TMP05 data' %waitTime)
        time.sleep(waitTime)  #wait 200 mS per TMP sensor, in tester board we have 4. Max of 10, so prob ~2 sec max.
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
        self.configReg1_defaults()   #reapply default config

    def rbINT(self):
        print('!-------------------REPORT rbINT-------------------!')
        print('Interrupt Status Register 1 0x41: %s' %bin(self.writeRead(0x41)))
        print('Interrupt Mask   Register 1 0x72: %s' %bin(self.writeRead(0x72)))
        print('Interrupt Status Register 2 0x42: %s' %bin(self.writeRead(0x42)))
        print('Interrupt Mask   Register 2 0x73: %s' %bin(self.writeRead(0x73)))
        print('ALERT Pin state is %s' %self.getPinState(14))

    def rbAutoMonitor(self):
        tminList = []
        pminList = []
        pmaxList = []
        print('!-------------------REPORT: rbAutoMonitor-------------------!')
        print('PWM Config 1/2 0x68 & 3/4 0x69. Expected: 0xc0 vs. Read: %s & %s.' %(hex(self.writeRead(0x68)), hex(self.writeRead(0x69))))
        print('Therm Zone - Fan Assignment Zone 1/2 0x7c. Expected: 0x12 vs. Read: %s.' %(hex(self.writeRead(0x7c))))
        print('Therm Zone - Fan Assignment Zone 3/4. 0x7d. Expected: 0x34 vs. Read: %s.' %(hex(self.writeRead(0x7d))))
        for i in [0x6E, 0x6F, 0x70, 0x71]:  #Tmin Registers
            tminList.append(self.writeRead(i))
        print('Tmin1: %s || Tmin2: %s || Tmin3: %s || Tmin4: %s' %(tminList[0], tminList[1], tminList[2], tminList[3]))
        for i in [0x6A, 0x6B, 0x6C, 0x6D]:  #PWM min Registers
            pminList.append(int(self.writeRead(i)*.39))
        print('PMin Registers. Pmin1: %s%% || Pmin2: %s%% || Pmin3: %s%% || Pmin4: %s%%' %(pminList[0], pminList[1], pminList[2], pminList[3]))
        for i in [0x38, 0x39, 0x3A, 0x3B]:  #PWM max Registers
            pmaxList.append(int(self.writeRead(i)*.39))
        print('PMax Registers. Pmax1: %s%% || Pmax2: %s%% || Pmax3: %s%% || Pmax4: %s%%' %(pmaxList[0], pmaxList[1], pmaxList[2], pmaxList[3]))
        print('Config Register 1. Expected: 0b1x000001 vs. Read: %s' %(bin(self.writeRead(0x40))))

    def configReg1_defaults(self, STRT=0, HF_LF=1, T05_STB=1):
        '''!-INCOMPLETE-! - change to dynamically take in values instead of hard-set values'''
        self.bus.write_byte_data(0x2c, 0x40, 0xc1)  #config to run monitoring (0), low freq (1), & TMPstartpulse (1)
        self.validateRegister(0x40, 0xc1)
        print('Config Register 1 bits set - STRT: %s HF_LF: %s T05_STB: %s' %(STRT, HF_LF, T05_STB))

    def validateRegister(self, wantedReg, wantedVal):  #assumes a prior write has been performed so pointer address previously set
        readback = self.bus.read_byte(0x2c, 0x00)
        if wantedVal == readback:
            print('Register %s value: (%s, %s, %s)' %(hex(wantedReg), hex(wantedVal), bin(wantedVal), wantedVal))
        else:
            print('!--ERROR--! Register %s value is %s, not %s wanted' %(hex(wantedReg),readback, wantedVal))

    def insertBits(self, regAddress, posHi, posLow, payLoad):
        '''Helper function to insert in a bit payload without impacting surrounding bits in the byte. The regAddress is pointer address, posHi & posLow are bit position to be inserted, payload is wanted binary, ex. 0b11. Example: self.insertBits(0x43, 7, 6, 0b11) will insert in 0b11 into positions 7 & 6 of the byte at address 0x43.'''
        bitMaskList = [0b0, 0b1, 0b11, 0b111, 0b1111, 0b11111, 0b111111, 0b1111111] #mask list for masking bits 0-6
        currentReg = self.writeRead(regAddress)
        posHi = posHi + 1   #shift it up by one
        bitEndtoHi = (currentReg >> posHi) << posHi
        logging.info('insertBits: Hi bit[7:%s] from currentReg is %s' %(posHi, bin(bitEndtoHi)))
        bitMask = bitMaskList[posLow]
        logging.info('insertBits: Low bitmask applied is %s' %bin(bitMask))
        bitLowtoEnd = bitMask & currentReg
        logging.info('insertBits: Low bit[%s:0] from currentReg is %s' %(posLow, bin(bitLowtoEnd)))
        bitEnds = bitEndtoHi | bitLowtoEnd
        logging.info('insertBits: Applied final mask is %s' %bin(bitEnds))
        byteLoad = payLoad << posLow | bitEnds
        logging.info('insertBits: Final byteload with insertion is %s' %bin(byteLoad))
        return byteLoad

    def writeRead(self, pointerAddress):
        self.bus.write_byte(0x2c, pointerAddress)
        return self.bus.read_byte(0x2c, pointerAddress)
    