
Basic API
---------

Constructor
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
    :param int spi_frequency: Specify which SPI frequency (in Hz) to use on the SPI bus. This
        parameter only applies to the instantiated object and is made persistent via
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

