"""
Example of library usage for streaming multiple payloads.
"""
import time
import board
import digitalio as dio
# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
address = b"1Node"

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12


def master(count=1):  # count = 5 will transmit the list 5 times
    """Transmits a massive buffer of payloads"""
    # lets create a `list` of payloads to be streamed to
    # the nRF24L01 running slave()
    buffers = []
    # we'll use SIZE for the number of payloads in the list and the
    # payloads' length
    size = 32
    for i in range(size):
        # prefix payload with a sequential letter to indicate which
        # payloads were lost (if any)
        buff = bytes([i + (65 if 0 <= i < 26 else 71)])
        for j in range(size - 1):
            char = bool(j >= (size - 1) / 2 + abs((size - 1) / 2 - i))
            char |= bool(j < (size - 1) / 2 - abs((size - 1) / 2 - i))
            buff += bytes([char + 48])
        buffers.append(buff)
        del buff

    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(address)
    # ensures the nRF24L01 is in TX mode
    nrf.listen = False

    successful = 0
    for _ in range(count):
        now = time.monotonic() * 1000  # start timer
        result = nrf.send(buffers, force_retry=2)
        print("Transmission took", time.monotonic() * 1000 - now, "ms")
        for r in result:
            successful += 1 if r else 0
    print(
        "successfully sent {}% ({}/{})".format(
            successful / (size* count) * 100, successful, size * count
        )
    )


def slave(timeout=5):
    """Stops listening after timeout with no response"""
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 0
    # pipe number options range [0,5]
    # the pipe numbers used during a transition don't have to match
    nrf.open_rx_pipe(0, address)
    nrf.listen = True  # put radio into RX mode and power up

    count = 0
    now = time.monotonic()  # start timer
    while time.monotonic() < now + timeout:
        if nrf.any():
            count += 1
            # retreive the received packet's payload
            rx = nrf.recv()  # clears flags & empties RX FIFO
            print("Received: {} - {}".format(repr(rx), count))
            now = time.monotonic()

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False  # put the nRF24L01 is in TX mode


print(
    """\
    nRF24L01 Stream test\n\
    Run slave() on receiver\n\
    Run master() on transmitter"""
)
