"""
This example uses the nRF24L01 as a 'fake' BLE Beacon

    .. warning:: ATSAMD21 M0-based boards have memory allocation
        error when loading 'fake_ble.mpy'
"""
import time
from circuitpython_nrf24l01.fake_ble import (
    chunk,
    FakeBLE,
    UrlServiceData,
    BatteryServiceData,
    TemperatureServiceData,
)
from circuitpython_nrf24l01.rf24 import address_repr

# import wrappers to imitate circuitPython's DigitalInOut
from circuitpython_nrf24l01.wrapper import RPiDIO, DigitalInOut

# RPiDIO is wrapper for RPi.GPIO on Linux
# DigitalInOut is a wrapper for machine.Pin() on MicroPython
#   or simply digitalio.DigitalInOut on CircuitPython and Linux

# default values that allow using no radio module (for testing only)
spi = None
csn_pin = None
ce_pin = None

try:  # on CircuitPython & Linux
    import board
    # change these (digital output) pins accordingly
    ce_pin = DigitalInOut(board.D4)
    csn_pin = DigitalInOut(board.D5)

    try:  # on Linux
        import spidev

        spi = spidev.SpiDev()  # for a faster interface on linux
        csn_pin = 0  # use CE0 on default bus (even faster than using any pin)
        if RPiDIO is not None:  # RPi.GPIO lib is present
            # RPi.GPIO is faster than CircuitPython on Linux
            ce_pin = RPiDIO(22)  # using pin gpio22 (BCM numbering)

    except ImportError:  # on CircuitPython only
        # using board.SPI() automatically selects the MCU's
        # available SPI pins, board.SCK, board.MOSI, board.MISO
        spi = board.SPI()  # init spi bus object

except ImportError:  # on MicroPython
    from machine import SPI

    # the argument passed here changes according to the board used
    spi = SPI(1)

    # instantiate the integers representing micropython pins as
    # DigitalInOut compatible objects
    csn_pin = DigitalInOut(5)
    ce_pin = DigitalInOut(4)

# initialize the nRF24L01 on the spi bus object as a BLE compliant radio
nrf = FakeBLE(spi, csn_pin, ce_pin)
# On Linux, csn_pin value is a bit coded

# the name parameter is going to be its broadcasted BLE name
# this can be changed at any time using the `name` attribute
# nrf.name = b"foobar"

# you can optionally set the arbitrary MAC address to be used as the
# BLE device's MAC address. Otherwise this is randomly generated upon
# instantiation of the FakeBLE object.
# nrf.mac = b"\x19\x12\x14\x26\x09\xE0"

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceiver in close proximity to the
# BLE scanning application
nrf.pa_level = -12


def _prompt(remaining):
    if remaining % 5 == 0 or remaining < 5:
        if remaining - 1:
            print(remaining, "advertisments left to go!")
        else:
            print(remaining, "advertisment left to go!")


# create an object for manipulating the battery level data
battery_service = BatteryServiceData()
# battery level data is 1 unsigned byte representing a percentage
battery_service.data = 85


def master(count=50):
    """Sends out the device information."""
    # using the "with" statement is highly recommended if the nRF24L01 is
    # to be used for more than a BLE configuration
    with nrf as ble:
        ble.name = b"nRF24L01"
        # include the radio's pa_level attribute in the payload
        ble.show_pa_level = True
        print(
            "available bytes in next payload:",
            ble.len_available(chunk(battery_service.buffer)),
        )  # using chunk() gives an accurate estimate of available bytes
        for i in range(count):  # advertise data this many times
            if ble.len_available(chunk(battery_service.buffer)) >= 0:
                _prompt(count - i)  # something to show that it isn't frozen
                # broadcast the device name, MAC address, &
                # battery charge info; 0x16 means service data
                ble.advertise(battery_service.buffer, data_type=0x16)
                # channel hoping is recommended per BLE specs
                ble.hop_channel()
                time.sleep(0.5)  # wait till next broadcast
    # nrf.show_pa_level & nrf.name both are set to false when
    # exiting a with statement block


