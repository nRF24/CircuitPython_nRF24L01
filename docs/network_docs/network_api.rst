.. |traffic_direect| replace:: The specified direction of the frame. By default, this
        will invoke the automatic routing mechanisms. However, this parameter
        can be set to a network node's :ref:`Logical Address <logical address>` for direct transmission to the
        specified node - meaning the transmission's automatic routing will begin at the
        network node that is specified with this parameter instead of being automatically
        routed from the transmission actual origin.
.. |if_nothing_in_queue| replace:: If there is nothing in the `queue`, this method will return


RF24Network API
===============

.. versionadded:: 2.1.0

.. seealso:: Documentation for:

    1. `Shared Networking API <base_api.html#>`_
    2. `Network Data Structures <structs.html>`_
    3. `Network Constants <constants.html>`_

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

    .. important::
        It is imperitive that this function be called at least once during the application main
        loop. For applications that perform long operations on each iteration of its main loop,
        it is encouraged to call this function more than once when possible.

    :Returns:
        The latest received message's `message_type`. The returned value is not gotten
        from frame's in the `queue`, but rather it is only gotten from the messages handled
        during the function's operation.

available()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.available

peek()
------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.peek

    :Returns: A `RF24NetworkFrame` object. However, the data returned is not removed
        from the `queue`. |if_nothing_in_queue| `None`.

peek_header()
-------------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.peek_header

    :Returns: A `RF24NetworkHeader` object. However, the data returned is not removed
        from the `queue`. |if_nothing_in_queue| `None`.

peek_message_length()
---------------------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.peek_message_length

    :Returns: An `int` describing the length of the next available message's length
        from the `queue`. |if_nothing_in_queue| ``0``.

read()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.read

    This function differs from `peek()`, `peek_header()`, and `peek_message_length()` because
    this function also removes the header & message from the `queue`.

    :Returns:
        A `RF24NetworkFrame` object. |if_nothing_in_queue| `None`.

send()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.send

    :param RF24NetworkHeader header: The outgoing frame's `header`. It is important to
        have the header's `to_node` attribute set to the target network node's
        :ref:`Logical Address <Logical Address>`.
    :param bytes,bytearray message: The outgoing frame's `message`.

        .. note:: Be mindful of the message's size as this cannot exceed `MAX_FRAG_SIZE`
            (24 bytes) if `fragmentation` is disabled. If `fragmentation` is enabled (it
            is by default), then the message's size must be less than `max_message_length`
    :param int traffic_direct: |traffic_direect|

    :Returns:
        A `bool` describing if the message has been transmitted. This does not necessarily
        describe if the message has been received at its target destination.

        .. note::
            This function will always return `True` if a message is directed to a node's pipe
            that does not have `auto_ack` enabled (which will likely be pipe 0 in most network
            contexts).
        .. tip:: To ensure a message has been delivered to its target destination, set the
            header's `message_type` to an `int` in range [65, 127].

Advanced API
************

node_address
------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.node_address

    Setting this attribute will alter the :ref:`physical addresses <Physical Address>`
    used on the radio's data pipes and the default `multicast_level` value.

    .. warning::
        If this attribute is set to an invald network
        :ref:`Logical Address <Logical Address>`, then nothing is done and the invalid address is ignored.

multicast()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.multicast

    :param RF24NetworkHeader header: The outgoing frame's `header`.
    :param bytes,bytearray message: The outgoing frame's `message`.
    :param int level: The `network level <topology.html#network-levels>`_ of nodes to broadcast to.
        If this optional parameter is not specified, then the node's `multicast_level` is used.

    .. seealso:: `multicast_level`, `multicast_relay`, and `allow_multicast`

    :Returns:
        A `bool` describing if the message has been transmitted. This does not necessarily
        describe if the message has been received at its target destination.

        .. note::
            This function will always return `True` if a message is directed to a node's pipe
            that does not have `auto_ack` enabled (which will likely be pipe 0 in most network
            contexts).
        .. tip:: To ensure a message has been delivered to its target destination, set the
            header's `message_type` to an `int` in range [65, 127].

write()
-----------

.. automethod:: circuitpython_nrf24l01.network.rf24_network.RF24Network.write

    :param RF24NetworkFrame frame: The complete frame to send. It is important to
        have the header's `to_node` attribute set to the target network node's address.
        If a `FrameQueue` object is passed, then all frames in the passed `FrameQueue`
        will be processed in a FIFO (First In First Out) basis.
    :param int traffic_direct: |traffic_direect|
    :param int send_type: The behavior to use when sending a frame. This parameter is
        overridden if the ``traffic_direct`` and ``send_type`` parameters are set to
        anything other than their default values. This parameter should be considered
        reserved for special applicable use cases (like `RF24Mesh`).

    :Returns:

        * `True` if the ``frame`` has been transmitted. This does not necessarily
          describe if the message has been received at its target destination.
        * `False` if the ``frame``  has not been transmitted.
        * If a `FrameQueue` object is passed to the ``frame`` parameter, then a
          `list` of `bool` values that descrbes the result of transmitting the frames in the
          `FrameQueue` object that was passed.

        .. note::
            This function will always return `True` if a message is directed to a node's pipe
            that does not have `auto_ack` enabled (which will likely be pipe 0 in most network
            contexts).
        .. tip:: To ensure a message has been delivered to its target destination, set the
            frame's header's `message_type` to an `int` in range [65, 127].

parent
-----------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.parent

    Returns `None` if on the network's master node.

Configuration API
*****************

max_message_length
------------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.max_message_length

    By default this is set to ``144``. If a network node is driven by the TMRh20
    RF24Network library on a ATTiny-based board, set this to ``72`` (as per TMRh20's
    RF24Network library default behavior).

multicast_relay
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.multicast_relay

    Duplicate frames are filtered out, so multiple forwarding nodes at the
    same level should not interfere. Forwarded payloads will also be
    received.

multicast_level
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.multicast_level

    Setting this attribute will also change the :ref:`physical address <Physical Address>`
    on the radio's RX data pipe 0.

    .. seealso::
        The `network levels <topology.html#network-levels>`_ are explained in more detail on
        the `topology <topology.html>`_ document.

tx_timeout
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.tx_timeout


fragmentation
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.fragmentation

    Changing this attribute's state will also appropriately changes the type of `FrameQueue`
    (or `FrameQueueFrag`) object used for storing incoming network packets. Disabling
    fragmentation can save some memory (not as much as TMRh20's RF24Network library's
    ``DISABLE_FRAGMENTATION`` macro), but messages will be limited to 24 bytes
    (`MAX_FRAG_SIZE`) maximum.

allow_multicast
---------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.allow_multicast

    This attribute affects the :ref:`Physical Address <Physical Address>` translation done by setting the `node_address`,
    all incoming multicasted frames, and `multicast_relay` behavior.
