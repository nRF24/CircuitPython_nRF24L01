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
found here <http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_"""
from os import urandom
import struct
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


BLE_FREQ = (
    2,
    26,
    80,
)  #: The BLE channel number is different from the nRF channel number.


class FakeBLE(RF24):
    """A class to implement BLE advertisements using the nRF24L01."""

    def __init__(self, spi, csn, ce_pin, spi_frequency=10000000):
        super().__init__(spi, csn, ce_pin, spi_frequency=spi_frequency)
        self._curr_freq = 0
        self._show_dbm = False
        self._ble_name = None
        self._mac = urandom(6)
        self._config = self._config & 3 | 0x10  # disable CRC
        # disable auto_ack, dynamic payloads, all TX features, & auto-retry
        self._aa, self._dyn_pl, self._features, self._retry_setup = (0,) * 4
        self._addr_len = 4  # use only 4 byte address length
        self._tx_address[:4] = b"\x71\x91\x7D\x6B"
        with self:
            self.payload_length = 32
            super().open_rx_pipe(0, b"\x71\x91\x7D\x6B\0")

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
    def name(self, n):
        if n is not None:
            if not isinstance(n, (bytes, bytearray)):
                raise ValueError("name must be a bytearray or bytes object.")
            if len(n) > (18 - self._show_dbm * 3):
                raise ValueError("name length exceeds maximum.")
        self._ble_name = n

    @property
    def show_pa_level(self):
        """If this attribute is `True`, the payload will automatically include
        the nRF24L01's pa_level in the advertisement."""
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
        """Whitening the BLE packet data ensures there's no long repeatition
        of bits."""
        data, coef = (bytearray(data), (self._curr_freq + 37) | 0x40)
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
        payload = self._make_payload(payload)
        self.send(reverse_bits(self.whiten(payload)))

    @property
    def channel(self):
        """The only allowed channels are those contained in the `BLE_FREQ`
        tuple."""
        return self._channel

    @channel.setter
    def channel(self, value):
        if value not in BLE_FREQ:
            raise ValueError("channel {} is not a valid BLE frequency".format(value))
        self._channel = value
        self._reg_write(0x05, value)

    # pylint: disable=missing-function-docstring
    @property
    def dynamic_payloads(self):
        raise NotImplementedError(
            "adjusting dynamic_payloads breaks BLE specifications"
        )

    def set_dynamic_payloads(self, enable, pipe_number=None):
        raise NotImplementedError(
            "adjusting dynamic_payloads breaks BLE specifications"
        )

    @property
    def data_rate(self):
        raise NotImplementedError("adjusting data_rate breaks BLE specifications")

    @property
    def address_length(self):
        raise NotImplementedError("adjusting address_length breaks BLE specifications")

    @property
    def auto_ack(self):
        raise NotImplementedError("adjusting auto_ack breaks BLE specifications")

    def set_auto_ack(self, enable, pipe_number=None):
        raise NotImplementedError("adjusting auto_ack breaks BLE specifications")

    @property
    def ack(self):
        raise NotImplementedError("adjusting ack breaks BLE specifications")

    @property
    def crc(self):
        raise NotImplementedError("adjusting crc breaks BLE specifications")

    def open_rx_pipe(self, pipe_number, address):
        raise NotImplementedError("BLE implementation only uses 1 address on pipe 0")

    def open_tx_pipe(self, address):
        raise NotImplementedError("BLE implentation only uses 1 address")

    # pylint: enable=missing-function-docstring
    def print_details(self, dump_pipes=False):
        """This debuggung function aggregates and outputs all status/condition
        related information from the nRF24L01."""
        print("Is a plus variant_________{}".format(self.is_plus_variant))
        print("BLE device name___________{}".format(str(self.name)))
        print("Broadcasting PA Level_____{}".format(self.show_pa_level))
        print(
            "Channel___________________{} ~ {} GHz".format(
                self.channel, (self.channel + 2400) / 1000
            )
        )
        print("RF Data Rate______________1 Mbps")
        print("RF Power Amplifier________{} dbm".format(self.pa_level))
        print(
            "RF Low Noise Amplifier____{}".format(
                "Enabled" if self.is_lna_enabled else "Disabled"
            )
        )
        print("CRC bytes_________________3")
        print("Address length____________4 bytes")
        print("TX Payload lengths________{} bytes".format(self.payload_length))
        print("Auto retry delay__________250 microseconds")
        print("Auto retry attempts_______0 maximum")
        print("Re-use TX FIFO____________{}".format(bool(self._reg_read(0x17) & 64)))
        print(
            "IRQ on Data Ready__{}    Data Ready___________{}".format(
                "_Enabled" if not self._config & 0x40 else "Disabled", self.irq_dr
            )
        )
        print(
            "IRQ on Data Fail___{}    Data Failed__________{}".format(
                "_Enabled" if not self._config & 0x10 else "Disabled", self.irq_df
            )
        )
        print(
            "IRQ on Data Sent___{}    Data Sent____________{}".format(
                "_Enabled" if not self._config & 0x20 else "Disabled", self.irq_ds
            )
        )
        print(
            "TX FIFO full__________{}    TX FIFO empty________{}".format(
                "_True" if self.tx_full else "False", self.fifo(True, True)
            )
        )
        print(
            "RX FIFO full__________{}    RX FIFO empty________{}".format(
                "_True" if self.fifo(False, False) else "False", self.fifo(False, True)
            )
        )
        print(
            "Ask no ACK_________{}    Custom ACK Payload___Disabled".format(
                "_Allowed" if self.allow_ask_no_ack else "Disabled",
            )
        )
        print("Dynamic Payloads___Disabled    Auto Acknowledgment__Disabled")
        print(
            "Primary Mode_____________{}    Power Mode___________{}".format(
                "RX" if self.listen else "TX",
                ("Standby-II" if self.ce_pin.value else "Standby-I")
                if self._config & 2
                else "Off",
            )
        )
        if dump_pipes:
            self._dump_pipes()


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
        """The service's data. This is a `bytearray`, and its format is
        defined by relative Bluetooth Service Specifications (and GATT
        supplemental specifications)."""
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
        """For convenience, this class is compatible with python's builtin
        :py:func:`len()` method. In this context, this will return the length
        of the object (in bytes) as it would appear in the advertisement
        payload."""
        return len(self._type) + len(self.data)


