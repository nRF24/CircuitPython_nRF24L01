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
"""Original research was done by Dmitry Grinberg and his write-up can be found at
http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery"""
from os import urandom
import struct

try:
    from typing import Union, List, Optional
except ImportError:
    pass
import busio  # type: ignore[import]
from digitalio import DigitalInOut  # type: ignore[import]
from micropython import const
from .rf24 import RF24, address_repr


def swap_bits(original: int) -> int:
    """This function reverses the bit order for a single byte."""
    original &= 0xFF
    reverse = 0
    for _ in range(8):
        reverse <<= 1
        reverse |= original & 1
        original >>= 1
    return reverse


def reverse_bits(original: Union[bytes, bytearray]) -> bytearray:
    """This function reverses the bit order for an entire buffer protocol object."""
    ret = bytearray(len(original))
    for i, byte in enumerate(original):
        ret[i] = swap_bits(byte)
    return ret


def chunk(buf: Union[bytes, bytearray], data_type: int = 0x16) -> bytearray:
    """This function is used to pack data values into a block of data that
    make up part of the BLE payload per Bluetooth Core Specifications."""
    return bytearray([len(buf) + 1, data_type & 0xFF]) + buf


def whitener(buf: Union[bytes, bytearray], coef: int) -> bytearray:
    """Whiten and de-whiten data according to the given coefficient."""
    data = bytearray(buf)
    for i, byte in enumerate(data):
        res, mask = (0, 1)
        for _ in range(8):
            if coef & 1:
                coef ^= 0x88
                byte ^= mask
            mask <<= 1
            coef >>= 1
        data[i] = byte ^ res
    return data


def crc24_ble(
    data: Union[bytes, bytearray], deg_poly: int = 0x65B, init_val: int = 0x555555
) -> bytearray:
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

TEMPERATURE_UUID = const(0x1809)  #: The Temperature Service UUID number
BATTERY_UUID = const(0x180F)  #: The Battery Service UUID number
EDDYSTONE_UUID = const(0xFEAA)  #: The Eddystone Service UUID number


class QueueElement:
    """A data structure used for storing received & decoded BLE payloads in
    the :attr:`~circuitpython_nrf24l01.fake_ble.FakeBLE.rx_queue`.

    :param bytes,bytearray buffer: the validated BLE payload (not including
        the CRC checksum). The buffer passed here is decoded into this class's
        properties.
    """

    def __init__(self, buffer: bytearray):
        #: The transmitting BLE device's MAC address as a `bytes` object.
        self.mac: Union[bytes, bytearray] = bytes(buffer[2:8])
        self.name: Optional[Union[str, bytes]] = None
        """The transmitting BLE device's name. This will be a `str`, `bytes` object (if
        a `UnicodeError` was caught), or `None` (if not included in the received
        payload)."""
        self.pa_level: Optional[int] = None
        """The transmitting device's PA Level (if included in the received payload)
        as an `int`.

        .. note:: This value does not represent the received signal strength.
            The nRF24L01 will receive anything over a -64 dbm threshold."""
        self.data: List[Union[bytearray, "ServiceData"]] = []
        """A `list` of the transmitting device's data structures (if any).
        If an element in this `list` is not an instance (or descendant) of the
        `ServiceData` class, then it is likely a custom, user-defined, or unsupported
        specification - in which case it will be a `bytearray` object."""

        end = buffer[1] + 2
        i = 8
        while i < end:
            size = buffer[i]
            if size + i + 1 > end or i + 1 > end or not size:
                # data seems malformed. just append the buffer & move on
                self.data.append(buffer[i:end])
                break
            result = self._decode_data_struct(buffer[i + 1 : i + 1 + size])
            if not result:  # decoding failed
                self.data.append(buffer[i : i + 1 + size])
            i += 1 + size

    def _decode_data_struct(self, buf: bytearray):
        """Decode a data structure in a received BLE payload."""
        # print("decoding", address_repr(buf, 0, " "))
        if buf[0] not in (0x16, 0x0A, 0x08, 0x09):
            return False  # unknown/unsupported "chunk" of data
        if buf[0] == 0x0A and len(buf) == 2:  # if data is the device's TX-ing PA Level
            self.pa_level = struct.unpack("b", buf[1:2])[0]
        if buf[0] in (0x08, 0x09):  # if data is a BLE device name
            try:
                self.name = buf[1:].decode()
            except UnicodeError:
                self.name = bytes(buf[1:])
        if buf[0] == 0xFF:  # if it is a custom/user-defined data format
            self.data.append(buf)  # return the raw buffer as a value
        if buf[0] == 0x16:  # if it is service data
            service_data_uuid = struct.unpack("<H", buf[1:3])[0]
            if service_data_uuid == TEMPERATURE_UUID:
                service = TemperatureServiceData()
                service.data = buf[3:]  # type: ignore[assignment]
                self.data.append(service)
            elif service_data_uuid == BATTERY_UUID:
                service = BatteryServiceData()  # type: ignore[assignment]
                service.data = buf[3:]  # type: ignore[assignment]
                self.data.append(service)
            elif service_data_uuid == EDDYSTONE_UUID:
                service = UrlServiceData()  # type: ignore[assignment]
                service.pa_level_at_1_meter = buf[4:5]  # type: ignore[attr-defined]
                service.data = buf[5:]  # type: ignore[assignment]
                self.data.append(service)
            else:
                self.data.append(buf)
        return True


