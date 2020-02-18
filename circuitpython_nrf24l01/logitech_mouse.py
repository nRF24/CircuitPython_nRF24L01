# The MIT License (MIT)
#
# Copyright (c) 2020 Brendan Doherty
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
based on original work done by `Ronan Gaillard (ronan.gaillard@live.fr)
<https://github.com/ronangaillard/logitech-mouse>`_ for the Arduino platform.
"""
from struct import pack #, unpack
# from .rf24 import RF24

# Logitech unifying specific data
PAIRING_MAC_ADDRESS = b'\xBB\x0A\xDC\xA5\x75' # sufix = 'LL' from logitech-mouse.h
# Pre-defined pairing packets
PAIRING_PACKETS = [
    b'\x15\x5F\x01\x84\x5E\x3A\xA2\x57\x08\x10\x25\x04\x00\x01\x47\x00\x00\x00\x00\x00\x01\xEC',
    b'\x15\x40\x01\x84\x26',
    b'\x00\x5F\x02\x00\x00\x00\x00\x58\x8A\x51\xEA\x01\x07\x00\x00\x01\x00\x00\x00\x00\x00\x79',
    b'\x00\x40\x02\x01\xbd',
    b'\x00\x5F\x03\x01\x00\x04\x4D\x35\x31\x30\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xB6',
    b'\x00\x5F\x03\x01\x0f',
    b'\x00\x0F\x06\x01\x00\x00\x00\x00\x00\xEA']
# End of pre-defined pairing packets

class LogitechMouse:
    """A class to emulate the behavior of a Logitech-branded wireless mouse using the
    nRF24L01 transceiver and a Logitech Unifying USB Receiver.

    :param RF24 nrf24: the instantiated object of the nRF24L01 radio to be used.
    """
    def __init__(self, nrf24):
        self.radio = nrf24
        self.radio.listen = False # ensure TX mode
        self.power = False # power down nRF24L01 for configuration
        with self:
            # use the context manager to configure the radio accordingly
            self.radio.open_tx_pipe(PAIRING_MAC_ADDRESS)
            self.radio.open_rx_pipe(1, PAIRING_MAC_ADDRESS)
            # see __enter__()

    def __enter__(self):
        with self.radio as nrf:
            nrf.address_length = 5
            nrf.data_rate = 2
            nrf.channel = 5
            nrf.ack = True # enables dynamic_payloads and auto_ack
            nrf.ard = 1000 # delay 1000 microseconds between auto-retry attempts
            nrf.arc = 1 # auto-retry transmit 1 extra attempt
            nrf.payload_length = 22 # never actually used due to the use of ACK payloads

    def __exit__(self, *exc):
        return False

    def _set_addr(self, addr):
        self.radio.listen = False
        self.radio.open_tx_pipe(addr)
        self.radio.open_rx_pipe(1, addr)
        self.radio.open_rx_pipe(2, b'\x00')

    def pair(self, timeout=0):
        """initiate pairing sequence with a Logitech Unifying receiver.

        .. important:: Remember to put the Unifying receiver in discovery/pairing mode using
            Logitech's Unifying software!
        """
        #TODO

    def reconnect(self):
        """
        Attempts to reconnect to a bonded Unifying receiver (if said receiver's address is saved).
        """
        #TODO

    # pylint: disable=too-many-arguments
    def move(self,
             x_move=0, y_move=0,
             scroll_v=0, scroll_h=0,
             left_click=False, right_click=False):
        """Sends the mouse data to the Logitech Unifying receiver
        :param int x_move: a 12 bit signed int describing the velocity of the mouse on the X-axis.
        :param int y_move: a 12 bit signed int describing the velocity of the mouse on the Y-axis.
        :param int scroll_h: a 8 bit signed int describing the velocity of scrolling on the X-axis.
        :param int scroll_v: a 8 bit signed int describing the velocity of scrolling on the Y-axis.
        :param bool left_click: a boolean representing the state of the left mouse button.
            `True` means the button is pressed; `False` means the button is not pressed.
        :param bool right_click: a boolean representing the state of the right mouse button.
            `True` means the button is pressed; `False` means the button is not pressed.

        .. note:: Extra buttons such as 'browser forward' and 'browser backward' are not supperted
            at this time.

        .. important:: All of the parameters are keyword arguments with defaults that resemble
            their idle state.
        """
        mouse_payload = b'\x00\xC2' + pack('B', (right_click << 1) | left_click)
        cursor_velocity = pack('3B',
                               (y_move & 0xff0) >> 4,
                               (y_move & 0xf) << 4 | (x_move & 0xf00) >> 8,
                               (x_move & 0xff))
        mouse_payload += cursor_velocity + b'\x00' + pack('2b', scroll_v, scroll_h)
        checksum = 0
        for byte in mouse_payload:
            checksum += byte
        mouse_payload += bytes([(-1 * checksum) & 0xff])
        while not self.radio.send(mouse_payload):
            # tries to send until succeeds
            # may cause infinite loop if dongle is out-of-range/obstructed/unplugged
            pass
        self.radio.flush_rx() # dispose of ACK payload
