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
"""A module to hold all usuall accesssible RF24 API via the RF24Network API"""
# pylint: disable=missing-docstring
import time
from ..rf24 import RF24, address_repr
from .structs import RF24NetworkFrame, FrameQueue, FrameQueueFrag
from .constants import (
    MAX_FRAG_SIZE,
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
    TX_ROUTED,
    NETWORK_MULTICAST_ADDR,
    TX_NORMAL,
    USER_TX_TO_PHYSICAL_ADDRESS,
    USER_TX_TO_LOGICAL_ADDRESS,
    USER_TX_MULTICAST,
    MAX_USER_DEFINED_MSG_TYPE,
    FLAG_NO_POLL,
)


class RadoMixin:
    def __init__(self, spi, csn, ce_pin, spi_frequency=10000000):
        self._rf24 = RF24(spi, csn, ce_pin, spi_frequency=spi_frequency)
        super().__init__()

    def __enter__(self):
        self._rf24.__enter__()
        self._rf24.listen = True
        return self

    def __exit__(self, *exc):
        return self._rf24.__exit__()

    @property
    def power(self):
        return self._rf24.power

    @power.setter
    def power(self, val):
        self._rf24.power = val

    @property
    def channel(self):
        return self._rf24.channel

    @channel.setter
    def channel(self, val):
        self._rf24.channel = val

    def set_dynamic_payloads(self, enable, pipe=None):
        self._rf24.set_dynamic_payloads(enable, pipe_number=pipe)

    def get_dynamic_payloads(self, pipe=None):
        return self._rf24.get_dynamic_payloads(pipe)

    @property
    def listen(self):
        return self._rf24.listen

    @listen.setter
    def listen(self, is_rx):
        self._rf24.listen = is_rx

    @property
    def pa_level(self):
        return self._rf24.pa_level

    @pa_level.setter
    def pa_level(self, val):
        self._rf24.pa_level = val

    @property
    def is_lna_enabled(self):
        return self._rf24.is_lna_enabled

    @property
    def data_rate(self):
        return self._rf24.data_rate

    @data_rate.setter
    def data_rate(self, val):
        self._rf24.data_rate = val

    @property
    def crc(self):
        return self._rf24.crc

    @crc.setter
    def crc(self, val):
        self._rf24.crc = val

    def get_auto_retries(self):
        return self._rf24.get_auto_retries()

    def set_auto_retries(self, delay, count):
        self._rf24.set_auto_retries(delay, count)

    @property
    def last_tx_arc(self):
        return self._rf24.last_tx_arc

    def address(self, index=-1):
        return self._rf24.address(index)

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        self._rf24.interrupt_config(data_recv, data_sent, data_fail)

    def print_pipes(self):
        self._rf24.print_pipes()


def _level_to_address(level):
    """translate decimal tree ``level`` into an octal node address"""
    level_addr = 0
    if level:
        level_addr = 1 << ((level - 1) * 3)
    return level_addr


