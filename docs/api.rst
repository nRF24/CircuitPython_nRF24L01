
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

Contructor
******************

.. autoclass:: circuitpython_nrf24l01.rf24.RF24
  :no-members:

  A driver class for the nRF24L01(+) transceiver radios. This class aims to be compatible with
  other devices in the nRF24xxx product line that implement the Nordic proprietary Enhanced
  ShockBurst Protocol (and/or the legacy ShockBurst Protocol), but officially only supports
  (through testing) the nRF24L01 and nRF24L01+ devices.

  :param ~busio.SPI spi: The object for the SPI bus that the nRF24L01 is connected to.

      .. tip:: This object is meant to be shared amongst other driver classes (like
          adafruit_mcp3xxx.mcp3008 for example) that use the same SPI bus. Otherwise, multiple
          devices on the same SPI bus with different spi objects may produce errors or
          undesirable behavior.
  :param ~digitalio.DigitalInOut csn: The digital output pin that is connected to the nRF24L01's
      CSN (Chip Select Not) pin. This is required.
  :param ~digitalio.DigitalInOut ce: The digital output pin that is connected to the nRF24L01's
      CE (Chip Enable) pin. This is required.
  :param int channel: This is used to specify a certain radio frequency that the nRF24L01 uses.
      Defaults to 76 and can be changed at any time by using the `channel` attribute.
  :param int payload_length: This is the length (in bytes) of a single payload to be transmitted
      or received. This is ignored if the `dynamic_payloads` attribute is enabled. Defaults to 32
      and must be in range [1,32]. This can be changed at any time by using the `payload_length`
      attribute.
  :param int address_length: This is the length (in bytes) of the addresses that are assigned to
      the data pipes for transmitting/receiving. Defaults to 5 and must be in range [3,5]. This
      can be changed at any time by using the `address_length` attribute.
  :param int ard: This specifies the delay time (in µs) between attempts to automatically
      re-transmit. This can be changed at any time by using the `ard` attribute. This parameter
      must be a multiple of 250 in the range [250,4000]. Defualts to 1500 µs.
  :param int arc: This specifies the automatic re-transmit count (maximum number of automatically
      attempts to re-transmit). This can be changed at any time by using the `arc` attribute.
      This parameter must be in the range [0,15]. Defaults to 3.
  :param int crc: This parameter controls the CRC setting of transmitted packets. Options are
      ``0`` (off), ``1`` or ``2`` (byte long CRC enabled). This can be changed at any time by
      using the `crc` attribute. Defaults to 2.
  :param int data_rate: This parameter controls the RF data rate setting of transmissions.
      Options are ``1`` (Mbps), ``2`` (Mbps), or ``250`` (Kbps). This can be changed at any time
      by using the `data_rate` attribute. Defaults to 1.
  :param int pa_level: This parameter controls the RF power amplifier setting of transmissions.
      Options are ``0`` (dBm), ``-6`` (dBm), ``-12`` (dBm), or ``-18`` (dBm). This can be changed
      at any time by using the `pa_level` attribute. Defaults to 0.
  :param bool dynamic_payloads: This parameter enables/disables the dynamic payload length
      feature of the nRF24L01. Defaults to enabled. This can be changed at any time by using the
      `dynamic_payloads` attribute.
  :param bool auto_ack: This parameter enables/disables the automatic acknowledgment (ACK)
      feature of the nRF24L01. Defaults to enabled if `dynamic_payloads` is enabled. This can be
      changed at any time by using the `auto_ack` attribute.
  :param bool ask_no_ack: This represents a special flag that has to be thrown to enable a
      feature specific to individual payloads. Setting this parameter only enables access to this
      feature; it does not invoke it (see parameters for `send()` or `write()` functions).
      Enabling/Disabling this does not affect `auto_ack` attribute.
  :param bool ack: This represents a special flag that has to be thrown to enable a feature
      allowing custom response payloads appended to the ACK packets. Enabling this also requires
      the `auto_ack` attribute enabled. This can be changed at any time by using the `ack`
      attribute.
  :param bool irq_dr: When "Data is Ready", this configures the interrupt (IRQ) trigger of the
      nRF24L01's IRQ pin (active low). Defaults to enabled. This can be changed at any time by
      using the `interrupt_config()` function.
  :param bool irq_ds: When "Data is Sent", this configures the interrupt (IRQ) trigger of the
      nRF24L01's IRQ pin (active low). Defaults to enabled. This can be changed at any time by
      using the `interrupt_config()` function.
  :param bool irq_df: When "max retry attempts are reached" (specified by the `arc` attribute),
      this configures the interrupt (IRQ) trigger of the nRF24L01's IRQ pin (active low) and
      represents transmission failure. Defaults to enabled. This can be changed at any time by
      using the `interrupt_config()` function.

