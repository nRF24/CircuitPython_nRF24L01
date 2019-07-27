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
=========================================================================================

CircuitPython port of the nRF24L01 library from Micropython.
Original work by Damien P. George & Peter Hinch can be found `here <https://github.com/micropython/micropython/tree/master/drivers/nrf24l01>`_

The Micropython source has been rewritten to work on the Raspberry Pi and other Circuitpython compatible devices using Adafruit's `busio`, `bus_device.spi_device`, and `digitalio`, modules.
Modified by Brendan Doherty, Rhys Thomas

* Author(s): Damien P. George, Peter Hinch, Rhys Thomas, Brendan Doherty
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import time
from adafruit_bus_device.spi_device import SPIDevice

# nRF24L01+ registers
CONFIG       = 0x00
EN_AA        = 0x01
EN_RXADDR    = 0x02
SETUP_AW     = 0x03
SETUP_RETR   = 0x04
RF_CH        = 0x05
RF_SETUP     = 0x06
STATUS       = 0x07
OBSERVE_TX   = 0x08
RPD          = 0x09
RX_ADDR_P0   = 0x0a
TX_ADDR      = 0x10
RX_PW_P0     = 0x11
FIFO_STATUS  = 0x17
DYNPD	     = 0x1c
FEATURE      = 0x1d

# FEATURE register
EN_DPL       = 0x04
EN_ACK_PAY   = 0x02
EN_DYN_ACK   = 0x01

# CONFIG register
MASK_RX_DR   = 0x40 # disable interupt on data ready
MASK_TX_DS   = 0x20 # disable interrupt on data sent
MASK_MAX_RT  = 0x10 # disable interrupt on max re-transmits
EN_CRC       = 0x08 # enable CRC
CRCO         = 0x04 # CRC encoding scheme; 0=1 byte, 1=2 bytes
PWR_UP       = 0x02 # 1=power up, 0=power down
PRIM_RX      = 0x01 # RX/TX control; 0=PTX, 1=PRX

# RF_SETUP register
POWER_0      = 0x00 # -18 dBm
POWER_1      = 0x02 # -12 dBm
POWER_2      = 0x04 # -6 dBm
POWER_3      = 0x06 # 0 dBm
SPEED_1M     = 0x00
SPEED_2M     = 0x08
SPEED_250K   = 0x20

# STATUS register
RX_DR        = 0x40 # RX data ready; write 1 to clear
TX_DS        = 0x20 # TX data sent; write 1 to clear
MAX_RT       = 0x10 # max retransmits reached; write 1 to clear
RX_P_NO      = 0x0E # pipe number containing RX payload
TX_FULL      = 0x01 # is TX FIFO full

# FIFO_STATUS register
RX_EMPTY     = 0x01 # 1 if RX FIFO is empty

# constants for instructions
R_RX_PL_WID  = 0x60 # read RX payload width
R_RX_PAYLOAD = 0x61 # read RX payload
W_TX_PAYLOAD = 0xa0 # write TX payload
W_ACK_PAYLOAD= 0xa8 # write ACK payload
FLUSH_TX     = 0xe1 # flush TX FIFO
FLUSH_RX     = 0xe2 # flush RX FIFO
NOP          = 0xff # use to read STATUS register

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
    
    """
    def __init__(self, spi, csn, ce, channel=76, payload_length=32, address_length=5, dynamic_payloads=True, auto_ack=True, baudrate=10000000, polarity=0, phase=0, extra_clocks=0):
        # set payload length
        self.payload_length = payload_length
        # last address assigned to pipe0 for reading. init to None
        self.pipe0_read_addr = None
        # init the buffer used to store status data from spi transactions
        self._status = bytearray(1)
        # init ack storage to None
        self._ack = None
        # init the SPI bus and pins
        super(RF24, self).__init__(spi, chip_select=csn, baudrate=baudrate, polarity=polarity, phase=phase, extra_clocks=extra_clocks)

        # set address width and check for device presence by verifying successful spi read transaction
        self.address_length = address_length
        if self._reg_read(SETUP_AW) != self.address_length - 2:
            raise RuntimeError("nRF24L01 Hardware not responding")

        # store the ce pin
        self.ce = ce
        # reset ce.value & disable the chip comms
        self.ce.switch_to_output(value=False)
        # cycle power down mode
        self.power = False # sleep mode despite CE pin state
        # if power is ON and CE is LOW: standby-I mode
        # if power is ON and CE is HIGH: standby-II mode
        self.power = True
        
        # NOTE per spec sheet: nRF24L01+ must be in a standby or power down mode before writing to the configuration registers. I'm assuming this means any register with the word SETUP or CONFIG in it's mnemonic
        # set CRC encoding scheme in bytes
        self.crc = 2
        # set dynamic_payloads and automatic acknowledgment packets on all pipes
        self.auto_ack = auto_ack # this needs to be init before dynamic_payloads
        self.dynamic_payloads = dynamic_payloads 
        # auto retransmit delay: 1500us
        self.ard = 1500
        # auto retransmit count: 3
        self.arc = 3
        # set rf power amplitude to 0 dBm 
        self.pa_level = 0
        # set rf data rate to 1 Mbps
        self.data_rate = 1
        # set channel
        self.channel = channel
        # config interrupt to go LOW when any of the 3 most significant bits in status register are set True. See funcion comments for more detail
        self.interrupt_config()
        # clear status flags
        self.clear_status_flags()
        # flush buffers
        self._flush_rx()
        self._flush_tx()

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

    def _flush_rx(self):
        """A helper function to the nRF24L01's internal flush RX FIFO buffer. THIS IS NOT MEANT TO BE DIRECTLY CALLED BY END-USERS."""
        self._reg_read_bytes(FLUSH_RX)

    def _flush_tx(self):
        """A helper function to the nRF24L01's internal flush TX FIFO buffer. THIS IS NOT MEANT TO BE DIRECTLY CALLED BY END-USERS."""
        self._reg_read_bytes(FLUSH_TX)

    @property
    def status(self):
        """The latest status byte return from SPI transactions. (read-only)
        
        :returns int: 1 byte in which each bit represents a certain status flag.
        
        * bit 7 (MSB) is not used and should always be 0
        * bit 6 represents the RX data ready flag
        * bit 5 represents the TX data sent flag
        * bit 4 represents the max re-transmit flag
        * bit 3 through 1 represents the RX pipe number [0,5] that received the available payload in RX FIFO buffer. `111` means RX FIFO buffer is empty.
        * bit 0 (LSB) represents the TX FIFO buffer full flag
        
        """
        return self._status

    @property
    def ack(self):
        """This attribute contains the payload data that is part of the automatic acknowledgment (ACK) packet. (read-only)

        .. important:: To use this attribute properly, the `auto_ack` attribute must be enabled. Additionally, you must specify the `read_ack` parameter as `True` when calling `send()` or, in case of asychronous application, directly call `read_ack()` function after calling `send_fast()` and before calling `clear_status_flags()`. See `read_ack()` for more details. Otherwise, this attribute will always be its initial value of `None`.
        
        """
        return self._ack

    def what_happened(self):
        """This debuggung function aggregates all status/condition related information from the nRF24L01. Some flags may be irrelevant depending on nRF24L01's state/condition. 
        
        :returns dictionary: A dictionary that contains the data pertaining to the following keys:

        - `Data Ready` Is there RX data ready to be sent?
        - `Data Sent` Has the TX data been sent?
        - `Packets Lost` Amount of packets lost (transmission failures)
        - `Packets Re-transmitted` Maximum amount of attempts to re-transmit
        - `Max Re-transmit` Has the maximum attempts to re-transmit been reached?
        - `Received Power Detector` This is `True` only if OTA (over the air) transmission exceeded -64 dBm (not currently implemented by this driver class).
        - `Re-use TX Payload` Should the nRF24L01 re-use the last TX payload? (not currently implemented by this driver class)
        - `TX FIFO full` Is the TX FIFO buffer full?
        - `TX FIFO empty` Is the TX FIFO buffer empty?
        - `RX FIFO full` Is the RX FIFO buffer full?
        - `RX FIFO empty` Is the RX FIFO buffer empty?
        - `Custom ACK payload` Is the nRF24L01 setup to use an extra (user defined) payload attached to the acknowledgment packet?
        - `Automatic Acknowledgment` Is the automatic acknowledgement feature enabled?
        - `Dynamic Payloads` Is the dynamic payload length feature enabled?
        - `Primary Mode` The current mode (RX or TX) of communication of the nRF24L01 device.
        - `Power Mode` The power state can be Off, Standby-I, Standby-II, or On.
            
        .. note:: All data is fetched directly from nRF24L01 for user comparison to local copy of attributes and user expectations. Meaning, this data reflects only the information that the nRF24L01 is operating with, not the information stored this driver class's attributes.
        
        """
        watchdog = self._reg_read(OBSERVE_TX)
        config = self._reg_read(CONFIG)
        FIFOs = self._reg_read(FIFO_STATUS)
        features = self._reg_read(FEATURE)
        autoACK = bool(self._reg_read(EN_AA) & 0xff)
        dynPL = bool((features & EN_DPL) and (self._reg_read(DYNPD) & 0xff) and autoACK)
        return { 
            "Data Ready": bool(self.status & RX_DR),
            "Data Sent": bool(self.status & TX_DS),
            "Packets Lost": (watchdog & 0xf0) >> 4,
            "Packets Re-transmitted": watchdog & 0x0f,
            "Max Re-transmit": bool(self.status & MAX_RT),
            "Received Power Detector": bool(self._reg_read(RPD)),
            "Re-use TX Payload": bool(FIFOs & 0x40),
            "TX FIFO full": bool(self.status & TX_FULL),
            "TX FIFO empty": bool(FIFOs & 0x10),
            "RX FIFO full": bool(FIFOs & 0x02),
            "RX FIFO empty": bool(FIFOs & 0x01),
            "Custom ACK payload": bool(dynPL and (features & EN_ACK_PAY)),
            "Automatic Acknowledgment": autoACK,
            "Dynamic Payloads": dynPL,
            "Primary Mode": "RX" if config & 1 else "TX",
            "Power Mode": ("Standby-II" if self.ce.value else "Standby-I") if config & 2 else "Off"
            }

    def clear_status_flags(self, dataReady=True, dataSent=True, maxRetry=True):
        """This clears the interrupt flags in the status register. This functionality is exposed for asychronous applications only.

        :param bool dataReady: specifies wheather to clear the "RX Data Ready" flag.
        :param bool dataSent: specifies wheather to clear the "TX Data Sent" flag.
        :param bool maxRetry: specifies wheather to clear the "Max Re-transmit reached" flag.
        
        .. note:: Clearing certain flags is necessary for continued operation of the nRF24L01 despite wheather or not the user is taking advantage of the interrupt (IRQ) pin. Directly calling this function without being familiar with the nRF24L01's expected behavior (as outlined in the Specifications Sheet) can cause undesirable behavior. See `Appendix A-B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1047965>`_ for an outline of proper behavior.
        
        """
        self._reg_write(STATUS, (RX_DR & (dataReady << 6)) | (TX_DS & (dataSent << 5)) | (MAX_RT & (maxRetry << 4)))

    @property
    def power(self):
        """This `bool` attribute controls the PWR_UP bit in the CONFIG register.
        
        - `False` basically puts the nRF24L01 to sleep. No transmissions are executed when sleeping.
        - `True` powers up the nRF24L01
        
        .. note:: This attribute needs to be `True` if you want to put radio on standby-I (CE pin is HIGH) or standby-II (CE pin is LOW) modes. In case of either standby modes, transmissions are only executed based on certain criteria (see `Chapter 6.1.2-7 of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132980>`_).
        
        """
        return self._power_mode

    @power.setter
    def power(self, isOn):
        assert isinstance(isOn, int)
        # capture surrounding flags and set PWR_UP flag according to isOn boolean
        self._reg_write(CONFIG, (self._reg_read(CONFIG) & 0x7d) + (PWR_UP & (isOn << 1)))
        self._power_mode = isOn
        if isOn: # power up takes < 5 ms
            time.sleep(0.005)
        
    @property
    def auto_ack(self):
        """This `bool` attribute controls automatic acknowledgment feature on all nRF24L01's data pipes. 
        
        - `True` enables automatic acknowledgment packets.
            Enabling `dynamic_payloads` requires this attribute to be `True` (automatically handled accordingly by `dynamic_payloads`). Enabled `auto_ack` does not require `dynamic_payloads` to be `True`, thus does not automatically enable `dynamic_payloads` (use `dynamic_payloads` attribute to do that). Also the cycle redundancy checking (CRC) is enabled automatically by the nRF24L01 if this automatic acknowledgment feature is enabled (see `dynamic_payloads` and `crc` attribute for more details).
        - `False` disables automatic acknowledgment packets.
            As the `dynamic_payloads` requirement mentioned above, diasabling `auto_ack` also disables `dynamic_payloads` but not `CRC` attributes.
        
        .. note:: There is no plan to implement automatic acknowledgment on a per data pipe basis, therefore all 6 pipes are treated the same. 
        
        """
        return self._aa

    @auto_ack.setter
    def auto_ack(self, enable):
        assert isinstance(enable, int)
        self._reg_write(EN_AA, 0x7f if enable else 0)
        self._aa = enable
        if not enable: # we must disable dynamic_payloads
            self.dynamic_payloads = False
        else: 
            # radio automatically enables CRC if ACK packets are enabled
            if self.crc == 0:
                # if CRC is previously disabled, use default CRC encoding scheme
                self.crc = 2

    @property
    def dynamic_payloads(self):
        """This `bool` attribute controls dynamic payload length feature on all nRF24L01's data pipes. 
        
        - `True` enables nRF24L01's dynamic payload length feature.
            Enabling dynamic payloads REQUIRES enabling the automatic acknowledgment feature on corresponding data pipes AND asserting 'enable dynamic payloads' flag of FEATURE register (both are automatically handled here). 
        - `False` disables nRF24L01's dynamic payload length feature.
            As the `dynamic_payloads` requirement mentioned above, disabling `dynamic_payloads` does not disable `auto_ack` (use `auto_ack` attribute to disable that).
        
        .. note:: There is no plan to implement dynamic payload lengths on a per data pipe basis, therefore all 6 pipes are treated the same. 
        
        """
        return self._dyn_pl

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        assert isinstance(enable, int)
        # enable automatic acknowledgment packets if dynamic payloads is on else leave as is
        if enable and self.auto_ack != enable:
            self.auto_ack = enable
        self._reg_write(DYNPD, 0x7f if enable else 0)
        # capture current surrounding flags' states
        curr = self._reg_read(FEATURE) & 0b11
        # save EN_DPL flag as input variable enable with current state of surrounding flags
        self._reg_write(FEATURE, (EN_DPL & (enable << 2)) | curr)
        # save for access via getter property
        self._dyn_pl = enable

    @property
    def arc(self):
        """"This `int` attribute specifies the nRF24L01's number of attempts to re-transmit TX payload when acknowledgment packet is not received. The nRF24L01 does not attempt to re-transmit if `auto_ack` attribute is disabled. Default is set to 3.

        A valid input value must be in range [0,15]. Otherwise an `AssertionError` exception is thrown.
        
        """
        return self._arc
    
    @arc.setter
    def arc(self, count):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert 0 <= count <= 15
        self._reg_write(SETUP_RETR, (self._reg_read(SETUP_RETR) & 0xf0) | count)
        # save for access via getter property
        self._arc = count

    @property
    def ard(self):
        """This `int` attribute specifies the nRF24L01's delay (in microseconds) between attempts to automatically re-transmit the TX payload when an acknowledgement (ACK) packet is not received. During this time, the nRF24L01 is listening for the ACK packet. If the `auto_ack` attribute is disabled, this attribute is not applied. 
        
        .. note:: Paraphrased from spec sheet:
            Please take care when setting this parameter. If the ACK payload is more than 15 bytes in 2 Mbps data rate, the ARD must be 500µS or more. If the ACK payload is more than 5 bytes in 1 Mbps data rate, the ARD must be 500µS or more. In 250kbps data rate (even when the payload is not in ACK) the ARD must be 500µS or more.
            
            See `data_rate` attribute on how to set the data rate of the nRF24L01's transmissions.
        
        A valid input value must be a multiple of 250 in range [250,4000]. Otherwise an `AssertionError` exception is thrown. Default is 1500.
        
        """
        return self._ard

    @ard.setter
    def ard(self, t):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert 250 <= t <= 4000 and t % 250 == 0
        # set new ARD data and current ARC data to register
        self._reg_write(SETUP_RETR, (int((t-250)/250) << 4) | (self._reg_read(SETUP_RETR) & 15))
        # save for access via getter property
        self._ard = t

    @property
    def address_length(self):
        """This `int` attribute specifies the length (in bytes) of addresses to be used for RX/TX pipes.
        A valid input value must be in range [3,5]. Otherwise an `AssertionError` exception is thrown. Default is 5.

        .. note:: nRF24L01 uses the LSByte for padding addresses with lengths of less than 5 bytes.
        
        """
        return self._addr_width

    @address_length.setter
    def address_length(self, length):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert 3 <= length <= 5
        # address width is saved in 2 bits making range = [3,5]
        self._reg_write(SETUP_AW, length - 2) 
        # save for access via getter property
        self._addr_width = length

    # get payload length attribute
    @property
    def payload_length(self):
        """This `int` attribute specifies the length (in bytes) of payload that is regaurded, meaning 'how big of a payload should the radio care about?' If the `dynamic_payloads` attribute is enabled, this attribute has no affect.
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
        
        - `1` sets the frequency data rate to 1 Mbps
        - `2` sets the frequency data rate to 2 Mbps
        - `250` sets the frequency data rate to 250 Kbps
        
        Any invalid input throws an `AssertionError` exception. Default is 1 Mbps. 
        
        .. warning:: 250 Kbps is be buggy on the non-plus models of the nRF24L01 product line. If you use 250 Kbps data rate, and some transmissions report failed by the transmitting nRF24L01, even though the same packet in question actually reports received by the receiving nRF24L01, try a different different data rate.
        
        """
        if self._speed == SPEED_1M:
            return 1
        elif self._speed == SPEED_2M:
            return 2
        elif self._speed == SPEED_250K:
            return 250

    @data_rate.setter
    def data_rate(self, speed):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert speed in (1, 2, 250)
        if speed == 1: 
            speed = SPEED_1M
        elif speed == 2: 
            speed = SPEED_2M
        elif speed == 250: 
            speed = SPEED_250K
        # write new data rate with surrounding flags
        self._reg_write(RF_SETUP, (self._reg_read(RF_SETUP) & 0xd7) | speed)
        # save for access via getter property
        self._speed = speed

    @property
    def pa_level(self):
        """This `int` aattribute specifies the nRF24L01's power amplitude level (in dBm). 
        
        A valid input value is:

        - `-18` sets the nRF24L01's power amplitude to -18 dBm (lowest)
        - `-12` sets the nRF24L01's power amplitude to -12 dBm
        - `-6` sets the nRF24L01's power amplitude to -6 dBm
        - `0` sets the nRF24L01's power amplitude to 0 dBm (highest)
        
        Any invalid input throws an `AssertionError` exception. Default is 0 dBm.
        
        """
        if self._pa == POWER_0:
            return "-18 dBm"
        elif self._pa == POWER_1:
            return "-12 dBm"
        elif self._pa == POWER_2:
            return "-6 dBm"
        elif self._pa == POWER_3:
            return "0 dBm"
    
    @pa_level.setter
    def pa_level(self, power):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert power in (-18, -12, -6, 0)
        if power == -18: 
            power = POWER_0
        elif power == -12: 
            power = POWER_1
        elif power == -6: 
            power = POWER_2
        elif power == 0: 
            power = POWER_3
        # write new power amplifier level with surrounding flags
        self._reg_write(RF_SETUP, (self._reg_read(RF_SETUP) & 0xfc) | power)
        # save for access via getter property
        self._pa = power

    @property
    def crc(self):
        """This `int` attribute specifies the nRF24L01's cycle redundancy checking (CRC) encoding scheme in terms of bytes. 
        
        A valid input value is in range [0,2]: 
        
        - `0` disables CRC
        - `1` enables CRC encoding scheme using 1 byte
        - `2` enables CRC encoding scheme using 2 bytes
        
        Any invalid input throws an `AssertionError` exception. Default is enabled using 2 bytes.
        
        .. note:: The nRF24L01 automatically enables CRC if automatic acknowledgment feature is enabled (see `auto_ack` attribute).
        
        """
        return self._crc

    @crc.setter
    def crc(self, length):
        assert 0 <= length <= 2
        # capture surrounding flags and set both "enable CRC" & "CRC encoding scheme" flags to 0 (disabled)
        config = self._reg_read(CONFIG) & ~(CRCO | EN_CRC)
        if length == 1: 
            # enable CRC is True & 1 byte CRC encoding scheme means CRC0 = 0 
            config |= EN_CRC
        elif length == 2: 
            # enable CRC is True & 2 byte CRC encoding scheme means CRC0 = 1
            config |= EN_CRC | CRCO
        # save changes to register 
        self._reg_write(CONFIG, config) 
        # save for access via getter property
        self._crc = length
    
    @property
    def channel(self):
        """This `int` attribute specifies the nRF24L01's frequency (MHz).
        
        A valid input value must be in range [0-127]. Otherwise an `AssertionError` exception is thrown. Default is 76 (for compatibility with `TMRh20's arduino library <http://tmrh20.github.io/RF24/classRF24.html>`_ default).
        
        """
        return self._channel

    @channel.setter
    def channel(self, channel):
        assert 0 <= channel <= 127
        self._reg_write(RF_CH, channel)
        # save for access via getter property
        self._channel = channel

    def interrupt_config(self, onMaxARC=True, onDataSent=True, onDataRecv=True):
        """Sets the configuration of the nRF24L01's Interrupt (IRQ) pin. IRQ signal from the nRF24L01 is active LOW. (write-only)

        :param bool onMaxARC: If this is `True`, then interrupt pin goes active LOW when maximum number of attempts to re-transmit the packet have been reached.
        :param bool onDataSent: If this is `True`, then interrupt pin goes active LOW when a payload from TX buffer is successfully transmitted. If `auto_ack` attribute is enabled, then interrupt pin only goes active LOW when acknowledgment (ACK) packet is received.
        :param bool onDataRecv: If this is `True`, then interrupt pin goes active LOW when there is new data to read in the RX FIFO. 
        
        .. note:: Paraphrased from spec sheet:
            
            The procedure for handling `onDataRecv` interrupt should be: 
            
            1. read payload through `_reg_read_bytes()`
            2. clear `dataReady` status flag
            3. read FIFO_STATUS register (address `0x17`) to check if there are more payloads available in RX FIFO buffer (bit 0 of FIFO_STATUS register).
               For example: ``is_RX_empty = nrf._reg_read(0x17) & 1``
            4. if there is more data in RX FIFO, repeat from step 1
        
        """
        # capture surrounding flags and set interupt config flags to 0, then insert boolean args from user. Resulting '&' operation is 1 for disable, 0 for enable
        config = (self._reg_read(CONFIG) & 0x0f) | ((MASK_MAX_RT & ~(onMaxARC << 4)) | (MASK_TX_DS & ~(onDataSent << 5)) | (MASK_RX_DR & ~(onDataRecv << 6)))
        # save to register
        self._reg_write(CONFIG, config)

    # address should be a bytes object with the length = self.address_length
    def open_tx_pipe(self, address):
        """This function is used to open a data pipe for OTA (over the air) TX transactions. If `dynamic_payloads` attribute is `False`, then the `payload_length` attribute is used to specify the length of the payload to be transmitted.
            
        :param bytearray address: The virtual address of the receiving nRF24L01. This must have a length equal to the `address_length` attribute (see `address_length` attribute). Otherwise an `AssertionError` exception is thrown.
        
        .. note:: There is no option to specify which data pipe to use because the only data pipe that the nRF24L01 uses in TX mode is pipe 0. Additionally, the nRF24L01 uses the same data pipe (pipe 0) for receiving acknowledgement (ACK) packets in TX mode.
        
        """
        assert len(address) == self.address_length
        self._reg_write_bytes(RX_ADDR_P0, address)
        self._reg_write_bytes(TX_ADDR, address)
        if not self.dynamic_payloads: # radio doesn't care about payload_length if dynamic_payloads is enabled
            self._reg_write(RX_PW_P0, self.payload_length)

    # address should be a bytes object with the length = self.address_length
    # pipe 0 and 1 have 5 byte address
    # pipes 2-5 use same 4 MSBytes as pipe 1, plus 1 extra byte
    def open_rx_pipe(self, pipe_number, address, ack_payload=None):
        """This function is used to open a specific data pipe for OTA (over the air) RX transactions. If `dynamic_payloads` attribute is `False`, then the `payload_length` attribute is used to specify the length of the payload to be transmitted on the specified data pipe.

        :param int pipe_number: The data pipe to use for RX transactions. This must be in range [1,5]. Otherwise an `AssertionError` exception is thrown.
        :param bytearray address: The virtual address of the transmitting nRF24L01. This must have a length equal to the `address_length` attribute (see `address_length` attribute). Otherwise an `AssertionError` exception is thrown. If using a `pipe_number` greater than 2, then only the LSByte of the address is written (so make LSByte unique among other simultaneously broadcasting addresses).
            
            .. note:: The nRF24L01 shares the MSBytes (address[0:4]) on data pipes 2 through 5.
        :param bytearray ack_payload: A payload buffer to be included as part of the automatic acknowledgment (ACK) packet. This optional and must be 1 to 32 bytes long. Otherwise an `AssertionError` exception is thrown. 
            
            .. note:: Specifying this parameter has no affect (and isn't saved anywhere) if the `auto_ack` attribute is `False`.
        
        """
        assert len(address) == self.address_length
        assert 0 <= pipe_number <= 5
        assert ack_payload is None or 1 <= len(ack_payload) <= 32
        # open_tx_pipe() overrides pipe 0 address. Thus start_listening() will re-enforce this address using self.pipe0_read_addr attribute
        if pipe_number == 0: 
            # save shadow copy of address if target pipe_number is 0
            self.pipe0_read_addr = address
        elif pipe_number < 2: # write entire address if pip_id is 1
            self._reg_write_bytes(RX_ADDR_P0 + pipe_number, address)
        else: # only write LSB if pipe_number is not 0 or 1
            self._reg_write(RX_ADDR_P0 + pipe_number, address[len(address) - 1])
        if not self.dynamic_payloads: # radio doesn't care about payload_length if dynamic_payloads is enabled
            self._reg_write(RX_PW_P0 + pipe_number, self.payload_length)
        self._reg_write(EN_RXADDR, self._reg_read(EN_RXADDR) | (1 << pipe_number))
        if ack_payload is not None and self.auto_ack:
            self._reg_write_bytes(W_ACK_PAYLOAD | pipe_number, ack_payload)

    def start_listening(self):
        """Puts the nRF24L01 into RX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this function flushes the RX and TX FIFOs, clears the status flags, and puts nRf24L01 in powers up mode."""
        # ensure radio is in power down or standby-I mode
        self.ce.value = 0
        # power up radio & set radio in RX mode
        self._reg_write(CONFIG, (self._reg_read(CONFIG) & 0xfc) | PWR_UP | PRIM_RX)
        # manipulating local copy of power attribute saves an extra spi transaction because we already needed to access the same register to manipulate RX/TX mode
        self._power_mode = True
        time.sleep(0.005) # mandatory wait time to power on radio
        self.clear_status_flags()
        if not self.dynamic_payloads:
            self._reg_write(RX_PW_P0, self.payload_length)
        if self.pipe0_read_addr is not None:
            self._reg_write_bytes(RX_ADDR_P0, self.pipe0_read_addr)
        self._flush_rx()
        self._flush_tx()
        # enable radio comms
        self.ce.value = 1 # radio begins listening after CE pulse is > 130 us 
        time.sleep(0.00013) # ensure pulse is > 130 us

    def stop_listening(self):
        """Puts the nRF24L01 into TX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this function flushes the RX and TX FIFOs, clears the status flags, and puts nRF24L01 in powers down (sleep) mode."""
        # disable comms
        self.ce.value = 0
        self._flush_tx()
        self._flush_rx()
        self.clear_status_flags()
        # power down radio. Also set radio in TX mode as recommended behavior per spec sheet.
        self._reg_write(CONFIG, self._reg_read(CONFIG) & 0xfc)
        # manipulating local copy of power attribute saves an extra spi transaction because we already needed to access the same register to manipulate RX/TX mode
        self._power_mode = False 

    def available(self, pipe_number=None):
        """This function checks if the nRF24L01 has received data in relation to the data pipe that received it.
        
        :param int pipe_number: The specific number identifying a data pipe to check for RX data. This parameter is optional and must be in range [0,5]. Otherwise an `AssertionError` exception is thrown.
        
        :returns: `None` if there is no payload in RX FIFO.
        
        If user does not specify pipe_number:

        :returns: The `int` identifying pipe number that contains the RX payload. 
        
        If user does specify pipe_number:
        
        :returns: `True` only if `pipe_number` is equal to the identifying number of the data pipe that received the current (top level) RX payload in the FIFO buffer, otherwise `False`. 
        
        """
        assert pipe_number is None or 0 <= pipe_number <= 5 # check bounds on user input
        pipe = (self._reg_read(STATUS) & RX_P_NO) >> 1
        if pipe > 5:
            return None # RX FIFO is empty
        elif pipe_number is None:
            # return pipe number if user did not specify a pipe number to test against
            return pipe
        elif pipe_number != pipe:
            # return comparison of pipe number and user specified pipe number
            return False
        else: # return True if pipe number matches user input & there is data in RX FIFO 
            return True

    def any(self):
        """This function checks if the nRF24L01 has received any data at all.
        
        :returns: 
            `int` of the size (in bytes) of an available RX payload (if any). 
            `True` when the RX FIFO buffer is not empty and `dynamic_payloads` attribute is enabled. 
            `False` if there is no payload in the RX FIFO buffer.

        """
        if not bool(self._reg_read(FIFO_STATUS) & RX_EMPTY):
            return self._reg_read(R_RX_PL_WID) if not self.dynamic_payloads else True
        return False

    def recv(self):
        """This function is used to retrieve, then clears all the status flags. This function also serves as a helper function to `read_ack()` in TX mode to aquire the automatic acknowledgement (ACK) payload (if any).
        
        :returns: A `bytearray` of the RX payload data
            
            - If the `dynamic_payloads` attribute is disabled, then the returned bytearray's length is equal to the user defined `payload_length` attribute (which defaults to 32). 
            - If the `dynamic_payloads` attribute is enabled, then the returned bytearray's length is equal to the payload size in the RX FIFO buffer.
        
        .. note:: The `dynamic_payloads` attribute must be enabled in order to use ACK payloads.
        
        """
        # buffer size = current payload size + status byte
        curr_pl_size = self.payload_length if not self.dynamic_payloads else self._reg_read(R_RX_PL_WID)
        # get the data
        result = self._reg_read_bytes(R_RX_PAYLOAD, curr_pl_size)
        # clear status flags
        self.clear_status_flags()
        # return all available bytes from payload
        return result

    def read_ack(self):
        """Allows user to read the automatic acknowledgement (ACK) payload (if any). This function is called from a blocking `send()` call if the `read_ack` parameter in `send()` is passed as `True`. 
        Alternatively, this function can be called directly in case of using the less-blocking `send_fast()` function call during asychronous applications.
            
        .. warning:: In the case of asychronous applications, this function will do nothing if the status flags are cleared after calling `send_fast()` and before calling this function. Also, the `dynamic_payloads` attribute should be enabled in order to use ACK payloads.
        
        """
        if self.any(): # check RX payload for ACK packet
            self._ack = self.recv()

    def send(self, buf, read_ack=False, timeout=0.2):
        """This blocking function is used to transmit payload until one of the following results is acheived: 
        
        :returns: 
            `0` if transmission times out meaning nRF24L01 has malfunctioned.
            `1` if transmission succeeds.
            `2` if transmission fails.
        
        :param bytearray buf: The payload to transmit. This bytearray must have a length greater than 0 to execute transmission.
            
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.
        :param bool read_ack: A flag to specify wheather or not to save the automatic acknowledgement (ACK) payload to the `ack` attribute.
        :param float timeout: This an arbitrary number of seconds that is used to keep the application from indefinitely hanging in case of radio malfunction. Default is 200 milliseconds. This parameter may get depricated in the future. It is strongly advised to not alter this parameter AT ALL!
        
        """
        result = 0
        self.send_fast(buf)
        time.sleep(0.00001) # ensure CE pulse is >= 10 us
        start = time.monotonic()
        self.ce.value = 0
        while result == 0 and (time.monotonic() - start) < timeout:
            # let result be 0 if timeout, 1 if success, or 2 if fail
            if self._reg_read(STATUS) & (TX_DS | MAX_RT): # transmission done
                # get status flags to detect error
                result = 1 if (self._reg_read(STATUS) & TX_DS) else 2
        # read ack payload (if read_ack == True), clear status flags, then power down
        if read_ack: 
            # get and save ACK payload to self.ack if user wants it
            self.read_ack()
        else: # flags were not cleared by read_ack(),
            self.clear_status_flags()
        self.power = False
        return result
            
    def send_fast(self, buf):
        """This non-blocking function (when used as alternative to `send()`) is meant for asynchronous applications. 
        
        :param bytearray buf: The payload to transmit. This bytearray must have a length greater than 0 to execute transmission.
            
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.
        
        This function isn't completely non-blocking as we still need to wait just under 5 milliseconds for the CSN pin to settle (allowing for a clean SPI transaction). 
        
        .. note:: The nRF24L01 doesn't initiate sending until a mandatory minimum 10 microsecond pulse on the CE pin (which is initiated before this function exits) is acheived. However, we have left that 10 microsecond wait time to be managed by the user in cases of asychronous application, or it is managed by using `send()` instead of this function.
        
        .. warning:: A note paraphrased from the `nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_:
            It is important never to keep the nRF24L01+ in TX mode for more than 4 milliseconds at a time. If the [`auto_ack` and `dynamic_payloads`] features are enabled, nRF24L01+ is never in TX mode longer than 4 milliseconds.
        
        .. tip:: Use this function at your own risk. If you do, you MUST additionally use either interrupt flags/IRQ pin with user defined timer(s) OR enable the `dynamic_payloads` attribute (the `auto_ack` attribute is enabled with `dynamic_payloads` automatically) to obey the 4 milliseconds rule. If the nRF24L01+ Specifications Sheet explicitly states this, we have to assume radio damage or misbehavior as a result of disobeying the 4 milliseconds rule. Cleverly, `TMRh20's arduino library <http://tmrh20.github.io/RF24/classRF24.html>`_ recommends using auto re-transmit delay (the `ard` attribute) to avoid breaking this rule, but we have not verified this strategy as it requires the `auto_ack` attribute to be enabled anyway.
        
        """
        # pad out or truncate data to fill payload_length if dynamic_payloads == False
        if not self.dynamic_payloads:
            if len(buf) < self.payload_length:
                for _ in range(self.payload_length - len(buf)): 
                    buf += b'\x00'
            elif len(buf) > self.payload_length:
                buf = buf[:self.payload_length]
        # set the data to send in TX FIFO
        self._reg_write_bytes(W_TX_PAYLOAD, buf)
        # power up radio
        self.power = True
        # enable radio comms so it can send the data by starting the mandatory minimum 10 us pulse on CE. Let send() measure this pulse for blocking reasons
        self.ce.value = 1
        # radio will automatically go to standby-II after transmission while CE is still HIGH only if dynamic_payloads and auto_ack are enabled
