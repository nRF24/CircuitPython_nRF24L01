BLE API
=================

.. versionadded:: 1.2.0
    BLE API added

BLE Limitations
---------------

This module uses the `RF24` class to make the nRF24L01 imitate a
Bluetooth-Low-Emissions (BLE) beacon. A BLE beacon can send data (referred to as
advertisements) to any BLE compatible device (ie smart devices with Bluetooth
4.0 or later) that is listening.

Original research was done by `Dmitry Grinberg and his write-up (including C
source code) can be found here
<http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_
As this technique can prove invaluable in certain project designs, the code
here has been adapted to work with CircuitPython.

.. important:: Because the nRF24L01 wasn't designed for BLE advertising, it
    has some limitations that helps to be aware of.

    1. The maximum payload length is shortened to **18** bytes (when not
       broadcasting a device
       :py:attr:`~circuitpython_nrf24l01.fake_ble.FakeBLE.name` nor
       the nRF24L01
       :py:attr:`~circuitpython_nrf24l01.fake_ble.FakeBLE.show_pa_level`).
       This is calculated as:

       **32** (nRF24L01 maximum) - **6** (MAC address) - **5** (required
       flags) - **3** (CRC checksum) = **18**

       Use the helper function
       :py:func:`~circuitpython_nrf24l01.fake_ble.FakeBLE.available()` to
       detirmine if your payload can be transmit.
    2. the channels that BLE use are limited to the following three: 2.402
       GHz, 2.426 GHz, and 2.480 GHz. We have provided a tuple of these
       specific channels for convenience (See `BLE_FREQ` and `hop_channel()`).
    3. :py:attr:`~circuitpython_nrf24l01.rf24.RF24.crc` is disabled in the
       nRF24L01 firmware because BLE  specifications require 3 bytes
       (:py:func:`~circuitpython_nrf24l01.fake_ble.crc24_ble()`), and the
       nRF24L01 firmware can only handle a maximum of 2.
       Thus, we have appended the required 3 bytes of CRC24 into the payload.
    4. :py:attr:`~circuitpython_nrf24l01.rf24.RF24.address_length` of BLE
       packet only uses 4 bytes, so we have set that accordingly.
    5. The :py:attr:`~circuitpython_nrf24l01.rf24.RF24.auto_ack` (automatic
       acknowledgment) feature of the nRF24L01 is useless when tranmitting to
       BLE devices, thus it is disabled as well as automatic re-transmit
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.arc`) and custom ACK
       payloads (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.ack`) features
       which both depend on the automatic acknowledgments feature.
    6. The :py:attr:`~circuitpython_nrf24l01.rf24.RF24.dynamic_payloads`
       feature of the nRF24L01 isn't compatible with BLE specifications. Thus,
       we have disabled it.
    7. BLE specifications only allow using 1 Mbps RF
       :py:attr:`~circuitpython_nrf24l01.rf24.RF24.data_rate`, so that too has
       been hard coded.
    8. Only the "on data sent"
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_ds`) & "on data ready"
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_dr`) events will have
       an effect on the interrupt (IRQ) pin. The "on data fail"
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_df`) is never
       triggered because
       :py:attr:`~circuitpython_nrf24l01.rf24.RF24.arc` attribute is disabled.

helpers
----------------

swap_bits()
*****************

.. autofunction:: circuitpython_nrf24l01.fake_ble.swap_bits

   :returns:
      An `int` containing the byte whose bits are reversed
      compared to the value passed to the ``original`` parameter.
   :param int original: This should be a single unsigned byte, meaning the
      parameters value can only range from 0 to 255.

reverse_bits()
*****************

.. autofunction:: circuitpython_nrf24l01.fake_ble.reverse_bits

   :returns:
      A `bytearray` whose byte order remains the same, but each
      byte's bit order is reversed.
   :param bytearray,bytes original: The original buffer whose bits are to be
      reversed.

chunk()
*****************

.. autofunction:: circuitpython_nrf24l01.fake_ble.chunk

    :param bytearray,bytes buf: The actual data contained in the block.
    :param int data_type: The type of data contained in the chunk. This is a
        predefined number according to BLE specifications. The default value
        ``0x16`` describes all service data. ``0xFF`` describes manufacturer
        information. Any other values are not applicable to BLE
        advertisements.

    .. important:: This function is called internally by
        :py:func:`~circuitpython_nrf24l01.fake_ble.FakeBLE.advertise()`.
        To pack multiple data values into a single payload, use this function
        for each data value and pass a `list` or `tuple` of the returned
        results to
        :py:func:`~circuitpython_nrf24l01.fake_ble.FakeBLE.advertise()`
        (see example code in documentation about
        :py:func:`~circuitpython_nrf24l01.fake_ble.FakeBLE.advertise()`
        for more detail). Remember that broadcasting multiple data values may
        require the :py:attr:`~circuitpython_nrf24l01.fake_ble.FakeBLE.name`
        be set to `None` and/or the
        :py:attr:`~circuitpython_nrf24l01.fake_ble.FakeBLE.show_pa_level` be
        set to `False` for reasons about the payload size with
        `BLE Limitations`_.

