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
from .network.mixins import NetworkMixin
from .network.structs import (
    RF24NetworkFrame,
    RF24NetworkHeader,
    FrameQueue,
    FrameQueueFrag,
    is_address_valid
)
from .network.constants import (
    NETWORK_FRAG_FIRST,
    NETWORK_FRAG_MORE,
    NETWORK_FRAG_LAST,
    NETWORK_DEFAULT_ADDR,
    NETWORK_MULTICAST_ADDR,
    NETWORK_ADDR_RESPONSE,
    NETWORK_ADDR_REQUEST,
    NETWORK_ACK,
    NETWORK_EXTERNAL_DATA,
    NETWORK_PING,
    NETWORK_POLL,
    AUTO_ROUTING,
    TX_NORMAL,
    TX_ROUTED,
    USER_TX_TO_PHYSICAL_ADDRESS,
    USER_TX_TO_LOGICAL_ADDRESS,
    USER_TX_MULTICAST,
    SYS_MSG_TYPES,
    FLAG_NO_POLL,
    MAX_FRAG_SIZE,
)

# pylint: disable=unused-import
# from .rf24 import address_repr
from .network.constants import (
    NETWORK_DEBUG_MINIMAL,
    NETWORK_DEBUG,
    NETWORK_DEBUG_ROUTING,
)
# pylint: enable=unused-import

def _level_to_address(level):
    """translate decimal tree ``level`` into an octal node address"""
    level_addr = 0
    if level:
        level_addr = 1 << ((level - 1) * 3)
    return level_addr


