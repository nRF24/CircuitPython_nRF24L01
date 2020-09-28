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
This module uses the `RF24` class to make the nRF24L01 imitate a
Bluetooth-Low-Emissions (BLE) beacon. A BLE beacon can send (referred to as
advertise) data to any BLE compatible device (ie smart devices with Bluetooth
4.0 or later) that is listening.

Original research was done by `Dmitry Grinberg and his write-up (including C
source code) can be found here
<http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_
As this technique can prove invaluable in certain project designs, the code
here is simply ported to work on CircuitPython.

.. important:: Because the nRF24L01 wasn't designed for BLE advertising, it
    has some limitations that helps to be aware of.

    1. the maximum payload length is shortened to 21 bytes (when not
       broadcasting a device
       :py:attr:`~circuitpython_nrf24l01.fake_ble.FakeBLE.name`).
    2. the channels that BLE use are limited to the following three: 2.402
       GHz, 2.426 GHz, and 2.480 GHz
    3. :py:attr:`~circuitpython_nrf24l01.rf24.RF24.crc` is disabled in the
       nRF24L01 firmware as BLE requires 3 bytes
       (:py:func:`~circuitpython_nrf24l01.fake_ble.crc24_ble()`) and nRF24L01
       only handles a maximum of 2. Thus, we have appended the required 3
       bytes of CRC24 into the payload.
    4. :py:attr:`~circuitpython_nrf24l01.rf24.RF24.address_length` of BLE
       packet only uses 4 bytes, so we have set that accordingly.
    5. The :py:attr:`~circuitpython_nrf24l01.rf24.RF24.auto_ack` (automatic
       acknowledgment) feature of the nRF24L01 is useless when tranmitting to
       BLE devices, thus it is disabled as well as automatic re-transmit
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.arc`) and custom ACK
       payloads (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.ack`) which both
       depend on the automatic acknowledgments feature.
    6. The :py:attr:`~circuitpython_nrf24l01.rf24.RF24.dynamic_payloads`
       feature of the nRF24L01 isn't compatible with BLE specifications. Thus,
       we have disabled it.
    7. BLE specifications only allow using 1 Mbps RF
       :py:attr:`~circuitpython_nrf24l01.rf24.RF24.data_rate`, so that too has
       been hard coded.
    8. Only the "on data sent"
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_ds`) & "on data ready"
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_dr`) events will have
       an effect on the interrupt (IRQ) pin. The "on data fail"
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_df`), is never
       triggered because
       :py:attr:`~circuitpython_nrf24l01.rf24.RF24.auto_ack` feature is
       disabled.
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


def reverse_bytes(original):
    """Reverses the byte order for all bytes passed to the ``original``
    `bytearray` parameter."""
    result = bytearray(3)
    for i, byte in enumerate(original):
        result[len(original) - 1 - i] = byte
    return result


def chunk(buf, data_type=0x16):
    """containerize a chunk of data according to BLE specifications.
    This chunk makes up a part of the advertising payload.

    :param int data_type: the type of data contained in the chunk. This is a
        predefined number according to BLE specifications.
    :param bytearray,bytes buf: The actual data contained in the chunk.

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

* nRF channel 2  == BLE channel 37
* nRF channel 26 == BLE channel 38
* nRF channel 80 == BLE channel 39
"""

SERVICE_TYPES = {
    "Current Time": 0x1805,
    "Glucose": 0x1808,
    "Health Thermometer": 0x1809,
    "Heart Rate": 0x180D,
    "Battery": 0x180F,
    "Blood Pressure": 0x1810,
    "Location and Navigation": 0x1819,
    "Weight Scale": 0x181D,
    "Binary Sensor": 0x183B,
}
"""These are some of the common service types provided by the Bluetooth
SIG as part of the 16-bit UUID assigned numbers. There are many other options,
but due to the limitations of the nRF24L01 being used as a BLE beacon, these
would be the most useful."""


class ServiceData:
    """A helper class to package specific service data using Bluetooth SIG
    defined 16-bit UUID flags to describe the data type.

    :param int type_t: The 16-bit "assigned number" defined by the
        Bluetooth SIG to describe the service data.
    :param bytearray data: The service data. The format of the data here
        depends on the type of service being broadcast.
    """

    def __init__(self, type_t, data=b"0"):
        self._type = (type_t).to_bytes(2, "little")
        self._data = b""
        self.data = data

    @property
    def data(self):
        """The service's data. This is a `bytearray` and can have any format
        which is usually constructed by python's :py:func:`struct.pack()`"""
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def buffer(self):
        """Get the representation of the instantiated object as an
        immutable bytes object (read-only)."""
        return bytes(self._type + self.data)

    def __len__(self):
        return len(self._type) + len(self.data)


class FakeBLE:
    """Per the limitations of this technique, only `RF24.pa_level` is
    available for configuration when advertising BLE data.

    :param ~circuitpython_nrf24l01.RF24 nrf: The object for the nRF24L01
        transceiver to use for fake BLE advertisements.
    :param bytearray name: The BLE device name to be advertised with the
        payload.
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
        self._ble_name = n

    @property
    def show_pa_level(self):
        """If this attribute is `True`, the payload will automatically include
        the nRF24L01's pa_level in the advertisement. The default value of
        `False` will exclude this optional information.

        .. note:: This information takes up an extra 3 bytes, and is really
            only useful for some applications to calculate proximity of the
            nRF24L01 transceiver.
        """
        return bool(self._show_dbm)

    @show_pa_level.setter
    def show_pa_level(self, enable):
        self._show_dbm = bool(enable)

    def hop_channel(self):
        """trigger an automatic change of BLE compliant channels."""
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
                "buf must have a length less than {}".format(21 - name_length)
            )
        pl_size = 9 + len(payload) + name_length + self._show_dbm * 3
        pa_level = b""
        if self._show_dbm:
            pa_level = chunk(struct.pack(">b", self._device.pa_level), 0x0A)
        buf = bytes([self._to_iphone, pl_size]) + self.mac  # header
        buf += chunk(b"\x05", 1)  # device descriptor
        if name_length:
            buf += chunk(self.name, 0x09)  # device name
        return buf + pa_level + payload + crc24_ble(buf + pa_level + payload)

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
        self.hop_channel()
        rev_whiten_pl = reverse_bits(self.whiten(payload))
        # print("transmitting \n{}\nas\n{}".format(payload, rev_whiten_pl))
        self._device.send(rev_whiten_pl)
