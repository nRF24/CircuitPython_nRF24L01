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
import time
from micropython import const
from .wrapper import SPIDevCtx, SPIDevice


CONFIGURE = const(0x00)  # IRQ masking, CRC scheme, PWR control, & RX/TX roles
AUTO_ACK = const(0x01)  # auto-ACK status for all pipes
OPEN_PIPES = const(0x02)  # open/close RX status for all pipes
SETUP_RETR = const(0x04)  # auto-retry count & delay values
RF_PA_RATE = const(0x06)  # RF Power Amplifier & Data Rate values
RX_ADDR_P0 = const(0x0A)  # RX pipe addresses; pipes 0-5 = 0x0A-0x0F
TX_ADDRESS = const(0x10)  # Address used for TX transmissions
RX_PL_LENG = const(0x11)  # RX payload widths; pipes 0-5 = 0x11-0x16
DYN_PL_LEN = const(0x1C)  # dynamic payloads status for all pipes
TX_FEATURE = const(0x1D)  # dynamic TX-payloads, TX-ACK payloads, TX-NO_ACK


def address_repr(buf, reverse: bool = True, delimit: str = "") -> str:
    """Convert a buffer into a hexlified string."""
    order = range(len(buf) - 1, -1, -1) if reverse else range(len(buf))
    return delimit.join(["%02X" % buf[byte] for byte in order])


