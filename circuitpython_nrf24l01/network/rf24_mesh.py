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
    NETWORK_MULTICAST_ADDR,
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
from .packet_structs import RF24NetworkHeader
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
        self.less_blocking_helper_function = None
        """Requesting a new address can take a while since it sequentially attempts to
        get re-assigned to the first highest network level.

        This variable can be assigned a function to perform during this lengthy process
        of requesting a new address."""

        # force super().update() to return system message types
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
        """Forces address lease to expire. Useful when disconnecting from network."""
        if (
            self._addr != NETWORK_DEFAULT_ADDR
            and super().send(RF24NetworkHeader(0, MESH_ADDR_RELEASE), b"", 0)
        ):
            super()._begin(NETWORK_DEFAULT_ADDR)
            return True
        return False

    def renew_address(self, timeout=7.5) -> int:
        """Reconnect to the network and renew the node address."""
        if self._rf24.available():
            self.update()

        if self._addr != NETWORK_DEFAULT_ADDR:
            super()._begin(NETWORK_DEFAULT_ADDR)
        total_requests, request_counter = (0, 0)
        end_timer = time.monotonic() + timeout
        while not self._request_address(request_counter):
            if time.monotonic() >= end_timer:
                return 0
            time.sleep(
                (50 + ((total_requests + 1) * (request_counter + 1)) * 2) / 1000
            )
            request_counter = (request_counter + 1) % 4
            total_requests = (total_requests + 1) % 10
        return self._addr

    def get_address(self, _id=None) -> int:
        """Convert nodeID into a logical network address (as used by `RF24Network`)."""
        if not _id:
            return 0

        if not self.get_node_id() or self._addr == NETWORK_DEFAULT_ADDR:
            if self._addr != NETWORK_DEFAULT_ADDR:
                for n_id, addr in self._addr_dict:
                    if n_id == self.node_id:
                        return addr
            return -2

        if super().send(RF24NetworkHeader(0, MESH_ADDR_LOOKUP), bytes([self.node_id])):
            if self._wait_for_lookup_response():
                return struct.unpack("<H", self.frame_cache.message[:2])[0]
        return -1

    def get_node_id(self, address=None) -> int:
        """Convert logical network address (as used by `RF24Network`) into a nodeID."""
        if not address:
            return self.node_id if address is None else 0

        # if this is a master node
        if not self._addr or self._addr == NETWORK_DEFAULT_ADDR:
            if self._addr != NETWORK_DEFAULT_ADDR:
                for n_id, addr in self._addr_dict:
                    if addr == address:
                        return n_id
            return -2

        # else this is not a master node; request address lookup from master
        if super().send(RF24NetworkHeader(0, MESH_ID_LOOKUP), self._addr):
            if self._wait_for_lookup_response():
                return self.frame_cache.message[0]
        return -1

    def _wait_for_lookup_response(self):
        """returns False if timed out, otherwise True"""
        timeout = time.monotonic_ns() + MESH_LOOKUP_TIMEOUT / 1000000
        while super().update() != MESH_ID_LOOKUP:
            if self.less_blocking_helper_function is not None:
                self.less_blocking_helper_function()  # pylint: disable=not-callable
            if time.monotonic_ns() > timeout:
                return False
        return True

    @property
    def check_connection(self) -> bool:
        """Check for network conectivity."""
        return not self.get_address(self.node_id) < 1

    def update(self) -> int:
        """checks for incoming network data and returns last message type (if any)"""
        msg_t = super().update()
        if self._addr == NETWORK_DEFAULT_ADDR:
            return msg_t
        if msg_t == NETWORK_ADDR_REQUEST:
            self._do_dhcp = True

        if not self.get_node_id():  # if this is the master node
            if msg_t in (MESH_ADDR_LOOKUP, MESH_ID_LOOKUP):
                self.frame_cache.header.to_node = self.frame_cache.header.from_node

                return_addr = struct.unpack("<H", self.frame_cache.message[:2])
                if msg_t == MESH_ADDR_LOOKUP:
                    return_addr = self.get_address(return_addr)
                else:
                    return_addr = self.get_node_id(return_addr)
                super().send(self.frame_cache.header, struct.pack("<H", return_addr))
            elif msg_t == MESH_ADDR_RELEASE:
                from_addr = self.frame_cache.header.from_node
                for n_id, addr in self._addr_dict:
                    if addr == from_addr:
                        # del self._addr_dict[key]
                        self._addr_dict[n_id] = 0
        return msg_t

    def dhcp(self):
        """Updates the internal `dict` of assigned addresses (master node only). Be
        sure to call this after performing an
        :meth:`~circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.update()`."""
        # pylint: disable=too-many-branches
        if not self._do_dhcp:
            return
        self._do_dhcp = False
        header = self.frame_cache.header
        new_addr = 0
        if not header.reserved or header.message_type != NETWORK_ADDR_REQUEST:
            self._log(
                NETWORK_DEBUG,
                "Got bad node ID or not a NETWORK_ADDR_REQUEST type"
            )
            return

        via_node, shift_val, extra_child = (0, 0, False)
        if header.from_node != NETWORK_DEFAULT_ADDR:
            via_node = header.from_node
            temp = via_node
            while temp:
                temp >>= 3
                shift_val += 1
        else:
            extra_child = True
        for i in range(MESH_MAX_CHILDREN + extra_child, 0, -1):
            found_addr = False
            new_addr = via_node | (i << shift_val)
            if new_addr == NETWORK_DEFAULT_ADDR:
                continue
            for n_id, addr in self._addr_dict:
                self._log(
                    NETWORK_DEBUG_MINIMAL,
                    "(in _addr_dict) ID: {}, ADDR: {}".format(n_id, oct(addr))
                )
                if addr == new_addr and n_id != header.reserved:
                    found_addr = True
                    break
            if found_addr:
                self._log(NETWORK_DEBUG, "address {} not assigned.".format(new_addr))
            else:
                header.message_type = NETWORK_ADDR_RESPONSE
                header.to_node = header.from_node

                self._set_address(header.reserved, new_addr)
                if header.from_node != NETWORK_DEFAULT_ADDR:
                    if not super().send(header, struct.pack("<H", new_addr)):
                        self._rf24.resend()
                else:
                    super().send(header, struct.pack("<H", new_addr), header.to_node)
                break
        # pylint: enable=too-many-branches

    def _set_address(self, node_id, address, search_by_address=False):
        """Set or change a node_id and network address pair on the master node."""
        for n_id, addr in self._addr_dict:
            if not search_by_address:
                if n_id == node_id:
                    self._addr_dict[n_id] = address
                    break
            else:
                if addr == address:
                    del self._addr_dict[n_id]
                    self._addr_dict[node_id] = address
                    break
        # self.save_dhcp()

    # pylint: disable=arguments-renamed
    def send(self, message, message_type, to_node_id) -> bool:
        """Send a message to a node id."""
        to_node = 0
        timeout = time.monotonic_ns() + MESH_WRITE_TIMEOUT * 1000000
        retry_delay = 5
        while to_node < 0:
            to_node = self.get_address(to_node_id)
            if time.monotonic_ns() > timeout or to_node == -2:
                return False
            retry_delay += 10
            time.sleep(retry_delay / 1000)
        return self.write(to_node, message, message_type)

    def write(self, to_node, message, message_type):
        """send a message to a node address."""
        if self._addr == NETWORK_DEFAULT_ADDR:
            return False
        return super().send(RF24NetworkHeader(to_node, message_type), message)

    # pylint: enable=arguments-renamed
    def _request_address(self, level: int) -> bool:
        """Get a new address assigned from the master node"""
        self._log(NETWORK_DEBUG, "Mesh requesting address from master")
        contacts = self._make_contacts(level)
        self._log(
            NETWORK_DEBUG,
            "Got {} responses on level {}".format(len(contacts), level)
        )
        if not contacts:
            return False

        new_addy = -1
        for contact in contacts:
            head = RF24NetworkHeader(contact, NETWORK_ADDR_RESPONSE)
            head.reserved = self._addr
            self._log(NETWORK_DEBUG, "Requesting address from {}" % contact)
            super().send(head, b"", contact)  # direct write (no auto-ack)
            timeout = time.monotonic_ns() + 225000000
            while time.monotonic_ns() < timeout:  # wait for network ack
                if (
                    super().update() == NETWORK_ADDR_RESPONSE
                    and self.frame_cache.header.reserved == self.node_id
                ):
                    new_addy = struct.unpack("<H", self.frame_cache.message[:2])
                    mask = 0
                    for _ in range(_get_level(contact) * 3):
                        mask <<= 3
                        mask += 7
                    new_addy &= mask
                    if new_addy == contact:
                        break
                if self.less_blocking_helper_function is not None:
                    self.less_blocking_helper_function()  # pylint: disable=not-callable
        if new_addy == -1:
            return False

        super()._begin(new_addy)
        if self.get_node_id(self._addr) != self._addr:
            super()._begin(NETWORK_DEFAULT_ADDR)
            return False
        return True

    def _make_contacts(self, level):
        """Make a list of connections after multicasting a `NETWORK_POLL` message."""
        head = RF24NetworkHeader(NETWORK_MULTICAST_ADDR, NETWORK_POLL)
        super().multicast(head, b"", level)
        responders = []
        timeout = time.monotonic_ns() + 55000000
        while True:
            if super().update() == NETWORK_POLL:
                contacted = self.frame_cache.header.from_node
                is_duplicate = False
                for contact in responders:
                    if contacted == contact:
                        is_duplicate = True
                if not is_duplicate:
                    responders.append(contacted)

            if time.monotonic_ns() > timeout or len(responders) >= MESH_MAX_POLL:
                break
        return responders

    @property
    def allow_children(self):
        """allow/disallow child node to connect to this network node."""
        return bool(self.network_flags & FLAG_NO_POLL)

    @allow_children.setter
    def allow_children(self, allow):
        self.network_flags &= (~FLAG_NO_POLL if allow else FLAG_NO_POLL)