crc24_ble()
*****************

.. autofunction:: circuitpython_nrf24l01.fake_ble.crc24_ble

    This is exposed for convenience but should not be used for other buffer
    protocols that require big endian CRC24 format.

    :param bytearray,bytes data: The buffer of data to be uncorrupted.
    :param int deg_poly: A preset "degree polynomial" in which each bit
        represents a degree who's coefficient is 1. BLE specfications require
        ``0x00065b`` (default value).
    :param int init_val: This will be the initial value that the checksum
        will use while shifting in the buffer data. BLE specfications require
        ``0x555555`` (default value).
    :returns: A 24-bit `bytearray` representing the checksum of the data (in
        proper little endian).

BLE_FREQ
*****************

.. autodata:: circuitpython_nrf24l01.fake_ble.BLE_FREQ

    This tuple contains the relative predefined channels used:

    .. csv-table::
        :header: "nRF24L01 channel", "BLE channel"

        2, 37
        26, 38
        80, 39

FakeBLE class
-------------

.. autoclass:: circuitpython_nrf24l01.fake_ble.FakeBLE

    Per the limitations of this technique, only some of underlying
    :py:class:`~circuitpython_nrf24l01.rf24.RF24` functionality is
    available for configuration when implementing BLE transmissions.
    See the `Unavailable RF24 functionality`_ for more details.


    :param ~busio.SPI spi: The object for the SPI bus that the nRF24L01 is connected to.

        .. tip:: This object is meant to be shared amongst other driver classes (like
            adafruit_mcp3xxx.mcp3008 for example) that use the same SPI bus. Otherwise, multiple
            devices on the same SPI bus with different spi objects may produce errors or
            undesirable behavior.
    :param ~digitalio.DigitalInOut csn: The digital output pin that is connected to the nRF24L01's
        CSN (Chip Select Not) pin. This is required.
    :param ~digitalio.DigitalInOut ce_pin: The digital output pin that is connected to the nRF24L01's
        CE (Chip Enable) pin. This is required.
    :param int spi_frequency: Specify which SPI frequency (in Hz) to use on the SPI bus. This
        parameter only applies to the instantiated object and is made persistent via
        :py:class:`~adafruit_bus_device.spi_device.SPIDevice`.

mac
************

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.mac

   You can set this attribute using a 6-byte `int` or `bytearray`. If this is
   set to `None`, then a random 6-byte address is generated.

name
************

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.name

    This is not required. In fact setting this attribute will subtract from
    the available payload length (in bytes). Set this attribute to `None` to
    disable advertising the device name.

    .. note:: This information occupies (in the TX FIFO) an extra 2 bytes plus
        the length of the name set by this attribute.

show_pa_level
*************

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.show_pa_level

    The default value of `False` will exclude this optional information.

    .. note:: This information occupies (in the TX FIFO) an extra 3 bytes, and is
        really only useful for some applications to calculate proximity to the
        nRF24L01 transceiver.

hop_channel()
*************

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.hop_channel

