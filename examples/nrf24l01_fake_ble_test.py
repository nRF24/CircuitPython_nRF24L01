"""
This example of using the nRF24L01 as a 'fake' Buetooth Beacon
"""
import time
# import struct
import board
import digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24
from circuitpython_nrf24l01.fake_ble import FakeBLE

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# initialize the nRF24L01 on the spi bus object as a BLE radio using
nrf = FakeBLE(RF24(spi, csn, ce))

# the name parameter is going to be its broadcasted BLE device name
# this can be changed at any time using the attribute
nrf.name = b'RFtest'

# you can optionally set the arbitrary MAC address to be used as the
# BLE device's MAC address. This is randomized upon instantiation.
# nrf.mac = b'\x19\x12\x14\x26\x09\xE0'

def master(count=100):
    """Sends out an advertisement once a second for a default count of 100"""
    # using the "with" statement is highly recommended if the nRF24L01 is
    # to be used for more than a BLE configuration
    with nrf as ble:
        for i in range(count):  # advertise data this many times
            if (count - i) % 5 == 0 or (count - i) < 5:
                print(
                    count - i, 'advertisment{}left to go!'.format('s ' if count - i - 1 else ' '))
            # broadcast only the device name and MAC address
            ble.advertise()
            # channel is automatically managed by send() per BLE specs
            time.sleep(0.2)  # wait till next broadcast


print("""\
    nRF24L01 fake BLE beacon test.\n\
    Run master() to broadcast""")
    # Run slave() to listen\n\
