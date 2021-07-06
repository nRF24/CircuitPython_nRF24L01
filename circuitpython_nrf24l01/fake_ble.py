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
"""Original research was done by `Dmitry Grinberg and his write-up can be
found here
<http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_"""
from os import urandom
import struct
from micropython import const
from .rf24 import RF24


def swap_bits(original):
    """This function reverses the bit order for a single byte."""
    original &= 0xFF
    reverse = 0
    for _ in range(8):
        reverse <<= 1
        reverse |= original & 1
        original >>= 1
    return reverse


def reverse_bits(original):
    """This function reverses the bit order for an entire
    buffer protocol object."""
    ret = bytearray(len(original))
    for i, byte in enumerate(original):
        ret[i] = swap_bits(byte)
    return ret


def chunk(buf, data_type=0x16):
    """This function is used to pack data values into a block of data that
    make up part of the BLE payload per Bluetooth Core Specifications."""
    return bytearray([len(buf) + 1, data_type & 0xFF]) + buf


def crc24_ble(data, deg_poly=0x65B, init_val=0x555555):
    """This function calculates a checksum of various sized buffers."""
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
"""The BLE channel number is different from the nRF channel number."""


class QueueElement:
    """A data structure used for storing received & decoded BLE payloads in
    the `FakeBLE.rx_queue`."""

    def __init__(self):
        self.mac = None  #: The transmitting BLE device's MAC address
        self.name = None  #: The transmitting BLE device's name (if any)
        self.pa_level = None
        """The transmitting device's PA Level (if included in the received payload).

        .. note:: This value does not represent the received signal strength.
            The nRF24L01 will receive anything over a -64 dbm threshold."""
        self.data = []
        """A `list` of the transmitting device's data structures (if any).
        If an element in this `list` is not an instance (or descendant) of the
        `ServiceData` class, then it is likely a custom or user defined speification -
        in which case it will be a `bytearray` object."""


