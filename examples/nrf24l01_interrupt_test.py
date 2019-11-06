"""
Simple example of detecting (and verifying) the IRQ
interrupt pin on the nRF24L01
"""
import time
import board
import digitalio as dio
from circuitpython_nrf24l01 import RF24

# address needs to be in a buffer protocol object (bytearray is preferred)
address = b'1Node'

# select your digital input pin that's connected to the IRQ pin on the nRF4L01
irq = dio.DigitalInOut(board.D4)
irq.switch_to_input()  # make sure its an input object
# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)
nrf.arc = 15  # turn up automatic retries to the max. default is 3

def master(timeout=5):  # will only wait 5 seconds for slave to respond
    """Transmits once, receives once, and intentionally fails a transmit"""
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(address)
    # ensures the nRF24L01 is in TX mode
    nrf.listen = 0

    # on data sent test
    print("Pinging: enslaved nRF24L01 without auto_ack")
    nrf.write(b'ping')
    time.sleep(0.00001)  # mandatory 10 microsecond pulse starts transmission
    nrf.ce.value = 0  # end 10 us pulse; now in active TX
    while not nrf.irq_DS and not nrf.irq_DF:
        nrf.update()  # updates the current status on IRQ flags
    if nrf.irq_DS and not irq.value:
        print('interrupt on data sent successful')
    else:
        print(
            'IRQ on data sent is not active, check your wiring and call interrupt_config()')
    nrf.clear_status_flags()  # clear all flags for next test

    # on data ready test
    nrf.listen = 1
    nrf.open_rx_pipe(0, address)
    start = time.monotonic()
    while not nrf.any() and time.monotonic() - start < timeout:  # wait for slave to send
        pass
    if nrf.any():
        print('Pong received')
        if nrf.irq_DR and not irq.value:
            print('interrupt on data ready successful')
        else:
            print(
                'IRQ on data ready is not active, check your wiring and call interrupt_config()')
        nrf.flush_rx()
    else:
        print('pong reception timed out!. make sure to run slave() on the other nRF24L01')
    nrf.clear_status_flags()  # clear all flags for next test

    # on data fail test
    nrf.listen = False  # put the nRF24L01 is in TX mode
    # the writing pipe should still be open since we didn't call close_tx_pipe()
    nrf.flush_tx()  # just in case the previous "on data sent" test failed
    nrf.write(b'dummy')  # slave isn't listening anymore
    time.sleep(0.00001)  # mandatory 10 microsecond pulse starts transmission
    nrf.ce.value = 0  # end 10 us pulse; now in active TX
    while not nrf.irq_DS and not nrf.irq_DF:  # these attributes don't update themselves
        nrf.update()  # updates the current status on all IRQ flags (irq_DR, irq_DF, irq_DS)
    if nrf.irq_DF and not irq.value:
        print('interrupt on data fail successful')
    else:
        print(
            'IRQ on data fail is not active, check your wiring and call interrupt_config()')
    nrf.clear_status_flags()  # clear all flags for next test

def slave(timeout=10):  # will listen for 10 seconds before timing out
    """Acts as a ponging RX node to successfully complete the tests on the master"""
    # setup radio to recieve ping
    nrf.open_rx_pipe(0, address)
    nrf.listen = 1
    start = time.monotonic()
    while not nrf.any() and time.monotonic() - start < timeout:
        pass  # nrf.any() also updates the status byte on every call
    if nrf.any():
        print("ping received. sending pong now.")
    else:
        print('listening timed out, please try again')
    nrf.flush_rx()
    nrf.listen = 0
    nrf.open_tx_pipe(address)
    nrf.send(b'pong')  # send a payload to complete the on data ready test
    # we're done on this side

print("""\
    nRF24L01 Interrupt test\n\
    Run master() to run IRQ pin tests\n\
    Run slave() on the non-testing nRF24L01 to complete the test successfully""")
