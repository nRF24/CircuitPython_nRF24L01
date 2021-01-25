"""
Simple example of library usage in context.
This will not transmit anything, but rather
display settings after changing contexts ( & thus configurations)

    .. warning:: This script is not compatible with the rf24_lite module
"""
import board
import digitalio
from circuitpython_nrf24l01.rf24 import RF24
from circuitpython_nrf24l01.fake_ble import FakeBLE

# change these (digital output) pins accordingly
ce = digitalio.DigitalInOut(board.D4)
csn = digitalio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# initialize the nRF24L01 objects on the spi bus object
# the first object will have all the features enabled
nrf = RF24(spi, csn, ce)
# enable the option to use custom ACK payloads
nrf.ack = True
# set the static payload length to 8 bytes
nrf.payload_length = 8
# RF power amplifier is set to -18 dbm
nrf.pa_level = -18

# the second object has most features disabled/altered
ble = FakeBLE(spi, csn, ce)
# the IRQ pin is configured to only go active on "data fail"
# NOTE BLE operations prevent the IRQ pin going active on "data fail" events
ble.interrupt_config(data_recv=False, data_sent=False)
# using a channel 2
ble.channel = 2
# RF power amplifier is set to -12 dbm
ble.pa_level = -12

print("\nsettings configured by the nrf object")
with nrf:
    # only the first character gets written because it is on a pipe_number > 1
    nrf.open_rx_pipe(5, b"1Node")  # NOTE we do this inside the "with" block

    # display current settings of the nrf object
    nrf.print_details(True)  # True dumps pipe info

print("\nsettings configured by the ble object")
with ble as nerf:  # the "as nerf" part is optional
    nerf.print_details(1)

# if you examine the outputs from print_details() you'll see:
#   pipe 5 is opened using the nrf object, but closed using the ble object.
#   pipe 0 is closed using the nrf object, but opened using the ble object.
#   also notice the different addresses bound to the RX pipes
# this is because the "with" statements load the existing settings
# for the RF24 object specified after the word "with".

# NOTE it is not advised to manipulate seperate RF24 objects outside of the
# "with" block; you will encounter bugs about configurations when doing so.
# Be sure to use 1 "with" block per RF24 object when instantiating multiple
# RF24 objects in your program.
# NOTE exiting a "with" block will always power down the nRF24L01
# NOTE upon instantiation, this library closes all RX pipes &
# extracts the TX/RX addresses from the nRF24L01 registers