class FakeBLE(RF24):
    """A class to implement BLE advertisements using the nRF24L01."""

    def __init__(
        self,
        spi: busio.SPI,
        csn: DigitalInOut,
        ce_pin: DigitalInOut,
        spi_frequency: int = 10000000,
    ):
        super().__init__(spi, csn, ce_pin, spi_frequency=spi_frequency)
        self._curr_freq = 2
        self._show_dbm = False
        self._ble_name: Optional[Union[bytearray, bytes]] = None
        self._mac = urandom(6)
        self._config = self._config & 3 | 0x10  # disable CRC
        # disable auto_ack, dynamic payloads, all TX features, & auto-retry
        self._aa, self._dyn_pl, self._features, self._retry_setup = (0,) * 4
        self._addr_len = 4  # use only 4 byte address length
        self._tx_address[:4] = b"\x71\x91\x7D\x6B"
        with self:
            super().open_rx_pipe(0, b"\x71\x91\x7D\x6B\0")
        #: The internal queue of received BLE payloads' data.
        self.rx_queue: List[QueueElement] = []
        self.rx_cache: bytearray = bytearray(0)
        """The internal cache used when validating received BLE payloads."""
        self.hop_channel()

    def __exit__(self, *exc):
        self._show_dbm = False
        self._ble_name = None
        return super().__exit__()

    @property
    def mac(self) -> Union[bytes, bytearray]:
        """This attribute returns a 6-byte buffer that is used as the
        arbitrary mac address of the BLE device being emulated."""
        return self._mac

    @mac.setter
    def mac(self, address: Optional[Union[bytes, bytearray, int]]):
        if address is None:
            self._mac = urandom(6)
        if isinstance(address, int):
            self._mac = (address).to_bytes(6, "little")
        elif isinstance(address, (bytearray, bytes)):
            self._mac = address
        if len(self._mac) < 6:
            self._mac += urandom(6 - len(self._mac))

    @property
    def name(self) -> Optional[bytes]:
        """The broadcasted BLE name of the nRF24L01."""
        return self._ble_name

    @name.setter
    def name(self, _name: Optional[Union[str, bytes, bytearray]]):
        if _name is not None:
            if isinstance(_name, str):
                _name = _name.encode("utf-8")
            if not isinstance(_name, (bytes, bytearray)):
                raise ValueError("name must be a bytearray or bytes object.")
            if len(_name) > (18 - self._show_dbm * 3):
                raise ValueError("name length exceeds maximum.")
        self._ble_name = _name

    @property
    def show_pa_level(self) -> bool:
        """If this attribute is `True`, the payload will automatically include
        the nRF24L01's :attr:`~circuitpython_nrf24l01.rf24.RF24.pa_level` in the
        advertisement."""
        return bool(self._show_dbm)

    @show_pa_level.setter
    def show_pa_level(self, enable: bool):
        if enable and self._ble_name is not None and len(self._ble_name) > 16:
            raise ValueError("there is not enough room to show the pa_level.")
        self._show_dbm = bool(enable)

    def hop_channel(self):
        """Trigger an automatic change of BLE compliant channels."""
        self._curr_freq += 1 if self._curr_freq < 2 else -2
        self.channel = BLE_FREQ[self._curr_freq]

    def whiten(self, data: Union[bytes, bytearray]) -> bytearray:
        """Whitening the BLE packet data ensures there's no long repetition
        of bits."""
        coef = (self._curr_freq + 37) | 0x40
        # print("buffer: 0x" + address_repr(data, 0))
        # print(
        #     "Whiten Coef: {} on channel {}".format(
        #         hex(coef), BLE_FREQ[self._curr_freq]
        #     )
        # )
        data = whitener(data, coef)
        # print("whitened: 0x" + address_repr(data, 0))
        return data

    def _make_payload(self, payload: Union[bytes, bytearray]) -> bytes:
        """Assemble the entire packet to be transmitted as a payload."""
        if self.len_available(payload) < 0:
            raise ValueError(
                "Payload length exceeds maximum buffer size by "
                "{} bytes".format(abs(self.len_available(payload)))
            )
        name_length = 0 if self._ble_name is None else (len(self._ble_name) + 2)
        pl_size = 9 + len(payload) + name_length + self._show_dbm * 3
        buf = bytes([0x42, pl_size]) + self.mac
        buf += chunk(b"\x05", 1)
        pa_level = b""
        if self._show_dbm:
            pa_level = chunk(struct.pack(">b", self.pa_level), 0x0A)
        buf += pa_level
        if name_length and self._ble_name is not None:
            buf += chunk(self._ble_name, 0x08)
        buf += payload
        # print("PL: {} CRC: {}".format(
        #     address_repr(buf, 0), address_repr(crc24_ble(buf), 0)
        # ))
        buf += crc24_ble(buf)
        return buf

    def len_available(self, hypothetical: Union[bytes, bytearray] = b"") -> int:
        """This function will calculates how much length (in bytes) is
        available in the next payload."""
        name_length = 0 if self._ble_name is None else (len(self._ble_name) + 2)
        return 18 - name_length - self._show_dbm * 3 - len(hypothetical)

    def advertise(self, buf: Union[bytes, bytearray] = b"", data_type: int = 0xFF):
        """This blocking function is used to broadcast a payload."""
        if not isinstance(buf, (bytearray, bytes, list, tuple)):
            raise ValueError("buffer is an invalid format")
        payload = b""
        if isinstance(buf, (list, tuple)):
            for byte in buf:
                payload += byte
        else:
            payload = chunk(buf, data_type) if buf else b""
        payload = self.whiten(self._make_payload(payload))
        # print("original: 0x{}".format(address_repr(payload)))
        # print("reversed: 0x{}".format(address_repr(reverse_bits(payload))))
        self.send(reverse_bits(payload))

    def print_details(self, dump_pipes: bool = False):
        super().print_details(False)
        print("BLE device name___________{}".format(str(self.name)))
        print("Broadcasting PA Level_____{}".format(self.show_pa_level))
        if dump_pipes:
            super().print_pipes()

    @RF24.channel.setter  # type: ignore[attr-defined]
    def channel(self, value: int):
        if value in BLE_FREQ:
            self._channel = value
            self._reg_write(0x05, value)

    def available(self) -> bool:
        """A `bool` describing if there is a payload in the `rx_queue`."""
        if super().available():
            self.rx_cache = super().read(self.payload_length)  # type: ignore
            self.rx_cache = self.whiten(reverse_bits(self.rx_cache))
            end = self.rx_cache[1] + 2
            self.rx_cache = self.rx_cache[: end + 3]
            if end < 30 and self.rx_cache[end : end + 3] == crc24_ble(
                self.rx_cache[:end]
            ):
                # print("recv'd:", self.rx_cache)
                # print("crc:", self.rx_cache[end: end + 3])
                self.rx_queue.append(QueueElement(self.rx_cache))
        return bool(self.rx_queue)

    # pylint: disable=arguments-differ
    def read(self) -> Optional[QueueElement]:  # type: ignore[override]
        """Get the First Out element from the queue."""
        if self.rx_queue:
            ret_val = self.rx_queue[0]
            del self.rx_queue[0]
            return ret_val
        return None

    # pylint: enable=arguments-differ
    # pylint: disable=unused-argument
    @RF24.dynamic_payloads.setter  # type: ignore[attr-defined]
    def dynamic_payloads(self, val):
        raise NotImplementedError("using dynamic_payloads breaks BLE specifications")

    @RF24.data_rate.setter  # type: ignore[attr-defined]
    def data_rate(self, val):
        raise NotImplementedError("adjusting data_rate breaks BLE specifications")

    @RF24.address_length.setter  # type: ignore[attr-defined]
    def address_length(self, val):
        raise NotImplementedError("adjusting address_length breaks BLE specifications")

    @RF24.auto_ack.setter  # type: ignore[attr-defined]
    def auto_ack(self, val):
        raise NotImplementedError("using auto_ack breaks BLE specifications")

    @RF24.ack.setter  # type: ignore[attr-defined]
    def ack(self, val):
        raise NotImplementedError("adjusting ack breaks BLE specifications")

    @RF24.crc.setter  # type: ignore[attr-defined]
    def crc(self, val):
        raise NotImplementedError("BLE specifications only use crc24")

    def open_rx_pipe(self, pipe_number, address):
        raise NotImplementedError("BLE implementation only uses 1 address on pipe 0")

    def open_tx_pipe(self, address):
        raise NotImplementedError("BLE implementation only uses 1 address")

    # pylint: enable=unused-argument


