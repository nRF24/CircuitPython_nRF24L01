"""
A module to contain the basic queue implementation for the stack of received messages.
"""
from .constants import (
    NETWORK_FRAG_FIRST,
    NETWORK_FRAG_MORE,
    NETWORK_FRAG_LAST,
    # NETWORK_DEFAULT_ADDR,
    # NETWORK_EXTERNAL_DATA,
    # NETWORK_PING,
    # NETWORK_POLL,
    # TX_NORMAL,
    # TX_ROUTED,
    # MAX_USER_DEFINED_HEADER_TYPE,
    MAX_MESSAGE_SIZE,
)


class Queue:
    """A class that wraps python's list implementation with RF24Network Queue behavior

    :param int size: The maximum size that can be enqueued at once.
    """

    def __init__(self, size=6):
        self._max_size = size
        self._list = []

    def enqueue(self, frame):
        """ add a `RF24NetworkFrame` to the queue. """
        if self._max_size == len(self._list):
            return False
        self._list.append(frame)
        return True

    @property
    def peek(self):
        """ return First Out element without removing it from the queue """
        return self._list[0]

    @property
    def pop(self):
        """ return and remove the First Out element from the queue """
        ret_val = self._list[0]
        del self._list[0]
        return ret_val

    def __len__(self):
        """ return the number of the enqueued items """
        return len(self._list)


_frag_types = (NETWORK_FRAG_FIRST, NETWORK_FRAG_MORE, NETWORK_FRAG_LAST)
""" helper for identifying fragments """


class QueueFrag(Queue):
    """A specialized queue implementation with an additional cache for fragmented frames

    :param int size: The maximum size that can be enqueued at once.
    """

    def __init__(self, size=6):
        super().__init__(size)
        self._frag_cache = []

    def enqueue(self, frame):
        """ add a `RF24NetworkFrame` to the queue. """
        if frame.header.message_type in _frag_types:
            return self._cache_frag_frame(frame)
        return super().enqueue(frame)

    def _cache_frag_frame(self, frame):
        count = 0  # count the number of related fragments already in cache
        for frag_frame in self._frag_cache:
            if frame.header.from_node == frag_frame.header.to_node:
                count += 1
                if frame.header.id == frag_frame.header.id:
                    if frame.header.message_type == NETWORK_FRAG_FIRST and \
                        frag_frame.header.message_type == NETWORK_FRAG_FIRST:
                        return False  # Already received this fragment
        if frame.header.message_type == NETWORK_FRAG_MORE:
            self._frag_cache.append(frame)
            return True
