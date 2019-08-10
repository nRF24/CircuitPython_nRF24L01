
.. If you created a package, create one automodule per module in the package.

.. If your library file(s) are nested in a directory (e.g. /adafruit_foo/foo.py)
.. use this format as the module name: "adafruit_foo.foo"

====================================
circuitpython_nrf24l01.rf24 - RF24
====================================

CircuitPython port of the nRF24L01 library from Micropython.
Original work by Damien P. George & Peter Hinch can be found `here <https://github.com/micropython/micropython/tree/master/drivers/nrf24l01>`_

The Micropython source has been rewritten to expose all the nRF24L01's features and for compatibilty with the Raspberry Pi and other Circuitpython compatible devices using Adafruit's `busio`, `adafruit_bus_device.spi_device`, and `digitalio`, modules.
Modified by Brendan Doherty, Rhys Thomas

* Author(s): Damien P. George, Peter Hinch, Rhys Thomas, Brendan Doherty

.. important:: The nRF24L01 has 3 key features that are very interdependent of each other. Their priority of dependence is as follows:

    1. `dynamic_payloads` feature allowing either TX/RX nRf24L01 to be able to send/receive payloads with their size written into the payloads' packet. With this disabled, both RX/TX nRF24L01 must use matching `payload_length` attributes.
    2. `auto_ack` feature provides transmission verification by imediatedly sending an acknowledgment (ACK) packet in response to freshly received payloads. `auto_ack` requires `dynamic_payloads` to be enabled.
    3. `ack` feature allows the MCU to append a payload to the ACK packet, thus instant bi-directional communication. A transmitting ACK payload must be loaded into the nRF24L01's TX FIFO buffer (done using `load_ack()`) BEFORE receiving the payload that is to be acknowledged. Once transmitted, the payload is released from the TX FIFO buffer. This feature obviously requires the `auto_ack` feature enabled.

Remeber that the nRF24L01's FIFO (first-in,first-out) buffer has 3 levels. This means that there can be up to 3 payloads waiting to be read (RX) and up to 3 payloads waiting to be transmit (TX).

With the `auto_ack` feature enabled you get:

    * cycle redundancy checking (`crc`) automatically enabled
    * to change amount of automatic re-transmit attempts and the delay time between them. See the `arc` and `ard` attributes.

.. note:: A word on pipes vs addresses vs channels.

    You should think of the data pipes as RF pathways to a specified address. There are only six data pipes on the nRF24L01, thus it can simultaneously "talk" to a maximum of 6 other nRF24L01 radios. When assigning addresses to a data pipe, you can use any 5 byte long address you can think of (as long as the last byte is unique among simultaneously broadcasting addresses), so you're not limited to communicating to the same 6 radios (more on this when we support "Multiciever" mode). Also the radio's channel is not be confused with the radio's pipes. Channel selection is a way of specifying a certain radio frequency (frequency = [2400 + channel] MHz). Channel defaults to 76 (like the arduino library), but options range from 0 to 125 -- that's 2.4 GHz to 2.525 GHz. The channel can be tweaked to find a less occupied frequency amongst (Bluetooth & WiFi) ambient signals.

.. warning:: For successful transmissions, most of the endpoint trasceivers' settings/features must match. These settings/features includes:

    * The RX pipe's address on the receiving nRF24L01 MUST match the TX pipe's address on the transmitting nRF24L01
    * `address_length`
    * `channel`
    * `data_rate`
    * `dynamic_payloads`
    * `payload_length` only when `dynamic_payloads` is disabled
    * `auto_ack`
    * custom `ack` payloads
    * `crc`

    In fact the only attributes that aren't required to match on both endpoint trasceivers would be the `pa_level`, `arc`, & `ard` attributes. The ``ask_no_ack`` feature can be used despite the settings/features configuration (see `send()` & `write()` function parameters for more details).

.. automodule:: circuitpython_nrf24l01.rf24
    :members:
