
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
      `payload_length` attribute is ignored when this feature is enabled for all
      respective data pipes.
    - `False` or ``0`` disables nRF24L01's dynamic payload length feature for all data pipes.
      Be sure to adjust the `payload_length` attribute accordingly when this feature is
      disabled for any data pipes.
    - A `list` or `tuple` containing booleans or integers can be used control this feature per
      data pipe. Index 0 controls this feature on data pipe 0. Indices greater than 5 will be
      ignored since there are only 6 data pipes.

    .. note::
        This attribute mostly relates to RX operations, but data pipe 0 applies to TX
        operations also. The `auto_ack` attribute is set accordingly for data pipes that
        have this feature enabled. Disabling this feature for any data pipe will not
        affect the `auto_ack` feature for the corresponding data pipes.

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
