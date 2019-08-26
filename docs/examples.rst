
.. important:: There are 2 files in each subfolder of `this library's examples directory <https://github.com/2bndy5/CircuitPython_nRF24L01/tree/master/examples>`_. Only the file used for the raspberry pi is displayed here. Each subfolder represents a different test scenario. Both files (pi_test.py & m4_test.py) are identical with the exception of one line: The pin assignment to the ``ce`` variable. If you've connected the nRF24L01's CE or CSN pins to different pins (compared to what we specified in the examples), then you need change that pin assignment accordingly before running these examples/tests.

Simple test
------------

Ensure your device works with this simple test.

.. literalinclude:: ../examples/simple/pi_test.py
    :caption: examples/simple/pi_test.py
    :linenos:

ACK Payloads Example
--------------------

This is a test to show how to use custom acknowledgment payloads.

.. literalinclude:: ../examples/ack_payloads/pi_test.py
    :caption: examples/ack_payloads/pi_test.py
    :linenos:

IRQ Pin Example
---------------

This is a test to show how to use nRF24L01's interrupt pin.

.. literalinclude:: ../examples/interrupt/pi_test.py
    :caption: examples/interrupt/pi_test.py
    :linenos:

Stream Example
---------------

This is a test to show how to use the send() to transmit multiple payloads.

.. literalinclude:: ../examples/stream/pi_test.py
    :caption: examples/stream/pi_test.py
    :linenos:

Context Example
---------------

This is a test to show how to use "with" statements to manage multiple different nRF24L01 configurations on 1 transceiver.

.. literalinclude:: ../examples/context/pi_test.py
    :caption: examples/context/pi_test.py
    :linenos:
