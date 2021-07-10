RF24Mesh API
============

.. versionadded:: 2.1.0

.. seealso:: Documentation for:

    1. `Shared Networking API <base_api.html#>`_
    2. `Network Data Structures <structs.html>`_
    3. `Network Constants <constants.html>`_
    4. `RF24Network API <network_api.html>`_ (especially the `node_address` and
       :meth:`~circuitpython_nrf24l01.network.rf24_network.RF24Network.write()`)


RF24Mesh class
**************

.. autoclass:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh
    :show-inheritance:

    .. seealso:: For all parameters' descriptions, see the
        :py:class:`~circuitpython_nrf24l01.rf24.RF24` class' contructor documentation.

Basic API
*********

update()
--------

.. automethod:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.update

send()
--------

.. automethod:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.send

node_id
-------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.node_id

renew_address()
---------------

.. automethod:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.renew_address

Advanced API
************

get_node_id()
-------------

.. automethod:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.get_node_id

get_address()
-------------

.. automethod:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.get_address

check_connection
----------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.check_connection

release_address()
-----------------

.. automethod:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.release_address


allow_children
--------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.allow_children

less_blocking_helper_function
-----------------------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_mesh.RF24Mesh.less_blocking_helper_function
