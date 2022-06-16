"""
Simple example of library usage in context.
This will not transmit anything, but rather
display settings after changing contexts ( & thus configurations)

    .. warning:: This script is not compatible with the rf24_lite module
"""
import board
from digitalio import DigitalInOut
from circuitpython_nrf24l01.rf24 import RF24
from circuitpython_nrf24l01.fake_ble import FakeBLE

# invalid default values for scoping
SPI_BUS, CSN_PIN, CE_PIN = (None, None, None)

try:  # on Linux
    import spidev

    SPI_BUS = spidev.SpiDev()  # for a faster interface on linux
    CSN_PIN = 0  # use CE0 on default bus (even faster than using any pin)
    CE_PIN = DigitalInOut(board.D22)  # using pin gpio22 (BCM numbering)

except ImportError:  # on CircuitPython only
    # using board.SPI() automatically selects the MCU's
    # available SPI pins, board.SCK, board.MOSI, board.MISO
    SPI_BUS = board.SPI()  # init spi bus object

    # change these (digital output) pins accordingly
    CE_PIN = DigitalInOut(board.D4)
    CSN_PIN = DigitalInOut(board.D5)


# initialize the nRF24L01 objects on the spi bus object
# the first object will have all the features enabled
nrf = RF24(SPI_BUS, CSN_PIN, CE_PIN)
# On Linux, csn value is a bit coded
#                 0 = bus 0, CE0  # SPI bus 0 is enabled by default
#                10 = bus 1, CE0  # enable SPI bus 2 prior to running this
#                21 = bus 2, CE1  # enable SPI bus 1 prior to running this

# enable the option to use custom ACK payloads
nrf.ack = True
# set the static payload length to 8 bytes
nrf.payload_length = 8
# RF power amplifier is set to -18 dbm
nrf.pa_level = -18

# the second object has most features disabled/altered
ble = FakeBLE(SPI_BUS, CSN_PIN, CE_PIN)
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

# NOTE it is not advised to manipulate separate RF24 objects outside of the
# "with" block; you will encounter bugs about configurations when doing so.
# Be sure to use 1 "with" block per RF24 object when instantiating multiple
# RF24 objects in your program.
# NOTE exiting a "with" block will always power down the nRF24L01
# NOTE upon instantiation, this library closes all RX pipes &
# extracts the TX/RX addresses from the nRF24L01 registers
