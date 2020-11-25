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
        self.spi.max_speed_hz = 500000  #lets set the SPI bus to 500kHz
        self.spi.mode = 2    #lets set to mode 2 for default reading, note, when we change to magnetic strength sensing, we need to swap to spi mode 1.

    def ssi_extraction(self, mode):
        '''SSI comms from the device loses the 1st bit, so its technically 7, 8, 8 relevant bits coming in'''
        self.spi.mode = mode    #Use 2 for position data, use 1 for field strength data
        payload = self.spi.readbytes(3)
        beg_word = (payload[0] & 0b01111111) << 16   #mask off bit-7 MSB, then shift in space for 16 bits
        middle_word = payload[1] << 8    #bit shift word by 8
        end_word = payload[2] >> 5  #lose the last 5 bits
        combined_word = (beg_word | middle_word | end_word) >> 5    #combine and shift by 5 to get final 18-bit word
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
        zrange_lookup = {0b000 : {'state': 'green - static', 'range': '10..40 mT', 'distance': 'static'},
                        0b010 : {'state': 'green - dynamic', 'range': '10..40 mT', 'distance': 'increase'},
                        0b100 : {'state': 'green - dynamic', 'range': '10..40 mT', 'distance': 'decrease'},
                        0b110 : {'state': 'yellow - reduced accuracy', 'range': '3.4..54.5 mT', 'distance': 'n/a'},
                        0b111 : {'state': 'red - inaccurate', 'range': 'field < 3.4 mT | > 54.5 mT', 'distance': 'n/a'},
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
        if ocf == 1:
            return 'OCF Error'
        if cof == 1:
            return 'COF Error'
        if linearity == 1: 
            return 'Linearity Error'
    
    def report(self, word_type = 'position'):
        if word_type == 'position':
            combined_word = self.ssi_extraction(mode = 2)
            abs_position = combined_word >> 6
            print('%s absolute position' %abs_position)
        elif word_type == 'magnetic':
            field_strength = combined_word >> 6
            combined_word = self.ssi_extraction(mode = 1)
            print('%s mT field strength' %field_strength)
        else:
            print('Invalid word type')
        self.report_zrange(combined_word)   #prints z-range
        print(self.check_errors(combined_word))
        print('%s binary word' %bin(combined_word))
