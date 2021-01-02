"""
This example shows how to use the nRF24L01 to communicate to
a Logitech Unifying receiver as a Logitech mouse (model M510)
"""
from math import sin, cos, radians
import board
from digitalio import DigitalInOut
from circuitpython_nrf24l01.rf24 import RF24
from circuitpython_nrf24l01.logitech_mouse import LogitechMouse


ce = DigitalInOut(board.D4)
csn = DigitalInOut(board.D5)
SPI = board.SPI()
nrf = RF24(SPI, csn, ce)
logi_mouse = LogitechMouse(nrf)
CONNECTED = False
if not logi_mouse.reconnect():
    # could not reconnect to previous address saved on nRF24L01's RX_ADDR_P0 register
    # try to pair with Logitech Unifying receiver/dongle
    # NOTE dongle must be in pairing mode using Logitech Unifying software
    CONNECTED = logi_mouse.pair()

if CONNECTED:
    # move the mouse cursor in a circle
    for x in range(0, 360, 5):
        logi_mouse.input(
            x_move=(10.0 * cos(radians(x))),
            y_move=(10.0 * sin(radians(x)))
        )
