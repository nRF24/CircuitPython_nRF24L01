Recipes
========

USB-HID via RF24
****************

RF24 acting as a hub for HIDs
-----------------------------

This module uses CircuitPython's builtin usb_hid library as a wireless
hub to extend USB HID interfaces via the nRF24L01 transceivers.

Dependencies in CircuitPython firmware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- :py:data:`usb_hid.devices`
- :py:data:`~microcontroller.nvm`

.. warning:: This recipe is not compatible with linux-based SoC computers
    like the Raspberry Pi because the `adafruit-blinka
    <https://github.com/adafruit/Adafruit_Blinka>`_ library
    does not provide the :py:mod:`usb_hid` module and non-volatile memory
    (:py:data:`~microcontroller.nvm`) access.

.. literalinclude:: ../recipes/wireless_hid_hub.py
    :linenos:
    :lines: 15-

RF24 acting as a mouse HID
--------------------------

For simplicity, this recipe uses :py:mod:`board` pins for analog
and digital inputs. But it is highly recommended that your solution
uses a `MCP23017 <https://www.adafruit.com/product/732>`_ or
`MCP23008 <https://www.adafruit.com/product/593>`_ for digital inputs.
Possible alternative analog
inputs could include:

- `Cirque Glidepoint circle trackpad
  <https://www.mouser.com/Search/Refine?Ntk=P_MarCom&Ntt=118816186>`_
  with the `CircuitPython_Cirque_Pinnacle
  <https://github.com/2bndy5/CircuitPython_Cirque_Pinnacle>`_ library
- `MCP3008 <https://www.adafruit.com/product/856>`_ with the
  `Adafruit_CircuitPython_MCP3xxx
  <https://github.com/adafruit/Adafruit_CircuitPython_MCP3xxx>`_ library

.. literalinclude:: ../recipes/wireless_hid_mouse.py
    :linenos:
    :lines: 5-

