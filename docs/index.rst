:hide-navigation:

.. toctree::
    :hidden:

    examples

.. toctree::
    :caption: Core API Reference
    :hidden:

    core_api/basic_api
    core_api/advanced_api
    core_api/configure_api
    core_api/ble_api

.. toctree::
    :caption: Network API Reference
    :hidden:

    network_docs/topology
    network_docs/structs
    network_docs/shared_api
    network_docs/network_api
    network_docs/mesh_api
    network_docs/constants

.. toctree::
    :hidden:

    contributing
    troubleshooting

.. only:: html

    .. image:: https://img.shields.io/static/v1?label=Visual%20Studio%20Code&message=Use%20Online%20IDE&color=blue&logo=visualstudiocode&logoColor=3f9ae6
        :target: https://vscode.dev/github/nRF24/CircuitPython_nRF24L01
        :alt: Open in Visual Studio Code
    .. image:: https://img.shields.io/badge/Gitpod-Use%20Online%20IDE-B16C04?logo=gitpod
        :target: https://gitpod.io/#https://github.com/2bndy5/CircuitPython_nRF24L01
        :alt: Open in Gitpod

Getting Started
~~~~~~~~~~~~~~~

Introduction
===============

This is a Circuitpython driver library for the nRF24L01(+) transceiver.

Originally this code was a Micropython module written by Damien P. George
& Peter Hinch which can still be found `here
<https://github.com/micropython/micropython-lib/tree/master/micropython/drivers/radio/nrf24l01>`_

The Micropython source has since been rewritten to expose all the nRF24L01's
features and for Circuitpython compatible devices (including linux-based
SoC computers like the Raspberry Pi).
Modified by Brendan Doherty & Rhys Thomas.

* Authors: Damien P. George, Peter Hinch, Rhys Thomas, Brendan Doherty

Features currently supported
----------------------------

* Change the address's length (can be 3 to 5 bytes long)
* Dynamically sized payloads (max 32 bytes each) or statically sized payloads
* Automatic responding acknowledgment (ACK) packets for verifying transmission success
* Append custom payloads to the acknowledgment (ACK) packets for instant bi-directional communication
* Mark a single payload for no acknowledgment (ACK) from the receiving nRF24L01 (see ``ask_no_ack``
  parameter for :meth:`~circuitpython_nrf24l01.rf24.RF24.send()` and :meth:`~circuitpython_nrf24l01.rf24.RF24.write()` functions)
* Invoke the "re-use the same payload" feature (for manually re-transmitting failed transmissions that
  remain in the TX FIFO buffer)
* Multiple payload transmissions with one function call (see documentation on the
  :py:meth:`~circuitpython_nrf24l01.rf24.RF24.send()` function and try out the
  `Stream example <examples.html#stream-example>`_)
* Context manager compatible for easily switching between different radio configurations
  using `with` blocks (not available in ``rf24_lite.py`` version)
* Configure the interrupt (IRQ) pin to trigger (active low) on received, sent, and/or
  failed transmissions (these 3 events control 1 IRQ pin). There's also virtual
  representations of these interrupt events available (see `irq_dr`, `irq_ds`, & `irq_df` attributes)
* Invoke sleep mode (AKA power down mode) for ultra-low current consumption
* cyclic redundancy checking (CRC) up to 2 bytes long
* Adjust the nRF24L01's builtin automatic re-transmit feature's parameters (`arc`: number
  of attempts, `ard`: delay between attempts)
* Adjust the nRF24L01's frequency channel (2.4 - 2.525 GHz)
* Adjust the nRF24L01's power amplifier level (0, -6, -12, or -18 dBm)
* Adjust the nRF24L01's RF data rate (250kbps, 1Mbps, or 2Mbps)
* An nRF24L01 driven by this library can communicate with a nRF24L01 on an Arduino driven by the
  `TMRh20 RF24 library <http://tmrh20.github.io/RF24/>`_.
