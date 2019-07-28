'''
    Templated example of using the library to transmit
    and retrieve custom automatic acknowledgment payloads.

    Master transmits a dummy payload every second and prints the ACK payload.
    Slave prints the received value and sends a dummy ACK payload.
'''

import time, board, digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
addresses = (b'1Node', b'2Node')
# these addresses should be compatible with the GettingStarted.ino
# sketch included in TRMh20's arduino library

# payloads need to be in a buffer protocol object (bytearray)
tx = b'Hello'

# we must use a tuple to set the ACK payload
# data and corresponding pipe number
# pipe number options range [0,5]
# NOTE ACK payloads (like regular payloads and addresses)
# need to be in a buffer protocol object (bytearray)
ACK = (b'World', 1)
#  note that `0` is always the TX pipe in TX mode
#  we'll be using

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D7)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# the custom ACK payload feature is disabled by default
# the custom ACK payload feature can be enabled
# during instantiation by passing a custom ACK payload
# to the `ack` the parameter like so:
nrf = RF24(spi, csn, ce, ack=(b'dummy',1))

# NOTE the the custom ACK payload feature will be enabled
# automatically when you set the attribute to a tuple who's
# first item is a buffer protocol object (bytearray) of
# length ranging [1,32]
# remember the second item always needs to be an int ranging [0,5]

# to disable the custom ACK payload feature
# we need set some dummy data to the ack attribute
# NOTE the first item in the dummy tuple must be `None`
# remember the second item always needs to be an int ranging [0,5]
nrf.ack = (None, 1)

def master():
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(addresses[0])
    # since auto-acknowledgments feature is enabled, we need to
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 1
    # pipe number options range [0,5]
    nrf.open_rx_pipe(1, addresses[1])
    nrf.stop_listening() # put radio in TX mode and power down

    while True:
        try:
            print("Sending (raw): {}".format(repr(tx)))
            # to read the ACK payload during TX mode we
            # pass the parameter read_ack as True.
            result = nrf.send(tx, read_ack=True)
            if result == 0:
                print('send() timed out')
            elif result == 1:
                # print the received ACK that was automatically
                # fetched and saved to nrf's ack attribute via send()
                print('raw ACK: {}'.format(repr(nrf.ack)))
                # the ACk payload should also include the default
                # response data that the nRF24L01 uses despite
                # a custom set ACK payload.
            elif result == 2:
                print('send() failed')
        except KeyboardInterrupt:
            break
        time.sleep(1)

def slave():
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(addresses[1])
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 1
    nrf.open_rx_pipe(1, addresses[0])

    while True:
        try:
            if nrf.any():
                # print details about the received packet
                print('RX payload size =', nrf.any())
                print('RX payload on pipe', nrf.available())
                # retreive the received packet's payload
                rx = nrf.recv() # clears flags & empties RX FIFO
                print("Received (raw): {}".format(repr(rx)))
                nrf.ack = ACK # reload ACK for next response
        except KeyboardInterrupt:
            break

print("""\
    nRF24L01 ACK test.\n\
    Run slave() on receiver\n\
    Run master() on transmitter.""")
