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
import time
import math
from .network_mixin import RadioMixin
from ..rf24 import address_repr
from .packet_structs import RF24NetworkFrame, RF24NetworkHeader, _is_addr_valid
from .queue import QueueFrag, _frag_types
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
    USER_TX_TO_LOGICAL_ADDRESS,
    USER_TX_MULTICAST,
    MAX_USER_DEFINED_HEADER_TYPE,
    FLAG_FAST_FRAG,
    FLAG_NO_POLL,
    MAX_MESSAGE_SIZE,
)



def _level_to_address(level):
    """translate octal tree ``level`` into a node_address"""
    level_addr = 0
    if level:
        level_addr = 1 << ((level - 1) * 3)
    return level_addr


def _frame_frags(messages, header):
    """Add correct frame headers to a fragmented list of messages"""
    frames = []
    last_frame = len(messages) - 1
    for i, msg in enumerate(messages):
        # copy header
        head = RF24NetworkHeader()
        head.decode(header.buffer)

        # make header unique to frag pos & id
        head.reserved = last_frame - i
        if i == last_frame:
            head.message_type = NETWORK_FRAG_LAST
            head.reserved = header.message_type
        elif not i:
            head.message_type = NETWORK_FRAG_FIRST
        else:
            head.message_type = NETWORK_FRAG_MORE

        frames.append(RF24NetworkFrame(header=head, message=msg))
    return frames


def _frag_msg(msg):
    """Fragment a single message into a list of messages"""
    messages = []
    max_i = math.ceil(len(msg) / MAX_MESSAGE_SIZE)
    i = 0
    while i < max_i:
        start = i * MAX_MESSAGE_SIZE
        end = start + MAX_MESSAGE_SIZE
        if len(msg) < end:
            end = len(msg)
        messages.append(msg[start:end])
        i += 1
    return messages


