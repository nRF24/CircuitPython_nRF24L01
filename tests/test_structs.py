"""Simple tests for Network data structures."""
import struct
from typing import Union, Optional, List
import pytest
from circuitpython_nrf24l01.fake_ble import (
    chunk,
    FakeBLE,
    QueueElement,
    ServiceData,
    BatteryServiceData,
    TemperatureServiceData,
    UrlServiceData,
    BATTERY_UUID,
    TEMPERATURE_UUID,
    EDDYSTONE_UUID,
)
from circuitpython_nrf24l01.network.structs import (
    is_address_valid,
    RF24NetworkHeader,
    RF24NetworkFrame,
    FrameQueue,
    FrameQueueFrag,
)
from circuitpython_nrf24l01.network.constants import (
    MSG_FRAG_FIRST,
    MSG_FRAG_MORE,
    MSG_FRAG_LAST,
    NETWORK_EXT_DATA,
)


@pytest.mark.parametrize(
    "address",
    [
        pytest.param(None, marks=pytest.mark.xfail),
        pytest.param(0o70, marks=pytest.mark.xfail),
        pytest.param(0o67, marks=pytest.mark.xfail),
        0o4444,
        0o100,
        0,
    ],
)
def test_is_valid_addr(address: Optional[int]):
    """test address validation."""
    assert is_address_valid(address)


@pytest.mark.parametrize("to_node", [0o1, 0o4444, 0o7777])
@pytest.mark.parametrize("msg_t", [255, "T", -5])
def test_header(to_node: int, msg_t: Union[str, int]):
    """test a Network Header"""
    header = RF24NetworkHeader(to_node=to_node, message_type=msg_t)
    if isinstance(msg_t, str):
        assert header.message_type == ord(msg_t[0])
    else:
        assert msg_t & 0xFF == header.message_type
    header.message_type = msg_t
    assert header.to_string()
    data = header.pack()
    assert len(data) == len(header)
    assert header.to_node == to_node
    assert header.frame_id == header._RF24NetworkHeader__next_id - 1
    assert not header.unpack(b"\0")
    assert header.unpack(data)


@pytest.mark.parametrize(
    "header", [None, RF24NetworkHeader(), pytest.param(b"x", marks=pytest.mark.xfail)]
)
@pytest.mark.parametrize("msg", [None, b"", pytest.param("x", marks=pytest.mark.xfail)])
def test_net_frame(header, msg):
    """test Network Frame"""
    frame = RF24NetworkFrame(header=header, message=msg)
    data = frame.pack()
    assert len(data) == len(frame)
    assert not frame.unpack(b"\0")
    assert frame.unpack(data)
    assert not frame.is_ack_type()


def test_queue():
    """test Frame Queue"""
    queue = FrameQueue()
    count = queue.max_queue_size
    assert queue.peek() is None
    assert queue.dequeue() is None
    for i in range(count):
        assert queue.enqueue(RF24NetworkFrame(RF24NetworkHeader(), bytes([count - i])))
        assert not queue.enqueue(queue.peek())
    assert len(queue) == count
    queue = FrameQueue(queue)
    while len(queue):
        msg = queue.dequeue().message
        assert msg[0] == len(queue) + 1


@pytest.mark.parametrize(
    "types",
    [
        [MSG_FRAG_FIRST, MSG_FRAG_LAST],
        [MSG_FRAG_FIRST, MSG_FRAG_MORE, MSG_FRAG_LAST],
        pytest.param([MSG_FRAG_MORE, MSG_FRAG_LAST], marks=pytest.mark.xfail),
        pytest.param(
            [MSG_FRAG_FIRST, MSG_FRAG_MORE, MSG_FRAG_MORE], marks=pytest.mark.xfail
        ),
    ],
    ids=[
        "2 fragments",
        "3 fragments",
        "no beginning fragment",
        "non-sequential fragments",
    ],
)
def test_frag_queue(types: List[int]):
    """test de-fragmenting Frame Queue"""
    queue = FrameQueueFrag()
    frame = RF24NetworkFrame()  # frame_id must be constant for this
    assert queue.enqueue(frame)
    for i, typ in enumerate(types):
        frame.header.message_type = typ
        frame.message = bytes([i])
        if typ == MSG_FRAG_LAST:
            # just for better code coverage
            frame.header.reserved = NETWORK_EXT_DATA
        else:
            # mock sequence of frames with frag type (allows for non-sequential test)
            frame.header.reserved = MSG_FRAG_LAST - typ
        print("queueing frame", frame.header.to_string())
        assert queue.enqueue(frame)


@pytest.mark.parametrize("dev_name", [b"n", b"\xFF", None])
def test_queue_element(ble_obj: FakeBLE, dev_name: Optional[bytes]):
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
    url.data = "https://null.com/"  # payload size is a significant factor with URLs
    url.pa_level_at_1_meter = 20
    assert "https://null.com/" in str(url)
    assert url.uuid == struct.pack("<H", EDDYSTONE_UUID)
    assert url.pa_level_at_1_meter == 20
    assert len(url) == 10  # enough to include a 1 char name and pa_level in payload

    ble_obj.name = dev_name
    ble_obj.show_pa_level = True
    for data in [batt, temp, url]:
        queue = QueueElement(ble_obj._make_payload(chunk(data.buffer, 0x16)))
        assert queue.mac == ble_obj.mac
        if isinstance(queue.name, str):
            assert queue.name == ble_obj.name.decode(encoding="utf-8")
        else:
            assert queue.name == ble_obj.name
        assert queue.pa_level == ble_obj.pa_level
        for chunk_d in queue.data:
            if isinstance(chunk_d, ServiceData):
                assert chunk_d.data == data.data
