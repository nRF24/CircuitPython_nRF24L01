
.. |irq note| replace::  parameter as `True` to
    :py:func:`~circuitpython_nrf24l01.rf24.RF24.clear_status_flags()` and reset this.
    As this is a virtual representation of the interrupt event, this attribute will
    always be updated despite what the actual IRQ pin is configured to do about this
    event.

.. |update manually| replace:: Calling this does not execute an SPI transaction. It only
    exposes that latest data contained in the STATUS byte that's always returned from any
    other SPI transactions. Use the :py:func:`~circuitpython_nrf24l01.rf24.RF24.update()`
    function to manually refresh this data when needed

Advanced RF24 API
-----------------

resend()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.resend

    This function is meant to be used for payloads that failed to transmit using the
    `send()` function. If a payload failed to transmit using the `write()` function,
    just call `clear_status_flags()` and re-start the pulse on the nRF24L01's CE pin.

    :returns: Data returned from this function follows the same pattern that `send()`
        returns with the added condition that this function will return `False` if the TX
        FIFO buffer is empty.
    :param bool send_only: This parameter only applies when the `ack` attribute is set to
        `True`. Pass this parameter as `True` if the RX FIFO is not to be manipulated. Many
        other libraries' behave as though this parameter is `True`
        (e.g. The popular TMRh20 Arduino RF24 library). This parameter defaults to `False`.
        If this parameter is set to `True`, then use `read()` to get the ACK payload
        (if there is any) from the RX FIFO. Remember that the RX FIFO can only hold
        up to 3 payloads at once.

    .. note:: The nRF24L01 normally removes a payload from the TX FIFO buffer after successful
        transmission, but not when this function is called. The payload (successfully
        transmitted or not) will remain in the TX FIFO buffer until `flush_tx()` is called to
        remove them. Alternatively, using this function also allows the failed payload to be
        over-written by using `send()` or `write()` to load a new payload into the TX FIFO
        buffer.

write()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.write

    This function isn't completely non-blocking as we still need to wait
    for the necessary SPI transactions to complete. Example usage of
    this function can be seen in the `IRQ pin example <examples.html#irq-pin-example>`_ and
    in the `Stream example's "master_fifo()" function <examples.html#stream-example>`_

    :returns: `True` if the payload was added to the TX FIFO buffer. `False` if the TX FIFO
        buffer is already full, and no payload could be added to it.
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
        this for every payload if the `auto_ack` attribute is disabled, however setting this
        parameter to `True` will work despite the `auto_ack` attribute's setting.

        .. important:: If the `allow_ask_no_ack` attribute is disabled (set to `False`),
            then this parameter will have no affect at all. By default the
            `allow_ask_no_ack` attribute is enabled.

        .. note:: Each transmission is in the form of a packet. This packet contains sections
            of data around and including the payload. `See Chapter 7.3 in the nRF24L01
            Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1136318>`_ for more
            details.
    :param bool write_only: This function will not manipulate the nRF24L01's CE pin if this
        parameter is `True`. The default value of `False` will ensure that the CE pin is
        HIGH upon exiting this function. This function does not set the CE pin LOW at
        any time. Use this parameter as `True` to fill the TX FIFO buffer before beginning
        transmissions.

        .. note:: The nRF24L01 doesn't initiate sending until a mandatory minimum 10 µs pulse
            on the CE pin is acheived. If the ``write_only`` parameter is `False`, then that
            pulse is initiated before this function exits. However, we have left that 10 µs
            wait time to be managed by the MCU in cases of asychronous application, or it is
            managed by using `send()` instead of this function. According to the
            Specification sheet, if the CE pin remains HIGH for longer than 10 µs, then the
            nRF24L01 will continue to transmit all payloads found in the TX FIFO buffer.

    .. warning::
        A note paraphrased from the `nRF24L01+ Specifications Sheet
        <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_:

        It is important to NEVER to keep the nRF24L01+ in TX mode for more than 4 ms at a time.
        If the [`auto_ack` attribute is] enabled, nRF24L01+ is never in TX mode longer than 4
        ms.

    .. tip:: Use this function at your own risk. Because of the underlying
        `"Enhanced ShockBurst Protocol" <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132607>`_, disobeying the 4
        ms rule is easily avoided if the `auto_ack` attribute is greater than ``0``. Alternatively,
        you MUST use nRF24L01's IRQ pin and/or user-defined timer(s) to AVOID breaking the
        4 ms rule. If the `nRF24L01+ Specifications Sheet explicitly states this
        <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_, we have to assume
        radio damage or misbehavior as a result of disobeying the 4 ms rule. See also `table 18
        in the nRF24L01 specification sheet <https://www.sparkfun.com/datasheets/Components/
        SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1123001>`_ for
        calculating an adequate transmission timeout sentinal.
    .. versionadded:: 1.2.0
        ``write_only`` parameter

