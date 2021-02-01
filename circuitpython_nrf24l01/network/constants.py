"""All the constants related to managing a network with nRF24L01 radios."""
from micropython import const


# contraints on user-defined header types
MIN_USER_DEFINED_HEADER_TYPE = const(0)
MAX_USER_DEFINED_HEADER_TYPE = const(127)

# other constants
NETWORK_DEFAULT_ADDR = const(0o4444)
FLAG_NO_POLL = const(8)
USER_TX_TO_PHYSICAL_ADDRESS = const(2)


# constants used to define `RF24NetworkHeader.message_type`
NETWORK_PING = const(130)  #: Used for network pings
NETWORK_POLL = const(194)
"""Used by RF24Mesh.

Messages of this type are used with multi-casting , to find active/available nodes.
Any node receiving a NETWORK_POLL sent to a multicast address will respond
directly to the sender with a blank message, indicating the
address of the available node via the header.
"""

NETWORK_ADDR_REQUEST = const(195)
#: Used for requesting data from network base node
NETWORK_ADDR_RESPONSE = const(128)
#: Used for routing messages/responses throughout the network

NETWORK_FRAG_FIRST = const(148)
#: Used to indicate the first frame of fragmented payloads
NETWORK_FRAG_MORE = const(149)
#: Used to indicate a middle frame of fragmented payloads
NETWORK_FRAG_LAST = const(150)
#: Used to indicate the last frame of fragmented payloads
NETWORK_ACK = const(193)
#: Used to forward acknowledgements directed to origin

NETWORK_EXTERNAL_DATA = const(131)
"""Used for bridging different network protocols between an RF24Network
and LAN/WLAN networks (unsupported at this time as this operation requires
a gateway implementation)"""
