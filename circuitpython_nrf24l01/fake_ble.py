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
"""This module uses the `RF24` class to make the nRF24L01 imitate a
Bluetooth-Low-Emissions (BLE) beacon. A BLE beacon can send (referred to as
advertise) data to any BLE compatible device (ie smart devices with Bluetooth
4.0 or later) that is listening.

Original research was done by `Dmitry Grinberg and his write-up (including C
source code) can be found here
<http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_
As this technique can prove invaluable in certain project designs, the code
here is simply ported to work on CircuitPython.
"""
from os import urandom
import struct


def swap_bits(original):
    """reverses the bit order for a single byte.

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
    """reverses the bit order into LSBit to MSBit.

    :returns:
        A `bytearray` whose bytes still go from MSByte to LSByte, but each
        byte's bits go from LSBit to MSBit.
    :param bytearray,bytes original: The original buffer whose bits are to be
        reversed.
    """
    length = len(original) - 1
    ret = bytearray(length + 1)
    for i, byte in enumerate(original):
        ret[i] = swap_bits(byte)
    return ret


def chunk(buf, data_type=0x16):
    """containerize a chunk of data according to BLE specifications.
    This chunk makes up a part of the advertising payload.

    :param bytearray,bytes buf: The actual data contained in the chunk.
    :param int data_type: the type of data contained in the chunk. This is a
        predefined number according to BLE specifications.

    .. important:: This function is called internally, but can also be used
        to containerize multiple types of data in a single payload.
        Broadcasting multiple types of data may require the `FakeBLE.name`
        be set to `None` for reasons about the payload size limitations due
        to using a nRf24L01 as a BLE beacon.
    """
    # container = 1 Byte info about container length
    #             1 Byte info describing datatype
    #             X bytes holding the data
    return bytearray([len(buf) + 1, data_type & 0xFF]) + buf


def crc24_ble(data, deg_poly=0x65B, init_val=0x555555):
    """Calculates a checksum of various sized buffers. this is exposed for
    convenience.

    :param bytearray data: This `bytearray` of data to be uncorrupted.
    :param int deg_poly: A preset "degree polynomial" in which each bit
        represents a degree who's coefficient is 1. BLE specfications require
        ``0x00065b`` (default value).
    :param int init_val: This will be the initial value that the checksum
        will use while shifting in the buffer data. BLE specfications require
        ``0x555555`` (default value).
    :returns: A 24-bit `bytearray` representing the checksum of the data (in
        proper little endian).
    """
    crc = init_val
    for byte in data:
        crc ^= swap_bits(byte) << 16
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

* nRF channel 2  == BLE channel 37
* nRF channel 26 == BLE channel 38
* nRF channel 80 == BLE channel 39
"""


