"""
This example of using the nRF24L01 as a 'fake' Buetooth Beacon
"""
import time
import struct
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
radio = RF24(spi, csn, ce)
nrf = FakeBLE(radio, name=b'nRF24')

# the name parameter is going to be its braodcasted BLE name
# this can be changed at any time using the attribute
nrf.name = b'RFtest'

def master(count=15):
    """Sends out an advertisement once a second for a default count of 15"""
    with nrf as ble:
        for i in range(count):  # advertise data this many times
            if (count - i) % 5 == 0 or (count - i) < 5:
                print(
                    count - i, 'advertisment{}left to go!'.format('s ' if count - i - 1 else ' '))
            # pack into bytearray using struct.pack()
            ble.advertise(struct.pack('i', count))  # 'i' = 4 byte integer
            # channel is automatically managed by send() per BLE specs
            time.sleep(1)  # wait till next broadcast
