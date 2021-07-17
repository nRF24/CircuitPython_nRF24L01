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
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import struct
from .constants import NETWORK_MULTICAST_ADDR

def _is_addr_valid(address):
    """Test if a given address is a valid RF24Network node address."""
    if address in (NETWORK_MULTICAST_ADDR, NETWORK_MULTICAST_ADDR >> 3):
        return True
    byte_count = 0
    while address:
        if (not 0 < (address & 7) <= 5) or (byte_count > 5):
            return False
        address >>= 3
        byte_count += 1
    return True


class RF24NetworkHeader:
    """The header information used for routing network messages.

    :param int to_node: The :ref:`Logical Address <logical address>` designating the
        message's destination.
    :param int message_type: A 1-byte `int` representing the `message_type`.

    .. note:: |can_be_blank|
    """

    def __init__(self, to_node=None, message_type=None):
        self._from = None
        self._to = (to_node & 0xFFFF) if to_node is not None else 0
        self._msg_t = 0
        if message_type is not None:
            # convert the first char in `message_type` to int if it is a string
            self._msg_t = (
                ord(message_type[0]) if isinstance(message_type, str) else message_type
            )
        self._msg_t &= 0xFF
        self._id = RF24NetworkHeader.__next_id
        RF24NetworkHeader.__next_id = (RF24NetworkHeader.__next_id + 1) & 0xFFFF
        self._rsv = 0

    __next_id = 0

    @property
    def from_node(self):
        """Describes the message origin using a
        :ref:`Logical Address <logical address>`. |uint16_t|"""
        return self._from

    @from_node.setter
    def from_node(self, val: int):
        self._from = val & 0xFFFF

    @property
    def to_node(self):
        """Describes the message destination using a
        :ref:`Logical Address <logical address>`. |uint16_t|"""
        return self._to

    @to_node.setter
    def to_node(self, val):
        self._to = val & 0xFFFF

    @property
    def message_type(self):
        """The type of message. This `int` must be less than 256.

        .. seealso::
            `Reserved Message Types <constants.html#reserved-network-message-types>`_
        """
        return self._msg_t

    @message_type.setter
    def message_type(self, val):
        self._msg_t = val & 0xFF

    @property
    def frame_id(self):
        """The sequential identifying number for the frame (relative to the originating
        network node). Each sequential frame's ID is incremented, but frames containing
        fragmented messages have the same ID number. |uint16_t|"""
        return self._id

    @property
    def reserved(self):
        """A single byte reserved for network usage. This will be the sequential ID
        number for fragmented messages, but on the last message fragment, this will be
        the `message_type`. `RF24Mesh` will also use this attribute to hold a newly
        assigned network :ref:`Logical Address <logical address>` for
        `NETWORK_ADDR_RESPONSE` messages."""
        return self._rsv

    @reserved.setter
    def reserved(self, val):
        self._rsv = val & 0xFF

    def decode(self, buffer) -> bool:
        """Decode frame's header from the first 8 bytes of a frame's buffer.
        This function |internal_use|"""
        if len(buffer) < self.__len__():
            return False
        (
            self._from,
            self._to,
            self._id,
            self._msg_t,
            self._rsv,
        ) = struct.unpack("HHHBB", buffer[: self.__len__()])
        return True

    @property
    def buffer(self) -> bytes:
        """This attribute |internal_use|

        :Returns: The entire header as a `bytes` object."""
        return struct.pack(
            "HHHBB",
            0o7777 if self._from is None else self._from,
            self._to,
            self._id,
            self._msg_t,
            self._rsv,
        )

    def __len__(self):
        return 8

    @property
    def is_valid(self) -> bool:
        """A `bool` that describes if the `header`'s
        :ref:`Logical Addresses <logical address>` are valid or not."""
        if self._from is not None and _is_addr_valid(self._from):
            return _is_addr_valid(self._to)
        return False


class RF24NetworkFrame:
    """Structure of a single frame for either a fragmented message of payloads
    or a single payload whose message is less than 25 bytes.

    :param RF24NetworkHeader header: The header describing the frame's `message`.
    :param bytes,bytearray message: The actual `message` containing the payload
        or a fragment of a payload.

    .. note:: |can_be_blank|
    """

    def __init__(self, header: RF24NetworkHeader=None, message=None):
        if header is not None and not isinstance(header, RF24NetworkHeader):
            raise TypeError("header must be a RF24NetworkHeader object")
        if message is not None and not isinstance(message, (bytes, bytearray)):
            raise TypeError("message must be a `bytes` or `bytearray` object")
        self.header = RF24NetworkHeader() if header is None else header
        """The `RF24NetworkHeader` about the frame's message."""
        self.message = bytearray(0) if message is None else bytearray(message)
        """The entire message or a fragment of the message allocated to this
        frame. This attribute is typically a `bytearray` or `bytes` object."""

    def decode(self, buffer) -> bool:
        """Decode `header` & `message` from a ``buffer``. This function |internal_use|

        :Returns: `True` if successful; otherwise `False`.
        """
        if self.header.decode(buffer):
            self.message = buffer[len(self.header) :]
            return True
        return False

    @property
    def buffer(self) -> bytes:
        """This attribute |internal_use|

        :Returns:  The entire object as a `bytes` object."""
        return self.header.buffer + bytes(self.message)

    def __len__(self):
        return len(self.header) + len(self.message)

    @property
    def is_ack_type(self) -> bool:
        """Is the frame to expect a `NETWORK_ACK` message? This function |internal_use|
        """
        return 64 < self.header.message_type < 192