class RF24Network(NetworkMixin):
    """The object used to instantiate the nRF24L01 as a network node."""

    def __init__(self, spi, csn_pin, ce_pin, node_address, spi_frequency=10000000):
        if not is_address_valid(node_address):
            raise ValueError("node_address argument is invalid or malformed")
        super().__init__(spi, csn_pin, ce_pin, spi_frequency)

        # setup radio
        self._begin(node_address)


    def _begin(self, node_addr: int):
        self._rf24.listen = False
        self._rf24.auto_ack = 0x3E
        self._rf24.set_auto_retries(250 * (((node_addr % 6) + 1) * 2 + 3) + 250, 5)
        self.node_address = node_addr
        self._rf24.listen = True

    @property
    def node_address(self):
        """get/set the node's :ref:`Logical Address <Logical Address>` for the
        `RF24Network` object."""
        return self._addr

    @node_address.setter
    def node_address(self, val):
        if not is_address_valid(val):
            return
        self._addr = val
        self._addr_mask = 0
        self._multicast_level = 0
        for i in range(6):
            self._rf24.open_rx_pipe(i, self._pipe_address(val, i))

        # calc inverted address mask
        mask = 0xFFFF
        while self._addr & mask:
            mask = (mask << 3) & 0xFFFF
            self._multicast_level += 1
        self._addr_mask_inverted = mask

        # calc address mask
        while not mask & 7:
            self._addr_mask = (self._addr_mask << 3) | 7
            mask >>= 3

        # calc parent's address & pipe number
        self._parent = self._addr & (self._addr_mask >> 3)
        self._parent_pipe = self._addr
        mask = self._addr_mask >> 3
        while mask:
            mask >>= 3
            self._parent_pipe >>= 3

    @property
    def fragmentation(self):
        """Enable/disable (`True`/`False`) the message fragmentation feature."""
        return self._frag_enabled

    @fragmentation.setter
    def fragmentation(self, enabled):
        enabled = bool(enabled)
        if enabled != self._frag_enabled:
            if enabled:
                self.queue = FrameQueueFrag(self.queue)
            else:
                self.queue = FrameQueue(self.queue)
            self.max_message_length = 144 if enabled else MAX_FRAG_SIZE
            self.queue.max_message_length = self.max_message_length
            self._frag_enabled = enabled

    @property
    def multicast_relay(self):
        """Enabling this attribute will allow this node to automatically forward
        received multicasted frames to the next highest multicast level."""
        return self.allow_multicast and self._multicast_relay

    @multicast_relay.setter
    def multicast_relay(self, enable):
        self._multicast_relay = enable and self.allow_multicast

    @property
    def multicast_level(self):
        """Override the default multicasting network level which is set by the
        `node_address` attribute."""
        return self._multicast_level

    @multicast_level.setter
    def multicast_level(self, level):
        level = min(3, max(level, 0))
        self._multicast_level = level
        self._rf24.listen = False
        self._rf24.open_rx_pipe(0, self._pipe_address(_level_to_address(level), 0))
        self._rf24.listen = True

    @property
    def parent(self):
        """Get address for the parent node"""
        return self._parent

    def _pipe_address(self, node_addr, pipe_number):
        """translate node address for use on any pipe number"""
        result, count, dec = ([self.address_prefix] * 5, 1, node_addr)
        while dec:
            if not self.allow_multicast or (
                self.allow_multicast and (pipe_number or not node_addr)
            ):
                result[count] = self.address_suffix[dec % 8]
            dec = int(dec / 8)
            count += 1

        if not self.allow_multicast or (
            self.allow_multicast and (pipe_number or not node_addr)
        ):
            result[0] = self.address_suffix[pipe_number]
        elif self.allow_multicast and (not pipe_number or node_addr):
            result[1] = self.address_suffix[count - 1]
        # self._log(
        #     NETWORK_DEBUG,
        #     "address for pipe {} using address {} is {}".format(
        #         pipe_number, oct(node_addr), address_repr(bytearray(result))
        #     ),
        # )
        return bytearray(result)

    def update(self):
        """This function is used to keep the network layer current."""
        return self._net_update()

    def _net_update(self):
        """keep the network layer current; returns the received message type"""
        ret_val = 0  # sentinal indicating there is nothing to report
        while True:
            temp_buf = self._rf24.read()
            if temp_buf is None:
                return ret_val
            if (
                not self.frame_cache.from_bytes(temp_buf)
                or not self.frame_cache.header.is_valid
            ):
                self.logger.log(
                    NETWORK_DEBUG,
                    "discarding packet due to inadequate length"
                    " or invalid network addresses.",
                )
                continue

            # self._log(
            #     NETWORK_DEBUG,
            #     "Received packet: {}\n\t{}".format(
            #         self.frame_cache.header.to_string(),
            #         address_repr(
            #             self.frame_cache.to_bytes(), reverse=False, delimit=" "
            #         )
            #     )
            # )
            ret_val = self.frame_cache.header.message_type
            keep_updating = False
            if self.frame_cache.header.to_node == self._addr:
                # frame was directed to this node
                keep_updating, ret_val = self._handle_frame_for_this_node(ret_val)
            else:  # frame was not directed to this node
                keep_updating, ret_val = self._handle_frame_for_other_node(ret_val)

            if not keep_updating:
                return ret_val

    def _handle_frame_for_this_node(self, msg_t):
        """Returns False if the frame is not consumed or True if consumed"""
        if msg_t == NETWORK_PING:
            return (True, msg_t)

        if msg_t == NETWORK_ADDR_RESPONSE and NETWORK_DEFAULT_ADDR != self._addr:
            self.frame_cache.header.to_node = NETWORK_DEFAULT_ADDR
            self._write(NETWORK_DEFAULT_ADDR, USER_TX_TO_PHYSICAL_ADDRESS)
            return (True, msg_t)
        if msg_t == NETWORK_ADDR_REQUEST and self._addr:
            self.frame_cache.header.from_node = self._addr
            self.frame_cache.header.to_node = 0
            self._write(0, TX_NORMAL)
            return (True, msg_t)
        if self.ret_sys_msg and msg_t > SYS_MSG_TYPES or msg_t == NETWORK_ACK:
            self._log(
                NETWORK_DEBUG_ROUTING, "Received system payload type " + str(msg_t)
            )
            if msg_t not in (
                NETWORK_FRAG_FIRST,
                NETWORK_FRAG_MORE,
                NETWORK_FRAG_LAST,
                NETWORK_EXTERNAL_DATA
            ):
                return (False, msg_t)

        self.queue.enqueue(self.frame_cache)
        if (
            msg_t == NETWORK_EXTERNAL_DATA
            or msg_t == NETWORK_FRAG_LAST
            and self.frame_cache.header.reserved == NETWORK_EXTERNAL_DATA
        ):
            self._log(NETWORK_DEBUG_MINIMAL, "Received external data type")
            return (False, NETWORK_EXTERNAL_DATA)
        return (True, msg_t)

    def _handle_frame_for_other_node(self, msg_t):
        """Returns False if the frame is not consumed or True if consumed"""
        if self.allow_multicast:
            if self.frame_cache.header.to_node == NETWORK_MULTICAST_ADDR:
                if msg_t == NETWORK_POLL:
                    if self._addr != NETWORK_DEFAULT_ADDR:
                        if not self.network_flags & FLAG_NO_POLL:
                            self.frame_cache.header.to_node = (
                                self.frame_cache.header.from_node
                            )
                            self.frame_cache.header.from_node = self._addr
                            time.sleep(self._parent_pipe / 1000)
                            self._write(
                                self.frame_cache.header.to_node,
                                USER_TX_TO_PHYSICAL_ADDRESS
                            )
                        return (True, 0)
                self.queue.enqueue(self.frame_cache)
                if self.multicast_relay:
                    self._log(
                        NETWORK_DEBUG_ROUTING,
                        "Forwarding multicast frame from {} to {}".format(
                            oct(self.frame_cache.header.from_node),
                            oct(self.frame_cache.header.to_node)
                        ),
                    )
                    if not self._addr >> 3:
                        time.sleep(0.0024)
                    time.sleep((self._addr % 4) * 0.0006)
                    self._write(
                        (_level_to_address(self._multicast_level) << 3) & 0xffff,
                        USER_TX_MULTICAST
                    )
                if (
                    msg_t == NETWORK_EXTERNAL_DATA
                    or msg_t == NETWORK_FRAG_LAST
                    and self.frame_cache.header.reserved == NETWORK_EXTERNAL_DATA
                ):
                    return (False, NETWORK_EXTERNAL_DATA)
            elif self._addr != NETWORK_DEFAULT_ADDR:
                # pass it along
                self._write(self.frame_cache.header.to_node, TX_ROUTED)
                return (True, 0)
        elif self._addr != NETWORK_DEFAULT_ADDR:  # multicast not enabled
            # pass it along
            self._write(self.frame_cache.header.to_node, TX_ROUTED)
            msg_t = 0
        return (True, msg_t)

    def available(self):
        """:Returns: A `bool` describing if there is a frame waiting in the `queue`."""
        return bool(len(self.queue))

    def peek_header(self):
        """Get (from `queue`) the next available header."""
        if len(self.queue):
            return self.queue.peek().header
        return None

    def peek_message_length(self):
        """Get (from `queue`) the next available message's length."""
        if len(self.queue):
            return len(self.queue.peek().message)
        return 0

    def peek(self):
        """Get (from `queue`) the next available frame."""
        return self.queue.peek()

    def read(self):
        """Get (from `queue`) the next available frame."""
        return self.queue.dequeue()

    def multicast(self, header: RF24NetworkHeader, message, level=None):
        """Broadcast a message to all nodes on a certain
        `network level <topology.html#network-levels>`_."""
        if len(message) > self.max_message_length:
            raise ValueError("message's length is too large!")
        level = self._multicast_level if level is None else min(3, max(level, 0))
        header.to_node = NETWORK_MULTICAST_ADDR
        if header.from_node is None:
            header.from_node = self._addr
        return self._pre_write(
            RF24NetworkFrame(header, message), _level_to_address(level)
        )

    def send(self, header: RF24NetworkHeader, message):
        """Deliver a message according to the header information."""
        if len(message) > self.max_message_length:
            raise ValueError("message's length is too large!")
        header.from_node = self._addr
        if not header.is_valid():
            return False
        return self._pre_write(RF24NetworkFrame(header, message))

    def write(self, frame: RF24NetworkFrame, traffic_direct=AUTO_ROUTING):
        """Deliver a network frame."""
        if not isinstance(frame, RF24NetworkFrame):
            raise TypeError("frame expected object of type RF24NetworkFrame.")
        if len(frame.message) > self.max_message_length:
            raise ValueError("message's length is too large!")
        frame.header.from_node = self._addr
        if not frame.header.is_valid():
            return False
        return self._pre_write(frame, traffic_direct)

    def _pre_write(self, frame: RF24NetworkFrame, traffic_direct=AUTO_ROUTING):
        """Helper to do prep work for _write_to_pipe(); like to TMRh20's _write()"""
        if len(frame.message) > MAX_FRAG_SIZE and not self._frag_enabled:
            frame.message = frame.message[:MAX_FRAG_SIZE]
        self.frame_cache = frame
        if traffic_direct != AUTO_ROUTING:
            # Payload is multicast to the first node, and routed normally to the next
            send_type = USER_TX_TO_LOGICAL_ADDRESS
            if frame.header.to_node == NETWORK_MULTICAST_ADDR:
                send_type = USER_TX_MULTICAST
            if frame.header.to_node == traffic_direct:
                # Payload is multicast to the first node, which is the recipient
                send_type = USER_TX_TO_PHYSICAL_ADDRESS
            return self._write(traffic_direct, send_type)
        return self._write(frame.header.to_node, TX_NORMAL)

    def _write(self, traffic_direct, send_type):
        """Helper that transmits current frame_cache"""
        is_ack_type = self.frame_cache.is_ack_type()

        to_node, to_pipe, use_multicast = self._logical_to_physical(
            traffic_direct, send_type
        )

        if send_type == TX_ROUTED and traffic_direct == to_node and is_ack_type:
            time.sleep(0.002)

        # send the frame
        result = self._write_to_pipe(to_node, to_pipe, use_multicast)
        # self._log(
        #     NETWORK_DEBUG_ROUTING,
        #     "{} to {} via {} at pipe {}".format(
        #         "Failed sending" if not result else "Successfully sent",
        #         oct(self.frame_cache.header.to_node),
        #         oct(to_node),
        #         to_pipe
        #     ),
        # )

        # conditionally send the NETWORK_ACK message
        if (
            send_type == TX_ROUTED
            and result
            and to_node == traffic_direct
            and is_ack_type
        ):
            # respond with a network ACK
            self.frame_cache.header.message_type = NETWORK_ACK
            self.frame_cache.header.to_node = self.frame_cache.header.from_node
            ack_to_node, ack_to_pipe, use_multicast = self._logical_to_physical(
                self.frame_cache.header.from_node, TX_ROUTED
            )
            ack_ok = self._write_to_pipe(ack_to_node, ack_to_pipe, use_multicast)
            self._log(
                NETWORK_DEBUG_ROUTING,
                "Network ACK {} origin {} (pipe {})".format(
                    "reached" if ack_ok else "failed to reach",
                    oct(self.frame_cache.header.from_node),
                    ack_to_pipe,
                ),
            )

        # conditionally wait for NETWORK_ACK message
        elif (
            result
            and to_node != traffic_direct
            and is_ack_type
            and send_type in (TX_NORMAL, USER_TX_TO_LOGICAL_ADDRESS)
        ):
            result = self._wait_for_network_ack()
            self._log(
                NETWORK_DEBUG_ROUTING,
                "Network ACK {}received from {} (pipe{})".format(
                    "" if result else "not ", oct(to_node), to_pipe
                ),
            )
            return result

        # ready radio to continue listening
        self._rf24.listen = True
        if not use_multicast:
            self._rf24.auto_ack = 0x3E
        return result

    def _wait_for_network_ack(self):
        """wait for network ack from target node"""
        result = True
        self._rf24.listen = True
        self._rf24.auto_ack = 0x3E
        rx_timeout = self.route_timeout * 1000000 + time.monotonic_ns()
        while self._net_update() != NETWORK_ACK:
            if time.monotonic_ns() > rx_timeout:
                result = False
                break
        return result

    def _write_to_pipe(self, to_node, to_pipe, use_multicast):
        """send prepared frame to a particular network node pipe's RX address."""
        result = False
        self._rf24.auto_ack = 0x3E + (not use_multicast)
        self.listen = False
        # self._log(
        #     NETWORK_DEBUG,
        #     "Sending {} on pipe {}".format(
        #         self.frame_cache.header.to_string(),
        #         to_pipe,
        #     )
        # )
        self._rf24.open_tx_pipe(self._pipe_address(to_node, to_pipe))
        if len(self.frame_cache.message) <= MAX_FRAG_SIZE:
            result = self._rf24.send(self.frame_cache.to_bytes(), send_only=True)
            if not result:
                result = self._tx_standby(self.tx_timeout)
        else:
            # break message into fragments and send the multiple resulting frames
            total = bool(len(self.frame_cache.message) % MAX_FRAG_SIZE) + int(
                len(self.frame_cache.message) / MAX_FRAG_SIZE
            )
            msg_t = self.frame_cache.header.message_type
            for count in range(total):
                buf_start = count * MAX_FRAG_SIZE
                buf_end = count * MAX_FRAG_SIZE + MAX_FRAG_SIZE
                self.frame_cache.header.reserved = total - count
                if count == total - 1:
                    self.frame_cache.header.message_type = NETWORK_FRAG_LAST
                    self.frame_cache.header.reserved = msg_t
                    buf_end = len(self.frame_cache.message)
                elif not count:
                    self.frame_cache.header.message_type = NETWORK_FRAG_FIRST
                else:
                    self.frame_cache.header.message_type = NETWORK_FRAG_MORE

                result = self._rf24.send(
                    self.frame_cache.header.to_bytes()
                    + self.frame_cache.message[buf_start : buf_end],
                    send_only=True
                )
                retries = 3
                while not result and retries:
                    time.sleep(0.002)
                    result = self._tx_standby(self.tx_timeout)
                    retries -= 1
                # print(
                #     "Frag {} of {} {}".format(
                #         count + 1,
                #         total,
                #         "sent successfully" if result else "failed to send. Aborting"
                #     )
                # )
                if not result:
                    break
            self.frame_cache.header.message_type = msg_t
        return result

    def _logical_to_physical(self, to_node, send_type, use_multicast=False):
        """translates logical address routing to physical address and data pipe number
        with a conditional use_multicast flag"""
        converted_to_node = self._parent
        converted_to_pipe = self._parent_pipe
        if send_type > TX_ROUTED:
            use_multicast = True
            converted_to_pipe = 0
            converted_to_node = to_node
        elif to_node & self._addr_mask == self._addr:
            # to_node is a descendant
            converted_to_pipe = 5
            if not to_node & (self._addr_mask_inverted << 3):
                # to_node is a direct child
                converted_to_node = to_node
            else:
                # to_node is a descendant of a descendant
                converted_to_node = to_node & ((self._addr_mask << 3) | 7)
        return (converted_to_node, converted_to_pipe, use_multicast)
