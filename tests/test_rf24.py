"""Test functions related to core RF24 functionality."""
from typing import Optional
import pytest
from circuitpython_nrf24l01.rf24 import RF24
from circuitpython_nrf24l01.fake_ble import FakeBLE


def test_context(rf24_obj: RF24, ble_obj: FakeBLE):
    """test context manager"""
    with rf24_obj as nrf:
        nrf.pa_level = -12
        nrf.data_rate = 2
    with ble_obj as ble:
        assert ble.pa_level == 0
        assert ble.data_rate == 1
        assert ble.dynamic_payloads == 0
        assert ble.auto_ack == 0
        assert ble.address_length == 4
    with rf24_obj as rf24:
        assert rf24.pa_level == -12
        assert rf24.data_rate == 2
        assert rf24.dynamic_payloads == 0x3F
        assert rf24.auto_ack == 0x3F
        assert rf24.address_length == 5


@pytest.mark.parametrize("value", [True, False])
def test_ce(rf24_obj: RF24, value: False):
    """test ce_pin attribute."""
    rf24_obj.ce_pin = value
    assert rf24_obj.ce_pin == value


@pytest.mark.parametrize(
    "value", [5, 4, 3, 2, pytest.param(1, marks=pytest.mark.xfail)]
)
def test_addr_len(rf24_obj: RF24, value: int):
    """test address_length attribute."""
    rf24_obj.address_length = value
    assert rf24_obj.address_length == value


@pytest.mark.parametrize(
    "pipe",
    [
        0,
        1,
        2,
        3,
        4,
        5,
        pytest.param(6, marks=pytest.mark.xfail),
        pytest.param(-1, marks=pytest.mark.xfail),
    ],
)
@pytest.mark.parametrize(
    "addr", [b"1Node", b"2", pytest.param(b"", marks=pytest.mark.xfail)]
)
def test_rx_pipe(rf24_obj: RF24, pipe: int, addr: bytes):
    """test open/close_rx_pipe()"""
    try:
        rf24_obj.open_rx_pipe(pipe, addr)
    except IndexError:
        pass
    finally:
        rf24_obj.close_rx_pipe(pipe)
    assert bytearray(addr) in bytearray(rf24_obj.address(pipe))


def inject_rx_fifo(obj: RF24):
    """Fake a received payloads by injecting them into the state machine."""
    obj._spi._spi.state.rx_fifo.append(bytearray(b"\xFF" * 32))
    obj._spi._spi.state.registers[7][0] &= 0xF1
    obj._spi._spi.state.registers[7][0] |= 4


def test_available(rf24_obj: RF24):
    """test available()"""
    assert not rf24_obj.available()
    inject_rx_fifo(rf24_obj)
    assert rf24_obj.available()


@pytest.mark.parametrize("dyn_pl", [True, False])
def test_any(rf24_obj: RF24, dyn_pl):
    """test any()"""
    assert not rf24_obj.any()
    rf24_obj.dynamic_payloads = dyn_pl
    inject_rx_fifo(rf24_obj)
    assert rf24_obj.any()


@pytest.mark.parametrize("dyn_pl", [True, False])
def test_read(rf24_obj: RF24, dyn_pl):
    """test read()"""
    assert rf24_obj.read() is None
    assert rf24_obj.read(32) == bytearray(b"." * 32)
    rf24_obj.dynamic_payloads = dyn_pl

    for _ in range(4):  # inject 128 bytes in state machine's RX FIFO
        inject_rx_fifo(rf24_obj)
    assert rf24_obj.read() == bytearray(b"\xFF" * 32)
    assert rf24_obj.read(96) == bytearray(b"\xFF" * 96)
    assert rf24_obj.any() == 0


def test_tx_full(rf24_obj: RF24):
    """test tx_full attribute"""
    assert not rf24_obj.tx_full
    rf24_obj.ack = True
    for _ in range(3):
        assert rf24_obj.load_ack(b"\xFF" * 32, 1)
    assert rf24_obj.update() and rf24_obj.tx_full


