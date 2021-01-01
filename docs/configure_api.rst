
.. |per_data_pipe_control| replace:: can be used control this feature per data pipe. Index 0
    controls this feature on data pipe 0. Indices greater than 5 will be
    ignored since there are only 6 data pipes.

.. |mostly_rx_but_tx0| replace:: This attribute mostly relates to RX operations, but data
    pipe 0 applies to TX operations also.

Configurable RF24 API
-----------------------

dynamic_payloads
******************************

.. note::
    |mostly_rx_but_tx0|

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.dynamic_payloads

    Default setting is enabled on all pipes. A valid input is:

    - A `bool` to enable (`True`) or disable (`False`) the dynamic payload length feature for all data pipes.
    - A `list` or `tuple` containing booleans or integers |per_data_pipe_control| If any
      index's value is less than 0 (a negative value), then the pipe corresponding to that
      index will remain unaffected.
    - An `int` where each bit in the integer represents the dynamic payload feature
      per pipe. Bit position 0 controls this feature for data pipe 0, and bit position 5
      controls this feature for data pipe 5. All bits in positions greater than 5 are ignored.

    .. note::
        - The `payload_length` attribute is ignored when this feature is enabled
          for any respective data pipes.
        - Be sure to adjust the `payload_length` attribute accordingly when this
          feature is disabled for any respective data pipes.

    :returns:
        An `int` (1 unsigned byte) where each bit in the integer represents the dynamic
        payload length feature per pipe.

    .. versionchanged:: 1.2.0
        accepts a list or tuple for control of the dynamic payload length feature per pipe.
    .. versionchanged:: 2.0.0

        - returns a integer instead of a boolean
        - accepts an integer for binary control of the dynamic payload length
          feature per pipe

set_dynamic_payloads()
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.set_dynamic_payloads

    :param bool enable: The state of the dynamic payload feature about a specified
        data pipe.
    :param int pipe_number: The specific data pipe number in range [0, 5] to apply the
        ``enable`` parameter. If this parameter is not specified the ``enable`` parameter is
        applied to all data pipes. If this parameter is not in range [0, 5], then a
        `IndexError` exception is thrown.

    .. versionadded:: 2.0.0

get_dynamic_payloads()
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.get_dynamic_payloads

    :param int pipe_number: The specific data pipe number in range [0, 5] concerning the
        dynamic payload length feature. If this parameter is not in range [0, 5], then a
        `IndexError` exception is thrown. If this parameter is not specified, then the data
        returned is about data pipe 0.

payload_length
******************************

.. note::
    |mostly_rx_but_tx0|

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.payload_length

    This attribute can be used to specify the static payload length used for all data pipes
    in which the `dynamic_payloads` attribute is *disabled*

    A valid input value must be:

    * an `int` in which the value that will be clamped to the range [1, 32]. Setting this attribute to a
      single `int` configures all 6 data pipes.
    * A `list` or `tuple` containing integers |per_data_pipe_control| If any index's
      value is less than or equal to``0``, then the existing setting for the corresponding data pipe will
      persist (not be changed).

    Default is set to the nRF24L01's maximum of 32 (on all data pipes).

    :returns:
        The current setting of the expected static payload length feature for pipe 0 only.

    .. versionchanged:: 1.2.0
        return a list of all payload length settings for all pipes. This implementation
        introduced a couple bugs:

        1. The settings could be changed improperly in a way that was not written to the
           nRF24L01 registers.
        2. There was no way to catch an invalid setting if configured improperly via the
           first bug. This led to errors in using other functions that handle payloads or
           the length of payloads.

    .. versionchanged:: 2.0.0
        this attribute returns the configuration about static payload length for data pipe 0
        only. Use `get_payload_length()` to fetch the configuration of the static payload
        length feature for any data pipe.

set_payload_length()
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.set_payload_length

    This function only affects data pipes for which the `dynamic_payloads` attribute is
    *disabled*.

    :param int length: The number of bytes in range [1, 32] for to be used for static
        payload lengths. If this number is not in range [1, 32], then it will be clamped to
        that range.
    :param int pipe_number: The specific data pipe number in range [0, 5] to apply the
        ``length`` parameter. If this parameter is not specified the ``length`` parameter is
        applied to all data pipes. If this parameter is not in range [0, 5], then a
        `IndexError` exception is thrown.

    .. versionadded:: 2.0.0

