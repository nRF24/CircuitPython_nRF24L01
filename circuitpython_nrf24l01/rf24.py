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
rf24 module containing the base class RF24
"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import time
from adafruit_bus_device.spi_device import SPIDevice

# nRF24L01 registers
# pylint: disable=bad-whitespace
CONFIG     = 0x00 #: register for configuring IRQ, CRC, PWR & RX/TX roles
EN_AA      = 0x01 #: register for auto-ACK feature. Each bit represents this feature per pipe
EN_RX      = 0x02 #: register to open/close pipes. Each bit represents this feature per pipe
SETUP_AW   = 0x03 #: address width register
SETUP_RETR = 0x04 #: auto-retry count and delay register
RF_CH      = 0x05 #: channel register
RF_SETUP   = 0x06 #: RF Power Amplifier & Data Rate
RX_ADDR    = 0x0a #: RX pipe addresses == [0,5]:[0x0a:0x0f]
RX_PW      = 0x11 #: RX payload widths on pipes == [0,5]:[0x11,0x16]
FIFO       = 0x17 #: register containing info on both RX/TX FIFOs + re-use payload flag
DYNPD      = 0x1c #: dynamic payloads feature. Each bit represents this feature per pipe
FEATURE    = 0x1d #: global flags for dynamic payloads, custom ACK payloads, & Ask no ACK
TX_ADDR    = 0x10 #: Address that is used for TX transmissions
# pylint: enable=bad-whitespace

