"""Simple tests for Network data structures."""
from typing import Union, Optional, List
import pytest
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
