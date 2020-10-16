nRF24L01 Features
=================

Simple test
------------

Ensure your device works with this simple test.

.. literalinclude:: ../examples/nrf24l01_simple_test.py
    :caption: examples/nrf24l01_simple_test.py
    :linenos:

ACK Payloads Example
--------------------

This is a test to show how to use custom acknowledgment payloads. See also documentation on `ack` and `load_ack()`.

.. literalinclude:: ../examples/nrf24l01_ack_payload_test.py
    :caption: examples/nrf24l01_ack_payload_test.py
    :linenos:

Multiceiver Example
--------------------

This example shows how use a group of 6 nRF24L01 transceivers to transmit to 1 nRF24L01 transceiver. `This technique is called "Multiceiver" in the nRF24L01 Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1104474>`_

.. note:: This example follows the diagram illistrated in `figure 12 of section 7.7 of the nRF24L01 Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#page=39>`_ Please note that if `auto_ack` (on the base station) and `arc` (on the trnasmitting nodes) are disabled, then `figure 10 of section 7.7 of the nRF24L01 Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1104474>`_ would be a better illustration.

.. hint:: A paraphrased note from the the nRF24L01 Specifications Sheet:

    *Only when a data pipe receives a complete packet can other data pipes begin to receive data. When multiple [nRF24L01]s are transmitting to [one nRF24L01], the* `ard` *can be used to skew the auto retransmission so that they only block each other once.*

    This basically means that it might help packets get received if the `ard` attribute is set to various values among multiple transmitting nRF24L01 transceivers.

.. literalinclude:: ../examples/nrf24l01_multiceiver_test.py
    :caption: examples/nrf24l01_multiceiver_test.py
    :linenos:

IRQ Pin Example
---------------

This is a test to show how to use nRF24L01's interrupt pin. Be aware that :py:func:`~circuitpython_nrf24l01.rf24.RF24.send()` clears all IRQ events on exit, so we use the non-blocking :py:func:`~circuitpython_nrf24l01.rf24.RF24.write()` instead. Also the `ack` attribute is enabled to trigger the :py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_dr` event when the master node receives ACK payloads. Simply put, this example is the most advanced example script (in this library), and it runs VERY quickly.

.. literalinclude:: ../examples/nrf24l01_interrupt_test.py
    :caption: examples/nrf24l01_interrupt_test.py
    :linenos:

Library-Specific Features
=========================

Stream Example
---------------

This is a test to show how to stream data. The ``master()`` uses the `send()` to
transmit multiple payloads with 1 function call. However ``master()`` only uses 1
level of the nRF24L01's TX FIFO. An alternate function, called ``master_fifo()``
uses all 3 levels of the nRF24L01's TX FIFO to stream data, but it uses the
`write()` function to do so.

.. literalinclude:: ../examples/nrf24l01_stream_test.py
    :caption: examples/nrf24l01_stream_test.py
    :linenos:

Context Example
---------------

This is a test to show how to use `with` blocks to manage multiple different nRF24L01 configurations on 1 transceiver.

.. literalinclude:: ../examples/nrf24l01_context_test.py
    :caption: examples/nrf24l01_context_test.py
    :linenos:

OTA compatibility
=================

Fake BLE Example
----------------

This is a test to show how to use the nRF24L01 as a BLE advertising beacon using the :py:class:`~circuitpython_nrf24l01.rf24.fake_ble.FakeBLE` class.

.. literalinclude:: ../examples/nrf24l01_fake_ble_test.py
    :caption: examples/nrf24l01_fake_ble_test.py
    :linenos:

TMRh20's Arduino library
------------------------

This test is meant to prove compatibility with the popular Arduino library for the nRF24L01 by TMRh20 (available for install via the Arduino IDE's Library Manager). The following code has been designed/test with the TMRh20 library example named `GettingStarted_HandlingData.ino <https://tmrh20.github.io/RF24/GettingStarted_HandlingData_8ino-example.html>`_. If you changed the ``role`` variable in the TMRh20 sketch, you will have to adjust the addresses assigned to the pipes in this script.

.. literalinclude:: ../examples/nrf24l01_2arduino_handling_data.py
    :caption: examples/nrf24l01_2arduino_handling_data.py
    :linenos:
