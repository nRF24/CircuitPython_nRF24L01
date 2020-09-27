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
from os import urandom


def swap_bits(original):
    """reverses the bit order into LSbit to MSBit in a single byte.

    :returns:
        An `int` containing the byte whose bits go from LSBit to MSBit
        compared to the value passed to the ``original`` parameter.
    :param int original: This should be a single unsigned byte, meaning the
        parameters value can only range from 0 to 255.
    """
    original &= 0xFF
    reverse = 0
    for _ in range(8):
        reverse <<= 1
        reverse |= original & 1
        original >>= 1
    return reverse


def reverse_bits(original):
    """reverses the bit the byte order into LSB to MSB

    :returns:
        A `bytearray` whose bytes still go from MSByte to LSByte, but each
        byte's bits go from LSBit to MSBit.
    :param bytearray original: The original buffer whose bits are to be
        reversed.
    """
    length = len(original) - 1
    ret = bytearray(length + 1)
    for i, byte in enumerate(original):
        ret[i] = swap_bits(byte)
    return ret


def reverse_bytes(original):
    """Reverses the byte order for all bytes passed to the ``original``
    `bytearray`"""
    result = bytearray(3)
    for i, byte in enumerate(original):
        result[len(original) - 1 - i] = byte
    return result


def add_chunk(data_type, buf):
    """containerize a chunk of data according to BLE specs.
    This chunk makes up a part of the advertising payload."""
    # container = 1 Byte info about container length
    #             1 Byte info describing datatype
    #             X bytes holding the data
    return bytearray([len(buf) + 1, data_type & 0xFF]) + buf


def make_payload(mac, name, payload):
    """assemble the entire packet to be transmitted as a payload."""
    # data is ordered like so:
    # 1 byte PDU type (always 0x42)
    # 1 byte payload size
    # 6 byte random mac address
    # 21 bytes of containerized data including descriptor and name
    # 3 bytes for CRC24
    pl_size = 9 + (len(name) + 2 if name is not None else 0) + len(payload)
    buf = bytes([0x42, pl_size]) + mac  # header
    buf += add_chunk(1, b"\x05")  # device descriptor
    if name is not None:
        buf += add_chunk(0x09, name)  # device name
    return buf + payload + crc24_ble(buf + payload)


def ble_whitening(data, ble_channel):
    """for "whiten"ing the BLE packet data according to expected parameters"""
    data = bytearray(data)
    coef = ble_channel | 0x40
    for i, byte in enumerate(data):  # for every byte
        res = 0
        mask = 1
        for _ in range(8):
            if coef & 1:
                coef ^= 0x88
                byte ^= mask
            mask <<= 1
            coef >>= 1
        data[i] = byte ^ res
    return data


def crc24_ble(data, deg_poly=0x65B, init_val=0x555555):
    """Calculates a checksum of various sized buffers

    :param bytearray data: This `bytearray` of data to be uncorrupted.
    :param int deg_poly: A preset "degree polynomial" in which each bit represents a degree who's
        coefficient is 1.
    :param int init_val: This will be the initial value that the checksum will use while shifting in
        the buffer data.
    :returns: A 24-bit `bytearray` representing the checksum of the data.
    """
    crc = init_val
    for byte in data:
        crc ^= (swap_bits(byte) << 16)
        for _ in range(8):
            if crc & 0x800000:
                crc = (crc << 1) ^ deg_poly
            else:
                crc <<= 1
        crc &= 0xFFFFFF
    return reverse_bits((crc).to_bytes(3, "big"))

BLE_FREQ = (2, 26, 80)
""" BLE channel number is different from the nRF channel number.
These are the predefined channels used.
- nRF channel 2  == BLE channel 37
- nRF channel 26 == BLE channel 38
- nRF channel 80 == BLE channel 39
"""


class FakeBLE:
    """Per the limitations of this technique, only `RF24.pa_level` is
    available for configuration when advertising BLE data.

    :param ~circuitpython_nrf24l01.RF24 nrf: The object for the nRF24L01
        transceiver to use for fake BLE advertisements.
    :param bytearray name: The BLE device name to be advertised with the
        payload.
    """

    def __init__(self, nrf, name=None):
        self._device = nrf
        self._chan = 0
        self._ble_name = None
        self.name = name
        self.mac = None
        with self:
            self._device.open_rx_pipe(0, b"\x71\x91\x7D\x6B")
            self._device.open_tx_pipe(b"\x71\x91\x7D\x6B")
        # b'\x8E\x89\xBE\xD6' = proper address for BLE advertisments
        # with bits and bytes reversed address is b'\x6B\x7D\x91\x71'

    def __enter__(self):
        self._device.address_length = 4
        self._device.dynamic_payloads = False
        self._device.auto_ack = False
        self._device.crc = 0
        self._device.arc = 0
        self._device.power = 1
        self._device.payload_length = 32
        return self

    def __exit__(self, *exc):
        self._device.power = 0
        return False

    @property
    def mac(self):
        """This attribute returns a 6-byte buffer that is used as the
        arbitrary mac address of the BLE device being emulated. You can set
        this attribute using a 6-byte `int` or `bytearray`. If this is set to
        `None`, then a random 6-byte address is generated.
        """
        return self._mac

    @mac.setter
    def mac(self, address):
        if address is None:
            self._mac = urandom(6)
        if isinstance(address, int):  # assume its a 6-byte int
            self._mac = (address).to_bytes(6, "little")
        elif isinstance(address, (bytearray, bytes)):
            self._mac = address
        if len(self._mac) < 6:
            self._mac += urandom(6 - len(self._mac))

    @property
    def name(self):
        """The broadcasted BLE name of the nRF24L01. This is not required. In
        fact setting this attribute will subtract from the available payload
        length (in bytes). Set this attribute to `None` to disable advertising the device name

            * payload_length has a maximum of 21 bytes when NOT broadcasting a
              name for itself.
            * payload_length has a maximum of [19 - length of name] bytes when
              broadcasting a name for itself.
        """
        return self._ble_name

    @name.setter
    def name(self, n):
        self._ble_name = n

    def hop_channel(self):
        """trigger an automatic change of BLE compliant channels."""
        self._chan += 1
        if self._chan > 2:
            self._chan = 0
        self._device.channel = BLE_FREQ[self._chan]

    def advertise(self, buf, data_type=0xFF):
        """This blocking function is used to transmit a payload.

        :returns: Nothing as every transmission will register as a success under these required
            settings.

        :param bytearray buf: The payload to transmit. This bytearray must have
            a length greater than 0 and less than 20, otherwise a `ValueError`
            exception is thrown. This can also be a list or tuple of payloads
            (`bytearray`); in which case, all items in the list/tuple are
            processed for consecutive transmissions.

        .. note:: If the name of the emulated BLE device is also to be
            broadcast, then the 'name' attribute should be set prior to calling
            `advertise()`.
        """
        if len(buf) > (21 - len(self.name)):
            raise ValueError(
                "buf must have a length less than {}".format(21 - len(self.name))
            )
        payload = make_payload(self._mac, self.name, (add_chunk(data_type, buf) if buf else b''))
        self.hop_channel()
        # self._device.payload_length = [len(payload)] * 2
        rev_whiten_pl = reverse_bits(ble_whitening(payload, self._chan + 37))
        print("transmitting \n{}\nas\n{}".format(payload, rev_whiten_pl))
        self._device.send(rev_whiten_pl)
