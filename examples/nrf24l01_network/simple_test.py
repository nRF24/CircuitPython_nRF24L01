"""
A simple example of sending data from 1 nRF24L01 transceiver to another.
This example was written to be used on 2 devices acting as 'nodes'.
"""
import time
import struct

USE_SHIM = False
try:
    import board
    import digitalio
except (NotImplementedError, NameError):
    USE_SHIM = True
    print("logging shim on x86.")

# pylint: disable=wrong-import-position
from circuitpython_nrf24l01.network.rf24_network import (
    RF24Network,
    NETWORK_DEBUG,
    # RF24NetworkFrame,
    RF24NetworkHeader,
)

# change these (digital output) pins accordingly
ce = None if USE_SHIM else digitalio.DigitalInOut(board.D4)
csn = None if USE_SHIM else digitalio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = None if USE_SHIM else board.SPI()  # init spi bus object

# to use different addresses on a pair of radios, we need a variable to
# uniquely identify which address this radio will use
radio_number = int(
    input("Which radio is this? Enter '0' or '1' or octal int. Defaults to '0' ") or "0",
    8,  # octal base
)

# initialize the network node using `radio_number` as `nrf.node_address`
nrf = RF24Network(spi, csn, ce, radio_number)
nrf.channel = 90

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12

# log debug msgs specific to RF24Network.
# use NETWORK_DEBUG_MINIMAL for less verbosity
nrf.logger.setLevel(NETWORK_DEBUG)
# using the python keyword global is bad practice. Instead we'll use a 1 item
# list to store our float number for the payloads sent/received
packets_sent = [0]


def master(count=5):
    """Transmits 2 incrementing long ints every 2 second"""
    nrf.listen = True  # stay in active RX mode when not sleeping/TXing
    failures = 0
    while failures < 6 and count:
        count -= 1
        nrf.update()
        now = time.monotonic()
        last_sent = now + 2
        # If it's time to send a message, send it!
        if now - last_sent >= 2:
            last_sent = now
            ok = nrf.send(
                RF24NetworkHeader(not bool(radio_number % 8)),
                struct.pack("<LL", time.monotonic_ns() / 1000, packets_sent[0]),
            )
            packets_sent[0] += 1
            failures += not ok
            print("Sending %d..." % packets_sent[0], "ok." if ok else "failed.")
    print(failures, "failures detected. Leaving TX role.")


def slave(timeout=6):
    """Listen for any payloads and print the transaction

    :param int timeout: The number of seconds to wait (with no transmission)
        until exiting function.
    """
    nrf.listen = True  # put radio in RX mode

    start_timer = time.monotonic()
    while (time.monotonic() - start_timer) < timeout:
        nrf.update()
        while nrf.available():
            header, payload = nrf.read()
            print("payload length", len(payload))
            millis, number = struct.unpack("<LL", bytes(payload))
            print(
                "Received payload", number,
                "at", millis,
                "from", oct(header.from_node),
                "to", oct(header.to_node)
            )
            start_timer = time.monotonic()  # reset timer
        time.sleep(0.05)  # wait 50 ms


def set_role():
    """Set the role using stdin stream. Timeout arg for slave() can be
    specified using a space delimiter (e.g. 'R 10' calls `slave(10)`)

    :return:
        - True when role is complete & app should continue running.
        - False when app should exit
    """
    user_input = (
        input(
            "*** Enter 'R' for receiver role.\n"
            "*** Enter 'T' for transmitter role.\n"
            "*** Enter 'Q' to quit example.\n"
        )
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("R"):
        if len(user_input) > 1:
            slave(int(user_input[1]))
        else:
            slave()
        return True
    if user_input[0].upper().startswith("T"):
        if len(user_input) > 1:
            master(int(user_input[1]))
        else:
            master()
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = 0
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nrf24l01_network/simple_test")  # print example name

if __name__ == "__main__":

    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = 0
else:
    print(
        "    Run master() on transmitter.\n    Run slave() on receiver."
    )
