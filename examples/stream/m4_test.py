'''
    Example of library usage for streaming multiple payloads.
    Master transmits an payloads until FIFO is empty.
    Slave stops listening after 3 seconds of no response.
'''

import time, board, digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
address = b'1Node'

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D7)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

# lets create a list of payloads to be streamed to the nRF24L01 running slave()
buffers = []
SIZE = 32 # we'll use SIZE for the number of payloads in the list and the payloads' length
for i in range(SIZE):
    buff = b''
    for j in range(SIZE):
        buff += bytes([(j >= SIZE / 2 + abs(SIZE / 2 - i) or j < SIZE / 2 - abs(SIZE / 2 - i)) + 48])
    buffers.append(buff)
    del buff

def master(count=1): # count = 5 will only transmit 5 packets
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(address)
    # ensures the nRF24L01 is in TX mode
    nrf.listen = False

    success_percentage = 0
    for _ in range(count):
        now = time.monotonic_ns() / 1000000 # start timer
        result = nrf.send(buffers)
        print('Transmission took', time.monotonic_ns() / 1000000 - now, 'ms')
        for r in result:
            success_percentage += 1 if r else 0
    success_percentage /= SIZE * count
    print('successfully sent', success_percentage * 100, '%')

# running slave to only fetch/receive & count number of packets
def slave(timeout=5):
    # set address of TX node into an RX pipe. NOTE you MUST specify
    # which pipe number to use for RX, we'll be using pipe 0
    # pipe number options range [0,5]
    # the pipe numbers used during a transition don't have to match
    nrf.open_rx_pipe(0, address)
    nrf.listen = True # put radio into RX mode and power up

    count = 0
    now = time.monotonic() # start timer
    while time.monotonic() < now + timeout:
        if nrf.any():
            count += 1
            # retreive the received packet's payload
            rx = nrf.recv() # clears flags & empties RX FIFO
            print("Received (raw): {} - {}".format(repr(rx), count))
            now = time.monotonic()

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False # put the nRF24L01 is in TX mode

print("""\
    nRF24L01 Stream test\n\
    Run slave() on receiver\n\
    Run master() on transmitter""")
