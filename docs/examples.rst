nRF24L01 Features
=================

Simple test
------------

.. versionchanged:: 2.0.0

    - uses 2 addresses on pipes 1 & 0 to demonstrate proper addressing convention.
    - transmits an incrementing `float` instead of an `int`

Ensure your device works with this simple test.

.. literalinclude:: ../examples/nrf24l01_simple_test.py
    :caption: examples/nrf24l01_simple_test.py
    :start-at: import time
    :end-before: def set_role():

ACK Payloads Example
--------------------

.. versionchanged:: 2.0.0

    - uses 2 addresses on pipes 1 & 0 to demonstrate proper addressing convention.
    - changed payloads to show use of c-strings' NULL terminating character.

This is a test to show how to use custom acknowledgment payloads.

.. seealso:: More details are found in the documentation on `ack` and `load_ack()`.

.. literalinclude:: ../examples/nrf24l01_ack_payload_test.py
    :caption: examples/nrf24l01_ack_payload_test.py
    :start-at: import time
    :end-before: def set_role():

Multiceiver Example
--------------------

.. versionadded:: 1.2.2

.. versionchanged:: 2.0.0
    no longer uses ACK payloads for responding to node 1.

This example shows how use a group of 6 nRF24L01 transceivers to transmit to 1 nRF24L01
transceiver. This technique is called `"Multiceiver" in the nRF24L01 Specifications Sheet
<https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1104474>`_

.. note:: This example follows the diagram illistrated in
    `figure 12 of section 7.7 of the nRF24L01 Specifications Sheet
    <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#page=39>`_
    Please note that if `auto_ack` (on the base station) and `arc` (on the
    transmitting nodes) are disabled, then
    `figure 10 of section 7.7 of the nRF24L01 Specifications Sheet
    <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1104474>`_
    would be a better illustration.

.. hint:: A paraphrased note from the the nRF24L01 Specifications Sheet:

        *Only when a data pipe receives a complete packet can other data pipes begin
        to receive data. When multiple [nRF24L01]s are transmitting to [one nRF24L01],
        the* `ard` *can be used to skew the auto retransmission so that they only block
        each other once.*

    This basically means that it might help packets get received if the `ard` attribute
    is set to various values among multiple transmitting nRF24L01 transceivers.

.. literalinclude:: ../examples/nrf24l01_multiceiver_test.py
    :caption: examples/nrf24l01_multiceiver_test.py
    :start-at: import time
    :end-before: def set_role():

Scanner Example
---------------

.. versionadded:: 2.0.0

This example simply scans the entire RF frquency (2.4 GHz to 2.525 GHz)
and outputs a vertical graph of how many signals (per
:py:attr:`~circuitpython_nrf24l01.rf24.RF24.channel`) were detected. This example
can be used to find a frequency with the least ambient interference from other
radio-emitting sources (i.e. WiFi, Bluetooth, or etc).

.. literalinclude:: ../examples/nrf24l01_scanner_test.py
    :caption: examples/nrf24l01_scanner_test.py
    :start-at: import time
    :end-before: def set_role():

Reading the scanner output
**************************

.. hint:: Make sure the terminal window used to run the scanner example is expanded
    to fit 125 characters. Otherwise the output will look weird.

The output of the scanner example is supposed to be read vertically (as columns).
So, the following

    | 000
    | 111
    | 789
    | ~~~
    | 13-

should be interpreted as

- ``1`` signal detected on channel ``017``
- ``3`` signals detected on channel ``018``
- no signal (``-``) detected on channel ``019``

The ``~`` is just a divider between the vertical header and the signal counts.

IRQ Pin Example
---------------

.. versionchanged:: 1.2.0
    uses ACK payloads to trigger all 3 IRQ events.
.. versionchanged:: 2.0.0
    uses 2 addresses on pipes 1 & 0 to demonstrate proper addressing convention.

This is a test to show how to use nRF24L01's interrupt pin using the non-blocking
`write()`. Also the `ack` attribute is enabled to trigger the `irq_dr` event when
the master node receives ACK payloads. Simply put, this example is the most advanced
example script (in this library), and it runs **very** quickly.

.. literalinclude:: ../examples/nrf24l01_interrupt_test.py
    :caption: examples/nrf24l01_interrupt_test.py
    :start-at: import time
    :end-before: def set_role():

Library-Specific Features
=========================

Stream Example
---------------

.. versionchanged:: 1.2.3
    added ``master_fifo()`` to demonstrate using full TX FIFO to stream data.
.. versionchanged:: 2.0.0
    uses 2 addresses on pipes 1 & 0 to demonstrate proper addressing convention.

