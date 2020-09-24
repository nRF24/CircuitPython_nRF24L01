

.. currentmodule:: circuitpython_nrf24l01.rf24

.. |irq note| replace::  parameter as `True` to `clear_status_flags()` and reset this. As this
    is a virtual representation of the interrupt event, this attribute will always be updated
    despite what the actual IRQ pin is configured to do about this event.
    
.. |update manually| replace:: Calling this does not execute an SPI transaction. It only
    exposes that latest data contained in the STATUS byte that's always returned from any
    other SPI transactions. Use the `update()` function to manually refresh this data when
    needed.

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

RF24 class
==============

Basic API
---------

Contructor
******************

.. autoclass:: circuitpython_nrf24l01.rf24.RF24
    :no-members:

    This class aims to be compatible with other devices in the nRF24xxx product line that
    implement the Nordic proprietary Enhanced ShockBurst Protocol (and/or the legacy
    ShockBurst Protocol), but officially only supports (through testing) the nRF24L01 and
    nRF24L01+ devices.

    :param ~busio.SPI spi: The object for the SPI bus that the nRF24L01 is connected to.

        .. tip:: This object is meant to be shared amongst other driver classes (like
            adafruit_mcp3xxx.mcp3008 for example) that use the same SPI bus. Otherwise, multiple
            devices on the same SPI bus with different spi objects may produce errors or
            undesirable behavior.
    :param ~digitalio.DigitalInOut csn: The digital output pin that is connected to the nRF24L01's
        CSN (Chip Select Not) pin. This is required.
    :param ~digitalio.DigitalInOut ce: The digital output pin that is connected to the nRF24L01's
        CE (Chip Enable) pin. This is required.
    :param int spi_frequency: Specify which SPI frequency to use on the SPI bus.This parameter
        only applies to the instantiated object and is made persistent via
        :py:class:`~adafruit_bus_device.spi_device`.

open_tx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.open_tx_pipe

    :param bytearray address: The virtual address of the receiving nRF24L01. The address
        specified here must match the address set to one of the RX data pipes of the receiving
        nRF24L01. The existing address can be altered by writting a bytearray with a length
        less than 5. The nRF24L01 will use the first `address_length` number of bytes for the
        RX address on the specified data pipe.

    .. note:: There is no option to specify which data pipe to use because the nRF24L01 only
        uses data pipe 0 in TX mode. Additionally, the nRF24L01 uses the same data pipe (pipe
        0) for receiving acknowledgement (ACK) packets in TX mode when the `auto_ack` attribute
        is enabled for data pipe 0. Thus, RX pipe 0 is appropriated with the TX address
        (specified here) when `auto_ack` is enabled for data pipe 0.

close_rx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.close_rx_pipe

    :param int pipe_number: The data pipe to use for RX transactions. This must be in range
        [0, 5]. Otherwise a `ValueError` exception is thrown.

open_rx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.open_rx_pipe

    If `dynamic_payloads` attribute is disabled for the specifed data pipe, then the
    `payload_length` attribute is used to define the expected length of the static RX payload
    on the specified data pipe.

    :param int pipe_number: The data pipe to use for RX transactions. This must be in range
        [0, 5]. Otherwise a `ValueError` exception is thrown.
    :param bytearray address: The virtual address to the receiving nRF24L01. If using a
        ``pipe_number`` greater than 1, then only the MSByte of the address is written, so make
        sure MSByte (first character) is unique among other simultaneously receiving addresses.
        The existing address can be altered by writing a bytearray with a length less than 5.
        The nRF24L01 will use the first `address_length` number of bytes for the RX address on
        the specified data pipe.

    .. note:: The nRF24L01 shares the addresses' last 4 LSBytes on data pipes 2 through
        5. These shared LSBytes are determined by the address set to data pipe 1.

listen
******************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.listen

    Setting this attribute incorporates the proper transitioning to/from RX mode as it involves
    playing with the `power` attribute and the nRF24L01's CE pin. This attribute does not power
    down the nRF24L01, but will power it up when needed; use `power` attribute set to `False`
    to put the nRF24L01 to sleep.

    A valid input value is a `bool` in which:

        - `True` enables RX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications
          Sheet <https://www.sparkfun.com/datasheets/Components/SMD/
          nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this attribute
          flushes the RX FIFO, clears the `irq_dr` status flag, and puts nRF24L01 in power up
          mode. Notice the CE pin is be held HIGH during RX mode.
        - `False` disables RX mode. As mentioned in above link, this puts nRF24L01's power in
          Standby-I (CE pin is LOW meaning low current & no transmissions) mode which is ideal
          for post-reception work. Disabing RX mode doesn't flush the RX/TX FIFO buffers, so
          remember to flush your 3-level FIFO buffers when appropriate using `flush_tx()` or
          `flush_rx()` (see also the `recv()` function).

