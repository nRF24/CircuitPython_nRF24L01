
.. module:: circuitpython_nrf24l01.rf24_mesh

.. |use_msg_t| replace:: To ensure a message has been delivered to its target destination, set the
    ``message_type`` parameter to an `int` in range [65, 127]. This will invoke
    a `NETWORK_ACK` response message.

RF24Mesh API
============

.. versionadded:: 2.1.0

.. seealso:: Documentation for:

    1. `Shared Networking API <shared_api.html#>`_ (API common to `RF24Mesh` and `RF24Network`)
    2. `RF24Network API <network_api.html>`_ (`RF24Mesh` inherits from the same mixin class
       that `RF24Network` inherits from)

RF24MeshNoMaster class
**********************

.. autoclass:: circuitpython_nrf24l01.rf24_mesh.RF24MeshNoMaster

    This class exists to save memory for nodes that don't behave like mesh network master nodes.
    It is the python equivalent to TMRh20's ``MESH_NO_MASTER`` macro in the C++ RF24Mesh library.
    All the API is the same as `RF24Mesh` class.

    :param node_id: The unique identifying :attr:`~circuitpython_nrf24l01.rf24_mesh.RF24Mesh.node_id`
        number for the instantiated mesh node.

    .. seealso:: For all parameters' descriptions, see the
        :py:class:`~circuitpython_nrf24l01.rf24.RF24` class' constructor documentation.


RF24Mesh class
**************

.. autoclass:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh
    :show-inheritance:

    :param node_id: The unique identifying `node_id` number for the instantiated mesh node.

    .. seealso:: For all parameters' descriptions, see the
        :py:class:`~circuitpython_nrf24l01.rf24.RF24` class' constructor documentation.

Basic API
*********


.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.send

    This function will use `lookup_address()` to fetch the necessary
    :ref:`Logical Address <Logical Address>` to set the frame's header's `to_node`
    attribute.

    .. hint::
        If you already know the destination node's :ref:`Logical Address <Logical Address>`,
        then you can use :meth:`~circuitpython_nrf24l01.rf24_mesh.RF24Mesh.write()`
        for quicker operation.

    :param to_node: The unique mesh network `node_id` of the frame's destination.
        Defaults to :python:`0` (which is reserved for the master node).
    :param message_type: The `int` that describes the frame header's `message_type`.
    :param message: The frame's `message` to be transmitted.

        .. note::
            Be mindful of the message's size as this cannot exceed `MAX_FRAG_SIZE` (24 bytes) if
            `fragmentation` is disabled. If `fragmentation` is enabled (it is by default), then
            the message's size must be less than
            :attr:`~circuitpython_nrf24l01.rf24_network.RF24Network.max_message_length`.

    :Returns:

        * `True` if the ``frame`` has been transmitted. This does not necessarily
          describe if the message has been received at its target destination.
        * `False` if the ``frame``  has not been transmitted.

        .. tip:: |use_msg_t|


.. autoproperty:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.node_id

    This is not to be confused with the network node's `node_address`. This attribute is meant to
    distinguish different mesh network nodes that may, at separate instances, use the same
    `node_address`. It is up to the developer to make sure each mesh network node uses a different
    ID number.

    .. warning::
        Changing this attributes value after instantiation will automatically call
        `release_address()` which disconnects the node from the mesh network. Notice the
        `node_address` is set to `NETWORK_DEFAULT_ADDR`  when consciously not connected to the
        mesh network.
    .. tip::
        When a mesh node becomes disconnected from the mesh network, use `renew_address()`
        to fetch (from the master node) an assigned logical address to be used as the mesh node's
        `node_address`.

.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.renew_address

    :param timeout: The amount of time (in seconds) to continue trying to connect
        and get an assigned :ref:`Logical Address <Logical Address>`. Defaults to 7.5 seconds.

    .. note:: This function automatically sets the `node_address` accordingly.

    :Returns:
        * If successful: The `node_address` that was set to the newly assigned
          :ref:`Logical Address <Logical Address>`.
        * If unsuccessful: `None`, and the `node_address` attribute will be set to
          `NETWORK_DEFAULT_ADDR` (:python:`0o4444` in octal or :python:`2340` in decimal).


Advanced API
************

.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.lookup_node_id

    :param address: The :ref:`Logical Address <Logical Address>` for which
        a unique `node_id` is assigned from network master node.

    :Returns:
        - The unique `node_id` assigned to the specified ``address``.
        - Error codes include

          - :python:`-2` means the specified ``address`` has not been assigned a
            unique `node_id` from the master node or the requesting
            network node's `node_address` is equal to `NETWORK_DEFAULT_ADDR`.
          - :python:`-1` means the address lookup operation failed due to no network connection
            or the master node has not assigned a unique `node_id`
            for the specified ``address``.