This is a test to show how to stream data. The ``master()`` uses the `send()`
function to transmit multiple payloads with 1 function call. However
``master()`` only uses 1 level of the nRF24L01's TX FIFO. An alternate function,
called ``master_fifo()`` uses all 3 levels of the nRF24L01's TX FIFO to stream
data, but it uses the `write()` function to do so.

.. literalinclude:: ../examples/nrf24l01_stream_test.py
    :caption: examples/nrf24l01_stream_test.py
    :start-at: import time
    :end-before: def set_role():

Context Example
---------------

.. versionchanged:: 1.2.0
    demonstrates switching between `FakeBLE` object & `RF24` object with the same nRF24L01

This is a test to show how to use `with` blocks to manage multiple different nRF24L01 configurations on 1 transceiver.

.. literalinclude:: ../examples/nrf24l01_context_test.py
    :caption: examples/nrf24l01_context_test.py
    :start-at: import board

Manual ACK Example
------------------

.. versionadded:: 2.0.0
    Previously, this example was strictly made for TMRh20's RF24 library example
    titled "GettingStarted_HandlingData.ino". With the latest addition of new
    examples to the TMRh20 RF24 library, this example was renamed from
    "nrf24l01_2arduino_handling_data.py" and adapted for both this library and
    TMRh20's RF24 library.

This is a test to show how to use the library for acknowledgement (ACK) responses
without using the automatic ACK packets (like the `ACK Payloads Example`_ does).
Beware, that this technique is not faster and can be more prone to communication
failure. However, This technique has the advantage of using more updated information
in the responding payload as information in ACK payloads are always outdated by 1
transmission.

.. literalinclude:: ../examples/nrf24l01_manual_ack_test.py
    :caption: examples/nrf24l01_manual_ack_test.py
    :start-at: import time
    :end-before: def set_role():

OTA compatibility
=================

Fake BLE Example
----------------

.. versionadded:: 1.2.0

This is a test to show how to use the nRF24L01 as a BLE advertising beacon using the
`FakeBLE` class.

.. literalinclude:: ../examples/nrf24l01_fake_ble_test.py
    :caption: examples/nrf24l01_fake_ble_test.py
    :start-at: import time
    :end-before: def set_role():

TMRh20's Arduino library
------------------------

All examples are designed to work with TMRh20's RF24 library examples.
This Circuitpython library uses dynamic payloads enabled by default.
TMRh20's library uses static payload lengths by default.

To make this circuitpython library compatible with
`TMRh20's RF24 library <https://github.com/nRF24/RF24/>`_:

1. set `dynamic_payloads` to `False`.
2. set `allow_ask_no_ack` to `False`.
3. set :py:attr:`~circuitpython_nrf24l01.rf24.RF24.payload_length` to the value that
   is passed to TMRh20's ``RF24::setPayloadSize()``. 32 is the default (& maximum)
   payload length/size for both libraries.

   .. warning:: Certain C++ datatypes allocate a different amount of memory depending on
       the board being used in the Arduino IDE. For example, ``uint8_t`` isn't always
       allocated to 1 byte of memory for certain boards.
       Make sure you understand the amount of memory that different datatypes occupy in C++.
       This will help you comprehend how to configure
       :py:attr:`~circuitpython_nrf24l01.rf24.RF24.payload_length`.

For completness, TMRh20's RF24 library uses a default value of 15 for the `ard` attribute,
but this Circuitpython library uses a default value of 3.

.. csv-table:: Corresponding examples
    :header: circuitpython_nrf24l01, TMRh20 RF24

    "nrf24l01_simple_test\ [1]_ ", gettingStarted
    nrf24l01_ack_payload_test, acknowledgementPayloads
    "nrf24l01_manual_ack_test\ [1]_ ", manualAcknowledgements
    "nrf24l01_multiceiver_test\ [1]_ ", multiceiverDemo
    "nrf24l01_stream_test\ [1]_ ", streamingData
    nrf24l01_interrupt_test, interruptConfigure
    nrf24l01_context_test, feature is not available
    nrf24l01_fake_ble_test, feature is available via `floe's BTLE library <https://github.com/floe/BTLE>`_

.. [1] Some of the Circuitpython examples (that are compatible with TMRh20's examples)
       contain 2 or 3 lines of code that are commented out for easy modification. These lines
       look like this in the examples' source code:

       .. code-block:: python

           # uncomment the following 3 lines for compatibility with TMRh20 library
           # nrf.allow_ask_no_ack = False
           # nrf.dynamic_payloads = False
           # nrf.payload_length = 4
