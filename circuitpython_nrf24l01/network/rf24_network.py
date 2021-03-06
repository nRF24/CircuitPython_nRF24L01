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

# pylint: disable=unused-import
from .constants import (
    NETWORK_DEBUG_MINIMAL,
    NETWORK_DEBUG,
    NETWORK_DEBUG_FRAG,
    NETWORK_DEBUG_FRAG_L2,
    NETWORK_DEBUG_ROUTING,
    NETWORK_FRAG_FIRST,
    NETWORK_FRAG_MORE,
    NETWORK_FRAG_LAST,
    NETWORK_DEFAULT_ADDR,
    NETWORK_ADDR_RESPONSE,
    NETWORK_ADDR_REQUEST,
    NETWORK_ACK,
    NETWORK_EXTERNAL_DATA,
    NETWORK_PING,
    NETWORK_POLL,
    TX_NORMAL,
    TX_ROUTED,
    USER_TX_TO_PHYSICAL_ADDRESS,
    MAX_USER_DEFINED_HEADER_TYPE,
)

# pylint: enable=unused-import
from .network_mixin import RadioMixin
from ..rf24 import address_repr

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


class RF24Network(RadioMixin):
    """The object used to instantiate the nRF24L01 as a network node.

    :param int node_address: The octal `int` for this node's address
    """

    def __init__(self, spi, csn_pin, ce_pin, node_address, spi_frequency=10000000):
        if not _is_addr_valid(node_address):
            raise ValueError("node_address argument is invalid or malformed")
        super().__init__(spi, csn_pin, ce_pin, spi_frequency)
        self.address_suffix = [0xC3, 0x3C, 0x33, 0xCE, 0x3E, 0xE3]
        self.address_prefix = [0xCC] * 5
        self._multicast_level = 0
        self._addr = 0
        self._addr_mask = 0xFFFF

        self.multicast = True  #: enable (`True`) or disable (`False`) multicasting
        self._multicast_relay = True
        self.max_message_length = 144
        """If a network node is driven by the TMRh20 RF24Network library on a
        ATTiny-based board, set this to ``72``."""
        # init internal frame buffer
        self._frame_buf = bytearray(self.max_message_length + len(RF24NetworkHeader()))
        self.fragmentation = True
        #: enable (`True`) or disable (`False`) message fragmentation
        self.ret_sys_msg = False  #: for use with RF24Mesh (unsupported)

        # setup node_address & private properies
        self.node_address = node_address
        self.force_retry = 6
        """Instead of a ``RF24Network::txTimeout``, we use the minimum amount
        of forced retries during transmission failure (with auto-retries
        observed for every forced retry)."""

        self._rf24.ack = True
        self._rf24.set_auto_retries(((node_address % 6) + 1) * 2 + 3, 5)
        self._rf24.listen = True
        self._queue = []  # each item is a 2-tuple containing header & message

    def __enter__(self):
        self.node_address = self._addr
        self._rf24.__enter__()
        self._rf24.listen = True
        return self

    def __exit__(self, *exc):
        return self._rf24.__exit__()

    # pylint: disable=missing-docstring
    def print_details(self, dump_pipes=True):
        self._rf24.print_details(dump_pipes)
        print("Net node address__________{}".format(oct(self.node_address)))

    # pylint: enable=missing-docstring

    @property
    def node_address(self):
        """get/set the node_address for the RF24Network object."""
        return self._addr

    @node_address.setter
    def node_address(self, val):
        if _is_addr_valid(val):
            self._addr = val
            while self._addr & self._addr_mask:
                self._addr_mask <<= 3
                self._multicast_level += 1
            self._addr_mask = ~self._addr_mask
            for i in range(6):
                self._rf24.open_rx_pipe(i, self._pipe_address(val, i))

    @property
    def multicast_relay(self):
        """Enabling this will allow this node to automatically forward
        received multicast frames to the next highest multicast level.
        Duplicate frames are filtered out, so multiple forwarding nodes at the
        same level should not interfere. Forwarded payloads will also be
        received."""
        return self.multicast and self._multicast_relay

    @multicast_relay.setter
    def multicast_relay(self, enable):
        self._multicast_relay = enable and self.multicast

    def _pipe_address(self, node_address, pipe_number):
        """translate node address for use on all pipes"""
        # self.address_suffix = [0xC3, 0x3C, 0x33, 0xCE, 0x3E, 0xE3]
        result, count, dec = (self.address_prefix[:6], 1, node_address)
        while dec:
            if not self.multicast or (
                self.multicast and (pipe_number or not node_address)
            ):
                result[count] = self.address_suffix[dec % 8]
            dec = int(dec / 8)
            count += 1

        if (self.multicast and (pipe_number or not node_address)) or not self.multicast:
            result[0] = self.address_suffix[pipe_number]
        elif self.multicast and (not pipe_number or node_address):
            result[1] = self.address_suffix[count - 1]
        # print(
        #     "address for pipe {} using address {} is {}".format(
        #         pipe_number, oct(node_address), address_repr(bytearray(result))
        #     )
        # )
        return bytearray(result)

    def update(self):
        """keep the network layer current; returns the next header"""
        ret_val = 0  # sentinal indicating there is nothing to report
        while self._rf24.available():
            # grab the frame from RX FIFO
            frame_buf = RF24NetworkFrame()
            frame = self._rf24.read()
            if self.logger is not None:
                prompt = "Received packet:" + address_repr(frame)
                self.logger.log(NETWORK_DEBUG, prompt)
            if not frame_buf.decode(frame) or not frame.header.is_valid:
                if self.logger is not None:
                    self.logger.log(
                        NETWORK_DEBUG,
                        "discarding packet due to inadequate length"
                        " or bad network addresses.",
                    )
                continue

            ret_val = frame_buf.header.message_type
            if frame_buf.header.to_node == self._addr:
                # frame was directed to this node
                if ret_val == NETWORK_PING:
                    continue

                # used for RF24Mesh
                if ret_val == NETWORK_ADDR_RESPONSE:
                    requester = NETWORK_DEFAULT_ADDR
                    if requester != self._addr:
                        frame_buf.header.to_node = requester
                        self.write(frame_buf, USER_TX_TO_PHYSICAL_ADDRESS)
                        continue
                if ret_val == NETWORK_ADDR_REQUEST and self._addr:
                    frame_buf.header.from_node = self._addr
                    frame_buf.header.to_node = 0
                    self.write(frame_buf, TX_NORMAL)
                    continue

                if (
                    self.ret_sys_msg
                    and ret_val > MAX_USER_DEFINED_HEADER_TYPE
                    or ret_val == NETWORK_ACK
                    and ret_val not in _frag_types + (NETWORK_EXTERNAL_DATA,)
                ):
                    return ret_val

                self._queue.append(frame)
            else:  # frame was not directed to this node
                if self.multicast_relay:
                    if frame.header.to_node == 0o100:
                        # used by RF24Mesh
                        if (
                            ret_val == NETWORK_POLL
                            and self._addr != NETWORK_DEFAULT_ADDR
                        ):
                            pass

                elif self._addr != NETWORK_DEFAULT_ADDR:
                    self.write(frame, 1)  # pass it along
                    ret_val = 0  # indicate its a routed payload
        # end while _rf24.available()
        return ret_val

    def available(self):
        """Is there a message for this node?"""
        return bool(len(self._queue))

    @property
    def peek_header(self):
        """:Return: the next available message's header from the internal queue
        without removing it from the queue"""
        return self._queue[0][0]

    @property
    def peek(self):
        """:Return: the next available header & message from the internal queue
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
        frame = RF24NetworkFrame(header=header, message=message)
        return self.write(frame, 0o70)

    # pylint: disable=unnecessary-pass
    def write(self, frame, to_node=0):
        """deliver a constructed ``frame`` with a header routed to ``to_node`` """
        if not isinstance(frame, RF24NetworkFrame):
            raise TypeError("expected object of type RF24NetworkFrame.")
        frame.header.from_node = self._addr
        frame.header.to_node = int(to_node) & 0xFFFF
        if frame.header.is_valid():
            return self._rf24.send(frame)
        return False

    def _write_to_pipe(self, to_node, to_pipe):
        """extract pipe's RX address for a particular node."""
        result = False
        # if not network_flags & FAST_FRAG:
        self.listen = True
        if self.multicast:
            self._rf24.set_auto_ack(0, 0)
        else:
            self._rf24.set_auto_ack(1, 0)
        self._rf24.open_tx_pipe(self._pipe_address(to_node, to_pipe))
        result = self._rf24.send(self._frame_buf, force_retry=self.force_retry)
        # if not network_flags & FAST_FRAG:
        self._rf24.set_auto_ack(0, 0)
        return result

    def set_multicast_level(self, level):
        """Set the pipe 0 address according to octal tree ``level``"""
        self._multicast_level = level
        self._rf24.listen = False
        self._rf24.open_rx_pipe(0, self._pipe_address(_level_to_address(level), 0))

    def logical_to_physical(self, to_node, to_pipe, frame):
        """translate ``frame`` to node physical address and data pipe number"""
        pass

    # pylint: enable=unnecessary-pass
    def _is_descendant(self, _address):
        """Is the given ``node_address`` a descendant of `node_address`"""
        return _address & self._addr_mask == self._addr

    def _is_direct_child(self, _address):
        """Is the given ``_address`` a direct child of `node_address`"""
        if self._is_descendant(_address):
            return not _address & ((~self._addr_mask) << 3)
        return False

    def _address_of_pipe(self, _address, _pipe):
        """return the node_address on a specified pipe"""
        temp_mask = self._addr_mask >> 3
        count_bits = 0
        while temp_mask:
            temp_mask >>= 1
            count_bits += 1
        return _address | (_pipe << count_bits)

    def _direct_child_route_to(self, node_address):
        """return address for a direct child"""
        # this pressumes that node_address is a direct child
        return node_address & ((self._addr_mask << 3) | 0x07)