class FakeBLE(RF24):
    """A class to implement BLE advertisements using the nRF24L01."""

    def __init__(self, spi, csn, ce_pin, spi_frequency=10000000):
        super().__init__(spi, csn, ce_pin, spi_frequency=spi_frequency)
        self._curr_freq = 2
        self._show_dbm = False
        self._ble_name = None
        self._mac = urandom(6)
        self._config = self._config & 3 | 0x10  # disable CRC
        # disable auto_ack, dynamic payloads, all TX features, & auto-retry
        self._aa, self._dyn_pl, self._features, self._retry_setup = (0,) * 4
        self._addr_len = 4  # use only 4 byte address length
        self._tx_address[:4] = b"\x71\x91\x7D\x6B"
        with self:
            super().open_rx_pipe(0, b"\x71\x91\x7D\x6B\0")
        self.rx_queue = []  #: The internal queue of received BLE payloads' data.
        self.rx_cache = bytearray(0)
        """The internal cache used when validating received BLE payloads."""
        self.hop_channel()

    def __exit__(self, *exc):
        self._show_dbm = False
        self._ble_name = None
        return super().__exit__()

    @property
    def mac(self):
        """This attribute returns a 6-byte buffer that is used as the
        arbitrary mac address of the BLE device being emulated."""
        return self._mac

    @mac.setter
    def mac(self, address):
        if address is None:
            self._mac = urandom(6)
        if isinstance(address, int):
            self._mac = (address).to_bytes(6, "little")
        elif isinstance(address, (bytearray, bytes)):
            self._mac = address
        if len(self._mac) < 6:
            self._mac += urandom(6 - len(self._mac))

    @property
    def name(self):
        """The broadcasted BLE name of the nRF24L01."""
        return self._ble_name

    @name.setter
    def name(self, _name):
        if _name is not None:
            if not isinstance(_name, (bytes, bytearray)):
                raise ValueError("name must be a bytearray or bytes object.")
            if len(_name) > (18 - self._show_dbm * 3):
                raise ValueError("name length exceeds maximum.")
        self._ble_name = _name

    @property
    def show_pa_level(self):
        """If this attribute is `True`, the payload will automatically include
        the nRF24L01's :attr:`~circuitpython_nrf24l01.rf24.RF24.pa_level` in the
        advertisement."""
        return bool(self._show_dbm)

    @show_pa_level.setter
    def show_pa_level(self, enable):
        if enable and len(self.name) > 16:
            raise ValueError("there is not enough room to show the pa_level.")
        self._show_dbm = bool(enable)

    def hop_channel(self):
        """Trigger an automatic change of BLE compliant channels."""
        self._curr_freq += 1 if self._curr_freq < 2 else -2
        self.channel = BLE_FREQ[self._curr_freq]

    def whiten(self, data):
        """Whitening the BLE packet data ensures there's no long repetition
        of bits."""
        data, coef = (bytearray(data), (self._curr_freq + 37) | 0x40)
        # print("buffer: 0x{}".format(address_repr(data)))
        # print("Whiten Coef: {} on channel {}".format(
        #     hex(coef), BLE_FREQ[self._curr_freq]
        # ))
        for i, byte in enumerate(data):
            res, mask = (0, 1)
            for _ in range(8):
                if coef & 1:
                    coef ^= 0x88
                    byte ^= mask
                mask <<= 1
                coef >>= 1
            data[i] = byte ^ res
        # print("whitened: 0x{}".format(address_repr(data)))
        return data

    def _make_payload(self, payload):
        """Assemble the entire packet to be transmitted as a payload."""
        if self.len_available(payload) < 0:
            raise ValueError(
                "Payload length exceeds maximum buffer size by "
                "{} bytes".format(abs(self.len_available(payload)))
            )
        name_length = (len(self.name) + 2) if self.name is not None else 0
        pl_size = 9 + len(payload) + name_length + self._show_dbm * 3
        buf = bytes([0x42, pl_size]) + self.mac
        buf += chunk(b"\x05", 1)
        pa_level = b""
        if self._show_dbm:
            pa_level = chunk(struct.pack(">b", self.pa_level), 0x0A)
        buf += pa_level
        if name_length:
            buf += chunk(self.name, 0x08)
        buf += payload
        # print("payload: 0x{} +CRC24: 0x{}".format(
        #     address_repr(buf), address_repr(crc24_ble(buf))
        # ))
        buf += crc24_ble(buf)
        return buf

    def len_available(self, hypothetical=b""):
        """This function will calculates how much length (in bytes) is
        available in the next payload."""
        name_length = (len(self.name) + 2) if self.name is not None else 0
        return 18 - name_length - self._show_dbm * 3 - len(hypothetical)

    def advertise(self, buf=b"", data_type=0xFF):
        """This blocking function is used to broadcast a payload."""
        if not isinstance(buf, (bytearray, bytes, list, tuple)):
            raise ValueError("buffer is an invalid format")
        payload = b""
        if isinstance(buf, (list, tuple)):
            for b in buf:
                payload += b
        else:
            payload = chunk(buf, data_type) if buf else b""
        payload = self.whiten(self._make_payload(payload))
        # print("original: 0x{}".format(address_repr(payload)))
        # print("reversed: 0x{}".format(address_repr(reverse_bits(payload))))
        self.send(reverse_bits(payload))

    def print_details(self, dump_pipes=False):
        super().print_details(dump_pipes)
        print("BLE device name___________{}".format(str(self.name)))
        print("Broadcasting PA Level_____{}".format(self.show_pa_level))

    @RF24.channel.setter
    def channel(self, value):
        if value in BLE_FREQ:
            self._channel = value
            self._reg_write(0x05, value)

    def available(self):
        """A `bool` describing if there is a payload in the `rx_queue`."""
        if super().available():
            self.rx_cache = super().read(self.payload_length)
            self.rx_cache = self.whiten(reverse_bits(self.rx_cache))
            end = self.rx_cache[1] + 2
            if (
                end > 30
                and self.rx_cache[end:end + 3] != crc24_ble(self.rx_cache[:end])
            ):
                # self.rx_cache = bytearray(0)  # clear invalid cache
                return bool(self.rx_queue)
            # print("recv'd:", self.rx_cache)
            # print("crc:", self.rx_cache[end: end + 3])
            new_q = QueueElement()
            new_q.mac = bytes(self.rx_cache[2 : 8])
            i = 9
            while i < end:
                size = self.rx_cache[i]
                if size + i + 1 > end or i + 1 > end:
                    # data seems malformed. just append the buffer & move on
                    new_q.data.append(self.rx_cache[i: end])
                    break
                result = decode_data_struct(self.rx_cache[i + 1 : i + 1 + size])
                if isinstance(result, int):
                    new_q.pa_level = result
                elif isinstance(result, str):
                    new_q.name = result
                elif isinstance(result, (ServiceData, bytearray)):
                    new_q.data.append(result)
                i += 1 + size
            self.rx_queue.append(new_q)
        return bool(self.rx_queue)

    # pylint: disable=arguments-differ
    def read(self):
        """Get the First Out element from the queue."""
        if self.rx_queue:
            ret_val = self.rx_queue[0]
            del self.rx_queue[0]
            return ret_val
        return None

    # pylint: enable=arguments-differ
    # pylint: disable=unused-argument
    @RF24.dynamic_payloads.setter
    def dynamic_payloads(self, val):
        raise RuntimeWarning("adjusting dynamic_payloads breaks BLE specifications")

    @RF24.data_rate.setter
    def data_rate(self, val):
        raise RuntimeWarning("adjusting data_rate breaks BLE specifications")

    @RF24.address_length.setter
    def address_length(self, val):
        raise RuntimeWarning("adjusting address_length breaks BLE specifications")

    @RF24.auto_ack.setter
    def auto_ack(self, val):
        raise RuntimeWarning("adjusting auto_ack breaks BLE specifications")

    @RF24.ack.setter
    def ack(self, val):
        raise RuntimeWarning("adjusting ack breaks BLE specifications")

    @RF24.crc.setter
    def crc(self, val):
        raise RuntimeWarning("adjusting crc breaks BLE specifications")

    def open_rx_pipe(self, pipe_number, address):
        raise RuntimeWarning("BLE implementation only uses 1 address on pipe 0")

    def open_tx_pipe(self, address):
        raise RuntimeWarning("BLE implentation only uses 1 address")

    # pylint: enable=unused-argument