address_length
******************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.address_length

  This `int` attribute specifies the length (in bytes) of addresses to be used for RX/TX
  pipes. The addresses assigned to the data pipes must have byte length equal to the value
  set for this attribute.

  A valid input value must be an `int` in range [3,5]. Otherwise a `ValueError` exception is
  thrown. Default is set to the nRF24L01's maximum of 5.

open_tx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.open_tx_pipe

  This function is used to open a data pipe for OTA (over the air) TX transmissions.

  :param bytearray address: The virtual address of the receiving nRF24L01. This must have a
      length equal to the `address_length` attribute (see `address_length` attribute).
      Otherwise a `ValueError` exception is thrown. The address specified here must match the
      address set to one of the RX data pipes of the receiving nRF24L01.

  .. note:: There is no option to specify which data pipe to use because the nRF24L01 only
      uses data pipe 0 in TX mode. Additionally, the nRF24L01 uses the same data pipe (pipe
      0) for receiving acknowledgement (ACK) packets in TX mode when the `auto_ack` attribute
      is enabled. Thus, RX pipe 0 is appropriated with the TX address (specified here) when
      `auto_ack` is set to `True`.

close_rx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.close_rx_pipe

  This function is used to close a specific data pipe from OTA (over the air) RX
  transmissions.

  :param int pipe_number: The data pipe to use for RX transactions. This must be in range
      [0,5]. Otherwise a `ValueError` exception is thrown.
  :param bool reset: `True` resets the address for the specified ``pipe_number`` to the
      factory address (different for each pipe). `False` leaves the address on the specified
      ``pipe_number`` alone. Be aware that the addresses will remain despite loss of power.

open_rx_pipe()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.open_rx_pipe

  This function is used to open a specific data pipe for OTA (over the air) RX
  transmissions. If `dynamic_payloads` attribute is `False`, then the `payload_length`
  attribute is used to specify the expected length of the RX payload on the specified data
  pipe.

  :param int pipe_number: The data pipe to use for RX transactions. This must be in range
      [0,5]. Otherwise a `ValueError` exception is thrown.
  :param bytearray address: The virtual address to the receiving nRF24L01. This must have a
      byte length equal to the `address_length` attribute. Otherwise a `ValueError`
      exception is thrown. If using a ``pipe_number`` greater than 1, then only the MSByte
      of the address is written, so make sure MSByte (first character) is unique among other
      simultaneously receiving addresses).

  .. note:: The nRF24L01 shares the addresses' LSBytes (address[1:5]) on data pipes 2 through
      5. These shared LSBytes are determined by the address set to pipe 1.

listen
******************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.listen

  An attribute to represent the nRF24L01 primary role as a radio.

  Setting this attribute incorporates the proper transitioning to/from RX mode as it involves
  playing with the `power` attribute and the nRF24L01's CE pin. This attribute does not power
  down the nRF24L01, but will power it up when needed; use `power` attribute set to `False`
  to put the nRF24L01 to sleep.

  A valid input value is a `bool` in which:

      `True` enables RX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications
      Sheet
      <https://www.sparkfun.com/datasheets/Components/SMD/
      nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this attribute
      flushes the RX FIFO, clears the `irq_dr` status flag, and puts nRF24L01 in power up
      mode. Notice the CE pin is be held HIGH during RX mode.

      `False` disables RX mode. As mentioned in above link, this puts nRF24L01's power in
      Standby-I (CE pin is LOW meaning low current & no transmissions) mode which is ideal
      for post-reception work. Disabing RX mode doesn't flush the RX/TX FIFO buffers, so
      remember to flush your 3-level FIFO buffers when appropriate using `flush_tx()` or
      `flush_rx()` (see also the `recv()` function).