class RF24Network(RadioMixin):
    """The object used to instantiate the nRF24L01 as a network node.

    :param int node_address: The octal `int` for this node's address
    """

    def __init__(self, spi, csn_pin, ce_pin, node_address, spi_frequency=10000000):
        if not _is_addr_valid(node_address):
            raise ValueError("node_address argument is invalid or malformed")
        super().__init__(spi, csn_pin, ce_pin, spi_frequency)
        # setup private members
        self._multicast_level = 0
        self._network_flags = 0
        self._addr = 0
        self._addr_mask = 0

        # setup members specific to network node
        #: enable (`True`) or disable (`False`) multicasting
        self.allow_multicast = True
        self._tx_timeout = 25000
        self._rx_timeout = 3 * self._tx_timeout
        self._multicast_relay = True
        self.ret_sys_msg = False  #: for use with RF24Mesh
        self.max_message_length = 144
        """If a network node is driven by the TMRh20 RF24Network library on a
        ATTiny-based board, set this to ``72``."""

        # init internal frame buffer
        self._frame_buf = bytearray(self.max_message_length + len(RF24NetworkHeader()))
        self.address_suffix = [0xC3, 0x3C, 0x33, 0xCE, 0x3E, 0xE3]
        self.address_prefix = [0xCC] * 5
        self.fragmentation = True
        #: enable/disable (`True`/`False`) message fragmentation
        self._queue = QueueFrag()
        self.force_retry = 6
        """Instead of a ``RF24Network::txTimeout``, we use the minimum amount
        of forced retries during transmission failure (with auto-retries
        observed for every forced retry)."""

        # setup radio
        self._rf24.auto_ack = 0x3E
        self._rf24.set_auto_retries(250 * (((node_address % 6) + 1) * 2 + 3) + 250, 5)
        self.node_address = node_address
        self._rf24.listen = True

    def __enter__(self):
        self.node_address = self._addr
        self._rf24.__enter__()
        self._rf24.listen = True
        return self

    def __exit__(self, *exc):
        return self._rf24.__exit__()

    def print_details(self, dump_pipes: bool=True) -> None:
        """.. seealso:: :py:meth:`~circuitpython_nrf24l01.rf24.RF24.print_details()`"""
        self._rf24.print_details(dump_pipes)
        print("Network node address__", oct(self.node_address))

    @property
    def node_address(self):
        """get/set the node_address for the RF24Network object."""
        return self._addr

    @node_address.setter
    def node_address(self, val):
        if _is_addr_valid(val):
            self._addr = val
            mask = 0xFFFF
            while self._addr & mask:
                mask = (mask << 3) & 0xFFFF
                self._multicast_level += 1
            while not mask & 7:
                self._addr_mask = (self._addr_mask << 3) | 7
                mask >>= 3
            for i in range(6):
                self._rf24.open_rx_pipe(i, self._pipe_address(val, i))

    @property
    def tx_timeout(self):
        """The timeout (in milliseconds) to wait for successful transmission.
        Defaults to 25. The rx_timeout will be three times this value."""
        return self._tx_timeout / 1000

    @tx_timeout.setter
    def tx_timeout(self, val):
        self._tx_timeout = min(val, 1000)
        self._rx_timeout = 3 * self._tx_timeout

    @property
    def multicast_relay(self):
        """Enabling this will allow this node to automatically forward
        received multicast frames to the next highest multicast level.
        Duplicate frames are filtered out, so multiple forwarding nodes at the
        same level should not interfere. Forwarded payloads will also be
        received."""
        return self.allow_multicast and self._multicast_relay

    @multicast_relay.setter
    def multicast_relay(self, enable):
        self._multicast_relay = enable and self.allow_multicast

    @property
    def parent_pipe(self):
        """The pipe that the parent node uses to listen to child nodes."""
        result = self._addr
        mask = self._addr_mask >> 3
        while mask:
            result >>= 3
            mask >>= 3
        return result

    @property
    def parent(self):
        """get address for parent node"""
        if not self._addr:
            return None
        return self._addr & (self._addr_mask >> 3)

    def _pipe_address(self, node_address, pipe_number):
        """translate node address for use on all pipes"""
        result, count, dec = (self.address_prefix[:6], 1, node_address)
        while dec:
            if not self.allow_multicast or (
                self.allow_multicast and (pipe_number or not node_address)
            ):
                result[count] = self.address_suffix[dec % 8]
            dec = int(dec / 8)
            count += 1

        if not self.allow_multicast or (
            self.allow_multicast and (pipe_number or not node_address)
        ):
            result[0] = self.address_suffix[pipe_number]
        elif self.allow_multicast and (not pipe_number or node_address):
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
            self._log(NETWORK_DEBUG, "Received packet:" + address_repr(frame))
            if not frame_buf.decode(frame) or not frame_buf.header.is_valid:
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
                    self._log(
                        NETWORK_DEBUG_ROUTING, "Received system payload type " + ret_val
                    )
                    return ret_val

                self._queue.enqueue(frame_buf)
                if ret_val == NETWORK_EXTERNAL_DATA:
                    self._log(NETWORK_DEBUG_MINIMAL, "return external data type")
                    return ret_val

            else:  # frame was not directed to this node
                if self.multicast_relay:
                    if frame.header.to_node == 0o100:
                        if (
                            ret_val == NETWORK_POLL
                            and self._addr != NETWORK_DEFAULT_ADDR
                        ):
                            ret_val = 0
                            if (
                                not self._network_flags & FLAG_NO_POLL
                                and self._addr != NETWORK_DEFAULT_ADDR
                            ):
                                frame.header.to_node = frame.header.from_node
                                frame.header.from_node = self._addr
                                self.write(frame, USER_TX_TO_PHYSICAL_ADDRESS)
                                continue
                        self._queue.enqueue(frame_buf)
                        if self.multicast_relay:
                            self._log(
                                NETWORK_DEBUG_ROUTING,
                                "Forwarding multicast frame from {} to {}".format(
                                    frame.header.from_node, frame.header.to_node
                                )
                            )
                            if not self._addr >> 3:
                                time.sleep(0.0024)
                            time.sleep((self._addr % 4) * 0.0006)
                        if ret_val == NETWORK_EXTERNAL_DATA:
                            return ret_val
                    elif self._addr != NETWORK_DEFAULT_ADDR:
                        self.write(frame, 1)  # pass it along
                        ret_val = 0  # indicate its a routed payload
                elif self._addr != NETWORK_DEFAULT_ADDR:  # multicast not enabled
                    self.write(frame, 1)
                    ret_val = 0
        # end while _rf24.available()
        return ret_val

    def available(self):
        """Is there a message for this node?"""
        return bool(len(self._queue))

    @property
    def peek_header(self):
        """:Return: the next available message's header from the internal queue
        without removing it from the queue"""
        return self._queue.peek.header

    @property
    def peek(self):
        """:Return: the next available header & message from the internal queue
        without removing it from the queue"""
        return self._queue.peek

    def read(self):
        """Get the next available header & message from internal queue. This
        differs from `peek` because this function also removes the header &
        message from the internal queue.

        :returns: A 2-item tuple containing the next available

            1. `RF24NetworkHeader`
            2. a `bytearray` message
        """
        return self._queue.pop

    def set_multicast_level(self, level):
        """Set the pipe 0 address according to octal tree ``level``"""
        self._multicast_level = level
        self._rf24.listen = False
        self._rf24.open_rx_pipe(0, self._pipe_address(_level_to_address(level), 0))

    def multicast(self, header, message, level):
        """Broadcast a message to all nodes on a certain address level"""
        header.to_node = 0o100
        header.from_node = self.node_address
        return self.send(header, message, _level_to_address(level))

    def send(self, header, message, traffic_direct=0):
        """Deliver a ``message`` according to the ``header`` information."""
        if not isinstance(header, RF24NetworkHeader):
            raise TypeError("header is not a RF24NetworkHeader object")
        if not isinstance(message, (bytes, bytearray)):
            raise TypeError("message is not a byteaarray or bytes object")
        frame = RF24NetworkFrame(header=header, message=message)
        return self.write(frame, traffic_direct)

    def _write_frag(self, frame, traffic_direct):
        """write a message fragmented into multiple payloads"""
        if len(frame.message) > self.max_message_length and self.fragmentation:
            raise ValueError("message is too large to fragment")
        frames = _frame_frags(_frag_msg(frame.message), frame.header)
        for i, frm in enumerate(frames):
            result = self.write(frm, traffic_direct)
            retries = 0
            while not result and retries < 3:
                result = self.write(frm, traffic_direct)
                retries += 1
            prompt = "Frag {} of {} ".format(i, len(frames))
            if not result:
                self._log(NETWORK_DEBUG_FRAG, prompt + "failed to send. Aborting")
                return False
            self._log(NETWORK_DEBUG_FRAG_L2, prompt + "sent successfully")
        return True

    def write(self, frame, traffic_direct=0o70):
        """Deliver a constructed ``frame`` routed as ``traffic_direct``"""
        if not isinstance(frame, RF24NetworkFrame):
            raise TypeError("expected object of type RF24NetworkFrame.")
        frame.header.from_node = self._addr
        frame.header.to_node = int(traffic_direct)
        if traffic_direct != 0o70:
            send_type = USER_TX_TO_LOGICAL_ADDRESS
            if frame.header.to_node == 0o100:
                send_type = USER_TX_MULTICAST
            if frame.header.to_node == traffic_direct:
                send_type = USER_TX_TO_PHYSICAL_ADDRESS

            # write(traffic_direct, send_type)
            traffic_direct = send_type
        else:
            traffic_direct = TX_NORMAL

        result = False
        if len(frame.message) > MAX_MESSAGE_SIZE and self.fragmentation:
            self._write_frag(frame, traffic_direct)

        # send the frame
        to_node, to_pipe, use_multicast = self._logical_to_physical(
            frame.header.to_node, traffic_direct
        )
        result = self._write_to_pipe(frame, to_node, to_pipe, use_multicast)
        if not result:
            self._log(
                NETWORK_DEBUG_ROUTING,
                "Failed to send to {} via {} on pipe {}".format(
                    oct(frame.header.to_node), oct(to_node), to_pipe
                ),
            )
        if (
            traffic_direct == TX_ROUTED
            and result
            and to_node == frame.header.to_node
            and frame.is_ack_type
        ):
            # respond with a network ACK
            ack_to_node, ack_to_pipe, use_multicast = self._logical_to_physical(
                frame.header.from_node, TX_ROUTED
            )
            ack_ok = self._write_to_pipe(frame, ack_to_node, ack_to_pipe, use_multicast)
            self._log(
                NETWORK_DEBUG_ROUTING,
                "Network ACK {} origin {} (pipe {})".format(
                    "reached" if ack_ok else "failed to reach",
                    oct(frame.header.from_node),
                    ack_to_pipe,
                ),
            )

        # ready radio to continue listening
        if (
            result
            and to_node != frame.header.to_node
            and frame.is_ack_type
            and traffic_direct in (0, 3)
        ):
            # wait for Network ACK
            if self._network_flags & FLAG_FAST_FRAG:
                self._network_flags &= ~FLAG_FAST_FRAG
                self._rf24.set_auto_ack(0, 0)
            self._rf24.listen = True
            rx_timeout = time.monotonic_ns() / 1000 + self._rx_timeout
            while self.update() != NETWORK_ACK:
                if time.monotonic_ns() / 1000 > rx_timeout:
                    result = False
                    self._log(
                        NETWORK_DEBUG_ROUTING,
                        "No Network ACK received from {} (pipe{})".format(
                            oct(to_node), to_pipe
                        ),
                    )
                    break
        if not self._network_flags & FLAG_FAST_FRAG:
            self._rf24.listen = True
        return result

    def _write_to_pipe(self, frame, to_node, to_pipe, use_multicast):
        """send prepared frame to a particular network node pipe's RX address."""
        result = False
        if not frame.header.is_valid:
            return result
        if not self._network_flags & FLAG_FAST_FRAG:
            self.listen = True
        if use_multicast:
            self._rf24.set_auto_ack(0, 0)
        else:
            self._rf24.set_auto_ack(1, 0)
        self._log(
            NETWORK_DEBUG,
            "Sending type {} with ID {} from {} to {} on pipe {}".format(
                frame.header.message_type,
                frame.header.frame_id,
                oct(frame.header.from_node),
                oct(frame.header.to_node),
                to_pipe
            )
        )
        self._rf24.open_tx_pipe(self._pipe_address(to_node, to_pipe))

        result = self._rf24.send(frame.buffer)
        timeout = time.monotonic_ns() / 1000 + self._tx_timeout
        if not self._network_flags & FLAG_FAST_FRAG:
            while not result and time.monotonic_ns() / 1000 < timeout:
                result = self._rf24.resend()
        self._rf24.set_auto_ack(0, 0)
        return result

    def _address_of_pipe(self, _address, _pipe):
        """return the node_address on a specified pipe"""
        temp_mask = self._addr_mask >> 3
        count_bits = 0
        while temp_mask:
            temp_mask >>= 1
            count_bits += 1
        return _address | (_pipe << count_bits)

    def _logical_to_physical(self, to_node, to_pipe, use_multicast=False):
        """translates logical routing to physical address and data pipe number with
        a use_multicast flag"""
        if to_pipe > TX_ROUTED:
            use_multicast = True
            to_pipe = 0
        elif self._is_direct_child(to_node):
            to_pipe = 5
        elif self._is_descendant(to_node):
            to_node = self._direct_child_route_to(to_node)
            to_pipe = 5
        else:
            to_node = self.parent
            to_pipe = self.parent_pipe
        return (to_node, to_pipe, use_multicast)

    def _is_descendant(self, address):
        """Is the given ``node_address`` a descendant of `node_address`"""
        return address & self._addr_mask == self._addr

    def _is_direct_child(self, address):
        """Is the given ``address`` a direct child of `node_address`"""
        if self._is_descendant(address):
            return not address & ((~self._addr_mask) << 3)
        return False

    def _direct_child_route_to(self, address):
        """return address for a direct child"""
        # this pressumes that address is a direct child
        return address & ((self._addr_mask << 3) | 0o7)
