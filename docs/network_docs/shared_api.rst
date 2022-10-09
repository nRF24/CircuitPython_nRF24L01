
.. module:: circuitpython_nrf24l01.network.mixins

Shared Networking API
======================

Order of Inheritance
********************

.. graphviz::
    :align: center

    digraph inheritance {
        bgcolor="#323232A1"
        fontcolor="#FEF9A9"
        fontsize=16
        fontname="Roboto"
        style="rounded,bold"
        color="#FFFFFF00"
        newrank=true
        node [
            style="filled"
            fillcolor="#0E6902"
            color="#FEFEFE"
            fontcolor="#FEFEFE"
            fontsize=16
        ]
        edge [
            color="white"
            penwidth=1.5
        ]

        subgraph cluster_rf24 {
            graph [xref=":mod:`circuitpython_nrf24l01.rf24`"]
            RF24 [xref=":class:`~circuitpython_nrf24l01.rf24.RF24`"]
        }

        subgraph cluster_network_mixins{
            graph [xref=":mod:`circuitpython_nrf24l01.network.mixins`"]
            rank="same"
            RadioMixin [tooltip="RadioMixin (Python class)"]
            NetworkMixin [tooltip="NetworkMixin (Python class)"]
            RadioMixin -> NetworkMixin
        }

        subgraph cluster_rf24_network {
            graph [
                labelloc="b"
                //label="  circuitpython_nrf24l01.rf24_network  "
                xref=":mod:`circuitpython_nrf24l01.rf24_network`"
            ]
            RF24NetworkRoutingOnly [
                xref=":class:`~circuitpython_nrf24l01.rf24_network.RF24NetworkRoutingOnly`"
            ]
            RF24Network [
                xref=":class:`~circuitpython_nrf24l01.rf24_network.RF24Network`"
            ]
            RF24NetworkRoutingOnly -> RF24Network
        }

        subgraph cluster_rf24_mesh {
            labelloc="b"
            graph [
                xref=":mod:`circuitpython_nrf24l01.rf24_mesh`"
            ]
            RF24MeshNoMaster [
                xref=":class:`~circuitpython_nrf24l01.rf24_mesh.RF24MeshNoMaster`"
            ]
            RF24Mesh [
                xref=":class:`~circuitpython_nrf24l01.rf24_mesh.RF24Mesh`"
            ]
            RF24MeshNoMaster -> RF24Mesh
        }
        RF24 -> RadioMixin
        NetworkMixin -> RF24NetworkRoutingOnly
        NetworkMixin -> RF24MeshNoMaster
    }

The ``RadioMixin`` and ``NetworkMixin`` classes are not documented directly. Instead, this
documentation follows the OSI (Open Systems Interconnection) model. This is done to mimic how the
TMRh20 C++ libraries and documentation are structured.

Consequentially, all functions and members inherited from the ``NetworkMixin`` class are
documented here as part of the `RF24Network` class. Note that the `RF24MeshNoMaster`, `RF24Mesh`,
and `RF24NetworkRoutingOnly` classes all share the same API inherited from the ``NetworkMixin``
class.

Accessible RF24 API
*******************

The purpose of the ``RadioMixin`` class is

1. to provide a networking layer its own instantiated `RF24` object
2. to prevent applications from changing the radio's configuration in a way that breaks the
   networking layer's behavior

The following list of `RF24` functions and attributes are exposed in the
`RF24Network API <network_api.html>`_ and `RF24Mesh API <mesh_api.html>`_.

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

      >>> # the following command is the same as `nrf.print_details(0, 1)`
      >>> nrf.print_details(dump_pipes=False, network_only=True)
      Network frame_buf contents:
          Header is from 0o7777 to 0o0 type 0 id 1 reserved 0. Message contains:
              an empty buffer
      Return on system messages__False
      Allow network multicasts___True
      Multicast relay____________Disabled
      Network fragmentation______Enabled
      Network max message length_144 bytes
      Network TX timeout_________25 milliseconds
      Network Routing timeout___75 milliseconds
      Network node address_______0o0

  .. note::
      The address :python:`0o7777` (seen in output above) is an invalid address used as a
      sentinel when the frame is unpopulated with a proper `from_node` address.

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
