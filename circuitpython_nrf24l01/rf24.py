# The MIT License (MIT)
#
# Copyright (c) 2017 Damien P. George
# Copyright (c) 2019 Brendan Doherty
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`circuitpython_nrf24l01.rf24` - RF24
====================================

CircuitPython port of the nRF24L01 library from Micropython.
Original work by Damien P. George & Peter Hinch can be found `here <https://github.com/micropython/micropython/tree/master/drivers/nrf24l01>`_

The Micropython source has been rewritten to work on the Raspberry Pi and other Circuitpython compatible devices using Adafruit's `busio`, `adafruit_bus_device.spi_device`, and `digitalio`, modules.
Modified by Brendan Doherty, Rhys Thomas

* Author(s): Damien P. George, Peter Hinch, Rhys Thomas, Brendan Doherty
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import time
from adafruit_bus_device.spi_device import SPIDevice

# nRF24L01+ registers
SETUP_AW     = 0x03 # address width
RF_CH        = 0x05 # channel
RF_SETUP     = 0x06 # RF Power Amptlitude & Data Rate
RX_ADDR_P0   = 0x0a # RX pipe addresses rangeing [0,5]:[0xA:0xF]
RX_PW_P0     = 0x11 # RX payload widths on pipes ranging [0,5]:[0x11,0x16]
FIFO_STATUS  = 0x17 # register containing info on both RX/TX FIFOs + re-use payload flag
DYNPD	     = 0x1c # dynamic payloads feature. each bit represents this feature per pipe
FEATURE      = 0x1d # global enablers/disablers for dynamic payloads, auto-ACK, and custom ACK features