# create an object for manipulating temperature measurements
temperature_service = TemperatureServiceData()
# temperature's float data has up to 2 decimal places of percision
temperature_service.data = 42.0


def send_temp(count=50):
    """Sends out a fake temperature."""
    with nrf as ble:
        ble.name = b"nRF24L01"
        print(
            "available bytes in next payload:",
            ble.len_available(chunk(temperature_service.buffer)),
        )
        for i in range(count):
            if ble.len_available(chunk(temperature_service.buffer)) >= 0:
                _prompt(count - i)
                # broadcast a temperature measurement; 0x16 means service data
                ble.advertise(temperature_service.buffer, data_type=0x16)
                ble.hop_channel()
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
    """Sends out a URL."""
    with nrf as ble:
        print(
            "available bytes in next payload:",
            ble.len_available(chunk(url_service.buffer)),
        )
        # NOTE we did NOT set a device name in this with block
        for i in range(count):
            # URLs easily exceed the nRF24L01's max payload length
            if ble.len_available(chunk(url_service.buffer)) >= 0:
                _prompt(count - i)
                ble.advertise(url_service.buffer, 0x16)
                ble.hop_channel()
                time.sleep(0.2)


def slave(timeout=6):
    """read and decipher BLE payloads for `timeout` seconds."""
    nrf.listen = True
    end_timer = time.monotonic() + timeout
    while time.monotonic() <= end_timer:
        if nrf.available():
            result = nrf.read()
            print(
                "recevied payload from MAC address {}".format(
                    address_repr(result.mac, delimit=":")
                )
            )
            if result.name is not None:
                print("\tdevice name:", result.name)
            if result.pa_level is not None:
                print("\tdevice transmitting PA Level:", result.pa_level)
            for service_data in result.data:
                if isinstance(service_data, TemperatureServiceData):
                    print("\tTemperature:", service_data.data)
                if isinstance(service_data, BatteryServiceData):
                    print("\tBattery capacity remaining:", service_data.data)
                if isinstance(service_data, UrlServiceData):
                    print("\tURL advertised:", service_data.data)
                if isinstance(service_data, (bytearray, bytes)):
                    print("\traw buffer (unknowmn format):", service_data)


# pylint: disable=too-many-branches
def set_role():
    """Set the role using stdin stream. Count arg for all functions can be
    specified using a space delimiter (e.g. 'T 10' calls `send_temp(10)`)

    :return:
        - True when role is complete & app should continue running.
        - False when app should exit
    """
    user_input = (
        input(
            "*** Enter 'M' to broadcast the device name, pa_level, & battery"
            " charge.\n"
            "*** Enter 'T' to broadcast the device name & a temperature\n"
            "*** Enter 'U' to broadcast a custom URL link\n"
            "*** Enter 'R' to receive BLE payloads\n"
            "*** Enter 'Q' to quit example.\n"
        )
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("M"):
        if len(user_input) > 1:
            master(int(user_input[1]))
        else:
            master()
        return True
    if user_input[0].upper().startswith("T"):
        if len(user_input) > 1:
            send_temp(int(user_input[1]))
        else:
            send_temp()
        return True
    if user_input[0].upper().startswith("U"):
        if len(user_input) > 1:
            send_url(int(user_input[1]))
        else:
            send_url()
        return True
    if user_input[0].upper().startswith("R"):
        if len(user_input) > 1:
            slave(int(user_input[1]))
        else:
            slave()
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = False
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nRF24L01 fake BLE beacon test")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = False
else:
    print(
        "    Run master() to broadcast the device name, pa_level, & battery "
        "charge\n    Run send_temp() to broadcast the device name & a "
        "temperature\n    Run send_url() to broadcast a custom URL link\n"
        "    Run slave() to receive BLE payloads."
    )