any()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.any

  This function checks if the nRF24L01 has received any data at all, and then reports the
  next available payload's length (in bytes) -- if there is any.

  :returns:
      - `int` of the size (in bytes) of an available RX payload (if any).
      - ``0`` if there is no payload in the RX FIFO buffer.

recv()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.recv

  This function is used to retrieve the next available payload in the RX FIFO buffer, then
  clears the `irq_dr` status flag. This function synonomous to `read_ack()`.

  :returns: A `bytearray` of the RX payload data or `None` if there is no payload

      - If the `dynamic_payloads` attribute is disabled, then the returned bytearray's length
        is equal to the user defined `payload_length` attribute (which defaults to 32).
      - If the `dynamic_payloads` attribute is enabled, then the returned bytearray's length
        is equal to the payload's length

send()
******************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.send

  This blocking function is used to transmit payload(s).

  :returns:
      * `list` if a list or tuple of payloads was passed as the ``buf`` parameter. Each item
        in the returned list will contain the returned status for each corresponding payload
        in the list/tuple that was passed. The return statuses will be in one of the
        following forms:
      * `False` if transmission fails or reaches the timeout sentinal. The timeout condition
        is very rare and could mean something/anything went wrong with either/both TX/RX
        transceivers. The timeout sentinal for transmission is calculated using `table 18 in
        the nRF24L01 specification sheet <https://www.sparkfun.com/datasheets/Components/SMD/
        nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1123001>`_.
        Transmission failure can only be returned if `arc` is greater than ``0``.
      * `True` if transmission succeeds.
      * `bytearray` or `None` when the `ack` attribute is `True`. Because the payload expects
        a responding custom ACK payload, the response is returned (upon successful
        transmission) as a
        `bytearray` (or `None` if ACK payload is empty)

  :param bytearray,list,tuple buf: The payload to transmit. This bytearray must have a length
      greater than 0 and less than 32, otherwise a `ValueError` exception is thrown. This can
      also be a list or tuple of payloads (`bytearray`); in which case, all items in the
      list/tuple are processed for consecutive transmissions.

      - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less
        than the `payload_length` attribute, then this bytearray is padded with zeros until
        its length is equal to the `payload_length` attribute.
      - If the `dynamic_payloads` attribute is disabled and this bytearray's length is
        greater than `payload_length` attribute, then this bytearray's length is truncated to
        equal the `payload_length` attribute.
  :param bool ask_no_ack: Pass this parameter as `True` to tell the nRF24L01 not to wait for
      an acknowledgment from the receiving nRF24L01. This parameter directly controls a
      ``NO_ACK`` flag in the transmission's Packet Control Field (9 bits of information about
      the payload). Therefore, it takes advantage of an nRF24L01 feature specific to
      individual payloads, and its value is not saved anywhere. You do not need to specify
      this for every payload if the `arc` attribute is disabled, however this parameter
      will work despite the `arc` attribute's setting.

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
      `resend()` as using this parameter carries the same implications documented there.

  .. tip:: It is highly recommended that `arc` attribute is enabled when sending
      multiple payloads. Test results with the `arc` attribute disabled were very poor
      (much < 50% received). This same advice applies to the ``ask_no_ack`` parameter (leave
      it as `False` for multiple payloads).
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

  This debuggung function aggregates and outputs all status/condition related information
  from the nRF24L01. Some information may be irrelevant depending on nRF24L01's
  state/condition.

  :prints:

      - ``Channel`` The current setting of the `channel` attribute
      - ``RF Data Rate`` The current setting of the RF `data_rate` attribute.
      - ``RF Power Amplifier`` The current setting of the `pa_level` attribute.
      - ``CRC bytes`` The current setting of the `crc` attribute
      - ``Address length`` The current setting of the `address_length` attribute
      - ``Payload lengths`` The current setting of the `payload_length` attribute
      - ``Auto retry delay`` The current setting of the `ard` attribute
      - ``Auto retry attempts`` The current setting of the `arc` attribute
      - ``Packets lost on current channel`` Total amount of packets lost (transmission
        failures). This only resets when the `channel` is changed. This count will
        only go up 15.
      - ``Retry attempts made for last transmission`` Amount of attempts to re-transmit
        during last
        transmission (resets per payload)
      - ``IRQ - Data Ready`` The current setting of the IRQ pin on "Data Ready" event
      - ``IRQ - Data Sent`` The current setting of the IRQ pin on "Data Sent" event
      - ``IRQ - Data Fail`` The current setting of the IRQ pin on "Data Fail" event
      - ``Data Ready`` Is there RX data ready to be read?
        (state of the `irq_dr` flag)
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
      - ``Automatic Acknowledgment`` Is the `auto_ack` attribute enabled?
      - ``Dynamic Payloads`` Is the `dynamic_payloads` attribute enabled?
      - ``Primary Mode`` The current mode (RX or TX) of communication of the nRF24L01 device.
      - ``Power Mode`` The power state can be Off, Standby-I, Standby-II, or On.

  :param bool dump_pipes: `True` appends the output and prints:

      * the current address used for TX transmissions
      * ``Pipe [#] ([open/closed]) bound: [address]`` where ``#`` represent the pipe number,
        the ``open/closed`` status is relative to the pipe's RX status, and ``address`` is
        read directly from the nRF24L01 registers.
      * if the pipe is open, then the output also prints ``expecting [X] byte static
        payloads`` where ``X`` is the `payload_length` (in bytes) the pipe is setup to
        receive when `dynamic_payloads` is disabled.

      Default is `False` and skips this extra information.

dynamic_payloads
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.dynamic_payloads

  This `bool` attribute controls the nRF24L01's dynamic payload length feature.

  - `True` enables nRF24L01's dynamic payload length feature. The `payload_length`
    attribute is ignored when this feature is enabled.
  - `False` disables nRF24L01's dynamic payload length feature. Be sure to adjust
    the `payload_length` attribute accordingly when `dynamic_payloads` feature is disabled.

payload_length
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.payload_length

  This `int` attribute specifies the length (in bytes) of payload that is regarded,
  meaning "how big of a payload should the radio care about?" If the `dynamic_payloads`
  attribute is enabled, this attribute has no affect. When `dynamic_payloads` is disabled,
  this attribute is used to specify the payload length when entering RX mode.

  A valid input value must be an `int` in range [1,32]. Otherwise a `ValueError` exception is
  thrown. Default is set to the nRF24L01's maximum of 32.

  .. note:: When `dynamic_payloads` is disabled during transmissions:

      - Payloads' size of greater than this attribute's value will be truncated to match.
      - Payloads' size of less than this attribute's value will be padded with zeros to
        match.

auto_ack
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.auto_ack

  This `bool` attribute controls the nRF24L01's automatic acknowledgment feature during
  the process of receiving a packet.

  - `True` enables transmitting automatic acknowledgment packets. The CRC (cyclic redundancy
    checking) is enabled automatically by the nRF24L01 if the `auto_ack` attribute is enabled
    (see also `crc` attribute).
  - `False` disables transmitting automatic acknowledgment packets. The `crc` attribute will
    remain unaffected when disabling the `auto_ack` attribute.

arc
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.arc

  This `int` attribute specifies the nRF24L01's number of attempts to re-transmit TX
  payload when acknowledgment packet is not received. The `auto_ack` must be enabled on the
  receiving nRF24L01, otherwise this attribute will make `send()` seem like it failed.

  A valid input value must be in range [0,15]. Otherwise a `ValueError` exception is thrown.
  Default is set to 3. A value of ``0`` disables the automatic re-transmit feature and
  considers all payload transmissions a success.

ard
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.ard

  This `int` attribute specifies the nRF24L01's delay (in µs) between attempts to
  automatically re-transmit the TX payload when an expected acknowledgement (ACK) packet is
  not received. During this time, the nRF24L01 is listening for the ACK packet. If the
  `auto_ack` attribute is disabled, this attribute is not applied.

  A valid input value must be a multiple of 250 in range [250,4000]. Otherwise a `ValueError`
  exception is thrown. Default is 1500 for reliability.

  .. note:: Paraphrased from nRF24L01 specifications sheet:

      Please take care when setting this parameter. If the custom ACK payload is more than 15
      bytes in 2 Mbps data rate, the `ard` must be 500µS or more. If the custom ACK payload
      is more than 5 bytes in 1 Mbps data rate, the `ard` must be 500µS or more. In 250kbps
      data rate (even when there is no custom ACK payload) the `ard` must be 500µS or more.

      See `data_rate` attribute on how to set the data rate of the nRF24L01's transmissions.

ack
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.ack

  This `bool` attribute represents the status of the nRF24L01's capability to use custom
  payloads as part of the automatic acknowledgment (ACK) packet. Use this attribute to
  set/check if the custom ACK payloads feature is enabled.

  - `True` enables the use of custom ACK payloads in the ACK packet when responding to
    receiving transmissions. As `dynamic_payloads` and `auto_ack` attributes are required for
    this feature to work, they are automatically enabled as needed.
  - `False` disables the use of custom ACK payloads. Disabling this feature does not disable
    the `auto_ack` and `dynamic_payloads` attributes (they work just fine without this
    feature).

load_ack()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.load_ack

  This allows the MCU to specify a payload to be allocated into the TX FIFO buffer for use
  on a specific data pipe. This payload will then be appended to the automatic acknowledgment
  (ACK) packet that is sent when fresh data is received on the specified pipe. See
  `read_ack()` on how to fetch a received custom ACK payloads.

  :param bytearray buf: This will be the data attached to an automatic ACK packet on the
      incoming transmission about the specified ``pipe_number`` parameter. This must have a
      length in range [1,32] bytes, otherwise a `ValueError` exception is thrown. Any ACK
      payloads will remain in the TX FIFO buffer until transmitted successfully or
      `flush_tx()` is called.
  :param int pipe_number: This will be the pipe number to use for deciding which
      transmissions get a response with the specified ``buf`` parameter's data. This number
      must be in range [0,5], otherwise a `ValueError` exception is thrown.

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

  Allows user to read the automatic acknowledgement (ACK) payload (if any) when nRF24L01
  is in TX mode. This function is called from a blocking `send()` call if the `ack` attribute
  is enabled. Alternatively, this function can be called directly in case of calling the
  non-blocking `write()` function during asychronous applications. This function is an alias
  of `recv()` and remains for bakward compatibility with older versions of this library.

  .. note:: See also the `ack`, `dynamic_payloads`, and `auto_ack` attributes as they must be
      enabled to use custom ACK payloads.

irq_dr
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_dr

  A `bool` that represents the "Data Ready" interrupted flag. (read-only)

  * `True` represents Data is in the RX FIFO buffer
  * `False` represents anything depending on context (state/condition of FIFO buffers) --
    usually this means the flag's been reset.

  Pass ``dataReady`` parameter as `True` to `clear_status_flags()` and reset this. As this is
  a virtual representation of the interrupt event, this attribute will always be updated
  despite what the actual IRQ pin is configured to do about this event.

  Calling this does not execute an SPI transaction. It only exposes that latest data
  contained in the STATUS byte that's always returned from any other SPI transactions. Use
  the `update()` function to manually refresh this data when needed.

irq_df
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_df

  A `bool` that represents the "Data Failed" interrupted flag. (read-only)

  * `True` signifies the nRF24L01 attemped all configured retries
  * `False` represents anything depending on context (state/condition) -- usually this means
    the flag's been reset.

  Pass ``dataFail`` parameter as `True` to `clear_status_flags()` to reset this. As this is a
  virtual representation of the interrupt event, this attribute will always be updated
  despite what the actual IRQ pin is configured to do about this event.see also the `arc` and
  `ard` attributes.

  Calling this does not execute an SPI transaction. It only exposes that latest data
  contained in the STATUS byte that's always returned from any other SPI transactions. Use
  the `update()` function to manually refresh this data when needed.

irq_ds
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.irq_ds

  A `bool` that represents the "Data Sent" interrupted flag. (read-only)

  * `True` represents a successful transmission
  * `False` represents anything depending on context (state/condition of FIFO buffers) --
    usually this means the flag's been reset.

  Pass ``dataSent`` parameter as `True` to `clear_status_flags()` to reset this. As this is a
  virtual representation of the interrupt event, this attribute will always be updated
  despite what the actual IRQ pin is configured to do about this event.

  Calling this does not execute an SPI transaction. It only exposes that latest data
  contained in the STATUS byte that's always returned from any other SPI transactions. Use
  the `update()` function to manually refresh this data when needed.

clear_status_flags()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.clear_status_flags

  This clears the interrupt flags in the status register. Internally, this is
  automatically called by `send()`, `write()`, `recv()`, and when `listen` changes from
  `False` to `True`.

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

interrupt_config()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.interrupt_config

  Sets the configuration of the nRF24L01's IRQ (interrupt) pin. The signal from the
  nRF24L01's IRQ pin is active LOW. (write-only)

  :param bool data_recv: If this is `True`, then IRQ pin goes active when there is new data
      to read in the RX FIFO buffer.
  :param bool data_sent: If this is `True`, then IRQ pin goes active when a payload from TX
      buffer is successfully transmit.
  :param bool data_fail: If this is `True`, then IRQ pin goes active when maximum number of
      attempts to re-transmit the packet have been reached. If `auto_ack` attribute is
      disabled, then this IRQ event is not used.

  .. note:: To fetch the status (not configuration) of these IRQ flags, use the `irq_df`,
      `irq_ds`, `irq_dr` attributes respectively.

  .. tip:: Paraphrased from nRF24L01+ Specification Sheet:

      The procedure for handling ``data_recv`` IRQ should be:

      1. read payload through `recv()`
      2. clear ``dataReady`` status flag (taken care of by using `recv()` in previous step)
      3. read FIFO_STATUS register to check if there are more payloads available in RX FIFO
          buffer. (a call to `pipe()`, `any()` or even ``(False,True)`` as parameters to
          `fifo()` will get this result)
      4. if there is more data in RX FIFO, repeat from step 1

data_rate
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.data_rate

  This `int` attribute specifies the nRF24L01's frequency data rate for OTA (over the air)
  transmissions.

  A valid input value is:

  - ``1`` sets the frequency data rate to 1 Mbps
  - ``2`` sets the frequency data rate to 2 Mbps
  - ``250`` sets the frequency data rate to 250 Kbps

  Any invalid input throws a `ValueError` exception. Default is 1 Mbps.

  .. warning:: 250 Kbps is be buggy on the non-plus models of the nRF24L01 product line. If
      you use 250 Kbps data rate, and some transmissions report failed by the transmitting
      nRF24L01, even though the same packet in question actually reports received by the
      receiving nRF24L01, then try a higher data rate. CAUTION: Higher data rates mean less
      maximum distance between nRF24L01 transceivers (and vise versa).

channel
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.channel

  This `int` attribute specifies the nRF24L01's frequency (in 2400 + `channel` MHz).

  A valid input value must be in range [0, 125] (that means [2.4, 2.525] GHz). Otherwise a
  `ValueError` exception is thrown. Default is 76.

crc
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.crc

  This `int` attribute specifies the nRF24L01's CRC (cyclic redundancy checking) encoding
  scheme in terms of byte length. CRC is a way of making sure that the transmission didn't
  get corrupted over the air.

  A valid input value is in range [0,2]:

  - ``0`` disables CRC (no anti-corruption of data)
  - ``1`` enables CRC encoding scheme using 1 byte (weak anti-corruption of data)
  - ``2`` enables CRC encoding scheme using 2 bytes (better anti-corruption of data)

  Any invalid input throws a `ValueError` exception. Default is enabled using 2 bytes.

  .. note:: The nRF24L01 automatically enables CRC if automatic acknowledgment feature is
      enabled (see `auto_ack` attribute).

power
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.power

  This `bool` attribute controls the power state of the nRF24L01. This is exposed for
  asynchronous applications and user preference.

  - `False` basically puts the nRF24L01 to sleep (AKA power down mode) with ultra-low
    current consumption. No transmissions are executed when sleeping, but the nRF24L01 can
    still be accessed through SPI. Upon instantiation, this driver class puts the nRF24L01
    to sleep until the MCU invokes RX/TX transmissions. This driver class doesn't power down
    the nRF24L01 after RX/TX transmissions are complete (avoiding the required power up/down
    130 µs wait time), that preference is left to the user.
  - `True` powers up the nRF24L01. This is the first step towards entering RX/TX modes (see
    also `listen` attribute). Powering up is automatically handled by the `listen` attribute
    as well as the `send()` and `write()` functions.

  .. note:: This attribute needs to be `True` if you want to put radio on Standby-II (highest
      current consumption) or Standby-I (moderate current consumption) modes. TX
      transmissions are only executed during Standby-II by calling `send()` or `write()`. RX
      transmissions are received during Standby-II by setting `listen` attribute to `True`
      (see `Chapter 6.1.2-7 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/
      datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0
      .pdf#G1132980>`_). After using `send()` or setting `listen` to `False`, the nRF24L01
      is left in Standby-I mode (see also notes on the `write()` function).

pa_level
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.pa_level

  This `int` attribute specifies the nRF24L01's power amplifier level (in dBm). Higher
  levels mean the transmission will cover a longer distance. Use this attribute to tweak the
  nRF24L01 current consumption on projects that don't span large areas.

  A valid input value is:

  - ``-18`` sets the nRF24L01's power amplifier to -18 dBm (lowest)
  - ``-12`` sets the nRF24L01's power amplifier to -12 dBm
  - ``-6`` sets the nRF24L01's power amplifier to -6 dBm
  - ``0`` sets the nRF24L01's power amplifier to 0 dBm (highest)

  Any invalid input throws a `ValueError` exception. Default is 0 dBm.

tx_full
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.tx_full

  An attribute to represent the nRF24L01's status flag signaling that the TX FIFO buffer
  is full. (read-only)

  Calling this does not execute an SPI transaction. It only exposes that latest data
  contained in the STATUS byte that's always returned from any SPI transactions with the
  nRF24L01. Use the `update()` function to manually refresh this data when needed.

  :returns:
      * `True` for TX FIFO buffer is full
      * `False` for TX FIFO buffer is not full. This doesn't mean the TX FIFO buffer is
        empty.

rpd
******************************

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.rpd

  This read-only attribute returns `True` if RPD (Received Power Detector) is triggered
  or `False` if not triggered.

  .. note:: The RPD flag is triggered in the following cases:

      1. During RX mode (`listen` = `True`) and a RF transmission with a gain above a preset
          (non-adjustable) -64 dBm threshold.
      2. When a packet is received (indicative of the nRF24L01 used to detect/"listen" for
          incoming packets).
      3. When the nRF24L01's CE pin goes from HIGH to LOW (or when the `listen` attribute
          changes from `True` to `False`).
      4. When the underlying ESB (Enhanced ShockBurst) protocol reaches a hardcoded
          (non-adjustable) RX timeout.

