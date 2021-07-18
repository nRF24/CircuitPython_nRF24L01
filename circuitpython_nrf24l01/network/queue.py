# The MIT License (MIT)
#
# Copyright (c) 2021 Brendan Doherty
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
"""
A module to contain the basic queue implementation for the stack of received messages.
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
from .network_mixin import LoggerMixin
from .constants import (
    NETWORK_FRAG_FIRST,
    NETWORK_FRAG_MORE,
    NETWORK_FRAG_LAST,
    NETWORK_DEBUG_FRAG,
    MAX_FRAG_SIZE,
)
from .packet_structs import RF24NetworkFrame


class FrameQueue(LoggerMixin):
    """A class that wraps python's list implementation with RF24Network Queue behavior.

    :param int max_queue_size: The maximum number of frames that can be enqueued at
        once. Defaults to 6 frames.
    """

    def __init__(self, max_queue_size=6):
        #: The maximum number of frames that can be enqueued at once. Defaults to 6.
        self.max_queue_size = max_queue_size
        self.max_message_length = MAX_FRAG_SIZE
        """The maximum message length (in bytes) allowed in each enqueued frame.
        Any attempt to enqueue a frame that contains a message larger than this
        attribute's value is discarded. Default value is `MAX_FRAG_SIZE` (24 bytes)."""
        self._list = []
        super().__init__()

    def enqueue(self, frame: RF24NetworkFrame):
        """Add a `RF24NetworkFrame` to the queue.

        :Returns: `True` if the frame was added to the queue, or `False` if it was not.
        """
        if (
            self.max_queue_size == len(self._list)
            or len(frame.message) > self.max_message_length
        ):
            return False
        for frm in self._list:
            if (
                frm.header.from_node == frame.header.from_node
                and frm.header.frame_id == frame.header.frame_id
            ):
                return False  # already enqueued this frame
        self._list.append(frame)
        return True

    def peek(self) -> RF24NetworkFrame:
        """:Returns: The First Out element without removing it from the queue."""
        if self._list:
            return self._list[0]
        return None

    def dequeue(self) -> RF24NetworkFrame:
        """:Returns: The First Out element and removes it from the queue."""
        if self._list:
            ret_val = self._list[0]
            del self._list[0]
            return ret_val
        return None

    def __len__(self):
        """:Returns: the number of the enqueued items."""
        return len(self._list)


class FrameQueueFrag(FrameQueue):
    """A specialized queue implementation with an additional cache for fragmented frames

    .. note:: This class will only cache 1 fragmented message at a time. If parts of
        the fragmented message are missing (or duplicate fragments are received), then
        the fragment is discarded. If a new fragmented message is received (before a
        previous fragmented message is completed and reassembled), then the cache
        is reused for the new fragmented message to avoid memory leaks.

    :param int max_queue_size: The maximum number of frames that can be enqueued at
        once. Defaults to 6 frames.
    """

    def __init__(self, max_queue_size=6):
        super().__init__(max_queue_size)
        self._frag_cache = None

    def enqueue(self, frame: RF24NetworkFrame) -> bool:
        """Add a `RF24NetworkFrame` to the queue."""
        if frame.header.message_type in (
            NETWORK_FRAG_FIRST,
            NETWORK_FRAG_MORE,
            NETWORK_FRAG_LAST,
        ):
            return self._cache_frag_frame(frame)
        return super().enqueue(frame)

    def _cache_frag_frame(self, frame: RF24NetworkFrame) -> bool:
        prompt = ""
        if self._logger is not None:
            prompt = "queueing fragment id {}.{} ".format(
                frame.header.frame_id,
                frame.header.reserved
                if frame.header.message_type != NETWORK_FRAG_LAST
                else 1,
            )
        if (
            self._frag_cache is not None
            and frame.header.to_node == self._frag_cache.header.to_node
            and frame.header.frame_id == self._frag_cache.header.frame_id
        ):
            if (
                frame.header.message_type == NETWORK_FRAG_FIRST
                and self._frag_cache.header.message_type == NETWORK_FRAG_FIRST
            ):
                self._log(NETWORK_DEBUG_FRAG, prompt + "duplicate 1st fragment dropped")
                return False  # Already received this fragment
            if len(self._frag_cache.message) + len(
                frame.message
            ) > self.max_message_length or (
                self._frag_cache.header.reserved - 1 != frame.header.reserved
                and frame.header.message_type != NETWORK_FRAG_LAST
            ):
                self._log(
                    NETWORK_DEBUG_FRAG,
                    prompt
                    + "dropping fragment due to excessive size or not sequential",
                )
                return False
            if frame.header.message_type == NETWORK_FRAG_MORE:
                self._log(NETWORK_DEBUG_FRAG, prompt + "type NETWORK_FRAG_MORE")
                self._frag_cache.header = frame.header
                self._frag_cache.message += frame.message
                return True
            if frame.header.message_type == NETWORK_FRAG_LAST:
                self._log(NETWORK_DEBUG_FRAG, prompt + "type NETWORK_FRAG_LAST")
                self._frag_cache.header = frame.header
                self._frag_cache.header.message_type = frame.header.reserved
                self._frag_cache.message += frame.message
                super().enqueue(self._frag_cache)
                self._frag_cache = None
                return True
        if frame.header.message_type == NETWORK_FRAG_FIRST:
            self._log(NETWORK_DEBUG_FRAG, prompt + "type NETWORK_FRAG_FIRST")
            self._frag_cache = frame
            return True
        self._log(
            NETWORK_DEBUG_FRAG, prompt + "dropping fragment due to missing 1st fragment"
        )
        return False
