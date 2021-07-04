RF24Network API
===============

.. versionadded:: 2.1.0

RF24Network class
*****************

.. autoclass:: circuitpython_nrf24l01.network.rf24_network.RF24Network

    :param int node_address: The octal `int` for this node's address

    .. seealso:: For all other parameters' descriptions, see the
        :py:class:`~circuitpython_nrf24l01.rf24.RF24` class' contructor documentation.

Basic API
*********

update()
--------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.update

available()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.available

peek
------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.peek

peek_header
-----------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.peek_header

read()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.read

send()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.send


Advanced API
************

node_address
------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.node_address

multicast()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.multicast

write()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.write

parent
-----------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.parent

Configuration API
*****************

multicast_relay
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.multicast_relay

multicast_level
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.multicast_level


tx_timeout
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.tx_timeout


fragmentation
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.fragmentation


allow_multicast
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.allow_multicast
