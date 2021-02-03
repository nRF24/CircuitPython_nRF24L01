"""All the constants related to managing a network with nRF24L01 radios."""
from micropython import const


# contraints on user-defined header types
MIN_USER_DEFINED_HEADER_TYPE = const(0)
MAX_USER_DEFINED_HEADER_TYPE = const(127)


# internal constants
NETWORK_DEFAULT_ADDR = const(0o4444)
TX_NORMAL = const(0)
TX_ROUTED = const(1)
USER_TX_TO_PHYSICAL_ADDRESS = const(2)  #: no network ACK
USER_TX_TO_LOGICAL_ADDRESS = const(3)  #: network ACK
USER_TX_MULTICAST = const(4)
MAX_FRAME_SIZE = const(32)  # for a single frame (containing header + message)


# additional internal constants about handling payloads
FLAG_HOLD_INCOMING = const(1)
#: prevents reading additional data from the radio when buffers are full.

FLAG_BYPASS_HOLDS = const(2)
"""mainly for use with RF24Mesh as follows:

#. Ensure no data in radio buffers, else exit
#. Address is changed to multicast address for renewal
#. Holds Cleared (bypass flag is set)
#. Address renewal takes place and is set
#. Holds Enabled (bypass flag off)
"""

FLAG_FAST_FRAG = const(4)
FLAG_NO_POLL = const(8)

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
it to the master node using a normal network write."""

NETWORK_ADDR_RESPONSE = const(128)
"""This message type is used to manually route custom messages containing a
single RF24Network address.

Used by RF24Mesh.

If a node receives a message of this type that is directly addressed to it, it
will read the included message, and forward the payload on to the proper
recipient. This allows nodes to forward multicast messages to the master node,
receive a response, and forward it back to the requester.
"""

NETWORK_FRAG_FIRST = const(148)
#: Used to indicate the first frame of fragmented messages
NETWORK_FRAG_MORE = const(149)
#: Used to indicate a middle frame of fragmented messages
NETWORK_FRAG_LAST = const(150)
#: Used to indicate the last frame of fragmented messages
NETWORK_ACK = const(193)
#: Used to forward acknowledgements directed to origin

NETWORK_EXTERNAL_DATA = const(131)
"""Used for bridging different network protocols between an RF24Network
and LAN/WLAN networks (unsupported at this time as this operation requires
a gateway implementation)"""

# debugging levels (to be used a binary mneumonics with RF24Network.debug attribute)
NETWORK_DEBUG_MINIMAL = const(1)
#: minimal debugging
NETWORK_DEBUG = const(2)
#: general debugging (spicific to the RF24Network object)
NETWORK_DEBUG_ROUTING = const(3)
#: shows debugging info about routing messages through the RF24Network object
NETWORK_DEBUG_FRAG = const(4)
#: shows debugging info about fragmented messages
NETWORK_DEBUG_FRAG_L2 = const(5)
#: shows advanced debugging info about fragmented messages
