'''
    Simple example of library usage.

    Master transmits an incrementing integer every second. 
    Slave polls the radio every 0.5s and prints the received value.

    This is a simple test to get communications up and running.
'''

import time, struct, board, digitalio as dio
from busio import SPI
from circuitpython_nrf24l01 import NRF24L01

addresses = (b'1Node', b'2Node')
# these addresses should be compatible with the GettingStarted.ino sketch included in TRMh20's arduino library 

ce = dio.DigitalInOut(board.D7)
csn = dio.DigitalInOut(board.D5)

spi = board.SPI()
# we'll be sending a dynamic payload of size 8 bytes (1 double)
nrf = NRF24L01(spi, csn, ce, payload_length=8) 

def master():
    nrf.stop_listening() # put radio in TX mode
    nrf.open_tx_pipe(addresses[0]) # set address of RX node into a TX pipe
    i = -0.01 # data to send

    while True:
        try:
            i += 0.01 
            # use struct.pack to packetize your data into a usable payload
            temp = struct.pack('<d', i) # 'd' means a single 8 byte double value. '<' means little endian byte order
            print("Sending: {} as struct: {}".format(i, temp))
            now = time.monotonic() * 1000 # start timer
            nrf.send(temp)
        except OSError:
            print('send() failed')
        except KeyboardInterrupt: 
            break
        finally:
            # print timer results despite transmission success
            print('Transmission took', time.monotonic() * 1000 - now, 'ms')
        time.sleep(1)

def slave():
    # set address of TX node into an RX pipe. NOTE you MUST specify which pipe number to use for RX, we'll be using pipe 1 (options range [0,5])
    nrf.open_rx_pipe(1, addresses[1]) 
    nrf.start_listening() # put radio into RX mode

    while True:
        try:
            if nrf.any():
                then = nrf.recv()
                temp = struct.unpack('<d', then) # expecting a long int
                print("Received: {}, Raw: {}".format(temp[0], repr(then)))
            # time.sleep(0.5)
        except KeyboardInterrupt: break

print('NRF24L01 test module.\nRun slave() on receiver, and master() on transmitter.')
