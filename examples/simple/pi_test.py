'''
    Simple example of library usage.

    Master transmits an incrementing double every second.
    Slave polls the radio and prints the received value.
'''

import time, struct, board, digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
address = b'1Node'

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.CE0) # AKA board.D8
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

def master(count=5): # count = 5 will only transmit 5 packets
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(address)
    # ensures the nRF24L01 is in TX mode
    nrf.listen = False

    counter = count
    while counter:
        # use struct.pack to packetize your data
        # into a usable payload
        buffer = struct.pack('<i', counter)
        # 'i' means a single 4 byte int value.
        # '<' means little endian byte order. this may be optional
        print("Sending: {} as struct: {}".format(counter, buffer))
        now = time.monotonic() * 1000 # start timer
        result = nrf.send(buffer)
        if result is None:
            print('send() timed out')
        elif not result:
            print('send() failed')
        else:
            print('send() successful')
        # print timer results despite transmission success
        print('Transmission took',\
                time.monotonic() * 1000 - now, 'ms')
        time.sleep(1)
        counter -= 1

# running slave to only fetch/receive count number of packets
# count = 3 will mimic a full RX FIFO behavior via nrf.listen = False
def slave(count=3):
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 0
    # pipe number options range [0,5]
    # the pipe numbers used during a transition don't have to match
    nrf.open_rx_pipe(0, address)
    nrf.listen = True # put radio into RX mode and power up

    counter = count
    start = time.monotonic()
    while counter and (time.monotonic() - start) < (count * 2):
        if nrf.any():
            # print details about the received packet (if any)
            print("Found {} bytes on pipe {}\
                ".format(repr(nrf.any()), nrf.pipe()))
            # retreive the received packet's payload
            rx = nrf.recv() # clears flags & empties RX FIFO
            # expecting an int, thus the string format '<i'
            buffer = struct.unpack('<i', rx)
            # print the only item in the resulting tuple from
            # using `struct.unpack()`
            print("Received: {}, Raw: {}".format(buffer[0], repr(rx)))
            start = time.monotonic()
            counter -= 1
            # this will listen indefinitely till counter == 0
        time.sleep(0.25)

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False # put the nRF24L01 is in TX mode

print("""\
    nRF24L01 Simple test.\n\
    Run slave() on receiver\n\
    Run master() on transmitter""")
