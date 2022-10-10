"""tests related to helper functions."""
import os
import struct
from typing import Union, Optional
import pytest
from circuitpython_nrf24l01.rf24 import address_repr
from circuitpython_nrf24l01.network.mixins import _lvl_2_addr
from circuitpython_nrf24l01.fake_ble import (
    whitener,
    crc24_ble,
    reverse_bits,
    swap_bits,
    BLE_FREQ,
    FakeBLE,
    ServiceData,
    BATTERY_UUID,
)

# pylint: disable=redefined-outer-name


@pytest.mark.parametrize(
    "addr,expected", [(b"1Node", "65646F4E31"), (b"\0\xFF\1", "01FF00")]
)
def test_addr_repr(addr: Union[bytes, bytearray], expected: str):
    """test address_repr()"""
    assert expected == address_repr(addr)


@pytest.mark.parametrize(
    "lvl,expected", [(0, 0), (1, 0o1), (2, 0o10), (3, 0o100), (4, 0o1000)]
)
def test_lvl_mask(lvl: int, expected: int):
    """test _lvl_2_addr()"""
    assert expected == _lvl_2_addr(lvl)


def test_whitener(ble_obj: FakeBLE):
    """test whitening and dewhitening an arbitrary buffer."""
    buf = os.urandom(24)
    for freq in range(3):
        coef = (freq + 37) | 0x40
        whitened = ble_obj.whiten(buf)
        assert buf == whitener(whitened, coef)
        ble_obj.hop_channel()


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


@pytest.mark.parametrize("addr", [None, 0xAABBCCDDEEFF, b"\xAA\xBB\xCC"])
def test_ble_mac(ble_obj: FakeBLE, addr: Optional[Union[int, bytes]]):
    """test the FakeBLE mac attribute."""
    assert isinstance(ble_obj.mac, (bytes, bytearray))
    ble_obj.mac = addr
    assert ble_obj.mac is not None and len(ble_obj.mac) == 6
    if addr is not None:
        if isinstance(addr, int):
            mac = (addr).to_bytes(6, byteorder="little", signed=False)
            assert mac == ble_obj.mac
        else:
            assert addr in ble_obj.mac


@pytest.mark.parametrize(
    "name",
    [
        "nRF24L01",
        b"nRF24L01",
        pytest.param(0, marks=pytest.mark.xfail),
        pytest.param("A really long name!", marks=pytest.mark.xfail),
    ],
)
def test_name(ble_obj: FakeBLE, name: Optional[Union[str, bytes, int]]):
    """test FakeBLE name attribute."""
    ble_obj.name = name
    if isinstance(name, str):
        assert name.encode(encoding="utf-8") == ble_obj.name
    else:
        assert ble_obj.name == name


@pytest.mark.parametrize(
    "name",
    [
        "nRF24L01",
        pytest.param("a really long name", marks=pytest.mark.xfail),
    ],
)
def test_show_pa_level(ble_obj: FakeBLE, name: Optional[Union[str, bytes, int]]):
    """test FakeBLE show_pa_level attribute."""
    assert not ble_obj.show_pa_level
    ble_obj.name = name
    ble_obj.show_pa_level = True
    assert ble_obj.show_pa_level


def test_hop_channel(ble_obj: FakeBLE):
    """test FakeBLE hop_channel()."""
    for freq in BLE_FREQ:
        assert ble_obj.channel == freq
        ble_obj.hop_channel()
    assert ble_obj.channel == BLE_FREQ[0]


@pytest.mark.parametrize(
    "attr",
    [
        "dynamic_payloads",
        "data_rate",
        "address_length",
        "auto_ack",
        "ack",
        "crc",
    ],
)
@pytest.mark.xfail
def test_not_implemented(ble_obj: FakeBLE, attr: str):
    """assert some FakeBLE attributes cannot be set."""
    setattr(ble_obj, attr, None)  # the value doesn't matter


@pytest.mark.parametrize(
    "func_name,args",
    [
        ("open_rx_pipe", [0, b"AnyA"]),
        ("open_tx_pipe", ["AnyA"]),
    ],
)
@pytest.mark.xfail
def test_pipe_restricted(ble_obj: FakeBLE, func_name: str, args: list):
    """assert FakeBLE pipe addresses cannot be altered."""
    getattr(ble_obj, func_name)(*args)


def test_print_details(ble_obj: FakeBLE, capsys: pytest.CaptureFixture):
    """test print_details()"""
    ble_obj.print_details(dump_pipes=True)
    out, _ = capsys.readouterr()
    assert "BLE device name" in out
    assert "Broadcasting PA Level" in out


@pytest.fixture
def inject_rx_payload(ble_obj: FakeBLE, monkeypatch: pytest.MonkeyPatch):
    """Inject a payload into the state machine's RX FIFO."""
    service_data = ServiceData(BATTERY_UUID)
    service_data.data = bytes([42])
    assert isinstance(service_data.data, bytes)
    with ble_obj as ble:
        ble.name = "test"
        ble.show_pa_level = True
        monkeypatch.setattr(ble, "send", ble._spi._spi.state.rx_fifo.append)
        ble.advertise(service_data.buffer, data_type=0x16)
    ble_obj._spi._spi.state.registers[7][0] &= 0xF1
    return repr(service_data)


def test_rx_payload(ble_obj: FakeBLE, inject_rx_payload: pytest.fixture):
    """test available() and read()"""
    buf_repr = inject_rx_payload
    assert ble_obj.available()
    payload = ble_obj.read()
    assert payload.mac == ble_obj.mac
    assert payload.name == "test"
    assert not payload.pa_level
    for data in payload.data:
        print("data type", type(data), data)
        if isinstance(data, ServiceData):
            assert address_repr(data.buffer, False) == buf_repr
            assert data.data == 42
            assert data.uuid == struct.pack("<H", BATTERY_UUID)
            break
    else:  # pragma: no cover
        raise ValueError("ServiceData item not found in decrypted payload")
    assert ble_obj.read() is None