class RF24(SPIDevice):
    """A driver class for the nRF24L01 transceiver radio. This class aims to be compatible with other devices in the nRF24xxx product line, but officially only supports (through testing) the nRF24L01 and nRF24L01+ devices. This class also inherits from `adafruit_bus_device.spi_device`, thus that module should be extracted/copied from the `Adafruit library and driver bundle <https://github.com/adafruit/Adafruit_CircuitPython_Bundle>`_, or, if using CPython's pip, automatically installed using ``pip install circuitpython-nrf24l01``.

    :param ~busio.SPI spi: The SPI bus that the nRF24L01 is connected to.
        ..tip:: This object is meant to be shared amongst other driver classes (like adafruit_mcp3xxx.mcp3008 for example) that use the same SPI bus. Otherwise, multiple devices on the same SPI bus with different spi objects may produce errors or undesirable behavior.
    :param ~digitalio.DigitalInOut csn: The digital output pin that is connected to the nRF24L01's CSN (Chip Select Not) pin. This is required.
    :param ~digitalio.DigitalInOut ce: The digital output pin that is connected to the nRF24L01's CE (Chip Enable) pin. This is required.
    :param int channel: This is used to specify a certain frequency that the nRF24L01 uses. This is optional and can be set later using the 'channel' attribute. Defaults to 76. This can be changed at any time by using the `channel` attribute
    :param int payload_length: This is the length (in bytes) of a single payload to be transmitted or received. This is optional and ignored if the `dynamic_payloads` attribute is enabled. Defaults to the maximum (32). This can be changed at any time by using the `payload_length` attribute
    :param int address_length: This is the length (in bytes) of the addresses that are assigned to the data pipes for transmitting/receiving. It is optional and defaults to 5. This can be changed at any time by using the `address_length` attribute
    :param bool dynamic_payloads: This parameter enables or disables the dynamic payload length feature of the nRF24L01. It is optional and defaults to enabled. This can be changed at any time by using the `dynamic_payloads` attribute
    :param bool auto_ack: This parameter enables or disables the automatic acknowledgment (ACK) feature of the nRF24L01. It is optional and defaults to enabled. This can be changed at any time by using the `auto_ack` attribute
    :param bool irq_DR: When "Data is Ready", this configures the interrupt (IRQ) trigger of the nRF24L01's IRQ pin (active low). This parameter is optional and defaults to enabled. This can be changed at any time by using the `interrupt_config()` method.
    :param bool irq_DS: When "Data is Sent", this configures the interrupt (IRQ) trigger of the nRF24L01's IRQ pin (active low). This parameter is optional and defaults to enabled. This can be changed at any time by using the `interrupt_config()` method.
    :param bool irq_DF: When "max retry attempts are reached", this configures the interrupt (IRQ) trigger of the nRF24L01's IRQ pin (active low). This parameter is optional and defaults to enabled. This can be changed at any time by using the `interrupt_config()` method.

    """
    def __init__(self, spi, csn, ce, channel=76, payload_length=32, address_length=5, dynamic_payloads=True, auto_ack=True, irq_DR=True, irq_DS=True, irq_DF=True):
        # set payload length
        self.payload_length = payload_length
        # last address assigned to pipe0 for reading. init to None
        self.pipe0_read_addr = None
        # init the buffer used to store status data from spi transactions
        self._status = 0
        self._config = 0
        self._fifo = 0
        # init the SPI bus and pins
        super(RF24, self).__init__(spi, chip_select=csn, baudrate=10000000, polarity=0, phase=0, extra_clocks=0)

        # store the ce pin
        self.ce = ce
        # reset ce.value & disable the chip comms
        self.ce.switch_to_output(value=False)
        # if radio is still powered up and CE is LOW: standby-I mode
        # if radio is still powered up and CE is HIGH: standby-II mode

        self.flush_rx() # updates the status attribute
        self.flush_tx() # updates the status attribute
        # check for device presence by verifying RX FIFO has been cleared
        if self.status & 0xE != 0xE:
            raise RuntimeError("nRF24L01 Hardware not responding")
        # fetch config and clear status flags (& get fifo flags)
        self.clear_status_flags()
        # NOTE per spec sheet: nRF24L01+ must be in a standby or power down mode before writing to the configuration register ( CONFIG  @ 0x00 )
        if self.power or self.xx_mode: # if in standby-II/I or RX mode
            self.power = False # power down

        self.channel = channel # always writes value to register
        self.address_length = address_length # always writes value to register

        # configure SETUP_RETR register to our defaults
        self._setup_retr = 0x53 # ard: 1500us (recommended default); arc: 3
        self._reg_write(SETUP_AW + 1, self._setup_retr)
        # configure RF_SETUP register to our defaults
        self._rf_setup = 0x06 # < -- 0dBm @ 1Mbps
        self._reg_write(RF_SETUP, self._rf_setup)

        # configure special case flags in the FEATURE register
        self._features = 0x07 # <- enables all :(not default)
        self._reg_write(FEATURE, self._features)

        # configure registers for which each bit is specific per pipe
        self._ack = None # init RX ACK payload buffer
        self._auto_ack = int(auto_ack) * 0x3F # <- means all enabled
        self._reg_write(1, self._auto_ack)
        self._open_pipes = 0 # <- means all closed
        self._reg_write(2, self._open_pipes)

        # set dynamic_payloads and automatic acknowledgment packets on all pipes
        self._dyn_pl = self._reg_read(DYNPD)
        self.dynamic_payloads = dynamic_payloads
        # config interrupt to go LOW when any of the 3 most significant bits in status register are set True. See funcion comments for more detail
        self.interrupt_config(irq_DR, irq_DS, irq_DF) # (all True == nRF24L01's default)

    def _reg_read(self, reg):
        """A helper function to read a single byte of data from a specified register on the nRF24L01's internal IC. THIS IS NOT MEANT TO BE DIRECTLY CALLED BY END-USERS.

        :param int reg: The address of the register you wish to read from.

        Please refer to `Chapter 9 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1090864>`_ for applicable register addresses.

        """
        buf = bytearray(2) # 2 = 1 status byte + 1 byte of returned content
        with self:
            # according to datasheet we must wait for CSN pin to settle
            # this depends on the capacitor used on the VCC & GND
            # assuming a 100nF (HIGHLY RECOMMENDED) wait time is slightly < 5ms
            time.sleep(0.005) # time for CSN to settle
            self.spi.readinto(buf, write_value=reg)
        self._status = buf[0] # save status byte
        return buf[1] # drop status byte and return the rest

    def _reg_read_bytes(self, reg, buf_len=5):
        """A helper function to read multiple bytes of data from a specified register on the nRF24L01's internal IC. THIS IS NOT MEANT TO BE DIRECTLY CALLED BY END-USERS.

        :param int reg: The address of the register you wish to read from.
        :param int buf_len: the amount of bytes to read from a register specified by `reg`. A default of 5 is meant to be used for checking pipe addresses.

        To read the full payload in a FIFO, pass `buf_len` as `32`.

        .. note:: Reading `buf_len` bytes from FIFO buffer would also remove `buf_len` bytes from the FIFO buffer. There is no bounds checking on this parameter.

        Please refer to `Chapter 9 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1090864>`_ for applicable register addresses.

        """
        # allow an extra byte for status data
        buf = bytearray(buf_len + 1)
        with self:
            time.sleep(0.005) # time for CSN to settle
            self.spi.readinto(buf, write_value=reg)
        self._status = buf[0] # save status byte
        return buf[1:] # drop status byte and return the rest

    def _reg_write_bytes(self, reg, outBuf):
        """A helper function to write multiple bytes of data to a specified register on the nRF24L01's internal IC. THIS IS NOT MEANT TO BE DIRECTLY CALLED BY END-USERS.

        :param int reg: The address of the register you wish to read from.
        :param bytearray outBuf: The buffer of bytes to write to a register specified by `reg`. Useful for writing pipe address or TX payload data.

        .. note:: The nRF24L01's internal FIFO buffer stack has 3 levels, meaning you can only write up to 3 payloads (maximum 32 byte length per payload). There is no bounds checking on this parameter.
        Please refer to `Chapter 9 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1090864>`_ for applicable register addresses.

        """
        outBuf = bytes([0x20 | reg]) + outBuf
        inBuf = bytearray(len(outBuf))
        with self:
            time.sleep(0.005) # time for CSN to settle
            self.spi.write_readinto(outBuf, inBuf)
        self._status = inBuf[0] # save status byte

    def _reg_write(self, reg, value):
        """A helper function to write a single byte of data to a specified register on the nRF24L01's internal IC. THIS IS NOT MEANT TO BE DIRECTLY CALLED BY END-USERS.

        :param int reg: The address of the register you wish to read from.
        :param int value: The one byte content to write to a register specified by `reg`. There is a rigid expectation of bit order & content. There is no bounds checking on this parameter.

        Please refer to `Chapter 9 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1090864>`_ for applicable register addresses.

        """
        outBuf = bytes([0x20 | reg, value])
        inBuf = bytearray(len(outBuf))
        with self:
            time.sleep(0.005) # time for CSN to settle
            self.spi.write_readinto(outBuf, inBuf)
        self._status = inBuf[0] # save status byte

    def flush_rx(self):
        """An helper function to flush the nRF24L01's internal RX FIFO buffer. (write-only)

        ..note:: The nRF24L01 RX FIFO is 3 level stack that holds payload data. This means that there can be up to 3 received payloads (of maximum length equal to 32 bytes) waiting to be read (and popped from the stack) by `recv()`. This function clears all 3 levels.

        """
        self._reg_read_bytes(0xE2)

    def flush_tx(self):
        """An helper function to flush the nRF24L01's internal TX FIFO buffer. (write-only)

        ..note:: The nRF24L01 TX FIFO is 3 level stack that holds payload data. This means that there can be up to 3 payloads (of maximum length equal to 32 bytes) waiting to be transmitted by `send()` or `send_fast()`. This function clears all 3 levels. It is worth noting that the payload data is only popped from the TX FIFO stack upon successful transmission and the ``reUseTX`` parameter in send() & send_fast() is passed as `False` (that parameter's default value).

        """
        self._reg_read_bytes(0xE1)

    @property
    def status(self):
        """The latest status byte return from SPI transactions. (read-only)

        :returns: 1 byte `int` in which each bit represents a certain status flag.

            * bit 7 (MSB) is not used and will always be 0
            * bit 6 represents the RX data ready flag
            * bit 5 represents the TX data sent flag
            * bit 4 represents the max re-transmit flag
            * bit 3 through 1 represents the RX pipe number [0,5] that received the available payload in RX FIFO buffer. ``0b111`` means RX FIFO buffer is empty.
            * bit 0 (LSB) represents the TX FIFO buffer full flag

        """
        return self._status

    @property
    def config(self):
        """The latest configuration register's byte returned from recent SPI transactions. (read-only)

        :returns: 1 byte `int` in which each bit represents a certain configuration.

            * bit 7 (MSB) is not used and will always be 0
            * bit 6 represents the RX data ready IRQ config (``0``:Enabled, ``1``:Disabled)
            * bit 5 represents the TX data sent IRQ config (``0``:Enabled, ``1``:Disabled)
            * bit 4 represents the max re-transmit IRQ config (``0``:Enabled, ``1``:Disabled)
            * bit 3 represents the CRC (cycle redundancy check) enabled state
            * bit 2 represent the CRC encoding scheme ( ``0``:1 byte, ``1``:2 byte)
            * bit 1 represents the powered up flag (used to enable sleeping) (``1``:ON. ``0``:OFF)
            * bit 0 (LSB) represents the RX/TX mode flag (``1``:RX, ``0``:TX)

        """
        return self._config

    @property
    def fifo(self):
        """The latest FIFO_STATUS byte returned from SPI transactions. (read-only)

        :returns: 1 byte `int` in which each bit represents a certain status flag.

            * bit 7 (MSB) is not used and will always be 0
            * bit 6 represents the flag to re-use the currently payload in TX FIFO. Must be set when writing the payload in question
            * bit 5 represents the TX FIFO full flag
            * bit 4 represents the TX FIFO empty flag
            * bit 3 through 2 are not used only '00' allowed
            * bit 1 (LSB) represents the RX FIFO full flag
            * bit 0 (LSB) represents the RX FIFO empty flag

        """
        return self._fifo

    @property
    def setup_retr(self):
        """The latest byte about the SETUP_RETR register from recent SPI transactions. (read-only)

        :returns: 1 byte `int` in which each bit represents a certain configuration.

            * bit 7 (MSB) through 4 represents the delay time (in multiples of 250 micrseconds) between attemped re-transmissions
            * bit 3 through 0 (LSB) represents a count of the latest made attempts to re-trnsmit

        """
        return self._setup_retr

    @property
    def rf_setup(self):
        """The latest byte about the RF_SETUP register from recent SPI transactions. (read-only)

        :returns: 1 byte `int` in which each bit represents a certain configuration.

            * bit 7 (MSB) flag to enable Continuous carrier transmissions (we don't use thse, so ``0``)
            * bit 6 is reseerved and will always be ``0``
            * bit 5 represents the RF data data rate of 250Kbps
            * bit 4 represents represents some kind of internal PLL_LOCK ("used for [QA?] testing")
            * bit 3 represents the RF data data rate of 1 or 2 Mbps mode (notice the other bit in this register about 250Kbps should be ``0`` as far as these modes are concerned)
            * bit 2 through 1 represents the RF power amplitude setting see this register in `Chapter 9 on nRF24L01 specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1090864>`_
            * bit 0 (LSB) is reseerved and will always be ``0``

        """
        return self._rf_setup

    @property
    def features(self):
        """The latest byte about the FEATURE register from recent SPI transactions. (read-only)

        :returns: 1 byte `int` in which each bit represents a certain configuration.

            * bit 7 (MSB) through 3 is not used and will always be 0
            * bit 2 represent the global dynamic payloads flag (required for ACK)
            * bit 1 represents the the flag to attach custom payloads to the ACK
            * bit 0 (LSB) represents the "Ask no ACK" bit for the next packet containing the current payload in TX buffer

        """
        return self._features
    @property

    def open_pipes(self):
        """The latest byte about the EN_RXADDR register from recent SPI transactions. (read-only)

        :returns: 1 byte `int` in which each bit represents a pipe's configuration.

            * bit 7 (MSB) through 6 is not used and will always be 00
            * bit 5 through 0 (LSB) represents the flag to enable the pipe for RX using a previously-set configured address

        """
        return self._open_pipes

    @property
    def ack(self):
        """This attribute contains the payload data that is part of the automatic acknowledgment (ACK) packet. You can use this attribute to set a custom ACK payload to be used on a specified pipe number.

        :param tuple ack_pl: This tuple must have the following 2 items in their repective order:

            - The `bytearray` of payload data to be attached to the ACK packet in RX mode. This must have a length in range [1,32] bytes. If `None` is passed then the custom ACK payload feature is disabled and any concurrent ACK payloads in the TX FIFO will remain until transmitted or `flush_tx()`.

                .. tip:: Pass ``(None, 0)`` to `start_listening()` to disable custom payloads and flush the TX FIFO buffer upon entering RX Mode.

            - The `int` identifying data pipe number to be used for transmitting the ACK payload in RX mode. This number must be in range [0,5], otherwise an `AssertionError` exception is thrown.

            .. note:: The `payload_length` attribute has nothing to do with the ACK payload length as enabling the `dynamic_payloads` attribute is required.

        Setting this attribute does NOT change the data stored within it. Instead it only writes the specified payload data to the nRF24L01's TX FIFO buffer in regaurd to the specified data pipe number.

        .. important:: To use this attribute properly, the `auto_ack` attribute must be enabled. Additionally, if retrieving the ACK payload data, you must specify the `read_ack` parameter as `True` when calling `send()` or, in case of asychronous application, directly call `read_ack()` function after calling `send_fast()` and before calling `clear_status_flags()`. See `read_ack()` for more details. Otherwise, this attribute will always be its initial value of `None`.

        .. tip:: As the ACK payload can only be set during RX mode and must be set prior to a transmission, use the ``ack_pl`` parameter of `start_listening()` to set the ACK payload for transmissions upon entering RX mode. Set the ACK payload data using this attribute only after `start_listening()` has been called to ensure the nRF24L01 is in RX mode. It is also worth noting that the nRF24L01 exits RX mode upon calling `stop_listening()`.

        """
        return self._ack

    @ack.setter
    def ack(self, ack_pl):
        assert (ack_pl[0] is None or 1 <= len(ack_pl[0]) <= 32) and 0 <= ack_pl[1] <= 5
        # we need to throw the EN_ACK_PAY flag in the FEATURES register accordingly
        if (self.features & 2) != (ack_pl is None): # should this get thrown every time?
            self._features = self.features & 5 | (0 if ack_pl[0] is None else 2)
            self._reg_write(FEATURE,  self.features)
        # this attribute should also represents the state of the custom ACK payload feature
        # the data stored "privately" gets written by a separate trigger (read_ack())
        if not (self.auto_ack): # ensure auto_ack feature is enabled
            self.auto_ack = True
        if ack_pl[0] is not None and self.auto_ack: # enabling
            # only prepare payload if the auto_ack attribute is enabled and ack_pl[0] is not None
            self._reg_write_bytes(0xA8 | ack_pl[1], ack_pl[0])
        else: # disabling
            self._ack = None # init/reset the attribute

    @property
    def irq_DR(self):
        """A `bool` that represents the "Data Ready" interrupted flag. (read-only)

        * `True` represents Data is in the RX FIFO buffer
        * `False` represents anything depending on context (state/condition of FIFO buffers) -- usually this means the flag's been reset.

        Pass ``dataReady`` parameter as `True` to `clear_status_flags()` to reset this.
        """
        return self.status & 0x40

    @property
    def irq_DS(self):
        """A `bool` that represents the "Data Sent" interrupted flag. (read-only)

        * `True` represents a successful transmission
        * `False` represents anything depending on context (state/condition of FIFO buffers) -- usually this means the flag's been reset.

        Pass ``dataSent`` parameter as `True` to `clear_status_flags()` to reset this.
        """
        return self.status & 0x20

    @property
    def irq_DF(self):
        """A `bool` that represents the "Data Failed" interrupted flag. (read-only)

        * `True` signifies the nRF24L01 attemped all configured retries?
        * `False` represents anything depending on context (state/condition) -- usually this means the flag's been reset.

        Pass ``maxRetry`` parameter as `True` to `clear_status_flags()` to reset this.
        """
        return self.status & 0x10

    def what_happened(self, dump_pipes=False):
        """This debuggung function aggregates all status/condition related information from the nRF24L01. Some flags may be irrelevant depending on nRF24L01's state/condition.

        :returns: A dictionary that contains the data pertaining to the following keys:

            - ``Data Ready`` Is there RX data ready to be sent?
            - ``Data Sent`` Has the TX data been sent?
            - ``Packets Lost`` Amount of packets lost (transmission failures)
            - ``Re-transmitted Count`` Maximum amount of attempts to re-transmit
            - ``Max Re-transmit`` Has the maximum attempts to re-transmit been reached?
            - ``Received Power Detector`` This is `True` only if OTA (over the air) transmission exceeded -64 dBm (not currently implemented by this driver class).
            - ``Re-use TX Payload`` Should the nRF24L01 re-use the last TX payload? (not currently implemented by this driver class)
            - ``TX FIFO full`` Is the TX FIFO buffer full?
            - ``TX FIFO empty`` Is the TX FIFO buffer empty?
            - ``RX FIFO full`` Is the RX FIFO buffer full?
            - ``RX FIFO empty`` Is the RX FIFO buffer empty?
            - ``Custom ACK payload`` Is the nRF24L01 setup to use an extra (user defined) payload attached to the acknowledgment packet?
            - ``Ask no ACK`` Is the nRF24L01 set up to transmit individual packets that don't require acknowledgment?
            - ``Automatic Acknowledgment`` Is the automatic acknowledgement feature enabled?
            - ``Dynamic Payloads`` Is the dynamic payload length feature enabled?
            - ``Primary Mode`` The current mode (RX or TX) of communication of the nRF24L01 device.
            - ``Power Mode`` The power state can be Off, Standby-I, Standby-II, or On.
        :param bool dump_pipes: `True` will append all addresses from the RX nRF24L01's registers of stored addresses. This defaults to `False`. The appended keys will be titled: ``pipe addr on #`` where "#" represent the pipe number.

        Remember, we only use `recv()` to read payload data as that transaction will also remove it from the FIFO buffer.

        .. note:: Only some data is fetched directly from nRF24L01. Specifically ``Packets Lost``, ``Retry Count``, ``Recvd Pwr Detect``, and all pipe addresses. These data are not stored inernally on purpose. All other data is computed from memory of last SPI transaction related to that data.

        """
        assert isinstance(dump_pipes, (bool, int))
        watchdog = self._reg_read(0x08) # OBSERVE_TX register
        result = {
            "Data Ready": bool(self.irq_DR),
            "Data Sent": bool(self.irq_DS),
            "Packets Lost": (watchdog & 0xF0) >> 4,
            "Retry Count": watchdog & 0x0F,
            "Max Retry Hit": bool(self.irq_DF),
            "Recvd Pwr Detect": bool(self._reg_read(0x09)), # RDP register
            "Re-use TX Payload": bool(self.reuse_tx),
            "TX FIFO full": self.tx_full,
            "TX FIFO empty": bool(self.fifo & 0x10),
            "RX FIFO full": bool(self.fifo & 2),
            "RX FIFO empty": bool(self.fifo & 1),
            "Custom ACK Payload": bool(self.ack is not None or (self.features & 2)),
            "Ask no ACK": bool(self.features & 1),
            "Automatic Acknowledgment": bin(self.auto_ack),
            "Dynamic Payloads": bin(self._dyn_pl) if self.dynamic_payloads else False,
            "Primary Mode": "RX" if self.xx_mode else "TX",
            "Power Mode": ("Standby-II" if self.ce.value else "Standby-I") if self.config & 2 else "Off"
            }
        if dump_pipes:
            for i in range(RX_ADDR_P0, RX_ADDR_P0 + 6):
                j = i - RX_ADDR_P0
                # some hidden goodies in memory
                isOpen = "opened" if (self._open_pipes & (1 << j)) else "closed"
                isDP = "dynamic" if self._dyn_pl & (1 << j) else " static"
                # condense to one dictionary entry key and store pipe address as key's value
                result["Address on {} pipe {} using {} payloads".format(isOpen,j,isDP)] = self._reg_read_bytes(i)
        return result

    @property
    def reuse_tx(self):
        """This `bool` attribute is used to report if the current payload ib the nRF24L01's TX FIFO buffer is flagged for use on subsequent transmissions. (read-only)

        .. note:: The nRF24L01 automatically resets attribute when either:

            - A new payload is (over)written to the TX FIFO buffer
            - The entire TX FIFO buffer is emptied using `flush_tx()`

        """
        return self.fifo & 0x40

    def clear_status_flags(self, dataReady=True, dataSent=True, maxRetry=True):
        """This clears the interrupt flags in the status register. This functionality is exposed for asychronous applications only.

        :param bool dataReady: specifies wheather to clear the "RX Data Ready" flag.
        :param bool dataSent: specifies wheather to clear the "TX Data Sent" flag.
        :param bool maxRetry: specifies wheather to clear the "Max Re-transmit reached" flag.

        .. note:: Clearing certain flags is necessary for continued operation of the nRF24L01 despite wheather or not the user is taking advantage of the interrupt (IRQ) pin. Directly calling this function without being familiar with the nRF24L01's expected behavior (as outlined in the Specifications Sheet) can cause undesirable behavior. See `Appendix A-B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1047965>`_ for an outline of proper behavior.

        """
        # take this chance to update both FIFO flags and STATUS flags (STATUS is returned by nRF24L01 on every transaction)
        self._fifo = self._reg_read(FIFO_STATUS)
        if self.status & 0x70 != (dataReady <<6) + (dataSent <<5) + (maxRetry <<4):
            self._status = self.status & 0xf | ((dataReady <<6) + (dataSent <<5) + (maxRetry <<4))
            self._reg_write(0x07, self.status) # write only if needed

    @property
    def power(self):
        """This `bool` attribute controls the PWR_UP bit in the CONFIG register.

        - `False` basically puts the nRF24L01 to sleep. No transmissions are executed when sleeping.
        - `True` powers up the nRF24L01

            .. important:: Everytime the nRF24L01 powers up to "Standby-II" mode the TX FIFO buffer automatically emptied unless the ``reuse_rx`` attribute was triggered via ``reUseTX`` parameter as `True` when calling `send()` or `send_fast()`.

        .. note:: This attribute needs to be `True` if you want to put radio on standby-I (CE pin is HIGH) or standby-II (CE pin is LOW) modes. In case of either standby modes, transmissions are only executed based on certain criteria (see `Chapter 6.1.2-7 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132980>`_).

        """
        return self.config & 0x2

    @property
    def tx_full(self):
        """An attribute to represent if the nRF24L01's status flag signaling that the TX FIFO buffer is full. (read-only).
        :returns:

                * `True` for TX FIFO buffer full
                * `False` for TX FIFO buffer NOT full

        Use the `start_listening()` and `stop_listening()` to controls this attribute properly. As handling the transition between modes involves playing with the nRF24L01's CE pin.

        """
        return self.status & 1

    @property
    def xx_mode(self):
        """An attribute to represent if the nRF24L01 is set in TX mode (master) or TX mode (slave). (read-only).
        :returns:

                * `True` for RX mode
                * `False` for TX mode

        Use the `start_listening()` and `stop_listening()` to controls this attribute properly. As handling the transition between modes involves playing with the nRF24L01's CE pin.

        """
        return self.config & 1

    @power.setter
    def power(self, isOn):
        assert isinstance(isOn, (bool, int))
        # capture surrounding flags and set PWR_UP flag according to isOn boolean
        self._config = self._reg_read(0x0)
        if self.power != isOn:
            # only write changes
            self._config = (self.config & 0x7d) + (isOn << 1)
            self._reg_write(0x0, self.config)
            # power up/down takes < 150 us + 4 us
            time.sleep(0.00016)

    @property
    def auto_ack(self):
        """This `bool` attribute controls automatic acknowledgment feature on all nRF24L01's data pipes.

        - `True` enables automatic acknowledgment packets.
            Enabling `dynamic_payloads` requires this attribute to be `True` (automatically handled accordingly by `dynamic_payloads`). Enabled `auto_ack` does not require `dynamic_payloads` to be `True`, thus does not automatically enable `dynamic_payloads` (use `dynamic_payloads` attribute to do that). Also the cycle redundancy checking (CRC) is enabled automatically by the nRF24L01 if this automatic acknowledgment feature is enabled (see `dynamic_payloads` and `crc` attribute for more details).
        - `False` disables automatic acknowledgment packets.
            As the `dynamic_payloads` requirement mentioned above, diasabling `auto_ack` also disables `dynamic_payloads` but not `crc` attributes.

        .. note:: There is no plan to implement automatic acknowledgment on a per data pipe basis, therefore all 6 pipes are treated the same.

        """
        return self._auto_ack

    @auto_ack.setter
    def auto_ack(self, enable):
        assert isinstance(enable, (bool, int))
        # manage EN_DYN_ACK in FEATURE register
        if self.features & 1 != enable: # if not already
            self._features = (self.features & 6) | 1
            self._reg_write(FEATURE, self.features)
        if not self.dynamic_payloads and enable:
            self.dynamic_payloads = enable
        if self.auto_ack != enable:
            self._auto_ack = b'0x3F' if enable else b'0'
            self._reg_write(0x01, self._auto_ack)
        # radio automatically enables CRC if ACK packets are enabled
        if enable: # thus let the record show so
            self._config = (self.config & ~6) | 6

    @property
    def dynamic_payloads(self):
        """This `bool` attribute controls dynamic payload length feature on all nRF24L01's data pipes.

        - `True` enables nRF24L01's dynamic payload length feature.
            Enabling dynamic payloads REQUIRES enabling the automatic acknowledgment feature on corresponding data pipes AND asserting 'enable dynamic payloads' flag of FEATURE register (both are automatically handled here).
        - `False` disables nRF24L01's dynamic payload length feature.
            As the `dynamic_payloads` requirement mentioned above, disabling `dynamic_payloads` does not disable `auto_ack` (use `auto_ack` attribute to disable that).

        .. note:: There is no plan to implement dynamic payload lengths on a per data pipe basis, therefore all 6 pipes are treated the same.

        """
        return (self._dyn_pl) & (self.features & 4)

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        assert isinstance(enable, (bool, int))
        if self.dynamic_payloads != enable:# write only if needed
            # save changes to register(&its Shadow)
            self._features = (self.features & 3) | (enable << 2)
            self._reg_write(FEATURE, self.features)
            self._dyn_pl = 0x3F if enable else 0
            self._reg_write(DYNPD, self._dyn_pl)

    @property
    def arc(self):
        """"This `int` attribute specifies the nRF24L01's number of attempts to re-transmit TX payload when acknowledgment packet is not received. The nRF24L01 does not attempt to re-transmit if `auto_ack` attribute is disabled. Default is set to 3.

        A valid input value must be in range [0,15]. Otherwise an `AssertionError` exception is thrown.

        """
        return self._setup_retr & 0x0f

    @arc.setter
    def arc(self, count):
        assert 0 <= count <= 15
        self._setup_retr = self._reg_read(0x04) # refresh data
        if self.arc & 0x0F != count:# write only if needed
            # save changes to register(&its Shadow)
            self._setup_retr = (self.setup_retr & 0xF0) | count
            self._reg_write(0x04, self._setup_retr)

    @property
    def ard(self):
        """This `int` attribute specifies the nRF24L01's delay (in microseconds) between attempts to automatically re-transmit the TX payload when an acknowledgement (ACK) packet is not received. During this time, the nRF24L01 is listening for the ACK packet. If the `auto_ack` attribute is disabled, this attribute is not applied.

        .. note:: Paraphrased from spec sheet:
            Please take care when setting this parameter. If the ACK payload is more than 15 bytes in 2 Mbps data rate, the ARD must be 500µS or more. If the ACK payload is more than 5 bytes in 1 Mbps data rate, the ARD must be 500µS or more. In 250kbps data rate (even when the payload is not in ACK) the ARD must be 500µS or more.

            See `data_rate` attribute on how to set the data rate of the nRF24L01's transmissions.

        A valid input value must be a multiple of 250 in range [250,4000]. Otherwise an `AssertionError` exception is thrown. Default is 1500.

        """
        return ((self._setup_retr & 0xf0) >> 4) * 250 + 250

    @ard.setter
    def ard(self, t):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert 250 <= t <= 4000 and t % 250 == 0
        # save for access via getter property(s)
        self._setup_retr = self._reg_read(0x04)
        # set new ARD data and current ARC data to register
        if self.ard != t:# write only if needed
            # save changes to register(&its Shadow)
            self._setup_retr = (int((t-250)/250) << 4) | (self._setup_retr & 0x0F)
            self._reg_write(0x04, self._setup_retr)

    @property
    def address_length(self):
        """This `int` attribute specifies the length (in bytes) of addresses to be used for RX/TX pipes.
        A valid input value must be in range [3,5]. Otherwise an `AssertionError` exception is thrown. Default is 5. This is really a place holder for the ocasional need to specify the address length on a per pipe basis.

        .. note:: nRF24L01 uses the LSByte for padding addresses with lengths of less than 5 bytes.

        """
        return self._address_length

    @address_length.setter
    def address_length(self, length):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert 3 <= length <= 5
        # save for access via getter property
        self._address_length = length
        # address width is saved in 2 bits making range = [3,5]
        self._reg_write(SETUP_AW, length - 2)

    # get payload length attribute
    @property
    def payload_length(self):
        """This `int` attribute specifies the length (in bytes) of payload that is regaurded, meaning 'how big of a payload should the radio care about?' If the `dynamic_payloads` attribute is enabled, this attribute has no affect. This is really a place holder for the ocasional need to specify the payload length on a per pipe basis.
        A valid input value must be in range [0,32]. Otherwise an `AssertionError` exception is thrown. Default is 32.

        - Payloads of less than input value will be truncated.
        - Payloads of greater than input value will be padded with zeros.
        - Input value of 0 negates radio's transmissions.

        """
        return self._payload_length

    @payload_length.setter
    def payload_length(self, length):
        # max payload size is 32 bytes
        assert 0 <= length <= 32
        # save for access via getter property
        self._payload_length = length

    @property
    def data_rate(self):
        """This `int` attribute specifies the nRF24L01's frequency data rate for OTA (over the air) transmissions.

        A valid input value is:

        - ``1`` sets the frequency data rate to 1 Mbps
        - ``2`` sets the frequency data rate to 2 Mbps
        - ``250`` sets the frequency data rate to 250 Kbps

        Any invalid input throws an `AssertionError` exception. Default is 1 Mbps.

        .. warning:: 250 Kbps is be buggy on the non-plus models of the nRF24L01 product line. If you use 250 Kbps data rate, and some transmissions report failed by the transmitting nRF24L01, even though the same packet in question actually reports received by the receiving nRF24L01, try a different different data rate.

        """
        if self.rf_setup & 0x28 == 0x0:
            return 1
        elif self.rf_setup & 0x28 == 0x8:
            return 2
        elif self.rf_setup & 0x28 == 0x20:
            return 250

    @data_rate.setter
    def data_rate(self, speed):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert speed in (1, 2, 250)
        if speed == 1:
            speed = 0x0
        elif speed == 2:
            speed = 0x8
        elif speed == 250:
            speed = 0x20
        # save for access via getter property
        self._rf_setup = self._reg_read(0x06)
        if self.rf_setup & 0x28 != speed:# write only if needed
            # save changes to register(&its Shadow)
            self.rf_setup = self.rf_setup & ~(0x28) | speed
            self._reg_write(RF_SETUP, self.rf_setup)

    @property
    def pa_level(self):
        """This `int` aattribute specifies the nRF24L01's power amplitude level (in dBm).

        A valid input value is:

        - ``-18`` sets the nRF24L01's power amplitude to -18 dBm (lowest)
        - ``-12`` sets the nRF24L01's power amplitude to -12 dBm
        - ``-6`` sets the nRF24L01's power amplitude to -6 dBm
        - ``0`` sets the nRF24L01's power amplitude to 0 dBm (highest)

        Any invalid input throws an `AssertionError` exception. Default is 0 dBm.

        """

        return (3 - ((self._rf_setup & RF_SETUP) >> 1)) * -6
        # if (self._rf_setup & 0x6) == 0x0:
        #     return "-18 dBm"
        # elif (self._rf_setup & 0x6) == 0x2:
        #     return "-12 dBm"
        # elif (self._rf_setup & 0x6) == 0x4:
        #     return "-6 dBm"
        # elif (self._rf_setup & 0x6) == 0x6:
        #     return "0 dBm"

    @pa_level.setter
    def pa_level(self, power):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert power in (-18, -12, -6, 0)
        self._rf_setup = self._reg_read(RF_SETUP) # refresh values
        power = (3-(power/-3)) >> 1
        # if power == -18:
        #     power = 0x0
        # elif power == -12:
        #     power = 0x2
        # elif power == -6:
        #     power = 0x4
        # elif power == 0:
        #     power = 0x6
        if self._rf_setup & RF_SETUP != power: # write only if needed
            # save changes to register(&its Shadow)
            self._rf_setup = (self._rf_setup & ~(RF_SETUP)) | power
            self._reg_write(RF_SETUP, self._rf_setup)

    @property
    def crc(self):
        """This `int` attribute specifies the nRF24L01's cycle redundancy checking (CRC) encoding scheme in terms of bytes.

        A valid input value is in range [0,2]:

        - ``0`` disables CRC
        - ``1`` enables CRC encoding scheme using 1 byte
        - ``2`` enables CRC encoding scheme using 2 bytes

        Any invalid input throws an `AssertionError` exception. Default is enabled using 2 bytes.

        .. note:: The nRF24L01 automatically enables CRC if automatic acknowledgment feature is enabled (see `auto_ack` attribute).

        """
        return -1 * (self.config & 0xc / -4 + 1)

    @crc.setter
    def crc(self, length):
        assert 0 <= length <= 2
        self._config = self._reg_read(0x0) # refresh values
        length = ((length * -1) - 1) * -4
        # if length == 1:
        #     # enable CRC is True & 1 byte CRC encoding scheme means CRC0 = 0
        #     length = 0x8
        # elif length == 2:
        #     # enable CRC is True & 2 byte CRC encoding scheme means CRC0 = 1
        #     length = 0x8 | 0x4
        if (self.config & (0x12) != length):
            # save changes to register(&its Shadow)
            self._config = self.config & 0x73 | length
            self._reg_write(0x0, self.config)

    @property
    def channel(self):
        """This `int` attribute specifies the nRF24L01's frequency (MHz).

        A valid input value must be in range [0-127]. Otherwise an `AssertionError` exception is thrown. Default is 76 (for compatibility with `TMRh20's arduino library <http://tmrh20.github.io/RF24/classRF24.html>`_ default).

        """
        return self._channel

    @channel.setter
    def channel(self, channel):
        assert 0 <= channel <= 127
        self._channel = channel
        self._reg_write(RF_CH, channel) # always wries to reg

    def interrupt_config(self, onMaxARC=True, onDataSent=True, onDataRecv=True):
        """Sets the configuration of the nRF24L01's Interrupt (IRQ) pin. IRQ signal from the nRF24L01 is active LOW. (write-only)
        To fetch the status of these interrupt (IRQ) flags, use the  `status` attribute's bits 4 through 6.

        :param bool onMaxARC: If this is `True`, then interrupt pin goes active LOW when maximum number of attempts to re-transmit the packet have been reached.
        :param bool onDataSent: If this is `True`, then interrupt pin goes active LOW when a payload from TX buffer is successfully transmitted. If `auto_ack` attribute is enabled, then interrupt pin only goes active LOW when acknowledgment (ACK) packet is received.
        :param bool onDataRecv: If this is `True`, then interrupt pin goes active LOW when there is new data to read in the RX FIFO.

            .. tip:: Paraphrased from nRF24L01+ Specification Sheet:

                The procedure for handling ``onDataRecv`` interrupt should be:

                1. read payload through `recv()`
                2. clear ``dataReady`` status flag (taken care of by using `recv()` in previous step)
                3. read FIFO_STATUS register to check if there are more payloads available in RX FIFO buffer. (a call to `any()` will get this result)
                4. if there is more data in RX FIFO, repeat from step 1

        """
        self._config = self._reg_read(0) # refresh data
        if (self._config & 0x0f) != (onMaxARC << 4) | (onDataSent << 5) | (onDataRecv << 6):
            # save to register and update local copy of pwr & RX/TX modes' flags
            self._config = (self._config & 0x0f) | (onMaxARC << 4) | (onDataSent << 5) | (onDataRecv << 6)
            self._reg_write(0x0, self._config)

    # address should be a bytes object with the length = self.address_length
    def open_tx_pipe(self, address):
        """This function is used to open a data pipe for OTA (over the air) TX transactions. If `dynamic_payloads` attribute is `False`, then the `payload_length` attribute is used to specify the length of the payload to be transmitted.

        :param bytearray address: The virtual address of the receiving nRF24L01. This must have a length equal to the `address_length` attribute (see `address_length` attribute). Otherwise an `AssertionError` exception is thrown.

        .. note:: There is no option to specify which data pipe to use because the only data pipe that the nRF24L01 uses in TX mode is pipe 0. Additionally, the nRF24L01 uses the same data pipe (pipe 0) for receiving acknowledgement (ACK) packets in TX mode (when the `auto_ack` attribute is enables).

        """
        assert len(address) <= self.address_length
        if self.ack is not None:
            self._reg_write_bytes(RX_ADDR_P0, address)
        if not self.dynamic_payloads:
            # radio doesn't care about this if dynamic_payloads is enabled
            self._reg_write(RX_PW_P0, self.payload_length)
        self._reg_write_bytes(0x10, address)
        #let self._open_pipes only reflect RX pipes

    def close_rx_pipe(self, pipe_number):
        """This function is used to close a specific data pipe for OTA (over the air) RX transactions.

        :param int pipe_number: The data pipe to use for RX transactions. This must be in range [0,5]. Otherwise an `AssertionError` exception is thrown.
        """
        assert 0 <= pipe_number <= 5
        # reset pipe address accordingly
        if not pipe_number:
            # reset pipe 0. NOTE this does not clear the shadow copy, so we also need to do that.
            self.pipe0_read_addr = b'\xe7' * 5
            self._reg_write_bytes(pipe_number + RX_ADDR_P0, b'\xe7' * 5)
        elif pipe_number < 2: # write the full address for pipe 1
            self._reg_write_bytes(pipe_number + RX_ADDR_P0, b'\xc2' * 5)
        else: # write just LSB for 2 <= pipes >= 5
            self._reg_write(pipe_number + RX_ADDR_P0, (b'\xc1' + pipe_number) * 5)
        # disable the specified data pipe if not already
        if self._open_pipes & (1 << pipe_number):
            self._open_pipes = self._open_pipes & ~(1 << pipe_number)
            self._reg_write(0x2, self._open_pipes)

    def open_rx_pipe(self, pipe_number, address=None):
        """This function is used to open a specific data pipe for OTA (over the air) RX transactions. If `dynamic_payloads` attribute is `False`, then the `payload_length` attribute is used to specify the length of the payload to be expected on the specified data pipe.

        :param int pipe_number: The data pipe to use for RX transactions. This must be in range [0,5]. Otherwise an `AssertionError` exception is thrown.
        :param bytearray address: The virtual address of the receiving nRF24L01. This must have a length equal to the `address_length` attribute (see `address_length` attribute). If ``None`` is passed for the ``address`` parameter, then the address for the specified ``pipe_number`` will be reset to recommended defaults and the pipe will be closed. Otherwise an `AssertionError` exception is thrown. If using a ``pipe_number`` greater than 1, then only the LSByte of the address is written (so make LSByte unique among other simultaneously broadcasting addresses).

            .. note:: The nRF24L01 shares the MSBytes (address[0:4]) on data pipes 2 through 5.

        """
        assert (address is None or 1 <= len(address) <= self.address_length) and 0 <= pipe_number <= 5
        if address is None:
            self.close_rx_pipe(pipe_number)
        else: # address is not None
            if pipe_number < 2: # write entire address if pipe_number is 1
                if pipe_number == 0:
                    # save shadow copy of address if target pipe_number is 0. This is done to help ensure the proper address is set to pipe 0 via start_listening() as open_tx_pipe() will modify the address on pipe 0 if auto_ack is enabled during TX mode
                    self.pipe0_read_addr = address
                self._reg_write_bytes(RX_ADDR_P0 + pipe_number, address)
            else:
                # only write LSB if pipe_number is not 0 or 1. This saves time on the SPI transaction
                self._reg_write(RX_ADDR_P0 + pipe_number, address[len(address) - 1])
            if not self.dynamic_payloads and not (self._dyn_pl & (1 << pipe_number)):
                # radio doesn't care about payload_length if dynamic_payloads is enabled. This saves time on the SPI transaction
                self._reg_write(RX_PW_P0 + pipe_number, self.payload_length)
            # enable the specified data pipe if not already
            if not (self._open_pipes & (1 << pipe_number)):
                self._open_pipes = self._open_pipes | (1 << pipe_number)
                self._reg_write(0x2, self._open_pipes)

    def start_listening(self, ack_pl=(None, 0)):
        """Puts the nRF24L01 into RX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this function flushes the RX and TX FIFOs, clears the status flags, and puts nRf24L01 in powers up mode.

        :param tuple ack_pl: This tuple must have the following 2 items in their repective order:

            - The `bytearray` of payload data to be attached to the ACK packet in RX mode. This must have a length in range [1,32] bytes. Otherwise an `AssertionError` exception is thrown.
            - The `int` identifying data pipe number to be used for transmitting the ACK payload in RX mode. This number must be in range [0,5], otherwise an `AssertionError` exception is thrown. Generally this is the same data pipe set by `open_rx_pipe()`, but it is not limited to that convention.

            .. note:: The `payload_length` attribute has nothing to do with the ACK payload length as enabling the `dynamic_payloads` attribute is required.

            .. note:: Specifying this parameter has no affect (and isn't saved anywhere) if the `auto_ack` attribute is `False`. Use this parameter to prepare an ACK payload for the first received transmission. For any subsequent transmissions, use the `ack` attribute to continue writing ACK payload data to the nRF24L01's FIFO buffer as it is emptied upon successful transmission.

        .. important:: the ``ack_pl`` parameter's payload and pipe number are both required to be specified if there is to be a customized ACK payload transmitted. Otherwise an `AssertionError` exception is thrown.

        """
        assert (ack_pl[0] is None or 1 <= len(ack_pl[0]) <= 32) and 0 <= ack_pl[1] <= 5
        # ensure radio is in power down or standby-I mode
        if self.ce.value:
            self.ce.value = 0
        # handle ACK features
        if ack_pl[0] is None or 1 <= len(ack_pl[0]) <= 32:
            # use setter to load custom ACK payload and enable that feature accordingly
            self.ack = ack_pl
            if ack_pl[0] is None: # the custom ACK feature has been disabled
                self.flush_tx() # flush the TX FIFO buffer
        if not self.dynamic_payloads:
            self._reg_write(RX_PW_P0, self.payload_length)
        # make sure the last call to open_rx_pipe(0) sticks
        if self.pipe0_read_addr != self._reg_read_bytes(RX_ADDR_P0):
            self._reg_write_bytes(RX_ADDR_P0, self.pipe0_read_addr)
        # power up radio & set radio in RX mode
        self._config = self.config & 0xFC | 3
        self._reg_write(0x0, self.config)
        time.sleep(0.00015) # mandatory wait time to power up radio
        # enable radio comms
        self.ce.value = 1 # radio begins listening after CE pulse is > 130 us
        time.sleep(0.00013) # ensure pulse is > 130 us
        # nRF24L01 has just entered RX standby-II mode

    def stop_listening(self):
        """Puts the nRF24L01 into TX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this function puts nRF24L01 in powers Standby-I (low current & no transmissions) mode which is ideal for post-transmission work. Remeber to flush your 3-level FIFO buffers when appropriate using `flush_tx()` or `flush_rx()`."""
        # ensure radio is in standby-I mode
        if self.ce.value:
            self.ce.value = 0
        # set radio in TX mode as recommended behavior per spec sheet.
        self._config = self.config & ~0x01 # does not put radio to sleep
        self._reg_write(0x0, self.config)
        # exits while still in Standby-I (low current & no transmissions)

    def pipe(self, pipe_number=None):
        """This function works like an equivalent to TMRh20's available(). Returns information about the data pipe that received latest payload.

        :param int pipe_number: The specific number identifying a data pipe to check for RX data. This parameter is optional and must be in range [0,5], otherwise an `AssertionError` exception is thrown.

        :returns: `None` if there is no payload in RX FIFO.

        If user does not specify pipe_number:

        :returns: The `int` identifying pipe number that contains the RX payload.

        If user does specify pipe_number:

        :returns: `True` only if the specified ``pipe_number`` parameter is equal to the identifying number of the data pipe that received the current (top level) RX payload in the FIFO buffer, otherwise `False`.

        """
        assert pipe_number is None or 0 <= pipe_number <= 5 # check bounds on user input
        self._reg_read(0x0)
        self._fifo = self._reg_read(FIFO_STATUS) # take this chance to update both FIFO flags and STATUS flags (STATUS is returned by nRF24L01 on every transaction)
        pipe = (self.status & 0x0E) >> 1 # 0x0E==RX_P_NO
        if pipe <= 5: # is there data in RX FIFO?
            if pipe_number is None:
                # return pipe number if user did not specify a pipe number to test against
                return pipe
            elif pipe_number != pipe:
                # return comparison of RX pipe number vs user specified pipe number
                return False
            # return True if pipe number matches user input & there is data in RX FIFO
            return True
        return None # RX FIFO is empty

    def any(self):
        """This function checks if the nRF24L01 has received any data at all. (read-only)

        :returns:

            - `int` of the size (in bytes) of an available RX payload (if any).
            - `True` when the RX FIFO buffer is not empty and `dynamic_payloads` attribute is enabled.
            - `False` if there is no payload in the RX FIFO buffer.

        """
        self._fifo = self._reg_read(FIFO_STATUS)
        if not (self.fifo & (1 | (1 << 4))):# 1 << 4 == TXmt?; 1 == RXmt?
            return self._reg_read(0x60) if not self.dynamic_payloads else True # 0x60 == R_RX_PL_WID command
        return False

    def recv(self):
        """This function is used to retrieve, then clears all the status flags. This function also serves as a helper function to `read_ack()` in TX mode to aquire the automatic acknowledgement (ACK) payload (if any).

        :returns: A `bytearray` of the RX payload data

            - If the `dynamic_payloads` attribute is disabled, then the returned bytearray's length is equal to the user defined `payload_length` attribute (which defaults to 32).
            - If the `dynamic_payloads` attribute is enabled, then the returned bytearray's length is equal to the payload size in the RX FIFO buffer.

        .. note:: The `dynamic_payloads` attribute must be enabled in order to use ACK payloads.

        """
        # buffer size = current payload size + status byte
        curr_pl_size = self.payload_length if not self.dynamic_payloads else self._reg_read(0x60)
        # get the data
        result = self._reg_read_bytes(0x61, curr_pl_size)
        # clear only the data ready status flag for continued RX/TX operations
        self.clear_status_flags(True, False, False)
        # return all available bytes from payload
        return result

    def read_ack(self):
        """Allows user to read the automatic acknowledgement (ACK) payload (if any) when nRF24L01 is in TX mode. This function is called from a blocking `send()` call if the ``read_ack`` parameter in `send()` is passed as `True`.
        Alternatively, this function can be called directly in case of using the non-blocking `send_fast()` function call during asychronous applications.

        .. warning:: In the case of asychronous applications, this function will do nothing if the status flags are cleared after calling `send_fast()` and before calling this function. Also, the `dynamic_payloads` and `auto_ack` attributes must be enabled to use ACK payloads. It is worth noting that enabling the `dynamic_payloads` attribute automatically enables the `auto_ack` attribute.

        """
        if self.any(): # check RX payload for ACK packet
            # directly save ACK payload to the ack internal attribute.
            # `self.ack = x` does not not save anything internally
            self._ack = self.recv()
        return self.ack # this is ok as it reads from internal _ack attribute

    def send(self, buf=None, AskNoACK=False, reUseTX=False, read_ack=False, timeout=0.2):
        """This blocking function is used to transmit payload until one of the following results is acheived:

        :returns:

            * ``0`` if transmission times out meaning nRF24L01 has malfunctioned.
            * ``1`` if transmission succeeds.
            * ``2`` if transmission fails.

        :param bytearray buf: The payload to transmit. This bytearray must have a length greater than 0 to execute transmission.

            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.

        :param bool AskNoACK: Pass this parameter as `True` to tell the nRF24L01 not to wait for an acknowledgment from the receiving nRF24L01. This parameter directly controls a ``NO_ACK`` flag in the transmission's Packet Control Field (9 bits of information about the payload).Therefore, it takes advantage of an nRF24L01 feature specific to individual payloads, and its value is not saved anywhere. You do not need to specify this everytime if the `auto_ack` attribute is `False`.

            .. note:: Each transmission is in the form of a packet. This packet contains sections of data around and including the payload. `See Chapter 7.3 in the nRF24L01 Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1136318>`_

        :param bool reUseTX: `True` prevents the nRF24L01 from automatically removing the TX payload data from the FIFO buffer. This is optional and defaults to `False`

            .. note:: When this parameter is `False`, the nRF24L01 only removes the payload from the TX FIFO buffer after successful transmission. Otherwise use `flush_tx()` to clear anitquated payloads (those that failed to transmit or were intentionally kept in the TX FIFO buffer using this parameter).

        :param bool read_ack: A flag to specify wheather or not to save the customized automatic acknowledgement (ACK) payload to the `ack` attribute.

        :param float timeout: This an arbitrary number of seconds that is used to keep the application from indefinitely hanging in case of radio malfunction. Default is 200 milliseconds.

            .. warning:: A note from the developer: This parameter may evolve into a "privatized" internal constant, so it is STRONGLY ADVISED TO NOT GET IN THE HABIT OF ALTERING THIS PARAMETER! This driver class is still young, be gentle.

        """
        result = 0
        self._fifo = self.send_fast(buf, AskNoACK, reUseTX)
        time.sleep(0.00015) # ensure CE pulse is >= 150 us
        start = time.monotonic()
        while result == 0 and (time.monotonic() - start) < timeout:
            # let result be 0 if timeout, 1 if success, or 2 if fail
            self._reg_read(0xFF) # perform Non-operation command to get status byte (should be faster)
            if  self.irq_DS or self.irq_DF: # transmission done
                # get status flags to detect error
                result = 1 if self.irq_DS else 2
        # read ack payload (if read_ack == True), clear status flags, then power down
        if read_ack:
            # get and save ACK payload to self.ack if user wants it
            self.read_ack()
        # TX related flags are not cleared by read_ack(), do that now
        self.clear_status_flags(False,True,True)
        self.ce.value = 0 # go to Standby-I power mode (power attribute still == True)
        return result

    def send_fast(self, buf=None, AskNoACK=False, reUseTX=False):
        """This non-blocking function (when used as alternative to `send()`) is meant for asynchronous applications.

        :param bytearray buf: The payload to transmit. This bytearray must have a length greater than 0 to execute transmission.

            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.
        :param bool AskNoACK: Pass this parameter as `True` to tell the nRF24L01 not to wait for an acknowledgment from the receiving nRF24L01. This parameter directly controls a ``NO_ACK`` flag in the transmission's Packet Control Field (9 bits of information about the payload).Therefore, it takes advantage of an nRF24L01 feature specific to individual payloads, and its value is not saved anywhere. You do not need to specify this everytime if the `auto_ack` attribute is `False`.

            .. note:: Each transmission is in the form of a packet. This packet contains sections of data around and including the payload. `See Chapter 7.3 in the nRF24L01 Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1136318>`_

        :param bool reUseTX: `True` prevents the nRF24L01 from automatically removing the TX payload data from the FIFO buffer. This is optional and defaults to `False`

            .. note:: When this parameter is `False`, the nRF24L01 removes the payload from the TX FIFO buffer after successful transmission and every time the nRF24L01 power mode cycles from Standby-II mode (everytime `stop_listening()` is called). Otherwise use `flush_tx()` to clear anitquated payloads (those that failed to transmit or were intentionally kept in the TX FIFO buffer using this parameter).

        This function isn't completely non-blocking as we still need to wait just under 5 milliseconds for the CSN pin to settle (allowing for a clean SPI transaction).

        .. note:: The nRF24L01 doesn't initiate sending until a mandatory minimum 10 microsecond pulse on the CE pin (which is initiated before this function exits) is acheived. However, we have left that 10 microsecond wait time to be managed by the user in cases of asychronous application, or it is managed by using `send()` instead of this function.

        .. warning:: A note paraphrased from the `nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_:
            It is important TO NEVER to keep the nRF24L01+ in TX mode for more than 4 milliseconds at a time. If the [`auto_ack` and `dynamic_payloads`] features are enabled, nRF24L01+ is never in TX mode longer than 4 milliseconds.

        .. tip:: Use this function at your own risk. Because of the underlying `"Enhanced ShockBurst Protocol" <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132607>`_, this is often avoided if you enable the `dynamic_payloads` attribute (the `auto_ack` attribute is enabled with `dynamic_payloads` automatically) to obey the 4 milliseconds rule. Alternatively, you MUST additionally use either interrupt flags/IRQ pin with user defined timer(s) to AVOID breaking the 4 millisecond rule. If the `nRF24L01+ Specifications Sheet explicitly states this <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_, we have to assume radio damage or misbehavior as a result of disobeying the 4 milliseconds rule. Cleverly, `TMRh20's arduino library <http://tmrh20.github.io/RF24/classRF24.html>`_ recommends using auto re-transmit delay (the `ard` attribute; see also `arc` attribute) to avoid breaking this rule, but we have not verified this strategy.

        """
        # capture snapshot of TX/RX FIFOs' status
        self._fifo = self._reg_read(FIFO_STATUS)
        assert (buf is None and self.reuse_tx) or 0 <= len(buf) <= 32

        # pad out or truncate data to fill payload_length if dynamic_payloads == False
        if not self.dynamic_payloads:
            if len(buf) < self.payload_length:
                for _ in range(self.payload_length - len(buf)):
                    buf += b'\x00'
            elif len(buf) > self.payload_length:
                buf = buf[:self.payload_length]
        if not self.power:# power up radio if it isn't yet
            self._config = (self.config & 0x7d) + 2
            self._reg_write(0x0, self.config)
            # power up/down takes < 150 us + 4 us
            time.sleep(0.00016)

        if reUseTX:  # mark reuse_tx has been triggered
            # payload will get re-used. This command tells the radio not pop TX payload from FIFO on success
            self._reg_read(0xE3) # command returns only status byte

        # now handle the payload accordingly
        if self.reuse_tx and buf is None: # shouldn't execeute on the initial triggering
            with self: # write no payload
                pass # this cycles the CSN pin to enable transmission of re-used payload
        elif AskNoACK or not self.auto_ack:
            # payload doesn't require acknowledgment
            # 0xB0 = W_TX_PAYLOAD_NO ACK
            self._reg_write_bytes(0xB0, buf) # write appropriate command with payload
        else:# payload does require acknowledgment
            # 0xA0 = W_TX_PAYLOAD
            self._reg_write_bytes(0xA0, buf) # write appropriate command with payload

        # enable radio comms so it can send the data by starting the mandatory minimum 10 us pulse on CE. Let send() measure this pulse for blocking reasons
        self.ce.value = 1
        # radio will automatically go to standby-II after transmission while CE is still HIGH only if dynamic_payloads and auto_ack are enabled
        return self.fifo
