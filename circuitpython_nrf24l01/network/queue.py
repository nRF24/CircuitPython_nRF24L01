"""
A module to contain the basic queue implementation for the stack of received messages.
"""
from .network_mixin import logging
from .constants import (
    NETWORK_FRAG_FIRST,
    NETWORK_FRAG_MORE,
    NETWORK_FRAG_LAST,
    NETWORK_DEBUG_FRAG,
)


class Queue:
    """A class that wraps python's list implementation with RF24Network Queue behavior

    :param int size: The maximum size that can be enqueued at once.
    """

    def __init__(self, max_message_length, max_queue_size=6):
        self._max_q_size = max_queue_size
        self._max_msg_len = max_message_length
        self._list = []
        self._logger = None
        if logging is not None:
            self._logger = logging.getLogger(type(self).__name__)

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

    @property
    def logger(self):
        """Get/Set the current ``Logger()``."""
        return self._logger

    @logger.setter
    def logger(self, val):
        if logging is not None and isinstance(val, logging.Logger):
            self._logger = val

    def _log(self, level, prompt, force_print=False):
        if self.logger is not None:
            self.logger.log(level, prompt)
        elif force_print:
            print(prompt)


class QueueFrag(Queue):
    """A specialized queue implementation with an additional cache for fragmented frames

    :param int size: The maximum size that can be enqueued at once.
    """

    def __init__(self, max_message_length, max_queue_size=6):
        super().__init__(max_message_length, max_queue_size)
        self._frag_cache = None

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
        prompt = "queueing fragment id {}.{} ".format(
            frame.header.frame_id,
            frame.header.reserved,
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
            if (
                len(self._frag_cache.message) + len(frame.message) > self._max_msg_len
                or (
                    self._frag_cache.header.reserved - 1 != frame.header.reserved
                    and frame.header.message_type != NETWORK_FRAG_LAST
                )
            ):
                self._log(
                    NETWORK_DEBUG_FRAG,
                    prompt + "dropping fragment due to excessive size or not sequential"
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
            self._log(NETWORK_DEBUG_FRAG,  prompt + "type NETWORK_FRAG_FIRST")
            self._frag_cache = frame
            return True
        self._log(
            NETWORK_DEBUG_FRAG,
            prompt + "dropping fragment due to missing 1st fragment"
        )
        return False