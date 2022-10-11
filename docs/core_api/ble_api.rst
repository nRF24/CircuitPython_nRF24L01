
.. module:: circuitpython_nrf24l01.fake_ble

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
       :py:func:`~circuitpython_nrf24l01.fake_ble.FakeBLE.len_available()` to
       determine if your payload can be transmit.
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
       acknowledgment) feature of the nRF24L01 is useless when transmitting to
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
       :py:attr:`~circuitpython_nrf24l01.rf24.RF24.auto_ack` attribute is disabled.

``fake_ble`` module helpers
---------------------------

.. autofunction:: circuitpython_nrf24l01.fake_ble.swap_bits

    :returns:
        An `int` containing the byte whose bits are reversed
        compared to the value passed to the ``original`` parameter.
    :param int original: This is truncated to a single unsigned byte,
        meaning this parameter's value can only range from 0 to 255.

.. autofunction:: circuitpython_nrf24l01.fake_ble.reverse_bits

    :returns:
       A `bytearray` whose byte order remains the same, but each
       byte's bit order is reversed.
    :param bytearray,bytes original: The original buffer whose bits are to be
       reversed.

.. autofunction:: circuitpython_nrf24l01.fake_ble.chunk

    :param buf: The actual data contained in the block.
    :param data_type: The type of data contained in the chunk. This is a
        predefined number according to BLE specifications. The default value
        :python:`0x16` describes all service data. :python:`0xFF` describes manufacturer
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

.. autofunction:: circuitpython_nrf24l01.fake_ble.crc24_ble

    This is exposed for convenience and should not be used for other buffer
    protocols that require big endian CRC24 format.

    :param data: The buffer of data to be uncorrupted.
    :param deg_poly: A preset "degree polynomial" in which each bit
        represents a degree who's coefficient is 1. BLE specifications require
        ``0x00065b`` (default value).
    :param init_val: This will be the initial value that the checksum
        will use while shifting in the buffer data. BLE specifications require
        ``0x555555`` (default value).
    :returns: A 24-bit `bytearray` representing the checksum of the data (in
        proper little endian).

.. autofunction:: circuitpython_nrf24l01.fake_ble.whitener

    This is a helper function to `FakeBLE.whiten()`. It has been broken out of the
    `FakeBLE` class to allow whitening and dewhitening a BLE payload without the
    hardcoded coefficient.

    :param buf: The BLE payloads data. This data should include the
        CRC24 checksum.
    :param coef: The whitening coefficient used to avoid repeating binary patterns.
        This is the index of `BLE_FREQ` tuple for nRF24L01 channel that the payload transits
        (plus 37).

        .. code-block:: python

            coef = None  # placeholder for the coefficient
            rx_channel = nrf.channel
            for index, chl in enumerate(BLE_FREQ):
                if chl == rx_channel:
                    coef = index + 37
                    break

        .. note::
            If currently used nRF24L01 channel is different from the channel in which the
            payload was received, then set this parameter accordingly.

.. autodata:: circuitpython_nrf24l01.fake_ble.BLE_FREQ

    This tuple contains the relative predefined channels used:

    .. csv-table::
        :header: "nRF24L01 channel", "BLE channel"

        2, 37
        26, 38
        80, 39

QueueElement class
------------------

.. versionadded:: 2.1.0
    This class was added when implementing BLE signal sniffing.

.. autoclass:: circuitpython_nrf24l01.fake_ble.QueueElement
    :members:

FakeBLE class
-------------

.. autoclass:: circuitpython_nrf24l01.fake_ble.FakeBLE
    :show-inheritance:

    Per the limitations of this technique, only some of underlying
    :py:class:`~circuitpython_nrf24l01.rf24.RF24` functionality is
    available for configuration when implementing BLE transmissions.
    See the `Unavailable RF24 functionality`_ for more details.

    .. seealso::
        For all parameters' descriptions, see the
        :py:class:`~circuitpython_nrf24l01.rf24.RF24` class' constructor documentation.

.. autoproperty:: circuitpython_nrf24l01.fake_ble.FakeBLE.mac

   You can set this attribute using a 6-byte `int` or `bytearray`. If this is
   set to `None`, then a random 6-byte address is generated.

.. autoproperty:: circuitpython_nrf24l01.fake_ble.FakeBLE.name

    This is not required. In fact, setting this attribute will subtract from
    the available payload length (in bytes). Set this attribute to `None` to
    disable advertising the device name.

    Valid inputs are `str`, `bytes`, `bytearray`, or `None`. A `str` will be converted to
    a `bytes` object automatically.

    .. note::
        This information occupies (in the TX FIFO) an extra 2 bytes plus
        the length of the name set by this attribute.

    .. versionchanged:: 2.2.0
        This attribute can also be set with a `str`, but it must be UTF-8 compatible.

.. autoproperty:: circuitpython_nrf24l01.fake_ble.FakeBLE.show_pa_level

    The default value of `False` will exclude this optional information.

    .. note:: This information occupies (in the TX FIFO) an extra 3 bytes, and is
        really only useful for some applications to calculate proximity to the
        nRF24L01 transceiver.

