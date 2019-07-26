Introduction
============

.. image:: https://readthedocs.org/projects/circuitpython-nrf24l01/badge/?version=latest
    :target: https://circuitpython-nrf24l01.readthedocs.io/
    :alt: Documentation Status

.. image:: https://img.shields.io/discord/327254708534116352.svg
    :target: https://discord.gg/nBQh6qu
    :alt: Discord

.. image:: https://travis-ci.com/2bndy5/CircuitPython_nRF24L01.svg?branch=master
    :target: https://travis-ci.com/2bndy5/CircuitPython_nRF24L01
    :alt: Build Status

Circuitpython driver library for the nRF24L01 transceiver


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
.. note:: This library is not available on PyPI yet. Install documentation is included
   as a standard element. Stay tuned for PyPI availability!

.. todo:: Remove the above note if PyPI version is/will be available at time of release.
   If the library is not planned for PyPI, remove the entire 'Installing from PyPI' section.

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
.. image:: ../nRF24L01_Pinout.png

The nRF24L01 is controlled through SPI so there are 3 pins (SCK, MOSI, & MISO) that can only be connected to their counterparts on the microcontroller. The other 2 essential pins (CE & CSN) can be connected to any digital output pins. The following pinout is used in the example codes of this repo's example directory.

+------------+----------------+----------------+
|  nRF24L01  |  Raspberry Pi  |  ItsyBitsy M4  |
+============+================+================+
|    GND     |      GND       |       GND      |
+------------+----------------+----------------+
|    VCC     |       3V       |      3.3V      |
+------------+----------------+----------------+
|    CE      |  GPIO8 (CE0)   |       D7       |
+------------+----------------+----------------+
|    CSN     |     GPIO5      |       D5       |
+------------+----------------+----------------+
|    SCK     |      SCK       |       SCK      |
+------------+----------------+----------------+
|    MOSI    |     MOSI       |      MOSI      |
+------------+----------------+----------------+
|    MISO    |      MISO      |      MISO      |
+------------+----------------+----------------+
|    IRQ     |    not used    |    not used    |
+------------+----------------+----------------+

Usage Example
=============

See `examples/` for an example of how to use the library. Notice that there are 2 files in each scenario/folder; one file titled "pi_test.py" for testing on the raspberry pi, and another file titled "m4_test.py" for testing on an adafruit boards with atsamd51. This was developed and tested on both Raspberry Pi and ItsyBitsy M4. Pins have been hard coded in the examples for the corresponding device, so please adjust these accordingly to your circuitpython device if necessary.

To run the simple example, open a python terminal in this repo's example/simple folder and run the following:

.. code-block:: python
    
    # if using an adafruit feather, try using "from m4_test import *"
    >>> from pi_test import * 

        NRF24L01 test module.
        Run slave() on receiver, and master() on transmitter.

    >>> master()
    Sending:  0
    Sending:  1

Firstly import the necessary packages for your application.

.. code-block:: python

    # transmitted packet must be a byte array, thus the need for struct
    import time, board, struct, digitalio as dio
    from busio import SPI
    from circuitpython_nrf24l01.rf24 import RF24 
    # circuitpython_nrf24l01.rf24 is this library
    # RF24 is the main driver class

Define the nodes' virtual addresses/IDs for use on the radio's data pipes. Also define the SPI pin connections to the radio. Now you're ready to instantiate the NRF24L01 object 

.. note:: A word on pipes vs addresses vs channels.

    You should think of the pipes as RF pathways to a specified address. There are only six pipes on the nRF24L01, thus it can simultaneously talk to a maximum of 6 other nRF24L01 radios. However, you can use any 5 byte long address you can think of (as long as the last byte is unique among simultaneous braodcasting addresses), so you're not limited to just talking to the same 6 radios. Also the radio's channel is not be confused with the radio's pipes. Channel selection is a way of specifying a certain radio frequency. Channel defaults to 76 (like the arduino library), but options range from 0 to 127. The channel can be tweaked to find a less occupied frequency amongst Bluetooth & WiFi ambient signals.

.. warning::
    The RX pipe's address on the receiving node MUST match the TX pipe's address on the transmitting node. Also the specified channel MUST match on both tranceivers.

.. code-block:: python

    addresses = (b'1Node', b'2Node') # tx, rx node ID's

    ce = dio.DigitalInOut(board.D8) # pin AKA board.CE0
    cs = dio.DigitalInOut(board.D5)
    
    spi = SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO) # create instance of spi port
    nrf = RF24(spi, cs, ce) # create instance of the radio

To transmit firstly open the TX and RX pipes and set the desired enpoints' addresses, stop listening (puts radio in transmit mode) and send your packet (`buf`).

.. code-block:: python

    def master():
        nrf.open_tx_pipe(addresses[0])
        nrf.open_rx_pipe(1, addresses[1])
        nrf.stop_listening()

        i = 0

        while True:
            try:
                print("Sending:", i)
                # use struct to pack the data into a bytearray
                nrf.send(struct.pack('i', i)) 
            except OSError:
                print("sending failed")
            time.sleep(1) # send every 1s

To receive this data, again open the TX and RX pipes and set the desired endpoint addresses, then start listening for data. The `nrf.any()` method returns true when there is data ready to be received.

.. code-block:: python

    def slave():
        nrf.open_tx_pipe(addresses[1])
        nrf.open_rx_pipe(1, addresses[0])
        nrf.start_listening()

        while True:
            if nrf.any():
                while nrf.any():
                    buf = nrf.recv()
                    # use struct to unpack the bytearray into a tuple
                    # according to the data type format string
                    i = struct.unpack('i', buf) 
                    # format string 'i' matches a 4 byte iterable object 
                    # where the payload is stored (maximum is 32 bytes) 
                    # check out other available format strings: https://docs.python.org/2/library/struct.html#format-characters
                    print("Received:", i[0]) # prints the only integer in the resulting tuple.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/2bndy5/CircuitPython_nRF24L01/blob/master/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.

Sphinx documentation
-----------------------

Sphinx is used to build the documentation based on rST files and comments in the code. First,
install dependencies (feel free to reuse the virtual environment from above):

.. code-block:: shell

    python3 -m venv .env
    source .env/bin/activate
    pip install Sphinx sphinx-rtd-theme

Now, once you have the virtual environment activated:

.. code-block:: shell

    cd docs
    sphinx-build -E -W -b html . _build/html

This will output the documentation to ``docs/_build/html``. Open the index.html in your browser to
view them. It will also (due to -W) error out on any warning like Travis will. This is a good way to locally verify it will pass.
