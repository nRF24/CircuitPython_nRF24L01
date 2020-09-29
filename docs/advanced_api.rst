
.. |irq note| replace::  parameter as `True` to `clear_status_flags()` and reset this. As this
    is a virtual representation of the interrupt event, this attribute will always be updated
    despite what the actual IRQ pin is configured to do about this event.
    
.. |update manually| replace:: Calling this does not execute an SPI transaction. It only
    exposes that latest data contained in the STATUS byte that's always returned from any
    other SPI transactions. Use the `update()` function to manually refresh this data when
    needed.

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
