"""Tests related to the RF24Network class."""
from typing import Optional, Union, Tuple
import pytest
from circuitpython_nrf24l01.rf24_network import RF24Network
from circuitpython_nrf24l01.network.mixins import _lvl_2_addr
from circuitpython_nrf24l01.network.structs import (
    FrameQueue,
    FrameQueueFrag,
    RF24NetworkFrame,
    RF24NetworkHeader,
)
from circuitpython_nrf24l01.network.constants import (
    MAX_FRAG_SIZE,
    AUTO_ROUTING,
    NETWORK_MULTICAST_ADDR,
)


def test_tx_fifo(net_obj: RF24Network):
    """test fifo(about_tx=True)"""
    for _ in range(3):
        net_obj._rf24.write(b"\0")
    assert net_obj.fifo(about_tx=True, check_empty=False)
    assert not net_obj.fifo(about_tx=True, check_empty=True)
    net_obj._rf24._spi._spi.state.tx_fifo.pop()
    net_obj._rf24._spi._spi.state.registers[0x17][0] = 0
    assert not net_obj.fifo(about_tx=True)
    net_obj.flush_tx()
    assert not net_obj.fifo(about_tx=True, check_empty=False)
    assert net_obj.fifo(about_tx=True, check_empty=True)


def test_rx_fifo(net_obj: RF24Network):
    """test fifo(about_tx=False)"""
    for _ in range(3):
        net_obj._rf24._spi._spi.state.rx_fifo.append(b"\0")
    net_obj._rf24._spi._spi.state.registers[0x17][0] = 2
    assert net_obj.fifo(about_tx=False, check_empty=False)
    assert not net_obj.fifo(about_tx=False, check_empty=True)
    net_obj._rf24._spi._spi.state.rx_fifo.pop()
    net_obj._rf24._spi._spi.state.registers[0x17][0] = 0
    assert not net_obj.fifo(about_tx=False)
    net_obj.flush_rx()
    assert not net_obj.fifo(about_tx=False, check_empty=False)
    assert net_obj.fifo(about_tx=False, check_empty=True)


@pytest.mark.parametrize("power", [True, 0])
def test_power(net_obj: RF24Network, power: Union[bool, int]):
    """test power attribute."""
    net_obj.power = power
    assert net_obj.power is bool(power)


@pytest.mark.parametrize("channel", [0, 125, pytest.param(-1, marks=pytest.mark.xfail)])
def test_channel(net_obj: RF24Network, channel: int):
    """test channel attribute"""
    net_obj.channel = channel
    assert net_obj.channel == channel


@pytest.mark.parametrize("pipe", [None, 0, 1, 2, 3, 4, 5])
@pytest.mark.parametrize("enable", [True, False])
def test_dyn_pl_func(net_obj: RF24Network, pipe: Optional[int], enable: bool):
    """test sett/getter of dynamic_payloads."""
    net_obj.set_dynamic_payloads(enable, pipe)
    if pipe is not None:
        assert net_obj.get_dynamic_payloads(pipe) == enable


@pytest.mark.parametrize("rx_pipe", [0, 1])
def test_listen(net_obj: RF24Network, rx_pipe: int):
    """test listen attribute and open_tx_pipe()."""
    net_obj._rf24.open_rx_pipe(rx_pipe, b"1Node")
    net_obj._rf24.close_rx_pipe(0)
    net_obj._rf24.open_tx_pipe(b"2Node")
    net_obj._rf24.ack = True
    net_obj.listen = False
    assert not net_obj.listen
    net_obj.listen = True
    assert net_obj.listen


@pytest.mark.parametrize(
    "value", [0, -6, -12, -18, (0, False), pytest.param(20, marks=pytest.mark.xfail)]
)
def test_pa_level(net_obj: RF24Network, value: Union[int, Tuple[int, bool]]):
    """test pa_level and is_lna_enabled attributes."""
    net_obj.pa_level = value
    if isinstance(value, tuple):
        assert net_obj.is_lna_enabled is value[1]
        assert net_obj.pa_level == value[0]
    else:
        assert net_obj.is_lna_enabled
        assert net_obj.pa_level == value


@pytest.mark.parametrize("rate", [1, 2, 250, pytest.param(3, marks=pytest.mark.xfail)])
def test_data_rate(net_obj: RF24Network, rate: int):
    """test data_rate attribute"""
    net_obj.data_rate = rate
    assert net_obj.data_rate == rate


@pytest.mark.parametrize("length", [0, 1, 2])
def test_crc(net_obj: RF24Network, length: int):
    """test crc attribute"""
    net_obj._rf24.auto_ack = False  # allow disabling CRC
    net_obj.crc = length
    assert net_obj.crc == length
    net_obj._rf24.auto_ack = True  # if CRC is disabled then this will enable it
    assert net_obj.crc > 0


@pytest.mark.parametrize("delay", [500, 1500])
@pytest.mark.parametrize("count", [5, 15])
def test_auto_retries(net_obj: RF24Network, delay: int, count: int):
    """test ard/arc attributes and get_auto_retries()"""
    net_obj.set_auto_retries(delay, count)
    assert net_obj.get_auto_retries() == (delay, count)
    assert net_obj._rf24.arc == count
    assert net_obj._rf24.ard == delay
    net_obj._rf24.arc = 0
    net_obj._rf24.ard = 0
    assert net_obj._rf24.arc == 0
    assert net_obj._rf24.ard == 250


