"""
Simple example of using the RF24 class.
"""
import time
import struct
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


def master(count=5):  # count = 5 will only transmit 5 packets
    """Transmits an incrementing integer every second"""
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(address)
    # ensures the nRF24L01 is in TX mode
    nrf.listen = False

    while count:
        # use struct.pack to packetize your data
        # into a usable payload
        buffer = struct.pack("<i", count)
        # 'i' means a single 4 byte int value.
        # '<' means little endian byte order. this may be optional
        print("Sending: {} as struct: {}".format(count, buffer))
        now = time.monotonic() * 1000  # start timer
        result = nrf.send(buffer)
        if not result:
            print("send() failed or timed out")
        else:
            print("send() successful")
        # print timer results despite transmission success
        print("Transmission took", time.monotonic() * 1000 - now, "ms")
        time.sleep(1)
        count -= 1


def slave(count=5):
    """Polls the radio and prints the received value. This method expires
    after 6 seconds of no received transmission"""
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 0
    # pipe number options range [0,5]
    # the pipe numbers used during a transition don't have to match
    nrf.open_rx_pipe(0, address)
    nrf.listen = True  # put radio into RX mode and power up

    start = time.monotonic()
    while count and (time.monotonic() - start) < 6:
        if nrf.any():
            # print details about the received packet (if any)
            print("Found {} bytes on pipe {}".format(nrf.any(), nrf.pipe))
            # retreive the received packet's payload
            rx = nrf.recv()  # clears flags & empties RX FIFO
            # expecting an int, thus the string format '<i'
            buffer = struct.unpack("<i", rx[:4])
            # print the only item in the resulting tuple from
            # using `struct.unpack()`
            print("Received: {}, Raw: {}".format(buffer[0], repr(rx)))
            start = time.monotonic()
            count -= 1
            # this will listen indefinitely till count == 0
        time.sleep(0.25)

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False  # put the nRF24L01 is in TX mode


print(
    """\
    nRF24L01 Simple test.\n\
    Run slave() on receiver\n\
    Run master() on transmitter"""
)
