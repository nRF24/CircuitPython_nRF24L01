Shared Networking API
======================

Accessible RF24 API
*******************

The follow is a list of `RF24` functions and attributes that are exposed in the
`RF24Network` and `RF24Mesh` API.

* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.channel`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.flush_rx`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.flush_tx`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.fifo`
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

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.address_prefix
    :annotation: = b"\xCC"

    .. seealso::
        The usage of this attribute is more explained in the `Topology page <topology.html#physical-addresses-vs-logical-addresses>`_

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.address_suffix
    :annotation: = b"\xC3\x3C\x33\xCE\x3E\xE3"

    .. seealso::
        The usage of this attribute is more explained in the `Topology page <topology.html#physical-addresses-vs-logical-addresses>`_

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.frame_buf

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.queue

    This attribute will be an instantiated `FrameQueue` or `FrameQueueFrag` object depending on the state
    of the `fragmentation` attribute.

.. autoattribute:: circuitpython_nrf24l01.rf24_network.RF24Network.ret_sys_msg

    This `bool` attribute is asserted on mesh network nodes.
