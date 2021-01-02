# see license and copyright information in rf24.py
# pylint: disable=missing-docstring
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import time
from adafruit_bus_device.spi_device import SPIDevice


class RF24:
    def __init__(self, spi, csn, ce, spi_frequency=10000000):
        self._spi = SPIDevice(
            spi, chip_select=csn, baudrate=spi_frequency, extra_clocks=8
        )
        self.ce_pin = ce
        self.ce_pin.switch_to_output(value=False)
        self._status = 0
        self._reg_write(0, 0x0E)
        if self._reg_read(0) & 3 != 2:
            raise RuntimeError("nRF24L01 Hardware not responding")
        self._reg_write(3, 3)
        self._reg_write(6, 7)
        self._reg_write(2, 0)
        self._reg_write(0x1C, 0x3F)
        self._reg_write(1, 0x3F)
        self._reg_write(0x1D, 5)
        self._reg_write(4, 0x53)
        self._pipe0_read_addr = None
        self.channel = 76
        self.payload_length = 32
        self.flush_rx()
        self.flush_tx()
        self.clear_status_flags()

    # pylint: disable=no-member
    def _reg_read(self, reg):
        out_buf = bytes([reg, 0])
        in_buf = bytearray([0, 0])
        with self._spi as spi:
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]
        return in_buf[1]

    def _reg_read_bytes(self, reg, buf_len=5):
        in_buf = bytearray(buf_len + 1)
        out_buf = bytes([reg]) + b"\0" * buf_len
        with self._spi as spi:
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]
        return in_buf[1:]

    def _reg_write_bytes(self, reg, out_buf):
        out_buf = bytes([0x20 | reg]) + out_buf
        in_buf = bytearray(len(out_buf))
        with self._spi as spi:
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]

    def _reg_write(self, reg, val=None):
        out_buf = bytes([reg])
        if val is not None:
            out_buf = bytes([0x20 | reg, val])
        in_buf = bytearray(len(out_buf))
        with self._spi as spi:
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]

    # pylint: enable=no-member
    @property
    def address_length(self):
        return self._reg_read(0x03) + 2

    @address_length.setter
    def address_length(self, length):
        if not 3 <= length <= 5:
            raise ValueError("address_length must be in range [3, 5]")
        self._reg_write(0x03, length - 2)

    def open_tx_pipe(self, addr):
        self._reg_write_bytes(0x0A, addr)
        self._reg_write_bytes(0x10, addr)

    def close_rx_pipe(self, pipe_num):
        if pipe_num < 0 or pipe_num > 5:
            raise ValueError("pipe_number must be in range [0, 5]")
        open_pipes = self._reg_read(2)
        if open_pipes & (1 << pipe_num):
            self._reg_write(2, open_pipes & ~(1 << pipe_num))

    def open_rx_pipe(self, pipe_num, addr):
        if not 0 <= pipe_num <= 5:
            raise ValueError("pipe_number must be in range [0, 5]")
        if not addr:
            raise ValueError("address length cannot be 0")
        if pipe_num < 2:
            if not pipe_num:
                self._pipe0_read_addr = addr
            self._reg_write_bytes(0x0A + pipe_num, addr)
        else:
            self._reg_write(0x0A + pipe_num, addr[0])
        self._reg_write(2, self._reg_read(2) | (1 << pipe_num))

    @property
    def listen(self):
        return self._reg_read(0) & 3 == 3

    @listen.setter
    def listen(self, is_rx):
        self.ce_pin.value = 0
        if is_rx:
            if self._pipe0_read_addr is not None:
                self._reg_write_bytes(0x0A, self._pipe0_read_addr)
            else:
                self.close_rx_pipe(0)
            self._reg_write(0, (self._reg_read(0) & 0xFC) | 3)
            time.sleep(0.00015)
            self.clear_status_flags()
            self.ce_pin.value = 1
            time.sleep(0.00013)
        else:
            if self._reg_read(0x1D) & 6 == 6:
                self.flush_tx()
            self._reg_write(0, self._reg_read(0) & 0xFE | 2)
            self._reg_write(2, self._reg_read(2) | 1)
            time.sleep(0.00016)

    def available(self):
        return self.update() and self.pipe is not None

    def any(self):
        if self._reg_read(0x1D) & 4 and self.pipe is not None:
            return self._reg_read(0x60)
        if self.pipe is not None:
            return self._reg_read(0x11 + self.pipe)
        return 0

    def read(self, length=None):
        ret_size = length if length is not None else self.any()
        if not ret_size:
            return None
        result = self._reg_read_bytes(0x61, ret_size)
        self.clear_status_flags(True, False, False)
        return result

    def send(self, buf, ask_no_ack=False, force_retry=0, send_only=False):
        self.ce_pin.value = 0
        if isinstance(buf, (list, tuple)):
            result = []
            for b in buf:
                result.append(self.send(b, ask_no_ack, force_retry, send_only))
            return result
        self.flush_tx()
        if not send_only and self.pipe is not None:
            self.flush_rx()
        self.write(buf, ask_no_ack)
        while not self._status & 0x70:
            self.update()
        self.ce_pin.value = 0
        result = self.irq_ds
        if self.irq_df:
            for _ in range(force_retry):
                result = self.resend(send_only)
                if result is None or result:
                    break
        if self._status & 0x60 == 0x60 and not send_only:
            result = self.read()
        return result

    @property
    def tx_full(self):
        return bool(self._status & 1)

    @property
    def pipe(self):
        result = (self._status & 0x0E) >> 1
        if result <= 5:
            return result
        return None

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
        config = bool(data_recv) << 6 | bool(data_sent) << 5 | bool(data_fail) << 4
        self._reg_write(7, config)

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        config = (not data_recv) << 6 | (not data_fail) << 4 | (not data_sent) << 5
        self._reg_write(0, (self._reg_read(0) & 0x0F) | config)

    @property
    def dynamic_payloads(self):
        return self._reg_read(0x1D) & 4 == 4

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        self._reg_write(0x1D, (self._reg_read(0x1D) & 3) | bool(enable) << 2)
        self._reg_write(0x1C, 0x3F if enable else 0)

    @property
    def payload_length(self):
        return self._reg_read(0x11)

    @payload_length.setter
    def payload_length(self, length):
        for i in range(6):
            self._reg_write(0x11 + i, max(1, min(32, length)))

    @property
    def arc(self):
        return self._reg_read(4) & 0x0F

    @arc.setter
    def arc(self, cnt):
        self._reg_write(4, (self._reg_read(4) & 0xF0) | max(0, min(int(cnt), 15)))

    @property
    def ard(self):
        return ((self._reg_read(4) & 0xF0) >> 4) * 250 + 250

    @ard.setter
    def ard(self, delta):
        delta = max(250, min(delta, 4000))
        self._reg_write(4, (self._reg_read(4) & 0x0F) | int((delta - 250) / 250) << 4)

    @property
    def ack(self):
        return self._reg_read(0x1D) & 6 == 6 and bool(self._reg_read(0x1C))

    @ack.setter
    def ack(self, enable):
        features = self._reg_read(0x1D) & 5
        if enable:
            self._reg_write(0x1C, 0x3F)
            features = features | 4
        features |= 2 if enable else 0
        self._reg_write(0x1D, features)

    def load_ack(self, buf, pipe_num):
        if 0 <= pipe_num <= 5 and (not buf or (len(buf) < 32)):
            if not self._reg_read(0x1D) & 2:
                self.ack = True
            if not self.tx_full:
                self._reg_write_bytes(0xA8 | pipe_num, buf)
                return True
        return False

    @property
    def data_rate(self):
        rf_setup = self._reg_read(6) & 0x28
        return (2 if rf_setup == 8 else 250) if rf_setup else 1

    @data_rate.setter
    def data_rate(self, speed):
        speed = 0 if speed == 1 else (0x20 if speed != 2 else 8)
        self._reg_write(6, (self._reg_read(6) & 0xD7) | speed)

    @property
    def channel(self):
        return self._reg_read(5)

    @channel.setter
    def channel(self, chnl):
        if not 0 <= int(chnl) <= 125:
            raise ValueError("channel must be in range [0, 125]")
        self._reg_write(5, int(chnl))

    @property
    def power(self):
        return bool(self._reg_read(0) & 2)

    @power.setter
    def power(self, is_on):
        config = self._reg_read(0)
        if bool(config & 2) != bool(is_on):
            self._reg_write(0, config & 0x7D | bool(is_on) << 1)
            time.sleep(0.00016)

    @property
    def pa_level(self):
        return (3 - ((self._reg_read(6) & 6) >> 1)) * -6

    @pa_level.setter
    def pa_level(self, pwr):
        if pwr not in (-18, -12, -6, 0):
            raise ValueError("pa_level must be -18, -12, -6, or 0")
        self._reg_write(6, self._reg_read(6) & 0xF8 | (3 - int(pwr / -6)) * 2 | 1)

    def update(self):
        self._reg_write(0xFF)
        return True

    def resend(self, send_only=False):
        result = False
        if not self.fifo(True, True):
            self.ce_pin.value = 0
            if not send_only and self.pipe is not None:
                self.flush_rx()
            self.clear_status_flags()
            self._reg_write(0xE3)
            self.ce_pin.value = 1
            while not self._status & 0x30:
                self.update()
            self.ce_pin.value = 0
            result = self.irq_ds
            if self._status & 0x60 == 0x60 and not send_only:
                result = self.read()
        return result

    def write(self, buf, ask_no_ack=False, write_only=False):
        if not buf or len(buf) > 32:
            raise ValueError("buffer length must be in range [1, 32]")
        self.clear_status_flags()
        if self.tx_full:
            return False
        config = self._reg_read(0)
        if config & 3 != 2:
            self._reg_write(0, (config & 0x7C) | 2)
            time.sleep(0.00016)
        if not self.dynamic_payloads:
            pl_width = self.payload_length
            if len(buf) < pl_width:
                buf += b"\0" * pl_width - len(buf)
            elif len(buf) > pl_width:
                buf = buf[:pl_width]
        self._reg_write_bytes(0xA0 | (bool(ask_no_ack) << 4), buf)
        if not write_only:
            self.ce_pin.value = 1
        return True

    def flush_rx(self):
        self._reg_write(0xE2)

    def flush_tx(self):
        self._reg_write(0xE1)

    def fifo(self, about_tx=False, check_empty=None):
        _fifo, about_tx = (self._reg_read(0x17), bool(about_tx))
        if check_empty is None:
            return (_fifo & (0x30 if about_tx else 0x03)) >> (4 * about_tx)
        return bool(_fifo & ((2 - bool(check_empty)) << (4 * about_tx)))

    @property
    def rpd(self):
        return bool(self._reg_read(0x09))
