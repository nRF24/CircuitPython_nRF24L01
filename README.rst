

.. image:: https://readthedocs.org/projects/circuitpython-nrf24l01/badge/?version=stable
    :target: https://circuitpython-nrf24l01.readthedocs.io/en/stable/
    :alt: Documentation Status

.. image:: https://github.com/2bndy5/CircuitPython_nRF24L01/workflows/Build%20CI/badge.svg
    :target: https://github.com/2bndy5/CircuitPython_nRF24L01/actions?query=workflow%3A%22Build+CI%22
    :alt: Build Status

.. image:: https://img.shields.io/github/commits-since/2bndy5/CircuitPython_nRF24L01/latest?&style=plastic
    :alt: GitHub commits since latest release (by date)
    :target: https://github.com/2bndy5/CircuitPython_nRF24L01/commits/master

.. image:: https://img.shields.io/pypi/v/circuitpython-nrf24l01.svg
    :alt: latest version on PyPI
    :target: https://pypi.python.org/pypi/circuitpython-nrf24l01

.. image:: https://pepy.tech/badge/circuitpython-nrf24l01?label=pypi%20downloads&logo=python
    :alt: Total PyPI downloads
    :target: https://pepy.tech/project/circuitpython-nrf24l01

Introduction
============

Circuitpython driver library for the nRF24L01 transceiver

CircuitPython port of the nRF24L01 library from Micropython.
Original work by Damien P. George & Peter Hinch can be found `here
<https://github.com/micropython/micropython/tree/master/drivers/nrf24l01>`_

The Micropython source has been rewritten to expose all the nRF24L01's features and for
compatibilty with the Raspberry Pi and other Circuitpython compatible devices. Modified by Brendan Doherty, Rhys Thomas

* Author(s): Damien P. George, Peter Hinch, Rhys Thomas, Brendan Doherty

Features currently supported
============================

* change the addresses' length (can be 3 to 5 bytes long)
* dynamically sized payloads (max 32 bytes each) or statically sized payloads
* automatic responding acknowledgment (ACK) for verifying transmission success
* custom acknowledgment (ACK) payloads for bi-directional communication
* flag a single payload for no acknowledgment (ACK) from the receiving nRF24L01
* "re-use the same payload" feature (for manually re-transmitting failed transmissions that remain in the buffer)
* multiple payload transmissions with one function call (MUST read documentation on the `send()` function)
* context manager compatible for easily switching between different radio configurations using "with" statements (not available in ``rf24_lite.py`` variant for M0 based boards)
* configure the interrupt (IRQ) pin to trigger (active low) on received, sent, and/or failed transmissions (these 3 flags control the 1 IRQ pin). There's also virtual representations of these interrupt flags available (see `irq_dr`, `irq_ds`, `irq_df` attributes)
* invoke sleep mode (AKA power down mode) for ultra-low current consumption
* cyclic redundancy checking (CRC) up to 2 bytes long
* adjust the nRF24L01's builtin automatic re-transmit feature's parameters (`arc`: number of attempts, `ard`: delay between attempts)
* adjust the nRF24L01's frequency channel (2.4-2.525 GHz)
* adjust the nRF24L01's power amplifier level (0, -6, -12, or -18 dBm)
* adjust the nRF24L01's RF data rate (250Kbps is buggy due to hardware design, but 1Mbps and 2Mbps are reliable)
* a nRF24L01 driven by this library can communicate with a nRF24L01 on an Arduino driven by the `TMRh20 RF24 library <http://tmrh20.github.io/RF24/>`_. See the nrf24l01_2arduino_handling_data.py code in the `examples folder of this library's repository <examples.html#working-with-tmrh20-s-arduino-library>`_
* fake BLE module for sending BLE beacon advertisments from the nRF24L01 as outlined by `Dmitry Grinberg in his write-up (including C source code) <http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_.

Features currently unsupported
==============================

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

.. csv-table::
    :header: nRF2401, "Raspberry Pi", "ItsyBitsy M4"

    GND, GND, GND
    VCC, 3V, 3.3V
    CE, GPIO4, D4
    CSN, GPIO5, D5
    SCK, "GPIO11 (SCK)", SCK
    MOSI, "GPIO10 (MOSI)", MOSI
    MISO, "GPIO9 (MISO)", MISO
    IRQ, GPIO12, D12

.. tip:: User reports and personal experiences have improved results if there is a capacitor of 100 mirofarads [+ another optional 0.1 microfarads capacitor for added stability] connected in parrallel to the VCC and GND pins.

Using The Examples
==================

See `examples <https://circuitpython-nrf24l01.readthedocs.io/en/latest/examples.html>`_ for testing certain features of this the library. The examples were developed and tested on both Raspberry Pi and ItsyBitsy M4. Pins have been hard coded in the examples for the corresponding device, so please adjust these accordingly to your circuitpython device if necessary.

