"""
This example of using the nRF24L01 as a 'fake' Buetooth Beacon
"""
import time
import board
import digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24
from circuitpython_nrf24l01.fake_ble import (
    FakeBLE,
    chunk,
    ServiceData,
    BatteryServiceData,
    TemperatureServiceData,
)

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# initialize the nRF24L01 on the spi bus object as a BLE radio using
radio = RF24(spi, csn, ce)
nrf = FakeBLE(radio)

# the name parameter is going to be its braodcasted BLE name
# this can be changed at any time using the attribute
nrf.name = b"foobar"

# if broadcasting to an Android, set the to_iphone attribute to False
# if broadcasting to an iPhone, set the to_iphone attribute to True
nrf.to_iphone = False

# you can optionally set the arbitrary MAC address to be used as the
# BLE device's MAC address. Otherwise this is randomly generated.
nrf.mac = b"\x19\x12\x14\x26\x09\xE0"

# use the eddystone protocol from google to broadcast a URL
url_service = ServiceData(0xFEAA)
url_service.data = bytes([0x10, 0, 0x01]) + b"google.com"

def _prompt(count, iterator):
    if (count - iterator) % 5 == 0 or (count - iterator) < 5:
        if count - iterator - 1:
            print(count - iterator, "advertisments left to go!")
        else:
            print(count - iterator, "advertisment left to go!")


def master(count=50):
    """Sends out the device information twice a second."""
    # using the "with" statement is highly recommended if the nRF24L01 is
    # to be used for more than a BLE configuration
    battery_service = BatteryServiceData()
    # battery data is 1 unsigned byte representing a percentage
    battery_service.data = 85
    with nrf as ble:
        nrf.name = b"nRF24L01"
        nrf.show_pa_level = True
        for i in range(count):  # advertise data this many times
            _prompt(count, i)  # something to show that it isn't frozen
            # broadcast only the device name, MAC address, &
            # battery charge info; 0x16 means service data
            ble.advertise(battery_service.buffer, data_type=0x16)
            # channel hoping is recommended per BLE specs
            ble.hop_channel()
            time.sleep(0.5)  # wait till next broadcast
    # nrf.show_pa_level & nrf.name both are set to false when
    # exiting a with statement block


def send_temp(count=50):
    """Sends out a fake temperature twice a second."""
    temperature_service = TemperatureServiceData()
    temperature_service.data = 42.0
    with nrf as ble:
        ble.name = b"nRF24L01"
        for i in range(count):
            _prompt(count, i)
            # broadcast a device temperature; 0x16 means service data
            ble.advertise(temperature_service.buffer, data_type=0x16)
            # channel hoping is recommended per BLE specs
            ble.hop_channel()
            time.sleep(0.2)


def send_chunk(pl_chunk, count=50):
    """Sends out a chunk of data twice a second."""
    with nrf as ble:
        for i in range(count):
            _prompt(count, i)
            ble.advertise(pl_chunk, 0x16)
            ble.hop_channel()
            time.sleep(0.2)


print(
    """\
    nRF24L01 fake BLE beacon test.\n\
    Run master() to broadcast the device name, pa_level, & battery charge\n\
    Run send_temperature() to broadcast the device name & a temperature\n\
    Run send_chunk() to broadcast custom chunk of info"""
)