class RF24:
    """A driver class for the nRF24L01(+) transceiver radios. This class aims to be compatible with
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
    :param bool irq_DR: When "Data is Ready", this configures the interrupt (IRQ) trigger of the
        nRF24L01's IRQ pin (active low). Defaults to enabled. This can be changed at any time by
        using the `interrupt_config()` function.
    :param bool irq_DS: When "Data is Sent", this configures the interrupt (IRQ) trigger of the
        nRF24L01's IRQ pin (active low). Defaults to enabled. This can be changed at any time by
        using the `interrupt_config()` function.
    :param bool irq_DF: When "max retry attempts are reached" (specified by the `arc` attribute),
        this configures the interrupt (IRQ) trigger of the nRF24L01's IRQ pin (active low) and
        represents transmission failure. Defaults to enabled. This can be changed at any time by
        using the `interrupt_config()` function.
    """
    def __init__(self, spi, csn, ce,
                 channel=76,
                 payload_length=32,
                 address_length=5,
                 ard=1500,
                 arc=3,
                 crc=2,
                 data_rate=1,
                 pa_level=0,
                 dynamic_payloads=True,
                 auto_ack=True,
                 ask_no_ack=True,
                 ack=False,
                 irq_DR=True,
                 irq_DS=True,
                 irq_DF=True):
        self._payload_length = payload_length  # inits internal attribute
        self.payload_length = payload_length
        # last address assigned to pipe0 for reading. init to None
        self._fifo = 0
        self._status = 0
        # init shadow copy of RX addresses for all pipes
        self._pipes = [b'', b'', 0, 0, 0, 0]
        for i in range(6): # set all pipe's RX addresses to reset value
            if i < 2:
                if not i:
                    self._pipes[i] = b'\xe7' * address_length
                else:
                    self._pipes[i] = b'\xc2' * address_length
            else:
                self._pipes[i] = 0xc1 + i
        self._tx_address = self._pipes[0] # shadow copy of the TX_ADDR
        self._payload_widths = [0, 0, 0, 0, 0, 0] # payload_length specific to each pipe
        # shadow copy of last RX_ADDR written to pipe 0
        self._pipe0_read_addr = None # needed as open_tx_pipe() appropriates pipe 0 for ACK
        # init the _open_pipes attribute (reflects only RX state on each pipe)
        self._open_pipes = 0  # <- means all pipes closed
        # init the SPI bus and pins
        self.spi = SPIDevice(spi, chip_select=csn, baudrate=1250000)

        # store the ce pin
        self.ce = ce
        # reset ce.value & disable the chip comms
        self.ce.switch_to_output(value=False)
        # if radio is powered up and CE is LOW: standby-I mode
        # if radio is powered up and CE is HIGH: standby-II mode

        # NOTE per spec sheet: nRF24L01+ must be in a standby or power down mode before writing
        # to the configuration register
        # configure the CONFIG register:IRQ(s) config, setup CRC feature, and trigger standby-I &
        # TX mode (the "| 2")
        if 0 <= crc <= 2:
            self._config = ((not irq_DR) << 6) | ((not irq_DS) << 5) | ((not irq_DF) << 4) | \
                ((crc + 1) << 2 if crc else 0) | 2
            self._reg_write(CONFIG, self._config)  # dump to register
        else:
            raise ValueError(
                "CRC byte length must be an int equal to 0 (off), 1, or 2")

        # check for device presence by verifying nRF24L01 is in TX + standby-I mode
        if self._reg_read(CONFIG) & 3 == 2: # if in TX + standby-I mode
            self.power = False  # power down
        else: # hardware presence check NOT passed
            print(bin(self._reg_read(CONFIG)))
            raise RuntimeError("nRF24L01 Hardware not responding")

        # configure the SETUP_RETR register
        if 250 <= ard <= 4000 and ard % 250 == 0 and 0 <= arc <= 15:
            self._setup_retr = (int((ard - 250) / 250) << 4) | arc
        else:
            raise ValueError("automatic re-transmit delay can only be a multiple of 250 in range "
                             "[250,4000]\nautomatic re-transmit count(/attempts) must range "
                             "[0,15]")

        # configure the RF_SETUP register
        if data_rate in (1, 2, 250) and pa_level in (-18, -12, -6, 0):
            data_rate = 0 if data_rate == 1 else (
                8 if data_rate == 2 else 0x20)
            pa_level = (3 - int(pa_level / -6)) * 2
            self._rf_setup = data_rate | pa_level
        else:
            raise ValueError("data rate must be one of the following ([M,M,K]bps): 1, 2, 250"
                             "\npower amplifier must be one of the following (dBm): -18, -12,"
                             " -6, 0")

        # manage dynamic_payloads, auto_ack, and ack features
        self._dyn_pl = 0x3F if dynamic_payloads else 0  # 0x3F == enabled on all pipes
        self._aa = 0x3F if auto_ack else 0 # 0x3F == enabled on all pipes
        self._features = (dynamic_payloads << 2) | ((ack if auto_ack and dynamic_payloads
                                                     else False) << 1) | ask_no_ack

        # init the last few singleton attribute
        self._channel = channel
        self._addr_len = address_length

        with self:  # write to registers & power up
            # using __enter__() configures all virtual features and settings to the hardware
            # registers
            self.ce.value = 0  # ensure standby-I mode to write to CONFIG register
            self._reg_write(CONFIG, self._config | 1)  # enable RX mode
            time.sleep(0.000015)  # wait time for transitioning modes RX/TX
            self.flush_rx()  # spec sheet say "used in RX mode"
            self._reg_write(CONFIG, self._config & 0xC)  # power down + TX mode
            time.sleep(0.000015)  # wait time for transitioning modes RX/TX
            self.flush_tx()  # spec sheet say "used in TX mode"
            self.clear_status_flags()  # writes directly to STATUS register

    def __enter__(self):
        # dump IRQ and CRC data to CONFIG register
        self._reg_write(CONFIG, self._config & 0x7C)
        self._reg_write(RF_SETUP, self._rf_setup) # dump to RF_SETUP register
        # dump open/close pipe status to EN_RXADDR register (for all pipes)
        self._reg_write(EN_RX, self._open_pipes)
        self._reg_write(DYNPD, self._dyn_pl) # dump to DYNPD register
        self._reg_write(EN_AA, self._aa) # dump to EN_AA register
        self._reg_write(FEATURE, self._features) # dump to FEATURE register
        # dump to SETUP_RETR register
        self._reg_write(SETUP_RETR, self._setup_retr)
        # dump pipes' RX addresses and static payload lengths
        for i, address in enumerate(self._pipes):
            if i < 2:
                self._reg_write_bytes(RX_ADDR + i, address)
            else:
                self._reg_write(RX_ADDR + i, address)
            self._reg_write(RX_PW + i, self._payload_widths[i])
        # dump last used TX address
        self._reg_write_bytes(TX_ADDR, self._tx_address)
        self.address_length = self._addr_len  # writes directly to SETUP_AW register
        self.channel = self._channel  # writes directly to RF_CH register
        return self

    def __exit__(self, *exc):
        return False

    # pylint: disable=no-member
    def _reg_read(self, reg):
        buf = bytearray(2)  # 2 = 1 status byte + 1 byte of returned content
        with self.spi as spi:
            time.sleep(0.005)  # time for CSN to settle
            spi.readinto(buf, write_value=reg)
        self._status = buf[0]  # save status byte
        return buf[1]  # drop status byte and return the rest

    def _reg_read_bytes(self, reg, buf_len=5):
        # allow an extra byte for status data
        buf = bytearray(buf_len + 1)
        with self.spi as spi:
            time.sleep(0.005)  # time for CSN to settle
            spi.readinto(buf, write_value=reg)
        self._status = buf[0]  # save status byte
        return buf[1:]  # drop status byte and return the rest

    def _reg_write_bytes(self, reg, out_buf):
        out_buf = bytes([0x20 | reg]) + out_buf
        in_buf = bytearray(len(out_buf))
        with self.spi as spi:
            time.sleep(0.005)  # time for CSN to settle
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]  # save status byte

    def _reg_write(self, reg, value=None):
        if value is None:
            out_buf = bytes([reg])
        else:
            out_buf = bytes([0x20 | reg, value])
        in_buf = bytearray(len(out_buf))
        with self.spi as spi:
            time.sleep(0.005)  # time for CSN to settle
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]  # save status byte
    # pylint: enable=no-member

    @property
    def address_length(self):
        """This `int` attribute specifies the length (in bytes) of addresses to be used for RX/TX
        pipes. The addresses assigned to the data pipes must have byte length equal to the value
        set for this attribute.

        A valid input value must be an `int` in range [3,5]. Otherwise a `ValueError` exception is
        thrown. Default is set to the nRF24L01's maximum of 5.
        """
        return self._reg_read(SETUP_AW) + 2

    @address_length.setter
    def address_length(self, length):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration
        # registers.
        if 3 <= length <= 5:
            # address width is saved in 2 bits making range = [3,5]
            self._addr_len = int(length)
            self._reg_write(SETUP_AW, length - 2)
        else:
            raise ValueError(
                "address length can only be set in range [3,5] bytes")

    def open_tx_pipe(self, address):
        """This function is used to open a data pipe for OTA (over the air) TX transmissions.

        :param bytearray address: The virtual address of the receiving nRF24L01. This must have a
            length equal to the `address_length` attribute (see `address_length` attribute).
            Otherwise a `ValueError` exception is thrown. The address specified here must match the
            address set to one of the RX data pipes of the receiving nRF24L01.

        .. note:: There is no option to specify which data pipe to use because the nRF24L01 only
            uses data pipe 0 in TX mode. Additionally, the nRF24L01 uses the same data pipe (pipe
            0) for receiving acknowledgement (ACK) packets in TX mode when the `auto_ack` attribute
            is enabled. Thus, RX pipe 0 is appropriated with the TX address (specified here) when
            `auto_ack` is set to `True`.
        """
        if len(address) == self.address_length:
            # if auto_ack == True, then use this TX address as the RX address for ACK
            if self.auto_ack:
                # settings need to match on both transceivers: dynamic_payloads and payload_length
                self._pipes[0] = address
                self._reg_write_bytes(RX_ADDR, address) # using pipe 0
                self._open_pipes = self._open_pipes | 1 # open pipe 0 for RX-ing ACK
                self._reg_write(EN_RX, self._open_pipes)
                self._payload_widths[0] = self.payload_length
                self._reg_write(RX_PW, self.payload_length) # set expected payload_length
                self._pipes[0] = address # update the context as well
            self._tx_address = address
            self._reg_write_bytes(TX_ADDR, address)
        else:
            raise ValueError("address must be a buffer protocol object with a byte length\nequal "
                             "to the address_length attribute (currently set to"
                             " {})".format(self.address_length))

    def close_rx_pipe(self, pipe_number, reset=True):
        """This function is used to close a specific data pipe from OTA (over the air) RX
        transmissions.

        :param int pipe_number: The data pipe to use for RX transactions. This must be in range
            [0,5]. Otherwise a `ValueError` exception is thrown.
        :param bool reset: `True` resets the address for the specified ``pipe_number`` to the
            factory address (different for each pipe). `False` leaves the address on the specified
            ``pipe_number`` alone. Be aware that the addresses will remain despite loss of power.
        """
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        self._open_pipes = self._reg_read(EN_RX)  # refresh data
        if reset:# reset pipe address accordingly
            if not pipe_number:
                # NOTE this does not clear the shadow copy (pipe0_read_addr) of address for pipe 0
                self._reg_write_bytes(pipe_number + RX_ADDR, b'\xe7' * 5)
                self._pipes[pipe_number] = b'\xe7' * 5
            elif pipe_number == 1:  # write the full address for pipe 1
                self._reg_write_bytes(pipe_number + RX_ADDR, b'\xc2' * 5)
                self._pipes[pipe_number] = b'\xc2' * 5
            else:  # write just MSB for 2 <= pipes <= 5
                self._reg_write(pipe_number + RX_ADDR, pipe_number + 0xc1)
                self._pipes[pipe_number] = pipe_number + 0xc1
        # disable the specified data pipe if not already
        if self._open_pipes & (1 << pipe_number):
            self._open_pipes = self._open_pipes & ~(1 << pipe_number)
            self._reg_write(EN_RX, self._open_pipes)

    def open_rx_pipe(self, pipe_number, address):
        """This function is used to open a specific data pipe for OTA (over the air) RX
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
        """
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        if len(address) != self.address_length:
            raise ValueError("address must be a buffer protocol object with a byte length\nequal "
                             "to the address_length attribute (currently set to "
                             "{})".format(self.address_length))

        # write the address
        if pipe_number < 2:  # write entire address if pipe_number is 0 or 1
            if not pipe_number:
                # save shadow copy of address if target pipe_number is 0. This is done to help
                # ensure the proper address is set to pipe 0 via _start_listening() as
                # open_tx_pipe() will appropriate the address on pipe 0 if auto_ack is enabled for
                # TX mode
                self._pipe0_read_addr = address
            self._pipes[pipe_number] = address
            self._reg_write_bytes(RX_ADDR + pipe_number, address)
        else:
            # only write MSByte if pipe_number is not 0 or 1
            self._pipes[pipe_number] = address[0]
            self._reg_write(RX_ADDR + pipe_number, address[0])

        # now manage the pipe
        self._open_pipes = self._reg_read(EN_RX)  # refresh data
        # enable the specified data pipe
        self._open_pipes = self._open_pipes | (1 << pipe_number)
        self._reg_write(EN_RX, self._open_pipes)

        # now adjust payload_length accordingly despite dynamic_payload setting
        # radio only uses this info in RX mode when dynamic_payloads == True
        self._reg_write(RX_PW + pipe_number, self.payload_length)
        self._payload_widths[pipe_number] = self.payload_length

    @property
    def listen(self):
        """An attribute to represent the nRF24L01 primary role as a radio.

        Setting this attribute incorporates the proper transitioning to/from RX mode as it involves
        playing with the `power` attribute and the nRF24L01's CE pin. This attribute does not power
        down the nRF24L01, but will power it up when needed; use `power` attribute set to `False`
        to put the nRF24L01 to sleep.

        A valid input value is a `bool` in which:

            `True` enables RX mode. Additionally, per `Appendix B of the nRF24L01+ Specifications
            Sheet
            <https://www.sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1091756>`_, this attribute
            flushes the RX FIFO, clears the `irq_DR` status flag, and puts nRF24L01 in power up
            mode. Notice the CE pin is be held HIGH during RX mode.

            `False` disables RX mode. As mentioned in above link, this puts nRF24L01's power in
            Standby-I (CE pin is LOW meaning low current & no transmissions) mode which is ideal
            for post-reception work. Disabing RX mode doesn't flush the RX/TX FIFO buffers, so
            remember to flush your 3-level FIFO buffers when appropriate using `flush_tx()` or
            `flush_rx()` (see also the `recv()` function).
        """
        return self.power and bool(self._config & 1)

    @listen.setter
    def listen(self, is_rx):
        assert isinstance(is_rx, (bool, int))
        if self.listen != is_rx:
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self):
        # ensure radio is in power down or standby-I mode
        if self.ce.value:
            self.ce.value = 0

        if self._pipe0_read_addr is not None:
            # make sure the last call to open_rx_pipe(0) sticks if initialized
            self._reg_write_bytes(RX_ADDR, self._pipe0_read_addr)
            self._pipes[0] = self._pipe0_read_addr # update the context as well

        # power up radio & set radio in RX mode
        self._config = self._config & 0xFC | 3
        self._reg_write(CONFIG, self._config)
        time.sleep(0.00015) # mandatory wait time to power up radio or switch modes (RX/TX)
        self.flush_rx() # spec sheet says "used in RX mode"
        self.clear_status_flags(True, False, False) # only Data Ready flag

        # enable radio comms
        self.ce.value = 1 # radio begins listening after CE pulse is > 130 µs
        time.sleep(0.00013) # ensure pulse is > 130 µs
        # nRF24L01 has just entered active RX + standby-II mode

    def _stop_listening(self):
        # ensure radio is in standby-I mode
        if self.ce.value:
            self.ce.value = 0
        # set radio in TX mode as recommended behavior per spec sheet.
        self._config = self._config & 0xFE  # does not put radio to sleep
        self._reg_write(CONFIG, self._config)
        # mandated wait for transitioning between modes RX/TX
        time.sleep(0.00016)
        # exits while still in Standby-I (low current & no transmissions)

    def any(self):
        """This function checks if the nRF24L01 has received any data at all. Internally, this
        function uses `pipe()` then reports the next available payload's length (in bytes) -- if
        there is any.

        :returns:
            - `int` of the size (in bytes) of an available RX payload (if any).
            - ``0`` if there is no payload in the RX FIFO buffer.
        """
        if self.pipe() is not None:
            # 0x60 == R_RX_PL_WID command
            return self._reg_read(0x60)  # top-level payload length
        return 0  # RX FIFO empty

    def recv(self):
        """This function is used to retrieve the next available payload in the RX FIFO buffer, then
        clears the `irq_DR` status flag. This function also serves as a helper function to
        `read_ack()` in TX mode to aquire any custom payload in the automatic acknowledgement (ACK)
        packet -- only when the `ack` attribute is enabled.

        :returns: A `bytearray` of the RX payload data

            - If the `dynamic_payloads` attribute is disabled, then the returned bytearray's length
              is equal to the user defined `payload_length` attribute (which defaults to 32).
            - If the `dynamic_payloads` attribute is enabled, then the returned bytearray's length
              is equal to the payload's length

        .. tip:: Call the `any()` function before calling `recv()` to verify that there is data to
            fetch. If there's no data to fetch, then the nRF24L01 returns bogus data and should not
            regarded as a valid payload.
        """
        # buffer size = current payload size (0x60 = R_RX_PL_WID) + status byte
        curr_pl_size = self.payload_length if not self.dynamic_payloads else self._reg_read(
            0x60)
        # get the data (0x61 = R_RX_PAYLOAD)
        result = self._reg_read_bytes(0x61, curr_pl_size)
        # clear only Data Ready IRQ flag for continued RX operations
        self.clear_status_flags(True, False, False)
        # return all available bytes from payload
        return result

    def send(self, buf, ask_no_ack=False):
        """This blocking function is used to transmit payload(s).

        :returns:
            * `list` if a list or tuple of payloads was passed as the ``buf`` parameter. Each item
              in the returned list will contain the returned status for each corresponding payload
              in the list/tuple that was passed. The return statuses will be in one of the
              following forms:
            * `False` if transmission fails.
            * `True` if transmission succeeds.
            * `bytearray` when the `ack` attribute is `True`, the payload expects a responding
              custom ACK payload; the response is returned (upon successful transmission) as a
              `bytearray`. Empty ACK payloads (upon successful transmission) when the `ack`
              attribute is set `True` are replaced with an error message ``b'NO ACK RETURNED'``.
            * `None` if transmission times out meaning nRF24L01 has malfunctioned. This condition
              is very rare. The allowed time for transmission is calculated using `table 18 in the
              nRF24L01 specification sheet <https://www.sparkfun.com/datasheets/Components/SMD/
              nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1123001>`_

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
            this for every payload if the `auto_ack` attribute is disabled, however this parameter
            should work despite the `auto_ack` attribute's setting.

            .. note:: Each transmission is in the form of a packet. This packet contains sections
                of data around and including the payload. `See Chapter 7.3 in the nRF24L01
                Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/
                nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1136318>`_ for more
                details.

        .. tip:: It is highly recommended that `auto_ack` attribute is enabled when sending
            multiple payloads. Test results with the `auto_ack` attribute disabled were very poor
            (much < 50% received). This same advice applies to the ``ask_no_ack`` parameter (leave
            it as `False` for multiple payloads).

        .. warning::  The nRF24L01 will block usage of the TX FIFO buffer upon failed
            transmissions. Failed transmission's payloads stay in TX FIFO buffer until the MCU
            calls `flush_tx()` and `clear_status_flags()`. Therefore, this function will discard
            failed transmissions' payloads when sending a list or tuple of payloads, so it can
            continue to process through the list/tuple even if any payload fails to be
            acknowledged.

        .. note:: We've tried very hard to keep nRF24L01s driven by CircuitPython devices compliant
            with nRF24L01s driven by the Raspberry Pi. But due to the Raspberry Pi's seemingly
            slower SPI speeds, we've had to resort to internally deploying `resend()` twice (at
            most when needed) for payloads that failed during multi-payload processing. This tactic
            is meant to slow down CircuitPython devices just enough for the Raspberry Pi to catch
            up. Transmission failures are less possible this way.
        """
        # ensure power down/standby-I for proper manipulation of PWR_UP & PRIM_RX bits in
        # CONFIG register
        self.ce.value = 0
        self.flush_tx()
        self.clear_status_flags(False)  # clears TX related flags only
        # using spec sheet calculations:
        # timeout total = T_upload + 2 * stby2active + T_overAir + T_ack + T_irq

        # T_upload = payload length (in bits) / spi data rate (bits per second =
        # baudrate / bits per byte)
        # T_upload is finished before timeout begins

        # T_download == T_upload, however RX devices spi settings must match TX's for
        # accurate calc

        # let 2 * stby2active (in µs) ~= (2 + 1 if getting ack else 0) * 130

        # let T_ack = T_overAir as the payload size is the only distictive variable between
        # the 2
        # T_overAir (in seconds) = ( 8 (bits/byte) * (1 byte preamble + address length +
        # payload length + crc length) + 9 bit packet ID ) / RF data rate (in bits/sec)

        # spec sheet says T_irq is (0.0000082 if self.data_rate == 1 else 0.000006) seconds
        pl_coef = 1 + (bool(self.auto_ack) and not ask_no_ack)
        pl_len = 1 + self._addr_len + (max(0, ((self._config & 12) >> 2) - 1))
        bitrate = ((2000000 if self._rf_setup & 0x28 == 8 else 250000)
                   if self._rf_setup & 0x28 else 1000000) / 8
        stby2active = (1 + pl_coef) * 0.00013
        t_irq = 0.0000082 if not self._rf_setup & 0x28 else 0.000006
        t_retry = (((self._setup_retr & 0xf0) >> 4) * 250 + 380) * \
            (self._setup_retr & 0x0f) / 1000000
        if isinstance(buf, (list, tuple)):  # writing a set of payloads
            result = []
            for i, b in enumerate(buf):  # check invalid payloads first
                # this way when we raise a ValueError exception we don't leave the nRF24L01 in an
                # unknown frozen state.
                if not b or len(b) > 32:
                    raise ValueError("buf (item {} in the list/tuple) must be a"
                                     " buffer protocol object with a byte length of\nat least 1 "
                                     "and no greater than 32".format(i))
            for b in buf:
                timeout = pl_coef * (((8 * (len(b) + pl_len)) + 9) / bitrate) + \
                    stby2active + t_irq + t_retry + \
                    (len(b) * 64 / self.spi.baudrate)
                self.write(b, ask_no_ack)
                # wait for the ESB protocol to finish (or at least attempt)
                time.sleep(timeout) # TODO could do this better
                self.update()  # update status flags
                if self.irq_DF:  # need to clear for continuing transmissions
                    # retry twice at most -- this seemed adaquate during testing
                    for i in range(2):
                        if not self.resend():  # clears flags upon entering and exiting
                            if i:  # the last try
                                self.flush_tx()  # discard failed payloads in the name of progress
                                result.append(False)
                        else:  # resend succeeded
                            if self.ack:  # is there a custom ACK payload?
                                result.append(self.read_ack())
                            else:
                                result.append(True)
                            break
                elif self.irq_DS:
                    result.append(True)
                    # clears TX related flags only
                    self.clear_status_flags(False)
            self.ce.value = 0
            return result
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of"
                             "\nat least 1 and no greater than 32")
        result = None
        # T_upload is done before timeout begins (after payload write action AKA upload)
        timeout = pl_coef * (((8 * (len(buf) + pl_len)) + 9) /
                             bitrate) + stby2active + t_irq + t_retry
        self.write(buf, ask_no_ack)  # init using non-blocking helper
        time.sleep(0.00001)  # ensure CE pulse is >= 10 µs
        # if pulse is stopped here, the nRF24L01 only handles the top level payload in the FIFO.
        # hold CE HIGH to continue processing through the rest of the TX FIFO bound for the
        # address passed to open_tx_pipe()
        # go to Standby-I power mode (power attribute still == True)
        self.ce.value = 0

        # now wait till the nRF24L01 has determined the result or timeout (based on calcs
        # from spec sheet)
        start = time.monotonic()
        while not self.irq_DS and not self.irq_DF and (time.monotonic() - start) < timeout:
            self.update()  # perform Non-operation command to get status byte (should be faster)
            # print('status: DR={} DS={} DF={}'.format(self.irq_DR, self.irq_DS, self.irq_DF))
        if self.irq_DS or self.irq_DF:  # transmission done
            # get status flags to detect error
            result = self.irq_DS if self.auto_ack else not self.irq_DF

        # read ack payload clear status flags, then power down
        if self.ack and self.irq_DS and not ask_no_ack:
            # get and save ACK payload to self.ack if user wants it
            result = self.read_ack()  # save RX'd ACK payload to result
            if result is None:  # can't return empty handed
                result = b'NO ACK RETURNED'
        self.clear_status_flags(False)  # only TX related IRQ flags
        return result

    @property
    def irq_DR(self):
        """A `bool` that represents the "Data Ready" interrupted flag. (read-only)

        * `True` represents Data is in the RX FIFO buffer
        * `False` represents anything depending on context (state/condition of FIFO buffers) --
          usually this means the flag's been reset.

        Pass ``dataReady`` parameter as `True` to `clear_status_flags()` and reset this. As this is
        a virtual representation of the interrupt event, this attribute will always be updated
        despite what the actual IRQ pin is configured to do about this event.

        Calling this does not execute an SPI transaction. It only exposes that latest data
        contained in the STATUS byte that's always returned from any other SPI transactions. Use
        the `update()` function to manually refresh this data when needed.
        """
        return bool(self._status & 0x40)

    @property
    def irq_DS(self):
        """A `bool` that represents the "Data Sent" interrupted flag. (read-only)

        * `True` represents a successful transmission
        * `False` represents anything depending on context (state/condition of FIFO buffers) --
          usually this means the flag's been reset.

        Pass ``dataSent`` parameter as `True` to `clear_status_flags()` to reset this. As this is a
        virtual representation of the interrupt event, this attribute will always be updated
        despite what the actual IRQ pin is configured to do about this event.

        Calling this does not execute an SPI transaction. It only exposes that latest data
        contained in the STATUS byte that's always returned from any other SPI transactions. Use
        the `update()` function to manually refresh this data when needed.
        """
        return bool(self._status & 0x20)

    @property
    def irq_DF(self):
        """A `bool` that represents the "Data Failed" interrupted flag. (read-only)

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
        """
        return bool(self._status & 0x10)

    def clear_status_flags(self, data_recv=True, data_sent=True, data_fail=True):
        """This clears the interrupt flags in the status register. Internally, this is
        automatically called by `send()`, `write()`, `recv()`, and when `listen` changes from
        `False` to `True`.

        :param bool data_recv: specifies wheather to clear the "RX Data Ready" flag.
        :param bool data_sent: specifies wheather to clear the "TX Data Sent" flag.
        :param bool data_fail: specifies wheather to clear the "Max Re-transmit reached" flag.

        .. note:: Clearing the ``data_fail`` flag is necessary for continued transmissions from the
            nRF24L01 (locks the TX FIFO buffer when `irq_DF` is `True`) despite wheather or not the
            MCU is taking advantage of the interrupt (IRQ) pin. Call this function only when there
            is an antiquated status flag (after you've dealt with the specific payload related to
            the staus flags that were set), otherwise it can cause payloads to be ignored and
            occupy the RX/TX FIFO buffers. See `Appendix A of the nRF24L01+ Specifications Sheet
            <https://www.sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1047965>`_ for an outline of
            proper behavior.
        """
        # 0x07 = STATUS register; only bits 6 through 4 are write-able
        self._reg_write(0x07, (data_recv << 6) | (
            data_sent << 5) | (data_fail << 4))

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        """Sets the configuration of the nRF24L01's IRQ (interrupt) pin. The signal from the
        nRF24L01's IRQ pin is active LOW. (write-only)

        :param bool data_recv: If this is `True`, then IRQ pin goes active when there is new data
            to read in the RX FIFO buffer.
        :param bool data_sent: If this is `True`, then IRQ pin goes active when a payload from TX
            buffer is successfully transmit.
        :param bool data_fail: If this is `True`, then IRQ pin goes active when maximum number of
            attempts to re-transmit the packet have been reached. If `auto_ack` attribute is
            disabled, then this IRQ event is not used.

        .. note:: To fetch the status (not configuration) of these IRQ flags, use the `irq_DF`,
            `irq_DS`, `irq_DR` attributes respectively.

        .. tip:: Paraphrased from nRF24L01+ Specification Sheet:

            The procedure for handling ``data_recv`` IRQ should be:

            1. read payload through `recv()`
            2. clear ``dataReady`` status flag (taken care of by using `recv()` in previous step)
            3. read FIFO_STATUS register to check if there are more payloads available in RX FIFO
               buffer. (a call to `pipe()`, `any()` or even ``(False,True)`` as parameters to
               `fifo()` will get this result)
            4. if there is more data in RX FIFO, repeat from step 1
        """
        self._config = self._reg_read(CONFIG)  # refresh data
        # save to register and update local copy of pwr & RX/TX modes' flags
        self._config = (self._config & 0x0F) | (not data_fail << 4) | (not data_sent << 5) | \
            (not data_recv << 6)
        self._reg_write(CONFIG, self._config)

    def what_happened(self, dump_pipes=False):
        """This debuggung function aggregates and outputs all status/condition related information
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
            - ``Packets Lost`` Total amount of packets lost (transmission failures)
            - ``Retry Attempts Made`` Maximum amount of attempts to re-transmit during last
              transmission (resets per payload)
            - ``IRQ - Data Ready`` The current setting of the IRQ pin on "Data Ready" event
            - ``IRQ - Data Sent`` The current setting of the IRQ pin on "Data Sent" event
            - ``IRQ - Data Fail`` The current setting of the IRQ pin on "Data Fail" event
            - ``Data Ready`` Is there RX data ready to be read?
              (state of the `irq_DR` flag)
            - ``Data Sent`` Has the TX data been sent? (state of the `irq_DS` flag)
            - ``Data Failed`` Has the maximum attempts to re-transmit been reached?
              (state of the `irq_DF` flag)
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
        """
        watchdog = self._reg_read(8)  # 8 == OBSERVE_TX register
        print("Channel___________________{} ~ {} GHz".format(
            self.channel, (self.channel + 2400) / 1000))
        print("RF Data Rate______________{} {}".format(
            self.data_rate, "Mbps" if self.data_rate != 250 else "Kbps"))
        print("RF Power Amplifier________{} dbm".format(self.pa_level))
        print("CRC bytes_________________{}".format(self.crc))
        print("Address length____________{} bytes".format(self.address_length))
        print("Payload lengths___________{} bytes".format(self.payload_length))
        print("Auto retry delay__________{} microseconds".format(self.ard))
        print("Auto retry attempts_______{} maximum".format(self.arc))
        print("Packets Lost______________{} total".format((watchdog & 0xF0) >> 4))
        print("Retry Attempts Made_______{}".format(watchdog & 0x0F))
        print("IRQ - Data Ready______{}    Data Ready___________{}".format(
            '_True' if not bool(self._config & 0x40) else 'False', self.irq_DR))
        print("IRQ - Data Fail_______{}    Data Failed__________{}".format(
            '_True' if not bool(self._config & 0x20) else 'False', self.irq_DF))
        print("IRQ - Data Sent_______{}    Data Sent____________{}".format(
            '_True' if not bool(self._config & 0x10) else 'False', self.irq_DS))
        print("TX FIFO full__________{}    TX FIFO empty________{}".format(
            '_True' if bool(self.tx_full) else 'False', bool(self.fifo(True, True))))
        print("RX FIFO full__________{}    RX FIFO empty________{}".format(
            '_True' if bool(self._fifo & 2) else 'False', bool(self._fifo & 1)))
        print("Ask no ACK_________{}    Custom ACK Payload___{}".format(
            '_Allowed' if bool(self._features & 1) else 'Disabled',
            'Enabled' if self.ack else 'Disabled'))
        print("Dynamic Payloads___{}    Auto Acknowledgment__{}".format(
            '_Enabled' if self.dynamic_payloads else 'Disabled',
            'Enabled' if self.auto_ack else 'Disabled'))
        print("Primary Mode_____________{}    Power Mode___________{}".format(
            'RX' if self.listen else 'TX',
            ('Standby-II' if self.ce.value else 'Standby-I') if self._config & 2 else 'Off'))
        if dump_pipes:
            print('TX address____________', self._tx_address)
            for i, address in enumerate(self._pipes):
                is_open = "( open )" if self._open_pipes & (1 << i) else "(closed)"
                if i <= 1: # print full address
                    print("Pipe", i, is_open, "bound:", address)
                else: # print unique byte + shared bytes = actual address used by radio
                    print("Pipe", i, is_open, "bound:",
                          bytes([self._pipes[i]]) + self._pipes[1][1:])
                if self._open_pipes & (1 << i):
                    print('\t\texpecting', self._payload_widths[i], 'byte static payloads')

    @property
    def dynamic_payloads(self):
        """This `bool` attribute controls the nRF24L01's dynamic payload length feature.

        - `True` enables nRF24L01's dynamic payload length feature. The `payload_length`
          attribute is ignored when this feature is enabled.
        - `False` disables nRF24L01's dynamic payload length feature. Be sure to adjust
          the `payload_length` attribute accordingly when `dynamic_payloads` feature is disabled.
        """
        return bool(self._dyn_pl and (self._features & 4))

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        assert isinstance(enable, (bool, int))
        self._features = self._reg_read(FEATURE)  # refresh data
        # save changes to registers(& their shadows)
        if self._features & 4 != enable:  # if not already
            # throw a specific global flag for enabling dynamic payloads
            self._features = (self._features & 3) | (enable << 2)
            self._reg_write(FEATURE, self._features)
        #  0x3F == all pipes have enabled dynamic payloads
        self._dyn_pl = 0x3F if enable else 0
        self._reg_write(DYNPD, self._dyn_pl)

    @property
    def payload_length(self):
        """This `int` attribute specifies the length (in bytes) of payload that is regarded,
        meaning "how big of a payload should the radio care about?" If the `dynamic_payloads`
        attribute is enabled, this attribute has no affect. When `dynamic_payloads` is disabled,
        this attribute is used to specify the payload length when entering RX mode.

        A valid input value must be an `int` in range [1,32]. Otherwise a `ValueError` exception is
        thrown. Default is set to the nRF24L01's maximum of 32.

        .. note:: When `dynamic_payloads` is disabled during transmissions:

            - Payloads' size of greater than this attribute's value will be truncated to match.
            - Payloads' size of less than this attribute's value will be padded with zeros to
              match.
        """
        return self._payload_length

    @payload_length.setter
    def payload_length(self, length):
        # max payload size is 32 bytes
        if not length or length <= 32:
            # save for access via getter property
            self._payload_length = length
        else:
            raise ValueError(
                "{}: payload length can only be set in range [1,32] bytes".format(length))

    @property
    def auto_ack(self):
        """This `bool` attribute controls the nRF24L01's automatic acknowledgment feature.

        - `True` enables automatic acknowledgment packets. The CRC (cyclic redundancy checking)
          is enabled automatically by the nRF24L01 if the `auto_ack` attribute is enabled (see also
          `crc` attribute).
        - `False` disables automatic acknowledgment packets. The `crc` attribute will
          remain unaffected (remains enabled) when disabling the `auto_ack` attribute.
        """
        return self._aa

    @auto_ack.setter
    def auto_ack(self, enable):
        assert isinstance(enable, (bool, int))
        # the following 0x3F == enabled auto_ack on all pipes
        self._aa = 0x3F if enable else 0
        self._reg_write(EN_AA, self._aa)  # 1 == EN_AA register for ACK feature
        # nRF24L01 automatically enables CRC if ACK packets are enabled in the FEATURE register

    @property
    def ack(self):
        """This `bool` attribute represents the status of the nRF24L01's capability to use custom
        payloads as part of the automatic acknowledgment (ACK) packet. Use this attribute to
        set/check if the custom ACK payloads feature is enabled.

        - `True` enables the use of custom ACK payloads in the ACK packet when responding to
          receiving transmissions. As `dynamic_payloads` and `auto_ack` attributes are required for
          this feature to work, they are automatically enabled as needed.
        - `False` disables the use of custom ACK payloads. Disabling this feature does not disable
          the `auto_ack` and `dynamic_payloads` attributes (they work just fine without this
          feature).
        """
        return bool((self._features & 2) and self.auto_ack and self.dynamic_payloads)

    @ack.setter
    def ack(self, enable):
        assert isinstance(enable, (bool, int))
        # we need to throw the EN_ACK_PAY flag in the FEATURES register accordingly on both
        # TX & RX nRF24L01s
        if self.ack != enable: # if enabling
            self.auto_ack = True  # ensure auto_ack feature is enabled
            # dynamic_payloads required for custom ACK payloads
            self._dyn_pl = 0x3F
            self._reg_write(DYNPD, self._dyn_pl)
        else:
            # setting auto_ack feature automatically updated the _features attribute, so
            self._features = self._reg_read(FEATURE)  # refresh data here
        self._features = (self._features & 5) | (6 if enable else 0)
        self._reg_write(FEATURE, self._features)

    def load_ack(self, buf, pipe_number):
        """This allows the MCU to specify a payload to be allocated into the TX FIFO buffer for use
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
        """
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of"
                             "\nat least 1 and no greater than 32")
        # only prepare payload if the auto_ack attribute is enabled and ack[0] is not None
        if not self.ack:
            self.ack = True
        if not self.tx_full:
            # 0xA8 = W_ACK_PAYLOAD
            self._reg_write_bytes(0xA8 | pipe_number, buf)
            return True  # payload was loaded
        return False  # payload wasn't loaded

    def read_ack(self):
        """Allows user to read the automatic acknowledgement (ACK) payload (if any) when nRF24L01
        is in TX mode. This function is called from a blocking `send()` call if the `ack` attribute
        is enabled. Alternatively, this function can be called directly in case of calling the
        non-blocking `write()` function during asychronous applications.

        .. warning:: In the case of asychronous applications, this function will do nothing if the
            status flags are cleared after calling `write()` and before calling this function. See
            also the `ack`, `dynamic_payloads`, and `auto_ack` attributes as they must be enabled
            to use custom ACK payloads.
        """
        if self.any():  # check RX FIFO for ACK packet's payload
            return self.recv()
        return None

    @property
    def data_rate(self):
        """This `int` attribute specifies the nRF24L01's frequency data rate for OTA (over the air)
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
        """
        self._rf_setup = self._reg_read(RF_SETUP)  # refresh data
        return (2 if self._rf_setup & 0x28 == 8 else 250) if self._rf_setup & 0x28 else 1

    @data_rate.setter
    def data_rate(self, speed):
        # nRF24L01+ must be in a standby or power down mode before writing to the configuration
        # registers.
        if speed in (1, 2, 250):
            if self.data_rate != speed:
                speed = 0 if speed == 1 else (8 if speed == 2 else 0x20)
            # save changes to register(& its shadow)
            self._rf_setup = self._rf_setup & 0xD7 | speed
            self._reg_write(RF_SETUP, self._rf_setup)
        else:
            raise ValueError(
                "data rate must be one of the following ([M,M,K]bps): 1, 2, 250")

    @property
    def channel(self):
        """This `int` attribute specifies the nRF24L01's frequency (in 2400 + `channel` MHz).

        A valid input value must be in range [0, 125] (that means [2.4, 2.525] GHz). Otherwise a
        `ValueError` exception is thrown. Default is 76.
        """
        return self._reg_read(RF_CH)

    @channel.setter
    def channel(self, channel):
        if 0 <= channel <= 125:
            self._channel = channel
            self._reg_write(RF_CH, channel)  # always writes to reg
        else:
            raise ValueError("channel acn only be set in range [0,125]")

    @property
    def crc(self):
        """This `int` attribute specifies the nRF24L01's CRC (cyclic redundancy checking) encoding
        scheme in terms of byte length.

        A valid input value is in range [0,2]:

        - ``0`` disables CRC
        - ``1`` enables CRC encoding scheme using 1 byte
        - ``2`` enables CRC encoding scheme using 2 bytes

        Any invalid input throws a `ValueError` exception. Default is enabled using 2 bytes.

        .. note:: The nRF24L01 automatically enables CRC if automatic acknowledgment feature is
            enabled (see `auto_ack` attribute).
        """
        self._config = self._reg_read(CONFIG)  # refresh data
        return max(0, ((self._config & 12) >> 2) - 1)  # this works

    @crc.setter
    def crc(self, length):
        if 0 <= length <= 2:
            if self.crc != length:
                length = (length + 1) << 2 if length else 0  # this works
                # save changes to register(& its Shadow)
                self._config = self._config & 0x73 | length
                self._reg_write(0, self._config)
        else:
            raise ValueError(
                "CRC byte length must be an int equal to 0 (off), 1, or 2")

    @property
    def power(self):
        """This `bool` attribute controls the power state of the nRF24L01. This is exposed for
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
        """
        return bool(self._config & 2)

    @power.setter
    def power(self, is_on):
        assert isinstance(is_on, (bool, int))
        # capture surrounding flags and set PWR_UP flag according to is_on boolean
        self._config = self._reg_read(CONFIG)  # refresh data
        if self.power != is_on:
            # only write changes
            self._config = (self._config & 0x7d) | (
                is_on << 1)  # doesn't affect TX?RX mode
            self._reg_write(CONFIG, self._config)
            # power up/down takes < 150 µs + 4 µs
            time.sleep(0.00016)

    @property
    def arc(self):
        """"This `int` attribute specifies the nRF24L01's number of attempts to re-transmit TX
        payload when acknowledgment packet is not received. The nRF24L01 does not attempt to
        re-transmit if `auto_ack` attribute is disabled.

        A valid input value must be in range [0,15]. Otherwise a `ValueError` exception is thrown.
        Default is set to 3.
        """
        self._setup_retr = self._reg_read(SETUP_RETR)  # refresh data
        return self._setup_retr & 0x0f

    @arc.setter
    def arc(self, count):
        if 0 <= count <= 15:
            if self.arc & 0x0F != count:  # write only if needed
                # save changes to register(& its shadow)
                self._setup_retr = (self._setup_retr & 0xF0) | count
                self._reg_write(SETUP_RETR, self._setup_retr)
        else:
            raise ValueError(
                "automatic re-transmit count(/attempts) must in range [0,15]")

    @property
    def ard(self):
        """This `int` attribute specifies the nRF24L01's delay (in µs) between attempts to
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
        """
        self._setup_retr = self._reg_read(SETUP_RETR)  # refresh data
        return ((self._setup_retr & 0xf0) >> 4) * 250 + 250

    @ard.setter
    def ard(self, delta_t):
        if 250 <= delta_t <= 4000 and delta_t % 250 == 0:
            # set new ARD data and current ARC data to register
            if self.ard != delta_t:  # write only if needed
                # save changes to register(& its Shadow)
                self._setup_retr = (int((delta_t - 250) / 250)
                                    << 4) | (self._setup_retr & 0x0F)
                self._reg_write(SETUP_RETR, self._setup_retr)
        else:
            raise ValueError("automatic re-transmit delay can only be a multiple of 250 in range "
                             "[250,4000]")

    @property
    def pa_level(self):
        """This `int` attribute specifies the nRF24L01's power amplifier level (in dBm). Higher
        levels mean the transmission will cover a longer distance. Use this attribute to tweak the
        nRF24L01 current consumption on projects that don't span large areas.

        A valid input value is:

        - ``-18`` sets the nRF24L01's power amplifier to -18 dBm (lowest)
        - ``-12`` sets the nRF24L01's power amplifier to -12 dBm
        - ``-6`` sets the nRF24L01's power amplifier to -6 dBm
        - ``0`` sets the nRF24L01's power amplifier to 0 dBm (highest)

        Any invalid input throws a `ValueError` exception. Default is 0 dBm.
        """
        self._rf_setup = self._reg_read(RF_SETUP)  # refresh data
        return (3 - ((self._rf_setup & RF_SETUP) >> 1)) * -6

    @pa_level.setter
    def pa_level(self, power):
        # nRF24L01+ must be in a standby or power down mode before writing to the
        # configuration registers.
        if power in (-18, -12, -6, 0):
            power = (3 - int(power / -6)) * 2  # this works
            # save changes to register (& its shadow)
            self._rf_setup = (self._rf_setup & 0xF9) | power
            self._reg_write(RF_SETUP, self._rf_setup)
        else:
            raise ValueError(
                "power amplitude must be one of the following (dBm): -18, -12, -6, 0")

    @property
    def tx_full(self):
        """An attribute to represent the nRF24L01's status flag signaling that the TX FIFO buffer
        is full. (read-only)

        Calling this does not execute an SPI transaction. It only exposes that latest data
        contained in the STATUS byte that's always returned from any SPI transactions with the
        nRF24L01. Use the `update()` function to manually refresh this data when needed.

        :returns:
            * `True` for TX FIFO buffer is full
            * `False` for TX FIFO buffer is not full. This doesn't mean the TX FIFO buffer is
              empty.
        """
        return bool(self._status & 1)

    def update(self):
        """This function is only used to get an updated status byte over SPI from the nRF24L01 and
        is exposed to the MCU for asynchronous applications. Refreshing the status byte is vital to
        checking status of the interrupts, RX pipe number related to current RX payload, and if the
        TX FIFO buffer is full. This function returns nothing, but internally updates the `irq_DR`,
        `irq_DS`, `irq_DF`, and `tx_full` attributes. Internally this is a helper function to
        `pipe()`, `send()`, and `resend()` functions"""
        # perform non-operation to get status byte
        # should be faster than reading the STATUS register
        self._reg_write(0xFF)

    def resend(self):
        """Use this function to maunally re-send the previously failed-to-transmit payload in the
        top level (first out) of the TX FIFO buffer.

        .. note:: The nRF24L01 normally removes a payload from the TX FIFO buffer after successful
            transmission, but not when this function is called. The payload (successfully
            transmitted or not) will remain in the TX FIFO buffer until `flush_tx()` is called to
            remove them. Alternatively, using this function also allows the failed payload to be
            over-written by using `send()` or `write()` to load a new payload.
        """
        if not self.fifo(True, True):  # also updates _fifo attribute
            if self.irq_DF or self.irq_DS:  # check and clear flags
                self.clear_status_flags(False)  # clears TX related flags only
            result = None
            if self._features & 1 == 0:  # ensure REUSE_TX_PL optional command is allowed
                self._features = self._features & 0xFE | 1  # set EN_DYN_ACK flag high
                self._reg_write(FEATURE, self._features)
            # payload will get re-used. This command tells the radio not pop TX payload from
            # FIFO on success
            self._reg_write(0xE3)  # 0xE3 == REUSE_TX_PL command
            self.ce.value = 0  # this cycles the CE pin to re-enable transmission of re-used payload
            self.ce.value = 1
            time.sleep(0.00001)  # mandated 10 µs pulse
            # now get result
            self.ce.value = 0  # only send one payload
            start = time.monotonic()
            # timeout calc assumes 32 byte payload (no way to tell when payload has already been
            # loaded into TX FIFO)
            pl_coef = 1 + bool(self.auto_ack)
            pl_len = 1 + self._addr_len + \
                (max(0, ((self._config & 12) >> 2) - 1))
            bitrate = ((2000000 if self._rf_setup & 0x28 == 8 else 250000)
                       if self._rf_setup & 0x28 else 1000000) / 8
            stby2active = (1 + pl_coef) * 0.00013
            t_irq = 0.0000082 if not self._rf_setup & 0x28 else 0.000006
            t_retry = (((self._setup_retr & 0xf0) >> 4) * 250 +
                       380) * (self._setup_retr & 0x0f) / 1000000
            timeout = pl_coef * (((8 * (32 + pl_len)) + 9) /
                                 bitrate) + stby2active + t_irq + t_retry
            while not self.irq_DS and not self.irq_DF and (time.monotonic() - start) < timeout:
                self.update()  # perform Non-operation command to get status byte (should be faster)
            if self.irq_DS or self.irq_DF:  # transmission done
                # get status flags to detect error
                result = bool(self.irq_DS)
            # read ack payload clear status flags, then power down
            if self.ack and self.irq_DS:
                # get and save ACK payload to self.ack if user wants it
                result = self.read_ack()  # save reply in input buffer
                if result is None:  # can't return empty handed
                    result = b'NO ACK RETURNED'
            self.clear_status_flags(False)  # only TX related IRQ flags
            return result

    def write(self, buf=None, ask_no_ack=False):
        """This non-blocking function (when used as alternative to `send()`) is meant for
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
            application, or it is managed by using `send()` instead of this function. If the CE pin
            remains HIGH for longer than 10 µs, then the nRF24L01 will continue to transmit all
            payloads found in the TX FIFO buffer.

        .. warning:: A note paraphrased from the `nRF24L01+ Specifications Sheet <https://www.
            sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_:

            It is important to NEVER to keep the nRF24L01+ in TX mode for more than 4 ms at a time.
            If the [`auto_ack` and `dynamic_payloads`] features are enabled, nRF24L01+ is never in
            TX mode longer than 4 ms.

        .. tip:: Use this function at your own risk. Because of the underlying `"Enhanced
            ShockBurst Protocol" <https://www.sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132607>`_, disobeying the 4
            ms rule is easily avoided if you enable the `dynamic_payloads` and `auto_ack`
            attributes. Alternatively, you MUST use interrupt flags or IRQ pin with user defined
            timer(s) to AVOID breaking the 4 ms rule. If the `nRF24L01+ Specifications Sheet
            explicitly states this <https://www.sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_, we have to assume
            radio damage or misbehavior as a result of disobeying the 4 ms rule. See also `table 18
            in the nRF24L01 specification sheet <https://www.sparkfun.com/datasheets/Components/SMD/
            nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1123001>`_ for calculating
            necessary transmission time (these calculations are used in the `send()` function).
        """
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of"
                             "\nat least 1 and no greater than 32")
        self.clear_status_flags(False)  # only TX related IRQ flags

        if not self.power or (self._config & 1):  # ready radio if it isn't yet
            # also ensures tx mode
            self._config = (self._reg_read(CONFIG) & 0x7c) | 2
            self._reg_write(0, self._config)
            # power up/down takes < 150 µs + 4 µs
            time.sleep(0.00016)

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
            # write appropriate command with payload
            self._reg_write_bytes(0xB0, buf)
            # print("payload doesn't want acknowledgment")
        else:  # payload may require acknowledgment
            # 0xA0 = W_TX_PAYLOAD; this command works with auto_ack on or off
            # write appropriate command with payload
            self._reg_write_bytes(0xA0, buf)
            # print("payload does want acknowledgment")
        # enable radio comms so it can send the data by starting the mandatory minimum 10 µs pulse
        # on CE. Let send() measure this pulse for blocking reasons
        self.ce.value = 1  # re-used payloads start with this as well
        # radio will automatically go to standby-II after transmission while CE is still HIGH only
        # if dynamic_payloads and auto_ack are enabled

    def flush_rx(self):
        """A helper function to flush the nRF24L01's internal RX FIFO buffer. (write-only)

        .. note:: The nRF24L01 RX FIFO is 3 level stack that holds payload data. This means that
            there can be up to 3 received payloads (each of a maximum length equal to 32 bytes)
            waiting to be read (and popped from the stack) by `recv()` or `read_ack()`. This
            function clears all 3 levels.
        """
        self._reg_write(0xE2)

    def flush_tx(self):
        """A helper function to flush the nRF24L01's internal TX FIFO buffer. (write-only)

        .. note:: The nRF24L01 TX FIFO is 3 level stack that holds payload data. This means that
            there can be up to 3 payloads (each of a maximum length equal to 32 bytes) waiting to
            be transmit by `send()`, `resend()` or `write()`. This function clears all 3 levels. It
            is worth noting that the payload data is only popped from the TX FIFO stack upon
            successful transmission (see also `resend()` as the handling of failed transmissions
            can be altered).
        """
        self._reg_write(0xE1)

    def fifo(self, tx=False, empty=None):
        """This provides some precision determining the status of the TX/RX FIFO buffers.
        (read-only)

        :param bool tx:
            * `True` means information returned is about the TX FIFO buffer.
            * `False` means information returned is about the RX FIFO buffer. This parameter
              defaults to `False` when not specified.
        :param bool empty:
            * `True` tests if the specified FIFO buffer is empty.
            * `False` tests if the specified FIFO buffer is full.
            * `None` (when not specified) returns a 2 bit number representing both empty (bit 1) &
              full (bit 0) tests related to the FIFO buffer specified using the ``tx`` parameter.
        :returns:
            * A `bool` answer to the question:
              "Is the [TX/RX]:[`True`/`False`] FIFO buffer [empty/full]:[`True`/`False`]?
            * If the ``empty`` parameter is not specified: an `int` in range [0,2] for which:

              - ``1`` means the specified FIFO buffer is full
              - ``2`` means the specified FIFO buffer is empty
              - ``0`` means the specified FIFO buffer is neither full nor empty
        """
        if (empty is None and isinstance(tx, (bool, int))) or \
                (isinstance(empty, (bool, int)) and isinstance(tx, (bool, int))):
            self._fifo = self._reg_read(FIFO)  # refresh the data
            if empty is None:
                return (self._fifo & (0x30 if tx else 0x03)) >> (4 * tx)
            return bool(self._fifo & ((2 - empty) << (4 * tx)))
        raise ValueError("Argument 1 ('tx') must always be a bool or int. Argument 2 ('empty')"
                         ", if specified, must be a bool or int")

    def pipe(self):
        """This function returns information about the data pipe that received the next available
        payload in the RX FIFO buffer.

        :returns:
            - `None` if there is no payload in RX FIFO.
            - The `int` identifying pipe number [0,5] that received the next available payload in
              the RX FIFO buffer.
        """
        self.update()  # perform Non-operation command to get status byte (should be faster)
        pipe = (self._status & 0x0E) >> 1  # 0x0E==RX_P_NO
        if pipe <= 5:  # is there data in RX FIFO?
            return pipe
        return None  # RX FIFO is empty