get_payload_length()
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.get_payload_length

    The data returned by this function is only relevant for data pipes in which the
    `dynamic_payloads` attribute is *disabled*.

    :param int pipe_number: The specific data pipe number in range [0, 5] to concerning the
        static payload length feature. If this parameter is not in range [0, 5], then a
        `IndexError` exception is thrown. If this parameter is not specified, then the data
        returned is about data pipe 0.

    .. versionadded:: 2.0.0

auto_ack
******************************

.. note::
    |mostly_rx_but_tx0| This attribute will intuitively:
        - enable the automatic acknowledgement feature for pipe 0 if any other data pipe
          is configured to use the automatic acknowledgement feature.
        - disable the acknowledgement payload feature (`ack` attribute) when the
          automatic acknowledgement feature is disabled for data pipe 0.

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.auto_ack

    Default setting is enabled on all data pipes. A valid input is:

    - A `bool` to enable (`True`) or disable (`False`) transmitting automatic acknowledgment packets for all data pipes.
    - A `list` or `tuple` containing booleans or integers |per_data_pipe_control| If any
      index's value is less than 0 (a negative value), then the pipe corresponding to that
      index will remain unaffected.
    - An `int` where each bit in the integer represents the automatic acknowledgement feature
      per pipe. Bit position 0 controls this feature for data pipe 0, and bit position 5
      controls this feature for data pipe 5. All bits in positions greater than 5 are ignored.

    .. note:: The CRC (cyclic redundancy checking) is enabled (for all
        transmissions) automatically by the nRF24L01 if this attribute is enabled
        for any data pipe (see also `crc` attribute). The `crc` attribute will
        remain unaffected when disabling this attribute for any data pipes.

    :returns:
        An `int` (1 unsigned byte) where each bit in the integer represents the automatic
        acknowledgement feature per pipe.

    .. versionchanged:: 1.2.0
        accepts a list or tuple for control of the automatic acknowledgement feature per pipe.
    .. versionchanged:: 2.0.0

        - returns a integer instead of a boolean
        - accepts an integer for binary control of the automatic acknowledgement feature
          per pipe

set_auto_ack()
^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.set_auto_ack

    :param bool enable: The state of the automatic acknowledgement feature about a specified
        data pipe.
    :param int pipe_number: The specific data pipe number in range [0, 5] to apply the
        ``enable`` parameter. If this parameter is not specified the ``enable`` parameter is
        applied to all data pipes. If this parameter is not in range [0, 5], then a
        `IndexError` exception is thrown.

    .. versionadded:: 2.0.0

get_auto_ack()
^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.get_auto_ack

    :param int pipe_number: The specific data pipe number in range [0, 5] concerning the
        setting for the automatic acknowledgment feature. If this parameter is not in range
        [0, 5], then a `IndexError` exception is thrown. If this parameter is not specified,
        then the data returned is about data pipe 0.

    .. versionadded:: 2.0.0

Auto-Retry feature
******************************

arc
^^^^^^^^^^^^^^^^^^^^^^^

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.arc

    The `auto_ack` attribute must be enabled on the receiving nRF24L01's pipe 0 & the
    RX data pipe and the transmitting nRF24L01's pipe 0 to properly use this
    attribute. If `auto_ack` is disabled on the transmitting nRF24L01's pipe 0, then this
    attribute is ignored when calling `send()`.

    A valid input value will be clamped to range [0, 15]. Default is set to 3. A value of
    ``0`` disables the automatic re-transmit feature, but the sending nRF24L01 will still
    wait the number of microseconds specified by `ard` for an Acknowledgement (ACK) packet
    response (assuming `auto_ack` is enabled).

    .. versionchanged:: 2.0.0
        invalid input values are clamped to proper range instead of throwing a `ValueError`
        exception.

ard
^^^^^^^^^^^^^^^^^^^^^^^

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.ard

    During this time, the nRF24L01 is listening for the ACK packet. If the
    `auto_ack` attribute is disabled for pipe 0, then this attribute is not applied.

    A valid input value will be clamped to range [250, 4000]. Default is 1500 for
    reliability. If this is set to a value that is not multiple of 250, then the highest
    multiple of 250 that is no greater than the input value is used.

    .. note:: Paraphrased from nRF24L01 specifications sheet:

        Please take care when setting this parameter. If the custom ACK payload is more than
        15 bytes in 2 Mbps data rate, the `ard` must be 500µS or more. If the custom ACK
        payload is more than 5 bytes in 1 Mbps data rate, the `ard` must be 500µS or more.
        In 250kbps data rate (even when there is no custom ACK payload) the `ard` must be
        500µS or more.

        See `data_rate` attribute on how to set the data rate of the nRF24L01's transmissions.
    .. versionchanged:: 2.0.0
        invalid input values are clamped to proper range instead of throwing a `ValueError`
        exception.