TEMPERATURE_UUID = const(0x1809)  #: The Temperature Service UUID number
BATTERY_UUID = const(0x180F)  #: The Battery Service UUID number
EDDYSTONE_UUID = const(0xFEAA)  #: The Eddystone Service UUID number


def decode_data_struct(buf):
    """Decode a data structure in a received BLE payload."""
    if buf[0] not in (0x16, 0xFF, 0x0A, 0x08, 0x09):
        return None  # unknown/unsupported "chunk" of data
    if buf[0] == 0x0A:  # if data is a BLE device's TX-ing PA Level
        return struct.unpack("<b", buf[1:])[0]  # return a signed int
    if buf[0] in (0x08, 0x09):  # if data is a BLE device name
        return buf[1:].decode()  # return a string
    if buf[0] == 0xFF:  # if it is a custom/user-defined data format
        return buf  # return the raw buffer as a value
    ret_val = None
    if buf[0] == 0x16: # if it is service data
        service_data_uuid = struct.unpack("<H", buf[1:3])[0]
        if service_data_uuid == TEMPERATURE_UUID:
            ret_val = TemperatureServiceData()
            ret_val.data = buf[3:]
        elif service_data_uuid == BATTERY_UUID:
            ret_val = BatteryServiceData()
            ret_val.data = buf[3:]
        elif service_data_uuid == EDDYSTONE_UUID:
            ret_val = UrlServiceData()
            ret_val.pa_level_at_1_meter = buf[4:5]
            ret_val.data = buf[5:]
        else:
            ret_val = buf
    return ret_val


