"""
Simple example of library usage in context.
This will not transmit anything, but rather
display settings after changing contexts ( & thus configurations)
"""
import board
import digitalio as dio
from circuitpython_nrf24l01 import RF24

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# initialize the nRF24L01 objects on the spi bus object
nrf = RF24(spi, csn, ce, ack=True)
# the first object will have all the features enabled
# including the option to use custom ACK payloads

# the second object has most features disabled/altered
# disabled dynamic_payloads, but still using enabled auto_ack
# the IRQ pin is configured to only go active on "data fail"
# using a different channel: 2 (default is 76)
# CRC is set to 1 byte long
# data rate is set to 2 Mbps
# payload length is set to 8 bytes
# NOTE address length is set to 3 bytes
# RF power amplifier is set to -12 dbm
# automatic retry attempts is set to 15 (maximum allowed)
# automatic retry delay (between attempts) is set to 1000 microseconds
basicRF = RF24(spi, csn, ce,
               dynamic_payloads=False, irq_DR=False, irq_DS=False,
               channel=2, crc=1, data_rate=2, payload_length=8,
               address_length=3, pa_level=-12, ard=1000, arc=15)

print("\nsettings configured by the nrf object")
with nrf:
    nrf.open_rx_pipe(5, b'1Node')  # NOTE we do this inside the "with" block
    # only the first character gets written because it is on a pipe_number > 1
    # NOTE if opening pipes outside of the "with" block, you may encounter
    # conflicts in the differences between address_length attributes.
    # the address_length attribute must equal the length of addresses

    # display current settings of the nrf object
    nrf.what_happened(True)  # True dumps pipe info

print("\nsettings configured by the basicRF object")
with basicRF as nerf:  # the "as nerf" part is optional
    nerf.open_rx_pipe(2, b'SOS') # again only uses the first character
    nerf.what_happened(1)

# if you examine the outputs from what_happened() you'll see:
#   pipe 5 is opened using the nrf object, but closed using the basicRF object.
#   pipe 2 is closed using the nrf object, but opened using the basicRF object.
# this is because the "with" statements load the existing settings
# for the RF24 object specified after the word "with".

# the things that remain consistent despite the use of "with"
# statements includes the power mode (standby or sleep), and
# primary role (RX/TX mode)
# NOTE this library uses the adresses' reset values and closes all pipes upon
# instantiation