def test_pipe(rf24_obj: RF24):
    """test pipe attribute"""
    print("STATUS: %02X" % rf24_obj._in[0])
    assert rf24_obj.update() and rf24_obj.pipe is None
    rf24_obj._spi._spi.state.registers[7][0] &= 0xF1
    rf24_obj._spi._spi.state.registers[7][0] |= 2
    print("STATUS: %02X" % rf24_obj._in[0])
    assert rf24_obj.update() and rf24_obj.pipe == 1


def test_status_flags(rf24_obj: RF24):
    """test IRQ status flags/attributes and clear_status_flags()"""
    # Fake all status flags at once
    rf24_obj._spi._spi.state.registers[7][0] |= 0x70
    rf24_obj.update()  # read flags into RF24 class
    assert rf24_obj.irq_df
    assert rf24_obj.irq_dr
    assert rf24_obj.irq_ds
    rf24_obj.clear_status_flags()  # reset all flags
    assert not rf24_obj.irq_df
    assert not rf24_obj.irq_dr
    assert not rf24_obj.irq_ds


def test_print_details(rf24_obj: RF24, capsys: pytest.CaptureFixture):
    """test print_details()"""
    rf24_obj.set_dynamic_payloads(False, 1)
    rf24_obj.set_payload_length(8, 1)
    rf24_obj.open_rx_pipe(1, b"test")
    rf24_obj.print_details(dump_pipes=True)
    out, _ = capsys.readouterr()
    assert "Pipe 1 ( open ) bound" in out
    assert (
        "expecting {} byte static payloads".format(rf24_obj.get_payload_length(1))
        in out
    )


def test_dyn_pl_attr(rf24_obj: RF24):
    """test dynamic_payloads attribute (using list of integers)."""
    enable = [1, -1, 0, 1]
    previous = rf24_obj.dynamic_payloads & enable.index(-1)
    rf24_obj.dynamic_payloads = enable
    for i, pipe in enumerate(enable):
        if pipe < 0:
            assert rf24_obj.get_dynamic_payloads(i) == previous
        else:
            assert rf24_obj.get_dynamic_payloads(i) == pipe


@pytest.mark.parametrize("pipe", [None, 0, 1, 2, 3, 4, 5])
@pytest.mark.parametrize("length", [20, 32])
def test_payload_len_func(rf24_obj: RF24, pipe: Optional[int], length: int):
    """test setter/getter of payload_length()"""
    rf24_obj.set_payload_length(length, pipe)
    if pipe is not None:
        assert rf24_obj.get_payload_length(pipe) == length


def test_payload_length_attr(rf24_obj: RF24):
    """test payload_length attribute (using list of integers)."""
    enable = [1, -1, 20, 0]
    previous = rf24_obj.payload_length
    rf24_obj.payload_length = enable
    for i, pipe in enumerate(enable):
        if pipe <= 0:
            assert rf24_obj.get_payload_length(i) == previous
        else:
            assert rf24_obj.get_payload_length(i) == pipe


@pytest.mark.parametrize("pipe", [None, 0, 1, 2, 3, 4, 5])
@pytest.mark.parametrize("enable", [True, False])
def test_auto_ack_func(rf24_obj: RF24, pipe: Optional[int], enable: bool):
    """test setter/getter of auto_ack()"""
    rf24_obj.set_auto_ack(enable, pipe)
    if pipe is not None:
        assert rf24_obj.get_auto_ack(pipe) == enable


def test_auto_ack_attr(rf24_obj: RF24):
    """test auto_ack attribute (using list of integers)."""
    enable = [1, -1, 20, 0]
    previous = bool(rf24_obj.auto_ack & (enable.index(-1)))
    rf24_obj.auto_ack = enable
    for i, pipe in enumerate(enable):
        if pipe < 0:
            assert rf24_obj.get_auto_ack(i) == previous
        else:
            assert rf24_obj.get_auto_ack(i) == bool(pipe)


