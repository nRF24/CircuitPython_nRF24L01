"""
This is an example of how to use the nRF24L01's builtin
Received Power Detection (RPD) to scan for possible interference.
This example does not require a counterpart node.
"""
import time

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

# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn_pin, ce_pin)
# On Linux, csn_pin value is a bit coded
#                 0 = bus 0, CE0  # SPI bus 0 is enabled by default
#                10 = bus 1, CE0  # enable SPI bus 2 prior to running this
#                21 = bus 2, CE1  # enable SPI bus 1 prior to running this

# turn off RX features specific to the nRF24L01 module
nrf.auto_ack = 0
nrf.dynamic_payloads = 0


def scan(timeout=30):
    """Traverse the spectrum of accessible frequencies and print any detection
    of ambient signals.

    :param int timeout: The number of seconds in which scanning is performed.
    """
    # print the vertical header of channel numbers
    print("0" * 100 + "1" * 26)
    for i in range(13):
        print(str(i % 10) * (10 if i < 12 else 6), sep="", end="")
    print("")  # endl
    for i in range(126):
        print(str(i % 10), sep="", end="")
    print("\n" + "~" * 126)

    signals = [0] * 126  # store the signal count for each channel
    curr_channel = 0
    start_timer = time.monotonic()  # start the timer
    while time.monotonic() - start_timer < timeout:
        nrf.channel = curr_channel
        # time.sleep(0.00013)  # let radio modulate to new channel
        nrf.listen = 1  # start a RX session
        time.sleep(0.00013)  # wait 130 microseconds
        signals[curr_channel] += nrf.rpd  # if interference is present
        nrf.listen = 0  # end the RX session
        curr_channel = curr_channel + 1 if curr_channel < 125 else 0

        # ouptut the signal counts per channel
        sig_cnt = signals[curr_channel]
        print(
            hex(min(0x0F, sig_cnt))[2:] if sig_cnt else "-",
            sep="",
            end="" if curr_channel < 125 else "\r",
        )
    # finish printing results and end with a new line
    while curr_channel < len(signals) - 1:
        curr_channel += 1
        sig_cnt = signals[curr_channel]
        print(hex(min(0x0F, sig_cnt))[2:] if sig_cnt else "-", sep="", end="")
    print("")


def set_role():
    """Set the role using stdin stream. Timeout arg for scan() can be
    specified using a space delimiter (e.g. 'S 10' calls `scan(10)`)

    :return:
        - True when role is complete & app should continue running.
        - False when app should exit
    """
    user_input = (
        input("*** Enter 'S' to perform scan.\n" "*** Enter 'Q' to quit example.\n")
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("S"):
        if len(user_input) > 1:
            scan(int(user_input[1]))
        else:
            scan()
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = False
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nRF24L01 scanner test")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = False
else:
    print("    Run scan() to initiate scan for ambient signals.")
