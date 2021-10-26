# The MIT License (MIT)
#
# Copyright (c) 2020 Brendan Doherty
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
"""This module contains the data structures used foe network packets."""
import struct
from .constants import (
    NETWORK_EXT_DATA,
    NETWORK_MULTICAST_ADDR,
    MSG_FRAG_FIRST,
    MSG_FRAG_MORE,
    MSG_FRAG_LAST,
)

def is_address_valid(address) -> bool:
    """Test if a given address is a valid :ref:`Logical Address <Logical Address>`."""
    if address is None:
        return False
    if address == NETWORK_MULTICAST_ADDR:
        return True
    byte_count = 0
    while address:
        if (not 0 < (address & 7) <= 5) or (byte_count > 5):
            return False
        address >>= 3
        byte_count += 1
    return True


class RF24NetworkHeader:
    """The header information used for routing network messages."""

    def __init__(self, to_node: int=None, message_type=None):
        self.from_node = None  #: |uint16_t|
        self.to_node = (to_node & 0xFFF) if to_node is not None else 0  #: |uint16_t|
        #: The type of message.
        self.message_type = 0 if message_type is None else message_type
        if isinstance(message_type, str):
            # convert the first char to int if `message_type` is a string
            self.message_type = ord(message_type[0])
        else:
            self.message_type &= 0xFF
        self.frame_id = RF24NetworkHeader.__next_id  #: |uint16_t|
        RF24NetworkHeader.__next_id = (RF24NetworkHeader.__next_id + 1) & 0xFFFF
        self.reserved = 0  #: A single byte reserved for network usage.

    __next_id = 0

    def unpack(self, buffer) -> bool:
        """Decode header data from the first 8 bytes of a frame's buffer."""
        if len(buffer) < 8:
            return False
        (
            self.from_node,
            self.to_node,
            self.frame_id,
            self.message_type,
            self.reserved,
        ) = struct.unpack("HHHBB", buffer[:8])
        return True

    def pack(self) -> bytes:
        """This function |internal_use|"""
        return struct.pack(
            "HHHBB",
            0o7777 if self.from_node is None else self.from_node & 0xFFF,
            self.to_node & 0xFFF,
            self.frame_id & 0xFFFF,
            (
                self.message_type
                if not isinstance(self.message_type, str)
                else (ord(self.message_type[0]) if self.message_type else 0)
            ) & 0xFF,
            self.reserved & 0xFF,
        )

    def __len__(self) -> int:
        return 8

    def to_string(self) -> str:
        """:Returns: A `str` describing all of the header's attributes."""
        return "from {} to {} type {} id {} reserved {}".format(
            oct(0o7777 if self.from_node is None else self.from_node),
            oct(self.to_node),
            (
                self.message_type
                if not isinstance(self.message_type, str)
                else (ord(self.message_type[0]) if self.message_type else 0)
            ) & 0xFF,
            self.frame_id,
            self.reserved,
        )


class RF24NetworkFrame:
    """Structure of a single frame."""

    def __init__(self, header: RF24NetworkHeader=None, message=None):
        if header is not None and not isinstance(header, RF24NetworkHeader):
            raise TypeError("header must be a RF24NetworkHeader object")
        if message is not None and not isinstance(message, (bytes, bytearray)):
            raise TypeError("message must be a `bytes` or `bytearray` object")
        self.header = header if header is not None else RF24NetworkHeader()
        """The `RF24NetworkHeader` about the frame's `message`."""
        self.message = bytearray(0) if message is None else bytearray(message)
        """The entire message or a fragment of a message allocated to the frame."""


    def unpack(self, buffer) -> bool:
        """Decode the `header` & `message` from a ``buffer``."""
        if self.header.unpack(buffer):
            self.message = buffer[8:]
            return True
        return False

    def pack(self) -> bytes:
        """This attribute |internal_use|"""
        return self.header.pack() + bytes(self.message)

    def __len__(self) -> int:
        return 8 + len(self.message)

    def is_ack_type(self) -> bool:
        """Check if the frame is to expect a `NETWORK_ACK` message."""
        return 64 < self.header.message_type < 192


class FrameQueue:
    """A class that wraps a `list` with RF24Network Queue behavior."""

    def __init__(self, queue=None):
        #: The maximum number of frames that can be enqueued at once. Defaults to 6.
        self.max_queue_size = 6
        self._queue = []
        if queue is not None:
            while queue:
                self._queue.append(queue.dequeue())
            self.max_queue_size = queue.max_queue_size
        super().__init__()

    def enqueue(self, frame: RF24NetworkFrame) -> bool:
        """Add a `RF24NetworkFrame` to the queue."""
        if self.max_queue_size == len(self._queue):
            return False
        for frm in self._queue:
            if (
                frm.header.from_node == frame.header.from_node
                and frm.header.frame_id == frame.header.frame_id
                and frm.header.message_type == frame.header.message_type
            ):
                return False  # already enqueued this frame
        new_frame = RF24NetworkFrame()
        new_frame.unpack(frame.pack())
        self._queue.append(new_frame)
        return True

    def peek(self) -> RF24NetworkFrame:
        """:Returns: The First Out element without removing it from the queue."""
        return None if not self._queue else self._queue[0]

    def dequeue(self) -> RF24NetworkFrame:
        """:Returns: The First Out element and removes it from the queue."""
        return None if not self._queue else self._queue.pop(0)

    def __len__(self) -> int:
        """:Returns: The number of the enqueued frames."""
        return len(self._queue)

class FrameQueueFrag(FrameQueue):
    """A specialized `FrameQueue` with an additional cache for fragmented frames."""

    def __init__(self, queue=None):
        super().__init__(queue)
        self._frags = RF24NetworkFrame()  # initialize cache

    def enqueue(self, frame: RF24NetworkFrame) -> bool:
        """Add a `RF24NetworkFrame` to the queue."""
        if frame.header.message_type in (MSG_FRAG_FIRST, MSG_FRAG_MORE, MSG_FRAG_LAST):
            if frame.header.message_type == MSG_FRAG_FIRST:
                self._frags.unpack(frame.pack())  # make copy not reference
                return True
            if (
                self._frags.header.from_node is not None  # if not just initialized
                and frame.header.to_node == self._frags.header.to_node
                and frame.header.frame_id == self._frags.header.frame_id
            ):
                if (
                    self._frags.header.reserved - 1 != frame.header.reserved
                    and frame.header.message_type != MSG_FRAG_LAST
                ):
                    # print("dropping non sequential fragment")
                    return False
                self._frags.header.unpack(frame.header.pack())
                self._frags.message += frame.message[:]
                if frame.header.message_type == MSG_FRAG_LAST:
                    if frame.header.reserved == NETWORK_EXT_DATA:
                        # External data needs to be propagated back to update()
                        frame.header.message_type = NETWORK_EXT_DATA  # by reference
                    self._frags.header.message_type = frame.header.reserved
                    return super().enqueue(self._frags)
                return True
            # print("dropping fragment due to missing 1st fragment")
            return False
        return super().enqueue(frame)