class ServiceData:
    """An abstract helper class to package specific service data using
    Bluetooth SIG defined 16-bit UUID flags to describe the data type."""

    def __init__(self, uuid):
        self._type = struct.pack("<H", uuid)
        self._data = b""

    @property
    def uuid(self):
        """This returns the 16-bit Service UUID as a `bytearray` in little
        endian. (read-only)"""
        return self._type

    @property
    def data(self):
        """This attribute is a `bytearray` or `bytes` object."""
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def buffer(self):
        """Get the representation of the instantiated object as an
        immutable `bytes` object (read-only)."""
        return bytes(self._type + self._data)

    def __len__(self):
        """For convenience, this class is compatible with python's builtin
        :py:func:`len()` method. In this context, this will return the length
        of the object (in bytes) as it would appear in the advertisement
        payload."""
        return len(self._type) + len(self._data)


class TemperatureServiceData(ServiceData):
    """This derivitive of the `ServiceData` class can be used to represent
    temperature data values as a `float` value."""

    def __init__(self):
        super().__init__(TEMPERATURE_UUID)

    @property
    def data(self):
        """This attribute is a `float` value."""
        return struct.unpack("<i", self._data[:3] + b"\0")[0] / 100

    @data.setter
    def data(self, value: float):
        if isinstance(value, float):
            value = struct.pack("<i", int(value * 100) & 0xFFFFFF)
            self._data = value[:3] + bytes([0xFE])
        elif isinstance(value, (bytes, bytearray)):
            self._data = value


class BatteryServiceData(ServiceData):
    """This derivitive of the `ServiceData` class can be used to represent
    battery charge percentage as a 1-byte value."""

    def __init__(self):
        super().__init__(BATTERY_UUID)

    @property
    def data(self):
        """The attribute is a 1-byte unsigned `int` value."""
        return int(self._data[0])

    @data.setter
    def data(self, value: int):
        if isinstance(value, int):
            self._data = struct.pack(">B", value)
        elif isinstance(value, (bytes, bytearray)):
            self._data = value


class UrlServiceData(ServiceData):
    """This derivitive of the `ServiceData` class can be used to represent
    URL data as a `bytes` value."""

    def __init__(self):
        super().__init__(EDDYSTONE_UUID)
        self._type += bytes([0x10]) + struct.pack(">b", -25)

    byte_codes = {
        "http://www.": "\x00",
        "https://www.": "\x01",
        "http://": "\x02",
        "https://": "\x03",
        ".com/": "\x00",
        ".org/": "\x01",
        ".edu/": "\x02",
        ".net/": "\x03",
        ".info/": "\x04",
        ".biz/": "\x05",
        ".gov/": "\x06",
        ".com": "\x07",
        ".org": "\x08",
        ".edu": "\x09",
        ".net": "\x0A",
        ".info": "\x0B",
        ".biz": "\x0C",
        ".gov": "\x0D"
    }

    @property
    def pa_level_at_1_meter(self):
        """The TX power level (in dBm) at 1 meter from the nRF24L01. This
        defaults to -25 (due to testing when broadcasting with 0 dBm) and must
        be a 1-byte signed `int`."""
        return struct.unpack(">b", self._type[-1:])[0]

    @pa_level_at_1_meter.setter
    def pa_level_at_1_meter(self, value):
        if isinstance(value, int):
            self._type = self._type[:-1] + struct.pack(">b", int(value))
        elif isinstance(value, (bytes, bytearray)):
            self._type = self._type[:-1] + value[:1]

    @property
    def uuid(self):
        return self._type[:2]

    @property
    def data(self):
        """This attribute is a `str` of URL data."""
        value = self._data.decode()
        for section, b_code in UrlServiceData.byte_codes.items():
            value = value.replace(b_code, section)
        return value

    @data.setter
    def data(self, value: str):
        if isinstance(value, str):
            for section, b_code in UrlServiceData.byte_codes.items():
                value = value.replace(section, b_code)
            self._data = value.encode("utf-8")
        elif isinstance(value, (bytes, bytearray)):
            self._data = value
