"""
Simple example of using the library to transmit
and retrieve custom automatic acknowledgment payloads.
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
# the custom ACK payload feature is disabled by default
# the custom ACK payload feature should not be enabled
# during instantiation due to its singular use nature
# meaning 1 ACK payload per 1 RX'd payload
nrf = RF24(spi, csn, ce)

# NOTE the the custom ACK payload feature will be enabled
# automatically when you call load_ack() passing:
# a buffer protocol object (bytearray) of
# length ranging [1,32]. And pipe number always needs
# to be an int ranging [0,5]

# to enable the custom ACK payload feature
nrf.ack = True  # False disables again

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12

# addresses needs to be in a buffer protocol object (bytearray)
address = b"1Node"

# NOTE ACK payloads (like regular payloads and addresses)
# need to be in a buffer protocol object (bytearray)
ACK = b"World "


def master(count=5):  # count = 5 will only transmit 5 packets
    """Transmits a payload every second and prints the ACK payload"""
    nrf.listen = False  # put radio in TX mode
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(address)

    while count:
        buffer = b"Hello " + bytes([count + 48])  # output buffer
        print("Sent:", buffer, end=" ")
        start_timer = time.monotonic() * 1000  # start timer
        result = nrf.send(buffer)  # save the response (ACK payload)
        end_timer = time.monotonic() * 1000  # stop timer
        if not result:
            print("send() failed or timed out")
        else:
            # print the received ACK that was automatically
            # fetched and saved to "result" via send()
            print("Received:", result)
        # print timer results despite transmission success
        print("Transmission took", end_timer - start_timer, "ms")
        time.sleep(1)  # let the RX node prepare a new ACK payload
        count -= 1


def slave(count=5):
    """Prints the received value and sends an ACK payload"""
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX; we'll be using pipe 0
    nrf.open_rx_pipe(0, address)
    # put radio into RX mode, power it up
    nrf.listen = True

    # setup the first transmission's ACK payload
    buffer = ACK + bytes([count + 48])
    # we must set the ACK payload data and corresponding
    # pipe number [0,5]
    nrf.load_ack(buffer, 0)  # load ACK for first response

    start = time.monotonic()  # start timer
    while count and (time.monotonic() - start) < 6:  # use 6 second timeout
        if nrf.update() and nrf.pipe is not None:
            count -= 1
            # retreive the received packet's payload
            rx = nrf.recv()  # clears flags & empties RX FIFO
            print("Received: {} Sent: {}".format(rx, buffer))
            start = time.monotonic()  # reset timer
            if count:  # Going again?
                buffer = ACK + bytes([count + 48])  # build a new ACK
                nrf.load_ack(buffer, 0)  # load ACK for next response

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False  # put radio in TX mode
    nrf.flush_tx()  # flush any ACK payloads that remain


print(
    """\
    nRF24L01 ACK test\n\
    Run slave() on receiver\n\
    Run master() on transmitter"""
)
