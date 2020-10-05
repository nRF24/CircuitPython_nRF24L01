
Simple test
------------

Ensure your device works with this simple test.

.. literalinclude:: ../examples/nrf24l01_simple_test.py
    :caption: examples/nrf24l01_simple_test.py
    :linenos:

ACK Payloads Example
--------------------

This is a test to show how to use custom acknowledgment payloads.

.. literalinclude:: ../examples/nrf24l01_ack_payload_test.py
    :caption: examples/nrf24l01_ack_payload_test.py
    :linenos:

Stream Example
---------------

This is a test to show how to use the send() to transmit multiple payloads.

.. literalinclude:: ../examples/nrf24l01_stream_test.py
    :caption: examples/nrf24l01_stream_test.py
    :linenos:

Fake BLE Example
----------------

This is a test to show how to use the nRF24L01 as a BLE advertising beacon.

.. literalinclude:: ../examples/nrf24l01_fake_ble_test.py
    :caption: examples/nrf24l01_fake_ble_test.py
    :linenos:

Context Example
---------------

This is a test to show how to use "with" statements to manage multiple different nRF24L01 configurations on 1 transceiver.

.. literalinclude:: ../examples/nrf24l01_context_test.py
    :caption: examples/nrf24l01_context_test.py
    :linenos:

Working with TMRh20's Arduino library
-------------------------------------

This test is meant to prove compatibility with the popular Arduino library for the nRF24L01 by TMRh20 (available for install via the Arduino IDE's Library Manager). The following code has been designed/test with the TMRh20 library example named "GettingStarted_HandlingData.ino". If you changed the ``role`` variable in the TMRh20 sketch, you will have to adjust the addresses assigned to the pipes in this script.

.. literalinclude:: ../examples/nrf24l01_2arduino_handling_data.py
    :caption: examples/nrf24l01_2arduino_handling_data.py
    :linenos:

IRQ Pin Example
---------------

This is a test to show how to use nRF24L01's interrupt pin. Be aware that `send()` clears all IRQ events on exit, so we use the non-blocking `write()` instead. Also the `ack` attribute is enabled to trigger the :py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_dr` event when the master node receives ACK payloads. Simply put, this example is the most advanced example script, and it runs VERY quickly.

.. literalinclude:: ../examples/nrf24l01_interrupt_test.py
    :caption: examples/nrf24l01_interrupt_test.py
    :linenos:
