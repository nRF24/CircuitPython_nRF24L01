"""
This module uses nRF24L01 transceivers to transport normal
USB HID mouse report data.
"""
import time
import struct
import board
from digitalio import DigitalInOut
from analogio import AnalogIn
# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

is_paired = [False]  # we should re-pair on every boot-up
address = [b"\x33Pair"]  # only known address is the pairing address
# bonded address after pairing will be the HID descriptor's usage +
# 4 bytes received from pairing handshake (via ACK payload)
# the HID descriptor's usage for a mouse is `6`, so bonded address will be
address.append(bytearray([6 + 48, 0, 0, 0, 0]))  # needs to be a bytearray
# NOTE we use `6 + 48` to avoid bad address formatting because of the
# OTA packet's preamble (see datasheet section 7.3.1-2)

hid_report_buf = [0] * 4  # use a list for storing mouse inputs
# the report buffer has 4 bytes:
#   byte0 = buttons in which each bit corresponds to an action
#       bit5 = back, bit4 = forward, bit2 = middle, bit1 = right, bit0 = left
#   byte1 = delta x-axis
#   byte2 = delta y-axis
#   byte3 = delta scroll wheel

# INSTANTIATE THE HARDWARE
buttons = [
    # THE ORDER HERE MATTERS
    DigitalInOut(board.D9),  # the left mouse button
    DigitalInOut(board.D10),  # the middle mouse button
    DigitalInOut(board.D11),  # the right mouse button
    DigitalInOut(board.D12),  # the backward mouse button
    DigitalInOut(board.D13),  # the forward mouse button
]
axes = [
    # THE ORDER HERE MATTERS
    AnalogIn(board.A0),  # the x-axis
    AnalogIn(board.A1),  # the y-axis
    AnalogIn(board.A2),  # the scroll wheel
]
ce_pin = DigitalInOut(board.D4)  # the nRF24L01 CE pin
csn_pin = DigitalInOut(board.D5)  # the nRF24L01 CSN pin
spi = board.SPI()  # the SPI object for the SPI bus
nrf = RF24(spi, csn_pin, ce_pin)  # the nRF24L01 object
nrf.ack = True  # for getting pairing data from the HUB
nrf.arc = 9  # max is 15, but this should be performant enough


def scan_and_report():
    """Scans buttons and analog inputs to assemble a data structure
    that resembles a mouse HID report"""
    curr_buf = [0] * 4
    for i, button in enumerate(buttons):
        curr_buf[0] |= button.value << i
    for i, axis in enumerate(axes):
        # scale analog inputs down to a signed 8 bits
        curr_buf[i + 1] = (axis.value - 32768) / 512
    need_to_report = False
    for i, data in enumerate(curr_buf):
        if hid_report_buf[i] != data:
            hid_report_buf[i] = data
            need_to_report = True
    if need_to_report:
        buf = struct.pack(
            "bBBB",
            hid_report_buf[0],
            hid_report_buf[1],
            hid_report_buf[2],
            hid_report_buf[3],
        )
        if not nrf.send(buf):
            is_paired[0] = False  # connection has been lost


if __name__ == "__main__":
    # initiate pairing operation
    nrf.open_tx_pipe(address[0])
    pairing_timeout = time.monotonic() + 1
    while time.monotonic() < pairing_timeout:
        if nrf.send(address[1], send_only=True):
            break

    if nrf.available():
        # pairing handshake completed
        address[1][1:] = nrf.read(4)  # save bonded address
        nrf.open_tx_pipe(address[1])  # set bonded address
        is_paired[0] = True

    with nrf:
        while is_paired[0]:
            scan_and_report()  # also detects if connection is broken
    #  radio powers down upon exiting `with` block
