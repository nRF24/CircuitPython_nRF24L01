
.. If you created a package, create one automodule per module in the package.

.. If your library file(s) are nested in a directory (e.g. /adafruit_foo/foo.py)
.. use this format as the module name: "adafruit_foo.foo"

.. currentmodule:: circuitpython_nrf24l01.rf24

RF24 class
==============

Troubleshooting info
--------------------

.. important:: The nRF24L01 has 3 key features that can be interdependent of each other. Their
    priority of dependence is as follows:

    1. `dynamic_payloads` feature allowing either TX/RX nRF24L01 to be able to send/receive
       payloads with their size written into the payloads' packet. With this disabled, both RX/TX
       nRF24L01 must use matching `payload_length` attributes.
    2. `auto_ack` feature provides transmission verification by using the RX nRF24L01 to
       automatically and imediatedly send an acknowledgment (ACK) packet in response to freshly
       received payloads. `auto_ack` does not require `dynamic_payloads` to be enabled.
    3. `ack` feature allows the MCU to append a payload to the ACK packet, thus instant
       bi-directional communication. A transmitting ACK payload must be loaded into the nRF24L01's
       TX FIFO buffer (done using `load_ack()`) BEFORE receiving the payload that is to be
       acknowledged. Once transmitted, the payload is released from the TX FIFO buffer. This
       feature requires the `auto_ack` and `dynamic_payloads` features enabled.

Remeber that the nRF24L01's FIFO (first-in,first-out) buffer has 3 levels. This means that there
can be up to 3 payloads waiting to be read (RX) and up to 3 payloads waiting to be transmit (TX).

With the `auto_ack` feature enabled, you get:

    * cyclic redundancy checking (`crc`) automatically enabled
    * to change amount of automatic re-transmit attempts and the delay time between them. See the
      `arc` and `ard` attributes.

.. note:: A word on pipes vs addresses vs channels.

    You should think of the data pipes as a "parking spot" for your payload. There are only six
    data pipes on the nRF24L01, thus it can simultaneously "listen" to a maximum of 6 other nRF24L01
    radios. However, it can only "talk" to 1 other nRF24L01 at a time).

    The specified address is not the address of an nRF24L01 radio, rather it is more like a path
    that connects the endpoints. When assigning addresses to a data pipe, you can use any 5 byte
    long address you can think of (as long as the first byte is unique among simultaneously
    broadcasting addresses), so you're not limited to communicating with only the same 6 nRF24L01
    radios (more on this when we officially support "Multiciever" mode).

    Finnaly, the radio's channel is not be confused with the radio's pipes. Channel selection is a
    way of specifying a certain radio frequency (frequency = [2400 + channel] MHz). Channel
    defaults to 76 (like the arduino library), but options range from 0 to 125 -- that's 2.4
    GHz to 2.525 GHz. The channel can be tweaked to find a less occupied frequency amongst
    Bluetooth, WiFi, or other ambient signals that use the same spectrum of frequencies.

.. warning:: For successful transmissions, most of the endpoint trasceivers' settings/features must
    match. These settings/features include:

    * The RX pipe's address on the receiving nRF24L01 (passed to `open_rx_pipe()`) MUST match the
      TX pipe's address on the transmitting nRF24L01 (passed to `open_tx_pipe()`)
    * `address_length`
    * `channel`
    * `data_rate`
    * `dynamic_payloads`
    * `payload_length` only when `dynamic_payloads` is disabled
    * `auto_ack` on the recieving nRF24L01 must be enabled if `arc` is greater than 0 on the
      transmitting nRF24L01
    * custom `ack` payloads
    * `crc`

    In fact the only attributes that aren't required to match on both endpoint transceivers would
    be the identifying data pipe number (passed to `open_rx_pipe()` or `load_ack()`), `pa_level`,
    `arc`, & `ard` attributes. The ``ask_no_ack`` feature can be used despite the settings/features
    configuration (see `send()` & `write()` function
    parameters for more details).

Basic API
---------

Contrusctor
******************

.. autoclass:: circuitpython_nrf24l01.rf24.RF24
    :no-members:

address_length
******************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.address_length

open_tx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.open_tx_pipe

close_rx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.close_rx_pipe

open_rx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.open_rx_pipe

listen
******************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.listen

any()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.any

recv()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.recv

send()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.send

Advanced API
------------

what_happened()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.what_happened

dynamic_payloads
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.dynamic_payloads

payload_length
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.payload_length

auto_ack
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.auto_ack

arc
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.arc

ard
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.ard

ack
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.ack

load_ack()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.load_ack

read_ack()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.read_ack

irq_dr
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_dr

irq_df
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_df

irq_ds
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_ds

clear_status_flags()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.clear_status_flags

interrupt_config()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.interrupt_config

data_rate
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.data_rate

channel
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.channel

crc
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.crc

power
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.power

pa_level
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.pa_level

tx_full
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.tx_full

rpd
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.rpd

update()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.update

resend()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.resend

write()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.write

flush_rx()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.flush_rx

flush_tx()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.flush_tx

fifo()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.fifo

pipe()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.pipe

address()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.address

Sniffer
=======
    .. automodule:: circuitpython_nrf24l01.sniffer
        :members:

Logitech Mouse
==============

    .. automodule:: circuitpython_nrf24l01.logitech_mouse
        :members:
