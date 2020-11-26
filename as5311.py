import spidev

#x = bin((spi.readbytes(3)[0] << 4))
#((spi.readbytes(3)[0] & 0b01111111) << 5) | (spi.readbytes(3)[1] >> 5)
#pullBits = ((payload[0] & 0b01111111) << 5) | (payload[1] >> 5)

class AS5311:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.bus = 0    #use default SPI bus 0
        self.device = 0 #use default CS0 pin on Pi
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = 500000  #lets set the SPI bus to 500kHz, AS5311 can go up to 1MHz comms
        self.spi.mode = 3    #lets set to mode 3 for default reading, note, when we change to magnetic strength sensing, we need to swap to spi mode 0.

    def ssi_extraction(self, mode):
        '''SSI comms from the device loses the 1st bit, so its technically 7, 8, 8 relevant bits coming in'''
        self.spi.mode = mode    #Use 2 for position data, use 1 for field strength data
        payload = self.spi.readbytes(3)
        print('Bit check - Raw Payload: %s %s %s' %(bin(payload[0]), bin(payload[1]), bin(payload[2])))
        beg_word = (payload[0] & 0b01111111) << 16   #mask off bit-7 MSB, then shift in space for 16 bits 
        middle_word = payload[1] << 8    #bit shift word by 8
        end_word = payload[2]  #lose the last 5 bits
        print('Bit check - Treated Words: %s %s %s' %(bin(beg_word), bin(middle_word), bin(end_word)))
        combined_word = (beg_word | middle_word | end_word) >> 5   #combine and shift by 5 to get final 18-bit word
        print('Bit check - Combined Word: %s' %bin(combined_word))
        return combined_word
        
    def position_word(self):
        combined_word = self.ssi_extraction(mode = 2)
        abs_position = combined_word >> 6
        #print('%s absolute position' %abs_position)
        return abs_position

    def magnetic_word(self):
        combined_word = self.ssi_extraction(mode = 1)
        field_strength = combined_word >> 6
        #print('%s mT field strength' %field_strength)
        return field_strength

    def report_zrange(self, combined_word):
        zrange_lookup = {0b000 : {'state': 'Green - static', 'range': '10..40 mT', 'distance': 'static'},
                        0b010 : {'state': 'Green - increasing field', 'range': '10..40 mT', 'distance': 'increase'},
                        0b001 : {'state': 'Green - decreasing field', 'range': '10..40 mT', 'distance': 'decrease'},
                        0b011 : {'state': 'Yellow - Under / Over mT - reduced accuracy', 'range': '3.4..54.5 mT', 'distance': 'n/a'},
                        0b111 : {'state': 'Red - ERROR - signficant under / over mT', 'range': 'field < 3.4 mT | > 54.5 mT', 'distance': 'n/a'},
                        }
        magnetic_bits = (combined_word & 0b1111) >> 1   #mask off last 4 bits and shift off parity bit
        for bits in zrange_lookup:
            if magnetic_bits == bits:
                for items in zrange_lookup[bits]:
                    print('Zrange - %s : %s.' %(items, zrange_lookup[bits][items]))
                return  #EXIT OUT OF LOOP

    def parity_check(self, combined_word):
        '''Incomplete'''
        parity_bit = combined_word & 0b1    #mask
        return

    def check_errors(self, combined_word):
        error_bits = (0b111111 & combined_word) >> 3    #grab last 6 bits, move 3 off
        ocf = (0b100 & error_bits) >> 2
        cof = (0b010 & error_bits) >> 1
        linearity = (0b001 & error_bits)
        error_report = 'Error Flag Raised on:'
        if ocf == 0:    #LOW indicates offset compensation algorithm did not finish. Data invalid.
            error_report = ' Offset Compensation NOT finished (OCF)'
        if cof == 1:    #HIGH indicates cordic overflow. Data invalid.
            error_report += ' Cordic Overflow (COF)'
        if linearity == 1:  #HIGH indicates critical output linearity, i.e. field strength / signal outside of compensation regime. Reads are suspect.
            error_report += ' Linearity Alarm'
        if error_bits == 0b100:
            error_report += ' None'
        return error_report

    def report(self, mode = 3):
        combined_word = self.ssi_extraction(mode = mode)
        databits = combined_word >> 6
        '''Do not use mode 2 or 1, these are just experimental test modes to see what data comes back during development.'''
        if mode == 3:
            print('Position: %s. SPI mode 3 (bin: %s | hex: %s) ' %(databits, bin(databits),hex(databits)))
        elif mode == 0:
            print('Field Strength: %s (0-4096 proportional). SPI mode 0 (bin: %s | hex: %s).' %(databits, bin(databits), hex(databits)))
            print(self.fieldstrength_calculator(combined_word))
        elif mode == 2:
            print('Position: %s. SPI mode 2 - invalid data [wrong clock edge] (bin: %s | hex: %s) ' %(databits, bin(databits),hex(databits)))
        elif mode == 1:
            print('Field Strength: %s (0-4096 proportional). SPI mode 1 - invalid data [wrong clock edge] (bin: %s | hex: %s) ' %(databits, bin(databits),hex(databits)))
            print(self.fieldstrength_calculator(combined_word))
        self.report_zrange(combined_word)   #prints z-range info
        print(self.check_errors(combined_word)) #prints error bit checks

    def fieldstrength_calculator(self, combined_word):
        msb_eight = combined_word >> 10
        if msb_eight == 0x3F:
            return 'Field between 10-40 mT'
        elif (0x20 < msb_eight < 0x3F) or (0x3F < msb_eight < 0x5F):
            return 'Field between 3.4-10 mT'
        elif (0x3F < msb_eight < 0x5F):
            return 'Field between 40-54.5 mT'
        else:
            return 'ERROR: Outside of valid range 3.4 - 54.5 mT. Service stage.'