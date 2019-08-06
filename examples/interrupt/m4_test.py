'''
    Simple example of detecting (and verifying) the IRQ
    interrupt pin on the nRF24L01

    Master transmits twice and intentionally fails the third.
    Slave just acts as a RX node to success w/ aut_ack feature.
'''

import time, struct, board, digitalio as dio
from circuitpython_nrf24l01.rf24 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
addresses = (b'1Node', b'2Node')
# these addresses should be compatible with
# the GettingStarted.ino sketch included in
# TRMh20's arduino library

# select your digital input pin to attach to the IRQ pin on the nRF4L01
# TIP: connect an led + 220ohm (connected in series) to GND from IRQ
irq = dio.DigitalInOut(board.D4)
irq.switch_to_input() # make sure its an input object
# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D7)
csn = dio.DigitalInOut(board.D5)
irq = dio.DigitalInOut(board.D4)
irq.switch_to_input() # make this our interrupt detector

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)
# create a secong rf24 onject to be used on the same hardware radio
rf0 = RF24(spi, csn, ce, dynamic_payloads=False)
# disable all features that require dynamic_payloads on the second object.

def test(): # count = 5 will only transmit 5 packets
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(addresses[0])
    # ensures the nRF24L01 is in TX and power down modes
    nrf.listen = False

    counter = count
    while counter:
        # use struct.pack to packetize your data
        # into a usable payload
        temp = struct.pack('<d', i)
        # 'd' means a single 8 byte double value.
        # '<' means little endian byte order
        print("Sending: {} as struct: {}".format(i, temp))
        now = time.monotonic_ns() / 1000000 # start timer
        result = nrf.send(temp)
        if result is None:
            print('send() timed out')
        elif result == False:
            print('send() failed')
        else:
            print('send() succeessful')
        # print timer results despite transmission success
        print('Transmission took',\
                time.monotonic_ns() / 1000000 - now, 'ms')
        time.sleep(1)
        i += 0.1
        counter -= 1

        # recommended behavior is to keep in TX mode while sleeping
        nrf.listen = False # put the nRF24L01 is in TX and power down modes

print("""\
    nRF24L01 Interrupt test\n\
    Run test() to run IRQ pin tests""")
