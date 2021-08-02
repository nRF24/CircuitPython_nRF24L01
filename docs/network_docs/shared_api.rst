Shared Networking API
======================

Accessible RF24 API
*******************

The follow is a list of `RF24` functions and attributes that are exposed in the
`RF24Network` and `RF24Mesh` API.

* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.channel`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.flush_rx`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.flush_tx`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.power`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.set_dynamic_payloads`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.get_dynamic_payloads`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.listen`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.pa_level`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.is_lna_enabled`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.data_rate`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.crc`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.set_auto_retries`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.get_auto_retries`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.last_tx_arc`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.address`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.interrupt_config`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.print_pipes`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.print_details`

  For the ``print_details()`` function, an additional keyword parameter named ``network_only``
  can be used to filter out all the core details from the `RF24` object. The ``dump_pipes``
  parameter still exists and defaults to `False`. Usage is as follows:

  .. code-block:: python

      >>> # following command is the same as `nrf.print_details(0, 1)`
      >>> nrf.print_details(dump_pipes=False, network_only=True)
      Network frame_buf contents:
          Header is from 0o7777 to 0o0 type 0 id 2 reserved 0. Message contains:
              an empty buffer
      Network flags______________0b0000
      Return on system messages__False
      Allow network multicasts___True
      Multicast relay____________Disabled
      Network fragmentation______Enabled
      Network max message length_144 bytes
      Network TX timeout_________25 milliseconds
      Network Rounting timeout___75 milliseconds
      Network node address_______0o0

  .. note::
      The address ``0o7777`` (seen in output above) is used as a sentinel when frame is
      uninitalized.

External Systems API
********************

The following attributes are exposed in the `RF24Network` and `RF24Mesh` API for
extensibility via external applications or systems.

address_prefix
--------------

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.address_prefix
    :annotation: = 0xCC

    .. seealso::
        The usage of this attribute is more explained in the `Topology page <topology.html#physical-addresses-vs-logical-addresses>`_

address_suffix
--------------

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.address_suffix
    :annotation: = [0xC3, 0x3C, 0x33, 0xCE, 0x3E, 0xE3]

    .. seealso::
        The usage of this attribute is more explained in the `Topology page <topology.html#physical-addresses-vs-logical-addresses>`_

frame_buf
-----------

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.frame_buf

queue
-----

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.queue

    This attribute will be an instantiated `FrameQueue` or `FrameQueueFrag` object depending on the state
    of the `fragmentation` attribute.

ret_sys_msg
-----------

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.ret_sys_msg

    This `bool` attribute is asserted on mesh network nodes.

network_flags
-------------

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.network_flags

A 4-bit variable in which each bit corresponds to a specific behavioral modification.

.. csv-table::
    :header: "bit position", "flag name", "behavior"
    :widths: 2, 4, 10

    0, ``FLAG_HOLD_INCOMING``, "Prevents reading additional data from the radio when buffers are full."
    1, ``FLAG_BYPASS_HOLDS``, "
    - Ensure no data in radio buffers, else exit
    - Address is changed to multicast address for renewal
    - Holds Cleared (bypass flag is set)
    - Address renewal takes place and is set
    - Holds Enabled (bypass flag off)
    "
    2, ``FLAG_FAST_FRAG``, "Unused due to optmization. TMRh20's C++ RF24Network library uses this flag internally to minimize memory usage."
    3, ``FLAG_NO_POLL``, "Used to discard any `NETWORK_POLL` message types"

..
    original docs from RF24Network src comments
    main usagee is as follows:
    #. Ensure no data in radio buffers, else exit
    #. Address is changed to multicast address for renewal
    #. Holds Cleared (bypass flag is set)
    #. Address renewal takes place and is set
    #. Holds Enabled (bypass flag off)