.. autoproperty:: circuitpython_nrf24l01.fake_ble.FakeBLE.channel

    The only allowed channels are those contained in the `BLE_FREQ` tuple.

    .. versionchanged:: 2.1.0
        Any invalid input value (that is not found in `BLE_FREQ`) had raised a
        `ValueError` exception. This behavior changed to ignoring invalid input values,
        and the exception is no longer raised.

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.hop_channel

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.whiten

    This is done according to BLE specifications.

    :param bytearray,bytes data: The packet to whiten.
    :returns: A `bytearray` of the ``data`` with the whitening algorithm
        applied.

    .. note:: `advertise()` and
        :meth:`~circuitpython_nrf24l01.fake_ble.FakeBLE.available()` uses
        this function internally to prevent improper usage.
    .. warning:: This function uses the currently set BLE channel as a
        base case for the whitening coefficient.

        Do not call `hop_channel()` before calling
        :meth:`~circuitpython_nrf24l01.fake_ble.FakeBLE.available()`
        because this function needs to know the correct BLE channel to
        properly de-whiten received payloads.

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.len_available

    This is determined from the current state of `name` and `show_pa_level`
    attributes.

    :param bytearray,bytes hypothetical: Pass a potential `chunk()` of
        data to this parameter to calculate the resulting left over length
        in bytes. This parameter is optional.
    :returns: An `int` representing the length of available bytes for
        a single payload.

    .. versionchanged:: 2.0.0
        The name of this function changed from "available" to "len_available" to avoid confusion with
        :py:func:`circuitpython_nrf24l01.rf24.RF24.available()`. This change also
        allows providing the underlying `RF24` class'
        :py:func:`~circuitpython_nrf24l01.rf24.RF24.available()` method in the
        `FakeBLE` API.

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.advertise

    :returns: Nothing as every transmission will register as a success
        under the required settings for BLE beacons.

    :param buf: The payload to transmit. This bytearray must have
        a length greater than 0 and less than 22 bytes Otherwise a
        `ValueError` exception is thrown whose prompt will tell you the
        maximum length allowed under the current configuration. This can
        also be a list or tuple of payloads (`bytearray`); in which case,
        all items in the list/tuple are processed are packed into 1
        payload for a single transmissions. See example code below about
        passing a `list` or `tuple` to this parameter.
    :param data_type: This is used to describe the buffer data passed
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


.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.available

    This method will take the first available data from the radio's RX FIFO and
    validate the payload using the 24bit CRC checksum at the end of the payload.
    If the payload is indeed a valid BLE transmission that fit within the 32 bytes
    that the nRF24L01 can capture, then this method will decipher the data within
    the payload and enqueue the resulting `QueueElement` in the `rx_queue`.

    .. tip:: Use :meth:`~circuitpython_nrf24l01.fake_ble.FakeBLE.read()` to fetch the
        decoded data.

    :Returns:
        - `True` if payload was received *and* validated
        - `False` if no payload was received or the received payload could not be
          deciphered.

    .. versionchanged:: 2.1.0
        This was an added override to validate & decipher received BLE data.

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.rx_queue

    Each Element in this queue is a `QueueElement` object whose members are set according to the
    its internal decoding algorithm. The :meth:`~circuitpython_nrf24l01.fake_ble.FakeBLE.read()`
    function will remove & return the first element in this queue.

    .. hint::
        This attribute is exposed for debugging purposes, but it can also be used by applications.

    .. versionadded:: 2.1.0

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.rx_cache

    This attribute is only used by :meth:`~circuitpython_nrf24l01.fake_ble.FakeBLE.available()`
    to cache the data from the top level of the radio's RX FIFO then validate & decode it.

    .. hint::
        This attribute is exposed for debugging purposes.

    .. versionadded:: 2.1.0

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.read

    :Returns:
        - `None` if nothing is the internal `rx_queue`
        - A `QueueElement` object from the front of the `rx_queue` (like a FIFO buffer)

    .. versionchanged:: 2.1.0
        This was an added override to fetch deciphered BLE data from the `rx_queue`.

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.interrupt_config

    .. warning:: The :py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_df`
        attribute is not implemented for BLE operations.

    .. seealso::
        :py:meth:`~circuitpython_nrf24l01.rf24.RF24.interrupt_config()`

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

Abstract Parent
***************

.. autoclass:: circuitpython_nrf24l01.fake_ble.ServiceData
    :members:
    :special-members: __len__,__repr__

    :param uuid: The 16-bit UUID `"GATT Service assigned number"
        <https://specificationrefs.bluetooth.com/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf#page=19>`_ defined by the
        Bluetooth SIG to describe the service data. This parameter is
        required.

Service data UUID numbers
*************************

These are the 16-bit UUID numbers used by the
`Derivative Children of the ServiceData class <ble_api.html#derivative-children>`_

.. autodata:: circuitpython_nrf24l01.fake_ble.TEMPERATURE_UUID
    :annotation: = 0x1809
.. autodata:: circuitpython_nrf24l01.fake_ble.BATTERY_UUID
    :annotation: = 0x180F
.. autodata:: circuitpython_nrf24l01.fake_ble.EDDYSTONE_UUID
    :annotation: = 0xFEAA

Derivative Children
*******************

.. autoclass:: circuitpython_nrf24l01.fake_ble.TemperatureServiceData
    :members: data
    :show-inheritance:

    .. seealso:: Bluetooth Health Thermometer Measurement format as defined in the
        `GATT Specifications Supplement.
        <https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=502132&vId=542989>`_

.. autoclass:: circuitpython_nrf24l01.fake_ble.BatteryServiceData
    :members: data
    :show-inheritance:

    .. seealso:: The Bluetooth Battery Level format as defined in the
        `GATT Specifications Supplement.
        <https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=502132&vId=542989>`_

.. autoclass:: circuitpython_nrf24l01.fake_ble.UrlServiceData
    :members: pa_level_at_1_meter, data
    :show-inheritance:

    .. seealso::
        Google's `Eddystone-URL specifications
        <https://github.com/google/eddystone/tree/master/eddystone-url>`_.
