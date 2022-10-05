"""
This is an example of how to use the nRF24L01's builtin
Received Power Detection (RPD) to scan for possible interference.
This example does not require a counterpart node.
"""
import time
import board
from digitalio import DigitalInOut

# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24, address_repr

# invalid default values for scoping
SPI_BUS, CSN_PIN, CE_PIN = (None, None, None)

try:  # on Linux
    import spidev

    SPI_BUS = spidev.SpiDev()  # for a faster interface on linux
    CSN_PIN = 0  # use CE0 on default bus (even faster than using any pin)
    CE_PIN = DigitalInOut(board.D22)  # using pin gpio22 (BCM numbering)

except ImportError:  # on CircuitPython only
    # using board.SPI() automatically selects the MCU's
    # available SPI pins, board.SCK, board.MOSI, board.MISO
    SPI_BUS = board.SPI()  # init spi bus object

    # change these (digital output) pins accordingly
    CE_PIN = DigitalInOut(board.D4)
    CSN_PIN = DigitalInOut(board.D5)


# initialize the nRF24L01 on the spi bus object
nrf = RF24(SPI_BUS, CSN_PIN, CE_PIN)
# On Linux, csn value is a bit coded
#                 0 = bus 0, CE0  # SPI bus 0 is enabled by default
#                10 = bus 1, CE0  # enable SPI bus 2 prior to running this
#                21 = bus 2, CE1  # enable SPI bus 1 prior to running this

# turn off RX features specific to the nRF24L01 module
nrf.auto_ack = False
nrf.dynamic_payloads = False
nrf.crc = 0
nrf.arc = 0
nrf.allow_ask_no_ack = False

# use reverse engineering tactics for a better "snapshot"
nrf.address_length = 2
nrf.open_rx_pipe(1, b"\0\x55")
nrf.open_rx_pipe(0, b"\0\xAA")


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
        if nrf.available():
            nrf.flush_rx()  # flush the RX FIFO because it asserts the RPD flag
        nrf.listen = 1  # start a RX session
        time.sleep(0.00013)  # wait 130 microseconds
        signals[curr_channel] += nrf.rpd  # if interference is present
        nrf.listen = 0  # end the RX session
        curr_channel = curr_channel + 1 if curr_channel < 125 else 0

        # output the signal counts per channel
        sig_cnt = signals[curr_channel]
        print(
            ("%X" % min(15, sig_cnt)) if sig_cnt else "-",
            sep="",
            end="" if curr_channel < 125 else "\r",
        )
    # finish printing results and end with a new line
    while curr_channel < len(signals) - 1:
        curr_channel += 1
        sig_cnt = signals[curr_channel]
        print(("%X" % min(15, sig_cnt)) if sig_cnt else "-", sep="", end="")
    print("")


def noise(timeout=1, channel=None):
    """print a stream of detected noise for duration of time.

    :param int timeout: The number of seconds to scan for ambient noise.
    :param int channel: The specific channel to focus on. If not provided, then the
        radio's current setting is used.
    """
    if channel is not None:
        nrf.channel = channel
    nrf.listen = True
    timeout += time.monotonic()
    while time.monotonic() < timeout:
        signal = nrf.read()
        if signal:
            print(address_repr(signal, False, " "))
    nrf.listen = False
    while not nrf.fifo(False, True):
        # dump the left overs in the RX FIFO
        print(address_repr(nrf.read(), False, " "))


def set_role():
    """Set the role using stdin stream. Timeout arg for scan() can be
    specified using a space delimiter (e.g. 'S 10' calls `scan(10)`)
    """
    user_input = (
        input(
            "*** Enter 'S' to perform scan.\n"
            "*** Enter 'N' to display noise.\n"
            "*** Enter 'Q' to quit example.\n"
        )
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("S"):
        scan(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("N"):
        noise(*[int(x) for x in user_input[1:3]])
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = False
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nRF24L01 scanner test")
print(
    "!!!Make sure the terminal is wide enough for 126 characters on 1 line."
    " If this line is wrapped, then the output will look bad!"
)

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = False
else:
    print("    Run scan() to initiate scan for ambient signals.")
    print("    Run noise() to display ambient signals' data (AKA noise).")
