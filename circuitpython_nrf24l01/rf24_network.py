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
from .network.mixins import NetworkMixin
from .network.structs import (
    RF24NetworkFrame,
    is_address_valid,
)
from .network.constants import (
    NETWORK_MULTICAST_ADDR,
    AUTO_ROUTING,
    TX_NORMAL,
    USER_TX_TO_PHYSICAL_ADDRESS,
    USER_TX_TO_LOGICAL_ADDRESS,
    USER_TX_MULTICAST,
    MAX_FRAG_SIZE,
)


class RF24Network(NetworkMixin):
    """The object used to instantiate the nRF24L01 as a network node."""

    def __init__(self, spi, csn_pin, ce_pin, node_address, spi_frequency=10000000):
        if not is_address_valid(node_address):
            raise ValueError("node_address argument is invalid or malformed")
        super().__init__(spi, csn_pin, ce_pin, spi_frequency)

        # setup radio
        self._begin(node_address)

    @NetworkMixin.node_address.setter
    def node_address(self, val):
        if not is_address_valid(val):
            return
        self._begin(val)

    def update(self):
        """This function is used to keep the network layer current."""
        return self._net_update()

    def send(self, header, message):
        """Deliver a message according to the header information."""
        if not self._validate_msg_len(len(message)):
            message = message[:MAX_FRAG_SIZE]
        header.from_node = self._addr
        if not header.is_valid():
            return False
        return self._pre_write(RF24NetworkFrame(header, message))

    def write(self, frame, traffic_direct=AUTO_ROUTING):
        """Deliver a network frame."""
        if not isinstance(frame, RF24NetworkFrame):
            raise TypeError("frame expected object of type RF24NetworkFrame.")
        if not self._validate_msg_len(len(frame.message)):
            frame.message = frame.message[:MAX_FRAG_SIZE]
        frame.header.from_node = self._addr
        if not frame.header.is_valid():
            return False
        return self._pre_write(frame, traffic_direct)

    def _pre_write(self, frame, traffic_direct=AUTO_ROUTING):
        """Helper to do prep work for _write_to_pipe(); like to TMRh20's _write()"""
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
