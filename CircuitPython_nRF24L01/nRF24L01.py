# The MIT License (MIT)
#
# Copyright (c) 2017 Damien P. George
# Copyright (c) 2019 Rhys Thomas
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
`adafruit_circuitpython_nrf24l01` - nRF24L01 radio transceiver
===================================

CircuitPython port of the nRF24L01 library from Micropython.
Original work by Damien P. George & Peter Hinch can be found at https://github.com/micropython/micropython/tree/master/drivers/nrf24l01
Ported to work on the Raspberry Pi and other Circuitpython compatible devices using Adafruit's `busio`, `bus_device.spi_device`, and `digitalio`, modules.
Modified by Rhys Thomas, Brendan Doherty.

* Author(s): Damien P. George, Peter Hinch, Rhys Thomas, Brendan Doherty
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/Adafruit_CircuitPython_NRF24L01.git"
import busio, time, struct
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

class NRF24L01(SPIDevice):
    def __init__(self, spi, csn, ce, channel=76, payload_length=32, address_length=5, dynamic_payloads=True, auto_ack=True, baudrate=10000000, polarity=0, phase=0, extra_clocks=0):
        # set payload length
        self.payload_length = payload_length
        # last address assigned to pipe0 for reading. init to None
        self.pipe0_read_addr = None
        # init the buffer used to store status data from spi transactions
        self._status = bytearray(1)
        # init ack storage to None
        self.ack = None
        # init the SPI bus and pins
        super(NRF24L01, self).__init__(spi, chip_select=csn, baudrate=baudrate, polarity=polarity, phase=phase, extra_clocks=extra_clocks)

        # set address width and check for device presence by verifying successful spi read transaction
        self.address_length = address_length
        if self._reg_read(SETUP_AW) != self.address_length - 2:
            raise OSError("nRF24L01+ Hardware not responding")

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
        """
        for retrieving one byte of data from the specified register (reg). Useful for getting status byte.\n
        reg must be an int.
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
        """
        mainly for realtime debug of checking register contents of more than 1 byte. To read the full payload in a FIFO, pass buf_len as 32. NOTE: reading buf_len bytes from FIFO would also remove buf_len bytes from the FIFO.\n
        reg must be an int.\n
        buf_len specifies how many bytes to read. Default of 5 is meant to be used for checking pipe addresses. 
        """
        # allow an extra byte for status data
        buf = bytearray(buf_len + 1)
        with self:
            time.sleep(0.005) # time for CSN to settle
            self.spi.readinto(buf, write_value=reg)
        self._status = buf[0] # save status byte
        return buf[1:] # drop status byte and return the rest

    def _reg_write_bytes(self, reg, outBuf):
        """
        for writing more than 1 byte to a multi-byte register. Use this to set payload or address data.\n
        reg must be an int.\n
        outBuf must be of a buffer protocol object type (bytearray is most commonly used/expected).
        """
        outBuf = bytes([0x20 | reg]) + outBuf
        inBuf = bytearray(len(outBuf))
        with self:
            time.sleep(0.005) # time for CSN to settle
            self.spi.write_readinto(outBuf, inBuf)
        self._status = inBuf[0] # save status byte

    def _reg_write(self, reg, value):
        """
        for writing one byte of data (typical size of a single register).\n
        reg must be an int.\n
        value must be an int.
        """
        outBuf = bytes([0x20 | reg, value])
        inBuf = bytearray(len(outBuf))
        with self:
            time.sleep(0.005) # time for CSN to settle
            self.spi.write_readinto(outBuf, inBuf)
        self._status = inBuf[0] # save status byte

    def _flush_rx(self):
        """
        flush RX FIFO
        """
        self._reg_read_bytes(FLUSH_RX)

    def _flush_tx(self):
        """
        flush RX FIFO
        """
        self._reg_read_bytes(FLUSH_TX)

    @property
    def status(self):
        """
        a read-only attribute to return the latest status byte from SPI transactions.
        """
        return self._status

    def what_happened(self):
        """
        This debuggung function aggregates all status related info from the nRF24L01. It returns a dictionary in which each item represents a status related flag. Some flags may be irrelevant depending on nRF24L01's state/condition. NOTE: All data is fetched directly from nRF24L01 for comparison to local copy of attributes and user expectations.
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
        """
        This clears the interrupt flags in the status register. Clearing certain flags is necessary for continued operation of radio.\n
        dataReady (bool) specifies wheather to clear the RX_DR flag.\n
        dataSent (bool) specifies wheather to clear the TX_DS flag.\n
        maxRetry (bool) specifies wheather to clear the MAX_RT flag.
        """
        self._reg_write(STATUS, (RX_DR & (dataReady << 6)) | (TX_DS & (dataSent << 5)) | (MAX_RT & (maxRetry << 4)))

    @property
    def power(self):
        """
        This attribute controls the PWR_UP bit in the CONFIG register. Setting this to False basically puts the radio to sleep. No transmissions are executed when sleeping. NOTE: This attribute needs to be True if you want to put radio on standby-I (CE pin is HIGH) or standby-II (CE pin is LOW) modes. In case of either standby modes, transmissions are only executed based on certain criteria (see chapter 6.1.6-Operational modes configuration in the nRF24L01+ specs sheet.\n
        Input value must be a bool.
        """
        return self._power_mode

    @power.setter
    def power(self, isOn):
        # capture surrounding flags and set PWR_UP flag according to isOn boolean
        assert type(isOn) is bool
        self._reg_write(CONFIG, (self._reg_read(CONFIG) & 0x7d) + (PWR_UP & (isOn << 1)))
        self._power_mode = isOn
        if isOn: # power up takes < 5 ms
            time.sleep(0.005)
        

    # get boolean pertaining to auto acknowledgment
    @property
    def auto_ack(self):
        """
        Boolean to control enabled automatic acknowledgment packets on all pipes. There is no plan to implement automatic acknowledgment on a per pipe basis, therefore all 6 pipes are treated the same. Enabling dynamic_payloads requires this attribute to be True (automatically handled accordingly). Enabled auto_ack does not require dynamic_payloads to be True (use dynamic_payloads attribute to do that).\n
        Input value must be a bool.
        """
        return self._aa

    # set boolean pertaining to auto acknowledgment
    @auto_ack.setter
    def auto_ack(self, enable):
        assert type(enable) is bool
        self._reg_write(EN_AA, 0x7f if enable else 0)
        self._aa = enable
        if not enable:
            self.dynamic_payloads = False

    # get boolean pertaining to enabled dynamic payloads
    @property
    def dynamic_payloads(self):
        """Boolean to control enabled dynamic payloads. Enabling dynamic payloads REQUIRES enabling Auto Acknowledgment on corresponding pipes AND asserting 'enable dynamic payloads' flag of FEATURE register. There is no plan to implement dynamic payloads on a per pipe basis, therefore all 6 pipes are treated the same. Setting this to True will also ensable the aforementioned requisites. However, setting this to False does not disable Auto Acknowledgment feature (use auto_ack asttribute to disable that).\n
        Input value must be a bool.
        """
        return self._dyn_pl

    # set boolean pertaining to enabled dynamic payloads
    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        assert type(enable) is bool
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

    # get auto re-transmit count
    @property
    def arc(self):
        """"
        nRF24L01's number of attempts to re-transmit TX payload when ACK packet is not received. Default is 3.\n
        Intput value (int) must be in range [0,15].
        """
        return self._arc
    
    # set auto re-transmit count
    @arc.setter
    def arc(self, count):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert 0 <= count <= 15
        self._reg_write(SETUP_RETR, (self._reg_read(SETUP_RETR) & 0xf0) | count)
        # save for access via getter property
        self._arc = count

    # get auto re-transmit delay
    @property
    def ard(self):
        """
        nRF24L01's delay (in microseconds) between attempts to auto re-transmit TX payload when ACK packet is not received. Default is 1500. NOTE from spec sheet:
            Please take care when setting this parameter. If the ACK payload is more than 15 bytes in 2 Mbps data rate, the ARD must be 500µS or more. If the ACK payload is more than 5 bytes in 1 Mbps data rate, the ARD must be 500µS or more. In 250kbps data rate (even when the payload is not in ACK) the ARD must be 500µS or more.\n
        Intput value (int) must be a multiple of 250 in range [250,4000].
        """
        return self._ard

    # set auto re-transmit delay
    @ard.setter
    def ard(self, t):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert 250 <= t <= 4000 and t % 250 == 0
        # set new ARD data and current ARC data to register
        self._reg_write(SETUP_RETR, (int((t-250)/250) << 4) | (self._reg_read(SETUP_RETR) & 15))
        # save for access via getter property
        self._ard = t

    # get address length attribute
    @property
    def address_length(self):
        """
        Length of address to be used for RX/TX pipes. \n
        Input value (int) must be in range [3,5]. Default is 5. NOTE: nRF24L01 uses the LSByte for padding addresses with lengths of less than 5 bytes.
        """
        return self._addr_width

    # set address length in bytes. can be 3 - 5 bytes long
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
        """Length of payload (in bytes) that is regaurded, meaning 'how big of a payload should the radio care about?'\n
        Input value (int) must be in range [0,32]. Default is 32. 
            Payloads of less than input value will be truncated. 
            Payloads of greater than input value will be padded. 
            Input value of 0 negates radio's transmissions."""
        return self._payload_length

    # set payload size for RX/TX FIFOs
    # NOTE: payloads with size of 0 don't get transmitted/received
    @payload_length.setter
    def payload_length(self, length):
        # max payload size is 32 bytes
        assert 0 <= length <= 32
        # save for access via getter property
        self._payload_length = length

    # get data rate
    @property
    def data_rate(self):
        """
        nRF24L01's frequency data rate.\n 
        Valid input value (int) is 1 (1 Mbps), 2 (2 Mbps), or 250 (250 Kbps). Default is 1 Mbps. NOTE 250 Kbps may be buggy on the non-plus models of the nRF24L01 product line.
        """
        if self._speed == SPEED_1M:
            return "1 Mbps"
        elif self._speed == SPEED_2M:
            return "2 Mbps"
        elif self._speed == SPEED_250K:
            return "250 Kbps"

    # set data rate NOTE 250 Kbps is buggy on nRF24L01 (non plus model), default is 1 Mbps
    @data_rate.setter
    def data_rate(self, speed):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert speed == 1 or speed == 2 or speed == 250
        if speed == 1: speed = SPEED_1M
        elif speed == 2: speed = SPEED_2M
        elif speed == 250: speed = SPEED_250K
        # write new data rate with surrounding flags
        self._reg_write(RF_SETUP, (self._reg_read(RF_SETUP) & 0xd7) | speed)
        # save for access via getter property
        self._speed = speed

    # get power amplitude level
    @property
    def pa_level(self):
        """
        nRF24L01's power amplifier level.\n 
        Valid input value (int) is -18 (-18 dBm), -12 (-12 dBm), -6 (-6 dBm), or 0 (0 dBm). Default is 0 dBm.
        """
        if self._pa == POWER_0:
            return "-18 dBm"
        elif self._pa == POWER_1:
            return "-12 dBm"
        elif self._pa == POWER_2:
            return "-6 dBm"
        elif self._pa == POWER_3:
            return "0 dBm"
    
    # set power amplitude level
    @pa_level.setter
    def pa_level(self, power):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration registers.
        assert power == -18 or power == -12 or power == -6 or power == 0
        if power == -18: power = POWER_0
        elif power == -12: power = POWER_1
        elif power == -6: power = POWER_2
        elif power == 0: power = POWER_3
        # write new power amplifier level with surrounding flags
        self._reg_write(RF_SETUP, (self._reg_read(RF_SETUP) & 0xfc) | power)
        # save for access via getter property
        self._pa = power

    # get CRC length in bytes
    @property
    def crc(self):
        """
        nRF24L01's CRC encoding scheme in terms of bytes. CRC checking is automatically enabled if auto_ack is True.\n
        Input value (int) is in range [0,2]. Default is 2 bytes.
            0 = disables CRC encoding scheme.
            1 = enables CRC encoding scheme using 1 byte.
            2 = enables CRC encoding scheme using 2 bytes.
        """
        return self._crc

    # set CRC length in bytes (must be 0, 1 or 2)
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
    
    # set rf channel
    @property
    def channel(self):
        """
        nRF24L01's radio channel.\n
        Input value (int) must be in range [0-127]. Default is 76.
        """
        return self._channel

    # get rf channel
    @channel.setter
    def channel(self, channel):
        assert 0 <= channel <= 127
        self._reg_write(RF_CH, channel)
        # save for access via getter property
        self._channel = channel

    # this is a one-way implementation, meaning users will have no way to directly retrieve these settings. Radio's interrupt pin uses an acive low signal
    def interrupt_config(self, onMaxARC=True, onDataSent=True, onDataRecv=True):
        """
        onMaxARC (bool): if this is True, then interrupt pin goes active LOW when maximum attempt to re-transmit packet have been reached\n
        onDataSent (bool): if this is True, then interrupt pin goes active LOW when payload from TX buffer is successfully transmitted. If auto_ack is enabled, then interrupt pin only goes active LOW when ACK is received.\n
        onDataRecv (bool): if this is True, then interrupt pin goes active LOW when there is new data to read in the RX FIFO. NOTE from spec sheet:
            The procedure for handling this interrupt should be: 
            1) read payload through SPI
            2) clear RX_DR IRQ
            3) read FIFO_STATUS to check if there are more payloads available in RX FIFO
            4) if there are more data in RX FIFO, repeat from step 1
        """
        # capture surrounding flags and set interupt config flags to 0, then insert boolean args from user. Resulting '&' operation is 1 for disable, 0 for enable
        config = (self._reg_read(CONFIG) & 0x0f) | ((MASK_MAX_RT & ~(onMaxARC << 4)) | (MASK_TX_DS & ~(onDataSent << 5)) | (MASK_RX_DR & ~(onDataRecv << 6)))
        # save to register
        self._reg_write(CONFIG, config)


    # address should be a bytes object with the length = self.address_length
    def open_tx_pipe(self, address):
        assert len(address) == self.address_length
        self._reg_write_bytes(RX_ADDR_P0, address)
        self._reg_write_bytes(TX_ADDR, address)
        if not self.dynamic_payloads: # radio doesn't care about payload_length if dynamic_payloads is enabled
            self._reg_write(RX_PW_P0, self.payload_length)

    # address should be a bytes object with the length = self.address_length
    # pipe 0 and 1 have 5 byte address
    # pipes 2-5 use same 4 MSBytes as pipe 1, plus 1 extra byte
    def open_rx_pipe(self, pipe_id, address, ack_payload=None):
        """
        setup a data pipe for receiving data from a specified address.\n
        pipe_id (int) must be in range [0,5].\n
        address (bytearray) must be a maximum of 5 bytes long. If using a pipe_id greater than 2, then only the LSByte of the address is written (so make LSByte unique among other simultaneously broadcasting addresses).NOTE: MSBytes (address[0:4]) are shared on pipes 2 through 5\n
        ack_payload (bytearray) is optional and must be 1 to 32 bytes long. The specified payload (if not None) will be used as part of ACK packet during RX mode.
        """
        assert len(address) == self.address_length
        assert 0 <= pipe_id <= 5
        assert ack_payload is None or 1 <= len(ack_payload) <= 32
        # open_tx_pipe() overrides pipe 0 address. Thus start_listening() will re-enforce this address using self.pipe0_read_addr
        if pipe_id == 0: 
            # save shadow copy of address if target pipe_id is 0
            self.pipe0_read_addr = address
        elif pipe_id < 2: # write entire address if pip_id is 1
            self._reg_write_bytes(RX_ADDR_P0 + pipe_id, address)
        else: # only write LSB if pipe_id is not 0 or 1
            self._reg_write(RX_ADDR_P0 + pipe_id, address[len(address) - 1])
        if not self.dynamic_payloads: # radio doesn't care about payload_length if dynamic_payloads is enabled
            self._reg_write(RX_PW_P0 + pipe_id, self.payload_length)
        self._reg_write(EN_RXADDR, self._reg_read(EN_RXADDR) | (1 << pipe_id))
        if ack_payload is not None:
            self._reg_write_bytes(W_ACK_PAYLOAD | pipe_id, ack_payload)

    def start_listening(self):
        """
        This function flushes the RX and TX FIFOs, clears the status flags. This function also puts radio in powers up and RX mode.
        """
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
        """
        This function flushes the RX and TX FIFOs, clears the status flags. Before exiting, this function also puts radio in powers down and TX mode.
        """
        # disable comms
        self.ce.value = 0
        self._flush_tx()
        self._flush_rx()
        self.clear_status_flags()
        # power down radio. Also set radio in TX mode as recommended behavior per spec sheet.
        self._reg_write(CONFIG, self._reg_read(CONFIG) & 0xfc)
        # manipulating local copy of power attribute saves an extra spi transaction because we already needed to access the same register to manipulate RX/TX mode
        self._power_mode = False 

    def available(self, pipe_id=None):
        """
        pipe_id (int) is optional and must be in range [0,5].\n
        If user does not specify pipe_id, then this function returns the pipe number that contains the RX payload.\n
        If user does specify pipe_id, then this function returns True if pipe_id == RX pipe number else False.\n
        If there is no payload in RX FIFO, then this function returns None.
        """
        assert pipe_id == None or 0 <= pipe_id <= 5 # check bounds on user input
        pipe = (self._reg_read(STATUS) & RX_P_NO) >> 1
        if pipe > 5:
            return None # RX FIFO is empty
        elif pipe_id is None:
            # return pipe number if user did not specify a pipe number to test against
            return pipe # base 1 as pipe0 would be same as False
        elif pipe_id != pipe:
            # return comparison of pipe number and user specified pipe number
            return False
        else: # return True if pipe number matches user input & there is data in RX FIFO 
            return True

    def any(self):
        """
        This function returns the size (in bytes) of an available RX payload.\n
        If dynamic payloads are enabled, this function returns True when the RX FIFO is not empty.\n
        If there is no payload in the RX FIFO, this function returns False.
        """
        if not bool(self._reg_read(FIFO_STATUS) & RX_EMPTY):
            return self._reg_read(R_RX_PL_WID) if not self.dynamic_payloads else True
        else: return False

    def recv(self):
        """
        This function is used to retrieve the RX payload (as a bytearray), then clears all the status flags. This function is also used in TX mode to aquire the ACK payload (if any). NOTE: dynamic_payloads should be enabled in order to use ACK payloads.\n
        If dynamic_payloads are enabled, the returned bytearray's length = user defined payload_length (which defaults to 32).\n
        If dynamic_payloads are disabled, the returned bytearray's length = payload size in the RX FIFO.\n
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
        """
        Allows user to read the ACK payload if any. This function can be called from a blocking send() call via read_ack arg in send() or by itself in case of using the less-blocking send_fast() call\n
        NOTE: this function will do nothing if the status flags are cleared after calling send_fast() and before calling this function. Also, dynamic_payloads should be enabled in order to use ACK payloads.
        """
        if self.any(): # check RX payload for ACK packet
            self.ack = self.recv()

    def send(self, buf, read_ack=False, timeout=0.2):
        """
        A blocking function to transmit payload until one of the following results is acheived: 
            Returns 0 if timeout
            Returns 1 if success
            Returns 2 if fail
        buf (bytearray) must have a length greater than 0 to execute transmission.
            If dynamic_payloads == False and len(buf) less than payload_length, buf is padded with 0s till len(buf) == payload_length
            If dynamic_payloads == False and len(buf) greater than payload_length, buf is truncated to payload_length.
        read_ack (bool) specifies wheather or not to save the ACK payload to the ack attribute.\n
        timeout (float) is an arbitrary number of seconds that is used to keep application from indefinitely hanging in case of radio malfunction. Default is 200 milliseconds. This arg may get depricated in the future.
        """
        result = 0
        self.send_fast(buf)
        time.sleep(0.00001) # ensure CE pulse is >= 10 us
        start = time.monotonic()
        self.ce.value = 0
        while result is 0 and (time.monotonic() - start) < timeout:
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
        """
        This function (when used without send()) is meant for asynchronous operation. It isn't completely non-blocking as we still need to wait ~5 ms for CSN to settle. A NOTE from the spec sheet:
            It is important never to keep the nRF24L01+ in TX mode for more than 4ms at a time. If the [auto_ack and dynamic_payloads] features are enabled, nRF24L01+ is never in TX mode longer than 4ms.
        Conclusion: Use this function at your own risk. If you do, you MUST additionally use either interrupt flags with user defined timer(s) OR enabled dynamic_payloads (auto_ack is enabled with dynamic_payloads) to obey the 4ms rule. If the spec sheet explicitly states this, we have to assume radio damage or misbehavior as a result of disobeying the 4ms rule. Cleverly, TMRh20's arduino library recommends using auto retransmit delay (ARD) to avoid breaking this rule, but we have not verified this strategy.
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