print_details()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.print_details

    Some information may be irrelevant depending on nRF24L01's state/condition.

    :prints:

        - ``Is a plus variant`` True means the transceiver is a nRF24L01+. False
          means the transceiver is a nRF24L01 (not a plus variant).
        - ``Channel`` The current setting of the `channel` attribute
        - ``RF Data Rate`` The current setting of the RF `data_rate` attribute.
        - ``RF Power Amplifier`` The current setting of the `pa_level` attribute.
        - ``CRC bytes`` The current setting of the `crc` attribute
        - ``Address length`` The current setting of the `address_length` attribute
        - ``TX Payload lengths`` The current setting of the `payload_length` attribute for TX
          operations (concerning data pipe 0)
        - ``Auto retry delay`` The current setting of the `ard` attribute
        - ``Auto retry attempts`` The current setting of the `arc` attribute
        - ``Re-use TX FIFO`` Is the first payload in the TX FIFO to be re-used for subsequent
          transmissions (this flag is set to `True` when entering `resend()` and reset to
          `False` when `resend()` exits)
        - ``Packets lost on current channel`` Total amount of packets lost (transmission
          failures). This only resets when the `channel` is changed. This count will
          only go up to 15.
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
        - ``Ask no ACK`` The current setting of the `allow_ask_no_ack` attribute.
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
          `address_length` is set to).
        - if the pipe is open, then the output also prints ``expecting [X] byte static
          payloads`` where ``X`` is the `payload_length` (in bytes) the pipe is setup to
          receive when `dynamic_payloads` is disabled for that pipe.

        This parameter's default is `False` and skips this extra information.

address_repr()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.address_repr

    This method is primarily used in :meth:`~RF24.print_details()` to
    display how the address is used by the radio.

    .. code-block:: python

        >>> from circuitpython_nrf24l01.rf24 import address_repr
        >>> address_repr(b"1Node")
        '65646f4e31'

    :Return:
        A string of hexidecimal characters in big endian form of the
        specified ``addr`` parameter.
    :param bytes,bytearray addr: The address to convert into a hexlified
        string

is_plus_variant
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.is_plus_variant

    This information is detirmined upon instantiation.

    .. versionadded:: 1.2.0

load_ack()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.load_ack

    This payload will then be appended to the automatic acknowledgment
    (ACK) packet that is sent when *new* data is received on the specified pipe. See
    `read()` on how to fetch a received custom ACK payloads.

    :param bytearray,bytes buf: This will be the data attached to an automatic ACK packet on the
        incoming transmission about the specified ``pipe_number`` parameter. This must have a
        length in range [1, 32] bytes, otherwise a `ValueError` exception is thrown. Any ACK
        payloads will remain in the TX FIFO buffer until transmitted successfully or
        `flush_tx()` is called.
    :param int pipe_number: This will be the pipe number to use for deciding which
        transmissions get a response with the specified ``buf`` parameter's data. This number
        must be in range [0, 5], otherwise a `IndexError` exception is thrown.

    :returns: `True` if payload was successfully loaded onto the TX FIFO buffer. `False` if it
        wasn't because TX FIFO buffer is full.

    .. note:: this function takes advantage of a special feature on the nRF24L01 and needs to
        be called for every time a customized ACK payload is to be used (not for every
        automatic ACK packet -- this just appends a payload to the ACK packet). The `ack`,
        `auto_ack`, and `dynamic_payloads` attributes are also automatically enabled (with
        respect to data pipe 0) by this function when necessary.

    .. tip:: The ACK payload must be set prior to receiving a transmission. It is also worth
        noting that the nRF24L01 can hold up to 3 ACK payloads pending transmission. Using this
        function does not over-write existing ACK payloads pending; it only adds to the queue
        (TX FIFO buffer) if it can. Use `flush_tx()` to discard unused ACK payloads when done
        listening.