class FakeBLE:
    """Per the limitations of this technique, only `RF24.pa_level` is
    available for configuration when advertising BLE data.

    :param ~circuitpython_nrf24l01.rf24.RF24 nrf: The object for the nRF24L01
        transceiver to use for fake BLE advertisements.
    """

    def __init__(self, nrf):
        self._device = nrf
        self._chan = 0
        self._to_iphone = 0x40
        self._show_dbm = False
        self._ble_name = None
        self._mac = urandom(6)
        with self:
            self._device.flush_rx()

    def __enter__(self):
        self._device.address_length = 4
        self._device.dynamic_payloads = False
        self._device.auto_ack = False
        self._device.crc = 0
        self._device.arc = 0
        self._device.power = 1
        self._device.payload_length = [32, 32]
        # b"\x8E\x89\xBE\xD6" = proper address for BLE advertisments
        # with bits reversed address is b"\x71\x91\x7D\x6B"
        self._device.open_rx_pipe(0, b"\x71\x91\x7D\x6B")
        self._device.open_tx_pipe(b"\x71\x91\x7D\x6B")
        return self

    def __exit__(self, *exc):
        self._show_dbm = False
        self._ble_name = None
        self._device.power = 0
        return False

    @property
    def to_iphone(self):
        """A `bool` to specify if advertisements should be compatible with
        the iPhone. A value of `False` should still be compatible with other
        Apple devices. Testing with this attribute as `False` showed
        compatibility with a Mac desktop."""
        return self._to_iphone == 0x40

    @to_iphone.setter
    def to_iphone(self, enable):
        self._to_iphone = 0x40 if enable else 0x42

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
        if n is not None:
            if not isinstance(n, (bytes, bytearray)):
                raise ValueError("name must be a bytearray or bytes object.")
            if len(n) > (21 - self._show_dbm * 3):
                raise ValueError("name length exceeds maximum.")
        self._ble_name = n

    @property
    def show_pa_level(self):
        """If this attribute is `True`, the payload will automatically include
        the nRF24L01's pa_level in the advertisement. The default value of
        `False` will exclude this optional information.

        .. note:: This information takes up an extra 3 bytes, and is really
            only useful for some applications to calculate proximity to the
            nRF24L01 transceiver.
        """
        return bool(self._show_dbm)

    @show_pa_level.setter
    def show_pa_level(self, enable):
        if enable and len(self.name) > 18:
            raise ValueError("there is not enough room to show the pa_level.")
        self._show_dbm = bool(enable)

    def hop_channel(self):
        """Trigger an automatic change of BLE compliant channels."""
        self._chan += 1
        if self._chan > 2:
            self._chan = 0
        self._device.channel = BLE_FREQ[self._chan]

    def whiten(self, data):
        """Whitening the BLE packet data ensures there's no long repeatition
        of bits. This is done according to BLE specifications.

        :param bytearray data: The packet to whiten.
        :returns: A `bytearray` of the ``data`` with the whitening algorythm
            applied.

        .. warning:: This function uses the current channel being used as a
            base case for the whitening coefficient. Do not call
            `hop_channel()` before using this function to de-whiten received
            payloads (which isn't officially supported yet). Note that
            `advertise()` uses this function internally to prevent such
            improper usage.
        """
        data = bytearray(data)
        coef = (self._chan + 37) | 0x40
        for i, byte in enumerate(data):
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

    def _make_payload(self, payload):
        """assemble the entire packet to be transmitted as a payload."""
        # data is ordered like so:
        # 1 byte PDU type (always 0x42)
        # 1 byte payload size
        # 6 byte random mac address
        # 21 bytes of containerized data including descriptor and name
        # 3 bytes for CRC24
        name_length = (len(self.name) + 2) if self.name is not None else 0
        if len(payload) > (21 - name_length - self._show_dbm * 3):
            raise ValueError(
                "Payload exceeds maximum size. Configuration allows "
                "{} bytes".format(21 - name_length - self._show_dbm * 3)
            )
        pl_size = 9 + len(payload) + name_length + self._show_dbm * 3
        buf = bytes([self._to_iphone, pl_size]) + self.mac  # header
        buf += chunk(b"\x05", 1)  # device descriptor
        pa_level = b""
        if self._show_dbm:
            pa_level = chunk(struct.pack(">b", self._device.pa_level), 0x0A)
        buf += pa_level
        if name_length:
            buf += chunk(self.name, 0x09)  # device name
        buf += payload
        buf += crc24_ble(buf)
        # print("Payload size =", len(buf))
        return buf

    def advertise(self, buf=b"", data_type=0xFF):
        """This function is used to broadcast a payload.

        :returns: Nothing as every transmission will register as a success
            under the required settings for BLE beacons.

        :param bytearray buf: The payload to transmit. This bytearray must have
            a length greater than 0 and less than 20, otherwise a `ValueError`
            exception is thrown. This can also be a list or tuple of payloads
            (`bytearray`); in which case, all items in the list/tuple are
            processed for consecutive transmissions.

        .. note:: If the name of the emulated BLE device is also to be
            broadcast, then the 'name' attribute should be set prior to calling
            `advertise()`.
        """
        if not isinstance(buf, (bytearray, bytes, list, tuple)):
            raise ValueError("buffer is an invalid format")
        payload = b""
        if isinstance(buf, (list, tuple)):
            for b in buf:
                payload += b
        else:
            payload = chunk(buf, data_type) if buf else b""
        payload = self._make_payload(payload)
        self._device.send(reverse_bits(self.whiten(payload)))


class ServiceData:
    """An abstract helper class to package specific service data using
    Bluetooth SIG defined 16-bit UUID flags to describe the data type.

    :param int type_t: The 16-bit "assigned number" defined by the
        Bluetooth SIG to describe the service data. This parameter is
        required.
    """

    def __init__(self, type_t):
        self._type = struct.pack("<H", type_t)
        self._data = b""

    @property
    def data(self):
        """The service's data. This is a `bytearray`, and its format is
        defined by Bluetooth Service Specifications (and GATT supplemental
        specifications)."""
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def buffer(self):
        """Get the representation of the instantiated object as an
        immutable `bytes` object (read-only)."""
        return bytes(self._type + self.data)

    def __len__(self):
        return len(self._type) + len(self.data)


class TemperatureServiceData(ServiceData):
    """This derivitve of the `ServiceData` class can be used to represent
    temperature data values as a `float` value."""

    def __init__(self):
        super().__init__(0x1809)

    @ServiceData.data.setter
    def data(self, value):
        # the first byte is the base 10 exponent = -2
        # the last 3 bytes are the mantissa
        value = struct.pack("<i", int(value * 100) & 0xFFFFFF)
        self._data = value[:3] + bytes([0xFE])


class BatteryServiceData(ServiceData):
    """This derivitve of the `ServiceData` class can be used to represent
    battery charge percentage as a byte value."""

    def __init__(self):
        super().__init__(0x180F)

    @ServiceData.data.setter
    def data(self, value):
        self._data = struct.pack(">B", value)
