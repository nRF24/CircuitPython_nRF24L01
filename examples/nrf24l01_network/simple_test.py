"""Network simple test"""
import time
import struct

USE_SHIM = False
try:
    import board
    import digitalio
except (NotImplementedError, NameError):
    USE_SHIM = True
    print("using shim on x86.")

# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.network.rf24_network import RF24Network, RF24NetworkFrame, RF24NetworkHeader

# change these (digital output) pins accordingly
ce = None if USE_SHIM else digitalio.DigitalInOut(board.D4)
csn = None if USE_SHIM else digitalio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = None if USE_SHIM else board.SPI()  # init spi bus object


# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24Network(spi, csn, ce, 0o0)

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
# nrf.pa_level = -12