.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.lookup_address

    :param node_id: The unique `node_id` for which a
        :ref:`Logical Address <Logical Address>` is assigned from network master node.

    :Returns:
        - The :ref:`Logical Address <Logical Address>` assigned to the specified ``node_id``.
        - Error codes include

          - :python:`-2` means the specified ``node_id`` has not been assigned a
            :ref:`Logical Address <Logical Address>` from the master node or the requesting
            network node's `node_address` is equal to `NETWORK_DEFAULT_ADDR`.
          - :python:`-1` means the address lookup operation failed due to no network connection
            or the master node has not assigned a :ref:`Logical Address <Logical Address>`
            for the specified ``node_id``.


.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.write

    :param to_node: The network node's :ref:`Logical Address <Logical Address>`.
        of the frame's destination. This must be the destination's network `node_address` which is
        not be confused with a mesh node's `node_id`.
    :param message_type: The `int` that describes the frame header's `message_type`.

        .. note:: Be mindful of the message's size as this cannot exceed
            `MAX_FRAG_SIZE` (24 bytes) if `fragmentation` is disabled. If `fragmentation` is
            enabled (it is by default), then the message's size must be less than
            :attr:`~circuitpython_nrf24l01.rf24_network.RF24Network.max_message_length`.
    :param message: The frame's `message` to be transmitted.

    :Returns:

        * `True` if the ``frame`` has been transmitted. This does not necessarily
          describe if the message has been received at its target destination.
        * `False` if the ``frame``  has not been transmitted.

        .. tip:: |use_msg_t|

.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.check_connection

.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.release_address

    .. hint::
        This should be called from a mesh network node that is disconnecting from the network.
        This is also recommended for mesh network nodes that are entering a powered down (or
        sleep) mode.

.. autoproperty:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.allow_children

.. autoattribute:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.block_less_callback

    .. note::
        Requesting a new address (via `renew_address()`) can take a while since it sequentially
        attempts to get re-assigned to the first available :ref:`Logical Address <Logical Address>`
        on the highest possible `network level <topology.html#network-levels>`_.

    The assigned function will be called during `renew_address()`, `lookup_address()` and
    `lookup_node_id()`.

    The callback function assigned should take no positional parameters and it's returned data (if
    any) is ignored. For example:

    .. code-block:: python
        :caption: In user/app code space

        arbitrary_global_counter = [0]

        def callback_func(kw_arg: int = 1):
            arbitrary_global_counter[0] += kw_arg

        # let `mesh_node` be the instantiated RF24Mesh object
        mesh_node.block_less_callback = callback_func

.. autoattribute:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.dhcp_dict

    This `dict` stores the assigned :ref:`Logical Addresses <Logical Address>` to the connected
    mesh node's `node_id`.

    - The keys in this `dict` are the unique `node_id` of a mesh network node.
    - The values in this `dict` (corresponding to each key) are the `node_address` assigned to the `node_id`.

.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.save_dhcp

    .. warning::
        This function will likely throw a `OSError` on boards running CircuitPython firmware
        because the file system is by default read-only.

    Calling this function on a Linux device (like the Raspberry Pi) will save the
    `dhcp_dict` to a JSON file located in the program's working directory.

    :param filename: The name of the json file to be used. This value should include a file extension
        (like ".json" or ".txt").
    :param as_bin: Set this parameter to `True` to save the DHCP list to a binary text file.
        Defaults to `False` which saves the DHCP list as JSON syntax.

    .. versionchanged:: 2.1.1
        Added ``as_bin`` parameter to make use of binary text files.

.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.load_dhcp

    :param filename: The name of the json file to be used. This value should include a file extension
        (like ".json" or ".txt").
    :param as_bin: Set this parameter to `True` to load the DHCP list from a binary text file.
        Defaults to `False` which loads the DHCP list from JSON syntax.

    .. warning::
        This function will raise an `OSError` exception if no file exists.
    .. versionchanged:: 2.1.1
        Added ``as_bin`` parameter to make use of binary text files.

.. automethod:: circuitpython_nrf24l01.rf24_mesh.RF24Mesh.set_address

    This function is only meant to be called on the mesh network's master node.
    Use this function to manually assign a `node_id` to a `RF24Network.node_address`.

    :param node_id: A unique identifying number ranging [1, 255].
    :param node_address: A :ref:`Logical Address <Logical Address>`
    :param search_by_address: A flag to traverse the `dhcp_dict` by value instead of by key.