any()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.any

    :returns:
        - `int` of the size (in bytes) of an available RX payload (if any).
        - ``0`` if there is no payload in the RX FIFO buffer.

recv()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.recv

    This function can also be used to fetch the last ACK packet's payload if `ack` is enabled.
    
    :param int length: An optional parameter to specify how many bytes to read from the RX
        FIFO buffer. This parameter is not contrained in any way.
        
            - If this parameter is less than the length of the first available payload in the
              RX FIFO buffer, then the payload will remain in the RX FIFO buffer until the
              entire payload is fetched by this function.
            - If this parameter is greater than the next available payload's length, then
              additional data from other payload(s) in the RX FIFO buffer are returned.

            .. note::
                The nRF24L01 will repeatedly return the last byte fetched from the RX FIFO
                buffer when there is no data to return (even if the RX FIFO is empty). Be
                aware that a payload is only removed from the RX FIFO buffer when the entire
                payload has been fetched by this function. Notice that this function always
                starts reading data from the first byte of the first available payload (if
                any) in the RX FIFO buffer.
    :returns:
        A `bytearray` of the RX payload data or `None` if there is no payload. If the
        ``length`` parameter is not specified, then one of the following two scenarios is
        applied.

        - If the `dynamic_payloads` attribute is disabled, then the returned bytearray's
          length is equal to the user defined `payload_length` attribute for the data pipe
          that received the payload.
        - If the `dynamic_payloads` attribute is enabled, then the returned bytearray's length
          is equal to the payload's length

