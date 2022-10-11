
.. module:: circuitpython_nrf24l01.rf24_network

.. |if_nothing_in_queue| replace:: If there is nothing in the `queue`, this method will return
.. |use_msg_t| replace:: To ensure a message has been delivered to its target destination, set the
    frame's header's `message_type` to an `int` in range [65, 127]. This will invoke
    a `NETWORK_ACK` response message.

RF24Network API
===============

.. versionadded:: 2.1.0

.. seealso:: Documentation for:

    1. `Network Topology <topology.html>`_
    2. `Shared Networking API <shared_api.html#>`_
    3. `Network Data Structures <structs.html>`_
    4. `Network Constants <constants.html>`_

RF24NetworkRoutingOnly class
****************************

.. autoclass:: circuitpython_nrf24l01.rf24_network.RF24NetworkRoutingOnly

    This class is a minimal variant of the `RF24Network` class. The API is almost identical to
    `RF24Network` except that it has no `RF24Network.write()` or `RF24Network.send()` functions.
    This is meant to be the python equivalent to TMRh20's ``DISABLE_USER_PAYLOADS`` macro in the
    C++ RF24Network library.

    :param node_address: The octal `int` for this node's :ref:`Logical Address <Logical Address>`

    .. seealso::
        For all other parameters' descriptions, see the
        :py:class:`~circuitpython_nrf24l01.rf24.RF24` class' constructor documentation.

RF24Network class
*****************

.. autoclass:: circuitpython_nrf24l01.rf24_network.RF24Network
    :show-inheritance:

    :param node_address: The octal `int` for this node's :ref:`Logical Address <Logical Address>`

    .. seealso::
        For all other parameters' descriptions, see the
        :py:class:`~circuitpython_nrf24l01.rf24.RF24` class' constructor documentation.

Basic API
*********

.. autoproperty:: circuitpython_nrf24l01.rf24_network.RF24Network.node_address

    Setting this attribute will alter

    1. The :ref:`Physical Addresses <Physical Address>` used on the radio's data pipes
    2. The `parent` attribute
    3. The `multicast_level` attribute's default value.

    .. warning::

        1. If this attribute is set to an invalid network
           :ref:`Logical Address <Logical Address>`, then nothing is done and the invalid address
           is ignored.
        2. A `RF24Mesh` object cannot set this attribute because the
           :ref:`Logical Address <Logical Address>` is assigned by the mesh network's master node.
           Therefore, this attribute is read-only for `RF24Mesh` objects.

           .. seealso:: Please review the tip documented in `RF24Mesh.node_id` for more details.

.. automethod:: circuitpython_nrf24l01.rf24_network.RF24Network.update

    .. important::
        It is imperative that this function be called at least once during the application's main
        loop. For applications that perform long operations on each iteration of its main loop,
        it is encouraged to call this function more than once when possible.

    :Returns:
        The latest received message's `message_type`. The returned value is not gotten
        from frame's in the `queue`, but rather it is only gotten from the messages handled
        during the function's operation.

.. automethod:: circuitpython_nrf24l01.rf24_network.RF24Network.available

.. automethod:: circuitpython_nrf24l01.rf24_network.RF24Network.peek

    :Returns: A `RF24NetworkFrame` object. However, the data returned is not removed
        from the `queue`. |if_nothing_in_queue| `None`.

.. automethod:: circuitpython_nrf24l01.rf24_network.RF24Network.read

    This function differs from `peek()` because this function also removes the header & message
    from the `queue`.

    :Returns:
        A `RF24NetworkFrame` object. |if_nothing_in_queue| `None`.

.. automethod:: circuitpython_nrf24l01.rf24_network.RF24Network.send

    :param RF24NetworkHeader header: The outgoing frame's `header`. It is important to
        have the header's `to_node` attribute set to the target network node's
        :ref:`Logical Address <Logical Address>`.
    :param bytes,bytearray message: The outgoing frame's `message`.

        .. note:: Be mindful of the message's size as this cannot exceed `MAX_FRAG_SIZE`
            (24 bytes) if `fragmentation` is disabled. If `fragmentation` is enabled (it
            is by default), then the message's size must be less than `max_message_length`

    :Returns:
        A `bool` describing if the message has been transmitted. This does not necessarily
        describe if the message has been received at its target destination.

        .. tip:: |use_msg_t|

Advanced API
************

