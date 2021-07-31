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

.. autoclass:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader
    :members:

Frame
-----------------

.. autoclass:: circuitpython_nrf24l01.network.structs.RF24NetworkFrame
    :members:

FrameQueue
-----------------

.. autoclass:: circuitpython_nrf24l01.network.structs.FrameQueue
    :members:

FrameQueueFrag
-----------------

.. autoclass:: circuitpython_nrf24l01.network.structs.FrameQueueFrag
    :show-inheritance:

Logical Address Validation
--------------------------

.. automethod:: circuitpython_nrf24l01.network.structs.is_address_valid

    :param int address: The :ref:`Logical Address <Logical Address>` to validate.

    :Returns:
        `True` if the given address can be used as a `node_address` or `to_node`
        destination. Otherwise, this function returns `False`.

        .. warning::
            Please note that this function also allows the value ``0o100`` to validate
            because it is used as the `NETWORK_MULTICAST_ADDR` for multicasted messages.
            Technically, ``0o100`` is an invalid address.
