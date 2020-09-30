
Troubleshooting info
====================

.. important:: The nRF24L01 has 3 key features that can be interdependent of each other. Their
    priority of dependence is as follows:

    1. `auto_ack` feature provides transmission verification by using the RX nRF24L01 to
       automatically and imediatedly send an acknowledgment (ACK) packet in response to freshly
       received payloads. `auto_ack` does not require `dynamic_payloads` to be enabled.
    2. `dynamic_payloads` feature allowing either TX/RX nRF24L01 to be able to send/receive
       payloads with their size written into the payloads' packet. With this disabled, both
       RX/TX nRF24L01 must use matching `payload_length` attributes. For `dynamic_payloads` to
       be enabled, the `auto_ack` feature must be enabled. Although, the `auto_ack` feature
       isn't required when the `dynamic_payloads` feature is disabled.
    3. `ack` feature allows the MCU to append a payload to the ACK packet, thus instant
       bi-directional communication. A transmitting ACK payload must be loaded into the
       nRF24L01's TX FIFO buffer (done using `load_ack()`) BEFORE receiving the payload that
       is to be acknowledged. Once transmitted, the payload is released from the TX FIFO
       buffer. This feature requires the `auto_ack` and `dynamic_payloads` features enabled.

Remeber that the nRF24L01's FIFO (first-in,first-out) buffer has 3 levels. This means that
there can be up to 3 payloads waiting to be read (RX) and up to 3 payloads waiting to be
transmit (TX).

With the `auto_ack` feature enabled, you get:

    * cyclic redundancy checking (`crc`) automatically enabled
    * to change amount of automatic re-transmit attempts and the delay time between them.
      See the `arc` and `ard` attributes.

.. note:: A word on pipes vs addresses vs channels.

    You should think of the data pipes as a "parking spot" for your payload. There are only six
    data pipes on the nRF24L01, thus it can simultaneously "listen" to a maximum of 6 other
    nRF24L01 radios. However, it can only "talk" to 1 other nRF24L01 at a time).

    The specified address is not the address of an nRF24L01 radio, rather it is more like a
    path that connects the endpoints. When assigning addresses to a data pipe, you can use any
    5 byte long address you can think of (as long as the first byte is unique among
    simultaneously broadcasting addresses), so you're not limited to communicating with only
    the same 6 nRF24L01 radios (more on this when we officially support "Multiciever" mode).

    Finnaly, the radio's channel is not be confused with the radio's pipes. Channel selection
    is a way of specifying a certain radio frequency (frequency = [2400 + channel] MHz).
    Channel defaults to 76 (like the arduino library), but options range from 0 to 125 --
    that's 2.4 GHz to 2.525 GHz. The channel can be tweaked to find a less occupied frequency
    amongst Bluetooth, WiFi, or other ambient signals that use the same spectrum of 
    frequencies.

.. warning:: 
    For successful transmissions, most of the endpoint trasceivers' settings/features must
    match. These settings/features include:

    * The RX pipe's address on the receiving nRF24L01 (passed to `open_rx_pipe()`) MUST match
      the TX pipe's address on the transmitting nRF24L01 (passed to `open_tx_pipe()`)
    * `address_length`
    * `channel`
    * `data_rate`
    * `dynamic_payloads`
    * `payload_length` only when `dynamic_payloads` is disabled
    * `auto_ack` on the recieving nRF24L01 must be enabled if `arc` is greater than 0 on the
      transmitting nRF24L01
    * custom `ack` payloads
    * `crc`

    In fact the only attributes that aren't required to match on both endpoint transceivers
    would be the identifying data pipe number (passed to `open_rx_pipe()` or `load_ack()`),
    `pa_level`, `arc`, & `ard` attributes. The ``ask_no_ack`` feature can be used despite the
    settings/features configuration (see `send()` & `write()` function parameters for more
    details).

About the lite version
======================

This library contains a "lite" version of ``rf24.py`` titled ``rf24_lite.py``. It has been
developed to save space on microcontrollers with limited amount of RAM and/or storage (like
boards using the ATSAMD21 M0). The following functionality has been removed from the lite
version:

    * `address()` removed.
    * `what_happened()` removed. However you can use the following function to dump all
      available registers' values (for advanced users):
      
      .. code-block:: python

          # let `nrf` be the instantiated RF24 object
          def dump_registers(end=0x1e):
              for i in range(end):
                  if i in (0xA, 0xB, 0x10):
                      print(hex(i), "=", nrf._reg_read_bytes(i))
                  elif i not in (0x18, 0x19, 0x1a, 0x1b):
                      print(hex(i), "=", hex(nrf._reg_read(i)))
    * `fifo()` removed.
    * `dynamic_payloads` applies to all pipes, not individual pipes.
    * `payload_length` applies to all pipes, not individual pipes.
    * `read_ack()` removed. This is deprecated on next major release anyway; use `recv()` 
      instead.
    * `load_ack()` is available, but it will not throw exceptions for malformed ``buf`` or
      invalid ``pipe_number`` parameters.
    * `crc` removed. 2-bytes encoding scheme (CRC16) is always enabled.
    * `auto_ack` removed. This is always enabled for all pipes. Pass ``ask_no_ack`` parameter
      as `True` to `send()` or `write()` to disable automatic acknowledgement for TX
      operations.
    * `is_lna_enabled` removed. This will always be enabled, and `pa_level` will not accept a
      `list` or `tuple`. This only affects certain boards anyway.
    * `rpd`, `start_carrier_wave()`, & `stop_carrier_wave()` removed. These only perform a
      test of the nRF24L01's hardware.
    * `CSN_DELAY` removed. This is hard-coded to 5 milliseconds
    * All comments and docstrings removed, meaning ``help()`` will not provide any specific
      information. Exception prompts have also been reduced and adjusted accordingly.
    * Cannot switch between different radio configurations using context manager (the `with`
      blocks). It is advised that only one `RF24` object be instantiated when RAM is limited
      (less than or equal to 32KB).
