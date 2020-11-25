x = bin((spi.readbytes(3)[0] << 4))

#mask first
0b01111111

((spi.readbytes(3)[0] & 0b01111111) << 5) | (spi.readbytes(3)[1
] >> 5)