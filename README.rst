
Introduction
------------

.. :py:currentmodule:: circuitpython_nrf24l01.rf24

.. :py:class:: RF24

.. image:: https://readthedocs.org/projects/circuitpython-nrf24l01/badge/?version=stable
    :target: https://circuitpython-nrf24l01.readthedocs.io/en/stable/
    :alt: Documentation Status

.. image:: https://travis-ci.org/2bndy5/CircuitPython_nRF24L01.svg?branch=master
    :target: https://travis-ci.org/2bndy5/CircuitPython_nRF24L01
    :alt: Build Status

.. image:: https://img.shields.io/pypi/v/circuitpython-nrf24l01.svg
    :alt: latest version on PyPI
    :target: https://pypi.python.org/pypi/circuitpython-nrf24l01

.. image:: https://pepy.tech/badge/circuitpython-nrf24l01
    :alt: Total PyPI downloads
    :target: https://pepy.tech/project/circuitpython-nrf24l01


Circuitpython driver library for the nRF24L01 transceiver

CircuitPython port of the nRF24L01 library from Micropython.
Original work by Damien P. George & Peter Hinch can be found `here
<https://github.com/micropython/micropython/tree/master/drivers/nrf24l01>`_

The Micropython source has been rewritten to expose all the nRF24L01's features and for
compatibilty with the Raspberry Pi and other Circuitpython compatible devices. Modified by Brendan Doherty, Rhys Thomas

* Author(s): Damien P. George, Peter Hinch, Rhys Thomas, Brendan Doherty

Features currently supported
----------------------------

* change the addresses' length (can be 3 to 5 bytes long)
* dynamically sized payloads (max 32 bytes each) or statically sized payloads
* automatic responding acknowledgment (ACK) for verifying transmission success
* custom acknowledgment (ACK) payloads for bi-directional communication
* flag a single payload for no acknowledgment (ACK) from the receiving nRF24L01
* "re-use the same payload" feature (for manually re-transmitting failed transmissions that remain in the buffer)
* multiple payload transmissions with one function call (MUST read documentation on the `send()` function)
* context manager compatible for easily switching between different radio configurations using "with" statements
* configure the interrupt (IRQ) pin to trigger (active low) on received, sent, and/or failed transmissions (these 3 flags control the 1 IRQ pin). There's also virtual representations of these interrupt flags available (see `irq_dr`, `irq_ds`, `irq_df` attributes)
* invoke sleep mode (AKA power down mode) for ultra-low current consumption
* cyclic redundancy checking (CRC) up to 2 bytes long
* adjust the nRF24L01's builtin automatic re-transmit feature's parameters (`arc`: number of attempts, `ard`: delay between attempts)
* adjust the nRF24L01's frequency channel (2.4-2.525 GHz)
* adjust the nRF24L01's power amplifier level (0, -6, -12, or -18 dBm)
* adjust the nRF24L01's RF data rate (250Kbps is buggy due to hardware design, but 1Mbps and 2Mbps are reliable)
* a nRF24L01 driven by this library can communicate with a nRF24L01 on an Arduino driven by the `TMRh20 RF24 library <http://tmrh20.github.io/RF24/>`_. See the nrf24l01_2arduino_handling_data.py code in the `examples folder of this library's repository <examples.html#working-with-tmrh20-s-arduino-library>`_

Features currently unsupported
-------------------------------

* as of yet, no [intended] implementation for Multiceiver mode (up to 6 TX nRF24L01 "talking" to 1 RX nRF24L01 simultaneously). Although this might be acheived easily using the "automatic retry delay" (`ard`) and "automatic retry count" (`arc`) attributes set accordingly (varyingly high -- this has not been tested).

Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Bus Device <https://github.com/adafruit/Adafruit_CircuitPython_BusDevice>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://github.com/adafruit/Adafruit_CircuitPython_Bundle>`_.

Installing from PyPI
=====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/circuitpython-nrf24l01/>`_. To install for current user:

.. code-block:: shell

    pip3 install circuitpython-nrf24l01

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install circuitpython-nrf24l01

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .env
    source .env/bin/activate
    pip3 install circuitpython-nrf24l01

Pinout
======
.. image:: https://lastminuteengineers.com/wp-content/uploads/2018/07/Pinout-nRF24L01-Wireless-Transceiver-Module.png
    :target: https://lastminuteengineers.com/nrf24l01-arduino-wireless-communication/#nrf24l01-transceiver-module-pinout

The nRF24L01 is controlled through SPI so there are 3 pins (SCK, MOSI, & MISO) that can only be connected to their counterparts on the MCU (microcontroller unit). The other 2 essential pins (CE & CSN) can be connected to any digital output pins. Lastly, the only optional pin on the nRf24L01 GPIOs is the IRQ (interrupt; a digital output that's active when low) pin and is only connected to the MCU via a digital input pin during the interrupt example. The following pinout is used in the example codes of this library's `example directory <https://github.com/2bndy5/CircuitPython_nRF24L01/tree/master/examples>`_.

+------------+----------------+----------------+
|  nRF24L01  |  Raspberry Pi  |  ItsyBitsy M4  |
+============+================+================+
|    GND     |      GND       |       GND      |
+------------+----------------+----------------+
|    VCC     |       3V       |      3.3V      |
+------------+----------------+----------------+
|    CE      |     GPIO4      |       D4       |
+------------+----------------+----------------+
|    CSN     |     GPIO5      |       D5       |
+------------+----------------+----------------+
|    SCK     | GPIO11 (SCK)   |       SCK      |
+------------+----------------+----------------+
|    MOSI    | GPIO10 (MOSI)  |      MOSI      |
+------------+----------------+----------------+
|    MISO    | GPIO9 (MISO)   |      MISO      |
+------------+----------------+----------------+
|    IRQ     |     GPIO4      |       D12      |
+------------+----------------+----------------+