send()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.send

    :returns:
        - `list` if a list or tuple of payloads was passed as the ``buf`` parameter. Each item
          in the returned list will contain the returned status for each corresponding payload
          in the list/tuple that was passed. The return statuses will be in one of the
          following forms:
        - `False` if transmission fails. Transmission failure can only be detected if `arc`
          is greater than ``0``.
        - `True` if transmission succeeds.
        - `bytearray` or `None` when the `ack` attribute is `True`. Because the payload
          expects a responding custom ACK payload, the response is returned (upon successful
          transmission) as a `bytearray` (or `None` if ACK payload is empty)

    :param bytearray,list,tuple buf: The payload to transmit. This bytearray must have a
        length in range [1, 32], otherwise a `ValueError` exception is thrown. This can
        also be a list or tuple of payloads (`bytearray`); in which case, all items in the
        list/tuple are processed for consecutive transmissions.

        - If the `dynamic_payloads` attribute is disabled for data pipe 0 and this bytearray's
          length is less than the `payload_length` attribute for pipe 0, then this bytearray
          is padded with zeros until its length is equal to the `payload_length` attribute for
          pipe 0.
        - If the `dynamic_payloads` attribute is disabled for data pipe 0 and this bytearray's
          length is greater than `payload_length` attribute for pipe 0, then this bytearray's
          length is truncated to equal the `payload_length` attribute for pipe 0.
    :param bool ask_no_ack: Pass this parameter as `True` to tell the nRF24L01 not to wait for
        an acknowledgment from the receiving nRF24L01. This parameter directly controls a
        ``NO_ACK`` flag in the transmission's Packet Control Field (9 bits of information
        about the payload). Therefore, it takes advantage of an nRF24L01 feature specific to
        individual payloads, and its value is not saved anywhere. You do not need to specify
        this for every payload if the `arc` attribute is disabled, however setting this
        parameter to `True` will work despite the `arc` attribute's setting.

        .. note:: Each transmission is in the form of a packet. This packet contains sections
            of data around and including the payload. `See Chapter 7.3 in the nRF24L01
            Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1136318>`_ for more
            details.
    :param int force_retry: The number of brute-force attempts to `resend()` a failed
        transmission. Default is 0. This parameter has no affect on transmissions if `arc` is
        ``0`` or ``ask_no_ack`` parameter is set to `True`. Each re-attempt still takes
        advantage of `arc` & `ard` attributes. During multi-payload processing, this
        parameter is meant to slow down CircuitPython devices just enough for the Raspberry
        Pi to catch up (due to the Raspberry Pi's seemingly slower SPI speeds). See also
        notes on `resend()` as using this parameter carries the same implications documented
        there. This parameter has no effect if the ``ask_no_ack`` parameter is set to `True`
        or if `arc` is disabled.

    .. tip:: It is highly recommended that `arc` attribute is enabled (greater than ``0``)
        when sending multiple payloads. Test results with the `arc` attribute disabled were
        rather poor (less than 79% received by a Raspberry Pi). This same advice applies to
        the ``ask_no_ack`` parameter (leave it as `False` for multiple payloads).
    .. warning::  The nRF24L01 will block usage of the TX FIFO buffer upon failed
        transmissions. Failed transmission's payloads stay in TX FIFO buffer until the MCU
        calls `flush_tx()` and `clear_status_flags()`. Therefore, this function will discard
        failed transmissions' payloads when sending a list or tuple of payloads, so it can
        continue to process through the list/tuple even if any payload fails to be
        acknowledged.

Advanced API
------------

what_happened()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.what_happened

    Some information may be irrelevant depending on nRF24L01's state/condition.

    :prints:

        - ``Channel`` The current setting of the `channel` attribute
        - ``RF Data Rate`` The current setting of the RF `data_rate` attribute.
        - ``RF Power Amplifier`` The current setting of the `pa_level` attribute.
        - ``CRC bytes`` The current setting of the `crc` attribute
        - ``Address length`` The current setting of the `address_length` attribute
        - ``TX Payload lengths`` The current setting of the `payload_length` attribute for TX
          operations (concerning data pipe 0)
        - ``Auto retry delay`` The current setting of the `ard` attribute
        - ``Auto retry attempts`` The current setting of the `arc` attribute
        - ``Packets lost on current channel`` Total amount of packets lost (transmission
          failures). This only resets when the `channel` is changed. This count will
          only go up 15.
        - ``Retry attempts made for last transmission`` Amount of attempts to re-transmit
          during last transmission (resets per payload)
        - ``IRQ - Data Ready`` The current setting of the IRQ pin on "Data Ready" event
        - ``IRQ - Data Sent`` The current setting of the IRQ pin on "Data Sent" event
        - ``IRQ - Data Fail`` The current setting of the IRQ pin on "Data Fail" event
        - ``Data Ready`` Is there RX data ready to be read? (state of the `irq_dr` flag)
        - ``Data Sent`` Has the TX data been sent? (state of the `irq_ds` flag)
        - ``Data Failed`` Has the maximum attempts to re-transmit been reached?
          (state of the `irq_df` flag)
        - ``TX FIFO full`` Is the TX FIFO buffer full? (state of the `tx_full` flag)
        - ``TX FIFO empty`` Is the TX FIFO buffer empty?
        - ``RX FIFO full`` Is the RX FIFO buffer full?
        - ``RX FIFO empty`` Is the RX FIFO buffer empty?
        - ``Custom ACK payload`` Is the nRF24L01 setup to use an extra (user defined) payload
          attached to the acknowledgment packet? (state of the `ack` attribute)
        - ``Ask no ACK`` Is the nRF24L01 setup to transmit individual packets that don't
          require acknowledgment?
        - ``Automatic Acknowledgment`` The status of the `auto_ack` feature. If this value is a
          binary representation, then each bit represents the feature's status for each pipe.
        - ``Dynamic Payloads`` The status of the `dynamic_payloads` feature. If this value is a
          binary representation, then each bit represents the feature's status for each pipe.
        - ``Primary Mode`` The current mode (RX or TX) of communication of the nRF24L01 device.
        - ``Power Mode`` The power state can be Off, Standby-I, Standby-II, or On.

    :param bool dump_pipes: `True` appends the output and prints:

        - the current address used for TX transmissions. This value is the entire content of
          the nRF24L01's register about the TX address (despite what `address_length` is set
          to).
        - ``Pipe [#] ([open/closed]) bound: [address]`` where ``#`` represent the pipe number,
          the ``open/closed`` status is relative to the pipe's RX status, and ``address`` is
          the full value stored in the nRF24L01's RX address registers (despite what
          `address_length` is set to.
        - if the pipe is open, then the output also prints ``expecting [X] byte static
          payloads`` where ``X`` is the `payload_length` (in bytes) the pipe is setup to
          receive when `dynamic_payloads` is disabled for that pipe.

        Default is `False` and skips this extra information.

load_ack()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.load_ack

    This payload will then be appended to the automatic acknowledgment
    (ACK) packet that is sent when fresh data is received on the specified pipe. See
    `read_ack()` on how to fetch a received custom ACK payloads.

    :param bytearray buf: This will be the data attached to an automatic ACK packet on the
        incoming transmission about the specified ``pipe_number`` parameter. This must have a
        length in range [1, 32] bytes, otherwise a `ValueError` exception is thrown. Any ACK
        payloads will remain in the TX FIFO buffer until transmitted successfully or
        `flush_tx()` is called.
    :param int pipe_number: This will be the pipe number to use for deciding which
        transmissions get a response with the specified ``buf`` parameter's data. This number
        must be in range [0, 5], otherwise a `ValueError` exception is thrown.

    :returns: `True` if payload was successfully loaded onto the TX FIFO buffer. `False` if it
        wasn't because TX FIFO buffer is full.

    .. note:: this function takes advantage of a special feature on the nRF24L01 and needs to
        be called for every time a customized ACK payload is to be used (not for every
        automatic ACK packet -- this just appends a payload to the ACK packet). The `ack`,
        `auto_ack`, and `dynamic_payloads` attributes are also automatically enabled by this
        function when necessary.

    .. tip:: The ACK payload must be set prior to receiving a transmission. It is also worth
        noting that the nRF24L01 can hold up to 3 ACK payloads pending transmission. Using this
        function does not over-write existing ACK payloads pending; it only adds to the queue
        (TX FIFO buffer) if it can. Use `flush_tx()` to discard unused ACK payloads when done
        listening.

read_ack()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.read_ack

    This function was internally called from a blocking `send()` call if the `ack` attribute
    is enabled. Alternatively, this function can be called directly in case of calling the
    non-blocking `write()` function during asychronous applications. This function is an alias
    of `recv()` and remains for backward compatibility with older versions of this library.

    .. note:: See also the `ack`, `dynamic_payloads`, and `auto_ack` attributes as they must be
        enabled to use custom ACK payloads.

    .. warning:: This function will be deprecated on next major release. Use `recv()` instead. 

irq_dr
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_dr

    .

    :Returns:
        
        - `True` represents Data is in the RX FIFO buffer
        - `False` represents anything depending on context (state/condition of FIFO buffers);
          usually this means the flag's been reset.

    Pass ``dataReady`` |irq note|

    |update manually|

irq_df
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_df

    .

    :Returns:
        
        - `True` signifies the nRF24L01 attemped all configured retries
        - `False` represents anything depending on context (state/condition); usually this
          means the flag's been reset.

    Pass ``dataFail`` |irq note|

    |update manually|

irq_ds
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_ds

    .

    :Returns:
        
        - `True` represents a successful transmission
        - `False` represents anything depending on context (state/condition of FIFO buffers);
          usually this means the flag's been reset.

    Pass ``dataSent`` |irq note|

    |update manually|

clear_status_flags()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.clear_status_flags

    Internally, this is automatically called by `send()`, `write()`, `recv()`, and when
    `listen` changes from `False` to `True`.

    :param bool data_recv: specifies wheather to clear the "RX Data Ready" flag.
    :param bool data_sent: specifies wheather to clear the "TX Data Sent" flag.
    :param bool data_fail: specifies wheather to clear the "Max Re-transmit reached" flag.

    .. note:: Clearing the ``data_fail`` flag is necessary for continued transmissions from the
        nRF24L01 (locks the TX FIFO buffer when `irq_df` is `True`) despite wheather or not the
        MCU is taking advantage of the interrupt (IRQ) pin. Call this function only when there
        is an antiquated status flag (after you've dealt with the specific payload related to
        the staus flags that were set), otherwise it can cause payloads to be ignored and
        occupy the RX/TX FIFO buffers. See `Appendix A of the nRF24L01+ Specifications Sheet
        <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1047965>`_ for an outline of
        proper behavior.

power
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.power

    This is exposed for convenience.

    - `False` basically puts the nRF24L01 to sleep (AKA power down mode) with ultra-low
      current consumption. No transmissions are executed when sleeping, but the nRF24L01 can
      still be accessed through SPI. Upon instantiation, this driver class puts the nRF24L01
      to sleep until the MCU invokes RX/TX transmissions. This driver class doesn't power down
      the nRF24L01 after RX/TX transmissions are complete (avoiding the required power up/down
      150 µs wait time), that preference is left to the application.
    - `True` powers up the nRF24L01. This is the first step towards entering RX/TX modes (see
      also `listen` attribute). Powering up is automatically handled by the `listen` attribute
      as well as the `send()` and `write()` functions.

    .. note:: This attribute needs to be `True` if you want to put radio on Standby-II (highest
        current consumption) or Standby-I (moderate current consumption) modes, which Standby
        mode depends on the state of the CE pin. TX transmissions are only executed during
        Standby-II by calling `send()` or `write()`. RX transmissions are received during
        Standby-II by setting `listen` attribute to `True` (see `Chapter 6.1.2-7 of the
        nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132980>`_). After using
        `send()` or setting `listen` to `False`, the nRF24L01 is left in Standby-I mode (see
        also notes on the `write()` function).

tx_full
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.tx_full

    .
    
    |update manually|

    :returns:
        
        - `True` for TX FIFO buffer is full
        - `False` for TX FIFO buffer is not full. This doesn't mean the TX FIFO buffer is
          empty.

update()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.update

    Refreshing the status byte is vital to checking status of the interrupt flags, RX pipe
    number related to current RX payload, and if the TX FIFO buffer is full. This function
    returns nothing, but internally updates the `irq_dr`, `irq_ds`, `irq_df`, `pipe`, and
    `tx_full` attributes. Internally this is a helper function to `send()`, and `resend()`
    functions.

resend()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.resend

    All returned data from this function follows the same patttern that `send()` returns with
    the added condition that this function will return `False` if the TX FIFO buffer is empty.

    .. note:: The nRF24L01 normally removes a payload from the TX FIFO buffer after successful
        transmission, but not when this function is called. The payload (successfully
        transmitted or not) will remain in the TX FIFO buffer until `flush_tx()` is called to
        remove them. Alternatively, using this function also allows the failed payload to be
        over-written by using `send()` or `write()` to load a new payload into the TX FIFO
        buffer.

write()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.write

    :param bytearray buf: The payload to transmit. This bytearray must have a length greater
        than 0 and less than 32 bytes, otherwise a `ValueError` exception is thrown.

        - If the `dynamic_payloads` attribute is disabled for data pipe 0 and this bytearray's
          length is less than the `payload_length` attribute for data pipe 0, then this
          bytearray is padded with zeros until its length is equal to the `payload_length`
          attribute for data pipe 0.
        - If the `dynamic_payloads` attribute is disabled  for data pipe 0 and this bytearray's
          length is greater than `payload_length` attribute for data pipe 0, then this
          bytearray's length is truncated to equal the `payload_length` attribute for data
          pipe 0.
    :param bool ask_no_ack: Pass this parameter as `True` to tell the nRF24L01 not to wait for
        an acknowledgment from the receiving nRF24L01. This parameter directly controls a
        ``NO_ACK`` flag in the transmission's Packet Control Field (9 bits of information about
        the payload). Therefore, it takes advantage of an nRF24L01 feature specific to
        individual payloads, and its value is not saved anywhere. You do not need to specify
        this for every payload if the `arc` attribute is disabled, however setting this
        parameter to `True` will work despite the `arc` attribute's setting.

        .. note:: Each transmission is in the form of a packet. This packet contains sections
            of data around and including the payload. `See Chapter 7.3 in the nRF24L01
            Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1136318>`_ for more
            details.

    This function isn't completely non-blocking as we still need to wait just under 5 ms for
    the CSN pin to settle (allowing a clean SPI transaction).

    .. note:: The nRF24L01 doesn't initiate sending until a mandatory minimum 10 µs pulse on
        the CE pin is acheived. That pulse is initiated before this function exits. However, we
        have left that 10 µs wait time to be managed by the MCU in cases of asychronous
        application, or it is managed by using `send()` instead of this function. According to
        the Specification sheet, if the CE pin remains HIGH for longer than 10 µs, then the
        nRF24L01 will continue to transmit all payloads found in the TX FIFO buffer.

    .. warning::
        A note paraphrased from the `nRF24L01+ Specifications Sheet
        <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_:

        It is important to NEVER to keep the nRF24L01+ in TX mode for more than 4 ms at a time.
        If the [`arc` attribute is] enabled, nRF24L01+ is never in TX mode longer than 4
        ms.

    .. tip:: Use this function at your own risk. Because of the underlying `"Enhanced
        ShockBurst Protocol" <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132607>`_, disobeying the 4
        ms rule is easily avoided if you enable the `auto_ack` attribute. Alternatively, you
        MUST use interrupt flags or IRQ pin with user defined timer(s) to AVOID breaking the
        4 ms rule. If the `nRF24L01+ Specifications Sheet explicitly states this
        <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_, we have to assume
        radio damage or misbehavior as a result of disobeying the 4 ms rule. See also `table 18
        in the nRF24L01 specification sheet <https://www.sparkfun.com/datasheets/Components/
        SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1123001>`_ for
        calculating an adequate transmission timeout sentinal.

flush_rx()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.flush_rx

    .. note:: The nRF24L01 RX FIFO is 3 level stack that holds payload data. This means that
        there can be up to 3 received payloads (each of a maximum length equal to 32 bytes)
        waiting to be read (and popped from the stack) by `recv()` or `read_ack()`. This
        function clears all 3 levels.

flush_tx()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.flush_tx

    .. note:: The nRF24L01 TX FIFO is 3 level stack that holds payload data. This means that
        there can be up to 3 payloads (each of a maximum length equal to 32 bytes) waiting to
        be transmit by `send()`, `resend()` or `write()`. This function clears all 3 levels. It
        is worth noting that the payload data is only popped from the TX FIFO stack upon
        successful transmission (see also `resend()` as the handling of failed transmissions
        can be altered).

fifo()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.fifo

    :param bool about_tx:
        - `True` means information returned is about the TX FIFO buffer.
        - `False` means information returned is about the RX FIFO buffer. This parameter
          defaults to `False` when not specified.
    :param bool check_empty:
        - `True` tests if the specified FIFO buffer is empty.
        - `False` tests if the specified FIFO buffer is full.
        - `None` (when not specified) returns a 2 bit number representing both empty (bit 1) &
          full (bit 0) tests related to the FIFO buffer specified using the ``about_tx``
          parameter.
    :returns:
        - A `bool` answer to the question:
          "Is the [TX/RX]:[`True`/`False`] FIFO buffer [empty/full]:[`True`/`False`]?
        - If the ``check_empty`` parameter is not specified: an `int` in range [0,2] for which:

            - ``1`` means the specified FIFO buffer is full
            - ``2`` means the specified FIFO buffer is empty
            - ``0`` means the specified FIFO buffer is neither full nor empty

pipe
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.pipe

    .
    
    |update manually|

    :Returns:
        
        - `None` if there is no payload in RX FIFO.
        - The `int` identifying pipe number [0,5] that received the next
          available payload in the RX FIFO buffer.

address_length
******************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.address_length

    A valid input value must be an `int` in range [3, 5]. Otherwise a `ValueError` exception is
    thrown. Default is set to the nRF24L01's maximum of 5.

address()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.address

    This function returns the full content of the nRF24L01's registers about RX/TX addresses
    despite what `address_length` is set to.

    :param int index: the number of the data pipe whose address is to be returned. Defaults to
        ``-1``. A valid index ranges [0,5] for RX addresses or any negative `int` for the TX
        address. Otherwise an `IndexError` is thown.

rpd
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.rpd

    The RPD flag is triggered in the following cases:

        1. During RX mode (`listen` = `True`) and an arbitrary RF transmission with a gain
           above -64 dBm threshold is/was present.
        2. When a packet is received (instigated by the nRF24L01 used to detect/"listen" for
           incoming packets).

    .. note:: See also
        `section 6.4 of the Specification Sheet concerning the RPD flag
        <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1160291>`_. Ambient
        temperature affects the -64 dBm threshold. The latching of this flag happens
        differently under certain conditions.

start_carrier_wave()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.start_carrier_wave

    This is a basic test of the nRF24L01's TX output. It is a commonly required
    test for telecommunication regulations. Calling this function may introduce
    interference with other transceivers that use frequencies in range [2.4,
    2.525] GHz. To verify that this test is working properly, use the following
    code on a seperate nRF24L01 transceiver:

    .. code-block:: python

        # declare objects for SPI bus and CSN pin and CE pin
        nrf. = RF24(spi, csn, ce)
        # set nrf.pa_level, nrf.channel, & nrf.data_rate values to
        # match the corresponding attributes on the device that is
        # transmitting the carrier wave
        nrf.listen = True
        if nrf.rpd:
            print("carrier wave detected")

    The `pa_level`, `channel` & `data_rate` attributes are vital factors to
    the success of this test. See also the `rpd` attribute.

stop_carrier_wave()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.stop_carrier_wave

    See `start_carrier_wave()` for more details.

    .. note::
        Calling this function puts the nRF24L01 to sleep (AKA power down mode).

Configuration API
-----------------

CSN_DELAY
******************************

.. autodata:: circuitpython_nrf24l01.rf24.CSN_DELAY

dynamic_payloads
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.dynamic_payloads

    Default setting is enabled on all pipes.

    - `True` or ``1`` enables nRF24L01's dynamic payload length feature for all data pipes. The
      `payload_length` attribute is ignored when this feature is enabled for respective or all
      data pipes.
    - `False` or ``0`` disables nRF24L01's dynamic payload length feature for all data pipes.
      Be sure to adjust the `payload_length` attribute accordingly when this feature is
      disabled for any data pipes.
    - A `list` or `tuple` containing booleans or integers can be used control this feature per
      data pipe. Index 0 controls this feature on data pipe 0. Indices greater than 5 will be
      ignored since there are only 6 data pipes.

    .. note::
        This attribute mostly relates to RX operations, but data pipe 0 applies to TX
        operations also.

payload_length
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.payload_length

    If the `dynamic_payloads` attribute is enabled for a certain data pipe, this attribute has
    no affect on that data pipe. When `dynamic_payloads` is disabled for a certain data pipe,
    this attribute is used to specify the payload length on that data pipe in RX mode.

    A valid input value must be:
    
        * an `int` in range [1, 32]. Otherwise a `ValueError` exception is thrown.
        * a `list` or `tuple` containing integers can be used to control this attribute per
          data pipe. Index 0 controls this feature on data pipe 0. Indices greater than 5 will
          be ignored since there are only 6 data pipes. if a index's value is ``0``, then the
          existing setting will persist (not be changed).
        
        Default is set to the nRF24L01's maximum of 32 (on all data pipes).

    .. note::
        This attribute mostly relates to RX operations, but data pipe 0 applies to TX
        operations also.

auto_ack
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.auto_ack

    Default setting is enabled on all data pipes.

    - `True` or ``1`` enables transmitting automatic acknowledgment packets for all data pipes.
      The CRC (cyclic redundancy checking) is enabled automatically by the nRF24L01 if the
      `auto_ack` attribute is enabled for any data pipe (see also `crc` attribute).
    - `False` or ``0`` disables transmitting automatic acknowledgment packets for all data
      pipes. The `crc` attribute will remain unaffected when disabling this attribute for any
      data pipes.
    - A `list` or `tuple` containing booleans or integers can be used control this feature per
      data pipe. Index 0 controls this feature on data pipe 0. Indices greater than 5 will be
      ignored since there are only 6 data pipes.

    .. note::
        This attribute mostly relates to RX operations, but data pipe 0 applies to TX
        operations also.

arc
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.arc

    The `auto_ack` attribute must be enabled on the receiving nRF24L01 respective data pipe,
    otherwise this attribute will make `send()` seem like it failed.

    A valid input value must be in range [0, 15]. Otherwise a `ValueError` exception is thrown.
    Default is set to 3. A value of ``0`` disables the automatic re-transmit feature and
    considers all payload transmissions a success.

ard
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.ard

    During this time, the nRF24L01 is listening for the ACK packet. If the
    `auto_ack` attribute is disabled, this attribute is not applied.

    A valid input value must be in range [250, 4000]. Otherwise a `ValueError` exception is
    thrown. Default is 1500 for reliability. If this is set to a value that is not multiple of
    250, then the highest multiple of 250 that is no greater than the input value is used. 

    .. note:: Paraphrased from nRF24L01 specifications sheet:

        Please take care when setting this parameter. If the custom ACK payload is more than 15
        bytes in 2 Mbps data rate, the `ard` must be 500µS or more. If the custom ACK payload
        is more than 5 bytes in 1 Mbps data rate, the `ard` must be 500µS or more. In 250kbps
        data rate (even when there is no custom ACK payload) the `ard` must be 500µS or more.

        See `data_rate` attribute on how to set the data rate of the nRF24L01's transmissions.

ack
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.ack

    Use this attribute to set/check if the custom ACK payloads feature is enabled. Default
    setting is `False`.

    - `True` enables the use of custom ACK payloads in the ACK packet when responding to
      receiving transmissions.
    - `False` disables the use of custom ACK payloads in the ACK packet when responding to
      receiving transmissions.

    .. important::
        As `dynamic_payloads` and `auto_ack` attributes are required for this feature to work,
        they are automatically enabled (on data pipe 0) as needed. However, it is required to
        enable the `auto_ack` and `dynamic_payloads` features on all applicable pipes.
        Disabling this feature does not disable the `auto_ack` and `dynamic_payloads`
        attributes for any data pipe; they work just fine without this feature.

interrupt_config()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.interrupt_config

    The digital signal from the nRF24L01's IRQ pin is active LOW. (write-only)

    :param bool data_recv: If this is `True`, then IRQ pin goes active when there is new data
        to read in the RX FIFO buffer. Default setting is `True`
    :param bool data_sent: If this is `True`, then IRQ pin goes active when a payload from TX
        buffer is successfully transmit. Default setting is `True`
    :param bool data_fail: If this is `True`, then IRQ pin goes active when maximum number of
        attempts to re-transmit the packet have been reached. If `auto_ack` attribute is
        disabled, then this IRQ event is not used. Default setting is `True`

    .. note:: To fetch the status (not configuration) of these IRQ flags, use the `irq_df`,
        `irq_ds`, `irq_dr` attributes respectively.

    .. tip:: Paraphrased from nRF24L01+ Specification Sheet:

        The procedure for handling ``data_recv`` IRQ should be:

        1. read payload through `recv()`
        2. clear ``dataReady`` status flag (taken care of by using `recv()` in previous step)
        3. read FIFO_STATUS register to check if there are more payloads available in RX FIFO
           buffer. A call to `pipe` (may require `update()` to be called), `any()` or even
           ``(False,True)`` as parameters to `fifo()` will get this result.
        4. if there is more data in RX FIFO, repeat from step 1

data_rate
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.data_rate

    A valid input value is:

    - ``1`` sets the frequency data rate to 1 Mbps
    - ``2`` sets the frequency data rate to 2 Mbps
    - ``250`` sets the frequency data rate to 250 Kbps

    Any invalid input throws a `ValueError` exception. Default is 1 Mbps.

    .. warning:: 250 Kbps can be buggy on the non-plus models of the nRF24L01 product line. If
        you use 250 Kbps data rate, and some transmissions report failed by the transmitting
        nRF24L01, even though the same packet in question actually reports received by the
        receiving nRF24L01, then try a higher data rate. CAUTION: Higher data rates mean less
        maximum distance between nRF24L01 transceivers (and vise versa).

channel
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.channel

    A valid input value must be in range [0, 125] (that means [2.4, 2.525] GHz). Otherwise a
    `ValueError` exception is thrown. Default is ``76`` (2.476 GHz).

crc
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.crc

    CRC is a way of making sure that the transmission didn't get corrupted over the air.

    A valid input value must be:

    - ``0`` disables CRC (no anti-corruption of data)
    - ``1`` enables CRC encoding scheme using 1 byte (weak anti-corruption of data)
    - ``2`` enables CRC encoding scheme using 2 bytes (better anti-corruption of data)

    Any invalid input throws a `ValueError` exception. Default is enabled using 2 bytes.

    .. note:: The nRF24L01 automatically enables CRC if automatic acknowledgment feature is
        enabled (see `auto_ack` attribute).

pa_level
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.pa_level

    Higher levels mean the transmission will cover a longer distance. Use this attribute to
    tweak the nRF24L01 current consumption on projects that don't span large areas.

    A valid input value is:

    - ``-18`` sets the nRF24L01's power amplifier to -18 dBm (lowest)
    - ``-12`` sets the nRF24L01's power amplifier to -12 dBm
    - ``-6`` sets the nRF24L01's power amplifier to -6 dBm
    - ``0`` sets the nRF24L01's power amplifier to 0 dBm (highest)

    If this attribute is set to a `list` or `tuple`, then the list/tuple must contain the
    desired power amplifier level (from list above) at index 0 and a `bool` to control
    the Low Noise Amplifier (LNA) feature at index 1. All other indices will be discarded.

        .. note::
            The LNA feature only applies to the nRF24L01 (non-plus variant). This
            includes boards with the RFX24C01-based PA/LNA muxing IC attached to an
            SMA-type detachable antenna.

    Any invalid input will invoke the default of 0 dBm with LNA enabled.

is_lna_enabled
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.is_lna_enabled

    See `pa_level` attribute about how to set this. Default is always enabled, but this
    feature is specific to certain nRF24L01-based circuits. Check with your module's
    manufacturer to see is it can toggle the Low Noise Amplifier feature.