class ServiceData:
    """An abstract helper class to package specific service data using
    Bluetooth SIG defined 16-bit UUID flags to describe the data type."""

    def __init__(self, uuid: int):
        self._type = struct.pack("<H", uuid)
        self._data = b""

    @property
    def uuid(self) -> bytes:
        """This returns the 16-bit Service UUID as a `bytearray` in little
        endian. (read-only)"""
        return self._type

    @property
    def data(self) -> Union[int, float, str, bytes, bytearray]:
        """This attribute is a `bytearray` or `bytes` object."""
        return self._data

    @data.setter
    def data(self, value: Union[int, float, str, bytes, bytearray]):
        self._data = value  # type: ignore[assignment]

    @property
    def buffer(self) -> bytes:
        """Get the representation of the instantiated object as an
        immutable `bytes` object (read-only)."""
        return bytes(self._type + self._data)

    def __len__(self) -> int:
        """For convenience, this class is compatible with python's builtin
        :py:func:`len()` method. In this context, this will return the length
        of the object (in bytes) as it would appear in the advertisement
        payload."""
        return len(self._type) + len(self._data)

    def __repr__(self) -> str:
        """For convenience, this class is compatible with python's builtin
        :py:func:`repr()` method. In this context, it will return a string of
        data with applicable suffixed units."""
        return address_repr(self.buffer, False)


