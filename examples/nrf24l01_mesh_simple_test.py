"""
A simple example of sending data from 1 nRF24L01 transceiver to another.
This example was written to be used on 2 devices acting as 'nodes'.
"""
import time
import struct
from circuitpython_nrf24l01.network.constants import NETWORK_DEBUG, MAX_FRAG_SIZE
from circuitpython_nrf24l01.network.rf24_mesh import RF24Mesh

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

# to use different addresses on a set of radios, we need a variable to
# uniquely identify which address this radio will use
this_node = int(
    input("Which radio is this? Enter a unique int. Defaults to '0' ") or "0"
)
# allow specifying the examples' master*() behavior's target for transmiting messages
other_node = int(
    input(
        "To which radio should we transmit to? Enter a unique int. Defaults to '1' "
    ) or "1",
)

# initialize the mesh node object
nrf = RF24Mesh(spi, csn_pin, ce_pin)
nrf.channel = 97

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12

nrf.node_id = this_node
if this_node:
    print("Connecting to network...", end=" ")
    # give this node a unique ID number and connect to network
    nrf.renew_address()
    print("assigned address:", oct(nrf.node_address))
else:
    nrf.node_address = nrf.get_node_id()
    print("Acting as mesh network master node.")

if nrf.logger is not None:
    # log debug msgs specific to RF24Network.
    # use NETWORK_DEBUG_MINIMAL for less verbosity
    nrf.logger.setLevel(NETWORK_DEBUG)
    nrf.queue.logger.setLevel(NETWORK_DEBUG)

# using the python keyword global is bad practice. Instead we'll use a 1 item
# list to store our number of the payloads sent
packets_sent = [0]


def master(count=5, frag=False, interval=2):
    """Transmits 2 incrementing long ints every 2 second

    :param int count: the max number of messages to transmit.
    :param bool frag: only use fragmented messages.
    :param int interval: time spent between transmitting messages.
    """
    failures = 0
    start_timer = time.monotonic()
    while failures < 6 and count:
        nrf.update()
        now = time.monotonic()
        if now >= start_timer + interval:  # If it's time to send a message, send it!
            start_timer = now
            count -= 1
            packets_sent[0] += 1
            length = 8
            message = struct.pack(
                "LL",
                int(time.monotonic_ns() / 1000000),
                packets_sent[0]
            )
            if frag:
                length = (packets_sent[0] + MAX_FRAG_SIZE) % nrf.max_message_length
                message = bytes(range(length))
            ok = nrf.send(message, "M", other_node)
            failures += not ok
            print(
                "Sending {} (len {})...".format(packets_sent[0], length),
                "ok." if ok else "failed."
            )
    print(failures, "failures detected. Leaving TX role.")


def slave(timeout=6, frag=False):
    """Listen for any payloads and print the transaction

    :param int timeout: The number of seconds to wait (with no transmission)
        until exiting function.
    :param bool frag: only use fragmented messages.
    """
    start_timer = time.monotonic()
    while (time.monotonic() - start_timer) < timeout:
        nrf.update()
        while nrf.available():
            start_timer = time.monotonic()  # reset timer
            payload = nrf.read()
            print("Received payload", end=" ")
            if not frag:
                print(struct.unpack("<LL", bytes(payload.message)), end=" ")
            print(
                "from", oct(payload.header.from_node),
                "to", oct(payload.header.to_node),
                "length", len(payload.message),
            )


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
            "*** Enter 'T <payload count> 1' or 'R <timeout seconds> 1' "
            "to demonstrate fragmented messages.\n"
            "*** Enter 'Q' to quit example.\n"
        )
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("R"):
        if len(user_input) > 1:
            if len(user_input) > 2:
                slave(int(user_input[1]), int(user_input[2]))
            else:
                slave(int(user_input[1]))
        else:
            slave()
        return True
    if user_input[0].upper().startswith("T"):
        if len(user_input) > 1:
            if len(user_input) > 2:
                master(int(user_input[1]), int(user_input[2]))
            else:
                master(int(user_input[1]))
        else:
            master()
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = 0
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nrf24l01_mesh_simple_test")  # print example name

if __name__ == "__main__":

    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = 0
else:
    print("    Run master() on transmitter.\n    Run slave() on receiver.")
    print("    Pass keyword arg `frag=True` to demonstrate message fragmentation.")