* fake BLE module for sending BLE beacon advertisements from the nRF24L01 as outlined by
  `Dmitry Grinberg in his write-up (including C source code) <http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_.
* Multiceiver\ :sup:`TM` mode (up to 6 TX nRF24L01 "talking" to 1 RX nRF24L01 simultaneously).
  See the `Multiceiver Example <examples.html#multiceiver-example>`_
* Networking capability that allows up to 781 transceivers to interact with each other.

  * This does not mean the radio can connect to WiFi. The networking implementation is a
    custom protocol ported from TMRh20's RF24Network & RF24Mesh libraries.


Dependencies
--------------------------

This driver depends on:

* `Adafruit CircuitPython Firmware <https://circuitpython.org/downloads>`_ or the
  `Adafruit_Blinka library <https://github.com/adafruit/Adafruit_Blinka>`_ for Linux
  SoC boards like Raspberry Pi
* `adafruit_bus_device` (specifically the :py:class:`~adafruit_bus_device.SPIDevice` class)

  .. tip:: Use CircuitPython v6.3.0 or newer because faster SPI execution yields
      faster transmissions.
* The `SpiDev <https://pypi.org/project/spidev/>`_ module is a C-extension that executes
  SPI transactions faster than Adafruit's PureIO library (a dependency of the
  `Adafruit_Blinka library <https://github.com/adafruit/Adafruit_Blinka>`_).

The `adafruit_bus_device`, `Adafruit_Blinka library <https://github.com/adafruit/Adafruit_Blinka>`_,
and `SpiDev <https://pypi.org/project/spidev/>`_ libraries
are installed automatically on Linux when installing this library.

.. versionadded:: 2.1.0
    Added support for the `SpiDev <https://pypi.org/project/spidev/>`_ module

.. important::
    This library supports Python 3.7 or newer because it uses the function
    :py:func:`time.monotonic_ns()` which returns an arbitrary time "counter" as an `int` of
    nanoseconds. CircuitPython firmware also supports :py:func:`time.monotonic_ns()`.


Installing from PyPI
--------------------

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/circuitpython-nrf24l01/>`_. To install for current user:

.. code-block:: shell

    pip3 install circuitpython-nrf24l01

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

The nRF24L01 is controlled through SPI so there are 3 pins (SCK, MOSI, & MISO) that can only be
connected to their counterparts on the MCU (microcontroller unit). The other 2 essential pins
(CE & CSN) can be connected to any digital output pins. Lastly, the only optional GPIO pin on the
nRF24L01 is the IRQ (interrupt; a digital output that's active when low) pin and is only connected
to the MCU via a digital input pin during the interrupt example.


.. csv-table:: The pins used in `this library's examples <examples.html>`_.
    :header: nRF24L01, "ItsyBitsy M4", "Raspberry Pi"
    :widths: 2, 6, 22


    GND, GND, GND
    VCC, 3.3V, 3V
    CE, D4, "- GPIO4 if using CircuitPython's :py:class:`~adafruit_bus_device.SPIDevice`
    - GPIO22 if using the `SpiDev <https://pypi.org/project/spidev/>`_ module"
    CSN, D5, "- GPIO5 if using CircuitPython's :py:class:`~adafruit_bus_device.SPIDevice`
    - GPIO8 (CE0) if using the `SpiDev <https://pypi.org/project/spidev/>`_ module"
    SCK, SCK, "GPIO11 (SCK)"
    MOSI, MOSI, "GPIO10 (MOSI)"
    MISO, MISO, "GPIO9 (MISO)"
    IRQ, D12, GPIO12

.. tip::
    User reports and personal experiences have improved results if there is a capacitor of
    100 microfarads (+ another optional 0.1 microfarads capacitor for added stability) connected
    in parallel to the VCC and GND pins.
.. important::
    The nRF24L01's VCC pin is not 5V compliant. All other nRF24L01 pins *should* be 5V compliant,
    but it is safer to assume they are not.

Using The Examples
==================

See `examples <examples.html>`_ for testing certain features of this the library.
The examples were developed and tested on both Raspberry Pi and ItsyBitsy M4.
Pins have been hard coded in the examples for the corresponding device, so please adjust these
accordingly to your circuitpython device if necessary.

