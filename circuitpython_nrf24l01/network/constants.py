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
"""All the constants related to managing a network with nRF24L01 radios."""
from micropython import const


# generic (internal) constants
MAX_USER_DEFINED_HEADER_TYPE = const(127)
"""Any message type above 127 (but cannot exceed 255) are reserved for internal
network usage."""
NETWORK_DEFAULT_ADDR = const(0o4444)  #: used as a sentinel during routing messages
#: Maximum message size for a single frame's message (does not including header)
MAX_FRAG_SIZE = const(24)
#: A reserved node address for multicasting messages
NETWORK_MULTICAST_ADDR = const(0o100)


# sending behavior types
#: Send a message with automatic network rounting
AUTO_ROUTING = const(0o70)
#: Send a routed message (used for most outgoing message types)
TX_NORMAL = const(0)
#: Send a routed message (internally used for network ACKs)
TX_ROUTED = const(1)
USER_TX_TO_PHYSICAL_ADDRESS = const(2)
"""Send a message directly to network node
these usually take 1 transmission, so they don't get a network ACK because the
radio's `auto_ack` will serve the ACK."""
USER_TX_TO_LOGICAL_ADDRESS = const(3)
"""Similar to `TX_NORMAL`, but allows the user to define the routed transmission's
first path (these still get a network ACK)."""
USER_TX_MULTICAST = const(4)
"""Manually broadcast a message to a level/group of nodes

.. seealso::
    :meth:`~circuitpython_nrf24l01.network.rf24_network.RF24Network.multicast_relay()`
"""
#: The message type used when forwarding acknowledgements directed to origin
NETWORK_ACK = const(193)
NETWORK_EXTERNAL_DATA = const(131)
"""Used for bridging different network protocols between an RF24Network
and LAN/WLAN networks (unsupported at this time as this operation requires
a gateway implementation)"""

# flags for managing queue while receiving message fragments
#: prevents reading additional data from the radio when buffers are full.
FLAG_HOLD_INCOMING = const(1)
FLAG_BYPASS_HOLDS = const(2)
"""mainly for use with RF24Mesh as follows:

#. Ensure no data in radio buffers, else exit
#. Address is changed to multicast address for renewal
#. Holds Cleared (bypass flag is set)
#. Address renewal takes place and is set
#. Holds Enabled (bypass flag off)
"""
FLAG_FAST_FRAG = const(4)  #: Disable the radio's `auto_ack` on pipe 0
FLAG_NO_POLL = const(8)  #: Used to discard any `NETWORK_POLL` message types


# constants used to define `RF24NetworkHeader.message_type`
NETWORK_PING = const(130)
"""Used for network pings. Messages of this type are automatically discarded
because the RF24.auto_ack feature will serve up the response."""
NETWORK_POLL = const(194)
"""Used by RF24Mesh.

Messages of this type are used with multi-casting , to find active/available nodes.
Any node receiving a NETWORK_POLL sent to a multicast address will respond
directly to the sender with a blank message, indicating the
address of the available node via the header.
"""
NETWORK_ADDR_REQUEST = const(195)
"""Used by RF24Mesh.

Messages of this type are used for requesting data from network base node.
Any (non-master) node receiving a message of this type will manually forward
it to the master node using a normal network write.
"""
NETWORK_ADDR_RESPONSE = const(128)
"""This message type is used to manually route custom messages containing a
single RF24Network address.

Used by RF24Mesh.

If a node receives a message of this type that is directly addressed to it, it
will read the included message, and forward the payload on to the proper
recipient. This allows nodes to forward multicast messages to the master node,
receive a response, and forward it back to the requester.
"""

# fragmented message types (used in the `header.reserved` attribute)
#: Used to indicate the first frame of fragmented messages
NETWORK_FRAG_FIRST = const(148)
#: Used to indicate a middle frame of fragmented messages
NETWORK_FRAG_MORE = const(149)
#: Used to indicate the last frame of fragmented messages
NETWORK_FRAG_LAST = const(150)


# debugging levels (to be used a binary mneumonics with RF24Network.debug attribute)
#: general debugging (specific to the RF24Network object)
NETWORK_DEBUG = const(10)
#: minimal debugging
NETWORK_DEBUG_MINIMAL = const(11)
#: shows debugging info about routing messages through the RF24Network object
NETWORK_DEBUG_ROUTING = const(12)
#: shows debugging info about fragmented messages
NETWORK_DEBUG_FRAG = const(13)
#: shows advanced debugging info about fragmented messages
NETWORK_DEBUG_FRAG_L2 = const(14)
