"""
Simple example of using 1 nRF24L01 to receive data from up to 6 other
transceivers. This technique is called "multiceiver" in the datasheet.
For fun, this example also sends an ACK payload from the base station
to the node-1 transmitter.
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
    b"\xCD\xB3\xB4\xB5\xB6",
    b"\xA3\xB3\xB4\xB5\xB6",
    b"\x0F\xB3\xB4\xB5\xB6",
    b"\x05\xB3\xB4\xB5\xB6"
]

# to use custom ACK payloads, we must enable that feature
nrf.ack = True
# let this be the ACk payload
ACK = b"Yak Back ACK"


def base(timeout=10):
    """Use the nRF24L01 as a base station for lisening to all nodes"""
    # write the addresses to all pipes.
    for pipe_n, addr in enumerate(addresses):
        nrf.open_rx_pipe(pipe_n, addr)
    # fill TX FIFO with ACK payloads
    while nrf.fifo(True, False):
        nrf.load_ack(ACK, 1)  # only send ACK payload to node 1
    nrf.listen = True
    start_timer = time.monotonic()
    while time.monotonic() - start_timer < timeout:
        while not nrf.fifo(False, True):
            print("node", nrf.pipe, "sent:", nrf.recv())
            start_timer = time.monotonic()
            if nrf.load_ack(ACK, 1):
                print("\t ACK re-loaded")
    nrf.listen = False


def node(node_number, count=6):
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
        counter += 1
        payload = b"PTX-" + bytes([node_number + 49])
        payload += b" pl" + bytes([counter + 48])
        print("attempt {} returned {}".format(counter, nrf.send(payload)))
        time.sleep(0.5)


print(
    """\
    nRF24L01 Multiceiver test.\n\
    Run base() on the receiver\n\
        base() sends ACK payloads to node 1\n\
    Run node(node_number) on a transmitter\n\
        node()'s parameter, `node_number`, must be in range [0, 5]"""
)
