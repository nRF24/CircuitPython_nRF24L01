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
from struct import pack  # , unpack

USE_NVM = True
try:
    from microcontroller import nvm
except ImportError:
    USE_NVM = False
except NotImplementedError:
    USE_NVM = False

# from .rf24 import RF24

# Logitech unifying specific data
PAIRING_ADDRESS = b"\x75\xA5\xDC\x0A\xBB"  # REVERSED 0xBB0ADCA575
# Pre-defined pairing packets
PAIRING_PACKETS = [
    # REVERSED 0x155F01845E3AA25708102504000147000000000001EC
    b"\xec\x01\x00\x00\x00\x00\x00G\x01\x00\x04%\x10\x08W\xa2:^\x84\x01_\x15"
    # REVERSED 0x1540018426
    b"&\x84\x01@\x15",
    # REVERSED 0x005F0200000000588A51EA0107000001000000000079
    b"y\x00\x00\x00\x00\x00\x01\x00\x00\x07\x01\xeaQ\x8AX\x00\x00\x00\x00\x02_\x00",
    # REVERSED 0x00400201BD
    b"\xBD\x01\x02@\x00",
    # REVERSED 0x005F03010004 + "M510" + 0x0000000000000000000000B6
    b"\xB6\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00015M\x04\x00\x01\x03_\x00",
    # REVERSED 0x005F03010f
    b"\x0F\x01\x03_\x00",
    # REVERSED 0x000F06010000000000EA + 0x00 * 12
    b"\x00" * 12 + b"\xea\x00\x00\x00\x00\x00\x01\x06\x0f\x00",
]
# End of pre-defined pairing packets