.. tip:: User reports and personal experiences have improved results if there is a capacitor of 100 mirofarads [+ another optional 0.1 microfarads capacitor for added stability] connected in parrallel to the VCC and GND pins.

Using The Examples
==================

See `examples <https://circuitpython-nrf24l01.readthedocs.io/en/latest/examples.html>`_ for testing certain features of this the library. The examples were developed and tested on both Raspberry Pi and ItsyBitsy M4. Pins have been hard coded in the examples for the corresponding device, so please adjust these accordingly to your circuitpython device if necessary.

To run the simple example, navigate to this repository's "examples" folder in the terminal. If you're working with a CircuitPython device (not a Raspberry Pi), copy the file named "nrf24l01_simple_test.py" from this repository's "examples" folder to the root directory of your CircuitPython device's CIRCUITPY drive. Now you're ready to open a python REPR and run the following commands:

.. code-block:: python

    >>> from nrf24l01_simple_test import *
        nRF24L01 Simple test
        Run slave() on receiver
        Run master() on transmitter
    >>> master(3)
    Sending: 3 as struct: b'\x03\x00\x00\x00'
    send() succeessful
    Transmission took 86.0 ms
    Sending: 2 as struct: b'\x02\x00\x00\x00'
    send() succeessful
    Transmission took 109.0 ms
    Sending: 1 as struct: b'\x01\x00\x00\x00'
    send() succeessful
    Transmission took 109.0 ms
    # these results were observed from a test on the Raspberry Pi 3
    # transmissions from a CircuitPython device took 32 to 64 ms


About the nRF24L01
==================

Here are the features listed directly from the datasheet (referenced here in the documentation as the `nRF24L01+ Specification Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf>`_):

Key Features:
-------------

    * Worldwide 2.4GHz ISM band operation
    * 250kbps, 1Mbps and 2Mbps on air data rates
    * Ultra low power operation
    * 11.3mA TX at 0dBm output power
    * 13.5mA RX at 2Mbps air data rate
    * 900nA in power down
    * 26μA in standby-I
    * On chip voltage regulator
    * 1.9 to 3.6V supply range
    * Enhanced ShockBurst™
    * Automatic packet handling
    * Auto packet transaction handling
    * 6 data pipe MultiCeiver™
    * Drop-in compatibility with nRF24L01
    * On-air compatible in 250kbps and 1Mbps with nRF2401A, nRF2402, nRF24E1 and nRF24E2
    * Low cost BOM
    * ±60ppm 16MHz crystal
    * 5V tolerant inputs
    * Compact 20-pin 4x4mm QFN package

Applications
------------

    * Wireless PC Peripherals
    * Mouse, keyboards and remotes
    * 3-in-1 desktop bundles
    * Advanced Media center remote controls
    * VoIP headsets
    * Game controllers
    * Sports watches and sensors
    * RF remote controls for consumer electronics
    * Home and commercial automation
    * Ultra low power sensor networks
    * Active RFID
    * Asset tracking systems
    * Toys

Future Project Ideas/Additions using the nRF24L01 (not currently supported by this circuitpython library):

    * `There's a few blog posts by Nerd Ralph demonstrating how to use the nRF24L01 via 2 or 3 pins <http://nerdralph.blogspot.com/2015/05/nrf24l01-control-with-2-mcu-pins-using.html>`_ (uses custom bitbanging SPI functions and an external circuit involving a resistor and a capacitor)
    * network linking layer, maybe something like `TMRh20's RF24Network <http://tmrh20.github.io/RF24Network/>`_
    * add a fake BLE module for sending BLE beacon advertisments from the nRF24L01 as outlined by `Dmitry Grinberg in his write-up (including C source code) <http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_. We've started developing this, but fell short of success in `the BLEfake branch of this library's repository <https://github.com/2bndy5/CircuitPython_nRF24L01/tree/BLEfake>`_

Where do I get 1?
=================

See the store links on the sidebar or just google "nRF24L01". It is worth noting that you generally don't want to buy just 1 as you need 2 for testing -- 1 to send & 1 to receive and vise versa. This library has been tested on a cheaply bought 10 pack from Amazon.com using a highly recommended capacitor (100 µF) on the power pins. Don't get lost on Amazon or eBay! There are other wireless transceivers that are NOT compatible with this library. For instance, the esp8266-01 (also sold in packs) is NOT compatible with this library, but looks very similar to the nRF24L01(+) and could lead to an accidental purchase.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/2bndy5/CircuitPython_nRF24L01/blob/master/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming. To contribute, all you need to do is fork `this repository <https://github.com/2bndy5/CircuitPython_nRF24L01.git>`_, develop your idea(s) and submit a pull request when stable. To initiate a discussion of idea(s), you need only open an issue on the aforementioned repository (doesn't have to be a bug report).

Sphinx documentation
-----------------------

Sphinx is used to build the documentation based on rST files and comments in the code. First,
install dependencies (feel free to reuse the virtual environment from `above <https://circuitpython-nrf24l01.readthedocs.io/en/latest/#installing-from-pypi>`_):

.. code-block:: shell

    python3 -m venv .env
    source .env/bin/activate
    pip install Sphinx sphinx-rtd-theme

Now, once you have the virtual environment activated:

.. code-block:: shell

    cd docs
    sphinx-build -E -W -b html . _build/html

This will output the documentation to ``docs/_build/html``. Open the index.html in your browser to
view them. It will also (due to -W) error out on any warning like Travis CI does. This is a good way to locally verify it will pass.
