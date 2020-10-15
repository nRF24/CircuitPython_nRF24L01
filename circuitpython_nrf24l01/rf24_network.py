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
"""rf24 module containing the base class RF24"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import struct
from micropython import const
from .rf24 import RF24

# contraints on user-defined header types
MIN_USER_DEFINED_HEADER_TYPE = const(0)
MAX_USER_DEFINED_HEADER_TYPE = const(127)


def _is_address_valid(address):
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


# pylint: disable=too-few-public-methods
class NetworkTypes:
    """ A collection of constants used to define
    `RF24NetworkHeader.message_type` """

    PING = const(130)
    """used for network pings"""

    ADDR_REQUEST = const(195)
    """used for requesting data from network base node"""

    ADDR_RESPONSE = const(128)
    """used for routing messages and their responses throughout the network"""

    FRAG_FIRST = const(148)
    """used to indicate the first frame of fragmented payloads"""

    FRAG_MORE = const(149)
    """used to indicate a frame (not first or last) of fragmented payloads"""

    FRAG_LAST = const(150)
    """used to indicate the last frame of fragmented payloads"""

    ACK = const(193)
    """used internally to forward acknowledgments from payload
    target/recipient to payload origin/sender"""

    EXT_DATA = const(131)
    """used for bridging different network protocols between an RF24Network
    and LAN/WLAN networks (unsupported at this time as this operation requires
    a gateway implementation)"""


# pylint: enable=too-few-public-methods
class RF24NetworkHeader:
    """message header used for routing network messages"""

    def __init__(self, to_node=None, from_node=None, frame_id=0, message_type=None):
        self.from_node = from_node  #: describe the message origin
        self.to_node = to_node  #: describe the message destination
        self.message_type = message_type  #: describe the message type
        self.frame_id = frame_id  #: describes the unique id for the frame
        self.next_id = 0  #: points to the next sequential frame of fragments

    def decode(self, buffer):
        """decode frame header for first 9 bytes of the payload."""
        unpacked = struct.unpack("hhhbbh", buffer[:9])
        self.from_node = unpacked[0]
        self.to_node = unpacked[1]
        self.frame_id = unpacked[2]
        self.message_type = unpacked[3]
        self.next_id = unpacked[5]

    @property
    def buffer(self):
        """Return the entire header as a `bytes` object"""
        return struct.pack(
            "hhhbbh",
            self.from_node,
            self.to_node,
            self.frame_id,
            self.message_type,
            0,  # reserved for sytem uses
            self.next_id,
        )


class RF24NetworkFrame:
    """contructs a single frame from either a fragmented message of payloads
    or a single payload of less than 28 bytes.

    :param RF24NetworkHeader header: The header describing the message's frame
    :param bytes,bytearray message: The actual message containing the payload
        or a fragment of a payload.
    """

    def __init__(self, header, message):
        self._header = header
        self._msg = message

    @property
    def header(self):
        """the RF24NetworkHeader of the message"""
        return self._header

    @property
    def message(self):
        """the entire message or a fragment of the message allocated to this
        frame"""
        return self._msg


class RF24Network:
    """ The object used to instantiate the nRF24L01 as a network node.

    :param int node_address: The octal `int` for this node's address
    :param int channel: The RF channel used by the RF24Network
    """

    def __init__(self, spi, csn_pin, ce_pin, node_address, channel=76):
        self._radio = RF24(spi, csn_pin, ce_pin)
        if not _is_address_valid(node_address):
            raise ValueError("node_address argument is invalid or malformed")
        # setup node_address
        self._node_address = node_address
        self._node_mask = 0xFFFF
        self._multicast_level = 0
        while self._node_address & self._node_mask:
            self._node_mask <<= 3
            self._multicast_level += 1
        self._node_mask = ~self._node_mask
        for i in range(6):
            self._radio.open_rx_pipe(i, _pipe_address(node_address, i))
        self._radio.channel = channel
        self._radio.ack = True
        self._radio.arc = 5
        self._radio.ard = (((int(node_address, 8) % 6) + 1) * 2) + 3
        self._radio.listen = True
        self._queue = []  # each item is a 2-tuple containing header & message

    def update(self):
        """keep the network layer current; returns the next header"""
        while self._radio.pipe:
            self._queue.append(self._radio.recv())
            self._radio.update()

    def available(self):
        """ is there a message for this node """
        pass

    def peek_header(self):
        """ return the next payload's header from internal queue
        without popping it from the queue """
        return self._queue[0][0]

    def peek_payload(self):
        """ return the next payload from internal queue
        without popping it from the queue """
        return self._queue[0][1]

    def read(self):
        """ return the next payload from internal queue; this differs
        from `peek()` as it also pops the payload from the internal
        queue. """
        ret = self._queue[0]
        del self._queue[0]
        return ret

    def write(self, header, message):
        """ deliver a message according to the header's information """
        pass

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
