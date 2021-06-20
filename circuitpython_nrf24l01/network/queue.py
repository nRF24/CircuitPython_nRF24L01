"""
A module to contain the basic queue implementation for the stack of received messages.
"""
from .constants import (
    NETWORK_FRAG_FIRST,
    NETWORK_FRAG_MORE,
    NETWORK_FRAG_LAST,
)


class Queue:
    """A class that wraps python's list implementation with RF24Network Queue behavior

    :param int size: The maximum size that can be enqueued at once.
    """

    def __init__(self, max_message_length, max_queue_size=6):
        self._max_q_size = max_queue_size
        self._max_msg_len = max_message_length
        self._list = []

    def enqueue(self, frame):
        """add a `RF24NetworkFrame` to the queue."""
        if (
            self._max_q_size == len(self._list)
            or len(frame.message) > self._max_msg_len
        ):
            return False
        for frm in self._list:
            if (
                frm.header.to_node == frame.header.to_node
                and frm.header.frame_id == frame.header.frame_id
            ):
                return False  # already enqueued this frame
        self._list.append(frame)
        return True

    @property
    def peek(self):
        """return First Out element without removing it from the queue"""
        return self._list[0]

    @property
    def dequeue(self):
        """return and remove the First Out element from the queue"""
        ret_val = self._list[0]
        del self._list[0]
        return ret_val

    def __len__(self):
        """return the number of the enqueued items"""
        return len(self._list)


class QueueFrag(Queue):
    """A specialized queue implementation with an additional cache for fragmented frames

    :param int size: The maximum size that can be enqueued at once.
    """

    def __init__(self, max_message_length, max_queue_size=6):
        super().__init__(max_message_length, max_queue_size)
        self._frag_cache = []

    def enqueue(self, frame):
        """add a `RF24NetworkFrame` to the queue."""
        if (
            frame.header.message_type in (
                NETWORK_FRAG_FIRST, NETWORK_FRAG_MORE, NETWORK_FRAG_LAST
            )
        ):
            return self._cache_frag_frame(frame)
        return super().enqueue(frame)

    def _cache_frag_frame(self, frame):
        print("queueing fragment id", frame.header.frame_id, end="")
        for i, frag_frm in enumerate(self._frag_cache):
            if (
                frame.header.to_node == frag_frm.header.to_node
                and frame.header.frame_id == frag_frm.header.frame_id
            ):
                if (
                    frame.header.message_type == NETWORK_FRAG_FIRST
                    and frag_frm.header.message_type == NETWORK_FRAG_FIRST
                ):
                    print("duplicate first fragment dropped")
                    return False  # Already received this fragment
                if (
                    len(frag_frm.message) + len(frame.message) > self._max_msg_len
                    or frag_frm.header.frame_id != frame.header.frame_id
                ):
                    # frame's message size will exceed max size allowed
                    # or frame's ID is sequentially out of order
                    print("dropping fragment")
                    return False
                if frame.header.message_type == NETWORK_FRAG_MORE:
                    print(" type", frame.header.message_type)
                    self._frag_cache[i].header = frame.header
                    self._frag_cache[i].message += frame.message
                    return True
                if frame.header.message_type == NETWORK_FRAG_LAST:
                    print(" type", frame.header.message_type)
                    frag_frm.header = frame.header
                    frag_frm.header.message_type = frame.header.reserved
                    frag_frm.message += frame.message
                    super().enqueue(frag_frm)
                    del self._frag_cache[i]
                    return True
        if frame.header.message_type == NETWORK_FRAG_FIRST:
            print(" type", frame.header.message_type)
            self._frag_cache.append(frame)
            return True
        return False
