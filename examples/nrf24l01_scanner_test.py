"""
This is an example of how to use the nRF24L01's builtin
Received Power Detection (RPD). This example does not require a
counterpart node, but a master() function is provided to broadcast a constant
carrier wave (which causes interference) for a certain RF data rate & channel.
"""
import time
import board
import digitalio as dio

# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)
spi = board.SPI()
nrf = RF24(spi, csn, ce)
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


print(
    """\
    nRF24L01 scanner test\n\
    Run scan() to initiate scan for ambient signals."""
)
