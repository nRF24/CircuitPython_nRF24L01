"""Tests for the fake_ble module's helper classes/functions."""
import os
import struct
from typing import Optional
import pytest
from circuitpython_nrf24l01.fake_ble import (
    whitener,
    crc24_ble,
    reverse_bits,
    swap_bits,
    chunk,
    BLE_FREQ,
    FakeBLE,
    QueueElement,
    BatteryServiceData,
    TemperatureServiceData,
    UrlServiceData,
    BATTERY_UUID,
    TEMPERATURE_UUID,
    EDDYSTONE_UUID,
)


@pytest.mark.parametrize("coef", BLE_FREQ)
def test_whitener(coef: int):
    """test whitening and dewhitening an arbitrary buffer."""
    buf = os.urandom(24)
    whitened = whitener(buf, coef)
    assert buf == whitener(whitened, coef)


def test_crc24():
    """test CRC 24 bit checksum."""
    buf = bytes(range(24))
    checksum = crc24_ble(buf)
    assert len(checksum) == 3
    assert checksum == bytearray(b"\x1d`\xeb")


def test_rev_bits():
    """test reverse_bits()"""
    buf = bytes(range(21))
    result = reverse_bits(buf)
    assert len(result) == len(buf)
    for x, y in zip(result, buf):
        assert x == swap_bits(y)


@pytest.mark.parametrize("dev_name", [b"n", b"\xFF", None])
def test_queue_element(dev_name: Optional[bytes]):
    """test the deciphering of BLE payload data from buffers."""
    batt = BatteryServiceData()
    batt.data = 100
    assert "100%" in str(batt)
    assert batt.uuid == struct.pack("<H", BATTERY_UUID)
    assert len(batt) == 3
    temp = TemperatureServiceData()
    temp.data = 32.1
    assert "32.1 C" in str(temp)
    assert temp.uuid == struct.pack("<H", TEMPERATURE_UUID)
    assert len(temp) == 6
    url = UrlServiceData()
    url.data = "https://github.com/"
    url.pa_level_at_1_meter = 20
    assert "https://github.com/" in str(url)
    assert url.uuid == struct.pack("<H", EDDYSTONE_UUID)
    assert url.pa_level_at_1_meter == 20
    assert len(url) == 12

    class Dummy:
        """A dummy class to mimic FakeBLE class"""

        def __init__(self, name: bytes = None):
            self._ble_name: Optional[bytes] = name
            self._show_dbm = False
            self.mac = os.urandom(6)

        @property
        def name(self):
            """mock the FakeBLE device name attribute."""
            try:
                return self._ble_name.decode("utf-8")
            except (AttributeError, UnicodeError, UnicodeDecodeError):
                return self._ble_name

        def len_available(self, payload):
            """forward to FakeBLE.len_available()"""
            return FakeBLE.len_available(self, payload)

        def make_payload(self, payload):
            """forward to FakeBLE._make_payload()"""
            return FakeBLE._make_payload(self, payload)

    dummy = Dummy(dev_name)

    for data in [batt, temp, url]:
        queue = QueueElement(dummy.make_payload(chunk(data.buffer, 0x16)))
        assert queue.mac == dummy.mac
        assert queue.name == dummy.name
        for chunk_d in queue.data:
            if not isinstance(chunk_d, (bytearray, bytes)):
                assert chunk_d.data == data.data