@pytest.mark.parametrize("enable", [True, False])
def test_ack(rf24_obj: RF24, enable: bool):
    """test ack attribute"""
    rf24_obj.ack = enable
    assert rf24_obj.ack == enable


@pytest.mark.parametrize(
    "pipe", [0, 1, 2, 3, 4, 5, pytest.param(6, marks=pytest.mark.xfail)]
)
@pytest.mark.parametrize("buf", [b"\xFF", pytest.param(b"", marks=pytest.mark.xfail)])
def test_load_ack(rf24_obj: RF24, pipe: int, buf: bytes):
    """test load_ack()"""
    for _ in range(3):
        assert rf24_obj.load_ack(buf, pipe)
    assert not rf24_obj.load_ack(buf, pipe)


@pytest.mark.parametrize("enable", [True, False])
def test_allow_ask_no_ack(rf24_obj: RF24, enable: bool):
    """test allow_ask_no_ack attribute"""
    rf24_obj.allow_ask_no_ack = enable
    assert rf24_obj.allow_ask_no_ack == enable


@pytest.mark.parametrize(
    "buf,dyn_pl",
    [
        (b"\xFF", False),
        (b"\0" * 33, False),
        (b"", False),
        (b"\xFF", True),
        pytest.param(b"\0" * 33, True, marks=pytest.mark.xfail),
        pytest.param(b"", True, marks=pytest.mark.xfail),
    ],
    ids=[
        "static 1 byte",
        "static 33 byte",
        "static 0 byte",
        "dynamic 1 byte",
        "dynamic 33 byte",
        "dynamic 0 byte",
    ],
)
def test_write(rf24_obj: RF24, buf: bytes, dyn_pl: bool):
    """test write()"""
    rf24_obj.dynamic_payloads = dyn_pl
    assert rf24_obj.write(buf, write_only=True)
    assert rf24_obj.write(buf, write_only=True)
    assert rf24_obj.write(buf, ask_no_ack=True)
    assert not rf24_obj.write(buf, write_only=True)


@pytest.mark.parametrize(
    "pipe", list(range(-1, 6)) + [pytest.param(6, marks=pytest.mark.xfail)]
)
def test_address(rf24_obj: RF24, pipe: int):
    """test address()"""
    addr = b"\xCC" * 5
    if pipe < 0:
        rf24_obj.open_tx_pipe(addr)
        assert rf24_obj.address() == addr
    else:
        if pipe != 1:
            rf24_obj.open_rx_pipe(1, addr)
        rf24_obj.open_rx_pipe(pipe, addr)
        assert rf24_obj.address(pipe) == addr


def test_rpd(rf24_obj: RF24):
    """test rpd attribute"""
    assert not rf24_obj.rpd
    rf24_obj._spi._spi.state.registers[9][0] = 1
    assert rf24_obj.rpd


def test_carrier_functions(rf24_obj: RF24, monkeypatch: pytest.MonkeyPatch):
    """test start/stop carrier wave functions"""
    monkeypatch.setattr(rf24_obj, "_is_plus_variant", False)
    rf24_obj.start_carrier_wave()
    assert rf24_obj._spi._spi.state.registers[6][0] & 0x90
    assert rf24_obj.ce_pin
    # some additional settings should be altered for non-plus variants
    assert not rf24_obj.auto_ack
    assert (250, 0) == rf24_obj.get_auto_retries()
    assert rf24_obj._spi._spi.state.registers[0x10] == bytearray(b"\xFF" * 5)
    assert rf24_obj._spi._spi.state.tx_fifo[0] == bytearray(b"\xFF" * 32)
    assert rf24_obj._spi._spi.state.registers[0][0] & 0x73 == 0x73

    rf24_obj.stop_carrier_wave()
    assert not rf24_obj.power
    assert not rf24_obj.ce_pin
    assert not rf24_obj._spi._spi.state.registers[6][0] & 0x90
