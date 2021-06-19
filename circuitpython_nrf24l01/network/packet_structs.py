"""This module contains the data structures used foe network packets."""
import struct


def _is_addr_valid(address):
    """Test is a given address is a valid RF24Network node address."""
    byte_count = 0
    while address:
        if (not 0 <= (address & 7) < 8) or (byte_count > 5):
            return False
        address >>= 3
        byte_count += 1
    return True


class RF24NetworkHeader:
    """The header information used for routing network messages.

    :param int to_node: The address designating the message's destination.
    :param int message_type: The pre-defined message type describing
        the message related to this header.

    .. note:: These parameters can be left unspecified to create a blank
        header that can be augmented after instantiation.
    """

    def __init__(self, to_node=None, message_type=None):
        self._from = 0
        self._to = to_node or 0
        self._to &= 0xFFFF
        self._msg_t = 0
        if message_type is not None:
            self._msg_t = (
                ord(message_type) if isinstance(message_type, str) else message_type
            )
        self._msg_t &= 0xFF
        self._id = RF24NetworkHeader.__next_id
        RF24NetworkHeader.__next_id = (RF24NetworkHeader.__next_id + 1) & 0xFFFF
        self._rsv = 0

    __next_id = 0

    @property
    def from_node(self):
        """Describes the message origin. This attribute is truncated to a
        2-byte `int`."""
        return self._from

    @from_node.setter
    def from_node(self, val: int):
        self._from = val & 0xFFFF

    @property
    def to_node(self):
        """Describes the message destination. This attribute is truncated to a
        2-byte `int`."""
        return self._to

    @to_node.setter
    def to_node(self, val):
        self._to = val & 0xFFFF

    @property
    def message_type(self):
        """The type of message. This `int` must be less than 256."""
        return self._msg_t

    @message_type.setter
    def message_type(self, val):
        self._msg_t = val & 0xFF

    @property
    def frame_id(self):
        """Describes the unique id for the frame. Each frame's id is
        incremented sequentially, but fragmented frames have the same id.
        This attribute is truncated to a 2-byte `int`."""
        return self._id

    @property
    def reserved(self):
        """A single byte reserved for network usage. This will be the
        fragment_id, but on the last fragment this will be the header_type."""
        return self._rsv

    @reserved.setter
    def reserved(self, val):
        self._rsv = val & 0xFF

    def decode(self, buffer):
        """decode frame header for first 9 bytes of the payload.
        This function is meant for library internal usage."""
        if len(buffer) < self.__len__():
            return False
        (
            self._from,
            self._to,
            self._id,
            self._msg_t,
            self._rsv,
        ) = struct.unpack("hhhbb", buffer[: self.__len__()])
        return True

    @property
    def buffer(self):
        """Return the entire header as a `bytes` object. This is similar to
        TMRh20's ``RF24NetworkHeader::toString()``."""
        return struct.pack(
            "hhhbb",
            self._from,
            self._to,
            self._id,
            self._msg_t,
            self._rsv,
        )

    def __len__(self):
        return 8

    @property
    def is_valid(self):
        """A `bool` that describes if the `header` addresses are valid or not."""
        if _is_addr_valid(self._from):
            return _is_addr_valid(self._to)
        return False


class RF24NetworkFrame:
    """Structure of a single frame for either a fragmented message of payloads
    or a single payload of less than 23 bytes.

    :param RF24NetworkHeader header: The header describing the message's frame
    :param bytes,bytearray message: The actual message containing the payload
        or a fragment of a payload.

    .. note:: These parameters can be left unspecified to create a blank
        header and message that can be augmented after instantiation.
    """

    def __init__(self, header=None, message=None):
        self.header = header
        """The `RF24NetworkHeader` of the message."""
        if not isinstance(header, RF24NetworkHeader):
            self.header = RF24NetworkHeader()
        self.message = bytearray(0) if message is None else bytearray(message)
        """The entire message or a fragment of the message allocated to this
        frame. This attribute is a `bytearray`."""

    def decode(self, buffer):
        """Decode header & message from ``buffer``. Returns `True` if
        successful; otherwise `False`."""
        if self.header.decode(buffer):
            self.message = buffer[len(self.header) :]
            return True
        return False

    @property
    def buffer(self):
        """Return the entire object as a `bytes` object."""
        return self.header.buffer + bytes(self.message)

    def __len__(self):
        return len(self.header) + len(self.message)

    @property
    def is_ack_type(self):
        """Is the frame to expect a network ACK? (for internal use)"""
        return 64 < self.header.message_type < 192