class TemperatureServiceData(ServiceData):
    """This derivitive of the `ServiceData` class can be used to represent
    temperature data values as a `float` value."""

    def __init__(self):
        super().__init__(0x1809)

    @ServiceData.data.setter
    def data(self, value):
        value = struct.pack("<i", int(value * 100) & 0xFFFFFF)
        self._data = value[:3] + bytes([0xFE])


class BatteryServiceData(ServiceData):
    """This derivitive of the `ServiceData` class can be used to represent
    battery charge percentage as a 1-byte value."""

    def __init__(self):
        super().__init__(0x180F)

    @ServiceData.data.setter
    def data(self, value):
        self._data = struct.pack(">B", value)


class UrlServiceData(ServiceData):
    """This derivitive of the `ServiceData` class can be used to represent
    URL data as a `bytes` value."""

    def __init__(self):
        super().__init__(0xFEAA)
        self._type += bytes([0x10]) + struct.pack(">b", -25)

    @property
    def pa_level_at_1_meter(self):
        """The TX power level (in dBm) at 1 meter from the nRF24L01. This
        defaults to -25 (due to testing when broadcasting with 0 dBm) and must
        be a 1-byte signed `int`."""
        return struct.unpack(">b", self._type[-1:])[0]

    @pa_level_at_1_meter.setter
    def pa_level_at_1_meter(self, value):
        self._type = self._type[:-1] + struct.pack(">b", int(value))

    @property
    def uuid(self):
        return self._type[:2]

    @ServiceData.data.setter
    def data(self, value):
        value = value.replace("http://www.", "\x00")
        value = value.replace("https://www.", "\x01")
        value = value.replace("http://", "\x02")
        value = value.replace("https://", "\x03")
        value = value.replace(".com/", "\x00")
        value = value.replace(".org/", "\x01")
        value = value.replace(".edu/", "\x02")
        value = value.replace(".net/", "\x03")
        value = value.replace(".info/", "\x04")
        value = value.replace(".biz/", "\x05")
        value = value.replace(".gov/", "\x06")
        value = value.replace(".com", "\x07")
        value = value.replace(".org", "\x08")
        value = value.replace(".edu", "\x09")
        value = value.replace(".net", "\x0A")
        value = value.replace(".info", "\x0B")
        value = value.replace(".biz", "\x0C")
        self._data = value.replace(".gov", "\x0D").encode("utf-8")
