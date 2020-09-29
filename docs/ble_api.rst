fake_ble module
===============

Limitations
-----------

This module uses the `RF24` class to make the nRF24L01 imitate a
Bluetooth-Low-Emissions (BLE) beacon. A BLE beacon can send (referred to as
advertise) data to any BLE compatible device (ie smart devices with Bluetooth
4.0 or later) that is listening.

Original research was done by `Dmitry Grinberg and his write-up (including C
source code) can be found here
<http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_
As this technique can prove invaluable in certain project designs, the code
here is simply ported to work on CircuitPython.

.. important:: Because the nRF24L01 wasn't designed for BLE advertising, it
    has some limitations that helps to be aware of.

    1. the maximum payload length is shortened to 21 bytes (when not
       broadcasting a device
       :py:attr:`~circuitpython_nrf24l01.fake_ble.FakeBLE.name`).
    2. the channels that BLE use are limited to the following three: 2.402
       GHz, 2.426 GHz, and 2.480 GHz
    3. :py:attr:`~circuitpython_nrf24l01.rf24.RF24.crc` is disabled in the
       nRF24L01 firmware as BLE requires 3 bytes
       (:py:func:`~circuitpython_nrf24l01.fake_ble.crc24_ble()`) and nRF24L01
       only handles a maximum of 2. Thus, we have appended the required 3
       bytes of CRC24 into the payload.
    4. :py:attr:`~circuitpython_nrf24l01.rf24.RF24.address_length` of BLE
       packet only uses 4 bytes, so we have set that accordingly.
    5. The :py:attr:`~circuitpython_nrf24l01.rf24.RF24.auto_ack` (automatic
       acknowledgment) feature of the nRF24L01 is useless when tranmitting to
       BLE devices, thus it is disabled as well as automatic re-transmit
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.arc`) and custom ACK
       payloads (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.ack`) which both
       depend on the automatic acknowledgments feature.
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
       (:py:attr:`~circuitpython_nrf24l01.rf24.RF24.irq_df`), is never
       triggered because
       :py:attr:`~circuitpython_nrf24l01.rf24.RF24.auto_ack` feature is
       disabled.

.. currentmodule:: circuitpython_nrf24l01.fake_ble

helpers
----------------

swap_bits
*****************

.. autofunction:: circuitpython_nrf24l01.fake_ble.swap_bits

reverse_bits
*****************

.. autofunction:: circuitpython_nrf24l01.fake_ble.reverse_bits

chunk
*****************

.. autofunction:: circuitpython_nrf24l01.fake_ble.chunk

crc24_ble
*****************

.. autofunction:: circuitpython_nrf24l01.fake_ble.crc24_ble

BLE_FREQ
*****************

.. autodata:: circuitpython_nrf24l01.fake_ble.BLE_FREQ

FakeBLE class
-------------

.. autoclass:: circuitpython_nrf24l01.fake_ble.FakeBLE

to_iphone
************

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.to_iphone

mac
************

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.mac

name
************

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.name

show_pa_level
*************

.. autoattribute:: circuitpython_nrf24l01.fake_ble.FakeBLE.show_pa_level

hop_channel()
*************

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.hop_channel

whiten()
*************

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.whiten

advertise()
*************

.. automethod:: circuitpython_nrf24l01.fake_ble.FakeBLE.advertise

Service related classes
-----------------------

abstract parent
***************

.. autoclass:: circuitpython_nrf24l01.fake_ble.ServiceData
    :members:

derivitive children
*******************

.. autoclass:: circuitpython_nrf24l01.fake_ble.TemperatureServiceData
    :members:

.. autoclass:: circuitpython_nrf24l01.fake_ble.BatteryServiceData
    :members:
