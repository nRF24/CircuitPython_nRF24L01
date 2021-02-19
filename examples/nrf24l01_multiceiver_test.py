"""
Simple example of using 1 nRF24L01 to receive data from up to 6 other
transceivers. This technique is called "multiceiver" in the datasheet.
"""
import time
import struct

# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# import wrappers to imitate circuitPython's DigitalInOut
from circuitpython_nrf24l01.wrapper import RPiDIO, DigitalInOut
# RPiDIO is wrapper for RPi.GPIO on Linux
# DigitalInOut is a wrapper for machine.Pin() on MicroPython
#   or simply digitalio.DigitalInOut on CircuitPython and Linux

# default values that allow using no radio module (for testing only)
spi = None
csn = None
ce_pin = None

try:  # on CircuitPython & Linux
    import board

    # change these (digital output) pins accordingly
    ce_pin = DigitalInOut(board.D4)
    csn = DigitalInOut(board.D5)

    try:  # on Linux
        import spidev

        spi = spidev.SpiDev()  # for a faster interface on linux
        csn = 0  # use CE0 on default bus (even faster than using any pin)
        if RPiDIO is not None:  # RPi.GPIO lib is present
            # RPi.GPIO is faster than CircuitPython on Linux & uses IRQ callbacks
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
    csn = DigitalInOut(5)
    ce_pin = DigitalInOut(4)

# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce_pin)
# On Linux, csn value is a bit coded
#                 0 = bus 0, CE0  # SPI bus 0 is enabled by default
#                10 = bus 1, CE0  # enable SPI bus 2 prior to running this
#                21 = bus 2, CE1  # enable SPI bus 1 prior to running this

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12

# setup the addresses for all transmitting nRF24L01 nodes
addresses = [
    b"\x78" * 5,
    b"\xF1\xB6\xB5\xB4\xB3",
    b"\xCD\xB6\xB5\xB4\xB3",
    b"\xA3\xB6\xB5\xB4\xB3",
    b"\x0F\xB6\xB5\xB4\xB3",
    b"\x05\xB6\xB5\xB4\xB3",
]

# uncomment the following 3 lines for compatibility with TMRh20 library
# nrf.allow_ask_no_ack = False
# nrf.dynamic_payloads = False
# nrf.payload_length = 8


def base(timeout=10):
    """Use the nRF24L01 as a base station for lisening to all nodes"""
    # write the addresses to all pipes.
    for pipe_n, addr in enumerate(addresses):
        nrf.open_rx_pipe(pipe_n, addr)
    nrf.listen = True  # put base station into RX mode
    start_timer = time.monotonic()  # start timer
    while time.monotonic() - start_timer < timeout:
        while not nrf.fifo(False, True):  # keep RX FIFO empty for reception
            # show the pipe number that received the payload
            # NOTE read() clears the pipe number and payload length data
            print("Received", nrf.any(), "on pipe", nrf.pipe, end=" ")
            node_id, payload_id = struct.unpack("<ii", nrf.read())
            print("from node {}. PayloadID: {}".format(node_id, payload_id))
            start_timer = time.monotonic()  # reset timer with every payload
    nrf.listen = False


def node(node_number=0, count=6):
    """start transmitting to the base station.

    :param int node_number: the node's identifying index (from the
        the `addresses` list)
    :param int count: the number of times that the node will transmit
        to the base station.
    """
    nrf.listen = False
    # set the TX address to the address of the base station.
    nrf.open_tx_pipe(addresses[node_number])
    counter = 0
    # use the node_number to identify where the payload came from
    while counter < count:
        counter += 1
        # payloads will include the node_number and a payload ID character
        payload = struct.pack("<ii", node_number, counter)
        # show something to see it isn't frozen
        start_timer = time.monotonic_ns()
        report = nrf.send(payload)
        end_timer = time.monotonic_ns()
        # show something to see it isn't frozen
        if report:
            print(
                "Transmission of payloadID {} as node {} successfull! "
                "Transmission time: {} us".format(
                    counter, node_number, (end_timer - start_timer) / 1000
                )
            )
        else:
            print("Transmission failed or timed out")
        time.sleep(0.5)  # slow down the test for readability


def set_role():
    """Set the role using stdin stream. Node number arg for node() can be
    specified using a space delimiter (e.g. 'T 0' calls `node(0)`)

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
            base(int(user_input[1]))
        else:
            base()
        return True
    if user_input[0].upper().startswith("T"):
        if len(user_input) > 2:
            node(int(user_input[1]), int(user_input[2]))
        elif len(user_input) > 1:
            node(int(user_input[1]))
        else:
            node()
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = False
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nRF24L01 Multiceiver test")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = False
else:
    print(
        "    Run base() on the receiver\n    "
        "Run node(node_number) on a transmitter\n    "
        "node()'s parameter, `node_number`, must be in range [0, 5]"""
    )
