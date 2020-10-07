"""
This example uses the nRF24L01 as a 'fake' BLE Beacon

    .. warning:: ATSAMD21 M0-based boards have memory allocation
        error when loading 'fake_ble.mpy'
"""
import time
import board
import digitalio as dio
from circuitpython_nrf24l01.fake_ble import (
    chunk,
    FakeBLE,
    UrlServiceData,
    BatteryServiceData,
    TemperatureServiceData,
)

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# initialize the nRF24L01 on the spi bus object as a BLE compliant radio
nrf = FakeBLE(spi, csn, ce)

# the name parameter is going to be its broadcasted BLE name
# this can be changed at any time using the `name` attribute
# nrf.name = b"foobar"

# if broadcasting to an Android, set the to_iphone attribute to False
# if broadcasting to an iPhone, set the to_iphone attribute to True
nrf.to_iphone = True  # default value is False

# you can optionally set the arbitrary MAC address to be used as the
# BLE device's MAC address. Otherwise this is randomly generated upon
# instantiation of the FakeBLE object.
# nrf.mac = b"\x19\x12\x14\x26\x09\xE0"

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceiver in close proximity to the
# BLE scanning application
nrf.pa_level = -12


def _prompt(count, iterator):
    if (count - iterator) % 5 == 0 or (count - iterator) < 5:
        if count - iterator - 1:
            print(count - iterator, "advertisments left to go!")
        else:
            print(count - iterator, "advertisment left to go!")


# create an object for manipulating the battery level data
battery_service = BatteryServiceData()
# battery level data is 1 unsigned byte representing a percentage
battery_service.data = 85


def master(count=50):
    """Sends out the device information twice a second."""
    # using the "with" statement is highly recommended if the nRF24L01 is
    # to be used for more than a BLE configuration
    with nrf as ble:
        ble.name = b"nRF24L01"
        # include the radio's pa_level attribute in the payload
        ble.show_pa_level = True
        print(
            "available bytes in next payload:",
            ble.available(chunk(battery_service.buffer))
        )  # using chunk() gives an accurate estimate of available bytes
        for i in range(count):  # advertise data this many times
            if ble.available(chunk(battery_service.buffer)) >= 0:
                _prompt(count, i)  # something to show that it isn't frozen
                # broadcast the device name, MAC address, &
                # battery charge info; 0x16 means service data
                ble.advertise(battery_service.buffer, data_type=0x16)
                # channel hoping is recommended per BLE specs
                ble.hop_channel()
                # alternate advertisements to target all devices
                ble.to_iphone = not ble.to_iphone
                time.sleep(0.5)  # wait till next broadcast
    # nrf.show_pa_level & nrf.name both are set to false when
    # exiting a with statement block


# create an object for manipulating temperature measurements
temperature_service = TemperatureServiceData()
# temperature's float data has up to 2 decimal places of percision
temperature_service.data = 42.0


def send_temp(count=50):
    """Sends out a fake temperature twice a second."""
    with nrf as ble:
        ble.name = b"nRF24L01"
        print(
            "available bytes in next payload:",
            ble.available(chunk(temperature_service.buffer))
        )
        for i in range(count):
            if ble.available(chunk(temperature_service.buffer)) >= 0:
                _prompt(count, i)
                # broadcast a temperature measurement; 0x16 means service data
                ble.advertise(temperature_service.buffer, data_type=0x16)
                # channel hoping is recommended per BLE specs
                ble.hop_channel()
                ble.to_iphone = not ble.to_iphone
                time.sleep(0.2)


# use the Eddystone protocol from Google to broadcast a URL as
# service data. We'll need an object to manipulate that also
url_service = UrlServiceData()
# the data attribute converts a URL string into a simplified
# bytes object using byte codes defined by the Eddystone protocol.
url_service.data = "http://www.google.com"
# Eddystone protocol requires an estimated TX PA level at 1 meter
# lower this estimate since we lowered the actual `ble.pa_level`
url_service.pa_level_at_1_meter = -45  # defaults to -25 dBm

def send_url(count=50):
    """Sends out a URL twice a second."""
    with nrf as ble:
        print(
            "available bytes in next payload:",
            ble.available(chunk(url_service.buffer))
        )
        # NOTE we did NOT set a device name in this with block
        for i in range(count):
            # URLs easily exceed the nRF24L01's max payload length
            if ble.available(chunk(url_service.buffer)) >= 0:
                _prompt(count, i)
                ble.advertise(url_service.buffer, 0x16)
                ble.hop_channel()
                ble.to_iphone = not ble.to_iphone
                time.sleep(0.2)

print(
    """\
    nRF24L01 fake BLE beacon test.\n\
    Run master() to broadcast the device name, pa_level, & battery charge\n\
    Run send_temp() to broadcast the device name & a temperature\n\
    Run send_url() to broadcast a custom URL link"""
)
