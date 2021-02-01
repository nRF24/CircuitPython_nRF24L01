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
"""rf24_network module containing the base class RF24Network"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import struct
from .constants import *
from ..rf24 import RF24

_frag_types = (
    NETWORK_FRAG_FIRST,
    NETWORK_FRAG_MORE,
    NETWORK_FRAG_LAST,
)  #: helper for identifying fragments

def _is_addr_valid(address):
    """Test is a given address is a valid RF24Network node address."""
    byte_count = 0
    while address:
        if (not 0 <= (address & 7) < 8) or (byte_count > 5):
            return False
        address >>= 3
        byte_count += 1
    return True


def _pipe_address(node_address, pipe_number):
    """translate node address for use on all pipes"""
    address_translation = [0xC3, 0x3C, 0x33, 0xCE, 0x3E, 0xE3, 0xEC]
    result, count, dec = ([0xCC] * 5, 1, node_address)
    while dec:
        if pipe_number or not node_address:
            result[count] = address_translation[dec % 8]
        dec = int(dec / 8)
        count += 1
    if pipe_number or not node_address:
        result[0] = address_translation[pipe_number]
        result[1] = address_translation[count - 1]
    return bytearray(result)


def _level_to_address(level):
    """translate octal tree ``level`` into a node_address"""
    level_addr = 0
    if level:
        level_addr = 1 << ((level - 1) * 3)
    return level_addr


# pylint: enable=too-few-public-methods
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
        self._msg_t = message_type or 0
        self._id = 0
        self._rsv = 0
        self._next = 1

    @property
    def from_node(self):
        """Describes the message origin. This attribute is truncated to a
        2-byte `int`."""
        return self._from

    @from_node.setter
    def from_node(self, val):
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
        """Describes the unique id for the frame. This attribute is truncated
        to a 2-byte `int`."""
        return self._id

    @frame_id.setter
    def frame_id(self, val):
        self._id = val & 0xFFFF

    @property
    def next_id(self):
        """points to the next sequential message to be sent. This attribute is
        truncated to a 2-byte `int`."""
        return self._next

    @next_id.setter
    def next_id(self, val):
        self._next = val & 0xFFFF

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
            self._next,
        ) = struct.unpack("hhhbbh", buffer[: self.__len__()])
        return True

    @property
    def buffer(self):
        """Return the entire header as a `bytes` object. This is similar to
        TMRh20's ``RF24NetworkHeader::toString()``."""
        return struct.pack(
            "hhhbbh",
            self._from,
            self._to,
            self._id,
            self._msg_t,
            self._rsv,
            self._next,
        )

    def __len__(self):
        return 10

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
        header that can be augmented after instantiation.
    """

    def __init__(self, header=None, message=None):
        self.header = header or RF24NetworkHeader()
        """The `RF24NetworkHeader` of the message."""
        self.message = message or bytearray(0)
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
        """Return the entire object as a `bytearray`."""
        return bytearray(self.header.buffer + self.message)

    def __len__(self):
        return len(self.header) + len(self.message)


class RF24Network:
    """The object used to instantiate the nRF24L01 as a network node.

    :param int node_address: The octal `int` for this node's address
    :param int channel: The RF channel used by the RF24Network
    """

    multicast = True  #: enable (`True`) or disable (`False`) multicasting
    multicast_relay = True
    """Enabling this will allow this node to automatically forward received
    multicast frames to the next highest multicast level. Duplicate frames are
    filtered out, so multiple forwarding nodes at the same level should not
    interfere. Forwarded payloads will also be received."""
    max_message_length = 144
    """If a network node is driven by the TMRh20 RF24Network library on a
    ATTiny-based board, set this to ``72``."""
    def __init__(self, spi, csn_pin, ce_pin, node_address, spi_frequency=10000000):
        if not _is_addr_valid(node_address):
            raise ValueError("node_address argument is invalid or malformed")
        self._radio = RF24(spi, csn_pin, ce_pin, spi_frequency=spi_frequency)

        # setup public proprties
        self.debug = NETWORK_DEBUG
        """controls the debugging prompts. each bit it reserved for use with
        ``DEBUG constants``"""
        self.fragmentation = True
        #: enable (`True`) or disable (`False`) message fragmentation
        self.ret_sys_msg = False  #: for use with RF24Mesh (unsupported)

        # setup node_address & private properies
        self._node_address = node_address
        self._node_mask = 0xFFFF
        self._multicast_level = 0
        while self._node_address & self._node_mask:
            self._node_mask <<= 3
            self._multicast_level += 1
        self._node_mask = ~self._node_mask
        for i in range(6):
            self._radio.open_rx_pipe(i, _pipe_address(node_address, i))
        self._radio.ack = True
        self._radio.set_auto_retries(((node_address % 6) + 1) * 2 + 3, 5)
        self._radio.listen = True
        self._queue = []  # each item is a 2-tuple containing header & message

    @property
    def channel(self):
        """The channel used by the network."""
        return self._radio.channel

    @channel.setter
    def channel(self, val):
        self._radio.channel = val

    def update(self):
        """keep the network layer current; returns the next header"""

        ret_val = 0  # sentinal indicating there is nothing to report
        while self._radio.available():
            # grab the frame from RX FIFO
            frame_buf = self._radio.read()
            frame = RF24NetworkFrame()
            if self.debug:
                print("Received packet:", frame_buf)

            if not frame.decode(frame_buf) or not frame.header.is_valid:
                if self.debug:
                    print(
                        "discarding packet due to inadequate length"
                        " or bad network addresses."
                    )
                # del frame
                continue

            ret_val = frame.header.message_type
            if frame.header.to_node == self._node_address:
                # frame was directed to this node
                if ret_val == NETWORK_PING:
                    continue

                # used for RF24Mesh
                if ret_val == NETWORK_ADDR_RESPONSE:
                    requester = NETWORK_DEFAULT_ADDR
                    if requester != self._node_address:
                        frame.header.to_node = requester
                        # self.write(frame.header.to_node, USER_TX_TO_PHYSICAL_ADDR)
                        continue
                if ret_val == NETWORK_ADDR_REQUEST and self._node_address:
                    frame.header.from_node = self._node_address
                    frame.header.to_node = 0
                    # self.write(frame.header.to_node, TX_NORMAL)
                    continue

                if (self.ret_sys_msg and ret_val > 127) or ret_val == NETWORK_ACK:
                    if ret_val not in _frag_types + (NETWORK_EXTERNAL_DATA,):
                        return ret_val

                self._queue.append(frame)
            else:  # frame was not directed to this node
                if self.multicast:
                    if frame.header.to_node == 0o100:
                        # used by RF24Mesh
                        if (
                            frame.header.message_type == NETWORK_POLL
                            and self._node_address != NETWORK_DEFAULT_ADDR
                        ):
                            pass

                elif self._node_address != NETWORK_DEFAULT_ADDR:
                    # self.write(frame.header.to_node, 1)  # pass it along
                    ret_val = 0  # indicate its a routed payload
        # end while _radio.available()
        return ret_val

    def available(self):
        """Is there a message for this node?"""
        return bool(len(self._queue))

    @property
    def peek_header(self):
        """return the next available message's header from the internal queue
        without removing it from the queue"""
        return self._queue[0][0]

    @property
    def peek(self):
        """return the next available header & message from the internal queue
        without removing it from the queue"""
        return self._queue[0]

    def read(self):
        """Get the next available header & message from internal queue. This
        differs from `peek` because this function also removes the header &
        message from the internal queue.

        :returns: A 2-item tuple containing the next available

            1. `RF24NetworkHeader`
            2. a `bytearray` message
        """
        ret = self._queue[0]
        del self._queue[0]
        return ret

    def send(self, header, message):
        """deliver a message according to the header's information """
        self.write(header, message, 0o70)

    # pylint: disable=unnecessary-pass
    def write(self, header, to_node):
        """deliver a message with a header routed to ``to_node`` """
        header.from_node = self._node_address

    # pylint: enable=unnecessary-pass
    def _is_descendant(self, node_address):
        """is the given node_address a descendant of self._node_address"""
        return node_address & self._node_mask == self._node_address

    def _is_direct_child(self, node_address):
        """is the given node_address a direct child of self._node_address"""
        if self._is_descendant(node_address):
            return not node_address & ((~self._node_mask) << 3)
        return False

    def _address_of_pipe(self, node_address, pipe_number):
        """return the node_address on a specified pipe"""
        temp_mask = self._node_mask >> 3
        count_bits = 0
        while temp_mask:
            temp_mask >>= 1
            count_bits += 1
        return node_address | (pipe_number << count_bits)

    def _direct_child_route_to(self, node_address):
        """return address for a direct child"""
        # this pressumes that node_address is a direct child
        return node_address & ((self._node_mask << 3) | 0x07)

    def _set_multicast_level(self, level):
        """Set the pipe 0 address to according to octal tree level"""
        self._multicast_level = level
        self._radio.listen = False
        self._radio.open_rx_pipe(0, _pipe_address(_level_to_address(level), 0))