update()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.update

  This function is only used to get an updated status byte over SPI from the nRF24L01 and
  is exposed to the MCU for asynchronous applications. Refreshing the status byte is vital to
  checking status of the interrupts, RX pipe number related to current RX payload, and if the
  TX FIFO buffer is full. This function returns nothing, but internally updates the `irq_dr`,
  `irq_ds`, `irq_df`, and `tx_full` attributes. Internally this is a helper function to
  `pipe()`, `send()`, and `resend()` functions

resend()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.resend

  Use this function to maunally re-send the previous payload in the
  top level (first out) of the TX FIFO buffer. All returned data follows the same patttern
  that `send()` returns with the added condition that this function will return `False`
  if the TX FIFO buffer is empty.

  .. note:: The nRF24L01 normally removes a payload from the TX FIFO buffer after successful
      transmission, but not when this function is called. The payload (successfully
      transmitted or not) will remain in the TX FIFO buffer until `flush_tx()` is called to
      remove them. Alternatively, using this function also allows the failed payload to be
      over-written by using `send()` or `write()` to load a new payload.

write()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.write

  This non-blocking function (when used as alternative to `send()`) is meant for
  asynchronous applications and can only handle one payload at a time as it is a helper
  function to `send()`.

  :param bytearray buf: The payload to transmit. This bytearray must have a length greater
      than 0 and less than 32 bytes, otherwise a `ValueError` exception is thrown.

      - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less
        than the `payload_length` attribute, then this bytearray is padded with zeros until
        its length is equal to the `payload_length` attribute.
      - If the `dynamic_payloads` attribute is disabled and this bytearray's length is
        greater than `payload_length` attribute, then this bytearray's length is truncated to
        equal the `payload_length` attribute.
  :param bool ask_no_ack: Pass this parameter as `True` to tell the nRF24L01 not to wait for
      an acknowledgment from the receiving nRF24L01. This parameter directly controls a
      ``NO_ACK`` flag in the transmission's Packet Control Field (9 bits of information about
      the payload). Therefore, it takes advantage of an nRF24L01 feature specific to
      individual payloads, and its value is not saved anywhere. You do not need to specify
      this for every payload if the `auto_ack` attribute is disabled, however this parameter
      should work despite the `auto_ack` attribute's setting.

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

  .. warning:: A note paraphrased from the `nRF24L01+ Specifications Sheet <https://www.
      sparkfun.com/datasheets/Components/SMD/
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
      in the nRF24L01 specification sheet <https://www.sparkfun.com/datasheets/Components/SMD/
      nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1123001>`_ for calculating
      necessary transmission time (these calculations are used in the `send()` and `resend()`
      functions).