class LogitechMouse:
    """A class to emulate the behavior of a Logitech-branded wireless mouse
    using the nRF24L01 transceiver and a Logitech Unifying USB Receiver.

    :param ~circuitpython_nrf24l01.rf24.RF24 nrf: the instantiated object of
        the nRF24L01 radio to be used.
    """

    def __init__(self, nrf):
        self._radio = nrf
        # get address to a specific Unifying dongle after pairing success
        self.bonded_address = self._radio.address()
        """The unique address to a particular Logitech Unifying receiver is
        fetched from the nRF24L01's ``TX_ADDR`` register. This assumes pairing
        success prior to instantiation, and the nRF24L01 hasn't been used for
        other applications since, and the nRF24L01 has not been powered down
        (TX address resets in Power-on-Reset).

        .. note:: Write access to circuitpython's FS (file system) is restricted
            `unless you modify boot.py <https://learn.adafruit.com/
            cpu-temperature-logging-with-circuit-python/
            writing-to-the-filesystem>`_ to re-mount the FS with write
            permission. See also important note in `pair()`.
        """
        with self:
            self._radio.flush_rx()
            self._radio.clear_status_flags()
        if USE_NVM:
            self.bonded_address = nvm[:5]
        else:
            try:
                with open("logitech unify address.txt", "rb") as file:
                    self.bonded_address = file.readline()
            except OSError:
                self.bonded_address = b"\xFF" * 5
        if self.bonded_address == b"\xFF" * 5:
            self.pair()

    def __enter__(self):
        self._radio.address_length = 5
        self._radio.data_rate = 2
        self._radio.channel = 5
        self._radio.ack = True  # enables dynamic_payloads and auto_ack
        self._radio.ard = 1000  # delay 1000 microseconds between auto-retry attempts
        self._radio.arc = 1  # auto-retry transmit 1 extra attempt
        # setting payload_length originally was needed for the nature of C++ arrays
        # the nRF24L01 never actually needs this set due to the use of ACK payloads
        self._radio.payload_length = 22
        self._radio.listen = False
        self._radio.power = True

    def __exit__(self, *exc):
        self._radio.power = False
        return False

    def _set_addr(self, addr):
        self._radio.listen = False
        self._radio.open_tx_pipe(addr)
        self._radio.open_rx_pipe(1, addr)
        self._radio.open_rx_pipe(2, b"\x00")

    def _pairing_step(self, index_long, index_short=None,
                      attempts=255, ack_payload=None):
        keep_going = True
        while keep_going:
            result = False
            while attempts and not result:
                result = self._radio.send(PAIRING_PACKETS[index_long])
                if isinstance(result, bool):  # transmit failed
                    attempts -= 1
                    print("transmit pairing packet", index_long, "failed")
                elif result is None:  # transmit success , but no ACK recv'd
                    print(
                        "transmit pairing packet",
                        index_long,
                        "succeeded, but with no ACK payload",
                    )
                    result = True
                    break  # send next packet
                # else we have ACK payload, but not the one we need
                else:  # for debugging
                    print("pairing packet", index_long, "returned", result)
            if index_short is not None and attempts:
                # if pairing sequence is not on last step and attempts > 0
                result = False  # discards any ACK payload from previous packet
                while attempts and not result:
                    result = self._radio.send(PAIRING_PACKETS[index_short])
                    if isinstance(result, bool) or result is None:  # transmit failed
                        print("transmit pairing packet", index_short, "failed")
                        attempts -= 1
                    elif ack_payload is not None and result is not None:
                        # if we need the ACK payload
                        print("pairing packet", index_short, "returned", result)
                        ack_payload[0] = result  # return ACK payload by reference
                    else:  # we don't need the ACK payload
                        # we're done with this step in the sequence
                        print(
                            "pairing packet", index_short, "returned (unused)", result
                        )
                        result = True
                        keep_going = False  # exit function
            else:
                # we're already done (triggered on last step of pairing sequence)
                keep_going = False
        return attempts

    def pair(self, retries=255):
        """Initiate pairing sequence with a Logitech Unifying receiver.
        Remember to put the Unifying receiver in discovery/pairing mode using
        Logitech's Unifying software!

        .. important:: The unique address assigned to a particular Unifying
            device would normally be saved to an Arduino's EEPROM to keep said
            address consistent when power supply is disconnected. If this
            address is lost, then you need to re-pair with the Unifying
            receiver. However, the CircuitPython core prohibits write access
            to the internal FS (File System) due to unpredictable behavior
            when USB also has simultaneous write access.

        .. tip:: One could alter ``boot.py`` to load the FS with write
            access when a dedicated pin is tied to ground. Theoretically,
            one could tie the dedicated pin to the center of a voltage
            divider circuit (2 resistors of the same resistance value in
            series) that starts from USB pin and ends on GND (ground),
            thus the dedicated pin will only read LOW when the USB
            connection isn't used (meaning the MCU is being powered by the
            BAT pin). None of this has been confirmed, and it assumes the
            USB voltage doesn't dip below 5V.
        """
        # length is arbitrary because recv() returns full ack payload when
        # dynamic_paylaods == True (needed for ACK payloads)
        # buffer to save ACK payload (as a list obj for passing by reference)
        ack_buf = [b"\x00"]
        attempts = self._pairing_step(
            0, index_short=1, ack_payload=ack_buf, attempts=retries
        )
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
        self.bonded_address = b""
        for byte in ack_buf[0][2:7]:
            self.bonded_address = bytes([byte]) + self.bonded_address

        # switch to bonded address now that pairing is complete
        self._set_addr(self.bonded_address)
        return True

    def reconnect(self):
        """
        Attempts to reconnect to a bonded Unifying receiver (if said
        receiver's address is saved).
        """
        self._set_addr(self.bonded_address)
        print("TX address set to", self.bonded_address)
        if not self.pair(retries=5):
            self._set_addr(PAIRING_ADDRESS)
            return False
        return True

    # pylint: disable=too-many-arguments
    def input(self, x_move=0, y_move=0, scroll_v=0,
              scroll_h=0, left=False, right=False):
        """Sends the mouse data to the Logitech Unifying receiver

        :param int x_move: a 12 bit signed int describing the velocity of the
            mouse on the X-axis.
        :param int y_move: a 12 bit signed int describing the velocity of the
            mouse on the Y-axis.
        :param int scroll_h: a 8 bit signed int describing the velocity of
            scrolling on the X-axis.
        :param int scroll_v: a 8 bit signed int describing the velocity of
            scrolling on the Y-axis.
        :param bool left: a boolean representing the state of the left mouse
            button. `True` means the button is pressed; `False` means the
            button is not pressed.
        :param bool right: a boolean representing the state of the right mouse
            button. `True` means the button is pressed; `False` means the
            button is not pressed.

        .. note:: Extra buttons such as 'browser forward' and 'browser
            backward' are not supperted at this time.

        .. important:: All of the parameters are keyword arguments with
            defaults that resemble their idle state.
        """
        mouse_payload = b"\x00\xC2" + pack("B", (right << 1) | left)
        cursor_velocity = pack(
            "3B",
            (y_move & 0xFF0) >> 4,
            (y_move & 0xF) << 4 | (x_move & 0xF00) >> 8,
            (x_move & 0xFF),
        )
        mouse_payload += cursor_velocity + b"\x00" + pack("2b", scroll_v, scroll_h)
        checksum = 0
        for byte in mouse_payload:
            checksum += byte
        mouse_payload += bytes([(-1 * checksum) & 0xFF])
        while not self._radio.send(mouse_payload):
            # tries to send until succeeds
            # may cause infinite loop if dongle is out-of-range/obstructed/unplugged
            pass
        self._radio.flush_rx()  # dispose of ACK payload
