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

try:
    from ubus_device import SPIDevice
except ImportError:
    from adafruit_bus_device.spi_device import SPIDevice

# nRF24L01 registers
CONFIGURE = const(0x00)  # IRQ, CRC, PWR control & RX/TX roles
AUTO_ACK = const(0x01)  # auto-ACK
OPEN_PIPES = const(0x02)  # open/close pipes
SETUP_RETR = const(0x04)  # auto-retry count & delay
RF_PA_RATE = const(0x06)  # RF Power Amplifier & Data Rate
RX_ADDR_P0 = const(0x0A)  # RX pipe addresses == [0, 5]:[0x0a, 0x0f]
RX_PL_LENG = const(0x11)  # RX payload widths on pipes == [0, 5]:[0x11, 0x16]
DYN_PL_LEN = const(0x1C)  # dynamic payloads
TX_FEATURE = const(0x1D)  # TX features dynamic payloads, ACK payloads, NO_ACK
TX_ADDRESS = const(0x10)  # Address used for TX transmissions


class RF24:
    """A driver class for the nRF24L01(+) transceiver radios."""

    def __init__(self, spi, csn, ce):
        self._pl_len = 32
        self.payload_length = 32
        self._fifo = 0
        self._status = 0
        # init shadow copy of RX addresses for all pipes for context manager
        self._pipes = [b"\xE7" * 5, b"\xC2" * 5, 0, 0, 0, 0]
        # shadow copy of last RX_ADDR_P0 written to pipe 0 needed as
        # open_tx_pipe() appropriates pipe 0 for ACK packet
        self._pipe0_read_addr = None
        # _open_pipes attribute reflects only RX state on each pipe
        self._open_pipes = 0  # 0 = all pipes closed
        self._spi = SPIDevice(spi, chip_select=csn, baudrate=1250000)
        self.ce_pin = ce
        self.ce_pin.switch_to_output(value=False)  # pre-empt standby-I mode
        # pre-configure the CONFIGURE register:
        #   0x0E = IRQs are all enabled, CRC is enabled with 2 bytes, and
        #          power up in TX mode
        self._config = 0x0E
        self._reg_write(CONFIGURE, self._config)
        if self._reg_read(CONFIGURE) & 3 == 2:
            self.power = False
        else:  # hardware presence check NOT passed
            raise RuntimeError("nRF24L01 Hardware not responding")
        # shadow copies of RX pipe addresses for context manager
        for i in range(6):
            if i < 2:
                self._pipes[i] = self._reg_read_bytes(RX_ADDR_P0 + i)
            else:
                self._pipes[i] = self._reg_read(RX_ADDR_P0 + i)
        # shadow copy of the TX_ADDRESS
        self._tx_address = self._reg_read_bytes(TX_ADDRESS)
        # pre-configure the SETUP_RETR register
        self._retry_setup = 0x53  # ard = 1500; arc = 3
        # pre-configure the RF_SETUP register
        self._rf_setup = 0x06  # 1 Mbps data_rate, and 0 dbm pa_level
        # pre-configure dynamic_payloads & auto_ack for RX operations
        self._dyn_pl = 0x3F  # 0x3F = enable dynamic_payloads on all pipes
        self._aa = 0x3F  # 0x3F = enable auto_ack on all pipes
        # pre-configure features for TX operations:
        #   5 = enable dynamic_payloads, disable custom ack payloads, &
        #       allow ask_no_ack command
        self._features = 5
        self._channel = 76  # 2.476 GHz
        self._addr_len = 5  # 5-byte long addresses

        with self:  # dumps internal attributes to all registers
            self.flush_rx()
            self.flush_tx()
            self.clear_status_flags()

    def __enter__(self):
        self._reg_write(CONFIGURE, self._config & 0x7C)
        self._reg_write(RF_PA_RATE, self._rf_setup)
        self._reg_write(OPEN_PIPES, self._open_pipes)
        self._reg_write(DYN_PL_LEN, self._dyn_pl)
        self._reg_write(AUTO_ACK, self._aa)
        self._reg_write(TX_FEATURE, self._features)
        self._reg_write(SETUP_RETR, self._retry_setup)
        for i, address in enumerate(self._pipes):
            if i < 2:
                self._reg_write_bytes(RX_ADDR_P0 + i, address)
            else:
                self._reg_write(RX_ADDR_P0 + i, address)
            self._reg_write(RX_PL_LENG + i, self._pl_len)
        self._reg_write_bytes(TX_ADDRESS, self._tx_address)
        self.address_length = self._addr_len
        self.channel = self._channel
        return self

    def __exit__(self, *exc):
        self.power = 0
        return False

    # pylint: disable=no-member
    def _reg_read(self, reg):
        out_buf = bytearray([reg, 0])
        in_buf = bytearray([0, 0])
        with self._spi as spi:
            time.sleep(0.005)
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]
        return in_buf[1]

    def _reg_read_bytes(self, reg, buf_len=5):
        in_buf = bytearray(buf_len + 1)
        out_buf = bytearray([reg]) + b"\x00" * buf_len
        with self._spi as spi:
            time.sleep(0.005)
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]
        return in_buf[1:]

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
        return self._reg_read(0x03) + 2

    @address_length.setter
    def address_length(self, length):
        if 3 <= length <= 5:
            self._addr_len = int(length)
            self._reg_write(0x03, length - 2)
        else:
            raise ValueError("address length can only be set in range [3, 5] bytes")

    def open_tx_pipe(self, address):
        """This function is used to open a data pipe for OTA (over the air)
        TX transmissions."""
        if len(address) == self._addr_len:
            if self.auto_ack:
                self._pipes[0] = address
                self._reg_write_bytes(RX_ADDR_P0, address)
                self._open_pipes = self._open_pipes | 1
                self._reg_write(OPEN_PIPES, self._open_pipes)
                self._pipes[0] = address
            self._tx_address = address
            self._reg_write_bytes(TX_ADDRESS, address)
        else:
            raise ValueError(
                "address must be a buffer protocol object with a"
                " byte length\nequal to the address_length "
                "attribute (currently set to"
                " {})".format(self._addr_len)
            )

    def close_rx_pipe(self, pipe_number):
        """This function is used to close a specific data pipe from OTA (over
        the air) RX transmissions."""
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        self._open_pipes = self._reg_read(OPEN_PIPES)
        if self._open_pipes & (1 << pipe_number):
            self._open_pipes = self._open_pipes & ~(1 << pipe_number)
            self._reg_write(OPEN_PIPES, self._open_pipes)

    def open_rx_pipe(self, pipe_number, address):
        """This function is used to open a specific data pipe for OTA (over
        the air) RX transmissions."""
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0,5]")
        if len(address) != self._addr_len:
            raise ValueError(
                "address must be a buffer protocol object with a"
                " byte length\nequal to the address_length "
                "attribute (currently set to"
                " {})".format(self._addr_len)
            )
        if pipe_number < 2:
            if not pipe_number:
                self._pipe0_read_addr = address
            self._pipes[pipe_number] = address
            self._reg_write_bytes(RX_ADDR_P0 + pipe_number, address)
        else:
            self._pipes[pipe_number] = address[0]
            self._reg_write(RX_ADDR_P0 + pipe_number, address[0])
        self._open_pipes = self._reg_read(OPEN_PIPES)
        self._open_pipes = self._open_pipes | (1 << pipe_number)
        self._reg_write(OPEN_PIPES, self._open_pipes)

    @property
    def listen(self):
        """An attribute to represent the nRF24L01 primary role as a radio."""
        return self.power and bool(self._config & 1)

    @listen.setter
    def listen(self, is_rx):
        assert isinstance(is_rx, (bool, int))
        if self.listen != is_rx:
            if is_rx:
                self._start_listening()
            else:
                self._stop_listening()

    def _start_listening(self):
        if self.ce_pin.value:
            self.ce_pin.value = 0
        if self._pipe0_read_addr is not None:
            self._pipes[0] = self._pipe0_read_addr
            self._reg_write_bytes(RX_ADDR_P0, self._pipe0_read_addr)
        self._config = (self._config & 0xFC) | 3
        self._reg_write(CONFIGURE, self._config)
        time.sleep(0.00015)  # mandatory wait to power up radio
        self.flush_rx()
        self.clear_status_flags(True, False, False)
        self.ce_pin.value = 1  # mandatory pulse is > 130 µs
        time.sleep(0.00013)

    def _stop_listening(self):
        if self.ce_pin.value:
            self.ce_pin.value = 0
        self._config = self._config & 0xFE
        self._reg_write(CONFIGURE, self._config)
        time.sleep(0.00016)

    def any(self):
        """This function checks if the nRF24L01 has received any data at all,
        and then reports the next available payload's length (in bytes)."""
        self._features = self._reg_read(TX_FEATURE)
        if self.irq_dr:
            if self._features & 4:
                return self._reg_read(0x60)
            return self._reg_read(RX_PL_LENG + self.pipe)
        return 0

    def recv(self):
        """This function is used to retrieve the next available payload in the
        RX FIFO buffer, then clears the `irq_dr` status flag."""
        curr_pl_size = self.any()
        if not curr_pl_size:
            return None
        result = self._reg_read_bytes(0x61, curr_pl_size)
        self.clear_status_flags(True, False, False)
        return result

    def send(self, buf, ask_no_ack=False, force_retry=0):
        """This blocking function is used to transmit payload(s)."""
        self.ce_pin.value = 0
        self.flush_tx()
        if isinstance(buf, (list, tuple)):
            result = []
            for i, b in enumerate(buf):
                if not b or len(b) > 32:
                    raise ValueError(
                        "buf (item {} in the list/tuple) must be"
                        " a buffer protocol object with length "
                        "in range [1, 32]".format(i)
                    )
            for i, b in enumerate(buf):
                result.append(self.send(b, ask_no_ack, force_retry))
            return result
        if not buf or len(buf) > 32:
            raise ValueError(
                "buf must be a buffer protocol object with " "length in range [1, 32]"
            )
        use_ack = bool(self._aa and not ask_no_ack)
        get_ack_pl = bool(self._features & 6 == 6 and self._dyn_pl and use_ack)
        if get_ack_pl:
            self.flush_rx()
        self.write(buf, ask_no_ack)
        time.sleep(0.00001)
        self.ce_pin.value = 0
        while not self._status & 0x30:
            self.update()
        if self._retry_setup & 0x0F and self.irq_df:
            for _ in range(force_retry):
                result = self.resend()
                if result is None or result:
                    break
        else:
            result = self.irq_ds
            if get_ack_pl:
                result = self.recv()
            self.clear_status_flags(False)
        return result

    @property
    def irq_dr(self):
        """A `bool` that represents the "Data Ready" interrupted flag.
        (read-only)"""
        return bool(self._status & 0x40)

    @property
    def irq_ds(self):
        """A `bool` that represents the "Data Sent" interrupted flag.
        (read-only)"""
        return bool(self._status & 0x20)

    @property
    def irq_df(self):
        """A `bool` that represents the "Data Failed" interrupted flag.
        (read-only)"""
        return bool(self._status & 0x10)

    def clear_status_flags(self, data_recv=True, data_sent=True, data_fail=True):
        """This clears the interrupt flags in the status register."""
        self._reg_write(0x07, (data_recv << 6) | (data_sent << 5) | (data_fail << 4))

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        """Sets the configuration of the nRF24L01's IRQ (interrupt) pin."""
        self._config = self._reg_read(CONFIGURE) & 0x0F
        self._config |= (not bool(data_fail)) << 4
        self._config |= (not bool(data_sent)) << 5
        self._config |= (not bool(data_recv)) << 6
        self._reg_write(CONFIGURE, self._config)

    def what_happened(self, dump_pipes=False):
        """This debuggung function aggregates and outputs all status/condition
        related information from the nRF24L01."""
        observer = self._reg_read(8)
        print(
            "Channel___________________{} ~ {} GHz".format(
                self.channel, (self.channel + 2400) / 1000
            )
        )
        print(
            "RF Data Rate______________{} {}".format(
                self.data_rate, "Mbps" if self.data_rate != 250 else "Kbps"
            )
        )
        print("RF Power Amplifier________{} dbm".format(self.pa_level))
        print("CRC bytes_________________{}".format(self.crc))
        print("Address length____________{} bytes".format(self.address_length))
        print("Payload lengths___________{} bytes".format(self.payload_length))
        print("Auto retry delay__________{} microseconds".format(self.ard))
        print("Auto retry attempts_______{} maximum".format(self.arc))
        print(
            "Packets lost on current channel_____________________{}".format(
                (observer & 0xF0) >> 4
            )
        )
        print(
            "Retry attempts made for last transmission___________{}".format(
                observer & 0x0F
            )
        )
        print(
            "IRQ - Data Ready______{}    Data Ready___________{}".format(
                "_True" if not bool(self._config & 0x40) else "False", self.irq_dr
            )
        )
        print(
            "IRQ - Data Fail_______{}    Data Failed__________{}".format(
                "_True" if not bool(self._config & 0x20) else "False", self.irq_df
            )
        )
        print(
            "IRQ - Data Sent_______{}    Data Sent____________{}".format(
                "_True" if not bool(self._config & 0x10) else "False", self.irq_ds
            )
        )
        print(
            "TX FIFO full__________{}    TX FIFO empty________{}".format(
                "_True" if bool(self.tx_full) else "False", bool(self.fifo(True, True))
            )
        )
        print(
            "RX FIFO full__________{}    RX FIFO empty________{}".format(
                "_True" if bool(self._fifo & 2) else "False", bool(self._fifo & 1)
            )
        )
        print(
            "Ask no ACK_________{}    Custom ACK Payload___{}".format(
                "_Allowed" if bool(self._features & 1) else "Disabled",
                "Enabled" if self.ack else "Disabled",
            )
        )
        print(
            "Dynamic Payloads___{}    Auto Acknowledgment__{}".format(
                "_Enabled" if self.dynamic_payloads else "Disabled",
                "Enabled" if self.auto_ack else "Disabled",
            )
        )
        print(
            "Primary Mode_____________{}    Power Mode___________{}".format(
                "RX" if self.listen else "TX",
                ("Standby-II" if self.ce_pin.value else "Standby-I")
                if self._config & 2
                else "Off",
            )
        )
        if dump_pipes:
            print("TX address____________", self.address())
            self._open_pipes = self._reg_read(OPEN_PIPES)
            for i in range(6):
                is_open = "( open )" if self._open_pipes & (1 << i) else "(closed)"
                print("Pipe", i, is_open, "bound:", self.address(i))
                if is_open:
                    print("\t\texpecting", self._pl_len, "byte static payloads")

    @property
    def dynamic_payloads(self):
        """This `bool` attribute controls the nRF24L01's dynamic payload
        length feature."""
        self._dyn_pl = self._reg_read(DYN_PL_LEN)
        self._features = self._reg_read(TX_FEATURE)
        return bool(self._dyn_pl and (self._features & 4))

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        assert isinstance(enable, (bool, int))
        self._features = self._reg_read(TX_FEATURE)
        if bool(self._features & 4) != bool(enable):
            self._features = (self._features & 3) | (bool(enable) << 2)
            self._reg_write(TX_FEATURE, self._features)
        self._dyn_pl = 0x3F if enable else 0
        self._reg_write(DYN_PL_LEN, self._dyn_pl)

    @property
    def payload_length(self):
        """This `int` attribute specifies the length (in bytes) of payload"""
        return self._pl_len

    @payload_length.setter
    def payload_length(self, length):
        if not length or length <= 32:
            self._pl_len = length
            for i in range(6):
                self._reg_write(RX_PL_LENG + i, length)
        else:
            raise ValueError(
                "{}: payload length can only be set in range [1,"
                " 32] bytes".format(length)
            )

    @property
    def arc(self):
        """This `int` attribute specifies the nRF24L01's number of attempts
        to re-transmit TX payload when acknowledgment packet is not received.
        """
        self._retry_setup = self._reg_read(SETUP_RETR)
        return self._retry_setup & 0x0F

    @arc.setter
    def arc(self, count):
        if 0 <= count <= 15:
            if self.arc != count:
                self._retry_setup = (self._retry_setup & 0xF0) | count
                self._reg_write(SETUP_RETR, self._retry_setup)
        else:
            raise ValueError(
                "automatic re-transmit count(/attempts) must in" " range [0, 15]"
            )

    @property
    def ard(self):
        """This `int` attribute specifies the nRF24L01's delay (in
        microseconds) between attempts to automatically re-transmit the
        TX payload when an expected acknowledgement (ACK) packet is not
        received."""
        self._retry_setup = self._reg_read(SETUP_RETR)
        return ((self._retry_setup & 0xF0) >> 4) * 250 + 250

    @ard.setter
    def ard(self, delta_t):
        if 250 <= delta_t <= 4000 and delta_t % 250 == 0:
            if self.ard != delta_t:
                self._retry_setup &= 0x0F
                self._retry_setup |= int((delta_t - 250) / 250) << 4
                self._reg_write(SETUP_RETR, self._retry_setup)
        else:
            raise ValueError(
                "automatic re-transmit delay can only be a "
                "multiple of 250 in range [250, 4000]"
            )

    @property
    def auto_ack(self):
        """This `bool` attribute controls the nRF24L01's automatic
        acknowledgment feature during the process of receiving a packet."""
        self._aa = self._reg_read(AUTO_ACK)
        return bool(self._aa)

    @auto_ack.setter
    def auto_ack(self, enable):
        assert isinstance(enable, (bool, int))
        self._aa = 0x3F if enable else 0
        self._reg_write(AUTO_ACK, self._aa)

    @property
    def ack(self):
        """This `bool` attribute represents the status of the nRF24L01's
        capability to use custom payloads as part of the automatic
        acknowledgment (ACK) packet."""
        self._aa = self._reg_read(AUTO_ACK)
        self._dyn_pl = self._reg_read(DYN_PL_LEN)
        self._features = self._reg_read(TX_FEATURE)
        return bool((self._features & 6) == 6 and self._aa and self._dyn_pl)

    @ack.setter
    def ack(self, enable):
        assert isinstance(enable, (bool, int))
        if self.ack != bool(enable):
            self.auto_ack = True
            self._dyn_pl = 0x3F
            self._reg_write(DYN_PL_LEN, self._dyn_pl)
        self._features = (self._features & 5) | (6 if enable else 0)
        self._reg_write(TX_FEATURE, self._features)

    def load_ack(self, buf, pipe_number):
        """This allows the MCU to specify a payload to be allocated into the
        TX FIFO buffer for use on a specific data pipe."""
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0, 5]")
        if not buf or len(buf) > 32:
            raise ValueError(
                "buf must be a buffer protocol object with " "length in range [1, 32]"
            )
        if not bool((self._features & 6) == 6 and self._aa and self._dyn_pl):
            self.ack = True
        if not self.tx_full:
            self._reg_write_bytes(0xA8 | pipe_number, buf)
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
        self._rf_setup = self._reg_read(RF_PA_RATE)
        if self._rf_setup & 0x28:
            if self._rf_setup & 0x28 == 8:
                return 2
            return 250
        return 1

    @data_rate.setter
    def data_rate(self, speed):
        if speed in (1, 2, 250):
            if self.data_rate != speed:
                speed = 0 if speed == 1 else (8 if speed == 2 else 0x20)
            self._rf_setup = self._rf_setup & 0xD7 | speed
            self._reg_write(RF_PA_RATE, self._rf_setup)
        else:
            raise ValueError(
                "data rate must be one of the following " "([M,M,K]bps): 1, 2, 250"
            )

    @property
    def channel(self):
        """This `int` attribute specifies the nRF24L01's frequency."""
        return self._reg_read(0x05)

    @channel.setter
    def channel(self, channel):
        if 0 <= channel <= 125:
            self._channel = channel
            self._reg_write(0x05, channel)
        else:
            raise ValueError("channel acn only be set in range [0, 125]")

    @property
    def crc(self):
        """This `int` attribute specifies the nRF24L01's CRC (cyclic
        redundancy checking) encoding scheme in terms of byte length."""
        self._config = self._reg_read(CONFIGURE)
        return max(0, ((self._config & 0x0C) >> 2) - 1)

    @crc.setter
    def crc(self, length):
        if 0 <= length <= 2:
            if self.crc != length:
                length = (length + 1) << 2 if length else 0
                self._config = self._config & 0x73 | length
                self._reg_write(0, self._config)
        else:
            raise ValueError("CRC byte length must be an int equal to 0 (off), 1, or 2")

    @property
    def power(self):
        """This `bool` attribute controls the power state of the nRF24L01."""
        return bool(self._config & 2)

    @power.setter
    def power(self, is_on):
        assert isinstance(is_on, (bool, int))
        self._config = self._reg_read(CONFIGURE)
        if self.power != bool(is_on):
            self._config = (self._config & 0x7D) | (bool(is_on) << 1)
            self._reg_write(CONFIGURE, self._config)
            time.sleep(0.00016)

    @property
    def pa_level(self):
        """This `int` attribute specifies the nRF24L01's power amplifier
        level (in dBm)."""
        self._rf_setup = self._reg_read(RF_PA_RATE)
        return (3 - ((self._rf_setup & RF_PA_RATE) >> 1)) * -6

    @pa_level.setter
    def pa_level(self, power):
        if power in (-18, -12, -6, 0):
            power = (3 - int(power / -6)) * 2
            if self.pa_level != power:
                self._rf_setup = (self._rf_setup & 0xF9) | power
                self._reg_write(RF_PA_RATE, self._rf_setup)
        else:
            raise ValueError(
                "power amplitude must be one of the following " "(dBm): -18, -12, -6, 0"
            )

    @property
    def rpd(self):
        """This read-only attribute returns `True` if RPD (Received Power
        Detector) is triggered or `False` if not triggered."""
        return bool(self._reg_read(0x09))

    @property
    def tx_full(self):
        """An attribute to represent the nRF24L01's status flag signaling
        that the TX FIFO buffer is full. (read-only)"""
        return bool(self._status & 1)

    def update(self):
        """This function is only used to get an updated status byte over SPI
        from the nRF24L01."""
        self._reg_write(0xFF)

    def resend(self):
        """Use this function to maunally re-send the previous payload in the
        top level (first out) of the TX FIFO buffer."""
        result = False
        if not self.fifo(True, True):
            get_ack_pl = bool(
                self._features & 6 == 6 and self._aa & 1 and self._dyn_pl & 1
            )
            if get_ack_pl:
                self.flush_rx()
            self.clear_status_flags(get_ack_pl)
            self._reg_write(0xE3)
            self.ce_pin.value = 0
            self.ce_pin.value = 1
            time.sleep(0.00001)
            self.ce_pin.value = 0
            while not self._status & 0x30:
                self.update()
            result = self.irq_ds
            if get_ack_pl:
                result = self.recv()  # get ACK payload
            self.clear_status_flags(False)
        return result

    def write(self, buf, ask_no_ack=False):
        """This non-blocking function (when used as alternative to `send()`)
        is meant for asynchronous applications and can only handle one
        payload at a time as it is a helper function to `send()`."""
        if not buf or len(buf) > 32:
            raise ValueError(
                "buf must be a buffer protocol object with " "length in range [1, 32]"
            )
        self.clear_status_flags(
            bool(self._features & 6 == 6 and self._aa and self._dyn_pl)
        )
        if self._config & 3 != 2:  # is radio powered up in TX mode?
            self._config = (self._reg_read(CONFIGURE) & 0x7C) | 2
            self._reg_write(CONFIGURE, self._config)
            time.sleep(0.00016)
        if not bool((self._dyn_pl & 1) and (self._features & 4)):
            if len(buf) < self._pl_len:
                for _ in range(self._pl_len - len(buf)):
                    buf += b"\x00"
            elif len(buf) > self._pl_len:
                buf = buf[: self._pl_len]
        if ask_no_ack:
            if self._features & 1 == 0:
                self._features = self._features & 0xFE | 1
                self._reg_write(TX_FEATURE, self._features)
        self._reg_write_bytes(0xA0 | (ask_no_ack << 4), buf)
        self.ce_pin.value = 1

    def flush_rx(self):
        """A helper function to flush the nRF24L01's RX FIFO buffer."""
        self._reg_write(0xE2)

    def flush_tx(self):
        """A helper function to flush the nRF24L01's TX FIFO buffer."""
        self._reg_write(0xE1)

    def fifo(self, about_tx=False, check_empty=None):
        """This provides some precision determining the status of the TX/RX
        FIFO buffers. (read-only)"""
        if (check_empty is None and isinstance(about_tx, (bool, int))) or (
                isinstance(check_empty, (bool, int)) and isinstance(about_tx, (bool, int))
        ):
            self._fifo = self._reg_read(0x17)
            mask = 4 * about_tx
            if check_empty is None:
                return (self._fifo & (0x30 if about_tx else 0x03)) >> mask
            return bool(self._fifo & ((2 - check_empty) << mask))
        raise ValueError(
            "Argument 1 ('about_tx') must always be a bool or "
            "int. Argument 2 ('check_empty'), if specified, must"
            " be a bool or int"
        )

    @property
    def pipe(self):
        """The identifying number of the data pipe that received
        the next available payload in the RX FIFO buffer. (read only)"""
        result = (self._status & 0x0E) >> 1
        if result <= 5:
            return result
        return None

    def address(self, index=-1):
        """Returns the current address set to a specified data pipe or the TX
        address. (read-only)"""
        if index > 5:
            raise IndexError("index {} is out of bounds [0,5]".format(index))
        if index < 0:
            return self._tx_address
        if index <= 1:
            return self._pipes[index]
        return bytes(self._pipes[index]) + self._pipes[1][1:]
