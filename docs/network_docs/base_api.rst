Shared Networking API
======================

Accessible RF24 API
*******************

The follow is a list of `RF24` functions and attributes that are exposed in the
`RF24Network` and `RF24Mesh` API.

* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.channel`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.dynamic_payloads`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.set_dynamic_payloads`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.get_dynamic_payloads`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.listen`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.pa_level`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.is_lna_enabled`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.data_rate`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.crc`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.ard`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.arc`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.set_auto_retries`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.get_auto_retries`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.last_tx_arc`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.address`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.interrupt_config`
* :py:meth:`~circuitpython_nrf24l01.rf24.RF24.print_details`


External Systems API
********************

The following attributes are exposed in the `RF24Network` and `RF24Mesh` API for
extensibility via external applications or systems.

frame_cache
-----------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.frame_cache

queue
-----

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.queue

ret_sys_msg
-----------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.ret_sys_msg

network_flags
-------------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.network_flags
