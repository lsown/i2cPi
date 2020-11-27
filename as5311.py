try:
    import spidev
except ModuleNotFoundError:
    print('AS5311 requires spidev library first before use!')

class AS5311:
    '''Class for talking to AS5311 chip. Commuicates via SSI, which is a modified version of SPI where we cut off first bit, and use the next 18-bits... but requires the standard 24-bit transaction. Uses SPI mode 3 for reading position, SPI mode 0 for reading magnetic field propotional strength. Physical requirements is a 1 mm pole for total distance 2 mm. Field strength requirements within 10-40 mT. 500 nm resolution.'''
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.bus = 0    #use default SPI bus 0
        self.device = 0 #use default CS0 pin on Pi
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = 1000000  #Up to 1 MHz SSI bus speed. ~ 42 Khz for 24-bits max theoretical... but internal sampling of position is restricted to ~10.4 kHz
        self.spi.mode = 3    #lets set to mode 3 for default reading, note, when we change to magnetic strength sensing, we need to swap to spi mode 0.

    def ssi_extraction(self, mode):
        '''SSI comms from the device loses the 1st bit, so its technically 7, 8, 8 relevant bits coming in'''
        self.spi.mode = mode    #Use 2 for position data, use 1 for field strength data
        payload = self.spi.readbytes(3)
        #print('Bit check - Raw Payload: %s %s %s' %(bin(payload[0]), bin(payload[1]), bin(payload[2])))
        beg_word = (payload[0] & 0b01111111) << 16   #mask off bit-7 MSB, then shift in space for 16 bits 
        middle_word = payload[1] << 8    #bit shift word by 8
        end_word = payload[2]  #lose the last 5 bits
        #print('Bit check - Treated Words: %s %s %s' %(bin(beg_word), bin(middle_word), bin(end_word)))
        combined_word = (beg_word | middle_word | end_word) >> 5   #combine and shift by 5 to get final 18-bit word
        print('Bit check - Combined Word: %s' %bin(combined_word))
        return combined_word
        
    def position(self, samples = 1, mode = 3):
        sample_count = samples
        sampled_databits = 0
        while samples != 0:
            combined_word = self.ssi_extraction(mode = mode)
            sampled_databits += (combined_word >> 6)
            sample_count -= 1
        #print('%s position' %abs_position)
        sampled_databits = sampled_databits / samples
        return sampled_databits

    def field(self, mode = 0):
        combined_word = self.ssi_extraction(mode = mode)
        databits = combined_word >> 6
        #print('%s field strength' %field_strength)
        return databits

    def check_zrange(self, combined_word):
        zrange_lookup = {0b000 : {'state': 'Green - static', 'range': '10..40 mT', 'distance': 'static'},
                        0b010 : {'state': 'Green - increasing field', 'range': '10..40 mT', 'distance': 'increase'},
                        0b001 : {'state': 'Green - decreasing field', 'range': '10..40 mT', 'distance': 'decrease'},
                        0b011 : {'state': 'Yellow - Under / Over mT - reduced accuracy', 'range': '3.4..54.5 mT', 'distance': 'n/a'},
                        0b111 : {'state': 'Red - ERROR - signficant under / over mT', 'range': 'field < 3.4 mT | > 54.5 mT', 'distance': 'n/a'},
                        }
        magnetic_bits = (combined_word & 0b1111) >> 1   #mask off last 4 bits and shift off parity bit
        z_report = ('Z-axis range indicator - ')
        for bits in zrange_lookup:
            if magnetic_bits == bits:
                for items in zrange_lookup[bits]:
                    z_report += ('%s : %s, ' %(items, zrange_lookup[bits][items]))
                z_report = z_report[:-2]    #remove extra , 
            return z_report #EXIT OUT OF LOOP

    def check_errors(self, combined_word):
        '''Interprets bits[5:3], these are error flags and returns interpretation to user.'''
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

    def check_parity(self, combined_word):
        '''Brute force method of checking data validity. Total # of bits in 18-bit stream should be even.'''
        parity_counter = 0
        while combined_word != 0:
            check_for_1 = 0b1 & combined_word   #mask
            parity_counter += check_for_1
            combined_word = combined_word >> 1  #bit-shift off last bit, run loop again.
        if parity_counter % 2 == 0: #check if its even
            return True #return true if even, data is VALID
        else:
            return False    #return false if odd, data is INVALID

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
        #self.report_zrange(combined_word)   #prints z-range info
        print(self.check_zrange(combined_word))
        print(self.check_errors(combined_word)) #prints error bit checks
        print('Even Parity Check: %s' %self.check_parity(combined_word))

    def fieldstrength_calculator(self, combined_word):
        msb_eight = combined_word >> 10
        if msb_eight == 0x3F:
            return 'Field Strength Range: 10-40 mT, optimal.'
        elif (0x20 < msb_eight < 0x3F) or (0x3F < msb_eight < 0x5F):
            return 'Field Strength Range: 3.4-10 mT, too weak but usable with inaccuracies.'
        elif (0x3F < msb_eight < 0x5F):
            return 'Field Strength Range: 40-54.5 mT, too strong but usable with inaccuracies.'
        else:
            return 'Field Strength Range: ERROR! Outside of 3.4 - 54.5 mT, data inaccurate.'