For an interactive REPL
---------------------------

All examples can be imported from within an interactive python REPL.

1. Make sure the examples are located in the current working directory.
   On CircuitPython devices, this will be the root directory of the CIRCUITPY drive.
2. Import everything from the desired example. The following code snippet demonstrates running the
   `Simple Test example <examples.html#simple-test>`_

   .. code-block:: python

       >>> from nrf24l01_simple_test import *
       Which radio is this? Enter '0' or '1'. Defaults to '0'
           nRF24L01 Simple test.
           Run slave() on receiver
           Run master() on transmitter
       >>> master()
       Transmission successful! Time to Transmit: 1563.904 us. Sent: 0.0
       Transmission successful! Time to Transmit: 1804.938 us. Sent: 0.01
       Transmission successful! Time to Transmit: 1690.977 us. Sent: 0.02
       Transmission successful! Time to Transmit: 1674.681 us. Sent: 0.03
       Transmission successful! Time to Transmit: 1729.976 us. Sent: 0.04

For CircuitPython devices
---------------------------

1. Copy the examples to the root directory of the CIRCUITPY device.
2. Rename the desired example file to ``main.py``.
3. If the REPL is not already running, then the example should start automatically.
   If the REPL is already running in interactive mode, then press :keys:`ctrl+D` to do a
   soft reset, and the example should start automatically.

For CPython in Linux
---------------------------

1. Clone the library repository, then navigate to the repository's example directory.

   .. code-block:: shell

       git clone https://github.com/2bndy5/CircuitPython_nRF24L01.git
       cd CircuitPython_nRF24L01/examples

2. Run the example as a normal python program

   .. code-block:: shell

       python3 nrf24l01_simple_test.py

What to purchase
=================

See the following links to Sparkfun or just google "nRF24L01+".

* `2.4GHz Transceiver IC - nRF24L01+ <https://www.sparkfun.com/products/690>`_
* `SparkFun Transceiver Breakout - nRF24L01+ <https://www.sparkfun.com/products/691>`_
* `SparkFun Transceiver Breakout - nRF24L01+ (RP-SMA) <https://www.sparkfun.com/products/705>`_

It is worth noting that you
generally want to buy more than 1 as you need 2 for testing -- 1 to send & 1 to receive and
vise versa. This library has been tested on a cheaply bought 6 pack from Amazon.com, but don't
take Amazon or eBay for granted! There are other wireless transceivers that are NOT compatible
with this library. For instance, the esp8266-01 (also sold in packs) is NOT compatible with
this library, but looks very similar to the nRF24L01+ and could lead to an accidental purchase.

.. warning::
    Beware, there are also `nrf24l01(+) clones and counterfeits`_ that may not work the same.

Power Stability
-------------------

If you're not using a dedicated 3V regulator to supply power to the nRF24L01,
then adding capacitor(s) (100 µF + an optional 0.1µF) in parallel (& as close
as possible) to the VCC and GND pins is highly recommended. Stabilizing the power
input provides significant performance increases. More finite details about the
nRF24L01 are available from the datasheet (referenced here in the documentation as the
`nRF24L01+ Specification Sheet <https://www.sparkfun.com/datasheets/
Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf>`_)

About the nRF24L01+PA+LNA modules
---------------------------------

You may find variants of the nRF24L01 transceiver that are marketed as "nRF24L01+PA+LNA".
These modules are distinct in the fact that they come with a detachable (SMA-type) antenna.
They employ additional circuitry with the antenna for enhanced Power Amplification (PA) and
Low Noise Amplification (LNA) features. While they boast greater range with the same
functionality, they are subject to a couple lesser known (and lesser advertised) drawbacks:

Additional requirements for the PA/LNA modules
**********************************************

These requirements are dependent on what manufacturer produced the radio module.

1. Needs a stronger power source. Below is a chart of advertised current requirements that many MCU
   boards' 3V regulators may not be able to provide (after supplying power to internal
   components).

   .. csv-table::
       :header: Specification, Value
       :widths: 10,5

       "Emission mode current(peak)", "115 mA"
       "Receive Mode current(peak)", "45 mA"
       "Power-down mode current", "4.2 µA"

   .. important:: These values may be different depending on what manufacturer produced the radio module.
       Please consult the manufacturer's specifications or datasheet.

