'''
    Simple example of library usage.

    Master transmits an incrementing double every second.
    Slave polls the radio and prints the received value.
'''

import time, struct, board, digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24

addresses = (b'1Node', b'2Node')
# these addresses should be compatible with
# the GettingStarted.ino sketch included in
# TRMh20's arduino library

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.CE0) # AKA board.D8
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

# recommended behavior is to keep in TX mode while sleeping
nrf.stop_listening() # put the nRF24L01 is in TX and power down modes

def master(count=5): # count = 5 will only transmit 5 packets
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(addresses[0])
    # ensures the nRF24L01 is in TX and power down modes
    # nrf.stop_listening()

    i = 0.0 # init data to send

    counter = count
    while counter:
        # use struct.pack to packetize your data
        # into a usable payload
        temp = struct.pack('<d', i)
        # 'd' means a single 8 byte double value.
        # '<' means little endian byte order
        print("Sending: {} as struct: {}".format(i, temp))
        now = time.monotonic() * 1000 # start timer
        result = nrf.send(temp)
        if result == 0:
            print('send() timed out')
        elif result == 1:
            print('send() succeessful')
        elif result == 2:
            print('send() failed')
        # print timer results despite transmission success
        print('Transmission took',\
                time.monotonic() * 1000 - now, 'ms')
        time.sleep(1)
        i += 0.1
        counter -= 1

# running slave to only fetch/receive count number of packets
# count = 3 will mimic a full RX FIFO behavior via nrf.stop_listening()
def slave(count=3):
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 1
    # pipe number options range [0,5]
    nrf.open_rx_pipe(1, addresses[0])
    nrf.start_listening() # put radio into RX mode and power up

    counter = count
    while counter:
        if nrf.any():
            # print details about the received packet
            print('RX payload size =', nrf.any())
            print('RX payload on pipe', nrf.available())
            # retreive the received packet's payload
            rx = nrf.recv() # clears flags & empties RX FIFO
            # expecting a long int, thus the string format '<d'
            temp = struct.unpack('<d', rx)
            # print the only item in the resulting tuple from
            # using `struct.unpack()`
            print("Received: {}, Raw: {}".format(temp[0],\
                    repr(rx)))
            # this will listen indefinitely till counter == 0
            counter -= 1
        time.sleep(0.25)

    # recommended behavior is to keep in TX mode while sleeping
    nrf.stop_listening() # put the nRF24L01 is in TX and power down modes

def debugRF24(dumpADDR=False):
    print('expected status =', bin(nrf.status))
    for item in nrf.what_happened(dumpADDR).items():
        print('{} : {}'.format(item[0], item[1]))

print("""\
    nRF24L01 Simple test.\n\
    Run slave() on receiver\n\
    Run master() on transmitter.""")
