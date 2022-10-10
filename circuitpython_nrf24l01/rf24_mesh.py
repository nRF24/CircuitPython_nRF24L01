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
import time
import struct

try:
    import json
except ImportError:
    pass  # some CircuitPython boards don't have the json module
try:
    from typing import Union, Dict, List, Optional, Callable, Any
except ImportError:
    pass
import busio  # type:ignore[import]
from digitalio import DigitalInOut  # type:ignore[import]
from .network.constants import (
    MESH_ADDR_REQUEST,
    MESH_ADDR_RESPONSE,
    NETWORK_DEFAULT_ADDR,
    NETWORK_MULTICAST_ADDR,
    NETWORK_POLL,
    MESH_ADDR_RELEASE,
    MESH_ADDR_LOOKUP,
    MESH_ID_LOOKUP,
    MESH_LOOKUP_TIMEOUT,
    MESH_WRITE_TIMEOUT,
    MESH_MAX_POLL,
    MESH_MAX_CHILDREN,
    TX_NORMAL,
    TX_PHYSICAL,
    TX_MULTICAST,
    MAX_FRAG_SIZE,
)
from .network.structs import RF24NetworkHeader, is_address_valid
from .network.mixins import NetworkMixin, _lvl_2_addr


class RF24MeshNoMaster(NetworkMixin):
    """A descendant of the same mixin class that `RF24Network` inherits from. This
    class adds easy Mesh networking capability (non-master nodes only)."""

    def __init__(
        self,
        spi: busio.SPI,
        csn_pin: DigitalInOut,
        ce_pin: DigitalInOut,
        node_id: int,
        spi_frequency: int = 10000000,
    ):
        super().__init__(spi, csn_pin, ce_pin, spi_frequency)
        self._id = min(255, node_id)
        #: This variable can be assigned a function to perform during long operations.
        self.block_less_callback: Optional[Callable[[], Any]] = None
        self.ret_sys_msg = True  # force _net_update() to return system message types
        self._begin(0 if not node_id else NETWORK_DEFAULT_ADDR)  # setup radio

    @property
    def node_id(self) -> int:
        """The unique ID number (1 byte long) of the mesh network node."""
        return self._id

    @node_id.setter
    def node_id(self, _id: int):
        if self._addr != NETWORK_DEFAULT_ADDR:
            self.release_address()
        self._id = _id & 0xFF

    def print_details(self, dump_pipes: bool = False, network_only: bool = False):
        """See RF24.print_details() and Shared Networking API docs"""
        super().print_details(False, network_only)
        print("Network node id____________{}".format(self.node_id))
        print("Mesh node allows children__{}".format(self._parenthood))
        if dump_pipes:
            self.print_pipes()

    def release_address(self) -> bool:
        """Forces an address lease to expire from the master."""
        if self._addr != NETWORK_DEFAULT_ADDR:
            self.frame_buf.header.to_node = 0
            self.frame_buf.header.from_node = self._addr
            self.frame_buf.header.message_type = MESH_ADDR_RELEASE
            self.frame_buf.message = b""
            if self._write(0, TX_NORMAL):
                super()._begin(NETWORK_DEFAULT_ADDR)
                return True
        return False

    def renew_address(self, timeout: Union[float, int] = 7.5):
        """Connect to the mesh network and request a new `node_address`."""
        if self._rf24.available():
            self.update()

        if self._addr != NETWORK_DEFAULT_ADDR:
            super()._begin(NETWORK_DEFAULT_ADDR)
        total_requests, request_count = (0, 0)
        end_timer = timeout + time.monotonic()
        while not self._request_address(request_count):
            if time.monotonic() > end_timer:
                return None
            time.sleep((25 + ((total_requests + 1) * (request_count + 1)) * 2) / 1000)
            request_count = (request_count + 1) % 4
            total_requests = (total_requests + 1) % 10
        return self._addr

    def lookup_address(self, node_id: int = None) -> int:
        """Convert a node's unique ID number into its corresponding
        :ref:`Logical Address <Logical Address>`."""
        if not node_id:
            return 0
        if self._addr == NETWORK_DEFAULT_ADDR:
            return -2
        return self._lookup_2_master(node_id, MESH_ADDR_LOOKUP)

    def lookup_node_id(self, address: int = None) -> int:
        """Convert a node's :ref:`Logical Address <Logical Address>` into its
        corresponding unique ID number."""
        if not address:
            return self._id if address is None else 0
        if self._addr == NETWORK_DEFAULT_ADDR:
            return -2
        return self._lookup_2_master(address, MESH_ID_LOOKUP)

    def _lookup_2_master(self, number: int, lookup_type: int) -> int:
        """Returns False if timed out, otherwise lookup result"""
        self.frame_buf.header.to_node = 0
        self.frame_buf.header.from_node = self._addr
        self.frame_buf.header.message_type = lookup_type
        if lookup_type == MESH_ID_LOOKUP:
            self.frame_buf.message = struct.pack("<H", number)
        else:
            self.frame_buf.message = bytes([number])
        if not self._write(0, TX_NORMAL):
            return -1
        timeout = MESH_LOOKUP_TIMEOUT * 1000000 + time.monotonic_ns()
        while self._net_update() not in (MESH_ID_LOOKUP, MESH_ADDR_LOOKUP):
            if callable(self.block_less_callback):
                self.block_less_callback()  # pylint: disable=not-callable
            if time.monotonic_ns() > timeout:
                return -1
        if lookup_type == MESH_ADDR_LOOKUP:
            return struct.unpack("<H", self.frame_buf.message[:2])[0]
        return self.frame_buf.message[0]

    def check_connection(self) -> bool:
        """Check for network connectivity (not for use on master node)."""
        # do a double check as a manual retry in lack of using auto-ack
        if self.lookup_address(self._id) < 1:
            if self.lookup_address(self._id) < 1:
                return False
        return True

    def update(self) -> int:
        """Checks for incoming network data and returns last message type (if any)"""
        msg_t = self._net_update()
        if self._addr == NETWORK_DEFAULT_ADDR:
            return msg_t
        return msg_t

    def _request_address(self, level: int) -> bool:
        """Get a new address assigned from the master node"""
        contacts = self._make_contact(level)
        # print("Got", len(contacts), "responses on level",level)
        if not contacts:
            return False

        new_addr = None
        for contact in contacts:
            # print("Requesting address from", oct(contact))
            self.frame_buf.header.to_node = contact
            self.frame_buf.header.from_node = NETWORK_DEFAULT_ADDR
            self.frame_buf.header.message_type = MESH_ADDR_REQUEST
            self.frame_buf.header.reserved = self._id
            self.frame_buf.message = b""
            self._write(contact, TX_PHYSICAL)  # do a no auto-ack write
            timeout = 225000000 + time.monotonic_ns()
            while time.monotonic_ns() < timeout:  # wait for network ack
                if (
                    self._net_update() == MESH_ADDR_RESPONSE
                    and self.frame_buf.header.reserved == self.node_id
                ):
                    new_addr = struct.unpack("<H", self.frame_buf.message[:2])[0]
                    level = 0 if contact < 7 else len(oct(contact)[2:])
                    test_addr = new_addr & ~(0xFFFF << (level * 3))
                    if test_addr != contact:
                        new_addr = None
                    else:
                        break
            if callable(self.block_less_callback):
                self.block_less_callback()  # pylint: disable=not-callable
        if new_addr is None:
            return False
        super()._begin(new_addr)
        # print("new address assigned:", oct(new_addr))
        # do a double check as a manual retry in lack of using auto-ack
        if self.lookup_node_id(self._addr) != self._id:
            if self.lookup_node_id(self._addr) != self._id:
                super()._begin(NETWORK_DEFAULT_ADDR)
                return False
        return True

    def _make_contact(self, lvl: int) -> List[int]:
        """Make a list of connections after multicasting a `NETWORK_POLL` message."""
        responders: List[int] = []
        self.frame_buf.header.to_node = NETWORK_MULTICAST_ADDR
        self.frame_buf.header.from_node = NETWORK_DEFAULT_ADDR
        self.frame_buf.header.message_type = NETWORK_POLL
        self.frame_buf.message = b""
        # self.multicast() does some extra logic to protect from user misuse.
        self._write(_lvl_2_addr(lvl), TX_MULTICAST)
        timeout = 55000000 + time.monotonic_ns()
        while time.monotonic_ns() < timeout and len(responders) < MESH_MAX_POLL:
            if self._net_update() == NETWORK_POLL:
                contacted = self.frame_buf.header.from_node
                is_duplicate = False
                for contact in responders:
                    if contacted == contact:
                        is_duplicate = True
                if not is_duplicate:
                    responders.append(contacted)
        return responders

    @property
    def allow_children(self) -> bool:
        """Allow/disallow child node to connect to this network node."""
        return self._parenthood

    @allow_children.setter
    def allow_children(self, allow: bool):
        self._parenthood = allow

    def send(
        self,
        to_node: int,
        message_type: Union[int, str],
        message: Union[bytes, bytearray],
    ) -> bool:
        """Send a message to a mesh `node_id`."""
        if self._addr == NETWORK_DEFAULT_ADDR:
            return False
        if to_node and to_node != self._id:
            timeout = MESH_WRITE_TIMEOUT * 1000000 + time.monotonic_ns()
            retry_delay = 5
            to_node_addr = -2
            while to_node_addr < 0:
                to_node_addr = self.lookup_address(to_node)
                if time.monotonic_ns() >= timeout:
                    return False
                if to_node_addr < 0:
                    time.sleep(retry_delay / 1000)
                    retry_delay += 10
            to_node = to_node_addr
        if to_node == self._id:
            to_node = self._addr
        return self.write(to_node, message_type, message)

    def write(
        self,
        to_node: int,
        message_type: Union[int, str],
        message: Union[bytes, bytearray],
    ) -> bool:
        """Send a message to a network `node_address`."""
        if not isinstance(message, (bytes, bytearray)):
            raise TypeError("message must be a `bytes` or `bytearray` object")
        if not self._validate_msg_len(len(message)):
            message = message[:MAX_FRAG_SIZE]
        if self._addr == NETWORK_DEFAULT_ADDR or not is_address_valid(to_node):
            return False
        self.frame_buf.header = RF24NetworkHeader(to_node, message_type)
        self.frame_buf.header.from_node = self._addr
        self.frame_buf.message = message
        return self._write(to_node, TX_NORMAL)


