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
ACK = (b'World', 0)
#  note that `0` is always the TX pipe in TX mode
#  we'll be using pipe 0 to receive ACK packets per the spec sheet

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D7)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# the custom ACK payload feature is disabled by default
# the custom ACK payload feature cannot be enabled
# during instantiation due to its singular use nature
# meaning 1 ACK payload per 1 RX'd payload
nrf = RF24(spi, csn, ce)

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

# recommended behavior is to keep in TX mode while idle
nrf.stop_listening() # put radio in TX mode

def master(count=5): # count = 5 will only transmit 5 packets
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(addresses[0])
    # ensures the nRF24L01 is in TX mode
    # nrf.stop_listening()

    counter = count
    while counter:
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
        time.sleep(1)
        counter -= 1

# running slave to only fetch/receive count number of packets
# count = 3 will mimic a full RX FIFO behavior via nrf.stop_listening()
def slave(count=3):
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 0
    nrf.open_rx_pipe(0, addresses[0])

    # put radio into RX mode, power it up, and set the first
    # transmission's ACK payload and pipe number
    nrf.start_listening(ACK)

    counter = count
    while counter:
        if nrf.any():
            # print details about the received packet
            print('RX payload size =', nrf.any())
            print('RX payload on pipe', nrf.available())
            # retreive the received packet's payload
            rx = nrf.recv() # clears flags & empties RX FIFO
            print("Received (raw): {}".format(repr(rx)))
            nrf.ack = ACK # reload ACK for next response
            # this will listen indefinitely till counter == 0
            counter -= 1

    # recommended behavior is to keep in TX mode while sleeping
    nrf.stop_listening() # put radio in TX mode and power down

def debugRF24(dumpADDR=False):
    print('expected status =', bin(nrf.status))
    for item in nrf.what_happened(dumpADDR).items():
        print('{} : {}'.format(item[0], item[1]))

print("""\
    nRF24L01 ACK test.\n\
    Run slave() on receiver\n\
    Run master() on transmitter.""")
