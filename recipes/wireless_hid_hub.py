"""
This module uses CircuitPython's builtin usb_hid library as a wireless
hub to extend USB HID interfaces via the nRF24L01 transceivers.

Dependencies in CircuitPython firmware
======================================

- usb_hid
- microcontroller.nvm

.. warning:: This recipe is not compatible with linux-based SoC computers
    like the Raspberry Pi because the `adafruit-blinka library
    does not provide the `usb_hid` module and non-volatile memory (`microcontroller.nvm`) access.
"""
import time
from os import urandom
import board
from digitalio import DigitalInOut
import usb_hid
from circuitpython_nrf24l01.rf24 import RF24
from microcontroller import nvm

# SETUP THE HID LIST
# indices 0-3 corresponds to the pipe for which the
# received HID data reports will be forwarded over the USB cable
hid = [None] * 4
for device in usb_hid.devices:
    if device.usage == 6 and device.usage_page == 1:
        hid[0] = device  #: mouse
    elif device.usage == 2 and device.usage_page == 1:
        hid[1] = device  #: keyboard
    elif device.usage == 5 and device.usage_page == 1:
        hid[2] = device  #: gamepad
    elif device.usage == 1 and device.usage_page == 0x0C:
        hid[3] = device  #: consumer

# INSTANTIATE THE HARDWARE
ce_pin = DigitalInOut(board.D4)  # the nRF24L01 CE pin
csn_pin = DigitalInOut(board.D5)  # the nRF24L01 CSN pin
spi = board.SPI()  # the SPI object for the SPI bus
nrf = RF24(spi, csn_pin, ce_pin)  # the nRF24L01 object
multi_func_button = DigitalInOut(board.D2)  # the pair/sleep hardware button

# SETUP THE TRANSCEIVER
if nvm[:4] == b"\xFF" * 4:
    # "securely" generate a base address for bonding
    nvm[:4] = urandom(4)
# NOTE reset the generated bonding address by
# stopping this script and executing:
#    from microcontroller import nvm
#    nvm[:4] = b"\xFF" * 4
# then start this script again

nrf.open_rx_pipe(0, b"\x33Pair")  # pipe for pairing operations
nrf.open_rx_pipe(1, b"\x06" + nvm[:4])  # pipe for mouse HID
nrf.open_rx_pipe(2, b"\x02" + nvm[:4])  # pipe for keyboard HID
nrf.open_rx_pipe(3, b"\x05" + nvm[:4])  # pipe for gamepad HID
nrf.open_rx_pipe(4, b"\x01" + nvm[:4])  # pipe for Consumer HID
nrf.close_rx_pipe(5)  # pipe not used (reserved for future features)
nrf.ack = True  # for returning data to peripherals in ACK payloads
while nrf.load_ack(0, nvm[:4]):
    pass  # fill the TX FIFO with pairing request responses

def host():
    """Run this function to enable the nRF24L01 as a wireless HID hub"""
    while multi_func_button.value:
        pass  # wait till the button is released
    with nrf:
        nrf.open_rx_pipe(0, nrf.address())  # open pipe for pairing
        pairing = True
        pairing_timeout = time.monotonic() + 1  # pair for 1 minute
        nrf.listen = True  # start listening
        while not multi_func_button.value:
            if nrf.available():
                if 0 < nrf.pipe < 5:  # if received from a bonded address
                    hid[nrf.pipe - 1].send_report(nrf.read())  # forward the data
                else:  # use pipe 0 as a cmd interface
                    nrf.read()  # discard pairing request
                    # pipe 0 only open when pairing
                    # keep TX FIFO full of pairing request responses
                    nrf.load_ack(0, nvm[:4])
            if pairing and time.monotonic() >= pairing_timeout:
                nrf.close_rx_pipe(0)  # exit pairing
                pairing = False
        nrf.listen = False
    # radio goes to sleep when exiting the `with` block
    while multi_func_button.value:
        pass  # wait till the button is released

if __name__ == "__main__":
    while True:
        if multi_func_button.value:
            # if button was pressed, then initiate pairing
            host()  # conitue acting as host until button is pressed again