Status Byte
******************************

tx_full
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.tx_full

    .

    |update manually| (especially after calling
    :py:func:`~circuitpython_nrf24l01.rf24.RF24.flush_tx()`).

    :returns:

        - `True` for TX FIFO buffer is full
        - `False` for TX FIFO buffer is not full. This doesn't mean the TX FIFO buffer is
          empty.

irq_dr
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_dr

    .

    :Returns:

        - `True` represents Data is in the RX FIFO buffer
        - `False` represents anything depending on context (state/condition of FIFO buffers);
          usually this means the flag's been reset.

    .. important:: It is recommended that this flag is only used when the IRQ pin is active.
        To detirmine if there is a payload in the RX FIFO, use `fifo()`, `any()`, or `pipe`.
        Notice that calling `read()` also resets this status flag.

    Pass ``data_recv`` |irq note|

    |update manually| (especially after calling
    :py:func:`~circuitpython_nrf24l01.rf24.RF24.clear_status_flags()`).

irq_df
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_df

    .

    :Returns:

        - `True` signifies the nRF24L01 attemped all configured retries
        - `False` represents anything depending on context (state/condition); usually this
          means the flag's been reset.

    .. important:: This can only return `True` if `auto_ack` is enabled, otherwise this will
        always be `False`.

    Pass ``data_fail`` |irq note|

    |update manually| (especially after calling
    :py:func:`~circuitpython_nrf24l01.rf24.RF24.clear_status_flags()`).

irq_ds
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_ds

    .

    :Returns:

        - `True` represents a successful transmission
        - `False` represents anything depending on context (state/condition of FIFO buffers);
          usually this means the flag's been reset.

    Pass ``data_sent`` |irq note|

    |update manually| (especially after calling
    :py:func:`~circuitpython_nrf24l01.rf24.RF24.clear_status_flags()`).

update()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.update

    Refreshing the status byte is vital to checking status of the interrupt flags, RX pipe
    number related to current RX payload, and if the TX FIFO buffer is full. This function
    returns nothing, but internally updates the `irq_dr`, `irq_ds`, `irq_df`, `pipe`, and
    `tx_full` attributes. Internally this is a helper function to `available()`, `send()`, and `resend()`
    functions.

    :returns: `True` for every call. This value is meant to allow this function to be used
        in `if` or `while` *in conjunction with* attributes related to the
        refreshed status byte.

    .. versionchanged:: 1.2.3
        arbitrarily returns `True`

pipe
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.pipe

    .

    .. versionchanged:: 1.2.0
        In previous versions of this library, this attribute was a read-only function
        (``pipe()``).

    |update manually| (especially after calling
    :py:func:`~circuitpython_nrf24l01.rf24.RF24.flush_rx()`).

    :Returns:

        - `None` if there is no payload in RX FIFO.
        - The `int` identifying pipe number [0,5] that received the next
          available payload in the RX FIFO buffer.

clear_status_flags()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.clear_status_flags

    Internally, this is automatically called by `send()`, `write()`, `read()`, and when
    `listen` changes from `False` to `True`.

    :param bool data_recv: specifies wheather to clear the "RX Data Ready"
        (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_dr`) flag.
    :param bool data_sent: specifies wheather to clear the "TX Data Sent"
        (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_ds`) flag.
    :param bool data_fail: specifies wheather to clear the "Max Re-transmit reached"
        (`irq_df`) flag.

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
      to sleep until the MCU invokes RX/TX modes. This driver class will only power down
      the nRF24L01 after exiting a `with` block.
    - `True` powers up the nRF24L01. This is the first step towards entering RX/TX modes (see
      also `listen` attribute). Powering up is automatically handled by the `listen` attribute
      as well as the `send()` and `write()` functions.

    .. note:: This attribute needs to be `True` if you want to put radio on Standby-II (highest
        current consumption) or Standby-I (moderate current consumption) modes. The state of
        the CE pin determines which Standby mode is acheived. See `Chapter 6.1.2-7 of the
        nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132980>`_ for more details.

FIFO management
******************************