set_auto_retries()
^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.set_auto_retries

    :param int delay: accepts the same input as the `ard` attribute.
    :param int count: accepts the same input as the `arc` attribute.

get_auto_retries()
^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: circuitpython_nrf24l01.rf24.RF24.get_auto_retries

    :Return:
        A tuple containing 2 items; index 0 will be the `ard` attribute,
        and index 1 will be the `arc` attribute.

ack
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.ack

    Use this attribute to set/check if the custom ACK payloads feature is
    enabled (`True`) or disabled (`False`). Default
    setting is `False`.

    .. note:: This attribute differs from the `auto_ack` attribute because the
        `auto_ack` attribute enables or disables the use of automatic ACK *packets*. By default,
        ACK *packets* have no *payload*. This attribute enables or disables attaching
        payloads to the ACK packets.
    .. seealso::
        Use `load_ack()` attach ACK payloads.

        Use `read()`, `send()`, `resend()` to retrieve ACK payloads.
    .. important::
        As `dynamic_payloads` and `auto_ack` attributes are required for this feature to work,
        they are automatically enabled (on data pipe 0) as needed. However, it is required to
        enable the `auto_ack` and `dynamic_payloads` features on all applicable pipes.
        Disabling this feature does not disable the `auto_ack` and `dynamic_payloads`
        attributes for any data pipe; they work just fine without this feature.

allow_ask_no_ack
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.allow_ask_no_ack

    This attribute is enabled by default, and it only exists to provide support for the
    Si24R1. The designers of the Si24R1 (a cheap chinese clone of the nRF24L01) happened to
    clone a typo from the first version of the nRF24L01 specification sheet. Disable this attribute for the Si24R1.

interrupt_config()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.interrupt_config

    The digital signal from the nRF24L01's IRQ (Interrupt ReQuest) pin is active LOW.

    :param bool data_recv: If this is `True`, then IRQ pin goes active when new data is put
        into the RX FIFO buffer. Default setting is `True`
    :param bool data_sent: If this is `True`, then IRQ pin goes active when a payload from TX
        buffer is successfully transmit. Default setting is `True`
    :param bool data_fail: If this is `True`, then IRQ pin goes active when the maximum
        number of attempts to re-transmit the packet have been reached. If `auto_ack`
        attribute is disabled for pipe 0, then this IRQ event is not used. Default setting
        is `True`

    .. note:: To fetch the status (not configuration) of these IRQ flags, use the `irq_df`,
        `irq_ds`, `irq_dr` attributes respectively.

    .. tip:: Paraphrased from nRF24L01+ Specification Sheet:

        The procedure for handling :py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_dr` IRQ
        should be:

        1. retreive the payload from RX FIFO using `read()`
        2. clear :py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_dr` status flag (taken care
           of by using `read()` in previous step)
        3. read FIFO_STATUS register to check if there are more payloads available in RX FIFO
           buffer. A call to `pipe` (may require `update()` to be called beforehand), `any()`
           or even ``(False, True)`` as parameters to `fifo()` will get this result.
        4. if there is more data in RX FIFO, repeat from step 1

data_rate
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.data_rate

    A valid input value is:

    - ``1`` sets the frequency data rate to 1 Mbps
    - ``2`` sets the frequency data rate to 2 Mbps
    - ``250`` sets the frequency data rate to 250 Kbps (see warning below)

    Any invalid input throws a `ValueError` exception. Default is 1 Mbps.

    .. warning:: 250 Kbps is not available for the non-plus variants of the
        nRF24L01 transceivers. Trying to set the data rate to 250 kpbs when
        `is_plus_variant` is `True` will throw a `NotImplementedError`.

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

    Any invalid input will be clamped to range [0, 2]. Default is enabled using 2 bytes.

    .. note:: The nRF24L01 automatically enables CRC if automatic acknowledgment feature is
        enabled (see `auto_ack` attribute) for any data pipe.
    .. versionchanged:: 2.0.0
        invalid input values are clamped to proper range instead of throwing a `ValueError`
        exception.

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

    .. note:: The LNA feature setting only applies to the nRF24L01 (non-plus variant).

    Any invalid input will invoke the default of 0 dBm with LNA enabled.

is_lna_enabled
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.is_lna_enabled

    See `pa_level` attribute about how to set this. Default is always enabled, but this
    feature is specific to non-plus variants of nRF24L01 transceivers. If
    `is_plus_variant` attribute is `True`, then setting feature in any way has no affect.
