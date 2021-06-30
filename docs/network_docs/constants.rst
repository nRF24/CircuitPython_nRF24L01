Network Constants
========================

Sending Behavior Types
----------------------

.. autodata:: circuitpython_nrf24l01.network.constants.AUTO_ROUTING
.. autodata:: circuitpython_nrf24l01.network.constants.TX_NORMAL
.. autodata:: circuitpython_nrf24l01.network.constants.TX_ROUTED
.. autodata:: circuitpython_nrf24l01.network.constants.USER_TX_TO_PHYSICAL_ADDRESS
.. autodata:: circuitpython_nrf24l01.network.constants.USER_TX_TO_LOGICAL_ADDRESS
.. autodata:: circuitpython_nrf24l01.network.constants.USER_TX_MULTICAST

Reserved Network Message Types
------------------------------

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_ACK
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_EXTERNAL_DATA

Generic Network constants
----------------------------

.. autodata:: circuitpython_nrf24l01.network.constants.MAX_USER_DEFINED_HEADER_TYPE
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_DEFAULT_ADDR
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_MULTICAST_ADDR
.. autodata:: circuitpython_nrf24l01.network.constants.MAX_FRAG_SIZE

Message Fragment Types
----------------------

Message fragments will use these values in the
:attr:`~circuitpython_nrf24l01.network.packet_structs.RF24NetworkHeader.message_type`.
The sequential fragment id number will be stored in the
:attr:`~circuitpython_nrf24l01.network.packet_structs.RF24NetworkHeader.reserved` attribute,
but the actual message type is transmitted in the
:attr:`~circuitpython_nrf24l01.network.packet_structs.RF24NetworkHeader.reserved` attribute
of the last fragment.

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_FRAG_FIRST
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_FRAG_MORE
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_FRAG_LAST

Debugging Levels
----------------

.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_DEBUG
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_DEBUG_MINIMAL
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_DEBUG_ROUTING
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_DEBUG_FRAG
.. autodata:: circuitpython_nrf24l01.network.constants.NETWORK_DEBUG_FRAG_L2