whiten()
*************

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.whiten

    This is done according to BLE specifications.

    :param bytearray,bytes data: The packet to whiten.
    :returns: A `bytearray` of the ``data`` with the whitening algorythm
        applied.

    .. warning:: This function uses the currently set BLE channel as a
        base case for the whitening coefficient. Do not call
        `hop_channel()` before using this function to de-whiten received
        payloads (which isn't officially supported yet). Note that
        `advertise()` uses this function internally to prevent such
        improper usage.

len_available()
******************

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.len_available

    This is detirmined from the current state of `name` and `show_pa_level`
    attributes.

    :param bytearray,bytes hypothetical: Pass a potential `chunk()` of
        data to this parameter to calculate the resulting left over length
        in bytes. This parameter is optional.
    :returns: An `int` representing the length of available bytes for the
        a single payload.

    .. versionchanged:: 2.0.0
        name changed from "available" to "len_available" to avoid confusion with
        :py:func:`circuitpython_nrf24l01.rf24.RF24.available()`. This change also
        allows providing the underlying `RF24` class'
        :py:func:`~circuitpython_nrf24l01.rf24.RF24.available()` method in the
        `FakeBLE` API.

advertise()
*************

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.advertise

    :returns: Nothing as every transmission will register as a success
        under the required settings for BLE beacons.

    :param bytearray buf: The payload to transmit. This bytearray must have
        a length greater than 0 and less than 22 bytes Otherwise a
        `ValueError` exception is thrown whose prompt will tell you the
        maximum length allowed under the current configuration. This can
        also be a list or tuple of payloads (`bytearray`); in which case,
        all items in the list/tuple are processed are packed into 1
        payload for a single transmissions. See example code below about
        passing a `list` or `tuple` to this parameter.
    :param int data_type: This is used to describe the buffer data passed
        to the ``buf`` parameter. ``0x16`` describes all service data. The
        default value ``0xFF`` describes manufacturer information. This
        parameter is ignored when a `tuple` or `list` is passed to the
        ``buf`` parameter. Any other values are not applicable to BLE
        advertisements.

    .. important:: If the name and/or TX power level of the emulated BLE
        device is also to be broadcast, then the `name` and/or
        `show_pa_level` attribute(s) should be set prior to calling
        `advertise()`.

    To pass multiple data values to the ``buf`` parameter see the
    following code as an example:

    .. code-block:: python

        # let UUIDs be the 16-bit identifier that corresponds to the
        # BLE service type. The following values are not compatible with
        # BLE advertisements.
        UUID_1 = 0x1805
        UUID_2 = 0x1806
        service1 = ServiceData(UUID_1)
        service2 = ServiceData(UUID_2)
        service1.data = b"some value 1"
        service2.data = b"some value 2"

        # make a tuple of the buffers
        buffers = (
            chunk(service1.buffer),
            chunk(service2.buffer)
        )

        # let `ble` be the instantiated object of the FakeBLE class
        ble.advertise(buffers)
        ble.hop_channel()

channel
####################

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.channel

interrupt_config()
####################

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.interrupt_config

    .. warning:: The :py:attr:`circuitpython_nrf24l01.rf24.RF24.irq_df`
        attribute is not implemented for BLE operations.

    .. seealso:: :py:meth:`~circuitpython_nrf24l01.rf24.RF24.interrupt_config()`

Unavailable RF24 functionality
******************************

The following `RF24` functionality is not available in `FakeBLE` objects:

- :py:attr:`~circuitpython_nrf24l01.rf24.RF24.dynamic_payloads`
- :py:meth:`~circuitpython_nrf24l01.rf24.RF24.set_dynamic_payloads()`
- :py:attr:`~circuitpython_nrf24l01.rf24.RF24.data_rate`
- :py:attr:`~circuitpython_nrf24l01.rf24.RF24.address_length`
- :py:attr:`~circuitpython_nrf24l01.rf24.RF24.auto_ack`
- :py:meth:`~circuitpython_nrf24l01.rf24.RF24.set_auto_ack()`
- :py:attr:`~circuitpython_nrf24l01.rf24.RF24.ack`
- :py:attr:`~circuitpython_nrf24l01.rf24.RF24.crc`
- :py:meth:`~circuitpython_nrf24l01.rf24.RF24.open_rx_pipe()`
- :py:meth:`~circuitpython_nrf24l01.rf24.RF24.open_tx_pipe()`


Service related classes
-----------------------

abstract parent
***************

.. autoclass:: circuitpython_nrf24l01.fake_ble.ServiceData
    :members:
    :special-members: __len__

    :param int uuid: The 16-bit UUID `"GATT Service assigned number"
        <https://specificationrefs.bluetooth.com/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf#page=19>`_ defined by the
        Bluetooth SIG to describe the service data. This parameter is
        required.

derivitive children
*******************

.. autoclass:: circuitpython_nrf24l01.fake_ble.TemperatureServiceData
    :show-inheritance:

    This class's `data` attribute accepts a `float` value as
    input and returns a `bytes` object that conforms to the Bluetooth
    Health Thermometer Measurement format as defined in the `GATT
    Specifications Supplement. <https://www.bluetooth.org/DocMan/handlers/
    DownloadDoc.ashx?doc_id=502132&vId=542989>`_

.. autoclass:: circuitpython_nrf24l01.fake_ble.BatteryServiceData
    :show-inheritance:

    The class's `data` attribute accepts a 1-byte unsigned `int` value as
    input and returns a `bytes` object that conforms to the Bluetooth
    Battery Level format as defined in the `GATT Specifications
    Supplement. <https://www.bluetooth.org/DocMan/handlers/
    DownloadDoc.ashx?doc_id=502132&vId=542989>`_

.. autoclass:: circuitpython_nrf24l01.fake_ble.UrlServiceData
    :members: pa_level_at_1_meter
    :show-inheritance:

    This class's `data` attribute accepts a `str` of URL data as input, and
    returns the URL as a `bytes` object where some of the URL parts are
    encoded using `Eddystone byte codes as defined by the specifications.
    <https://github.com/google/eddystone/tree/master/eddystone-url>`_