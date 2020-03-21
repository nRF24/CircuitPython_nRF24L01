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
# pylint: disable=too-many-lines
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

# documentation lives in api.rst to save space on M0
# pylint: disable=missing-class-docstring,missing-function-docstring
class RF24:
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
                 irq_dr=True,
                 irq_ds=True,
                 irq_df=True):
        self._payload_length = payload_length  # inits internal attribute
        self.payload_length = payload_length
        # last address assigned to pipe0 for reading. init to None
        self._fifo = 0
        self._status = 0
        # init shadow copy of RX addresses for all pipes
        self._pipes = [b'', b'', 0, 0, 0, 0]
        self._payload_widths = [0, 0, 0, 0, 0, 0] # payload_length specific to each pipe
        # shadow copy of last RX_ADDR written to pipe 0
        self._pipe0_read_addr = None # needed as open_tx_pipe() appropriates pipe 0 for ACK
        # init the _open_pipes attribute (reflects only RX state on each pipe)
        self._open_pipes = 0  # <- means all pipes closed
        # init the SPI bus and pins
        self._spi = SPIDevice(spi, chip_select=csn, baudrate=1250000)

        # store the ce pin
        self.ce_pin = ce
        # reset ce.value & disable the chip comms
        self.ce_pin.switch_to_output(value=False)
        # if radio is powered up and CE is LOW: standby-I mode
        # if radio is powered up and CE is HIGH: standby-II mode

        # NOTE per spec sheet: nRF24L01+ must be in a standby or power down mode before writing
        # to the configuration register
        # configure the CONFIG register:IRQ(s) config, setup CRC feature, and trigger standby-I &
        # TX mode (the "| 2")
        if 0 <= crc <= 2:
            self._config = ((not irq_dr) << 6) | ((not irq_ds) << 5) | ((not irq_df) << 4) | \
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

        # capture all pipe's RX addresses & the TX address from last usage
        for i in range(6):
            if i < 2:
                self._pipes[i] = self._reg_read_bytes(RX_ADDR + i)
            else:
                self._pipes[i] = self._reg_read(RX_ADDR + i)

        # shadow copy of the TX_ADDR
        self._tx_address = self._reg_read_bytes(TX_ADDR)

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
            self.ce_pin.value = 0  # ensure standby-I mode to write to CONFIG register
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
        self.power = 0
        return False

    # pylint: disable=no-member
    def _reg_read(self, reg):
        buf = bytearray(2)  # 2 = 1 status byte + 1 byte of returned content
        with self._spi as spi:
            time.sleep(0.005)  # time for CSN to settle
            spi.readinto(buf, write_value=reg)
        self._status = buf[0]  # save status byte
        return buf[1]  # drop status byte and return the rest

    def _reg_read_bytes(self, reg, buf_len=5):
        # allow an extra byte for status data
        buf = bytearray(buf_len + 1)
        with self._spi as spi:
            time.sleep(0.005)  # time for CSN to settle
            spi.readinto(buf, write_value=reg)
        self._status = buf[0]  # save status byte
        return buf[1:]  # drop status byte and return the rest

    def _reg_write_bytes(self, reg, out_buf):
        out_buf = bytes([0x20 | reg]) + out_buf
        in_buf = bytearray(len(out_buf))
        with self._spi as spi:
            time.sleep(0.005)  # time for CSN to settle
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]  # save status byte

    def _reg_write(self, reg, value=None):
        if value is None:
            out_buf = bytes([reg])
        else:
            out_buf = bytes([0x20 | reg, value])
        in_buf = bytearray(len(out_buf))
        with self._spi as spi:
            time.sleep(0.005)  # time for CSN to settle
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]  # save status byte
    # pylint: enable=no-member

    @property
    def address_length(self):
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
        if self.ce_pin.value:
            self.ce_pin.value = 0

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
        self.ce_pin.value = 1 # radio begins listening after CE pulse is > 130 µs
        time.sleep(0.00013) # ensure pulse is > 130 µs
        # nRF24L01 has just entered active RX + standby-II mode

    def _stop_listening(self):
        # ensure radio is in standby-I mode
        if self.ce_pin.value:
            self.ce_pin.value = 0
        # set radio in TX mode as recommended behavior per spec sheet.
        self._config = self._config & 0xFE  # does not put radio to sleep
        self._reg_write(CONFIG, self._config)
        # mandated wait for transitioning between modes RX/TX
        time.sleep(0.00016)
        # exits while still in Standby-I (low current & no transmissions)

    def any(self):
        # 0x60 == R_RX_PL_WID command
        return self._reg_read(0x60)  # top-level payload length

    def recv(self):
        if not self.irq_dr:
            return None
        # buffer size = current payload size
        curr_pl_size = self.payload_length if not self.dynamic_payloads else self.any()
        # get the data (0x61 = R_RX_PAYLOAD)
        result = self._reg_read_bytes(0x61, curr_pl_size)
        # clear only Data Ready IRQ flag for accurate RX FIFO read operations
        self.clear_status_flags(True, False, False)
        # return all available bytes from payload
        return result

    def send(self, buf, ask_no_ack=False, force_retry=0):
        # ensure power down/standby-I for proper manipulation of PWR_UP & PRIM_RX bits in
        # CONFIG register
        self.ce_pin.value = 0
        self.flush_tx()  # be sure there is space in the TX FIFO
        # using spec sheet calculations:
        # timeout total = T_upload + 2 * stby2active + T_overAir + T_ack + T_irq + T_retry
        # T_upload = payload length (in bits) / spi data rate (bits per second =
        # baudrate / bits per byte)
        # T_upload is finished before timeout begins
        # T_download == T_upload, however RX devices spi settings must match TX's for
        #   accurate calc
        # let 2 * stby2active (in µs) ~= (2 + (1 if getting ack else 0)) * 130
        # let T_ack = T_overAir as the payload size is the only distictive variable between
        #   the 2
        # T_overAir (in seconds) = ( 8 (bits/byte) * (1 byte preamble + address length +
        #   payload length + crc length) + 9 bit packet ID ) / RF data rate (in bits/sec)
        # T_irq (in seconds) = (0.0000082 if self.data_rate == 1 else 0.000006)
        # T_retry (in microseconds)= (arc * ard)
        need_ack = self._setup_retr & 0x0f and not ask_no_ack
        packet_data = 1 + self._addr_len + (max(0, ((self._config & 12) >> 2) - 1))
        bitrate = ((2000000 if self._rf_setup & 0x28 == 8 else 250000)
                   if self._rf_setup & 0x28 else 1000000) / 8
        t_ack = (((packet_data + 32) * 8 + 9) / bitrate) if need_ack else 0  # assumes 32-byte ACK
        stby2active = (1 + (need_ack)) * 0.00013
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
            for i, b in enumerate(buf):
                timeout = (((8 * (len(b) + packet_data)) + 9) / bitrate) + \
                    stby2active + t_irq + t_retry + t_ack + \
                    (len(b) * 64 / self._spi.baudrate)  # t_upload
                self.clear_status_flags(False) # clear TX related flags
                self.write(b, ask_no_ack)  # clears TX flags on entering
                time.sleep(0.00001)
                self.ce_pin.value = 0
                self._wait_for_result(timeout) # now get result
                if self._setup_retr & 0x0f and self.irq_df:
                    # need to clear for continuing transmissions
                    result.append(self._attempt2resend(force_retry))
                else:  # if auto_ack is disabled
                    if self.ack and self.irq_dr and not ask_no_ack:
                        result.append(self.recv()) # save ACK payload & clears RX flag
                    else:
                        result.append(self.irq_ds)  # will always be True (in this case)
            return result
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of"
                             "\nat least 1 and no greater than 32")
        # T_upload is done before timeout begins (after payload write action AKA upload)
        timeout = (((8 * (len(buf) + packet_data)) + 9) /
                   bitrate) + stby2active + t_irq + t_retry + t_ack
        self.write(buf, ask_no_ack)  # init using non-blocking helper
        time.sleep(0.00001)  # ensure CE pulse is >= 10 µs
        # if pulse is stopped here, the nRF24L01 only handles the top level payload in the FIFO.
        # we could hold CE HIGH to continue processing through the rest of the TX FIFO bound for
        # the address passed to open_tx_pipe()
        self.ce_pin.value = 0 # go to Standby-I power mode (power attribute still True)
        self._wait_for_result(timeout)
        if self._setup_retr & 0x0f and self.irq_df:
            # if auto-retransmit is on and last attempt failed
            result = self._attempt2resend(force_retry)
        else:  # if auto_ack is disabled
            if self.ack and self.irq_dr and not ask_no_ack:
                result = self.recv() # save ACK payload & clears RX flag
            else:
                result = self.irq_ds  # will always be True (in this case)
            self.clear_status_flags(False)  # only TX related IRQ flags
        return result

    @property
    def irq_dr(self):
        return bool(self._status & 0x40)

    @property
    def irq_ds(self):
        return bool(self._status & 0x20)

    @property
    def irq_df(self):
        return bool(self._status & 0x10)

    def clear_status_flags(self, data_recv=True, data_sent=True, data_fail=True):
        # 0x07 = STATUS register; only bits 6 through 4 are write-able
        self._reg_write(0x07, (data_recv << 6) | (
            data_sent << 5) | (data_fail << 4))

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        self._config = self._reg_read(CONFIG)  # refresh data
        # save to register and update local copy of pwr & RX/TX modes' flags
        self._config = (self._config & 0x0F) | (not data_fail << 4) | (not data_sent << 5) | \
            (not data_recv << 6)
        self._reg_write(CONFIG, self._config)

    def what_happened(self, dump_pipes=False):
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
        print("Packets lost on current channel_____________________{}".format(
            (watchdog & 0xF0) >> 4))
        print("Retry attempts made for last transmission___________{}".format(watchdog & 0x0F))
        print("IRQ - Data Ready______{}    Data Ready___________{}".format(
            '_True' if not bool(self._config & 0x40) else 'False', self.irq_dr))
        print("IRQ - Data Fail_______{}    Data Failed__________{}".format(
            '_True' if not bool(self._config & 0x20) else 'False', self.irq_df))
        print("IRQ - Data Sent_______{}    Data Sent____________{}".format(
            '_True' if not bool(self._config & 0x10) else 'False', self.irq_ds))
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
            ('Standby-II' if self.ce_pin.value else 'Standby-I') if self._config & 2 else 'Off'))
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
    def arc(self):
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
    def auto_ack(self):
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
        return self.recv()

    @property
    def data_rate(self):
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
    def pa_level(self):
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
    def rpd(self):
        return bool(self._reg_read(0x09))

    @property
    def tx_full(self):
        return bool(self._status & 1)

    def update(self):
        # perform non-operation to get status byte
        # should be faster than reading the STATUS register
        self._reg_write(0xFF)

    def resend(self):
        result = False
        if not self.fifo(True, True):  # is there a pre-existing payload
            self.clear_status_flags(False) # clear TX related flags
            # indicate existing payload will get re-used.
            # This command tells the radio not pop TX payload from FIFO on success
            self._reg_write(0xE3)  # 0xE3 == REUSE_TX_PL command
            # timeout calc assumes 32 byte payload because there is no way to tell when payload
            # has already been loaded into TX FIFO; also assemues 32-byte ACK if needed
            pl_coef = 1 + bool(self._setup_retr & 0x0f)
            pl_len = 1 + self._addr_len + (
                max(0, ((self._config & 12) >> 2) - 1))
            bitrate = ((2000000 if self._rf_setup & 0x28 == 8 else 250000)
                       if self._rf_setup & 0x28 else 1000000) / 8
            stby2active = (1 + pl_coef) * 0.00013
            t_irq = 0.0000082 if not self._rf_setup & 0x28 else 0.000006
            t_retry = (((self._setup_retr & 0xf0) >> 4) * 250 +
                       380) * (self._setup_retr & 0x0f) / 1000000
            timeout = pl_coef * (((8 * (32 + pl_len)) + 9) / bitrate) + \
                stby2active + t_irq + t_retry
            # cycle the CE pin to re-enable transmission of re-used payload
            self.ce_pin.value = 0
            self.ce_pin.value = 1
            time.sleep(0.00001)
            self.ce_pin.value = 0  # only send one payload
            self._wait_for_result(timeout)
            result = self.irq_ds
            if self.ack and self.irq_dr:  # check if there is an ACK payload
                result = self.recv()  # save ACK payload & clear RX related IRQ flag
            self.clear_status_flags(False)  # only clear TX related IRQ flags
        return result

    def write(self, buf, ask_no_ack=False):
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of"
                             "\nat least 1 and no greater than 32")
        self.clear_status_flags(False)  # only TX related IRQ flags
        if self._config & 3 != 2:  # ready radio if it isn't yet
            # ensures tx mode & powered up
            self._config = (self._reg_read(CONFIG) & 0x7c) | 2
            self._reg_write(CONFIG, self._config)
            time.sleep(0.00016)  # power up/down takes < 150 µs + 4 µs
        # pad out or truncate data to fill payload_length if dynamic_payloads == False
        if not self.dynamic_payloads:
            if len(buf) < self.payload_length:
                for _ in range(self.payload_length - len(buf)):
                    buf += b'\x00'
            elif len(buf) > self.payload_length:
                buf = buf[:self.payload_length]
        # now upload the payload accordingly with appropriate command
        if ask_no_ack:  # payload doesn't want acknowledgment
            # ensure this feature is allowed by setting EN_DYN_ACK flag in the FEATURE register
            if self._features & 1 == 0:
                self._features = self._features & 0xFE | 1  # set EN_DYN_ACK flag high
                self._reg_write(FEATURE, self._features)
        # write appropriate command with payload
        # 0xA0 = W_TX_PAYLOAD; 0xB0 = W_TX_PAYLOAD_NO_ACK
        self._reg_write_bytes(0xA0 | (ask_no_ack << 4), buf)
        # enable radio comms so it can send the data by starting the mandatory minimum 10 µs pulse
        # on CE. Let send() or resend() measure this pulse for blocking reasons
        self.ce_pin.value = 1
        # while CE is still HIGH only if dynamic_payloads and auto_ack are enabled
        # automatically goes to standby-II after successful TX of all payloads in the FIFO

    def flush_rx(self):
        self._reg_write(0xE2)

    def flush_tx(self):
        self._reg_write(0xE1)

    def fifo(self, about_tx=False, check_empty=None):
        if (check_empty is None and isinstance(about_tx, (bool, int))) or \
                (isinstance(check_empty, (bool, int)) and isinstance(about_tx, (bool, int))):
            self._fifo = self._reg_read(FIFO)  # refresh the data
            if check_empty is None:
                return (self._fifo & (0x30 if about_tx else 0x03)) >> (4 * about_tx)
            return bool(self._fifo & ((2 - check_empty) << (4 * about_tx)))
        raise ValueError("Argument 1 ('about_tx') must always be a bool or int. Argument 2"
                         " ('check_empty'), if specified, must be a bool or int")

    def pipe(self):
        self.update()  # perform Non-operation command to get status byte (should be faster)
        result = (self._status & 0x0E) >> 1  # 0x0E==RX_P_NO
        if result <= 5:  # is there data in RX FIFO?
            return result
        return None  # RX FIFO is empty

    def address(self, index=-1):
        if index > 5:
            raise IndexError("index {} is out of bounds [0,5]".format(index))
        if index < 0:
            return self._tx_address
        if index <= 1:
            return self._pipes[index]
        return bytes(self._pipes[index]) + self._pipes[1][1:]

    def _wait_for_result(self, timeout):
        start = time.monotonic()
        while not self.irq_ds and not self.irq_df and (time.monotonic() - start) < timeout:
            self.update()  # perform Non-operation command to get status byte (should be faster)
            # print('status: DR={} DS={} DF={}'.format(self.irq_dr, self.irq_ds, self.irq_df))

    def _attempt2resend(self, attempts):
        retry = False
        for _ in range(attempts):
            # resend() clears flags upon entering and exiting
            retry = self.resend()
            if retry is None or retry:
                break # retry succeeded
        return retry