def test_last_tx_arc(net_obj: RF24Network):
    """test last_tx_arc()"""
    assert not net_obj.last_tx_arc


def test_irq_config(net_obj: RF24Network):
    """test interrupt_config()"""
    net_obj.interrupt_config(0, 0, 0)  # disable all
    assert net_obj._rf24._spi._spi.state.registers[0][0] & 0x70 == 0x70
    net_obj.interrupt_config()  # enable all
    assert not net_obj._rf24._spi._spi.state.registers[0][0] & 0x70


@pytest.mark.parametrize(
    "logical",
    [0o0, 0o1, 0o12, 0o123, 0o1234, pytest.param(0o20, marks=pytest.mark.xfail)],
)
def test_ctor(spi_obj, logical: int):
    """test constructor's address validation."""
    RF24Network(*spi_obj, logical)


def test_context(spi_obj):
    """test context manager"""
    network_b_node = RF24Network(*spi_obj, 5)
    network_a_node = RF24Network(*spi_obj, 1)

    # let network_b use different values for address_prefix and address_suffix
    with network_b_node as net_b:
        net_b.address_prefix = bytearray([0xDB])
        net_b.address_suffix = bytearray([0xDD, 0x99, 0xB6, 0xD9, 0x9D, 0x66])

        # re-assign the node_address for the different physical addresses to be used
        net_b.node_address = 5

    with network_a_node as net_a:
        assert net_a.address_prefix == bytearray([0xCC])
        assert net_a.address_suffix == bytearray(b"\xC3\x3C\x33\xCE\x3E\xE3")
    with network_b_node as net_b:
        assert net_b.address_prefix == bytearray([0xDB])
        assert net_b.address_suffix == bytearray(b"\xDD\x99\xB6\xD9\x9D\x66")


@pytest.mark.parametrize(
    "logical",
    [0o0, 0o1, 0o12, 0o123, 0o1234, pytest.param(0o20, marks=pytest.mark.xfail)],
)
def test_id(net_obj: RF24Network, logical: int):
    """test RF24Network node_address"""
    net_obj.node_address = logical
    assert net_obj.node_address == logical
    assert net_obj.parent == (logical & (net_obj._mask >> 3))
    for pipe in range(6):
        assert net_obj.address(pipe) == net_obj._pipe_address(logical, pipe)


def test_print_details(net_obj: RF24Network, capsys: pytest.CaptureFixture):
    """verify network node_address is included with print_details()."""
    net_obj.print_details(dump_pipes=True)
    out, _ = capsys.readouterr()
    assert "Network node address" in out


def test_fragmentation(net_obj: RF24Network):
    """test fragmentation attribute"""
    assert isinstance(net_obj.queue, FrameQueueFrag)
    net_obj.queue.enqueue(RF24NetworkFrame(message=b"test"))
    assert net_obj.available()
    net_obj.fragmentation = False
    assert isinstance(net_obj.queue, FrameQueue)
    assert net_obj.peek().message == b"test"
    net_obj.fragmentation = not net_obj.fragmentation
    assert isinstance(net_obj.queue, FrameQueueFrag)
    assert net_obj.read().message == b"test"


@pytest.mark.parametrize("allow", [True, False])
@pytest.mark.parametrize("relay", [True, False])
def test_multicast_relay(net_obj: RF24Network, allow: bool, relay: bool):
    """test multicast_relay and allow_multicast attributes"""
    net_obj.allow_multicast = allow
    net_obj.multicast_relay = relay
    assert net_obj.multicast_relay is (allow and relay)


@pytest.mark.parametrize("level", list(range(5)))
def test_multicast_level(net_obj: RF24Network, level: int):
    """test multicast_level attribute"""
    net_obj.multicast_level = level
    assert net_obj.address(0) == net_obj._pipe_address(_lvl_2_addr(level), 0)
    assert net_obj.multicast_level == level


@pytest.mark.parametrize(
    "message",
    [b"\0", pytest.param(None, marks=pytest.mark.xfail)],
)
def test_send(net_obj: RF24Network, message: Optional[bytes]):
    """test send()"""
    assert net_obj.send(RF24NetworkHeader(0o4), message)


@pytest.mark.parametrize(
    "to_node",
    [NETWORK_MULTICAST_ADDR, 0o4, pytest.param(AUTO_ROUTING, marks=pytest.mark.xfail)],
    ids=["multicast", "direct", "invalid"],
)
@pytest.mark.parametrize("direction", [AUTO_ROUTING, 0o4], ids=["auto", "direct"])
@pytest.mark.parametrize("size", [4, MAX_FRAG_SIZE + 1])
def test_write(net_obj: RF24Network, to_node: int, direction: int, size: int):
    """test write()"""
    # use odd config to trigger payload truncating branch
    net_obj.fragmentation = False
    net_obj.max_message_length = MAX_FRAG_SIZE * 2
    assert net_obj.write(
        RF24NetworkFrame(RF24NetworkHeader(to_node), b"\0" * size), direction
    )


@pytest.mark.parametrize("level", [None, 4])
@pytest.mark.parametrize("size", [4, MAX_FRAG_SIZE + 1])
def test_multicast(net_obj: RF24Network, level: Optional[int], size: int):
    """test multicast()"""
    # use odd config to trigger payload truncating branch
    net_obj.fragmentation = False
    net_obj.max_message_length = MAX_FRAG_SIZE * 2
    assert net_obj.multicast(b"\0" * size, "T", level)