flush_rx()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.flush_rx

    .. note:: The nRF24L01 RX FIFO is 3 level stack that holds payload data. This means that
        there can be up to 3 received payloads (each of a maximum length equal to 32 bytes)
        waiting to be read (and removed from the stack) by `read()`. This
        function clears all 3 levels.

flush_tx()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.flush_tx

    .. note:: The nRF24L01 TX FIFO is 3 level stack that holds payload data. This means that
        there can be up to 3 payloads (each of a maximum length equal to 32 bytes) waiting to
        be transmit by `send()`, `resend()` or `write()`. This function clears all 3 levels. It
        is worth noting that the payload data is only removed from the TX FIFO stack upon
        successful transmission (see also `resend()` as the handling of failed transmissions
        can be altered).

fifo()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.fifo

    :param bool about_tx:
        - `True` means the information returned is about the TX FIFO buffer.
        - `False` means the information returned is about the RX FIFO buffer. This parameter
          defaults to `False` when not specified.
    :param bool check_empty:
        - `True` tests if the specified FIFO buffer is empty.
        - `False` tests if the specified FIFO buffer is full.
        - `None` (when not specified) returns a 2 bit number representing both empty (bit 1) &
          full (bit 0) tests related to the FIFO buffer specified using the ``about_tx``
          parameter.
    :returns:
        - A `bool` answer to the question:

          "Is the [TX/RX](``about_tx``) FIFO buffer [empty/full](``check_empty``)?
        - If the ``check_empty`` parameter is not specified: an `int` in range [0,2] for which:

          - ``1`` means the specified FIFO buffer is empty
          - ``2`` means the specified FIFO buffer is full
          - ``0`` means the specified FIFO buffer is neither full nor empty


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

    :param int index: the number of the data pipe whose address is to be returned. A valid
        index ranges [0,5] for RX addresses or any negative number for the TX address.
        Otherwise an `IndexError` is thown. This parameter defaults to ``-1``.

    .. versionadded:: 1.2.0

last_tx_arc
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.last_tx_arc

    This attribute resets to 0 at the beginning of every transmission in TX mode.
    Remember that the number of automatic retry attempts made for each transmission is
    configured with the `arc` attribute or the `set_auto_retries()` function.

Ambiguous Signal Detection
******************************

rpd
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.rpd

    The RPD flag is triggered in the following cases:

    1. During RX mode (when `listen` is `True`) and an arbitrary RF transmission with
       a gain above -64 dBm threshold is/was present.
    2. When a packet is received (instigated by the nRF24L01 used to detect/"listen" for
       incoming packets).

    .. note:: See also
        `section 6.4 of the Specification Sheet concerning the RPD flag
        <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1160291>`_. Ambient
        temperature affects the -64 dBm threshold. The latching of this flag happens
        differently under certain conditions.

    .. versionadded:: 1.2.0

start_carrier_wave()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    the success of this test. Be sure these attributes are set to the desired test
    conditions before calling this function. See also the `rpd` attribute.

    .. note:: To preserve backward compatibility with non-plus variants of the
        nRF24L01, this function will also change certain settings if `is_plus_variant`
        is `False`. These settings changes include

        - disabling `crc`
        - disabling `auto_ack`
        - disabling `arc` and setting `ard` to 250 microseconds
        - changing the TX address to ``b"\xFF\xFF\xFF\xFF\xFF"``
        - loading a 32-byte payload (each byte is ``0xFF``) into the TX FIFO buffer

        Finally the radio continuously behaves like using `resend()` to establish
        the constant carrier wave. If `is_plus_variant` is `True`, then none of these
        changes are needed nor applied.

    .. versionadded:: 1.2.0

stop_carrier_wave()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.stop_carrier_wave

    See `start_carrier_wave()` for more details.

    .. note::
        Calling this function puts the nRF24L01 to sleep (AKA power down mode).
    .. hint:: If the radio is a non-plus variant (`is_plus_variant` returns
        `False`), then use the following code snippet to re-establish the library
        default settings:

        .. code-block::

            # let `nrf` be the instantiated RF24 object
            nrf.crc = 2
            nrf.auto_ack = True
            nrf.set_auto_retries(1500, 3)
            nrf.open_tx_pipe(nrf.address())

    .. versionadded:: 1.2.0
