"""
This is an example of how to use the nRF24L01's builtin
Received Power Detection (RPD). This example does not require a
counterpart node, but a master() function is provided to broadcast a constant
carrier wave (which causes interference) for a certain RF data rate & channel.
"""
import time
import board
import digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

spi = board.SPI()
nrf = RF24(spi, csn, ce)


def print_header():
    """print the vertical header of channel numbers"""
    print("_" * 126 + "\n" + "0" * 100 + "1" * 26)
    for i in range(13):
        print(str(i % 10) * (10 if i < 12 else 6), sep="", end="")
    print("")  # endl
    for i in range(126):
        print(str(i % 10), sep="", end="")
    print("\n" + "^" * 126)

def scan(timeout=15):
    """Traverse the spectrum of accessible frequencies and print any detection
    of ambient signals.

    :param int timeout: The number of seconds for which scanning is performed.
    """
    # set the starting channel (2400 MHz for 1 Mbps or 2401 MHz for 2 Mbps)
    start_timer = time.monotonic()  # start the timer
    loop_count = 0
    while time.monotonic() - start_timer < timeout:
        if (loop_count % 19) == 0:
            print_header()
        signals = [0] * 126  # store the signal count for each channel
        for curr_channel in range(126):  # for each channel
            for _ in range(10):
                nrf.channel = curr_channel
                nrf.listen = 1  # start a RX session
                time.sleep(0.00013)  # wait 130 microseconds
                signals[curr_channel] += nrf.rpd * 1  # if interference is present
                nrf.listen = 0  # reset the RDP flag
                time.sleep(0.00013)

        # ouput the signal counts per channel
        for sig in signals:
            print(sig if sig else "-", sep="", end="")
        print("")  # endl
        loop_count += 1



print(
    """\
    nRF24L01 scanner test\n\
    Run scan() to initiate scan for ambient signals.\n\
    Or manually broadcast a constant carrier wave."""
)