class TemperatureServiceData(ServiceData):
    """This derivative of the `ServiceData` class can be used to represent
    temperature data values as a `float` value."""

    def __init__(self):
        super().__init__(TEMPERATURE_UUID)

    @property
    def data(self) -> float:
        """This attribute is a `float` value."""
        return struct.unpack("<i", self._data[:3] + b"\0")[0] * 10**-2

    @data.setter
    def data(self, value: Union[float, bytes, bytearray]):
        if isinstance(value, float):
            value = struct.pack("<i", int(value * 100) & 0xFFFFFF)
            self._data = value[:3] + bytes([0xFE])
        elif isinstance(value, (bytes, bytearray)):
            self._data = value

    def __repr__(self) -> str:
        return "Temperature: {} C".format(self.data)


class BatteryServiceData(ServiceData):
    """This derivative of the `ServiceData` class can be used to represent
    battery charge percentage as a 1-byte value."""

    def __init__(self):
        super().__init__(BATTERY_UUID)

    @property
    def data(self) -> int:
        """The attribute is a 1-byte unsigned `int` value."""
        return int(self._data[0])

    @data.setter
    def data(self, value: Union[int, bytes, bytearray]):
        if isinstance(value, int):
            self._data = struct.pack("B", value)
        elif isinstance(value, (bytes, bytearray)):
            self._data = value

    def __repr__(self) -> str:
        return "Battery capacity remaining: {}%".format(self.data)


class UrlServiceData(ServiceData):
    """This derivative of the `ServiceData` class can be used to represent
    URL data as a `bytes` value."""

    def __init__(self):
        super().__init__(EDDYSTONE_UUID)
        self._type += bytes([0x10]) + struct.pack(">b", -25)

    codex_prefix = ["http://www.", "https://www.", "http://", "https://"]
    codex_suffix = [".com", ".org", ".edu", ".net", ".info", ".biz", ".gov"]
    codex_suffix = [suffix + "/" for suffix in codex_suffix] + codex_suffix

    @property
    def pa_level_at_1_meter(self) -> int:
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
    def uuid(self) -> bytes:
        return self._type[:2]

    @property
    def data(self) -> str:
        """This attribute is a `str` of URL data."""
        value = self._data.decode()
        for i, b_code in enumerate(UrlServiceData.codex_prefix):
            if value.startswith(chr(i)):
                value = value.replace(chr(i), b_code, 1)
                break
        for i, b_code in enumerate(UrlServiceData.codex_suffix):
            value = value.replace(chr(i), b_code)
        return value

    @data.setter
    def data(self, value: Union[str, bytes, bytearray]):
        if isinstance(value, str):
            for i, b_code in enumerate(UrlServiceData.codex_prefix):
                if value.startswith(b_code):
                    value = value.replace(b_code, chr(i), 1)
            for i, b_code in enumerate(UrlServiceData.codex_suffix):
                value = value.replace(b_code, chr(i))
            self._data = value.encode("utf-8")
        elif isinstance(value, (bytes, bytearray)):
            self._data = value

    def __repr__(self) -> str:
        return "Advertised URL: " + self.data