class RF24Mesh(RF24MeshNoMaster):
    """A descendant of the base class `RF24MeshNoMaster` that adds algorithms needed
    for Mesh network master nodes."""

    def __init__(
        self,
        spi: busio.SPI,
        csn_pin: DigitalInOut,
        ce_pin: DigitalInOut,
        node_id: int,
        spi_frequency: int = 10000000,
    ):
        super().__init__(spi, csn_pin, ce_pin, node_id, spi_frequency)
        self._do_dhcp = False
        #: A `dict` that enables master nodes to act as a DNS.
        self.dhcp_dict = {}  # type: Dict[int, int]

    def update(self) -> int:
        """Checks for incoming network data and returns last message type (if any)"""
        msg_t = super().update()
        if msg_t == MESH_ADDR_REQUEST and self.frame_buf.header.reserved:
            self._do_dhcp = True
        if not self.lookup_node_id():  # if this is the master node
            if msg_t in (MESH_ADDR_LOOKUP, MESH_ID_LOOKUP):
                self.frame_buf.header.to_node = self.frame_buf.header.from_node

                ret_val = 0  # will be -2 for requesting un-assigned nodes
                if msg_t == MESH_ADDR_LOOKUP:
                    ret_val = self.lookup_address(self.frame_buf.message[0])
                    self.frame_buf.message = struct.pack("<H", ret_val)
                else:
                    ret_val = self.lookup_node_id(
                        struct.unpack("<H", self.frame_buf.message[:2])[0]
                    )
                    self.frame_buf.message = bytes([ret_val])
                self._write(self.frame_buf.header.to_node, TX_NORMAL)
            elif msg_t == MESH_ADDR_RELEASE:
                for n_id, addr in self.dhcp_dict.items():
                    if addr == self.frame_buf.header.from_node:
                        del self.dhcp_dict[n_id]
                        break
            self._dhcp()
        return msg_t

    def _dhcp(self):
        """Updates `_dhcp_dict` of assigned addresses (master node only)."""
        if self._do_dhcp:
            self._do_dhcp = False
        else:
            return
        new_addr, via_node, shift_val = (0, 0, 0)
        if self.frame_buf.header.from_node != NETWORK_DEFAULT_ADDR:
            via_node = self.frame_buf.header.from_node
            temp = via_node
            while temp:
                temp >>= 3
                shift_val += 3
        extra_child = self.frame_buf.header.from_node == NETWORK_DEFAULT_ADDR

        for i in range(MESH_MAX_CHILDREN + extra_child, 0, -1):
            found_addr, new_addr = (False, via_node | (i << shift_val))
            if new_addr == NETWORK_DEFAULT_ADDR:
                continue
            for n_id, addr in self.dhcp_dict.items():
                # print(i, "(in _addr_dict) ID:", n_id, "ADDR:", oct(addr))
                if addr == new_addr and n_id != self.frame_buf.header.reserved:
                    found_addr = True
                    break
            if not found_addr:
                self.set_address(self.frame_buf.header.reserved, new_addr)

                self.frame_buf.header.message_type = MESH_ADDR_RESPONSE
                self.frame_buf.header.to_node = self.frame_buf.header.from_node
                self.frame_buf.message = struct.pack("<H", new_addr)
                if self.frame_buf.header.from_node != NETWORK_DEFAULT_ADDR:
                    if not self._write(self.frame_buf.header.to_node, TX_NORMAL):
                        self._write(self.frame_buf.header.to_node, TX_NORMAL)
                else:
                    self._write(self.frame_buf.header.to_node, TX_PHYSICAL)
                break
            # print("address", new_addr, "not allocated.")

    def set_address(
        self, node_id: int, node_address: int, search_by_address: bool = False
    ):
        """Set/change a `node_id` and `node_address` pair in the `dhcp_dict`."""
        for n_id, addr in self.dhcp_dict.items():
            if not search_by_address:
                if n_id == node_id:
                    self.dhcp_dict[n_id] = node_address
                    return
            else:
                if addr == node_address:
                    del self.dhcp_dict[n_id]
                    self.dhcp_dict[node_id] = node_address
                    return
        self.dhcp_dict[node_id] = node_address

    def save_dhcp(self, filename: str = "dhcplist.json", as_bin: bool = False):
        """Save the `dhcp_dict` to a JSON file (meant for master nodes only)."""
        with open(filename, "wb") as json_file:
            # This throws an OSError if file system is read-only. ALL MCU boards
            # running CircuitPython firmware (not RPi) have read-only file system.
            if json is not None and not as_bin:
                json_file.write(
                    json.dumps(self.dhcp_dict, indent=2).encode(encoding="utf-8")
                )
            elif as_bin:
                for _id, _addr in self.dhcp_dict.items():
                    json_file.write(bytes([_id, 0]))  # pad id w/ 0 for mem alignment
                    json_file.write(struct.pack("<H", _addr))

    def load_dhcp(self, filename: str = "dhcplist.json", as_bin: bool = False):
        """Load the `dhcp_dict` from a JSON file (meant for master nodes only)."""
        with open(filename, "rb") as json_file:
            if json is not None and not as_bin:
                temp_dict = json.load(json_file)  # type: Dict[str, int]
                # convert keys from `str` to `int`
                for n_id, addr in temp_dict.items():
                    self.set_address(int(n_id), addr, True)
            elif as_bin:
                buffer = json_file.read()
                for i in range(int(len(buffer) / 4)):
                    index = i * 4
                    self.set_address(
                        buffer[index],  # skip index + 1 as it's only used for padding
                        struct.unpack("<H", buffer[index + 2 : index + 4])[0],
                    )

    def print_details(self, dump_pipes: bool = False, network_only: bool = False):
        """See RF24.print_details() and Shared Networking API docs"""
        super().print_details(False, network_only)
        if not self._id and self.dhcp_dict:  # only on master node
            print("DHCP List:\n    ID\tAddress\n    ---\t-------")
            for n_id, addr in self.dhcp_dict.items():
                print("    {}\t{}".format(n_id, oct(addr)))
        if dump_pipes:
            self._rf24.print_pipes()

    def lookup_address(self, node_id: int = None) -> int:
        """Convert a node's unique ID number into its corresponding
        :ref:`Logical Address <Logical Address>`."""
        if not node_id:
            return 0
        if self._addr == NETWORK_DEFAULT_ADDR:
            return -2
        if not self._id:
            return self._get_address(node_id, MESH_ADDR_LOOKUP)
        return self._lookup_2_master(node_id, MESH_ADDR_LOOKUP)

    def lookup_node_id(self, address: int = None) -> int:
        """Convert a node's :ref:`Logical Address <Logical Address>` into its
        corresponding unique ID number."""
        if not address:
            return self._id if address is None else 0
        if self._addr == NETWORK_DEFAULT_ADDR:
            return -2
        if not self._addr:
            return self._get_address(address, MESH_ID_LOOKUP)
        return self._lookup_2_master(address, MESH_ID_LOOKUP)

    def _get_address(self, number: int, lookup_type: int) -> int:
        """Helper for get_address() and lookup_node_id()"""
        for n_id, addr in self.dhcp_dict.items():
            if lookup_type == MESH_ID_LOOKUP and addr == number:
                return n_id
            if lookup_type == MESH_ADDR_LOOKUP and n_id == number:
                return addr
        return -2
