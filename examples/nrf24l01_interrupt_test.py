"""
Simple example of detecting (and verifying) the IRQ (interrupt) pin on the
nRF24L01
    .. note:: this script uses the non-blocking `write()` function because
        the function `send()` clears the IRQ flags upon returning
"""
import time
import board
import digitalio as dio
# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# address needs to be in a buffer protocol object (bytearray is preferred)
address = b"1Node"

# select your digital input pin that's connected to the IRQ pin on the nRF4L01
irq_pin = dio.DigitalInOut(board.D12)
irq_pin.switch_to_input()  # make sure its an input object
# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

# this example uses the ACK payload to trigger the IRQ pin active for
# the "on data received" event
nrf.ack = True  # enable ACK payloads

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12


def _ping_and_prompt(buf):
    """transmit dummy payload, wait till irq_pin goes active, print IRQ status
    flags."""
    nrf.write(buf)  # write payload to TX FIFO
    time.sleep(0.00001)  # mandatory 10 microsecond pulse starts transmission
    ce.value = 0  # end 10 us pulse; now in active TX
    while irq_pin.value:  # IRQ pin is active when LOW
        pass
    nrf.update()  # update irq_d? status flags
    print(
        "\tirq_ds: {}, irq_dr: {}, irq_df: {}".format(
            nrf.irq_ds, nrf.irq_dr, nrf.irq_df
        )
    )

def master():
    """Transmits 3 times: successfully receive ACK payload first, successfully
    transmit on second, and intentionally fail transmit on the third"""
    # set address of RX node into a TX pipe
    nrf.open_tx_pipe(address)
    # ensures the nRF24L01 is in TX mode
    nrf.listen = False
    # NOTE nrf.power is automatically set to True on first call to nrf.write()

    # on data ready test
    print("\nConfiguring IRQ pin to only ignore 'on data sent' event")
    nrf.interrupt_config(data_sent=False)
    print("    Pinging slave node for an ACK payload.")
    _ping_and_prompt(b"Ping ")
    if nrf.irq_dr:
        print("\t'on data ready' event test successful")
    else:
        print("\t'on data ready' event test unsucessful")
    nrf.clear_status_flags()  # clear all irq_d? flags for next test

    # on data sent test
    print("\nConfiguring IRQ pin to only ignore 'on data ready' event")
    nrf.interrupt_config(data_recv=False)
    print("    Pinging slave node again.")
    _ping_and_prompt(b"Pong ")
    if nrf.irq_ds:
        print("\t'on data sent' event test successful")
    else:
        print("\t'on data sent' event test unsucessful")
    nrf.clear_status_flags()  # clear all irq_d? flags for next test

    print("\nSending one extra payload to fill RX FIFO on slave node.")
    nrf.write(b"Radio")  # write payload to TX FIFO
    time.sleep(0.00001)  # mandatory 10 microsecond pulse starts transmission
    ce.value = 0  # end 10 us pulse; now in active TX
    nrf.clear_status_flags()  # clear all irq_d? flags for next test
    print("Slave node should not be listening anymore. Ready to continue.")

    # on data fail test
    print("\nConfiguring IRQ pin to go active for all events.")
    nrf.interrupt_config()
    print("    Sending a ping to inactive slave node.")
    nrf.flush_tx()  # just in case the previous "on data sent" test failed
    _ping_and_prompt(b"Dummy")
    if nrf.irq_df:
        print("\t'on data failed' event test successful")
    else:
        print("\t'on data failed' event test unsucessful")
    nrf.clear_status_flags()  # clear all irq_d? flags for next test
    # flush TX FIFO from any failed tests
    nrf.flush_tx()
    # all 3 ACK payloads received were 4 bytes each, and RX FIFO is full
    # so, fetching 12 bytes from the RX FIFO also flushes RX FIFO
    print("\nComplete RX FIFO:", nrf.recv(12))


def slave(timeout=6):  # will listen for 6 seconds before timing out
    """Only listen for 3 payload from the master node"""
    # setup radio to recieve pings, fill TX FIFO with ACK payloads
    nrf.open_rx_pipe(0, address)
    nrf.load_ack(b"Yak ", 0)
    nrf.load_ack(b"Back", 0)
    nrf.load_ack(b" ACK", 0)
    nrf.listen = True  # start listening & clear irq_dr flag
    start_timer = time.monotonic()  # start timer now
    while not nrf.fifo(0, 0) and time.monotonic() - start_timer < timeout:
        # if RX FIFO is not full and timeout is not reached; keep going
        pass
    nrf.listen = False  # put nRF24L01 in Standby-I mode when idling
    if not nrf.fifo(False, True):  # if RX FIFO is not empty
        # all 3 payloads received were 5 bytes each, and RX FIFO is full
        # so, fetching 15 bytes from the RX FIFO also flushes RX FIFO
        print("Complete RX FIFO:", nrf.recv(15))
    nrf.flush_tx()  # discard any pending ACK payloads
