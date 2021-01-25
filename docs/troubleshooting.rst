
Troubleshooting info
====================

Attribute dependency
********************

The nRF24L01 has 3 key features.

1. `auto_ack` feature provides transmission verification by using the RX nRF24L01 to
   automatically and immediatedly send an acknowledgment (ACK) packet in response to
   received payloads. `auto_ack` does not require `dynamic_payloads` to be enabled.

   .. note:: With the `auto_ack` feature enabled, you get:

       * cyclic redundancy checking (`crc`) automatically enabled
       * to change amount of automatic re-transmit attempts and the delay time between
         them. See the `arc` and `ard` attributes.
2. `dynamic_payloads` feature allows either TX/RX nRF24L01 to be able to send/receive
   payloads with their size written into the payloads' packet. With this disabled, both
   RX/TX nRF24L01 must use matching `payload_length` attributes. `dynamic_payloads`
   does not require `auto_ack` to be enabled.
3. `ack` feature allows the MCU to append a payload to the ACK packet, thus instant
   bi-directional communication. A transmitting ACK payload must be loaded into the
   nRF24L01's TX FIFO buffer (done using `load_ack()`) BEFORE receiving the payload that
   is to be acknowledged. Once transmitted, the payload is released from the TX FIFO
   buffer.

   .. important:: This `ack` feature requires the `auto_ack` and `dynamic_payloads`
       features enabled.

FIFO Capacity
*************

Remeber that the nRF24L01's FIFO (First-In, First-Out) buffers have 3 levels. This means that
there can be up to 3 payloads waiting to be read (RX) and up to 3 payloads waiting to be
transmit (TX). Notice there are seperate FIFO buffers sending & receiving (respectively mentioned
in this documentation as TX FIFO & RX FIFO).

Each of the 3 levels in the FIFO buffers can only store a *maximum* of 32 bytes. If you receive 2 payloads with a length of 4 bytes each, then there is only 1 level of the RX FIFO buffers left unoccupied.

Pipes vs Addresses vs Channels
******************************

.. hint:: Please review the `Multiceiver example <examples.html#multiceiver-example>`_ as a
    demonstration of proper addressing using all pipes (on the same channel).

Pipes
-----

You should think of the data pipes as a "parking spot" for your payload. There are only six
data pipes on the nRF24L01, thus it can simultaneously "listen" to a maximum of 6 other
nRF24L01 radios. However, it can only "talk" to 1 other nRF24L01 at a time.

Addresses
---------

The specified address is not the address of an nRF24L01 radio, rather it is more like a
path that connects the endpoints. When assigning addresses to a data pipe, you can use any
5 byte long address you can think of (as long as the first byte of the `bytearray` is unique
among simultaneously broadcasting addresses), so you're not limited to communicating with only
the same 6 nRF24L01 radios.

Channels
--------

Finnaly, the radio's channel is not be confused with the radio's pipes. Channel selection
is a way of specifying a certain radio frequency (frequency = [2400 + channel] MHz).
Channel defaults to 76 (like the arduino library), but options range from 0 to 125 --
that's 2.4 GHz to 2.525 GHz. The channel can be tweaked to find a less occupied frequency
amongst Bluetooth, WiFi, or other ambient signals that use the same spectrum of
frequencies.

Settings that must Match
************************

For successful transmissions, most of the endpoint trasceivers' settings/features must
match. These settings/features include:

* The RX pipe's address on the receiving nRF24L01 (passed to `open_rx_pipe()`) MUST match
  the TX pipe's address on the transmitting nRF24L01 (passed to `open_tx_pipe()`)
* `address_length`
* :py:attr:`~circuitpython_nrf24l01.rf24.RF24.channel`
* `data_rate`
* `dynamic_payloads`
* `payload_length` only when `dynamic_payloads` is disabled
* `auto_ack`
* custom `ack` payloads
* `crc`

Settings that do not need to Match
----------------------------------

In fact the only attributes that aren't required to match on both endpoint transceivers
would be

* the identifying data pipe number passed to `open_rx_pipe()` or `load_ack()` (as long as the
  corresponding addresses match)
* `pa_level`
* `arc`
* `ard`

The ``ask_no_ack`` feature can be used despite the
settings/features configuration (see :py:meth:`~circuitpython_nrf24l01.rf24.RF24.send()` &
`write()` function parameters for more details).

About the lite version
======================

.. versionadded:: 1.2.0

This library contains a "lite" version of ``rf24.py`` titled ``rf24_lite.py``. It has been
developed to save space on microcontrollers with limited amount of RAM and/or storage (like
boards using the ATSAMD21 M0). The following functionality has been removed from the lite
version:

* The `FakeBLE` class is not compatible with the ``rf24_lite.py`` module.
* `is_plus_variant` is removed, meaning the
  lite version is not compatibility with the older non-plus variants of the nRF24L01.