.. automethod:: circuitpython_nrf24l01.rf24_network.RF24Network.multicast

    :param message: The outgoing frame's `message`.
    :param message_type: The outgoing frame's `message_type`.
    :param level: The `network level <topology.html#network-levels>`_ of nodes to broadcast to.
        If this optional parameter is not specified, then the node's `multicast_level` is used.

    .. seealso:: `multicast_level`, `multicast_relay`, and `allow_multicast`

    :Returns:
        A `bool` describing if the message has been transmitted. This does not necessarily
        describe if the message has been received at its target destination.

        .. note::
            For multicasted messages, the radio's `auto_ack` feature is not used.

            This function will always return `True` if a message is directed to a node's pipe
            that does not have `auto_ack` enabled (which will likely be pipe 0 in most network
            contexts).
        .. tip::
            To ensure a message has been delivered to its target destination, set the
            header's `message_type` to an `int` in range [65, 127]. This will invoke a
            `NETWORK_ACK` response message.

.. automethod:: circuitpython_nrf24l01.rf24_network.RF24Network.write

    .. hint::
        This function can be used to transmit entire frames accumulated in a
        user-defined `FrameQueue` object.

        .. code-block:: python

            from circuitpython_nrf24l01.network.structs import FrameQueue, RF24NetworkFrame, RF24NetworkHeader

            my_q = FrameQueue()
            for i in range(my_q.max_queue_size):
                my_q.enqueue(
                    RF24NetworkFrame(
                        RF24NetworkHeader(0, "1"), bytes(range(i + 5))
                    )
                )

            # when it's time to send the queue
            while len(my_q):
                # let `nrf` be the instantiated RF24Network object
                nrf.write(my_q.dequeue())

    :param frame: The complete frame to send. It is important to
        have the header's `to_node` attribute set to the target network node's address.
    :param traffic_direct: The specified direction of the frame. By default, this
        will invoke the automatic routing mechanisms. However, this parameter
        can be set to a network node's :ref:`Logical Address <logical address>` for direct
        transmission to the specified node - meaning the transmission's automatic routing
        will begin at the network node that is specified with this parameter instead of being
        automatically routed from the actual origin of the transmission.

    :Returns:

        * `True` if the ``frame`` has been transmitted. This does not necessarily
          describe if the message has been received at its target destination.
        * `False` if the ``frame``  has failed to transmit.

        .. note::
            This function will always return `True` if the ``traffic_direct`` parameter is set to
            anything other than its default value. Using the ``traffic_direct`` parameter assumes
            there is a reliable/open connection to the `node_address` passed to ``traffic_direct``.
        .. tip:: |use_msg_t|

.. autoproperty:: circuitpython_nrf24l01.rf24_network.RF24Network.parent

    Returns :python:`0` if called on the network's master node.

Configuration API
*****************

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.max_message_length

    By default this is set to :python:`144`. If a network node is driven by the TMRh20
    RF24Network library on a ATTiny-based board, set this to :python:`72` (as per TMRh20's
    RF24Network library default behavior).

    Configuring the `fragmentation` attribute will automatically change the value that
    `max_message_length` attribute is set to.

.. autoproperty:: circuitpython_nrf24l01.rf24_network.RF24Network.fragmentation

    Changing this attribute's state will also appropriately changes the type of `FrameQueue`
    (or `FrameQueueFrag`) object used for storing incoming network packets. Disabling
    fragmentation can save some memory (not as much as TMRh20's RF24Network library's
    ``DISABLE_FRAGMENTATION`` macro), but `max_message_length` will be limited to :python:`24`
    bytes (`MAX_FRAG_SIZE`) maximum. Enabling this attribute will set `max_message_length`
    attribute to :python:`144` bytes.

.. autoproperty:: circuitpython_nrf24l01.rf24_network.RF24Network.multicast_relay

    Forwarded frames will also be enqueued on the forwarding node as a received frame.

.. autoproperty:: circuitpython_nrf24l01.rf24_network.RF24Network.multicast_level

    Setting this attribute will also change the :ref:`physical address <Physical Address>`
    on the radio's RX data pipe 0.

    .. seealso::
        The `network levels <topology.html#network-levels>`_ are explained in more detail on
        the `topology <topology.html>`_ document.

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.allow_multicast

    This attribute affects

    - the :ref:`Physical Address <Physical Address>` translation (for data pipe 0) when setting the
      `node_address`
    - all incoming multicasted frames (including `multicast_relay` behavior).

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.tx_timeout

    Defaults to 25.

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.route_timeout

    Defaults to 75.
