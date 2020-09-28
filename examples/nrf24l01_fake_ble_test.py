"""
This example of using the nRF24L01 as a 'fake' Buetooth Beacon
"""
import time
import struct
import board
import digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24
from circuitpython_nrf24l01.fake_ble import FakeBLE, chunk, SERVICE_TYPES, ServiceData

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

nrf.to_iphone = False

# you can optionally set the arbitrary MAC address to be used as the
# BLE device's MAC address
nrf.mac = b'\x19\x12\x14\x26\x09\xE0'

def _prompt(count, iterator):
    if (count - iterator) % 5 == 0 or (count - iterator) < 5:
        if count - iterator - 1:
            print(count - iterator, "advertisments left to go!")
        else:
            print(count - iterator, "advertisment left to go!")

def send_name(count=50):
    """Sends out the device name twice a second."""
    # using the "with" statement is highly recommended if the nRF24L01 is
    # to be used for more than a BLE configuration
    with nrf as ble:
        nrf.name = b"nRF24L01"
        nrf.show_pa_level = True
        for i in range(count):  # advertise data this many times
            _prompt(count, i)
            # broadcast only the device name and MAC address
            ble.advertise()
            # channel hoping is automatically managed by send() per BLE specs
            time.sleep(0.5)  # wait till next broadcast
    # nrf.show_pa_level returns to false when exiting a with statement block


def send_temp(count=50):
    """Sends out a fake temperature twice a second."""
    temperature_service = ServiceData(SERVICE_TYPES["Health Thermometer"])
    temperature_service.data = struct.pack(">f", 42.0)
    nrf.name = b"nRf24L01"
    for i in range(count):
        _prompt(count, i)
        payload = temperature_service.buffer
        # broadcast a device temperature; 0x16 means service data
        nrf.advertise(payload, data_type=0x16)
        time.sleep(0.2)

def send_battery_time(count=50):
    """Sends out a device's battery capacity twice a second."""
    nrf.name = None
    time_service = ServiceData(SERVICE_TYPES["Current Time"])
    #  the time data is seconds since Jan 1, 1970
    time_service.data = struct.pack(">i", time.time())
    battery_service = ServiceData(SERVICE_TYPES["Battery"])
    # battery data is 1 unsigned byte representing a percentage
    battery_service.data = struct.pack(">B", 80)
    payload = [
        chunk(time_service.buffer),
        chunk(battery_service.buffer)
    ]
    for i in range(count):
        _prompt(count, i)
        nrf.advertise(payload)
        time.sleep(0.2)


print("""\
    nRF24L01 fake BLE beacon test.\n\
    Run send_name_pa_level() to broadcast the device name and pa_level\n\
    Run send_temperature() to broadcast a temperature\n\
    Run send_battery_time() to broadcast battery and time info""")
