Network Constants
========================

.. automodule:: circuitpython_nrf24l01.network.constants

.. versionadded:: 2.1.0

Sending Behavior Types
----------------------

.. autodata:: circuitpython_nrf24l01.network.constants.AUTO_ROUTING
.. autodata:: circuitpython_nrf24l01.network.constants.TX_NORMAL

    This is used for most outgoing message types.

.. autodata:: circuitpython_nrf24l01.network.constants.TX_ROUTED

    This is internally used for `NETWORK_ACK` message routing.

.. autodata:: circuitpython_nrf24l01.network.constants.TX_PHYSICAL

    These usually take 1 transmission, so they don't get a network ACK because the
    radio's `auto_ack` will serve the ACK.

.. autodata:: circuitpython_nrf24l01.network.constants.TX_LOGICAL

    This allows the user to define the routed transmission's first path (these can still get a
    `NETWORK_ACK`).

.. autodata:: circuitpython_nrf24l01.network.constants.TX_MULTICAST

    .. seealso::

        - `Network Levels <topology.html#network-levels>`_
        - `multicast_relay`
        - `multicast()`
        - `multicast_level`


Reserved Network Message Types
------------------------------

.. autodata:: circuitpython_nrf24l01.network.constants.MESH_ADDR_RESPONSE

    This `message_type` is used to in the final step of `renew_address()` route a messages
    containing a newly allocated `node_address`. The header's `reserved` attribute for this
    `message_type` will store the requesting mesh node's `node_id` related to the newly assigned
    `node_address`. Any non-requesting network node receiving this `message_type` will forward it
    to the requesting node using normal network routing.

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_PING

    This `message_type` is automatically discarded because the radio's `auto_ack` feature will serve
    up the response.

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_EXT_DATA

    Used for bridging different network protocols between an RF24Network and LAN/WLAN networks.

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_ACK

    The message type used when forwarding acknowledgements directed to the
    instigating message's origin. This is not be confused with the radio's `auto_ack`
    attribute. In fact, all messages (except multicasted ones) take advantage of the
    radio's `auto_ack` feature when transmitting between directly related nodes (ie
    between a transmitting node's parent or child node).

    .. important::
        NETWORK_ACK messages are only sent by the last node in the route to a
        destination. For example: Node :python:`0o0` sends an instigating message to node
        :python:`0o11`. The NETWORK_ACK message is sent from node :python:`0o1` when it
        confirms node :python:`0o11` received the instigating message.
    .. hint::
        This feature is not flawless because it assumes a reliable connection
        between all necessary network nodes.

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_POLL

    This `message_type` is used with `NETWORK_MULTICAST_ADDR`
    to find active/available nodes. Any node receiving a `NETWORK_POLL` sent to a
    `NETWORK_MULTICAST_ADDR` will respond directly to the sender with a blank message,
    indicating the address of the available node via the header's `from_node` attribute.

.. autodata:: circuitpython_nrf24l01.network.constants.MESH_ADDR_REQUEST

    This `message_type` is used for requesting :ref:`Logical Address <Logical Address>` data from
    the mesh network's master node. Any non-master node receiving this `message_type` will manually
    forward it to the master node using normal network routing.

.. autodata:: circuitpython_nrf24l01.network.constants.MESH_ADDR_LOOKUP
.. autodata:: circuitpython_nrf24l01.network.constants.MESH_ADDR_RELEASE
.. autodata:: circuitpython_nrf24l01.network.constants.MESH_ID_LOOKUP

Generic Network constants
----------------------------

.. autodata:: circuitpython_nrf24l01.network.constants.MAX_USR_DEF_MSG_TYPE

    Any message type above 127 (but cannot exceed 255) are reserved for internal
    network usage.

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_DEFAULT_ADDR

    Any mesh node that disconnects or is trying to connect to a mesh network will use this value
    until it is assigned a :ref:`Logical Address <Logical Address>` from the master node.

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_MULTICAST_ADDR
.. autodata:: circuitpython_nrf24l01.network.constants.MAX_FRAG_SIZE

    This does not including header's byte length (which is always 8 bytes).

    .. warning::
        Do not increase this value in the source code. Adjust
        :attr:`~circuitpython_nrf24l01.rf24_network.RF24Network.max_message_length`
        instead.

Message Fragment Types
----------------------

Message fragments will use these values in the
:attr:`~circuitpython_nrf24l01.network.structs.RF24NetworkHeader.message_type` attribute.
The sequential fragment id number will be stored in the
:attr:`~circuitpython_nrf24l01.network.structs.RF24NetworkHeader.reserved` attribute,
but the actual message type is transmitted in the
:attr:`~circuitpython_nrf24l01.network.structs.RF24NetworkHeader.reserved` attribute
of the last fragment.

.. autodata:: circuitpython_nrf24l01.network.constants.MSG_FRAG_FIRST
.. autodata:: circuitpython_nrf24l01.network.constants.MSG_FRAG_MORE
.. autodata:: circuitpython_nrf24l01.network.constants.MSG_FRAG_LAST

RF24Mesh specific constants
---------------------------

.. autodata:: circuitpython_nrf24l01.network.constants.MESH_LOOKUP_TIMEOUT

    The time (in milliseconds) that a non-master mesh node will wait for a response when
    requesting a node's relative :ref:`Logical Address <Logical Address>` or unique ID number
    from the master node.

.. autodata:: circuitpython_nrf24l01.network.constants.MESH_MAX_POLL

    A mesh node polls the first 4 network levels (0-3) looking for a response.
    This value is used to used when aggregating a list of responding nodes (per level).

.. autodata:: circuitpython_nrf24l01.network.constants.MESH_MAX_CHILDREN

    This information is only used by mesh network master nodes when allocating a possible
    :ref:`Logical Address <Logical Address>` for the requesting node.

.. autodata:: circuitpython_nrf24l01.network.constants.MESH_WRITE_TIMEOUT

    When `RF24Mesh.send()` is called, This value is only used when getting the `node_address`
    assigned to a `node_id` from the mesh network's master node.
