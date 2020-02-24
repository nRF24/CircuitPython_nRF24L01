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
PAIRING_ADDRESS = b'\xBB\x0A\xDC\xA5\x75' # sufix = 'LL' from logitech-mouse.h
# Pre-defined pairing packets
PAIRING_PACKETS = [
    b'\x15\x5F\x01\x84\x5E\x3A\xA2\x57\x08\x10\x25\x04\x00\x01\x47\x00\x00\x00\x00\x00\x01\xEC',
    b'\x15\x40\x01\x84\x26',
    b'\x00\x5F\x02\x00\x00\x00\x00\x58\x8A\x51\xEA\x01\x07\x00\x00\x01\x00\x00\x00\x00\x00\x79',
    b'\x00\x40\x02\x01\xbd',
    b'\x00\x5F\x03\x01\x00\x04M510\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xB6',
    b'\x00\x5F\x03\x01\x0f',
    b'\x00\x0F\x06\x01\x00\x00\x00\x00\x00\xEA' + b'\x00' * 12]
# End of pre-defined pairing packets

class LogitechMouse:
    """A class to emulate the behavior of a Logitech-branded wireless mouse using the
    nRF24L01 transceiver and a Logitech Unifying USB Receiver.

    :param ~circuitpython_nrf24l01.rf24.RF24 nrf24: the instantiated object of the nRF24L01
        radio to be used.
    """
    def __init__(self, nrf24):
        self.radio = nrf24
        self.radio.listen = False # ensure TX mode
        self.power = False # power down nRF24L01 for configuration

        # get address to a specific Unifying dongle after pairing success
        self.bonded_address = self.radio.address(-1)
        """The unique address to a particular Logitech Unifying receiver is fetched from
        the nRF24L01's ``TX_ADDR`` register. This assumes pairing success prior to
        instantiation and the nRF24L01 hasn't been used for other applications since.

        .. note:: Write access to circuitpython's FS (file system) is restricted
            `unless you modify boot.py <https://learn.adafruit.com/
            cpu-temperature-logging-with-circuit-python/writing-to-the-filesystem>`_ to
            re-mount the FS with write permission. See also important note in `pair()`.
        """

        # configure the radio
        self.radio.address_length = 5
        self.radio.data_rate = 2
        self.radio.channel = 5
        self.radio.ack = True # enables dynamic_payloads and auto_ack
        self.radio.ard = 1000 # delay 1000 microseconds between auto-retry attempts
        self.radio.arc = 1 # auto-retry transmit 1 extra attempt
        # setting payload_length originally was needed for the nature of C++ arrays
        # the nRF24L01 never actually needs this set due to the use of ACK payloads
        self.radio.payload_length = 22 # doesn't cost an SPI transaction

    def __enter__(self):
        with self.radio:
            pass # radio is configured with RF24.__enter__()

    def __exit__(self, *exc):
        return False

    def _set_addr(self, addr):
        self.radio.listen = False
        self.radio.open_tx_pipe(addr)
        self.radio.open_rx_pipe(1, addr)
        self.radio.open_rx_pipe(2, b'\x00' + addr[1:])

    def _pairing_step(self, index_long, index_short=None, attempts=255, ack_payload=None):
        keep_going = True
        while keep_going:
            result = False
            while attempts and not result:
                result = self.radio.send(PAIRING_PACKETS[index_long])
                if isinstance(result, bool): # transmit failed
                    attempts -= 1
                elif result is None: # transmit success , but no ACK recv'd
                    break # send next packet
                # else we have ACK payload, but not the one we need
                else: # for debugging
                    print('packet', index_long, 'returned', result)
            if index_short is not None: # if pairing sequence is not on last step
                result = False # discards any ACK payload from previous packet
                while attempts and not result:
                    result = self.radio.send(PAIRING_PACKETS[index_short])
                    if isinstance(result, bool) or result is None: # transmit failed
                        attempts -= 1
                    elif ack_payload is not None: # if we need the ACK payload
                        ack_payload[0] = result # return ACK payload by reference
                    else: # we don't need the ACK payload
                        # we're done with this step in the sequence
                        result = True
                        keep_going = False # exit function
            else:
                # we're already done (triggered on last step of pairing sequence)
                keep_going = False
        return attempts

    def pair(self):
        """Initiate pairing sequence with a Logitech Unifying receiver. Remember to put
        the Unifying receiver in discovery/pairing mode using Logitech's Unifying software!

        .. important:: The unique address assigned to a particular Unifying device would
            normally be saved to an Arduino's EEPROM to keep said address consistent when power
            supply is disconnected. If this address is lost, then you need to re-pair with the
            Unifying receiver. However, the CircuitPython core prohibits write access to the
            internal FS (File System) due to unpredictable behavior when USB also has
            simultaneous write access.

            .. tip:: One could alter ``boot.py`` to load the FS with write
                access when a dedicated pin is tied to ground. Theoretically, one could tie the
                dedicated pin to the center of a voltage divider circuit (2 resistors of the same
                resistance value in series) that starts from USB pin and ends on GND (ground), thus
                the dedicated pin will only read LOW when the USB connection isn't used (meaning
                the MCU is being powered by the BAT pin). None of this has been confirmed, and it
                assumes the USB voltage doesn't dip below 5V.
        """
        # length is arbitrary because recv() returns full ack payload when
        # dynamic_paylaods == True (needed for ACK payloads)
        ack_buf = [b'\x00'] # buffer to save ACK payload (as a list obj for passing by reference)
        attempts = self._pairing_step(0, index_short=1, ack_payload=ack_buf)
        if not attempts:
            return False

        attempts = self._pairing_step(2, index_short=3, attempts=attempts)
        if not attempts:
            return False

        attempts = self._pairing_step(4, index_short=5, attempts=attempts)
        if not attempts:
            return False

        attempts = self._pairing_step(6, attempts=attempts)
        if not attempts:
            return False

        # save bonded addresses from ack_buf
        # NOTE address is recv()'d reversed w/ 2 byte offset
        self.bonded_address = b''
        for byte in ack_buf[0][2:7]:
            self.bonded_address = bytes([byte]) + self.bonded_address

        # switch to bonded address now that pairing is complete
        self._set_addr(self.bonded_address)
        return True

    def reconnect(self):
        """
        Attempts to reconnect to a bonded Unifying receiver (if said receiver's address is saved).
        """
        self._set_addr(self.bonded_address)
        return self.pair()

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
