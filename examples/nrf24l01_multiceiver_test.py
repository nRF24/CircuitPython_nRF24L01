"""
Simple example of using 1 nRF24L01 to receive data from up to 6 other
transceivers. This technique is called "multiceiver" in the datasheet.
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

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

# setup the addresses for all transmitting nRF24L01 nodes
addresses = [
    b"\x78" * 5,
    b"\xF1\xB3\xB4\xB5\xB6",
    b"\xCD",
    b"\xA3",
    b"\x0F",
    b"\x05"
]

def base(timeout=10):
    """Use the nRF24L01 as a base station for lisening to all nodes"""
    # write the addresses to all pipes.
    for pipe_n, addr in enumerate(addresses):
        nrf.open_rx_pipe(pipe_n, addr)

    nrf.listen = True
    start_timer = time.monotonic()
    while time.monotonic() - start_timer < timeout:
        while not nrf.fifo(False, True):
            print(
                "payload from {} = {}".format(
                    nrf.address(nrf.pipe),
                    nrf.recv()
                )
            )
            start_timer = time.monotonic()
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
    while counter < count:
        payload = b"PTX-" + bytes([node_number + 1])
        payload += b" pl" + bytes([count + 48])
        nrf.send(payload)
        time.sleep(0.5)
