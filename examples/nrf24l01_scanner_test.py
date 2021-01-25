"""
This is an example of how to use the nRF24L01's builtin
Received Power Detection (RPD) to scan for possible interference.
This example does not require a counterpart node.
"""
import time
import board
import digitalio

# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# change these (digital output) pins accordingly
ce = digitalio.DigitalInOut(board.D4)
csn = digitalio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

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
    start_timer = time.monotonic()  # start the timer
    while time.monotonic() - start_timer < timeout:
        for curr_channel in range(126):  # for each channel
            nrf.channel = curr_channel
            time.sleep(0.00013)  # let radio modulate to new channel
            nrf.listen = 1  # start a RX session
            time.sleep(0.00013)  # wait 130 microseconds
            signals[curr_channel] += nrf.rpd  # if interference is present
            nrf.listen = 0  # end the RX session

            # ouptut the signal counts per channel
            print(
                hex(min(0x0F, signals[curr_channel]))[2:]
                if signals[curr_channel]
                else "-",
                sep="",
                end="" if curr_channel < 125 else "\r",
            )
    # print results 1 last time to end with a new line
    for sig in signals:
        print(hex(min(0x0F, sig))[2:] if sig else "-", sep="", end="")
    print("")


def set_role():
    """Set the role using stdin stream. Timeout arg for scan() can be
    specified using a space delimiter (e.g. 'S 10' calls `scan(10)`)

    :return:
        - True when role is complete & app should continue running.
        - False when app should exit
    """
    user_input = (
        input(
            "*** Enter 'S' to perform scan.\n"
            "*** Enter 'Q' to quit example.\n"
        )
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
