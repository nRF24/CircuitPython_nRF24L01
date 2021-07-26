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
import struct
from .constants import (
    NETWORK_ADDR_REQUEST,
    NETWORK_ADDR_RESPONSE,
    NETWORK_DEBUG,
    NETWORK_DEBUG_MINIMAL,
    NETWORK_DEFAULT_ADDR,
    NETWORK_POLL,
    FLAG_NO_POLL,
    MESH_ADDR_RELEASE,
    MESH_ADDR_LOOKUP,
    MESH_ID_LOOKUP,
    MESH_LOOKUP_TIMEOUT,
    MESH_WRITE_TIMEOUT,
    MESH_MAX_POLL,
    MESH_MAX_CHILDREN,
)
from .packet_structs import RF24NetworkFrame, RF24NetworkHeader
from .rf24_network import RF24Network


def _get_level(address: int) -> int:
    """ return the number of digits in a given address """
    count = 0
    while address:
        address >>= 3
        count += 1
    return count


class RF24Mesh(RF24Network):
    """A descendant of the base class `RF24Network` that adds easy Mesh networking
    capability."""
    def __init__(self, spi, csn_pin, ce_pin, spi_frequency=10000000):
        super().__init__(
            spi,
            csn_pin,
            ce_pin,
            NETWORK_DEFAULT_ADDR,
            spi_frequency=spi_frequency
        )

        # 1-byte ID number unique to the network node (not the same as `node_address`)
        self._node_id = 0
        # allow child nodes to connect to this network node
        self.allow_children = True
        #: This variable can be assigned a function to perform during long operations.
        self.less_blocking_callback = None

        # force self._net_update() to return system message types
        self.ret_sys_msg = True
        # A `dict` of assigned addresses paired to the Mesh nod'es unique ID number
        self._addr_dict = {}
        self._do_dhcp = False  # flag used to manage updating the _addr_dict

    @property
    def node_id(self):
        """The unique ID number (1 byte long) of the mesh network node."""
        return self._node_id

    @node_id.setter
    def node_id(self, _id):
        self._node_id = _id & 0xFF

    def print_details(self, dump_pipes=True):
        """.. seealso:: :py:meth:`~circuitpython_nrf24l01.rf24.RF24.print_details()`"""
        super().print_details(dump_pipes)
        print("Network node id_______", self.node_id)

    def release_address(self) -> bool:
        """Forces an address lease to expire from the master."""
        if (
            self._addr != NETWORK_DEFAULT_ADDR
            and self._pre_write(
                RF24NetworkFrame(
                    RF24NetworkHeader(0, MESH_ADDR_RELEASE),
                    b""
                )
            )
        ):
            super()._begin(NETWORK_DEFAULT_ADDR)
            return True
        return False

    def renew_address(self, timeout=7.5):
        """Connect to the mesh network and request a new `node_address`."""
        if self._rf24.available():
            self.update()

        if self._addr != NETWORK_DEFAULT_ADDR:
            super()._begin(NETWORK_DEFAULT_ADDR)
        total_requests, request_counter = (0, 0)
        end_timer = time.monotonic() + timeout
        while not self._request_address(request_counter):
            if time.monotonic() >= end_timer:
                return None
            time.sleep(
                (50 + ((total_requests + 1) * (request_counter + 1)) * 2) / 1000
            )
            request_counter = (request_counter + 1) % 4
            total_requests = (total_requests + 1) % 10
        return self._addr

    def get_address(self, node_id=None) -> int:
        """Convert a node's unique ID number into its corresponding
        :ref:`Logical Address <Logical Address>`."""
        if not node_id:
            return 0

        if not self.get_node_id() or self._addr == NETWORK_DEFAULT_ADDR:
            if self._addr != NETWORK_DEFAULT_ADDR:
                for n_id, addr in self._addr_dict.items():
                    if n_id == node_id:
                        return addr
            return -2

        if self._pre_write(
            RF24NetworkFrame(
                RF24NetworkHeader(0, MESH_ADDR_LOOKUP), bytes([node_id])
            )
        ):
            if self._wait_for_lookup_response():
                return struct.unpack("<H", self.frame_cache.message[:2])[0]
        return -1

    def get_node_id(self, address=None) -> int:
        """Convert a node's :ref:`Logical Address <Logical Address>` into its unique ID
        number."""
        if not address:
            return self._node_id if address is None else 0

        # if this is a master node
        if not self._addr or self._addr == NETWORK_DEFAULT_ADDR:
            if self._addr != NETWORK_DEFAULT_ADDR:
                for n_id, addr in self._addr_dict.items():
                    if addr == address:
                        return n_id
            return -2

        # else this is not a master node; request address lookup from master
        if self._pre_write(
            RF24NetworkFrame(
                RF24NetworkHeader(0, MESH_ID_LOOKUP),
                struct.pack("<H", address)
            )
        ):
            if self._wait_for_lookup_response():
                return self.frame_cache.message[0]
        return -1

    def _wait_for_lookup_response(self):
        """returns False if timed out, otherwise True"""
        timeout = time.monotonic() + MESH_LOOKUP_TIMEOUT / 1000
        while self._net_update() not in (MESH_ID_LOOKUP, MESH_ADDR_LOOKUP):
            if callable(self.less_blocking_callback):
                self.less_blocking_callback()  # pylint: disable=not-callable
            if time.monotonic() > timeout:
                return False
        return True

    def check_connection(self):
        """Check for network conectivity (not for use on master node)."""
        # do a double check as a manual retry in lack of using auto-ack
        if self.get_address(self._node_id) < 1:
            if self.get_address(self._node_id) < 1:
                return False
        return True

    def update(self):
        """Checks for incoming network data and returns last message type (if any)"""
        msg_t = self._net_update()
        if self._addr == NETWORK_DEFAULT_ADDR:
            return msg_t
        if msg_t == NETWORK_ADDR_REQUEST:
            self._do_dhcp = True

        if not self.get_node_id():  # if this is the master node
            if msg_t in (MESH_ADDR_LOOKUP, MESH_ID_LOOKUP):
                self.frame_cache.header.to_node = self.frame_cache.header.from_node

                ret_val = 0
                if msg_t == MESH_ADDR_LOOKUP:
                    ret_val = self.get_address(self.frame_cache.message[0])
                    self.frame_cache.message = struct.pack("<H", ret_val)
                else:
                    ret_val = self.get_node_id(
                        struct.unpack("<H", self.frame_cache.message[:2])[0]
                    )
                    self.frame_cache.message = bytes([ret_val])
                self._pre_write(self.frame_cache)
            elif msg_t == MESH_ADDR_RELEASE:
                for n_id, addr in self._addr_dict.items():
                    if addr == self.frame_cache.header.from_node:
                        # pylint: disable=unnecessary-dict-index-lookup
                        del self._addr_dict[n_id]
                        # pylint: enable=unnecessary-dict-index-lookup
        return msg_t

    def dhcp(self):
        """Updates the internal `dict` of assigned addresses (master node only). Be
        sure to call this after performing an
        :meth:`~circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.update()`."""
        if not self._do_dhcp:
            return
        self._do_dhcp = False
        new_addr = 0
        if (
            not self.frame_cache.header.reserved
            or self.frame_cache.header.message_type != NETWORK_ADDR_REQUEST
        ):
            self._log(
                NETWORK_DEBUG,
                "frame_cache: improper node ID or not a NETWORK_ADDR_REQUEST type."
            )
            return

        via_node, shift_val = (0, 0)
        if self.frame_cache.header.from_node != NETWORK_DEFAULT_ADDR:
            via_node = self.frame_cache.header.from_node
            temp = via_node
            while temp:
                temp >>= 3
                shift_val += 3
        extra_child = self.frame_cache.header.from_node == NETWORK_DEFAULT_ADDR

        for i in range(MESH_MAX_CHILDREN + extra_child, 0, -1):
            found_addr = False
            new_addr = via_node | (i << shift_val)
            if new_addr == NETWORK_DEFAULT_ADDR:
                continue
            for n_id, addr in self._addr_dict.items():
                self._log(
                    NETWORK_DEBUG_MINIMAL,
                    "(in _addr_dict) ID: {}, ADDR: {}".format(n_id, oct(addr))
                )
                if addr == new_addr and n_id != self.frame_cache.header.reserved:
                    found_addr = True
                    break
            if not found_addr:
                self._set_address(self.frame_cache.header.reserved, new_addr)

                self.frame_cache.header.message_type = NETWORK_ADDR_RESPONSE
                self.frame_cache.header.to_node = self.frame_cache.header.from_node
                self.frame_cache.message = struct.pack("<H", new_addr)
                if self.frame_cache.header.from_node != NETWORK_DEFAULT_ADDR:
                    if not self._pre_write(self.frame_cache):
                        self._pre_write(self.frame_cache)
                else:
                    self._pre_write(self.frame_cache, self.frame_cache.header.to_node)
                break
            # log an error saying that address couldn't be assigned on the net lvl
            self._log(NETWORK_DEBUG, "address {} not allocated.".format(new_addr))

    def _set_address(self, node_id, address, search_by_address=False):
        """Set or change a node_id and network address pair on the master node."""
        for n_id, addr in self._addr_dict.items():
            if not search_by_address:
                if n_id == node_id:
                    self._addr_dict[n_id] = address
                    return
            else:
                if addr == address:
                    # pylint: disable=unnecessary-dict-index-lookup
                    del self._addr_dict[n_id]
                    # pylint: enable=unnecessary-dict-index-lookup
                    self._addr_dict[node_id] = address
                    return
        self._addr_dict[node_id] = address
        # self.save_dhcp()

    # pylint: disable=arguments-renamed,arguments-differ
    def send(self, to_node_id, message_type, message):
        """Send a message to a mesh `node_id`."""
        if not isinstance(message, (bytes, bytearray)):
            raise TypeError("message must be a `bytes` or `bytearray` object")
        to_node = -2
        timeout = time.monotonic() + MESH_WRITE_TIMEOUT / 1000
        retry_delay = 5
        while to_node < 0:
            to_node = self.get_address(to_node_id)
            if time.monotonic() > timeout and to_node == -2:
                return False
            retry_delay += 10
            time.sleep(retry_delay / 1000)
        if self._addr == NETWORK_DEFAULT_ADDR:
            return False
        return self._pre_write(
            RF24NetworkFrame(
                RF24NetworkHeader(to_node, message_type),
                message,
            )
        )

    def write(self, to_node_address, message_type, message):
        """Send a message to a network `node_address`."""
        return self._pre_write(
            RF24NetworkFrame(
                RF24NetworkHeader(to_node_address, message_type),
                message,
            )
        )

    # pylint: enable=arguments-renamed,arguments-differ
    def _request_address(self, level: int):
        """Get a new address assigned from the master node"""
        contacts = self._make_contacts(level)
        # self._log(
        #     NETWORK_DEBUG,
        #     "Got {} responses on level {}".format(len(contacts), level)
        # )
        if not contacts:
            return False

        new_addr = None
        for contact in contacts:
            head = RF24NetworkHeader(contact, NETWORK_ADDR_REQUEST)
            head.reserved = self._node_id
            self._log(NETWORK_DEBUG, "Requesting address from " + oct(contact))
            # do a direct write (no auto-ack)
            self._pre_write(RF24NetworkFrame(head, b""), contact)
            timeout = time.monotonic() + 0.225
            while time.monotonic() < timeout:  # wait for network ack
                if (
                    self._net_update() == NETWORK_ADDR_RESPONSE
                    and self.frame_cache.header.reserved == self.node_id
                ):
                    new_addr = struct.unpack("<H", self.frame_cache.message[:2])[0]
                    test_addr = new_addr
                    mask = 0
                    for _ in range(_get_level(contact) * 3):
                        mask <<= 3
                        mask += 7
                    test_addr &= mask
                    self._log(
                        NETWORK_DEBUG,
                        "{} vs {}; new address ({}) check {}!".format(
                            test_addr,
                            contact,
                            oct(new_addr),
                            "failed" if test_addr != contact else "passed",
                        )
                    )
                    if test_addr == contact:
                        break
                if callable(self.less_blocking_callback):
                    self.less_blocking_callback()  # pylint: disable=not-callable
        if new_addr is None:
            return False

        super()._begin(new_addr)

        # do a double check as a manual retry in lack of using auto-ack
        if self.get_node_id(self._addr) != self._node_id:
            if self.get_node_id(self._addr) != self._node_id:
                super()._begin(NETWORK_DEFAULT_ADDR)
                return False
        return True

    def _make_contacts(self, level):
        """Make a list of connections after multicasting a `NETWORK_POLL` message."""
        self.multicast(RF24NetworkHeader(message_type=NETWORK_POLL), b"", level)
        responders = []
        timeout = time.monotonic() + 0.055
        while True:
            if self._net_update() == NETWORK_POLL:
                contacted = self.frame_cache.header.from_node
                is_duplicate = False
                for contact in responders:
                    if contacted == contact:
                        is_duplicate = True
                if not is_duplicate:
                    responders.append(contacted)

            if time.monotonic() > timeout or len(responders) >= MESH_MAX_POLL:
                break
        return responders

    @property
    def allow_children(self):
        """Allow/disallow child node to connect to this network node."""
        return bool(self.network_flags & FLAG_NO_POLL)

    @allow_children.setter
    def allow_children(self, allow):
        self.network_flags &= (~FLAG_NO_POLL if allow else FLAG_NO_POLL)
