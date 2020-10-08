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
"""A sniffer class to try and detect/intercept data transmit
between 2 nRF24 series (or OTA-compatible) radio transceivers.
"""
import time

class Sniffer:
    """ A class to simplify detection or "sniffing" of RF signals/transmissions.

    :param ~circuitpython_nrf24l01.rf24.RF24 nrf24: The instantiated object of the nRF24L01
        transceiver used to detect OTA transmissions. Configuration of the nRF24L01 attributes
        is done directly with this object.
    """
    def __init__(self, nrf24):
        self.radio = nrf24

    def find_channel(self, wait_time=5):
        """This function scans all 125 channels for the presence of a RF
        transmission. If a transmission is detected, the channel is
        printed, and the scanning process continues until all available channels are checked.

        :param int wait_time: The amount of seconds that the scanning process waits at most per
            channel for signal detection. Defaults to 5 seconds.
        """
        for chnl in range(0, 125):
            self.radio.listen = True
            found_signal = False
            self.radio.channel = chnl
            timeout = time.monotonic() + wait_time # listen for x seconds
            while time.monotonic() <= timeout and not found_signal:
                if self.radio.rpd:
                    found_signal = True
            if found_signal:
                print("found signal on channel", chnl)
            self.radio.listen = False

    def find_address(self, wait_time=1):
        """This function sequentially scans all permutations of RF addresses for reception of a
        valid packet. If a valid packet is received, then the payload and address is printed.

        :param int wait_time: The number of seconds to wait per each 6 permutations of addresses.

        .. important:: Please keep in mind that a packet is only validated if certain attributes
            match the transmitting nRF24L01's attributes. These attributes include

                - `address_length`
                - :py:attr:`~circuitpython_nrf24l01.rf24.RF24.channel`
                - `data_rate`
                - `crc`
                - `dynamic_payloads`
                - :py:attr:`~circuitpython_nrf24l01.rf24.RF24.payload_length`
                  (only if `dynamic_payloads` is `False`)
                - `auto_ack`,
                - `ack` (only if `auto_ack` is `True`)

        .. warning:: This process can take A VERY LONG TIME as the number of possible permutations
            = 2 ^ (`address_length` * 8). All 6 data pipes are used to
            expedite the process.
        """
        length = self.radio.address_length
        for major in range(0, 256, 6): # [0,255] in increments of 6
            for minor in range(2 ** ((length - 1) * 8)):
                self.radio.listen = False
                # [0, 2 to the power of (number of bits in (total - 1) bytes]
                # convert minor address part from int to bytearray w/o using struct
                base_minor = b''
                for byte_pos in range(length - 2, -1, -1):
                    base_minor += bytes([(minor & (0xff << (byte_pos * 8))) >> byte_pos * 8])
                print("testing address minor", hex(minor), "major", hex(major))
                self._set_address_range(major, base_minor)
                self.radio.listen = True
                # wait for reception
                timeout = time.monotonic() + wait_time
                while time.monotonic() <= timeout:
                    while self.radio.any():
                        pl_origin = self.radio.address(self.radio.pipes())
                        print("payload from address", pl_origin, "=", self.radio.recv())

    def _set_address_range(self, base_major, base_minor):
        """ sets addresses to all 6 data pipes based on major (`int`) and minor (`bytearray`)
        starting points """
        for i in range(6):
            self.radio.open_rx_pipe(i, bytes([base_major + i]) + base_minor)
