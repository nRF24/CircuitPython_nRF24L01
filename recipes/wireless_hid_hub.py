"""
HID Hub Recipe
==============

This module uses CircuitPython's builtin usb_hid library as a wireless
hub to extend USB HID interfaces via the nRF24L01 transceivers.

Dependencies
------------

circuitpython firmware (namely the `usb_hid` module)

.. warning:: This is not compatible with linux-based SoC computers
    like the Raspberry Pi because the ``adafruit-blinka`` library
    does not provide the same *exact* API that the CircuitPython
    firmware does (concerning the usb_hid module).
"""
import board
from digitalio import DigitalInOut
import usb_hid
from circuitpython_nrf24l01.rf24 import RF24
# from microcontroller import nvm

# SETUP THE HID LIST
# index 0 for wireless cmds; indices 1-4 will relate to the pipe which
# received the HID data reports to pass on over the USB cable
hid = [b""] + [None] * 4
for device in usb_hid.devices:
    if device.usage == 6 and device.usage_page == 1:
        hid[1] = device  # mouse
    elif device.usage == 2 and device.usage_page == 1:
        hid[2] = device  # keyboard
    elif device.usage == 5 and device.usage_page == 1:
        hid[3] = device  # gamepad
    elif device.usage == 1 and device.usage_page == 0x0C:
        hid[4] = device  # consumer


# SETUP THE TRANSCEIVER
ce_pin = DigitalInOut(board.D4)  # the nRF24L01 CE pin
csn_pin = DigitalInOut(board.D5)  # the nRF24L01 CSN pin
spi = board.SPI()  # the SPI object for the SPI bus
nrf = RF24(spi, csn_pin, ce_pin)  # the nRF24L01 object
nrf.address_length = 4  # we only need 4-byte addresses
nrf.open_rx_pipe(0, b"Pair")  # pipe for pairing operations
nrf.open_rx_pipe(1, b"6HID")  # pipe for mouse HID
nrf.open_rx_pipe(2, b"2HID")  # pipe for keyboard HID
nrf.open_rx_pipe(3, b"5HID")  # pipe for gamepad HID
nrf.open_rx_pipe(4, b"1HID")  # pipe for Consumer HID
nrf.close_rx_pipe(5)  # pipe 5 will not be used
nrf.ack = True  # for returning data to peripherals in ACK payloads

def host():
    """Run this function to enable the nRF24L01 as a wireless HID hub"""
    nrf.listen = True  # start listening
    sleep_cmd = False  # can be told to
    while not sleep_cmd:
        while not nrf.fifo(False, True):
            if nrf.pipe:  # if pipe number > 0
                # forward the data
                hid[nrf.pipe].send_report(nrf.recv())
            else:  # use pipe 0 as a cmd interface
                hid[0] = nrf.recv()  # grab cmd buffer
                if hid[0][0] == 0:  # if first cmd byte is 0
                    sleep_cmd = True  # put radio to sleep
    nrf.listen = False
    nrf.power = False  # really; put it to sleep
