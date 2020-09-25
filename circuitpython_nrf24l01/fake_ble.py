# The MIT License (MIT)
#
# Copyright (c) 2019 Brendan Doherty
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
This module uses the RF24 module to make the nRF24L01 imitate a Bluetooth-Low-Emissions (BLE)
beacon. A BLE beacon can send (referred to as advertise) data to any BLE compatible device
(ie smart devices with Bluetooth 4.0 or later) that is listening.

Original research was done by `Dmitry Grinberg and his write-up (including C source code) can be
found here <http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_  As
this technique can prove invaluable in certain project designs, the code here is simply ported to
work on CircuitPython.

.. important:: Because the nRF24L01 wasn't designed for BLE advertising, it has some limitations
    that helps to be aware of.

    1. the maximum payload length is shortened to 19 bytes
    2. the channels that BLE use are limited to the following three: 2.402 GHz, 2.426 GHz,
       and 2.480 GHz
    3. CRC is disabled in the nRF24L01 firmware as BLE requires 3 bytes and nRF24L01 only handles
       2. Thus we have augmented the required 3 bytes of CRC into the payload.
    4. address length of BLE packet only uses 4 bytes, so we have set that acccordingly.
    5. the automatic acknowledgment feature of the nRF24L01 is useless when tranmitting to BLE
       devices, thus it is disabled as well as automatic re-transmit and custom ACK payloads
       (both depend on the automatic acknowledgments feature)
    6. the dynamic payloads feature of the nRF24L01 isn't compatible with BLE specifications.
       Thus we have disabled it in the nRF24L01 firmware and incorporated dynamic payloads
       properly into he payload data
    7. BLE specifications only allow using 1 Mbps RF data rate, so that too has been hard coded.
    8. both the "on data sent" & "on data ready" events control the interrupt (IRQ) pin; the
       other event, "on data fail", is ignored because it will never get thrown with "auto_ack"
       off. However the interrupt settings can be modified AFTER instantiation
"""
from .data_manip import crc32, swap_bits, reverse_bits

def _ble_whitening(data, whiten_coef):
    """for "whiten"ing the BLE packet data according to expected parameters"""
    # uint8_t  m;
    # while(len--){
    #     for(m = 1; m; m <<= 1){
    #         if(whitenCoeff & 0x80){
    #             whitenCoeff ^= 0x11;
    #             (*data) ^= m;
    #         }
    #         whitenCoeff <<= 1;
    #     }
    #     data++;
    result = b""
    for byte in data:  # for every byte
        for i in range(8):
            if whiten_coef & 0x80:
                whiten_coef ^= 0x11
                byte ^= 1 << i
            whiten_coef <<= 1
        result += bytes([byte])
    return result


class FakeBLE:
    """Per the limitations of this technique, only power amplifier level is available for
    configuration when advertising BLE data.

    :param ~circuitpython_nrf24l01 nrf: The object for the nRF24L01 transceiver to use
        for fake BLE advertisements.
    :param bytearray name: The BLE device name to be advertised with the payload.
    """

    def __init__(self, nrf, name=None):
        self._device = nrf
        self._device.address_length = 4
        self._device.dynamic_payloads = False
        self._device.auto_ack = False
        self._device.crc = 0
        self._device.arc = 0
        self._device.irq_df = False
        self._device.irq_dr = False
        self._device.irq_ds = True
        self._chan = 0
        self._ble_name = None
        self.name = name
        self._device.open_tx_pipe(reverse_bits(b"\x8E\x89\xBE\xD6"))
        # b'\x8E\x89\xBE\xD6' = proper address for BLE advertisments

    def __enter__(self):
        return self._device.__enter__()

    def __exit(self, *exc):
        return self._device.__exit__(exc)

    @property
    def name(self):
        """Represents the emulated BLE device name during braodcasts. This must
        be a buffer protocol object (`bytearray`) , and can be any length (less
        than 14) of UTF-8 freindly characters. Set this to `None` to disable
        advertising a BLE device name.

        .. note:: the BLE device's name will occupy the same space as your TX
            data. While space is limited to 32 bytes on the nRF24L01, actual
            usable BLE TX data = 16 - (name length + 2). The other 16 bytes
            available on the nRF24L01 TX FIFO buffer are reserved for the
            [arbitrary] MAC address and other BLE related stuff.
        """
        return self._ble_name[2:] if self._ble_name is not None else None

    @name.setter
    def name(self, n):
        """The broadcasted BLE name of the nRF24L01. This is not required. In
        fact setting this attribute will subtract from the available payload
        length (in bytes).

            * payload_length has a maximum of 19 bytes when NOT broadcasting a
              name for itself.
            * payload_length has a maximum of (17 - length of name) bytes when
              broadcasting a name for itself.
        """
        if (
            n is not None and 1 <= len(n) <= 12
        ):  # max defined by 1 byte payload data requisite
            self._ble_name = bytes([len(n) + 1]) + b"\x08" + n
        else:
            self._ble_name = None  # name will not be advertised

    def _chan_hop(self):
        # NOTE BLE channel number is different from the nRF channel number.
        #     - nRF channel 2  == BLE channel 37
        #     - nRF channel 26 == BLE channel 38
        #     - nRF channel 80 == BLE channel 39
        self._chan = (self._chan + 1) if (self._chan + 1) < 3 else 0
        self._device.channel = 26 if self._chan == 1 else (80 if self._chan == 2 else 2)

    def advertise(self, buf):
        """This blocking function is used to transmit a payload.

        :returns: Nothing as every transmission will register as a success under these required
            settings.

        :param bytearray buf: The payload to transmit. This bytearray must have
            a length greater than 0 and less than 20, otherwise a `ValueError`
            exception is thrown. This can also be a list or tuple of payloads
            (`bytearray`); in which case, all items in the list/tuple are
            processed for consecutive transmissions.

            - If the `dynamic_payloads` attribute is disabled and this
              bytearray's length is less than the `payload_length` attribute,
              then this bytearray is padded with zeros until its length is
              equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this
              bytearray's length is greater than `payload_length` attribute,
              then this bytearray's length is truncated to equal the
              `payload_length` attribute.

        .. note:: If the name of the emulated BLE device is also to be
            broadcast, then the 'name' attribute should be set prior to calling
            `advertise()`.
        """
        # max payload_length = 32 - 14(header, MAC, & CRC) - 2(container header) - 3(BLE flags)
        #                    = 13 - (BLE name length + 2 if any)
        name_len = len(self._ble_name) if self._ble_name is not None else 0
        if not buf or len(buf) > (13 - name_len):
            raise ValueError(
                "buf must have a length in range [1, {}]".format(13 - name_len)
            )
        # BLE payload =
        #   header(1) + payload length(1) + MAC address(6) + containers + CRC(3) bytes
        # header == PDU type, given MAC address is random/arbitrary
        #               type == 0x42 for Android or 0x40 for iPhone
        # containers (in bytes) = length(1) + type(1) + data
        # the 1 byte about container's length excludes only itself
        payload = b"\x42"  # init a temp payload buffer with header type byte
        # to avoid padding when dynamic_payloads is disabled, set payload_length attribute
        self._device.payload_length = len(buf) + 16 + name_len
        # payload length excludes the header, itself, and crc lengths
        payload += bytes([self._device.payload_length - 5])
        payload += b"\x11\x22\x33\x44\x55\x66"  # a bogus MAC address
        # payload will have at least 2 containers:
        # 3 bytes of flags (required for BLE discoverable), & at least (1+2) byte of data
        payload += b"\x02\x01\x06"  # BLE flags for discoverability and non-pairable etc
        # payload will also have to fit the optional BLE device name as
        # a seperate container ([name length + 2] bytes)
        if self._ble_name is not None:
            payload += self._ble_name
        payload += bytes([len(buf) + 1]) + b"\xFF" + buf  # append the data container
        # crc is generated from b'\x55\x55\x55' about everything except itself
        payload += crc32(payload)
        self._chan_hop()  # cycle to next BLE channel per specs
        # the whiten_coef value we need is the BLE channel (37,38, or 39) left shifted one
        whiten_coef = 37 + self._chan
        whiten_coef = swap_bits(whiten_coef) | 2
        rev_whiten_pl = reverse_bits(_ble_whitening(payload, whiten_coef))
        print("transmitting {} as {}".format(payload, rev_whiten_pl))
        self._device.send(rev_whiten_pl)