2. Needs shielding from electromagnetic interference. Shielding usually works best when
   it has a path to ground (GND pin), but this connection to the GND pin is not required.

.. seealso::
    I have documented `Testing nRF24L01+PA+LNA module <troubleshooting.html#testing-nrf24l01-pa-lna-module>`_

nRF24L01(+) clones and counterfeits
-----------------------------------

This library does not directly support clones/counterfeits as there is no way for the library
to differentiate between an actual nRF24L01+ and a clone/counterfeit. To determine if your
purchase is a counterfeit, please contact the retailer you purchased from (also `reading this
article and its links might help
<https://hackaday.com/2015/02/23/nordic-nrf24l01-real-vs-fake/>`_). The most notable clone is the `Si24R1 <https://lcsc.com/product-detail/
RF-Transceiver-ICs_Nanjing-Zhongke-Microelectronics-Si24R1_C14436.html>`_. I could not find
the `Si24R1 datasheet <https://datasheet.lcsc.com/szlcsc/
1811142211_Nanjing-Zhongke-Microelectronics-Si24R1_C14436.pdf>`_ in english. Troubleshooting
the SI24R1 may require `replacing the onboard antenna with a wire
<https://forum.mysensors.org/post/96871>`_. Furthermore, the Si24R1 has different power
amplifier options as noted in the `RF_PWR section (bits 0 through 2) of the RF_SETUP register
(address 0x06) of the datasheet <https://datasheet.lcsc.com/szlcsc/
1811142211_Nanjing-Zhongke-Microelectronics-Si24R1_C14436.pdf#%5B%7B%22num%22%3A329%2C%22gen%22%3A0%7D%2C%7B%22name%22%3A%22XYZ%22%7D%2C0%2C755%2Cnull%5D>`_.
While the options' values differ from those identified by this library's API, the
underlying commands to configure those options are almost identical to the nRF24L01.
The Si24R1 is also famous for not supporting :py:attr:`~circuitpython_nrf24l01.rf24.RF24.auto_ack`
correctly because the designers "cloned" a typo from the 1\ :sup:`st` version of the nRF24L01
(non-plus) datasheet into the Si24R1 firmware. Other known clones include the bk242x (also known as
RFM7x).

.. seealso::
    `Read this article
    <https://ncrmnt.org/2021/01/03/nrf24l01-fixing-the-magic-finger-problem/>`_
    about using clones with missing capacitors (includes pictures).

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/2bndy5/CircuitPython_nRF24L01/blob/master/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.

Please review our :doc:`contributing` for details on the development workflow.

To initiate a discussion of idea(s), you need only open an issue on the aforementioned repository
(it doesn't have to be a bug report).


Future Project Ideas/Additions
------------------------------

The following are only ideas; they are not currently supported by this circuitpython library.

* `There's a few blog posts by Nerd Ralph demonstrating how to use the nRF24L01 via 2 or 3
  pins <http://nerdralph.blogspot.com/2015/05/nrf24l01-control-with-2-mcu-pins-using.
  html>`_ (uses custom bitbanging SPI functions and an external circuit involving a
  resistor and a capacitor)
* TCI/IP OSI layer, maybe something like `TMRh20's RF24Ethernet
  <http://nRF24.github.io/RF24Ethernet/>`_
* implement the Gazelle-based protocol used by the BBC micro-bit (`makecode.com's radio
  blocks <https://makecode.microbit.org/reference/radio>`_) Additional resources can be found at
  `the MicroPython firmware source code <https://github.com/bbcmicrobit/micropython/blob/master/source/microbit/modradio.cpp>`_
  and `its related documentation <https://microbit-micropython.readthedocs.io/en/latest/radio.html>`_.


Sphinx documentation
-----------------------

Please read our :doc:`contributing` for instrcutions on how to build the documentation.

Site Index
==========

* :ref:`genindex`
* :ref:`modindex`
