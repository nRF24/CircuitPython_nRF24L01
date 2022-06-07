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
MAX_USR_DEF_MSG_TYPE = const(127)  #: A convenient sentinel value.
NETWORK_DEFAULT_ADDR = const(0o4444)  #: Primarily used by RF24Mesh.
MAX_FRAG_SIZE = const(24)  #: Maximum message size for a single frame's message.
NETWORK_MULTICAST_ADDR = const(0o100)  #: A reserved address for multicast messages.
MESH_LOOKUP_TIMEOUT = const(135)  #: Used for `lookup_address()` & `lookup_node_id()`
MESH_MAX_POLL = const(4)  #: The max number of contacts made during `renew_address()`.
MESH_MAX_CHILDREN = const(4)  #: The max number of children for 1 mesh node.
MESH_WRITE_TIMEOUT = const(115)  #: The time (in milliseconds) used to send messages.

# sending behavior types
AUTO_ROUTING = const(0o70)  #: Send a message with automatic network routing.
TX_NORMAL = const(0)  #: Send a routed message.
TX_ROUTED = const(1)  #: Send a routed message.
TX_PHYSICAL = const(2)  #: Send a message directly to network node.
TX_LOGICAL = const(3)  #: Similar to `TX_NORMAL`.
TX_MULTICAST = const(4)  #: Broadcast a message to a network level of nodes.

# constants used to define `RF24NetworkHeader.message_type`
NETWORK_ACK = const(193)  #: Used for network-wide acknowledgements.
NETWORK_PING = const(130)  #: Used for network pings
NETWORK_POLL = const(194)  #: Primarily for RF24Mesh
MESH_ADDR_REQUEST = const(195)  #: Primarily for RF24Mesh
MESH_ADDR_RESPONSE = const(128)  #: Primarily for RF24Mesh

#: Unsupported at this time as this operation requires a new implementation.
NETWORK_EXT_DATA = const(131)

# No Network ACK message types
#: The `message_type` when manually expiring a leased address.
MESH_ADDR_RELEASE = const(197)
#: The `message_type` to request a mesh node's network address from its unique ID.
MESH_ADDR_LOOKUP = const(196)
#: The `message_type` to request a mesh node's unique ID number from its node address.
MESH_ID_LOOKUP = const(198)


# fragmented message types (used in the `header.reserved` attribute)
#: Used to indicate the first frame of a fragmented message.
MSG_FRAG_FIRST = const(148)
#: Used to indicate a middle frame of a fragmented message.
MSG_FRAG_MORE = const(149)
#: Used to indicate the last frame of a fragmented message.
MSG_FRAG_LAST = const(150)
