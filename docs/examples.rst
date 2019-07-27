
.. important:: There are 2 files in each subfolder of `this repo's examples directory <https://github.com/2bndy5/CircuitPython_nRF24L01/tree/master/examples>`_. Only the file used for the raspberry pi is displayed here. Each subfolder represents a different test scenario. Both files (pi_test.py & m4_test.py) are identical with the exception of one line: The pin assignment to the ``ce`` variable. If you've connected the nRF24L01's CE or CSN pins to different pins (compared to what we specified in the examples), then you need change that pin assignment accordingly before running these examples/tests.

Simple test
------------

Ensure your device works with this simple test.

.. literalinclude:: ../examples/simple/pi_test.py
    :caption: examples/simple/pi_test.py
    :linenos:

.. important:: There are 2 files in each subfolder of `this repo's examples directory <https://github.com/2bndy5/CircuitPython_nRF24L01/tree/master/examples>`_. Only the file used for the raspberry pi is displayed here. Each subfolder represents a different test scenario. Both files (pi_test.py & m4_test.py) are identical with the exception of one line: The pin assignment to the ``ce`` variable. If you've connected the nRF24L01's CE or CSN pins to different pins (compared to what we specified in the examples), then you need change that pin assignment accordingly before running these examples/tests.

ACK Payloads Example
--------------------

This is a test to show how to use custom acknowledgment payloads.

.. literalinclude:: ../examples/ack_payloads/pi_test.py
    :caption: examples/ack_payloads/pi_test.py
    :linenos:

.. important:: There are 2 files in each subfolder of `this repo's examples directory <https://github.com/2bndy5/CircuitPython_nRF24L01/tree/master/examples>`_. Only the file used for the raspberry pi is displayed here. Each subfolder represents a different test scenario. Both files (pi_test.py & m4_test.py) are identical with the exception of one line: The pin assignment to the ``ce`` variable. If you've connected the nRF24L01's CE or CSN pins to different pins (compared to what we specified in the examples), then you need change that pin assignment accordingly before running these examples/tests.

IRQ Pin Example
---------------

This is a test to show how to use nRF24L01's interrupt pin.

.. literalinclude:: ../examples/interrupt/pi_test.py
    :caption: examples/interrupt/pi_test.py
    :linenos:
