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

.. important:: The nRF24L01 has 3 key features that are very interdependent of each other. Their priority of dependence is as follows:

    1. `dynamic_payloads` feature allowing either TX/RX nRf24L01 to be able to send/receive payloads with their size written into the payloads' packet. With this disabled, both RX/TX nRF24L01 must use matching `payload_length` attributes.
    2. `auto_ack` feature provides transmission verification by imediatedly sending an acknowledgment (ACK) packet in response to freshly received payloads. `auto_ack` requires `dynamic_payloads` to be enabled.
    3. `ack` feature allows the user to append a payload to the ACK packet, thus instant bi-directional communication. A transmitting ACK payload must be loaded into the nRF24L01's TX FIFO buffer (done using `load_ack()`) BEFORE receiving the payload that is to be acknowledged. Once transmitted, the payload is released from the TX FIFO buffer. This feature obviously requires the `auto_ack` feature enabled.

Remeber that the nRF24L01's FIFO (first-in,first-out) buffer has 3 levels. This means that there can be up to 3 payloads waiting to be read (RX) and up to 3 payloads waiting to be transmit (TX).

With the `auto_ack` feature enabled you get:

    * CRC (cycle redundancy checking) automatically enabled
    * to change amount of automatic re-transmit attempts and the delay time between them. See the `ard` and `arc` attributes.

"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import time
from adafruit_bus_device.spi_device import SPIDevice

# nRF24L01+ registers
CONFIG       = 0x00 # register for configuring IRQ, CRC, PWR & RX/TX roles
EN_AA        = 0x01 # register for auto-ACK feature. each bit represents this feature per pipe
EN_RX        = 0x02 # register to open/close pipes. each bit represents this feature per pipe
SETUP_AW     = 0x03 # address width register
SETUP_RETR   = 0x04 # auto-retry count and delay register
RF_CH        = 0x05 # channel register
RF_SETUP     = 0x06 # RF Power Amptlitude & Data Rate
RX_ADDR      = 0x0a # RX pipe addresses rangeing [0,5]:[0xA:0xF]
RX_PW        = 0x11 # RX payload widths on pipes ranging [0,5]:[0x11,0x16]
FIFO         = 0x17 # register containing info on both RX/TX FIFOs + re-use payload flag
DYNPD	     = 0x1c # dynamic payloads feature. each bit represents this feature per pipe
FEATURE      = 0x1d # global enablers/disablers for dynamic payloads, auto-ACK, and custom ACK features

class RF24:
    """A driver class for the nRF24L01 transceiver radio. This class aims to be compatible with other devices in the nRF24xxx product line, but officially only supports (through testing) the nRF24L01 and nRF24L01+ devices.

    :param ~busio.SPI spi: The object for the SPI bus that the nRF24L01 is connected to.

        .. tip:: This object is meant to be shared amongst other driver classes (like adafruit_mcp3xxx.mcp3008 for example) that use the same SPI bus. Otherwise, multiple devices on the same SPI bus with different spi objects may produce errors or undesirable behavior.

    :param ~digitalio.DigitalInOut csn: The digital output pin that is connected to the nRF24L01's CSN (Chip Select Not) pin. This is required.
    :param ~digitalio.DigitalInOut ce: The digital output pin that is connected to the nRF24L01's CE (Chip Enable) pin. This is required.
    :param int channel: This is used to specify a certain frequency that the nRF24L01 uses. Defaults to 76 and can be changed at any time by using the `channel` attribute
    :param int payload_length: This is the length (in bytes) of a single payload to be transmitted or received. This is optional and ignored if the `dynamic_payloads` attribute is enabled. Defaults to the maximum (32). This can be changed at any time by using the `payload_length` attribute
    :param int address_length: This is the length (in bytes) of the addresses that are assigned to the data pipes for transmitting/receiving. It is optional and defaults to 5. This can be changed at any time by using the `address_length` attribute
    :param int ard: This specifies the automatic re-transmit delay (between attempts to re-transmit). See the `ard` attribute for more details. This parameter must be a multiple of 250 in the range [250,4000]
    :param int arc: This specifies the automatic re-transmit count (maximum number of attempts to re-transmit). See the `arc` attribute for more details. This parameter must be in the range [0,15]
    :param int crc: This parameter controls the CRC setting of transmitted packets. Options are ``0`` (off), ``1`` or ``2`` (byte long CRC enabled). See the `crc` attribute for more details.
    :param int data_rate: This parameter controls the RF data rate setting of transmissions. Options are ``1`` (Mbps), ``2`` (Mbps), or ``250`` (Kbps). See the `data_rate` attribute for more details.
    :param int pa_level: This parameter controls the RF power amplifier setting of transmissions. Options are ``0`` (dBm), ``-6`` (dBm), ``-12`` (dBm), or ``-18`` (dBm). See the `pa_level` attribute for more details.
    :param bool dynamic_payloads: This parameter enables or disables the dynamic payload length feature of the nRF24L01. It is optional and defaults to enabled. This can be changed at any time by using the `dynamic_payloads` attribute
    :param bool auto_ack: This parameter enables or disables the automatic acknowledgment (ACK) feature of the nRF24L01. It is optional and defaults to enabled. This can be changed at any time by using the `auto_ack` attribute
    :param bool ask_no_ack: This represents a special flag that has to be thrown to enable a feature specific to individual payloads. This parameter is here for completeness as it is untested feature. Enabling/Disabling this does not affect `auto_ack` attribute.
    :param bool ack: This represents a special flag that has to be thrown to enable a feature allowing custom response payloads appended to the ACK packets. This parameter should be engaged only during transmissions that make use of this feature. Enabling this does affect `auto_ack` attribute. See the `ack` attribute for more details.
    :param bool irq_DR: When "Data is Ready", this configures the interrupt (IRQ) trigger of the nRF24L01's IRQ pin (active low). This parameter is optional and defaults to enabled. This can be changed at any time by using the `interrupt_config()` method.
    :param bool irq_DS: When "Data is Sent", this configures the interrupt (IRQ) trigger of the nRF24L01's IRQ pin (active low). This parameter is optional and defaults to enabled. This can be changed at any time by using the `interrupt_config()` method.
    :param bool irq_DF: When "max retry attempts are reached" (specified by the `arc` attribute), this configures the interrupt (IRQ) trigger of the nRF24L01's IRQ pin (active low). This parameter is optional and defaults to enabled. This can be changed at any time by using the `interrupt_config()` method.

    """
    def __init__(self, spi, csn, ce, channel=76, payload_length=32, address_length=5, ard=1500, arc=3, crc=2, data_rate=1, pa_level=0, dynamic_payloads=True, auto_ack=True, ask_no_ack=True, ack=False, irq_DR=True, irq_DS=True, irq_DF=True):
        # init the SPI bus and pins
        self.spi = SPIDevice(spi, chip_select=csn, baudrate=4000000)
        self.payload_length = payload_length # inits internal attribute
        # last address assigned to pipe0 for reading. init to None
        self.pipe0_read_addr = None
        self._fifo = 0

        # store the ce pin
        self.ce = ce
        # reset ce.value & disable the chip comms
        self.ce.switch_to_output(value=False)
        # if radio is powered up and CE is LOW: standby-I mode
        # if radio is powered up and CE is HIGH: standby-II mode

        # NOTE per spec sheet: nRF24L01+ must be in a standby or power down mode before writing to the configuration register
        # configure the CONFIG register:IRQ(s) config, setup CRC feature, and trigger standby-I + TX mode (the "| 2")
        if 0 <= crc <= 2:
            self._config = ((not irq_DR) << 6) | ((not irq_DS) << 5) | ((not irq_DF) << 4) | ((crc + 1) << 2 if crc else 0) | 2
            self._reg_write(CONFIG, self._config) # dump to register
        else:
            raise ValueError("CRC byte length must be an int equal to 0 (off), 1, or 2")
        # check for device presence by verifying nRF24L01 is in TX + standby-I mode
        if self._reg_read(CONFIG) & 3 == 2: # if in TX + standby-I mode
            self.power = False # power down
        else:  # hardware presence check NOT passed
            print(bin(self._reg_read(CONFIG)))
            raise RuntimeError("nRF24L01 Hardware not responding")

        # configure the SETUP_RETR register
        if 250 <= ard <= 4000 and ard % 250 == 0 and 0 <= arc <= 15:
            self._setup_retr = (int((ard - 250) / 250) << 4) | arc
        else:
            raise ValueError("automatic re-transmit delay can only be a multiple of 250 in range [250,4000]\nautomatic re-transmit count(/attempts) must in range [0,15]")

        # configure the RF_SETUP register
        if data_rate in (1, 2, 250) and pa_level in (-18, -12, -6, 0):
            data_rate = 0 if data_rate == 1 else (8 if data_rate == 2 else 0x20)
            pa_level = (3 - int(pa_level / -6)) * 2
            self._rf_setup = data_rate | pa_level
        else:
            raise ValueError("data rate must be one of the following ([M,M,K]bps): 1, 2, 250\npower amplifier must be one of the following (dBm): -18, -12, -6, 0")

        # manage dynamic_payloads, auto_ack, and ack features
        self._dyn_pl = 0x3F if dynamic_payloads else 0 # 0x3F == enabled on all pipes
        self._aa = 0x3F if auto_ack and dynamic_payloads else 0 # 0x3F == enabled on all pipes
        self._features = (dynamic_payloads << 2) | ((ack if auto_ack and dynamic_payloads else False) << 1) | ask_no_ack

        # init the last few singleton attribute
        self._channel = channel
        self._addr_len = address_length

        # init the _open_pipes attribute (reflects only RX state on each pipe)
        self._open_pipes = 0 # <- means all pipes closed

        with self: # write to registers & power up
            # using __enter__() configures all virtual features and settings to the hardware registers
            self.ce.value = 0 # ensure standby-I mode to write to CONFIG register
            self._reg_write(CONFIG, self._config | 1) # enable RX mode
            time.sleep(0.000015) # wait time for transitioning modes RX/TX
            self.flush_rx() # spec sheet say "used in RX mode"
            self._reg_write(CONFIG, self._config & 0xC) # power down + TX mode
            time.sleep(0.000015) # wait time for transitioning modes RX/TX
            self.flush_tx() # spec sheet say "used in TX mode"
            self.clear_status_flags() # writes directly to STATUS register

    def __enter__(self):
        """This ensures that the hardware is properly configured for the virtual object used to drive it by dumping all pre-existing register data buffered from previously configuring the device's features."""
        self._reg_write(CONFIG, self._config & 0x7C) # dump IRQ and CRC data to CONFIG register
        self._reg_write(RF_SETUP, self._rf_setup) # dump to RF_SETUP register
        self._open_pipes = self._reg_read(EN_RX) # update open pipe info from current state of EN_RXADDR register
        self._reg_write(DYNPD, self._dyn_pl) # dump to DYNPD register
        self._reg_write(EN_AA, self._aa) # dump to EN_AA register
        self._reg_write(FEATURE, self._features) # dump to FEATURE register
        self._reg_write(SETUP_RETR, self._setup_retr) # dump to SETUP_RETR register
        self.address_length = self._addr_len # writes directly to SETUP_AW register
        self.channel = self._channel # writes directly to RF_CH register
        return self

    def __exit__(self, *exc):
        """this does nothing as the state of the radio should ultimately be at the user's descretion"""
        return False

    def _reg_read(self, reg):
        """A helper function to read a single byte of data from a specified register on the nRF24L01's internal IC. THIS IS NOT MEANT TO BE DIRECTLY CALLED BY END-USERS.

        :param int reg: The address of the register you wish to read from.

        Please refer to `Chapter 9 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1090864>`_ for applicable register addresses.

        """
        buf = bytearray(2) # 2 = 1 status byte + 1 byte of returned content
        with self.spi as spi:
            time.sleep(0.005) # time for CSN to settle
            spi.readinto(buf, write_value=reg)
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
        with self.spi as spi:
            time.sleep(0.005) # time for CSN to settle
            spi.readinto(buf, write_value=reg)
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
        with self.spi as spi:
            time.sleep(0.005) # time for CSN to settle
            spi.write_readinto(outBuf, inBuf)
        self._status = inBuf[0] # save status byte

    def _reg_write(self, reg, value = None):
        """A helper function to write a single byte of data to a specified register on the nRF24L01's internal IC. THIS IS NOT MEANT TO BE DIRECTLY CALLED BY END-USERS.

        :param int reg: The address of the register you wish to read from.
        :param int value: The one byte content to write to a register specified by `reg`. There is a rigid expectation of bit order & content. There is no bounds checking on this parameter.

        Please refer to `Chapter 9 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1090864>`_ for applicable register addresses.

        """
        if value is None:
            outBuf = bytes([reg])
        else:
            outBuf = bytes([0x20 | reg, value])
        inBuf = bytearray(len(outBuf))
        with self.spi as spi:
            time.sleep(0.005) # time for CSN to settle
            spi.write_readinto(outBuf, inBuf)
        self._status = inBuf[0] # save status byte

    def flush_rx(self):
        """An helper function to flush the nRF24L01's internal RX FIFO buffer. (write-only)

        ..note:: The nRF24L01 RX FIFO is 3 level stack that holds payload data. This means that there can be up to 3 received payloads (of maximum length equal to 32 bytes) waiting to be read (and popped from the stack) by `recv()`. This function clears all 3 levels.

        """
        self._reg_write(0xE2)

    def flush_tx(self):
        """An helper function to flush the nRF24L01's internal TX FIFO buffer. (write-only)

        ..note:: The nRF24L01 TX FIFO is 3 level stack that holds payload data. This means that there can be up to 3 payloads (of maximum length equal to 32 bytes) waiting to be transmitted by `send()` or `write()`. This function clears all 3 levels. It is worth noting that the payload data is only popped from the TX FIFO stack upon successful transmission and the ``reUseTX`` parameter in send() & write() is passed as `False` (that parameter's default value).

        """
        self._reg_write(0xE1)

    @property
    def irq_DR(self):
        """A `bool` that represents the "Data Ready" interrupted flag. (read-only)

        * `True` represents Data is in the RX FIFO buffer
        * `False` represents anything depending on context (state/condition of FIFO buffers) -- usually this means the flag's been reset.

        Pass ``dataReady`` parameter as `True` to `clear_status_flags()` and reset this. As this is a virtual representation of the interrupt event, this attribute will always be updated despite what the actual IRQ pin is configured to do about this event.

        Calling this does not execute an SPI transaction. It only exposes that latest data contained in the STATUS byte that's always returned from any other SPI transactions.

        """
        return bool(self._status & 0x40)

    @property
    def irq_DS(self):
        """A `bool` that represents the "Data Sent" interrupted flag. (read-only)

        * `True` represents a successful transmission
        * `False` represents anything depending on context (state/condition of FIFO buffers) -- usually this means the flag's been reset.

        Pass ``dataSent`` parameter as `True` to `clear_status_flags()` to reset this. As this is a virtual representation of the interrupt event, this attribute will always be updated despite what the actual IRQ pin is configured to do about this event.

        Calling this does not execute an SPI transaction. It only exposes that latest data contained in the STATUS byte that's always returned from any other SPI transactions.

        """
        return bool(self._status & 0x20)

    @property
    def irq_DF(self):
        """A `bool` that represents the "Data Failed" interrupted flag. (read-only)

        * `True` signifies the nRF24L01 attemped all configured retries?
        * `False` represents anything depending on context (state/condition) -- usually this means the flag's been reset.

        Pass ``dataFail`` parameter as `True` to `clear_status_flags()` to reset this. As this is a virtual representation of the interrupt event, this attribute will always be updated despite what the actual IRQ pin is configured to do about this event.see also the `arc` and `ard` attributes.

        Calling this does not execute an SPI transaction. It only exposes that latest data contained in the STATUS byte that's always returned from any other SPI transactions.

        """
        return bool(self._status & 0x10)

    @property
    def tx_full(self):
        """An attribute to represent the nRF24L01's status flag signaling that the TX FIFO buffer is full.(read-only)

        Calling this does not execute an SPI transaction. It only exposes that latest data contained in the STATUS byte that's always returned from any other SPI transactions.
        :returns:

            * `True` for TX FIFO buffer is full
            * `False` for TX FIFO buffer is NOT full

        """
        return bool(self._status & 1)

    def update(self):
        """This function is only used to get an updated status byte over SPI from the nRF24L01. Refreshing the status byte is vital to checking status of the interrupt, RX pipe number related to current RX payload, and if the TX FIFO buffer is full."""
        self._reg_write(0xFF) # perform non-operation to get status byte (should be faster)

    def what_happened(self, dump_pipes=False):
        """This debuggung function aggregates and outputs all status/condition related information from the nRF24L01. Some flags may be irrelevant depending on nRF24L01's state/condition. (read-only)

        :prints:

            - ``Channel`` The current setting of the `channel` attribute
            - ``CRC bytes`` The current setting of the `crc` attribute
            - ``Address length`` The current setting of the `address_length` attribute
            - ``Payload lengths`` The current setting of the `payload_length` attribute
            - ``Auto retry delay`` The current setting of the `ard` attribute
            - ``Auto retry attempts`` The current setting of the `arc` attribute
            - ``IRQ - Data Ready`` The current setting of the IRQ pin on "Data Ready" event
            - ``IRQ - Data Sent`` The current setting of the IRQ pin on "Data Sent" event
            - ``IRQ - Data Fail`` The current setting of the IRQ pin on "Data Fail" event
            - ``Data Ready`` Is there RX data ready to be read?
            - ``Data Sent`` Has the TX data been sent?
            - ``Data Failed`` Has the maximum attempts to re-transmit been reached?
            - ``Packets Lost`` Amount of packets lost (transmission failures)
            - ``Retry Attempts Made`` Maximum amount of attempts to re-transmit during last transmission (resets per payload)
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

        :param bool dump_pipes: `True` appends the output and prints: ``Pipe [#] ([open/closed]) bound: [address]`` where "#" represent the pipe number, the "open/closed" status is relative to the pipe's RX status, and "address" is read directly from the nRF24L01 registers. Default is `False` and skips this extra information.

        Remember, we only use `recv()` to read payload data as that transaction will also remove it from the FIFO buffer.

        .. note:: Only some data is fetched directly from nRF24L01. Specifically ``Packets Lost``, ``Retry Attempts Made``, and all pipe addresses. That data is not stored internally on purpose. All other data is computed from memory of last SPI transaction about that data's register.

        """
        watchdog = self._reg_read(0x08) # OBSERVE_TX register
        print("Channel___________________{} ~ {} MHz\nCRC bytes_________________{}\nAddress length____________{} bytes\nPayload lengths___________{} bytes\nAuto retry delay__________{} microseconds\nAuto retry attempts_______{} maximum\nPackets Lost______________{} total\nRetry Attempts Made_______{}\nIRQ - Data Ready______{}    Data Ready___________{}\nIRQ - Data Fail_______{}    Data Failed__________{}\nIRQ - Data Sent_______{}    Data Sent____________{}\nTX FIFO full__________{}    TX FIFO empty________{}\nRX FIFO full__________{}    RX FIFO empty________{}\nAsk no ACK_________{}    Custom ACK Payload___{}\nDynamic Payloads___{}    Auto Acknowledgment__{}\nPrimary Mode_____________{}    Power Mode___________{}".format(self.channel, (self.channel + 2400) / 1000 , self.crc, self.address_length, self.payload_length, self.ard, self.arc, (watchdog & 0xF0) >> 4,  watchdog & 0x0F, "_True" if not bool(self._config & 0x40) else "False", self.irq_DR, "_True" if not bool(self._config & 0x20) else "False", self.irq_DF, "_True" if not bool(self._config & 0x10) else "False", self.irq_DS,  "_True" if bool(self.tx_full) else "False",  bool(self.fifo(True,True)), "_True" if bool(self._fifo & 2) else "False",  bool(self._fifo & 1), "_Allowed" if bool(self._features & 1) else "Disabled", "Enabled" if self.ack else "Disabled", "_Enabled" if self.dynamic_payloads else 'Disabled', "Enabled" if self.auto_ack else 'Disabled', "RX" if self.listen else "TX", ("Standby-II" if self.ce.value else "Standby-I") if (self._config & 2) else "Off" ))
        if dump_pipes:
            for i in range(RX_ADDR, RX_ADDR + 6):
                j = i - RX_ADDR
                isOpen = " open " if (self._open_pipes & (1 << j)) else "closed"
                print("Pipe {} ({}) bound: {}".format(j, isOpen, self._reg_read_bytes(i)))

    def clear_status_flags(self, dataReady=True, dataSent=True, dataFail=True):
        """This clears the interrupt flags in the status register. This functionality is exposed for asychronous applications only.

        :param bool dataReady: specifies wheather to clear the "RX Data Ready" flag.
        :param bool dataSent: specifies wheather to clear the "TX Data Sent" flag.
        :param bool dataFail: specifies wheather to clear the "Max Re-transmit reached" flag.

        .. note:: Clearing certain flags is necessary for continued operation of the nRF24L01 despite wheather or not the user is taking advantage of the interrupt (IRQ) pin. Directly calling this function without being familiar with the nRF24L01's expected behavior (as outlined in the Specifications Sheet) can cause undesirable behavior. See `Appendix A-B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1047965>`_ for an outline of proper behavior.

        """
        # 0x07 = STATUS register; only bits 6 through 4 are write-able
        self._reg_write(0x07, (dataReady << 6) | (dataSent << 5) | (dataFail << 4))

    def interrupt_config(self, onDataFail=True, onDataSent=True, onDataRecv=True):
        """Sets the configuration of the nRF24L01's Interrupt (IRQ) pin. IRQ signal from the nRF24L01 is active LOW. (write-only)
        To fetch the status (not config) of these interrupt (IRQ) flags, use the  `irq_DF`, `irq_DS`, `irq_DR` attributes respectively.

        :param bool onDataFail: If this is `True`, then interrupt pin goes active LOW when maximum number of attempts to re-transmit the packet have been reached.
        :param bool onDataSent: If this is `True`, then interrupt pin goes active LOW when a payload from TX buffer is successfully transmitted. If `auto_ack` attribute is enabled, then interrupt pin only goes active LOW when acknowledgment (ACK) packet is received.
        :param bool onDataRecv: If this is `True`, then interrupt pin goes active LOW when there is new data to read in the RX FIFO.

            .. tip:: Paraphrased from nRF24L01+ Specification Sheet:

                The procedure for handling ``onDataRecv`` interrupt should be:

                1. read payload through `recv()`
                2. clear ``dataReady`` status flag (taken care of by using `recv()` in previous step)
                3. read FIFO_STATUS register to check if there are more payloads available in RX FIFO buffer. (a call to `pipe()`, `any()` or even ``(False,True)`` as parameters to `fifo()` will get this result)
                4. if there is more data in RX FIFO, repeat from step 1

        """
        self._config = self._reg_read(CONFIG) # refresh data
        # save to register and update local copy of pwr & RX/TX modes' flags
        self._config = (self._config & 0x0F) | (not onDataFail << 4) | (not onDataSent << 5) | (not onDataRecv << 6)
        self._reg_write(CONFIG, self._config)

    @property
    def ack(self):
        """This attribute contains the status of the nRF24L01's capability to use custom payloads as part of the automatic acknowledgment (ACK) packet. You can use this attribute to set/check if this specific feature is enabled.

        :param bool enable: `True` enables the use of custom ACK payloads appended to receiving transmissions. `False` disables the use of custom ACK payloads

        .. note:: As `dynamic_payloads` and `auto_ack` attribute are required for this feature to work, they are automatyically enabled as needed. Disabling this feature does not require nor need to disable the `auto_ack` & `dynamic_payloads` attributes (they can work just fine without this).
        """
        return bool((self._features & 2) and self.auto_ack)

    @ack.setter
    def ack(self, enable):
        assert isinstance(enable, (bool,int))
        # we need to throw the EN_ACK_PAY flag in the FEATURES register accordingly on both TX & RX nRF24L01s
        if self.ack != enable: # if enabling
            self.auto_ack = True # ensure auto_ack feature is enabled
        else:
            # setting auto_ack feature automatically updated the _features attribute, so
            self._features = self._reg_read(FEATURE) # refresh data here
        self._features = (self._features & 5) | (2 if enable else 0)
        self._reg_write(FEATURE,  self._features)

    @property
    def power(self):
        """This `bool` attribute controls the PWR_UP bit in the CONFIG register.

        - `False` basically puts the nRF24L01 to sleep. No transmissions are executed when sleeping.
        - `True` powers up the nRF24L01

        .. note:: This attribute needs to be `True` if you want to put radio on standby-II (CE pin is HIGH) or standby-I (CE pin is LOW) modes. In case of either standby modes, transmissions are only executed during standby-II using `send()` or ` calling_fast()`. Otherwise OTA listening is done from standby-II using 'listen' attribute (see `Chapter 6.1.2-7 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132980>`_).

        """
        self._config = self._reg_read(CONFIG) # refresh data
        return bool(self._config & 2)

    @power.setter
    def power(self, isOn):
        assert isinstance(isOn, (bool, int))
        # capture surrounding flags and set PWR_UP flag according to isOn boolean
        if self.power != isOn:
            # only write changes
            self._config = (self._config & 0x7d) | (isOn << 1) # doesn't affect TX?RX mode
            self._reg_write(CONFIG, self._config)
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
        # 1 == EN_AA register for ACK feature
        return self._aa and self.dynamic_payloads

    @auto_ack.setter
    def auto_ack(self, enable):
        assert isinstance(enable, (bool, int))
        # this feature requires dynamic payloads enabled; check for that now
        if not self.dynamic_payloads and enable: # if dynamic_payloads is off and this is enabling
            self.dynamic_payloads = enable # enable dynamic_payloads
        self._aa = 0x3F if enable else 0 # the following 0x3F == enabled auto_ack on all pipes
        self._reg_write(EN_AA, self._aa) # 1 == EN_AA register for ACK feature
        # nRF24L01 automatically enables CRC if ACK packets are enabled in the FEATURE register

    @property
    def dynamic_payloads(self):
        """This `bool` attribute controls dynamic payload length feature on all nRF24L01's data pipes.

        - `True` enables nRF24L01's dynamic payload length feature.
            Enabling dynamic payloads REQUIRES enabling the automatic acknowledgment feature on corresponding data pipes AND asserting 'enable dynamic payloads' flag of FEATURE register (both are automatically handled here).
        - `False` disables nRF24L01's dynamic payload length feature.
            As the `dynamic_payloads` requirement mentioned above, disabling `dynamic_payloads` does not disable `auto_ack` (use `auto_ack` attribute to disable that).

        .. note:: There is no plan to implement dynamic payload lengths on a per data pipe basis, therefore all 6 pipes are treated the same.

        """
        return bool(self._dyn_pl and (self._features & 4))

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        assert isinstance(enable, (bool, int))
        self._features = self._reg_read(FEATURE) # refresh data
        if self.auto_ack and not enable: # disabling and auto_ack is still on
            self.auto_ack = enable # disable auto_ack as this is required for it
        # save changes to registers(& their shadows)
        if self._features & 4 != enable: # if not already
            # throw a specific global flag for enabling dynamic payloads
            self._features = (self._features & 3) | (enable << 2)
            self._reg_write(FEATURE, self._features)
        #  0x3F == all pipes have enabled dynamic payloads
        self._dyn_pl = 0x3F if enable else 0
        self._reg_write(DYNPD, self._dyn_pl)

    @property
    def arc(self):
        """"This `int` attribute specifies the nRF24L01's number of attempts to re-transmit TX payload when acknowledgment packet is not received. The nRF24L01 does not attempt to re-transmit if `auto_ack` attribute is disabled. Default is set to 3.

        A valid input value must be in range [0,15]. Otherwise a `ValueError` exception is thrown.

        """
        # SETUP_AW + 1 = SETUP_RETR register
        self._setup_retr = self._reg_read(SETUP_AW + 1) # refresh data
        return self._setup_retr & 0x0f

    @arc.setter
    def arc(self, count):
        # SETUP_AW + 1 = SETUP_RETR register
        if 0 <= count <= 15:
            if self.arc & 0x0F != count:# write only if needed
                # save changes to register(& its shadow)
                self._setup_retr = (self._setup_retr & 0xF0) | count
                self._reg_write(SETUP_AW + 1, self._setup_retr)
        else:
            raise ValueError("automatic re-transmit count(/attempts) must in range [0,15]")

    @property
    def ard(self):
        """This `int` attribute specifies the nRF24L01's delay (in microseconds) between attempts to automatically re-transmit the TX payload when an acknowledgement (ACK) packet is not received. During this time, the nRF24L01 is listening for the ACK packet. If the `auto_ack` attribute is disabled, this attribute is not applied.

        .. note:: Paraphrased from spec sheet:
            Please take care when setting this parameter. If the ACK payload is more than 15 bytes in 2 Mbps data rate, the ARD must be 500µS or more. If the ACK payload is more than 5 bytes in 1 Mbps data rate, the ARD must be 500µS or more. In 250kbps data rate (even when the payload is not in ACK) the ARD must be 500µS or more.

            See `data_rate` attribute on how to set the data rate of the nRF24L01's transmissions.

        A valid input value must be a multiple of 250 in range [250,4000]. Otherwise a `ValueError` exception is thrown. Default is 1500.

        """
        # SETUP_AW + 1 = SETUP_RETR register
        self._setup_retr = self._reg_read(SETUP_AW + 1) # refresh data
        return ((self._setup_retr & 0xf0) >> 4) * 250 + 250

    @ard.setter
    def ard(self, t):
        # SETUP_AW + 1 = SETUP_RETR register
        if 250 <= t <= 4000 and t % 250 == 0:
            # set new ARD data and current ARC data to register
            if self.ard != t:# write only if needed
                # save changes to register(&its Shadow)
                self._setup_retr = (int((t-250)/250) << 4) | (self._setup_retr & 0x0F)
                self._reg_write(SETUP_AW + 1, self._setup_retr)
        else:
            raise ValueError("automatic re-transmit delay can only be a multiple of 250 in range [250,4000]")

    @property
    def address_length(self):
        """This `int` attribute specifies the length (in bytes) of addresses to be used for RX/TX pipes.
        A valid input value must be in range [3,5]. Otherwise a `ValueError` exception is thrown. Default is 5.

        .. note:: nRF24L01 uses the LSByte for padding addresses with lengths of less than 5 bytes.

        """
        return self._reg_read(SETUP_AW) + 2

    @address_length.setter
    def address_length(self, length):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        if 3 <= length <= 5:
            # address width is saved in 2 bits making range = [3,5]
            self._addr_len = length
            self._reg_write(SETUP_AW, length - 2)
        else:
            raise ValueError("address length can only be set in range [3,5] bytes")

    @property
    def payload_length(self):
        """This `int` attribute specifies the length (in bytes) of payload that is regaurded, meaning 'how big of a payload should the radio care about?' If the `dynamic_payloads` attribute is enabled, this attribute has no affect. This is really a place holder for the ocasional need to specify the payload length on a per pipe basis.
        A valid input value must be in range [0,32]. Otherwise a `ValueError` exception is thrown. Default is 32.

        - Payloads of less than input value will be truncated.
        - Payloads of greater than input value will be padded with zeros.
        - Input value of 0 negates radio's transmissions.

        """
        return self._payload_length

    @payload_length.setter
    def payload_length(self, length):
        # max payload size is 32 bytes
        if 0 <= length <= 32:
            # save for access via getter property
            self._payload_length = length
        else:
            raise ValueError("payload length can only be set in range [0,32] bytes")

    @property
    def data_rate(self):
        """This `int` attribute specifies the nRF24L01's frequency data rate for OTA (over the air) transmissions.

        A valid input value is:

        - ``1`` sets the frequency data rate to 1 Mbps
        - ``2`` sets the frequency data rate to 2 Mbps
        - ``250`` sets the frequency data rate to 250 Kbps

        Any invalid input throws a `ValueError` exception. Default is 1 Mbps.

        .. warning:: 250 Kbps is be buggy on the non-plus models of the nRF24L01 product line. If you use 250 Kbps data rate, and some transmissions report failed by the transmitting nRF24L01, even though the same packet in question actually reports received by the receiving nRF24L01, try a different different data rate.

        """
        self._rf_setup = self._reg_read(RF_SETUP) # refresh data
        if self._rf_setup & 0x28 == 0x0:
            return 1
        elif self._rf_setup & 0x28 == 0x8:
            return 2
        elif self._rf_setup & 0x28 == 0x20:
            return 250

    @data_rate.setter
    def data_rate(self, speed):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        if speed in (1, 2, 250):
            if self.data_rate != speed:
                speed = 0 if speed == 1 else (8 if speed == 2 else 0x20)
            # save changes to register(& its shadow)
            self._rf_setup = self._rf_setup & 0xD7 | speed
            self._reg_write(RF_SETUP, self._rf_setup)
        else:
            raise ValueError("data rate must be one of the following ([M,M,K]bps): 1, 2, 250")

    @property
    def pa_level(self):
        """This `int` attribute specifies the nRF24L01's power amplifier level (in dBm).

        A valid input value is:

        - ``-18`` sets the nRF24L01's power amplifier to -18 dBm (lowest)
        - ``-12`` sets the nRF24L01's power amplifier to -12 dBm
        - ``-6`` sets the nRF24L01's power amplifier to -6 dBm
        - ``0`` sets the nRF24L01's power amplifier to 0 dBm (highest)

        Any invalid input throws a `ValueError` exception. Default is 0 dBm.

        """
        self._rf_setup = self._reg_read(RF_SETUP) # refresh data
        return (3 - ((self._rf_setup & RF_SETUP) >> 1)) * -6 # this seems to work!

    @pa_level.setter
    def pa_level(self, power):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        if power in (-18, -12, -6, 0):
            power = (3 - int(power / -6)) * 2 # this works
            # save changes to register (& its shadow)
            self._rf_setup = (self._rf_setup & 0xF9) | power
            self._reg_write(RF_SETUP, self._rf_setup)
        else:
            raise ValueError("power amplitude must be one of the following (dBm): -18, -12, -6, 0")

    @property
    def crc(self):
        """This `int` attribute specifies the nRF24L01's cycle redundancy checking (CRC) encoding scheme in terms of bytes.

        A valid input value is in range [0,2]:

        - ``0`` disables CRC
        - ``1`` enables CRC encoding scheme using 1 byte
        - ``2`` enables CRC encoding scheme using 2 bytes

        Any invalid input throws a `ValueError` exception. Default is enabled using 2 bytes.

        .. note:: The nRF24L01 automatically enables CRC if automatic acknowledgment feature is enabled (see `auto_ack` attribute).

        """
        self._config = self._reg_read(CONFIG) # refresh data
        return max(0, ((self._config & 12) >> 2) - 1) # this works

    @crc.setter
    def crc(self, length):
        if 0 <= length <= 2:
            if self.crc != length:
                length = (length + 1) << 2 if length else 0 # this works
                # save changes to register(&its Shadow)
                self._config = self._config & 0x73 | length
                self._reg_write(0, self._config)
        else:
            raise ValueError("CRC byte length must be an int equal to 0 (off), 1, or 2")

    @property
    def channel(self):
        """This `int` attribute specifies the nRF24L01's frequency (in 2400 + `channel` KHz).

        A valid input value must be in range [0-125] (that means [2.4, 2.525] MHz). Otherwise a `ValueError` exception is thrown. Default is 76 (for compatibility with `TMRh20's arduino library <http://tmrh20.github.io/RF24/classRF24.html>`_ default).

        .. important:: This attribute must match on both RX & TX nRF24L01 devices during transmissions for success.

        """
        return self._reg_read(RF_CH)

    @channel.setter
    def channel(self, channel):
        if 0 <= channel <= 125:
            self._channel = channel
            self._reg_write(RF_CH, channel) # always wries to reg
        else:
            raise ValueError("channel acn only be set in range [0,125]")

    @property
    def listen(self):
        """An attribute to represent the nRF24L01 primary role as a radio.

        Setting this attribute uses the built-in ``_start_listening()`` and ``_stop_listening()`` to control this attribute properly. As handling the transition between various modes involves playing with the `power` attribute and the nRF24L01's CE pin.

        :param bool rx:

            `True` enables RX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this function flushes the RX FIFO, clears the `irq_DR` status flags, and puts nRF24L01 in power up mode. Notice the CE pin should be held HIGH during RX mode

            `False` disables RX mode. As mentioned in above link, this puts nRF24L01's power in Standby-I (CE pin is LOW meaning low current & no transmissions) mode which is ideal for post-transmission work. This attribute doesn't flush the FIFOs, so remember to flush your 3-level FIFO buffers when appropriate using `flush_tx()` or `flush_rx()`. This attribute does not power down the nRF24L01, but will power it up when needed; use `power` attribute set to `False` to put the nRf24L01 to sleep.

        :returns:

                * `True` for RX mode
                * `False` for TX mode


        """
        return self.power and bool(self._config & 1)

    @listen.setter
    def listen(self, rx):
        assert isinstance(rx, (bool,int))
        if rx:
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self):
        """Puts the nRF24L01 into RX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this function flushes the RX FIFO, clears the `irq_DR` status flag, and puts nRf24L01 in powers up mode.

        """
        # ensure radio is in power down or standby-I mode
        if self.ce.value:
            self.ce.value = 0

        self._reg_write(RX_PW, self.payload_length)
        if self.pipe0_read_addr is not None:
            # make sure the last call to open_rx_pipe(0) sticks if initialized
            self._reg_write_bytes(RX_ADDR, self.pipe0_read_addr)

        # power up radio & set radio in RX mode
        self._config = self._config & 0xFC | 3
        self._reg_write(CONFIG, self._config)
        time.sleep(0.00015) # mandatory wait time to power up radio
        self.flush_rx() # spec sheet says "used in RX mode"
        self.clear_status_flags(True, False, False) # only Data Ready flag

        # enable radio comms
        self.ce.value = 1 # radio begins listening after CE pulse is > 130 us
        time.sleep(0.00013) # ensure pulse is > 130 us
        # nRF24L01 has just entered active RX + standby-II mode

    def _stop_listening(self):
        """Puts the nRF24L01 into TX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this function puts nRF24L01's power in Standby-I (low current & no transmissions) mode which is ideal for post-transmission work. Remember to flush your 3-level FIFO buffers when appropriate using `flush_tx()` or `flush_rx()`."""
        # ensure radio is in standby-I mode
        if self.ce.value:
            self.ce.value = 0
        # set radio in TX mode as recommended behavior per spec sheet.
        self._config = self._config & 0xFE # does not put radio to sleep
        self._reg_write(CONFIG, self._config)
        time.sleep(0.00016) # mandatedwait for transitioning between modes RX/TX
        # exits while still in Standby-I (low current & no transmissions)

    def _reverse(self, buf):
        """Reverses the byte order of the bytearray passed as ``buf``. This is meant to appease the SPI byte order used on the arduino when writing addresses"""
        rev = b''
        for b in buf:
            rev = bytes([b]) + rev
        return rev

    def open_tx_pipe(self, address):
        """This function is used to open a data pipe for OTA (over the air) TX transactions. If `dynamic_payloads` attribute is `False`, then the `payload_length` attribute is used to specify the length of the payload to be transmitted.

        :param bytearray address: The virtual address of the receiving nRF24L01. This must have a length equal to the `address_length` attribute (see `address_length` attribute). Otherwise a `ValueError` exception is thrown.

        .. note:: There is no option to specify which data pipe to use because the only data pipe that the nRF24L01 uses in TX mode is pipe 0. Additionally, the nRF24L01 uses the same data pipe (pipe 0) for receiving acknowledgement (ACK) packets in TX mode (when the `auto_ack` attribute is enables).

        """
        if len(address) == self.address_length:
            if self.auto_ack:
                self.open_rx_pipe(0, address)
            # let self._open_pipes only reflect RX pipes
            self._reg_write_bytes(0x10, address) # 0x10 = TX_ADDR register
        else:
            raise ValueError("address must be a buffer protocol object with a byte length\nequal to the address_length attribute (currently set to {})".format(self.address_length))

    def close_rx_pipe(self, pipe_number):
        """This function is used to close a specific data pipe for OTA (over the air) RX transactions.

        :param int pipe_number: The data pipe to use for RX transactions. This must be in range [0,5]. Otherwise a `ValueError` exception is thrown.
        """
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        self._open_pipes = self._reg_read(EN_RX) # refresh data
        # reset pipe address accordingly
        if not pipe_number:
            # NOTE this does not clear the shadow copy of address for pipe 0
            # self.pipe0_read_addr = None
            self._reg_write_bytes(pipe_number + RX_ADDR, b'\xe7' * 5)
        elif pipe_number < 2: # write the full address for pipe 1
            self._reg_write_bytes(pipe_number + RX_ADDR, b'\xc2' * 5)
        else: # write just LSB for 2 <= pipes >= 5
            self._reg_write(pipe_number + RX_ADDR, pipe_number + 0xc1)
        # disable the specified data pipe if not already
        if self._open_pipes & (1 << pipe_number):
            self._open_pipes = self._open_pipes & ~(1 << pipe_number)
            self._reg_write(EN_RX, self._open_pipes)

    def open_rx_pipe(self, pipe_number, address):
        """This function is used to open a specific data pipe for OTA (over the air) RX transactions. If `dynamic_payloads` attribute is `False`, then the `payload_length` attribute is used to specify the length of the payload to be expected on the specified data pipe.

        :param int pipe_number: The data pipe to use for RX transactions. This must be in range [0,5]. Otherwise a `ValueError` exception is thrown.
        :param bytearray address: The virtual address of the receiving nRF24L01. This must have a byte length equal to the `address_length` attribute (see `address_length` attribute). Otherwise a `ValueError` exception is thrown. If using a ``pipe_number`` greater than 1, then only the LSByte of the address is written (so make LSByte is unique among other simultaneously broadcasting addresses).

            .. note:: The nRF24L01 shares the MSBytes (address[0:4]) on data pipes 2 through 5.

        """
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        if len(address) != self.address_length:
            raise ValueError("address must be a buffer protocol object with a byte length\nequal to the address_length attribute (currently set to {})".format(self.address_length))
        # write the address
        if pipe_number < 2: # write entire address if pipe_number is 1
            if pipe_number == 0:
                # save shadow copy of address if target pipe_number is 0. This is done to help ensure the proper address is set to pipe 0 via _start_listening() as open_tx_pipe() will modify the address on pipe 0 if auto_ack is enabled during TX mode
                self.pipe0_read_addr = address
            self._reg_write_bytes(RX_ADDR + pipe_number, address)
        else:
            # only write LSByte if pipe_number is not 0 or 1.
            self._reg_write(RX_ADDR + pipe_number, address[0])
        # now manage the pipe
        self._open_pipes = self._reg_read(EN_RX) # refresh data
        # enable the specified data pipe
        self._open_pipes = self._open_pipes | (1 << pipe_number)
        self._reg_write(EN_RX, self._open_pipes)
        if not bool(self._dyn_pl & (1 << pipe_number)):
            # RX radio doesn't care about payload_length if dynamic_payloads is enabled.
            self._reg_write(RX_PW + pipe_number, self.payload_length)

    def fifo(self, tx=False, empty=None):
        """This provides a way to interpret the flags contained in the FIFO_STATUS register. (read-only)

        :param bool tx:

            `True` means information returned is about the TX FIFO.
            `False` means its about the RX FIFO. This parameter defaults to `False` when not specified.

        :param bool empty:

            `True` tests if specified FIFO is empty.
            `False` tests if the specified FIFO is full.
            `None` (when not specified) returns a 2 bit number representing both empty (bit 1) & full (bit 0) flags related to the FIFO specified using the ``tx`` parameter.

        :returns:

            * A `bool` answer to the question:

                "Is the [tx/rx]:[`True`/`False`] FIFO [empty/full]:[`True`/`False`]?

            * if ``empty`` is not specified: an `int` in range [0,2] for which:

                ``1`` means FIFO full
                ``2`` means FIFO empty
                ``0`` means FIFO is neither full nor empty.

        """
        assert (empty is None and isinstance(tx, (bool, int))) or (isinstance(empty, (bool, int)) and isinstance(tx, (bool, int)))
        self._fifo = self._reg_read(FIFO) # refresh the data
        if empty is None:
            return (self._fifo & (0x30 if tx else 0x03)) >> (4 * tx)
        return bool(self._fifo & ((2 - empty) << (4 * tx)))

    def pipe(self, pipe_number=None):
        """This function returns information about the data pipe(s) that have received payloads.

        :param int pipe_number: The specific number identifying a data pipe to check for RX data. This parameter is optional and nRF24L01 expects it to be in range [0,5]. Otherwise a `ValueError` exception is thrown.

        :returns: `None` if there is no payload in RX FIFO.

        If user does not specify pipe_number:

        :returns: The `int` identifying pipe number that received the current payload in the top-level of the RX FIFO buffer.

        If user does specify pipe_number:

        :returns: `True` only if the specified ``pipe_number`` has an RX payload in the FIFO buffer, otherwise `False`.

        """
        if pipe_number is not None and (pipe_number < 0 or pipe_number > 5):
            raise ValueError("pipe number must be in range [0,5]")
        if pipe_number is None:
            self.update() # perform Non-operation command to get status byte (should be faster)
            pipe = (self._status & 0x0E) >> 1 # 0x0E==RX_P_NO
            if pipe <= 5: # is there data in RX FIFO?
                # return pipe number if user did not specify a pipe number to test against
                return pipe
            return None # RX FIFO is empty
        return bool(self.any(pipe_number))

    def any(self, pipe_number=None):
        """This function checks if the nRF24L01 has received any data at all.
        Internally, this function uses `pipe()` then reports the payload length (in bytes) -- if there is any.

        :param int pipe_number: The identifying number of data pipe to be checked for an RX payload. If the specified pipe has payload data, this function returns the length (in bytes) of the RX payload received by that pipe. If this parameter remains unspecified, then this function only checks the RX FIFO buffer for the next available payload (if any).

        :returns:

            - `int` of the size (in bytes) of an available RX payload (if any).
            - ``0`` if there is no payload in the RX FIFO buffer.

        """
        if pipe_number is not None and (pipe_number < 0 or pipe_number > 5):
            raise ValueError("pipe number must be in range [0,5]")
        if pipe_number is None:
            if self.pipe() is not None:
                # 0x60 == R_RX_PL_WID command
                return self._reg_read(0x60) # top-level payload length
            return 0 # RX FIFO empty
        # return payload length from the specified pipe_number
        return self._reg_read(RX_PW + pipe_number)

    def recv(self):
        """This function is used to retrieve, then clears all the status flags. This function also serves as a helper function to `read_ack()` in TX mode to aquire any automatic acknowledgement (ACK) payload.  (read-only)

        :returns: A `bytearray` of the RX payload data

            - If the `dynamic_payloads` attribute is disabled, then the returned bytearray's length is equal to the user defined `payload_length` attribute (which defaults to 32).
            - If the `dynamic_payloads` attribute is enabled, then the returned bytearray's length is equal to the payload size in the RX FIFO buffer.

        .. note:: The `dynamic_payloads` attribute must be enabled in order to use ACK payloads.

        """
        # buffer size = current payload size (0x60 = R_RX_PL_WID) + status byte
        curr_pl_size = self.payload_length if not self.dynamic_payloads else self._reg_read(0x60)
        result = self._reg_read_bytes(0x61, curr_pl_size) # get the data (0x61 = R_RX_PAYLOAD)
        # clear all status flag for continued RX/TX operations
        self.clear_status_flags(True,False,False) # only Data Ready IRQ flag
        # return all available bytes from payload
        return result

    def load_ack(self, buf, pipe_number):
        """This allows user to specify a payload to be allocated into the TX FIFO for use with ACK packets on a specified pipe. (write-only)

        :param bytearray buf: This will be the data attached to an automatic acknowledgment packet on the incoming transmission about the specified ``pipe_number`` parameter. This must have a length in range [1,32] bytes, otherwise a `ValueError` exception is thrown. Any ACK payloads will remain in the TX FIFO buffer until transmitted or `flush_tx()`.
        :param int pipe_number: This will be the pipe number to use for deciding which transmissions get a response with the specified ``buf`` parameter's data. This number must be in range [0,5], otherwise a `ValueError` exception is thrown.

        :returns: `True` if payload was successfully loaded onto the TX FIFO buffer. `False` if it wasn't because TX FIFO buffer is full.

        ..note this function takes advantage of a special feature on the nRF24L01 and needs to be called for every time a customized ACK payload is to be used (not for every automatic ACK packet -- this just appends a payload to the `auto_ack` attribute). These special custom ACK payloads can be disabled by setting the `ack` attribute to `False`. The `ack` & `auto_ack` (with `dynamic_payloads` as well) attributes are also automatically enabled by this function when necessary.

        .. tip:: To retrieving the ACK payload data, you must specify the `read_ack` parameter as `True` when calling `send()` or, in case of asychronous application, directly call `read_ack()` function after calling `write()` and before calling `clear_status_flags()`. See `read_ack()` for more details. Otherwise, this attribute will always be its initial value of `None`.

        .. tip:: As the ACK payload must be set prior to receiving a transmission. Set the ACK payload data using this function while `listen` attribute is set `True` to ensure the nRF24L01 is in RX mode. It is also worth noting that the nRF24L01 can hold up to 3 ACK payloads pending transmission. Using this function does not over-write existing ACK payloads pending; it only adds to the queue (TX FIFO buffer) if it can.

        """
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of\nat least 1 and no greater than 32")
        # only prepare payload if the auto_ack attribute is enabled and ack[0] is not None
        if not self.ack:
            self.ack = True
        if not self.tx_full:
            # 0xA8 = W_ACK_PAYLOAD
            self._reg_write_bytes(0xA8 | pipe_number, buf)
            return True # payload was loaded
        return False # payload wasn't loaded

    def read_ack(self):
        """Allows user to read the automatic acknowledgement (ACK) payload (if any) when nRF24L01 is in TX mode. This function is called from a blocking `send()` call if the ``read_ack`` parameter in `send()` is passed as `True`.
        Alternatively, this function can be called directly in case of using the non-blocking `write()` function call during asychronous applications.

        .. warning:: In the case of asychronous applications, this function will do nothing if the status flags are cleared after calling `write()` and before calling this function. Also, the `dynamic_payloads` and `auto_ack` attributes must be enabled to use ACK payloads. It is worth noting that enabling the `dynamic_payloads` attribute automatically enables the `auto_ack` attribute.

        """
        if self.any(): # check RX payload for ACK packet
            # directly save ACK payload to the ack internal attribute.
            # `self.ack = x` does not not save anything internally
            return self.recv()
        return None

    def send(self, buf, ask_no_ack=False):
        """This blocking function is used to transmit payload(s) until one of the following results is acheived:

        :returns:

            * `None` if transmission times out meaning nRF24L01 has malfunctioned.
            * `False` if transmission fails.
            * `True` if transmission succeeds.
            * `bytearray` when the `ack` attribute is `True`, the payload expects a responding custom ACK payload; the response is returned (upon successful transmission) as a `bytearray`. Empty ACK payloads (upon successful transmission) when the `ack` attribute is set `True` are replaced with an error message ``b'NO ACK RETURNED'``.
            * ``nothing`` if a list or tuple of payloads was passed as the ``buf`` parameter.

        :param bytearray,list,tuple buf: The payload to transmit. This bytearray must have a length greater than 0 and less than 32, otherwise a `ValueError` exception is thrown. This can also be a list or tuple of payloads (`bytearray`); in which case, all items in the list/tuple are processed for consecutive transmissions. There is no data/status returned for transmitting multiple payloads as the return status flags are skewed due to the `ard` and `arc` attributes causing more than one response to a transmission.

            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.

            .. warning::  The nRF24L01 will block usage of the TX FIFO buffer upon failed transmissions. Failed transmission's payloads stay in TX FIFO buffer until the MCU calls `flush_tx()` and `clear_status_flags()`. Therefore, this function will discard failed transmissions' payloads when sending a list or tuple of payloads, so it can continue to process through the list/tuple even if any payload fails to be acknowledged.

            .. tip:: It is highly recommended that `auto_ack` attribute is enabled when sending multiple payloads. Test results with the `auto_ack` attribute disabled were very poor (much < 50% received). This same advice applies to the ``ask_no_ack`` parameter (leave it as `False` for multiple payloads).

        :param bool ask_no_ack: Pass this parameter as `True` to tell the nRF24L01 not to wait for an acknowledgment from the receiving nRF24L01. This parameter directly controls a ``NO_ACK`` flag in the transmission's Packet Control Field (9 bits of information about the payload). Therefore, it takes advantage of an nRF24L01 feature specific to individual payloads, and its value is not saved anywhere. You do not need to specify this for every payload if the `auto_ack` attribute is `False`, however this parameter should work despite the `auto_ack` attribute's setting.

            .. note:: Each transmission is in the form of a packet. This packet contains sections of data around and including the payload. `See Chapter 7.3 in the nRF24L01 Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1136318>`_

        """
        self.ce.value = 0 # ensure power down/standby-I for proper manipulation of PWR_UP & PRIM_RX bits in CONFIG register
        self.flush_tx()
        self.clear_status_flags(False) # clears data sent flag only
        if isinstance(buf, (list, tuple)): # writing a set of payloads
            for i, b in enumerate(buf): # check invalid payloads first
                # this way when we raise a ValueError exception we don't leave the nRF24L01 in a frozen state.
                if not b or len(b) > 32:
                    raise ValueError("buf (item {} in the list) must be a buffer protocol object with a byte length of\nat least 1 and no greater than 32".format(i))
            index = 0
            while index < len(buf) or not self.fifo(True,True):
                if self.irq_DF: # needed for continued transmission
                    self.flush_tx() # discard failed payloads in the name of progress
                    self.clear_status_flags(False) # clears data sent flag only
                # using spec sheet calculations:
                # timeout total = T_upload + 2 * stby2active + T_overAir + T_ack + T_irq
                # T_upload is done before timeout begins (after payload write action AKA upload)
                # let 2 * stby2active ~= 2 * 130 = 260 microseconds
                # let T_ack = T_overAir as the payload size is the only distictive variable between the 2
                # T_overAir = ( 8 (bits/byte) * (1 byte preamble + address length + payload length + crc length) + 9 bit packet ID ) / RF data rate (in bits/sec) = OTA transmission time in seconds
                # spec sheet says T_irq is (0.0000082 if self.data_rate == 1 else 0.000006) seconds
                if index < len(buf) and not self.tx_full:
                    timeout = (1 + (bool(self.auto_ack) and not ask_no_ack)) * (((8 * (1 + self.address_length + len(buf[index]) + self.crc )) + 9) / (self.data_rate * 1000000 if self.data_rate < 250 else 1000)) + 0.00026 + (0.0000082 if self.data_rate == 1 else 0.000006) + (self.ard * self.arc / 1000000) + (0.00001 if index == 0 else 0)
                    self.write(buf[index], ask_no_ack)
                    # print('loading payload', index + 1, 'waiting', timeout, 'seconds')
                    time.sleep(timeout) # wait for the ESB protocol to finish (or at least attempt)
                    index += 1
                # print(round(index/len(buf)*100,2), '% processed from the queue.')
            self.ce.value = 0
        else: # writing a single payload
            if not buf or len(buf) > 32:
                raise ValueError("buf must be a buffer protocol object with a byte length of\nat least 1 and no greater than 32")
            self.write(buf, ask_no_ack) # init using non-blocking helper
            time.sleep(0.00001) # ensure CE pulse is >= 10 us
            start = time.monotonic()
            # if pulse is stopped here, the nRF24L01 only handles the top level payload in the FIFO.
            # hold CE HIGH to continue processing through the rest of the TX FIFO bound for the address passed to open_tx_pipe()
            self.ce.value = 0 # go to Standby-I power mode (power attribute still == True)
            result = None
            timeout = (1 + (bool(self.auto_ack) and not ask_no_ack)) * (((8 * (1 + self.address_length + len(buf) + self.crc )) + 9) / (self.data_rate * 1000000 if self.data_rate < 250 else 1000)) + 0.00026 + (0.0000082 if self.data_rate == 1 else 0.000006) + (self.ard * self.arc / 1000000)
            while (not self.irq_DS or not self.irq_DF) and (time.monotonic() - start) < timeout:
                self.update() # perform Non-operation command to get status byte (should be faster)
                # print('status: DR={} DS={} DF={}'.format(self.irq_DR, self.irq_DS, self.irq_DF))
            if self.irq_DS or self.irq_DF: # transmission done
                # get status flags to detect error
                result = bool(self.irq_DS)
            # read ack payload clear status flags, then power down
            if self.ack and self.irq_DS and not ask_no_ack:
                # get and save ACK payload to self.ack if user wants it
                result = self.read_ack() # save reply in input buffer
                if result is None: # can't return empty handed
                    result = b'NO ACK RETURNED'
            self.clear_status_flags(False) # only TX related IRQ flags
            return result

    def resend(self):
        """Use this function to maunally re-send the current payload in the TX FIFO buffer (if any) that previously failed to transmit.

        .. note:: The nRF24L01 removes a payload from the TX FIFO buffer after successful transmission. Otherwise the failed transmission's payload will remain in the TX FIFO buffer until `flush_tx()` is called to clear anitquated payloads (those that failed to transmit or were intentionally kept in the TX FIFO buffer using this function).

        """
        if not self.fifo(True,True):  # update _fifo attribute
            result = None
            if self._features & 1 == 0: # ensure this optional command is enabled
                self._features = self._features & 0xFE | 1 # set EN_DYN_ACK flag high
                self._reg_write(FEATURE, self._features)
            # payload will get re-used. This command tells the radio not pop TX payload from FIFO on success
            self._reg_write(0xE3) # 0xE3 == REUSE_TX_PL command
            self.ce.value = 0 # this cycles the CE pin to re-enable transmission of re-used payload
            self.ce.value = 1
            time.sleep(0.00001) # mandated 10 microsecond pulse
            # now get result
            self.ce.value = 0 # only send one payload
            start = time.monotonic()
            # timeout calc assumes 32 byte payload (no way to tell when payload has already been loaded)
            timeout = (1 + bool(self.auto_ack)) * (((8 * (1 + self.address_length + 32 + self.crc )) + 9) / (self.data_rate * 1000000 if self.data_rate < 250 else 1000)) + 0.00026 + (0.0000082 if self.data_rate == 1 else 0.000006) + (self.ard * self.arc / 1000000)
            while (not self.irq_DS or not self.irq_DF) and (time.monotonic() - start) < timeout:
                self.update() # perform Non-operation command to get status byte (should be faster)
                # print('status: DR={} DS={} DF={}'.format(self.irq_DR, self.irq_DS, self.irq_DF))
            if self.irq_DS or self.irq_DF: # transmission done
                # get status flags to detect error
                result = bool(self.irq_DS)
            # read ack payload clear status flags, then power down
            if self.ack and self.irq_DS :
                # get and save ACK payload to self.ack if user wants it
                result = self.read_ack() # save reply in input buffer
                if result is None: # can't return empty handed
                    result = b'NO ACK RETURNED'
            self.clear_status_flags(False) # only TX related IRQ flags
            return result

    def write(self, buf=None, ask_no_ack=False):
        """This non-blocking function (when used as alternative to `send()`) is meant for asynchronous applications and can only handle one payload at a time -- no list or tuple of payloads is accepted. (write-only)

        :param bytearray buf: The payload to transmit. This bytearray must have a length greater than 0 and less than 32 bytes, otherwise a `ValueError` exception is thrown.

            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.

        :param bool ask_no_ack: Pass this parameter as `True` to tell the nRF24L01 not to wait for an acknowledgment from the receiving nRF24L01. This parameter directly controls a ``NO_ACK`` flag in the transmission's Packet Control Field (9 bits of information about the payload). Therefore, it takes advantage of an nRF24L01 feature specific to individual payloads, and its value is not saved anywhere. You do not need to specify this for every payload if the `auto_ack` attribute is `False`, however this parameter should work despite the `auto_ack` attribute's setting.

            .. note:: Each transmission is in the form of a packet. This packet contains sections of data around and including the payload. `See Chapter 7.3 in the nRF24L01 Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1136318>`_

        This function isn't completely non-blocking as we still need to wait just under 5 milliseconds for the CSN pin to settle (allowing for a clean SPI transaction).

        .. note:: The nRF24L01 doesn't initiate sending until a mandatory minimum 10 microsecond pulse on the CE pin is acheived. That pulse is initiated before this function exits. However, we have left that 10 microsecond wait time to be managed by the user in cases of asychronous application, or it is managed by using `send()` instead of this function.

        .. warning:: A note paraphrased from the `nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_:

            It is important to NEVER to keep the nRF24L01+ in TX mode for more than 4 milliseconds at a time. If the [`auto_ack` and `dynamic_payloads`] features are enabled, nRF24L01+ is never in TX mode longer than 4 milliseconds.

        .. tip:: Use this function at your own risk. Because of the underlying `"Enhanced ShockBurst Protocol" <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132607>`_, disobeying the 4 milliseconds rule is often avoided if you enable the `dynamic_payloads` and `auto_ack` attributes. Alternatively, you MUST additionally use either interrupt flags/IRQ pin with user defined timer(s) to AVOID breaking the 4 millisecond rule. If the `nRF24L01+ Specifications Sheet explicitly states this <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_, we have to assume radio damage or misbehavior as a result of disobeying the 4 milliseconds rule.

        """
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of\nat least 1 and no greater than 32")
        self.clear_status_flags(False) # only TX related IRQ flags

        if not self.power or (self._config & 1): # ready radio if it isn't yet
            self._config = (self._reg_read(CONFIG) & 0x7c) | 2 # also ensures tx mode
            self._reg_write(0, self._config)
            # power up/down takes < 150 us + 4 us
            time.sleep(0.0002)

        # pad out or truncate data to fill payload_length if dynamic_payloads == False
        if not self.dynamic_payloads:
            if len(buf) < self.payload_length:
                for _ in range(self.payload_length - len(buf)):
                    buf += b'\x00'
            elif len(buf) > self.payload_length:
                buf = buf[:self.payload_length]

        # now upload the payload accordingly
        if ask_no_ack:
            # payload doesn't want acknowledgment
            # 0xB0 = W_TX_PAYLOAD_NO_ACK; this command works with auto_ack on or off
            self._reg_write_bytes(0xB0, buf) # write appropriate command with payload
            # print("payload doesn't want acknowledgment")
        else:# payload may require acknowledgment
            # 0xA0 = W_TX_PAYLOAD; this command works with auto_ack on or off
            self._reg_write_bytes(0xA0, buf) # write appropriate command with payload
            # print("payload does want acknowledgment")
        # enable radio comms so it can send the data by starting the mandatory minimum 10 us pulse on CE. Let send() measure this pulse for blocking reasons
        self.ce.value = 1 # re-used payloads start with this as well
        # radio will automatically go to standby-II after transmission while CE is still HIGH only if dynamic_payloads and auto_ack are enabled