class NetworkMixin(RadoMixin):
    def __init__(self, spi, csn, ce_pin, spi_frequency=10000000):
        super().__init__(spi, csn, ce_pin, spi_frequency=spi_frequency)
        # setup private members
        self._multicast_level = 0
        self._addr = 0
        self._addr_mask = 0
        self._addr_mask_inverted = 0
        self._multicast_relay = False
        self._frag_enabled = True

        #: The timeout (in milliseconds) to wait for successful transmission.
        self.tx_timeout = 25
        #: The timeout (in milliseconds) to wait for transmission's `NETWORK_ACK`.
        self.route_timeout = 3 * self.tx_timeout
        #: enable/disable (`True`/`False`) multicasting
        self.allow_multicast = True
        self.ret_sys_msg = False  #: Force `update()` to return on system message types.
        self.network_flags = 0  #: Flags that affect Network node behavior.
        self.max_message_length = 144  #: The maximum length of a frame's message.
        #: The queue (FIFO) of recieved frames for this node
        self.queue = FrameQueueFrag()
        self.queue.max_message_length = self.max_message_length
        #: A buffer containing the last frame received by the network node
        self.frame_cache = RF24NetworkFrame()
        self.address_suffix = [0xC3, 0x3C, 0x33, 0xCE, 0x3E, 0xE3]
        """Each byte in this list corresponds to the unique byte per pipe and child
        node."""
        self.address_prefix = 0xCC
        """The base case for all pipes' address' bytes before mutating with
        `address_suffix`."""

    def _begin(self, node_addr):
        # prep radio
        self._rf24.listen = False
        self._rf24.auto_ack = 0x3E
        self._rf24.set_auto_retries(250 * (((node_addr % 6) + 1) * 2 + 3) + 250, 5)
        for i in range(6):
            self._rf24.open_rx_pipe(i, self._pipe_address(node_addr, i))
        self._rf24.listen = True

        # setup address-related instance attibutes
        self._addr = node_addr
        self._addr_mask = 0
        self._multicast_level = 0
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

    def print_details(self, dump_pipes=False, network_only=False):
        if not network_only:
            self._rf24.print_details(False)
        print(
            "Network frame_cache contents:\n    Header is {}. Message contains:\n\t"
            "{}".format(
                self.frame_cache.header.to_string(),
                "an empty buffer"
                if not self.frame_cache.message
                else address_repr(self.frame_cache.message, False, " "),
            )
        )
        print(
            "Network flags______________0b{}".format(
                ("0" * (4 - (len(bin(self.network_flags)) - 2)))
                + bin(self.network_flags)[2:]
            )
        )
        print("Return on system messages__{}".format(bool(self.ret_sys_msg)))
        print("Allow network multicasts___{}".format(bool(self.allow_multicast)))
        print(
            "Multicast relay____________{}".format(
                "Enabled" if self._multicast_relay else "Disabled"
            )
        )
        print(
            "Network fragmentation______{}".format(
                "Enabled" if self._frag_enabled else "Disabled"
            )
        )
        print("Network max message length_{} bytes".format(self.max_message_length))
        print("Network TX timeout_________{} milliseconds".format(self.tx_timeout))
        print("Network Rounting timeout___{} milliseconds".format(self.route_timeout))
        print("Network node address_______{}".format(oct(self._addr)))
        if dump_pipes:
            self._rf24.print_pipes()

    @property
    def node_address(self):
        """get/set the node's :ref:`Logical Address <Logical Address>` for the
        `RF24Network` object."""
        return self._addr

    @property
    def fragmentation(self):
        """Enable/disable (`True`/`False`) the message fragmentation feature."""
        return self._frag_enabled

    @fragmentation.setter
    def fragmentation(self, enabled):
        enabled = bool(enabled)
        if enabled != self._frag_enabled:
            self.max_message_length = 144 if enabled else MAX_FRAG_SIZE
            if enabled:
                self.queue.max_message_length = self.max_message_length
                self.queue = FrameQueueFrag(self.queue)
            else:
                self.queue = FrameQueue(self.queue)
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
        level = min(4, max(level, 0))
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
        # print(oct(node_addr), "for pipe", pipe_number, "is", address_repr(result))
        return bytearray(result)

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
                # print(
                #     "discarding packet due to inadequate length"
                #     " or invalid network addresses."
                # )
                continue

            # print(
            #     "Received packet:", self.frame_cache.header.to_string(),
            #     "\n\t", address_repr(
            #             self.frame_cache.to_bytes(), reverse=False, delimit=" "
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
        if (
            self.ret_sys_msg
            and msg_t > MAX_USER_DEFINED_MSG_TYPE
            or msg_t == NETWORK_ACK
        ):
            print("Received system payload type", msg_t)
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
            print("Received external data type")
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
                    print(
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

    def peek(self):
        """Get (from `queue`) the next available frame."""
        return self.queue.peek()

    def read(self):
        """Get (from `queue`) the next available frame."""
        return self.queue.dequeue()

    def multicast(self, message, message_type, level=None):
        """Broadcast a message to all nodes on a certain network level."""
        if not self._validate_msg_len(len(message)):
            message = message[:MAX_FRAG_SIZE]
        level = self._multicast_level if level is None else min(3, max(level, 0))
        self.frame_cache.header.to_node = NETWORK_MULTICAST_ADDR
        self.frame_cache.header.from_node = self._addr
        message_type = (
            message_type if not isinstance(message_type, str) else ord(message_type[0])
        )
        self.frame_cache.header.message_type = message_type & 0xFF
        self.frame_cache.message = message
        return self._write(_level_to_address(level), USER_TX_MULTICAST)

    def _validate_msg_len(self, length):
        if length > self.max_message_length:
            raise ValueError("message's length is too large!")
        if length > MAX_FRAG_SIZE and not self._frag_enabled:
            return False
        return True

    def _write(self, traffic_direct, send_type):
        """entry point for transmitting the current frame_cache"""
        is_ack_type = self.frame_cache.is_ack_type()

        to_node, to_pipe, is_multicast = self._logical_to_physical(
            traffic_direct, send_type
        )

        if send_type == TX_ROUTED and traffic_direct == to_node and is_ack_type:
            time.sleep(0.002)

        # send the frame
        result = self._write_to_pipe(to_node, to_pipe, is_multicast)
        # print("Failed to send" if not result else "Successfully sent")

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
            ack_to_node, ack_to_pipe, is_multicast = self._logical_to_physical(
                self.frame_cache.header.from_node, TX_ROUTED
            )
            ack_ok = self._write_to_pipe(ack_to_node, ack_to_pipe, is_multicast)
            print(
                "Network ACK {} origin {} on pipe {}".format(
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
            self._rf24.listen = True
            self._rf24.auto_ack = 0x3E
            rx_timeout = self.route_timeout * 1000000 + time.monotonic_ns()
            while self._net_update() != NETWORK_ACK:
                if time.monotonic_ns() > rx_timeout:
                    result = False
                    break
            print(
                "Network ACK {}received from {} on pipe {}".format(
                    "" if result else "not ", oct(to_node), to_pipe
                ),
            )
            return result

        # ready radio to continue listening
        self._rf24.listen = True
        if not is_multicast:
            self._rf24.auto_ack = 0x3E
        return result

    def _write_to_pipe(self, to_node, to_pipe, is_multicast):
        """send prepared frame to a particular node's pipe"""
        result = False
        self._rf24.auto_ack = 0x3E + (not is_multicast)
        self.listen = False
        # print("Sending", self.frame_cache.header.to_string(), "on pipe", to_pipe)
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
                #     "Frag", count + 1, "of", total,
                #     "sent successfully" if result else "failed to send. Aborting"
                # )
                if not result:
                    break
            self.frame_cache.header.message_type = msg_t
        return result

    def _tx_standby(self, delta_time):
        result = False
        timeout = delta_time * 1000000 + time.monotonic_ns()
        while not result and time.monotonic_ns() < timeout:
            result = self._rf24.resend(send_only=True)
        return result

    def _logical_to_physical(self, to_node, send_type, is_multicast=False):
        """translate msg route into node address, pipe number, & multicast flag."""
        converted_to_node = self._parent
        converted_to_pipe = self._parent_pipe
        if send_type > TX_ROUTED:
            is_multicast = True
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
        return (converted_to_node, converted_to_pipe, is_multicast)