To run the simple example, navigate to this repository's "examples" folder in the terminal. If you're working with a CircuitPython device (not a Raspberry Pi), copy the file named "nrf24l01_simple_test.py" from this repository's "examples" folder to the root directory of your CircuitPython device's CIRCUITPY drive. Now you're ready to open a python REPR and run the following commands:

.. code-block:: python

    >>> from nrf24l01_simple_test import *
        nRF24L01 Simple test.
        Run slave() on receiver
        Run master() on transmitter
    >>> master()
    Sending: 5 as struct: b'\x05\x00\x00\x00'
    send() successful
    Transmission took 36.0 ms
    Sending: 4 as struct: b'\x04\x00\x00\x00'
    send() successful
    Transmission took 28.0 ms
    Sending: 3 as struct: b'\x03\x00\x00\x00'
    send() successful
    Transmission took 24.0 ms


Where do I get 1?
=================

See the store links on the sidebar or just google "nRF24L01+". It is worth noting that you
generally want to buy more than 1 as you need 2 for testing -- 1 to send & 1 to receive and
vise versa. This library has been tested on a cheaply bought 6 pack from Amazon.com, but don't
take Amazon or eBay for granted! There are other wireless transceivers that are NOT compatible
with this library. For instance, the esp8266-01 (also sold in packs) is NOT compatible with
this library, but looks very similar to the nRF24L01+ and could lead to an accidental purchase.

About the nRF24L01+
===================

Stablizing the power input to the VCC and GND using parallel capacitors (100 µF + an optional
0.1µF) provides significant performance increases. This stability is very highly recommended!
More finite details about the nRF24L01 are available from the datasheet (referenced here in
the documentation as the `nRF24L01+ Specification Sheet <https://www.sparkfun.com/datasheets/
Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf>`_)

About the nRF24L01+PA+LNA modules
=================================

You may find variants of the nRF24L01 transceiver that are marketed as "nRF24L01+PA+LNA".
These modules are distinct in the fact that they come with a detachable (SMA-type) antenna.
They employ seperate RFX24C01 IC with the antenna for enhanced Power Amplification (PA) and
Low Noise Amplification (LNA) features. While they boast greater range with the same
functionality, they are subject to a couple lesser known (and lesser advertised) drawbacks:

1. Stronger power source. Below is a chart of advertised current requirements that many MCU
   boards' 3V regulators may not be able to handle.

    .. csv-table::
        :header: Specification, Value
        :widths: 10,5

        "Emission mode current(peak)", "115 mA"
        "Receive Mode current(peak)", "45 mA"
        "Power-down mode current", "4.2 µA"
2. Needs sheilding from electromagnetic interference. Sheilding works best when it has a path
   to ground (GND pin)

nRF24L01(+) clones and counterfeits
===================================

This library does not directly support clones/counterfeits as there is no way for the library
to differentiate between an actual nRF24L01+ and a clone/counterfeit. To determine if your
purchase is a counterfeit, please contact the retailer you purxhased from (`reading this
article and its links might help
<https://hackaday.com/2015/02/23/nordic-nrf24l01-real-vs-fake/>`_). The most notable clone is the `Si24R1 <https://lcsc.com/product-detail/
RF-Transceiver-ICs_Nanjing-Zhongke-Microelectronics-Si24R1_C14436.html>`_. I could not find
the `Si24R1 datasheet <https://datasheet.lcsc.com/szlcsc/
1811142211_Nanjing-Zhongke-Microelectronics-Si24R1_C14436.pdf>`_ in english. Troubleshooting
the SI24R1 may require `replacing the onboard antennae with a wire
<https://forum.mysensors.org/post/96871>`_. Furthermore, the Si24R1 has different power
amplifier options as noted in the `RF_PWR section (bits 0 through 2) of the RF_SETUP register
(hex address 6) of the datasheet <https://datasheet.lcsc.com/szlcsc/
1811142211_Nanjing-Zhongke-Microelectronics-Si24R1_C14436.pdf#%5B%7B%22num%22%3A329%2C%22gen%22%3A0%7D%2C%7B%22name%22%3A%22XYZ%22%7D%2C0%2C755%2Cnull%5D>`_.
While the options' values differ from those identified by this library's API, the
underlying commands to configure those options are almost identical to the nRF24L01. Other
known clones include the bk242x (AKA RFM7x).

Future Project Ideas/Additions
==============================

    The following are only ideas; they are not currently supported by this circuitpython library.

    * `There's a few blog posts by Nerd Ralph demonstrating how to use the nRF24L01 via 2 or 3
      pins <http://nerdralph.blogspot.com/2015/05/nrf24l01-control-with-2-mcu-pins-using.
      html>`_ (uses custom bitbanging SPI functions and an external circuit involving a
      resistor and a capacitor)
    * network linking layer, maybe something like `TMRh20's RF24Network
      <http://tmrh20.github.io/RF24Network/>`_
    * implement the Gazelle-based protocol used by the BBC micro-bit (`makecode.com's radio
      blocks <https://makecode.microbit.org/reference/radio>`_).

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
view them. It will also (due to -W) error out on any warning like the Github action, Build CI,
does. This is a good way to locally verify it will pass.
