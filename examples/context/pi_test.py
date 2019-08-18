'''
    Simple example of library usage in context.

    This will not transmit anything, but rather
    display settings after changing contexts ( & thus configurations)
'''

import board, digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
address = b'1Node'

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D7)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# initialize the nRF24L01 objects on the spi bus object
nrf = RF24(spi, csn, ce, ack=True)
# the first object will have all the features enabled
# including the option to use custom ACK payloads

# the second object has all the features disabled
# using a different channel (default is 76)
# disabling dynamic_payloads inherently disables auto_ack
# the IRQ is configured to only go active on data fail
# CRC is set to 1 byte long
# data rate is set to 250Kbps
# payload length is set to 8 bytes
# address length is set to 3 bytes
basicRF = RF24(spi, csn, ce, dynamic_payloads=False, irq_DR=False, irq_DS=False, channel=2, crc=1, data_rate=250, payload_length=8, address_length=3, ard=1000, arc=15)


print("\nsettings configured by the nrf object")
with nrf:
    # some stuff is not saved/restored by using "with" statements
    # open pipe 5 to demonstrate this
    nrf.open_rx_pipe(5, address) # NOTE we do this inside the "with" block
    # only the last character gets written because it is on a pipe_number > 1
    # NOTE if opening pipes outside of the "with" block, you may encounter
    # conflicts in the differences between address_length attributes.
    # the address_length attribute must equal the length of addresses

    # display current setting of the nrf object
    nrf.what_happened(True) # True dumps pipe info

print("\nsettings configured by the basicRF object")
with basicRF as nerf: # the "as nerf" part is optional
    nerf.what_happened(1)

# if you examine the outputs from what_happened() you'll
# see that pipe 5 is still open but the radio settings have changed.
# this is because the "with" statements load the existing settings
# for the RF24 object specified after the word "with".

# the things that remain consistent despite the use of "with"
# statements include: power mode (standby or sleep), state of the
# pipes and their addresses, and primary role (RX/TX mode)

# close all pipes because their state remains even if power is lost
with nrf: # addresses also remain despite power loss
    for i in range(6):
        nrf.close_rx_pipe(i) # resets addresses also
