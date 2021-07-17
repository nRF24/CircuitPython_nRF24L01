.. |internal_use| replace:: is meant for library internal usage.
.. |uint16_t| replace:: This value is truncated to a 2-byte unsigned `int`.
.. |can_be_blank| replace:: These parameters can be left unspecified to create a blank
    object that can be augmented after instantiation.

Network Data Structures
=======================

.. versionadded:: 2.1.0

These classes are used to structure the payload data for wireless network transactions.

Header
-----------------

.. autoclass:: circuitpython_nrf24l01.network.packet_structs.RF24NetworkHeader
    :members:

Frame
-----------------

.. autoclass:: circuitpython_nrf24l01.network.packet_structs.RF24NetworkFrame
    :members:

Queue
-----------------

.. autoclass:: circuitpython_nrf24l01.network.queue.Queue
    :members:

QueueFrag
-----------------

.. autoclass:: circuitpython_nrf24l01.network.queue.QueueFrag
    :show-inheritance:
