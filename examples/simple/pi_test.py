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

ce = dio.DigitalInOut(board.CE0) # AKA board.D8
csn = dio.DigitalInOut(board.D5)

spi = board.SPI()
# we'll be sending a dynamic
# payload of size 8 bytes (1 double)
nrf = RF24(spi, csn, ce)

def master():
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(addresses[0])
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 1
    # pipe number options range [0,5]
    nrf.open_rx_pipe(1, addresses[1])
    nrf.stop_listening() # put radio in TX mode and power down
    i = 0.0 # data to send

    while True:
        try:
            i += 0.01
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
        except KeyboardInterrupt:
            break
        finally:
            # print timer results despite transmission success
            print('Transmission took',\
                 time.monotonic() * 1000 - now, 'ms')
        time.sleep(1)

def slave():
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(addresses[1])
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 1
    # pipe number options range [0,5]
    nrf.open_rx_pipe(1, addresses[0])
    nrf.start_listening() # put radio into RX mode and power up

    while True:
        try:
            if nrf.any():
                then = nrf.recv()
                # expecting a long int, thus the string format '<d'
                temp = struct.unpack('<d', then)
                print("Received: {}, Raw: {}".format(temp[0],\
                     repr(then)))
        except KeyboardInterrupt:
            break

print("""\
    nRF24L01 Simple test.\
    Run slave() on receiver\
    Run master() on transmitter.""")