flush_rx()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.flush_rx

  A helper function to flush the nRF24L01's internal RX FIFO buffer. (write-only)

  .. note:: The nRF24L01 RX FIFO is 3 level stack that holds payload data. This means that
      there can be up to 3 received payloads (each of a maximum length equal to 32 bytes)
      waiting to be read (and popped from the stack) by `recv()` or `read_ack()`. This
      function clears all 3 levels.

flush_tx()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.flush_tx

  A helper function to flush the nRF24L01's internal TX FIFO buffer. (write-only)

  .. note:: The nRF24L01 TX FIFO is 3 level stack that holds payload data. This means that
      there can be up to 3 payloads (each of a maximum length equal to 32 bytes) waiting to
      be transmit by `send()`, `resend()` or `write()`. This function clears all 3 levels. It
      is worth noting that the payload data is only popped from the TX FIFO stack upon
      successful transmission (see also `resend()` as the handling of failed transmissions
      can be altered).

fifo()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.fifo

  This provides some precision determining the status of the TX/RX FIFO buffers.
  (read-only)

  :param bool about_tx:
      * `True` means information returned is about the TX FIFO buffer.
      * `False` means information returned is about the RX FIFO buffer. This parameter
        defaults to `False` when not specified.
  :param bool check_empty:
      * `True` tests if the specified FIFO buffer is empty.
      * `False` tests if the specified FIFO buffer is full.
      * `None` (when not specified) returns a 2 bit number representing both empty (bit 1) &
        full (bit 0) tests related to the FIFO buffer specified using the ``tx`` parameter.
  :returns:
      * A `bool` answer to the question:
        "Is the [TX/RX]:[`True`/`False`] FIFO buffer [empty/full]:[`True`/`False`]?
      * If the ``check_empty`` parameter is not specified: an `int` in range [0,2] for which:

        - ``1`` means the specified FIFO buffer is full
        - ``2`` means the specified FIFO buffer is empty
        - ``0`` means the specified FIFO buffer is neither full nor empty

pipe()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.pipe

  This function returns information about the data pipe that received the next available
  payload in the RX FIFO buffer.

  :returns:
      - `None` if there is no payload in RX FIFO.
      - The `int` identifying pipe number [0,5] that received the next available payload in
        the RX FIFO buffer.

address()
******************************

.. automethod:: circuitpython_nrf24l01.rf24.RF24.address

  Returns the current address set to a specified data pipe or the TX address. (read-only)

  :param int index: the number of the data pipe whose address is to be returned. Defaults to
      ``-1``. A valid index ranges [0,5] for RX addresses or any negative `int` for the TX
      address. Otherwise an `IndexError` is thown.