class RF24:
    """A driver class for the nRF24L01(+) transceiver radios."""

    def __init__(self, spi, csn, ce_pin, spi_frequency=10000000):
        self._ce_pin = ce_pin
        self._ce_pin.switch_to_output(value=False)
        # init shadow copy of RX addresses for all pipes for context manager
        self._pipes = []  # will be 2 bytearrays and 4 ints
        # self._status = status byte returned on all SPI transactions
        # pre-configure the CONFIGURE register:
        #   0x0E = all IRQs enabled, CRC is 2 bytes, and power up in TX mode
        self._status, self._config, self._spi = (0, 0x0E, None)
        # setup SPI
        if type(spi).__name__.endswith("SpiDev"):
            self._spi = SPIDevCtx(spi, csn, spi_frequency=spi_frequency)
        else:
            self._spi = SPIDevice(spi, chip_select=csn, baudrate=spi_frequency)
        self._reg_write(CONFIGURE, self._config)
        if self._reg_read(CONFIGURE) != self._config:
            raise RuntimeError("radio hardware not responding")
        for i in range(6):  # capture RX addresses from registers
            if i < 2:
                self._pipes.append(self._reg_read_bytes(RX_ADDR_P0 + i))
            else:
                self._pipes.append(self._reg_read(RX_ADDR_P0 + i))
        # test is nRF24L01 is a plus variant using a command specific to
        # non-plus variants
        self._open_pipes, self._is_plus_variant = (0, False)  # close all RX pipes
        self._features = self._reg_read(TX_FEATURE)
        self._reg_write(0x50, 0x73)  # derelict command toggles TX_FEATURE register
        after_toggle = self._reg_read(TX_FEATURE)
        if self._features == after_toggle:
            self._is_plus_variant = True
        elif not after_toggle:  # if features are disabled
            self._reg_write(0x50, 0x73)  # ensure they're enabled
        # pre-configure features for TX operations:
        #   5 = enable dynamic_payloads, disable custom ack payloads, &
        #       allow ask_no_ack command
        self._features = 5
        # init shadow copy of last RX_ADDR_P0 written to pipe 0 needed as
        # open_tx_pipe() appropriates pipe 0 for ACK packet
        self._pipe0_read_addr = None
        # shadow copy of the TX_ADDRESS
        self._tx_address = self._reg_read_bytes(TX_ADDRESS)
        # pre-configure the SETUP_RETR register
        self._retry_setup = 0x5F  # ard = 1500; arc = 15
        # pre-configure the RF_SETUP register
        self._rf_setup = 0x07  # 1 Mbps data_rate, and 0 dbm pa_level
        # pre-configure dynamic_payloads & auto_ack
        self._dyn_pl, self._aa = (0x3F,) * 2  # 0x3F = enable feature on all pipes
        self._channel = 76  # 2.476 GHz
        self._addr_len = 5  # 5-byte long addresses
        self._pl_len = [32] * 6  # 32-byte static payloads for all pipes

        with self:  # dumps internal attributes to all registers
            self.flush_rx()
            self.flush_tx()
            self.clear_status_flags()

    def __enter__(self):
        self._ce_pin.value = False
        self._config |= 2
        self._reg_write(CONFIGURE, self._config)
        # time.sleep(0.00015)  # let the rest of this function be the delay
        self._reg_write(RF_PA_RATE, self._rf_setup)
        self._reg_write(OPEN_PIPES, self._open_pipes)
        self._reg_write(DYN_PL_LEN, self._dyn_pl)
        self._reg_write(AUTO_ACK, self._aa)
        self._reg_write(TX_FEATURE, self._features)
        self._reg_write(SETUP_RETR, self._retry_setup)
        for i, addr in enumerate(self._pipes):
            if i < 2:
                self._reg_write_bytes(RX_ADDR_P0 + i, addr)
            else:
                self._reg_write(RX_ADDR_P0 + i, addr)
            self.set_payload_length(self._pl_len[i], i)
        self._reg_write_bytes(TX_ADDRESS, self._tx_address)
        self._reg_write(0x05, self._channel)
        self._reg_write(0x03, self._addr_len - 2)
        return self

    def __exit__(self, *exc):
        self._ce_pin.value = False
        self._config &= 0x7D  # power off radio
        self._reg_write(CONFIGURE, self._config)
        time.sleep(0.00015)
        return False

    @property
    def ce_pin(self):
        """Control the radio's CE pin (for advanced usage)"""
        return self._ce_pin.value

    @ce_pin.setter
    def ce_pin(self, val):
        self._ce_pin.value = val

    def _reg_read(self, reg: int) -> int:
        in_buf = bytearray([0, 0])
        with self._spi as spi:
            # time.sleep(0.000005)
            spi.write_readinto(bytes([reg, 0]), in_buf)
        self._status = in_buf[0]
        # print("SPI read 1 byte from", ("%02X" % reg), ("%02X" % in_buf[1]))
        return in_buf[1]

    def _reg_read_bytes(self, reg: int, buf_len: int = 5) -> bytearray:
        in_buf = bytearray(buf_len + 1)
        with self._spi as spi:
            # time.sleep(0.000005)
            spi.write_readinto(bytes([reg] + [0] * buf_len), in_buf)
        self._status = in_buf[0]
        # print("SPI read {} bytes from {} {}".format(
        #     buf_len, ("%02X" % reg), address_repr(in_buf[1:], 0)
        # ))
        return in_buf[1:]

    def _reg_write_bytes(self, reg: int, out_buf):
        in_buf = bytearray(len(out_buf) + 1)
        with self._spi as spi:
            # time.sleep(0.000005)
            spi.write_readinto(bytes([0x20 | reg]) + out_buf, in_buf)
        self._status = in_buf[0]
        # print("SPI write {} bytes to {} {}".format(
        #     len(out_buf), ("%02X" % reg), address_repr(out_buf, 0)
        # ))

    def _reg_write(self, reg: int, value: int = None):
        out_buf = bytes([reg])
        if value is not None:
            out_buf = bytes([(0x20 if reg != 0x50 else 0) | reg, value])
        in_buf = bytearray(len(out_buf))
        with self._spi as spi:
            # time.sleep(0.000005)
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]
        # if reg != 0xFF:
        #     print(
        #         "SPI write", "command" if value is None else "1 byte to",
        #         ("%02X" % reg), "" if value is None else ("%02X" % value)
        #     )

    @property
    def address_length(self) -> int:
        """This `int` is the length (in bytes) used of RX/TX addresses."""
        self._addr_len = self._reg_read(0x03) + 2
        return self._addr_len

    @address_length.setter
    def address_length(self, length: int):
        self._addr_len = int(length) if 3 <= length <= 5 else 2
        self._reg_write(0x03, self._addr_len - 2)

    def open_tx_pipe(self, address) -> None:
        """Open a data pipe for TX transmissions."""
        if self._pipe0_read_addr != address and self._aa & 1:
            for i, val in enumerate(address):
                self._pipes[0][i] = val
            self._reg_write_bytes(RX_ADDR_P0, address)
        for i, val in enumerate(address):
            self._tx_address[i] = val
        self._reg_write_bytes(TX_ADDRESS, address)

    def close_rx_pipe(self, pipe_number: int) -> None:
        """Close a specific data pipe from RX transmissions."""
        if pipe_number < 0 or pipe_number > 5:
            raise IndexError("pipe number must be in range [0, 5]")
        self._open_pipes = self._reg_read(OPEN_PIPES) & ~(1 << pipe_number)
        if not pipe_number:
            self._pipe0_read_addr = None
        self._reg_write(OPEN_PIPES, self._open_pipes)

    def open_rx_pipe(self, pipe_number: int, address) -> None:
        """Open a specific data pipe for RX transmissions."""
        if not 0 <= pipe_number <= 5:
            raise IndexError("pipe number must be in range [0, 5]")
        if not address:
            raise ValueError("address length cannot be 0")
        if pipe_number < 2:
            if not pipe_number:
                self._pipe0_read_addr = address
            for i, val in enumerate(address):
                self._pipes[pipe_number][i] = val
            self._reg_write_bytes(RX_ADDR_P0 + pipe_number, address)
        else:
            self._pipes[pipe_number] = address[0]
            self._reg_write(RX_ADDR_P0 + pipe_number, address[0])
        self._open_pipes = self._reg_read(OPEN_PIPES) | (1 << pipe_number)
        self._reg_write(OPEN_PIPES, self._open_pipes)

    @property
    def listen(self) -> bool:
        """This attribute is the primary role as a radio."""
        return self.power and bool(self._config & 1)

    @listen.setter
    def listen(self, is_rx: bool):
        self._ce_pin.value = False
        self._config = self._config & 0xFC | (2 + bool(is_rx))
        self._reg_write(CONFIGURE, self._config)
        start_timer = time.monotonic_ns()
        if is_rx:
            self._ce_pin.value = True
            if (
                self._pipe0_read_addr is not None
                and self._pipe0_read_addr != self.address(0)
            ):
                for i, val in enumerate(self._pipe0_read_addr):
                    self._pipes[0][i] = val
                self._reg_write_bytes(RX_ADDR_P0, self._pipe0_read_addr)
            elif self._pipe0_read_addr is None and self._open_pipes & 1:
                self._open_pipes &= 0x3E  # close_rx_pipe(0) is slower
                self._reg_write(OPEN_PIPES, self._open_pipes)
        else:
            if self._features & 6 == 6 and ((self._aa & self._dyn_pl) & 1):
                self.flush_tx()
            if self._aa & 1 and not self._open_pipes & 1:
                self._open_pipes |= 1
                self._reg_write(OPEN_PIPES, self._open_pipes)
        # mandatory wait time is 130 µs
        delta_time = time.monotonic_ns() - start_timer
        if delta_time < 150000:
            time.sleep((150000 - delta_time) / 1000000000)

    def available(self) -> bool:
        """A `bool` describing if there is a payload in the RX FIFO."""
        return self.update() and self._status >> 1 & 7 < 6

    def any(self) -> int:
        """This function reports the next available payload's length (in bytes)."""
        last_dyn_size = self._reg_read(0x60)
        if self._status >> 1 & 7 < 6:
            if self._features & 4:
                return last_dyn_size
            return self._pl_len[(self._status >> 1) & 7]
        return 0

    def read(self, length: int = None) -> bytearray:
        """This function is used to retrieve data from the RX FIFO."""
        return_size = length if length is not None else self.any()
        if not return_size:
            return None
        result = self._reg_read_bytes(0x61, return_size)
        self.clear_status_flags(True, False, False)
        return result

    def send(
        self,
        buf,
        ask_no_ack: bool = False,
        force_retry: int = 0,
        send_only: bool = False,
    ):
        """This blocking function is used to transmit payload(s)."""
        self._ce_pin.value = False
        if isinstance(buf, (list, tuple)):
            result = []
            for b in buf:
                result.append(self.send(b, ask_no_ack, force_retry, send_only))
            return result
        if self._status & 0x10 or self._status & 1:
            self.flush_tx()
        if not send_only and self._status >> 1 & 7 < 6:
            self.flush_rx()
        up_cnt = 0
        self.write(buf, ask_no_ack)
        while not self._status & 0x30:
            up_cnt += self.update()
        result = bool(self._status & 0x20)
        # print("send did {} updates. flags: {}".format(up_cnt, self._status >> 4))
        while force_retry and not result:
            result = self.resend(send_only)
            force_retry -= 1
        if self._status & 0x60 == 0x60 and not send_only:
            result = self.read()
        # self._ce_pin.value = False
        return result

    @property
    def tx_full(self) -> bool:
        """An `bool` to represent if the TX FIFO is full. (read-only)"""
        return bool(self._status & 1)

    @property
    def pipe(self):
        """The number of the data pipe that received the next available
        payload in the RX FIFO. (read only)"""
        result = self._status >> 1 & 7
        if result <= 5 and self._spi is not None:
            return result
        return None

    @property
    def irq_dr(self) -> bool:
        """A `bool` that represents the "Data Ready" interrupted flag. (read-only)"""
        return bool(self._status & 0x40)

    @property
    def irq_ds(self) -> bool:
        """A `bool` that represents the "Data Sent" interrupted flag. (read-only)"""
        return bool(self._status & 0x20)

    @property
    def irq_df(self) -> bool:
        """A `bool` that represents the "Data Failed" interrupted flag. (read-only)"""
        return bool(self._status & 0x10)

    def update(self) -> True:
        """This function gets an updated status byte over SPI."""
        self._reg_write(0xFF)
        return True

    def clear_status_flags(
        self, data_recv: bool = True, data_sent: bool = True, data_fail: bool = True
    ):
        """This clears the interrupt flags in the status register."""
        config = bool(data_recv) << 6 | bool(data_sent) << 5
        self._reg_write(7, config | bool(data_fail) << 4)

    def interrupt_config(
        self, data_recv: bool = True, data_sent: bool = True, data_fail: bool = True
    ):
        """Sets the configuration of the nRF24L01's IRQ pin. (write-only)"""
        self._config = (self._reg_read(CONFIGURE) & 0x0F) | (not data_recv) << 6
        self._config |= (not data_fail) << 4 | (not data_sent) << 5
        self._reg_write(CONFIGURE, self._config)

    def print_details(self, dump_pipes: bool = False):
        """This debuggung function outputs all details about the nRF24L01."""
        observer = self._reg_read(8)
        _fifo = self._reg_read(0x17)
        self._config = self._reg_read(CONFIGURE)
        self._rf_setup = self._reg_read(RF_PA_RATE)
        self._retry_setup = self._reg_read(SETUP_RETR)
        self._channel = self.channel
        self._addr_len = self._reg_read(0x03) + 2
        self._features = self._reg_read(TX_FEATURE)
        self._aa = self._reg_read(AUTO_ACK)
        self._dyn_pl = self._reg_read(DYN_PL_LEN)
        _crc = (
            (2 if self._config & 4 else 1)
            if self._aa
            else max(0, ((self._config & 0x0C) >> 2) - 1)
        )
        d_rate = self._rf_setup & 0x28
        d_rate = (2 if d_rate == 8 else 250) if d_rate else 1
        _pa_level = (3 - ((self._rf_setup & 6) >> 1)) * -6
        dyn_p = (
            ("_Enabled" if self._dyn_pl else "Disabled")
            if self._dyn_pl == 0x3F or not self._dyn_pl
            else "0b" + "0" * (8 - len(bin(self._dyn_pl))) + bin(self._dyn_pl)[2:]
        )
        auto_a = (
            ("Enabled" if self._aa else "Disabled")
            if self._aa == 0x3F or not self._aa
            else "0b" + "0" * (8 - len(bin(self._aa))) + bin(self._aa)[2:]
        )
        pwr = (
            ("Standby-II" if self._ce_pin.value else "Standby-I")
            if self._config & 2
            else "Off"
        )
        print(f"Is a plus variant_________{self.is_plus_variant}")
        print(
            f"Channel___________________{self._channel}",
            f"~ {(self._channel + 2400) / 1000} GHz",
        )
        print(
            f"RF Data Rate______________{d_rate}", "Mbps" if d_rate != 250 else "Kbps"
        )
        print(f"RF Power Amplifier________{_pa_level} dbm")
        print(
            "RF Low Noise Amplifier____{}abled".format(
                "En" if bool(self._rf_setup & 1) else "Dis"
            )
        )
        print(f"CRC bytes_________________{_crc}")
        print(f"Address length____________{self._addr_len} bytes")
        print(f"TX Payload lengths________{self._pl_len[0]} bytes")
        print(
            f"Auto retry delay__________"
            f"{((self._retry_setup & 0xF0) >> 4) * 250 + 250} microseconds",
        )
        print(f"Auto retry attempts_______{self._retry_setup & 0x0F} maximum")
        print(f"Re-use TX FIFO____________{bool(_fifo & 64)}")
        print(f"Packets lost on current channel_____________________{observer >> 4}")
        print(f"Retry attempts made for last transmission___________{observer & 0xF}")
        print(
            "IRQ on Data Ready__{}abled".format("Dis" if self._config & 64 else "_En"),
            f"   Data Ready___________{self.irq_dr}",
        )
        print(
            "IRQ on Data Fail___{}abled".format("Dis" if self._config & 16 else "_En"),
            f"   Data Failed__________{self.irq_df}",
        )
        print(
            "IRQ on Data Sent___{}abled".format("Dis" if self._config & 32 else "_En"),
            f"   Data Sent____________{self.irq_ds}",
        )
        print(
            "TX FIFO full__________{}e".format("_Tru" if _fifo & 0x20 else "Fals"),
            f"   TX FIFO empty________{bool(_fifo & 0x10)}",
        )
        print(
            "RX FIFO full__________{}e".format("_Tru" if _fifo & 2 else "Fals"),
            f"   RX FIFO empty________{bool(_fifo & 1)}",
        )
        print(
            "Ask no ACK_________{}ed    Custom ACK Payload___{}abled".format(
                "_Allow" if self._features & 1 else "Disabl",
                "En" if self._features & 2 else "Dis",
            ),
        )
        print(f"Dynamic Payloads___{dyn_p}    Auto Acknowledgment__{auto_a}")
        print(
            "Primary Mode_____________{}X".format("R" if self._config & 1 else "T"),
            f"   Power Mode___________{pwr}",
        )
        if dump_pipes:
            self.print_pipes()

    def print_pipes(self):
        """Prints all information specific to pipe's addresses, RX state, & expected
        static payload sizes (if configured to use static payloads)."""
        self._open_pipes = self._reg_read(OPEN_PIPES)
        self._tx_address = self._reg_read_bytes(TX_ADDRESS)
        for i in range(6):
            if i < 2:
                self._pipes[i] = self._reg_read_bytes(RX_ADDR_P0 + i)
            else:
                self._pipes[i] = self._reg_read(RX_ADDR_P0 + i)
            self._pl_len[i] = self._reg_read(RX_PL_LENG + i)
        print(f"TX address____________ 0x{address_repr(self.address())}")
        for i in range(6):
            is_open = self._open_pipes & (1 << i)
            print(
                "Pipe {} ({}) bound: 0x{}".format(
                    i, " open " if is_open else "closed", address_repr(self.address(i))
                ),
            )
            if is_open and not self._dyn_pl & (1 << i):
                print(f"\t\texpecting {self._pl_len[i]} byte static payloads")

    @property
    def is_plus_variant(self) -> bool:
        """A `bool` descibing if the nRF24L01 is a plus variant or not (read-only)."""
        return self._is_plus_variant

    @property
    def dynamic_payloads(self) -> int:
        """This `int` attribute is the dynamic payload length feature for
        any/all pipes."""
        self._dyn_pl = self._reg_read(DYN_PL_LEN)
        return self._dyn_pl

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        self._features = self._reg_read(TX_FEATURE)
        if isinstance(enable, bool):
            self._dyn_pl = 0x3F if enable else 0
        elif isinstance(enable, int):
            self._dyn_pl = 0x3F & enable
        elif isinstance(enable, (list, tuple)):
            self._dyn_pl = self._reg_read(DYN_PL_LEN)
            for i, val in enumerate(enable):
                if i < 6 and val >= 0:  # skip pipe if val is negative
                    self._dyn_pl = (self._dyn_pl & ~(1 << i)) | (bool(val) << i)
        else:
            raise ValueError(f"dynamic_payloads: {enable} is an invalid input")
        self._features = (self._features & 3) | (bool(self._dyn_pl) << 2)
        self._reg_write(TX_FEATURE, self._features)
        self._reg_write(DYN_PL_LEN, self._dyn_pl)

    def set_dynamic_payloads(self, enable: bool, pipe_number: int = None):
        """Control the dynamic payload feature for a specific data pipe."""
        if pipe_number is None:
            self.dynamic_payloads = bool(enable)
        elif 0 <= pipe_number <= 5:
            self._dyn_pl = self._reg_read(DYN_PL_LEN) & ~(1 << pipe_number)
            self.dynamic_payloads = self._dyn_pl | (bool(enable) << pipe_number)
        else:
            raise IndexError("pipe_number must be in range [0, 5]")

    def get_dynamic_payloads(self, pipe_number: int = 0) -> bool:
        """Returns a `bool` describing the dynamic payload feature about a pipe."""
        if 0 <= pipe_number <= 5:
            return bool(self.dynamic_payloads & (1 << pipe_number))
        raise IndexError("pipe_number must be in range [0, 5]")

    @property
    def payload_length(self) -> int:
        """This `int` attribute is the length of static payloads for any/all pipes."""
        return self._pl_len[0]

    @payload_length.setter
    def payload_length(self, length):
        if isinstance(length, int):
            length = [max(1, length)] * 6
        elif not isinstance(length, (list, tuple)):
            raise ValueError("length {} is not a valid input".format(length))
        for i, val in enumerate(length):
            if i < 6 and val > 0:  # don't throw exception, just skip pipe
                self._pl_len[i] = min(32, val)
                self._reg_write(RX_PL_LENG + i, self._pl_len[i])

    def set_payload_length(self, length: int, pipe_number: int = None):
        """Sets the static payload length feature for each/all data pipes."""
        if pipe_number is None:
            self.payload_length = length
        else:
            self._pl_len[pipe_number] = max(1, min(32, length))
            self._reg_write(RX_PL_LENG + pipe_number, length)

    def get_payload_length(self, pipe_number: int = 0) -> int:
        """Returns an `int` describing the specified data pipe's static
        payload length."""
        self._pl_len[pipe_number] = self._reg_read(RX_PL_LENG + pipe_number)
        return self._pl_len[pipe_number]

    @property
    def arc(self) -> int:
        """This `int` attribute specifies the number of attempts to
        re-transmit TX payload when ACK packet is not received."""
        self._retry_setup = self._reg_read(SETUP_RETR)
        return self._retry_setup & 0x0F

    @arc.setter
    def arc(self, count: int):
        count = max(0, min(int(count), 15))
        self._retry_setup = (self._retry_setup & 0xF0) | count
        self._reg_write(SETUP_RETR, self._retry_setup)

    @property
    def ard(self) -> int:
        """This `int` attribute specifies the delay (in microseconds) between attempts
        to automatically re-transmit the TX payload when no ACK packet is received."""
        self._retry_setup = self._reg_read(SETUP_RETR)
        return ((self._retry_setup & 0xF0) >> 4) * 250 + 250

    @ard.setter
    def ard(self, delta: int):
        delta = max(250, min(delta, 4000))
        self._retry_setup = (self._retry_setup & 15) | int((delta - 250) / 250) << 4
        self._reg_write(SETUP_RETR, self._retry_setup)

    def set_auto_retries(self, delay: int, count: int):
        """set the `ard` & `arc` attributes with 1 function."""
        delay = int((max(250, min(delay, 4000)) - 250) / 250) << 4
        self._retry_setup = delay | max(0, min(int(count), 15))
        self._reg_write(SETUP_RETR, self._retry_setup)

    def get_auto_retries(self) -> tuple:
        """get the `ard` & `arc` attributes with 1 function."""
        return (self.ard, self._retry_setup & 0x0F)

    @property
    def last_tx_arc(self) -> int:
        """Return the number of attempts made for last transission (read-only)."""
        return self._reg_read(8) & 0x0F

    @property
    def auto_ack(self) -> int:
        """This `int` attribute is the automatic acknowledgment feature for
        any/all pipes."""
        self._aa = self._reg_read(AUTO_ACK)
        return self._aa

    @auto_ack.setter
    def auto_ack(self, enable):
        if isinstance(enable, bool):
            self._aa = 0x3F if enable else 0
        elif isinstance(enable, int):
            self._aa = 0x3F & enable
        elif isinstance(enable, (list, tuple)):
            self._aa = self._reg_read(AUTO_ACK)
            for i, val in enumerate(enable):
                if i < 6 and val >= 0:  # skip pipe if val is negative
                    self._aa = (self._aa & ~(1 << i)) | (bool(val) << i)
        else:
            raise ValueError(f"auto_ack: {enable} is not a valid input")
        self._reg_write(AUTO_ACK, self._aa)

    def set_auto_ack(self, enable: bool, pipe_number: int):
        """Control the `auto_ack` feature for a specific data pipe."""
        if pipe_number is None:
            self.auto_ack = bool(enable)
        elif 0 <= pipe_number <= 5:
            self._aa = self._reg_read(AUTO_ACK) & ~(1 << pipe_number)
            self.auto_ack = self._aa | (bool(enable) << pipe_number)
        else:
            raise IndexError("pipe_number must be in range [0, 5]")

    def get_auto_ack(self, pipe_number: int) -> bool:
        """Returns a `bool` describing the `auto_ack` feature about a data pipe."""
        if 0 <= pipe_number <= 5:
            self._aa = self._reg_read(AUTO_ACK)
            return bool(self._aa & (1 << pipe_number))
        raise IndexError("pipe_number must be in range [0, 5]")

    @property
    def ack(self) -> bool:
        """Represents use of custom payloads as part of the ACK packet."""
        self._aa = self._reg_read(AUTO_ACK)
        self._dyn_pl = self._reg_read(DYN_PL_LEN)
        self._features = self._reg_read(TX_FEATURE)
        return bool((self._features & 6) == 6 and ((self._aa & self._dyn_pl) & 1))

    @ack.setter
    def ack(self, enable: bool):
        if bool(enable):
            self.set_auto_ack(True, 0)
            self._dyn_pl = self._dyn_pl & 0x3E | 1
            self._reg_write(DYN_PL_LEN, self._dyn_pl)
            self._features = self._features | 4
        self._features = self._features & 5 | bool(enable) << 1
        self._reg_write(TX_FEATURE, self._features)

    def load_ack(self, buf, pipe_number: int) -> bool:
        """Load a payload into the TX FIFO for use on a specific data pipe."""
        if pipe_number < 0 or pipe_number > 5:
            raise IndexError("pipe_number must be in range [0, 5]")
        if not buf or len(buf) > 32:
            raise ValueError("payload must have a byte length in range [1, 32]")
        if not bool((self._features & 6) == 6 and ((self._aa & self._dyn_pl) & 1)):
            self.ack = True
        if not self.tx_full:
            self._reg_write_bytes(0xA8 | pipe_number, buf)
            return True
        return False

    @property
    def allow_ask_no_ack(self) -> bool:
        """Allow or disable ``ask_no_ack`` parameter to `send()` & `write()`."""
        self._features = self._reg_read(TX_FEATURE)
        return bool(self._features & 1)

    @allow_ask_no_ack.setter
    def allow_ask_no_ack(self, enable: bool):
        self._features = self._reg_read(TX_FEATURE) & 6 | bool(enable)
        self._reg_write(TX_FEATURE, self._features)

    @property
    def data_rate(self) -> int:
        """This `int` attribute specifies the RF data rate."""
        self._rf_setup = self._reg_read(RF_PA_RATE)
        rf_setup = self._rf_setup & 0x28
        return (2 if rf_setup == 8 else 250) if rf_setup else 1

    @data_rate.setter
    def data_rate(self, speed: int):
        if not speed in (1, 2, 250):
            raise ValueError("data_rate must be 1 (Mbps), 2 (Mbps), or 250 (kbps)")
        speed = 0 if speed == 1 else (0x20 if speed != 2 else 8)
        self._rf_setup = self._reg_read(RF_PA_RATE) & 0xD7 | speed
        self._reg_write(RF_PA_RATE, self._rf_setup)

    @property
    def channel(self) -> int:
        """This `int` attribute specifies the nRF24L01's frequency."""
        return self._reg_read(5)

    @channel.setter
    def channel(self, channel: int):
        if not 0 <= int(channel) <= 125:
            raise ValueError("channel can only be set in range [0, 125]")
        self._channel = int(channel)
        self._reg_write(5, self._channel)

    @property
    def crc(self) -> int:
        """This `int` attribute specifies the CRC checksum length in bytes."""
        self._config = self._reg_read(CONFIGURE)
        self._aa = self._reg_read(AUTO_ACK)
        if self._aa:
            return 2 if self._config & 4 else 1
        return max(0, ((self._config & 0x0C) >> 2) - 1)

    @crc.setter
    def crc(self, length: int):
        length = min(2, abs(int(length)))
        length = (length + 1) << 2 if length else 0
        self._config = self._config & 0x73 | length
        self._reg_write(CONFIGURE, self._config)

    @property
    def power(self) -> bool:
        """This `bool` attribute controls the power state of the nRF24L01."""
        self._config = self._reg_read(CONFIGURE)
        return bool(self._config & 2)

    @power.setter
    def power(self, is_on: bool):
        self._config = self._reg_read(CONFIGURE) & 0x7D | bool(is_on) << 1
        self._reg_write(CONFIGURE, self._config)
        time.sleep(0.00015)

    @property
    def pa_level(self) -> int:
        """This `int` is the power amplifier level (in dBm)."""
        self._rf_setup = self._reg_read(RF_PA_RATE)
        return (3 - ((self._rf_setup & 6) >> 1)) * -6

    @pa_level.setter
    def pa_level(self, power):
        lna_bit = True
        if isinstance(power, (list, tuple)) and len(power) > 1:
            lna_bit, power = bool(power[1]), int(power[0])
        if power not in (-18, -12, -6, 0):
            raise ValueError("pa_level must be -18, -12, -6, or 0 (in dBm)")
        power = (3 - int(power / -6)) * 2
        self._rf_setup = (self._rf_setup & 0xF8) | power | lna_bit
        self._reg_write(RF_PA_RATE, self._rf_setup)

    @property
    def is_lna_enabled(self) -> bool:
        """A read-only `bool` attribute about the LNA gain feature."""
        self._rf_setup = self._reg_read(RF_PA_RATE)
        return bool(self._rf_setup & 1)

    def resend(self, send_only: bool = False):
        """Manually re-send the first-out payload from TX FIFO buffers."""
        if self.fifo(True, True):
            return False
        self._ce_pin.value = False
        if not send_only and (self._status >> 1) < 6:
            self.flush_rx()
        self.clear_status_flags()
        # self._reg_write(0xE3)
        up_cnt = 0
        self._ce_pin.value = True
        while not self._status & 0x30:
            up_cnt += self.update()
        # self._ce_pin.value = False
        result = bool(self._status & 0x20)
        # print("resend did {} updates. flags: {}".format(up_cnt, self._status >> 4))
        if result and self._status & 0x40 and not send_only:
            return self.read()
        return result

    def write(self, buf, ask_no_ack: bool = False, write_only: bool = False) -> bool:
        """This non-blocking and helper function to `send()` can only handle
        one payload at a time."""
        if not buf or len(buf) > 32:
            raise ValueError("buffer must have a length in range [1, 32]")
        self.clear_status_flags()
        is_power_up = self._config & 2
        if self._config & 3 != 2:  # is radio powered up in TX mode?
            self._config = (self._config & 0x7C) | 2
            self._reg_write(CONFIGURE, self._config)
            if not is_power_up:
                time.sleep(0.00015)
        if self._status & 1:
            return False
        if not bool((self._dyn_pl & 1) and (self._features & 4)):
            if len(buf) < self._pl_len[0]:
                buf += b"\0" * (self._pl_len[0] - len(buf))
            elif len(buf) > self._pl_len[0]:
                buf = buf[: self._pl_len[0]]
        if ask_no_ack and self._features & 1 == 0:
            self._features = self._features & 0xFE | 1
            self._reg_write(TX_FEATURE, self._features)
        self._reg_write_bytes(0xA0 | (bool(ask_no_ack) << 4), buf)
        if not write_only:
            self._ce_pin.value = True
        return True

    def flush_rx(self):
        """Flush all 3 levels of the RX FIFO."""
        self._reg_write(0xE2)

    def flush_tx(self):
        """Flush all 3 levels of the TX FIFO."""
        self._reg_write(0xE1)

    def fifo(self, about_tx: bool = False, check_empty: bool = None):
        """This provides the status of the TX/RX FIFO buffers. (read-only)"""
        _fifo, about_tx = (self._reg_read(0x17), bool(about_tx))
        if check_empty is None:
            return (_fifo & (0x30 if about_tx else 0x03)) >> (4 * about_tx)
        return bool(_fifo & ((2 - bool(check_empty)) << (4 * about_tx)))

    def address(self, index: int = -1):
        """Returns the current TX address or optionally RX address. (read-only)"""
        if index > 5:
            raise IndexError("index {} is out of bounds [0,5]".format(index))
        if index < 0:
            return self._tx_address
        if index <= 1:
            return self._pipes[index]
        return bytes([self._pipes[index]]) + self._pipes[1][1:]

    @property
    def rpd(self) -> bool:
        """Returns `True` if signal was detected or `False` if not. (read-only)"""
        return bool(self._reg_read(0x09))

    def start_carrier_wave(self):
        """Starts a continuous carrier wave test."""
        self.power = False
        self._ce_pin.value = False
        self.power = True
        self.listen = False
        self._rf_setup |= 0x90
        self._reg_write(RF_PA_RATE, self._rf_setup)
        if not self.is_plus_variant:
            self._reg_write(AUTO_ACK, 0)
            self._reg_write(SETUP_RETR, 0)
            self._reg_write_bytes(TX_ADDRESS, b"\xFF" * 5)
            self._reg_write_bytes(0xA0, b"\xFF" * 32)
            self._reg_write(CONFIGURE, 0x73)
            self._ce_pin.value = True
            time.sleep(0.001)
            self._ce_pin.value = False
            self.clear_status_flags()
            self._reg_write(0x17, 0x40)
        self._ce_pin.value = True

    def stop_carrier_wave(self):
        """Stops a continuous carrier wave test."""
        self._ce_pin.value = False
        self.power = False
        self._rf_setup &= ~0x90
        self._reg_write(RF_PA_RATE, self._rf_setup)