* `address()` removed.
* `print_details()` removed. However you can use the following function to dump all available
  registers' values (for advanced users):

  .. code-block:: python

      # let `nrf` be the instantiated RF24 object
      def dump_registers(end=0x1e):
          for i in range(end):
              if i in (0xA, 0xB, 0x10):
                  print(hex(i), "=", nrf._reg_read_bytes(i))
              elif i not in (0x18, 0x19, 0x1a, 0x1b):
                  print(hex(i), "=", hex(nrf._reg_read(i)))
* `dynamic_payloads` applies to all pipes, not individual pipes. This attribute will return
  a `bool` instead of an `int`. `set_dynamic_payloads()` and `get_dynamic_payloads()` have
  been removed.
* `payload_length` applies to all pipes, not individual pipes. `set_payload_length()` and
  `get_payload_length()` have been removed.
* `load_ack()` is available, but it will not throw exceptions for malformed ``buf`` or
  invalid ``pipe_number`` parameters. Rather any call to `load_ack()` with invalid
  parameters will have no affect on the TX FIFO.
* `crc` removed. 2-bytes encoding scheme (CRC16) is always enabled.
* `auto_ack` removed. This is always enabled for all pipes. Pass ``ask_no_ack`` parameter
  as `True` to :py:meth:`~circuitpython_nrf24l01.rf24.RF24.send()` or `write()` to disable
  automatic acknowledgement for TX operations.
* `is_lna_enabled` removed as it only affects non-plus variants of the nRF24L01.
* `pa_level` is available, but it will not accept a `list` or `tuple`.
* `start_carrier_wave()`, & `stop_carrier_wave()` removed. These only perform a
  test of the nRF24L01's hardware. `rpd` is still available.
* All comments and docstrings removed, meaning ``help()`` will not provide any specific
  information. Exception prompts have also been reduced and adjusted accordingly.
* Cannot switch between different radio configurations using context manager (the `with`
  blocks). It is advised that only one `RF24` object be instantiated when RAM is limited
  (less than or equal to 32KB).
* `last_tx_arc` attribute removed because it is only meant for troubleshooting.
* `allow_ask_no_ack` attribute removed because it is only provided for the Si24R1
  chinese clone.
* `set_auto_retries()` & `get_auto_retries()` removed. Use `ard` & `arc` attributes instead.

Testing nRF24L01+PA+LNA module
=================================

The following are semi-successful test results using a nRF24L01+PA+LNA module:

The Setup
*********************************

I wrapped the PA/LNA module with electrical tape and then foil around that (for shielding)
while being very careful to not let the foil touch any current carrying parts (like the GPIO pins and the soldier joints for the antenna mount). Then I wired up a PA/LNA module with a 3V
regulator (L4931 with a 2.2 µF capacitor between V\ :sub:`out` & GND) using my ItsyBitsy M4
5V (USB) pin going directly to the L4931 V\ :sub:`in` pin. The following are experiences from
running simple, ack, & stream examples with a reliable nRF24L01+ (no PA/LNA) on the other end (driven by a Raspberry Pi 2):

Results (ordered by :py:attr:`~circuitpython_nrf24l01.rf24.RF24.pa_level` settings)
***********************************************************************************

* 0 dBm: ``master()`` worked the first time (during simple example) then continuously failed
  (during all examples). ``slave()`` worked on simple & stream examples, but the opposing
  ``master()`` node reporting that ACK packets (without payloads) were **not** received from
  the PA/LNA module; ``slave()`` failed to send ACK packet payloads during the ack example.
* -6 dBm: ``master()`` worked consistently on simple, ack, & stream example. ``slave()`` worked
  reliably on simple & stream examples, but failed to transmit **any** ACK packet payloads in
  the ack example.
* -12 dBm: ``master()`` worked consistently on simple, ack, & stream example. ``slave()``
  worked reliably on simple & stream examples, but failed to transmit **some** ACK packet
  payloads in the ack example.
* -18 dBm: ``master()`` worked consistently on simple, ack, & stream example. ``slave()``
  worked reliably on simple, ack, & stream examples, meaning **all** ACK packet payloads were
  successfully transmit in the ack example.

I should note that without shielding the PA/LNA module and using the L4931 3V regulator,
no TX transmissions got sent (including ACK packets for the `auto_ack` feature).

Conclusion
*********************************

The PA/LNA modules seem to require quite a bit more power to transmit. The L4931 regulator
that I used in the tests boasts a 300 mA current limit and a typical current of 250 mA.
While the ItsyBitsy M4 boasts a 500 mA max, it would seem that much of that is consumed
internally. Since playing with the `pa_level` is a current saving hack (as noted in the
datasheet), I can only imagine that a higher power 3V regulator may enable sending
transmissions (including ACK packets -- with or without ACK payloads attached) from PA/LNA
modules using higher `pa_level` settings. More testing is called for, but I don't have an
oscilloscope to measure the peak current draws.
