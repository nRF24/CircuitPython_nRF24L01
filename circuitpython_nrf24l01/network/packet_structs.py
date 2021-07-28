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

def is_address_valid(address):
    """Test if a given address is a valid :ref:`Logical Address <Logical Address>`."""
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
    """The header information used for routing network messages.

    :param int to_node: The :ref:`Logical Address <logical address>` designating the
        message's destination.
    :param int,str message_type: A 1-byte `int` representing the `message_type`. If a
        `str` is passed, then the first character's numeric ASCII representation is
        used.

    .. note:: |can_be_blank|
    """

    def __init__(self, to_node=None, message_type=None):
        self.from_node = None
        """Describes the message origin using a
        :ref:`Logical Address <logical address>`. |uint16_t|"""

        self.to_node = (to_node & 0xFFF) if to_node is not None else 0
        """Describes the message destination using a
        :ref:`Logical Address <logical address>`. |uint16_t|"""

        self.message_type = 0
        """The type of message. This `int` must be less than 256.

        .. hint::
            Users are encouraged to specify a number in range [0, 127] (basically less
            than or equal to `SYS_MSG_TYPES`) as there are
            `Reserved Message Types <constants.html#reserved-network-message-types>`_.
        """
        if message_type is not None:
            # convert the first char in `message_type` to int if it is a string
            self.message_type = (
                ord(message_type[0]) if isinstance(message_type, str) else message_type
            )
        self.message_type &= 0xFF

        self.frame_id = RF24NetworkHeader.__next_id
        """The sequential identifying number for the frame (relative to the originating
        network node). Each sequential frame's ID is incremented, but frames containing
        fragmented messages have the same ID number. |uint16_t|"""
        # pylint: disable=unused-private-member
        RF24NetworkHeader.__next_id = (RF24NetworkHeader.__next_id + 1) & 0xFFFF
        # pylint: enable=unused-private-member
        self.reserved = 0
        """A single byte reserved for network usage. This will be the sequential ID
        number for fragmented messages, but on the last message fragment, this will be
        the `message_type`. `RF24Mesh` will also use this attribute to hold a newly
        assigned network :ref:`Logical Address <logical address>` for
        `NETWORK_ADDR_RESPONSE` messages."""

    __next_id = 0

    def from_bytes(self, buffer):
        """Decode frame's header from the first 8 bytes of a frame's buffer.
        This function |internal_use|

        :Returns: `True` if successful; otherwise `False`.
        """
        if len(buffer) < self.__len__():
            return False
        (
            self.from_node,
            self.to_node,
            self.frame_id,
            self.message_type,
            self.reserved,
        ) = struct.unpack("HHHBB", buffer[: self.__len__()])
        return True

    def to_bytes(self):
        """This attribute |internal_use|

        :Returns: The entire header as a `bytes` object."""
        return struct.pack(
            "HHHBB",
            0o7777 if self.from_node is None else self.from_node & 0xFFF,
            self.to_node & 0xFFF,
            self.frame_id & 0xFFFF,
            self.message_type & 0xFF,
            self.reserved & 0xFF,
        )

    def __len__(self):
        return 8

    def is_valid(self):
        """Check if the `header`'s :ref:`Logical Addresses <logical address>` are valid
        or not."""
        if self.from_node is not None and is_address_valid(self.from_node):
            return is_address_valid(self.to_node)
        return False

    def to_string(self):
        """Returns a `str` describing all of the header's attributes."""
        return "from {} to {} type {} id {} reserved {}".format(
            oct(self.from_node),
            oct(self.to_node),
            self.message_type,
            self.frame_id,
            self.reserved,
        )


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
        self.header = header if header is not None else RF24NetworkHeader()
        """The `RF24NetworkHeader` about the frame's `message`."""
        self.message = bytearray(0) if message is None else bytearray(message)
        """The entire message or a fragment of the message allocated to the
        frame. This attribute is typically a `bytearray` or `bytes` object."""

    def from_bytes(self, buffer):
        """Decode `header` & `message` from a ``buffer``. This function |internal_use|

        :Returns: `True` if successful; otherwise `False`.
        """
        if self.header.from_bytes(buffer):
            self.message = buffer[len(self.header) :]
            return True
        return False

    def to_bytes(self):
        """This attribute |internal_use|

        :Returns:  The entire object as a `bytes` object."""
        return self.header.to_bytes() + bytes(self.message)

    def __len__(self):
        return len(self.header) + len(self.message)

    def is_ack_type(self):
        """Check if the frame is to expect a `NETWORK_ACK` message. This function
        |internal_use|"""
        return 64 < self.header.message_type < 192
