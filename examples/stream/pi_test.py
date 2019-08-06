'''
    Example of library usage for streaming multiple payloads.
    Master transmits an payloads until FIFO is empty.
    Slave stops listening after 3 seconds of no response.
'''

import time, struct, board, digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
addresses = (b'1Node', b'2Node')
# these addresses should be compatible with
# the GettingStarted.ino sketch included in
# TRMh20's arduino library

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D8) # AKA board.CE0
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

#lets create a list of payloads to be streamed to the nRF24L01 running slave()
buffers = []
for i in range(32):
    buff = b''
    for j in range(32):
        buff += bytes([(j >= 16 + abs(16 - i) or j < 16 - abs(16 - i)) + 48])
    buffers.append(buff)
del buff

def master(): # count = 5 will only transmit 5 packets
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(addresses[0])
    # ensures the nRF24L01 is in TX and power down modes
    nrf.listen = False

    now = time.monotonic() * 1000 # start timer
    result = nrf.send(buffers)

    # print timer results despite transmission success
    print('Transmission took',\
            time.monotonic() * 1000 - now, 'ms')

    for i, r in result:
        if r is None:
            print('timed out {}'.format(buffers[i]))
        elif r == False:
            print('failed {}'.format(buffers[i]))
        else:
            print('succeessful {}'.format(buffers[i]))

# running slave to only fetch/receive count number of packets
# count = 3 will mimic a full RX FIFO behavior via nrf.listen = False
def slave(timeout=3):
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 0
    # pipe number options range [0,5]
    # the pipe numbers used during a transition don't have to match
    nrf.open_rx_pipe(0, addresses[0])
    nrf.listen = True # put radio into RX mode and power up

    now = time.monotonic() # start timer
    while time.monotonic() < now + timeout:
        if nrf.any():
            # retreive the received packet's payload
            rx = nrf.recv() # clears flags & empties RX FIFO
            print("Received (raw): {}".format(rx))
            now = time.monotonic()

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False # put the nRF24L01 is in TX and power down modes

print("""\
    nRF24L01 Stream test\n\
    Run slave() on receiver\n\
    Run master() on transmitter""")
