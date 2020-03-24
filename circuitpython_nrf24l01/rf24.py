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
"""rf24 module containing the base class RF24"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import time
from micropython import const
from adafruit_bus_device.spi_device import SPIDevice

# nRF24L01 registers
# pylint: disable=bad-whitespace
CONFIG     = const(0x00) # IRQ, CRC, PWR & RX/TX roles
EN_AA      = const(0x01) # auto-ACK
EN_RX      = const(0x02) # open/close pipes
SETUP_AW   = const(0x03) # address width
SETUP_RETR = const(0x04) # auto-retry count & delay
RF_CH      = const(0x05) # channel
RF_SETUP   = const(0x06) # RF Power Amplifier & Data Rate
RX_ADDR    = const(0x0a) # RX pipe addresses == [0,5]:[0x0a:0x0f]
RX_PW      = const(0x11) # RX payload widths on pipes == [0,5]:[0x11,0x16]
FIFO       = const(0x17) # info on both RX/TX FIFOs + re-use payload flag
DYNPD      = const(0x1c) # dynamic payloads
FEATURE    = const(0x1d) # TX flags (dynamic payloads, ACK payloads, & NO_ACK)
TX_ADDR    = const(0x10) # Address used for TX transmissions
# pylint: enable=bad-whitespace

# NOTE expanded documentation lives in api.rst to save space on M0

class RF24:
    """A driver class for the nRF24L01(+) transceiver radios."""
    def __init__(self, spi, csn, ce):
        self._payload_length = 32  # inits internal attribute
        self.payload_length = 32
        # last address assigned to pipe0 for reading. init to None
        self._fifo = 0
        self._status = 0
        # init shadow copy of RX addresses for all pipes
        self._pipes = [b'\xE7' * 5, b'\xC2' * 5, 0, 0, 0, 0]
        self._payload_widths = [32] * 6  # payload_length specific to each pipe
        # shadow copy of last RX_ADDR written to pipe 0
        self._pipe0_read_addr = None # needed as open_tx_pipe() appropriates pipe 0 for ACK
        # init the _open_pipes attribute (reflects only RX state on each pipe)
        self._open_pipes = 0  # 0 = all pipes closed
        self._spi = SPIDevice(spi, chip_select=csn, baudrate=1250000)
        self.ce_pin = ce
        self.ce_pin.switch_to_output(value=False)
        # configure the CONFIG register:
        # 0x0E = IRQs are all enabled, CRC is enabled with 2 bytes, and power up in TX mode
        self._config = 0x0E
        self._reg_write(CONFIG, self._config)  # dump to register
        # check for device presence by verifying nRF24L01 is in TX + standby-I mode
        if self._reg_read(CONFIG) & 3 == 2: # if in TX + standby-I mode
            self.power = False  # power down
        else: # hardware presence check NOT passed
            print(bin(self._reg_read(CONFIG)))
            raise RuntimeError("nRF24L01 Hardware not responding")
        for i in range(6):
            if i < 2:
                self._pipes[i] = self._reg_read_bytes(RX_ADDR + i)
            else:
                self._pipes[i] = self._reg_read(RX_ADDR + i)
        # shadow copy of the TX_ADDR
        self._tx_address = self._reg_read_bytes(TX_ADDR)
        # configure the SETUP_RETR register
        self._setup_retr = 0x53  #ard = 1500; arc = 3
        # configure the RF_SETUP register
        self._rf_setup = 0x06  # 1 Mbps data_rate, and 0 dbm pa_level
        # configure dynamic_payloads & auto_ack for RX operations
        self._dyn_pl = 0x3F  # 0x3F = dynamic_payloads enabled on all pipes
        self._aa = 0x3F  # 0x3F = auto_ack enabled on all pipes
        # configure features for TX operations
        # 5 = enable dynamic_payloads, disable custom ack payloads, and allow ask_no_ack command
        self._features = 5
        self._channel = 76
        self._addr_len = 5

        with self:  # write to registers & power up
            self.ce_pin.value = 0
            self._reg_write(CONFIG, self._config | 1)
            time.sleep(0.000015)
            self.flush_rx()
            self._reg_write(CONFIG, self._config & 0xC)
            time.sleep(0.000015)
            self.flush_tx()
            self.clear_status_flags()

    def __enter__(self):
        self._reg_write(CONFIG, self._config & 0x7C)
        self._reg_write(RF_SETUP, self._rf_setup)
        self._reg_write(EN_RX, self._open_pipes)
        self._reg_write(DYNPD, self._dyn_pl)
        self._reg_write(EN_AA, self._aa)
        self._reg_write(FEATURE, self._features)
        self._reg_write(SETUP_RETR, self._setup_retr)
        for i, address in enumerate(self._pipes):
            if i < 2:
                self._reg_write_bytes(RX_ADDR + i, address)
            else:
                self._reg_write(RX_ADDR + i, address)
            self._reg_write(RX_PW + i, self._payload_widths[i])
        self._reg_write_bytes(TX_ADDR, self._tx_address)
        self.address_length = self._addr_len
        self.channel = self._channel
        return self

    def __exit__(self, *exc):
        self.power = 0
        return False

    # pylint: disable=no-member
    def _reg_read(self, reg):
        buf = bytearray(2)
        with self._spi as spi:
            time.sleep(0.005)
            spi.readinto(buf, write_value=reg)
        self._status = buf[0]
        return buf[1]

    def _reg_read_bytes(self, reg, buf_len=5):
        buf = bytearray(buf_len + 1)
        with self._spi as spi:
            time.sleep(0.005)
            spi.readinto(buf, write_value=reg)
        self._status = buf[0]
        return buf[1:]

    def _reg_write_bytes(self, reg, out_buf):
        out_buf = bytes([0x20 | reg]) + out_buf
        in_buf = bytearray(len(out_buf))
        with self._spi as spi:
            time.sleep(0.005)
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]

    def _reg_write(self, reg, value=None):
        if value is None:
            out_buf = bytes([reg])
        else:
            out_buf = bytes([0x20 | reg, value])
        in_buf = bytearray(len(out_buf))
        with self._spi as spi:
            time.sleep(0.005)
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]
    # pylint: enable=no-member

    @property
    def address_length(self):
        """This `int` attribute specifies the length (in bytes) of addresses
        to be used for RX/TX pipes."""
        return self._reg_read(SETUP_AW) + 2

    @address_length.setter
    def address_length(self, length):
        if 3 <= length <= 5:
            self._addr_len = int(length)
            self._reg_write(SETUP_AW, length - 2)
        else:
            raise ValueError(
                "address length can only be set in range [3,5] bytes")

    def open_tx_pipe(self, address):
        """This function is used to open a data pipe for OTA (over the air) TX
        transmissions."""
        if len(address) == self.address_length:
            if self.auto_ack:
                self._pipes[0] = address
                self._reg_write_bytes(RX_ADDR, address)
                self._open_pipes = self._open_pipes | 1
                self._reg_write(EN_RX, self._open_pipes)
                self._payload_widths[0] = self.payload_length
                self._reg_write(RX_PW, self.payload_length)
                self._pipes[0] = address
            self._tx_address = address
            self._reg_write_bytes(TX_ADDR, address)
        else:
            raise ValueError("address must be a buffer protocol object with a byte length\nequal "
                             "to the address_length attribute (currently set to"
                             " {})".format(self.address_length))

    def close_rx_pipe(self, pipe_number):
        """This function is used to close a specific data pipe from OTA (over
        the air) RX transmissions."""
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        self._open_pipes = self._reg_read(EN_RX)
        if self._open_pipes & (1 << pipe_number):
            self._open_pipes = self._open_pipes & ~(1 << pipe_number)
            self._reg_write(EN_RX, self._open_pipes)

    def open_rx_pipe(self, pipe_number, address):
        """This function is used to open a specific data pipe for OTA (over
        the air) RX transmissions."""
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        if len(address) != self.address_length:
            raise ValueError("address must be a buffer protocol object with a byte length\nequal "
                             "to the address_length attribute (currently set to "
                             "{})".format(self.address_length))
        if pipe_number < 2:
            if not pipe_number:
                self._pipe0_read_addr = address
            self._pipes[pipe_number] = address
            self._reg_write_bytes(RX_ADDR + pipe_number, address)
        else:
            self._pipes[pipe_number] = address[0]
            self._reg_write(RX_ADDR + pipe_number, address[0])
        self._open_pipes = self._reg_read(EN_RX)
        self._open_pipes = self._open_pipes | (1 << pipe_number)
        self._reg_write(EN_RX, self._open_pipes)
        self._reg_write(RX_PW + pipe_number, self.payload_length)
        self._payload_widths[pipe_number] = self.payload_length

    @property
    def listen(self):
        """An attribute to represent the nRF24L01 primary role as a radio."""
        return self.power and bool(self._config & 1)

    @listen.setter
    def listen(self, is_rx):
        assert isinstance(is_rx, (bool, int))
        if self.listen != is_rx:
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self):
        if self.ce_pin.value:
            self.ce_pin.value = 0
        if self._pipe0_read_addr is not None:
            self._reg_write_bytes(RX_ADDR, self._pipe0_read_addr)
            self._pipes[0] = self._pipe0_read_addr
        self._config = self._config & 0xFC | 3
        self._reg_write(CONFIG, self._config)
        time.sleep(0.00015) # mandatory wait to power up radio
        self.flush_rx()
        self.clear_status_flags(True, False, False)
        self.ce_pin.value = 1  # mandatory pulse is > 130 µs
        time.sleep(0.00013)

    def _stop_listening(self):
        if self.ce_pin.value:
            self.ce_pin.value = 0
        self._config = self._config & 0xFE
        self._reg_write(CONFIG, self._config)
        time.sleep(0.00016)

    def any(self):
        """This function checks if the nRF24L01 has received any data at all,
        and then reports the next available payload's length (in bytes)"""
        return self._reg_read(0x60)  # 0x60 = R_RX_PL_WID command

    def recv(self):
        """This function is used to retrieve the next available payload"""
        if not self.irq_dr:
            return None
        curr_pl_size = self.payload_length if not self.dynamic_payloads else self.any()
        result = self._reg_read_bytes(0x61, curr_pl_size)  # 0x61 = R_RX_PAYLOAD
        self.clear_status_flags(True, False, False)
        return result

    def send(self, buf, ask_no_ack=False, force_retry=0):
        """This blocking function is used to transmit payload(s)."""
        # ensure power down/standby-I for proper manipulation of PWR_UP & PRIM_RX bits in
        # CONFIG register
        self.ce_pin.value = 0
        self.flush_tx()  # be sure there is space in the TX FIFO
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
                # use recursion for each payload
                result.append(self.send(b, ask_no_ack, force_retry))
            return result
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of"
                             "\nat least 1 and no greater than 32")
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
            retry = False
            for _ in range(force_retry):
                # resend() clears flags upon entering and exiting
                retry = self.resend()
                if retry is None or retry:
                    break # retry succeeded
            result = retry
        else:  # if succeeded
            if self.ack and self.irq_dr and not ask_no_ack:
                # if ACK payload is waiting in RX FIFO
                result = self.recv() # save ACK payload & clears RX flag
            else:  # if auto-ack is disabled
                result = self.irq_ds  # will always be True (in this case)
            self.clear_status_flags(False)  # only TX related IRQ flags
        return result

    @property
    def irq_dr(self):
        """A `bool` that represents the "Data Ready" interrupted flag."""
        return bool(self._status & 0x40)

    @property
    def irq_ds(self):
        """A `bool` that represents the "Data Sent" interrupted flag."""
        return bool(self._status & 0x20)

    @property
    def irq_df(self):
        """A `bool` that represents the "Data Failed" interrupted flag."""
        return bool(self._status & 0x10)

    def clear_status_flags(self, data_recv=True, data_sent=True, data_fail=True):
        """This clears the interrupt flags in the status register."""
        # 0x07 = STATUS register
        self._reg_write(0x07, (data_recv << 6) | (
            data_sent << 5) | (data_fail << 4))

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        """Sets the configuration of the nRF24L01's IRQ (interrupt) pin."""
        self._config = self._reg_read(CONFIG)
        self._config = (self._config & 0x0F) | (not data_fail << 4) | (not data_sent << 5) | \
            (not data_recv << 6)
        self._reg_write(CONFIG, self._config)

    def what_happened(self, dump_pipes=False):
        """This debuggung function aggregates and outputs all status/condition
        related information"""
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
        """This `bool` attribute controls the nRF24L01's dynamic payload
        length feature."""
        return bool(self._dyn_pl and (self._features & 4))

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        assert isinstance(enable, (bool, int))
        self._features = self._reg_read(FEATURE)
        if self._features & 4 != enable:
            self._features = (self._features & 3) | (enable << 2)
            self._reg_write(FEATURE, self._features)
        self._dyn_pl = 0x3F if enable else 0  # 0x3F =  enable dynamic payloads all pipes
        self._reg_write(DYNPD, self._dyn_pl)

    @property
    def payload_length(self):
        """This `int` attribute specifies the length (in bytes) of payload"""
        return self._payload_length

    @payload_length.setter
    def payload_length(self, length):
        # max payload size is 32 bytes
        if not length or length <= 32:
            self._payload_length = length
        else:
            raise ValueError(
                "{}: payload length can only be set in range [1,32] bytes".format(length))

    @property
    def arc(self):
        """This `int` attribute specifies the nRF24L01's number of attempts
        to re-transmit TX payload"""
        self._setup_retr = self._reg_read(SETUP_RETR)
        return self._setup_retr & 0x0f

    @arc.setter
    def arc(self, count):
        if 0 <= count <= 15:
            if self.arc & 0x0F != count:
                self._setup_retr = (self._setup_retr & 0xF0) | count
                self._reg_write(SETUP_RETR, self._setup_retr)
        else:
            raise ValueError(
                "automatic re-transmit count(/attempts) must in range [0,15]")

    @property
    def ard(self):
        """This `int` attribute specifies the nRF24L01's delay (in
        microseconds) between attempts to automatically re-transmit the
        TX payload"""
        self._setup_retr = self._reg_read(SETUP_RETR)
        return ((self._setup_retr & 0xf0) >> 4) * 250 + 250

    @ard.setter
    def ard(self, delta_t):
        if 250 <= delta_t <= 4000 and delta_t % 250 == 0:
            if self.ard != delta_t:
                self._setup_retr = (
                    int((delta_t - 250) / 250) << 4) | (self._setup_retr & 0x0F)
                self._reg_write(SETUP_RETR, self._setup_retr)
        else:
            raise ValueError("automatic re-transmit delay can only be a multiple of 250 in range "
                             "[250,4000]")

    @property
    def auto_ack(self):
        """This `bool` attribute controls the nRF24L01's automatic
        acknowledgment feature during the process of receiving"""
        return self._aa

    @auto_ack.setter
    def auto_ack(self, enable):
        assert isinstance(enable, (bool, int))
        self._aa = 0x3F if enable else 0  # 0x3F = enable auto_ack on all pipes
        self._reg_write(EN_AA, self._aa)

    @property
    def ack(self):
        """This `bool` attribute represents the status of the nRF24L01's
        capability to use custom payloads as part of the automatic
        acknowledgment (ACK) packet."""
        return bool((self._features & 2) and self.auto_ack and self.dynamic_payloads)

    @ack.setter
    def ack(self, enable):
        assert isinstance(enable, (bool, int))
        if self.ack != enable:
            self.auto_ack = True
            self._dyn_pl = 0x3F
            self._reg_write(DYNPD, self._dyn_pl)
        else:
            self._features = self._reg_read(FEATURE)
        self._features = (self._features & 5) | (6 if enable else 0)
        self._reg_write(FEATURE, self._features)

    def load_ack(self, buf, pipe_number):
        """This allows the MCU to specify a payload to be allocated into the
        TX FIFO buffer for use on a specific data pipe."""
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of"
                             "\nat least 1 and no greater than 32")
        if not self.ack:
            self.ack = True
        if not self.tx_full:
            self._reg_write_bytes(0xA8 | pipe_number, buf)  # 0xA8 = W_ACK_PAYLOAD
            return True
        return False

    def read_ack(self):
        """Allows user to read the automatic acknowledgement (ACK) payload (if
        any) when nRF24L01 is in TX mode."""
        return self.recv()

    @property
    def data_rate(self):
        """This `int` attribute specifies the nRF24L01's frequency data rate
        for OTA (over the air) transmissions."""
        self._rf_setup = self._reg_read(RF_SETUP)
        return (2 if self._rf_setup & 0x28 == 8 else 250) if self._rf_setup & 0x28 else 1

    @data_rate.setter
    def data_rate(self, speed):
        if speed in (1, 2, 250):
            if self.data_rate != speed:
                speed = 0 if speed == 1 else (8 if speed == 2 else 0x20)
            self._rf_setup = self._rf_setup & 0xD7 | speed
            self._reg_write(RF_SETUP, self._rf_setup)
        else:
            raise ValueError(
                "data rate must be one of the following ([M,M,K]bps): 1, 2, 250")

    @property
    def channel(self):
        """This `int` attribute specifies the nRF24L01's frequency."""
        return self._reg_read(RF_CH)

    @channel.setter
    def channel(self, channel):
        if 0 <= channel <= 125:
            self._channel = channel
            self._reg_write(RF_CH, channel)
        else:
            raise ValueError("channel acn only be set in range [0,125]")

    @property
    def crc(self):
        """This `int` attribute specifies the nRF24L01's CRC (cyclic redundancy
        checking) encoding scheme in terms of byte length."""
        self._config = self._reg_read(CONFIG)
        return max(0, ((self._config & 12) >> 2) - 1)

    @crc.setter
    def crc(self, length):
        if 0 <= length <= 2:
            if self.crc != length:
                length = (length + 1) << 2 if length else 0
                self._config = self._config & 0x73 | length
                self._reg_write(0, self._config)
        else:
            raise ValueError(
                "CRC byte length must be an int equal to 0 (off), 1, or 2")

    @property
    def power(self):
        """This `bool` attribute controls the power state of the nRF24L01."""
        return bool(self._config & 2)

    @power.setter
    def power(self, is_on):
        assert isinstance(is_on, (bool, int))
        self._config = self._reg_read(CONFIG)
        if self.power != is_on:
            self._config = (self._config & 0x7d) | (is_on << 1)
            self._reg_write(CONFIG, self._config)
            # power up/down takes < 150 µs + 4 µs
            time.sleep(0.00016)

    @property
    def pa_level(self):
        """This `int` attribute specifies the nRF24L01's power amplifier level
        (in dBm)."""
        self._rf_setup = self._reg_read(RF_SETUP)  # refresh data
        return (3 - ((self._rf_setup & RF_SETUP) >> 1)) * -6

    @pa_level.setter
    def pa_level(self, power):
        if power in (-18, -12, -6, 0):
            power = (3 - int(power / -6)) * 2
            self._rf_setup = (self._rf_setup & 0xF9) | power
            self._reg_write(RF_SETUP, self._rf_setup)
        else:
            raise ValueError(
                "power amplitude must be one of the following (dBm): -18, -12, -6, 0")

    @property
    def rpd(self):
        """This read-only attribute returns `True` if RPD (Received Power
        Detector) is triggered or `False` if not triggered."""
        return bool(self._reg_read(0x09))

    @property
    def tx_full(self):
        """An attribute to represent the nRF24L01's status flag signaling that
        the TX FIFO buffer is full. (read-only)"""
        return bool(self._status & 1)

    def update(self):
        """This function is only used to get an updated status byte over SPI
        from the nRF24L01"""
        self._reg_write(0xFF)  # 0xFF = non-operation command

    def resend(self):
        """Use this function to maunally re-send the previous payload in the
        top level (first out) of the TX FIFO buffer."""
        result = False
        if not self.fifo(True, True):
            self.clear_status_flags(False)
            self._reg_write(0xE3)  # 0xE3 == REUSE_TX_PL command
            # timeout calc assumes 32 byte payload (& 32-byte ACK if needed)
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
            self.ce_pin.value = 0
            self.ce_pin.value = 1
            time.sleep(0.00001)
            self.ce_pin.value = 0
            self._wait_for_result(timeout)
            result = self.irq_ds
            if self.ack and self.irq_dr:  # is there an ACK payload
                result = self.recv()
            self.clear_status_flags(False)
        return result

    def write(self, buf, ask_no_ack=False):
        """This non-blocking function (when used as alternative to `send()`) is meant for
        asynchronous applications and can only handle one payload at a time as it is a
        helper function to `send()`."""
        if not buf or len(buf) > 32:
            raise ValueError("buf must be a buffer protocol object with a byte length of"
                             "\nat least 1 and no greater than 32")
        self.clear_status_flags(False)
        if self._config & 3 != 2:
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
            if self._features & 1 == 0:
                self._features = self._features & 0xFE | 1  # set EN_DYN_ACK flag high
                self._reg_write(FEATURE, self._features)
        # 0xA0 = W_TX_PAYLOAD; 0xB0 = W_TX_PAYLOAD_NO_ACK
        self._reg_write_bytes(0xA0 | (ask_no_ack << 4), buf)
        self.ce_pin.value = 1

    def flush_rx(self):
        """A helper function to flush the nRF24L01's internal RX FIFO buffer. (write-only)"""
        self._reg_write(0xE2)

    def flush_tx(self):
        """A helper function to flush the nRF24L01's internal TX FIFO buffer. (write-only)"""
        self._reg_write(0xE1)

    def fifo(self, about_tx=False, check_empty=None):
        """This provides some precision determining the status of the TX/RX FIFO buffers.
        (read-only)"""
        if (check_empty is None and isinstance(about_tx, (bool, int))) or \
                (isinstance(check_empty, (bool, int)) and isinstance(about_tx, (bool, int))):
            self._fifo = self._reg_read(FIFO)  # refresh the data
            if check_empty is None:
                return (self._fifo & (0x30 if about_tx else 0x03)) >> (4 * about_tx)
            return bool(self._fifo & ((2 - check_empty) << (4 * about_tx)))
        raise ValueError("Argument 1 ('about_tx') must always be a bool or int. Argument 2"
                         " ('check_empty'), if specified, must be a bool or int")

    def pipe(self):
        """This function returns information about the data pipe that received the next
        available payload in the RX FIFO buffer."""
        self.update()
        result = (self._status & 0x0E) >> 1  # 0x0E==RX_P_NO
        if result <= 5:
            return result
        return None

    def address(self, index=-1):
        """Returns the current address set to a specified data pipe or the TX address.
        (read-only)"""
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
            self.update()
