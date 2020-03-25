# see license and copyright information in rf24.py of this directory
# pylint: disable=missing-class-docstring,missing-function-docstring,missing-module-docstring
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/2bndy5/CircuitPython_nRF24L01.git"
import time
from adafruit_bus_device.spi_device import SPIDevice

class RF24:
    def __init__(self, spi, csn, ce):
        self._pipe0_read_addr = None
        self._status = 0
        self._payload_length = 32
        self.ce_pin = ce
        self.ce_pin.switch_to_output(value=False)
        self._spi = SPIDevice(spi, chip_select=csn, baudrate=1250000)
        self._reg_write(0, 0x0E)
        if self._reg_read(0) & 3 == 2:
            self.power = False
        else:
            raise RuntimeError("nRF24L01 Hardware not responding")
        self.channel = 76
        self._reg_write(3, 3)
        self._reg_write(6, 6)
        self._reg_write(2, 0)
        self._reg_write(0x1C, 0x3F)
        self._reg_write(1, 0x3F)
        self._reg_write(0x1D, 5)
        self._reg_write(4, 0x53)

        self.flush_rx()
        self.flush_tx()
        self.clear_status_flags()

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

    def open_tx_pipe(self, address):
        if len(address) == 5:
            self._reg_write_bytes(0x0A, address)
            self._reg_write(2, self._reg_read(2) | 1)
            self._reg_write(0x11, self.payload_length)
            self._reg_write_bytes(0x10, address)
        else:
            raise ValueError(
                "address must be a buffer protocol object with a byte length\nequal "
                "to the address_length attribute (currently set to 5)")

    def close_rx_pipe(self, pipe_number):
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0, 5]")
        open_pipes = self._reg_read(2)
        if open_pipes & (1 << pipe_number):
            self._reg_write(2, open_pipes & ~(1 << pipe_number))

    def open_rx_pipe(self, pipe_number, address):
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0, 5]")
        if len(address) != 5:
            raise ValueError(
                "address must be a buffer protocol object with a byte length\nequal "
                "to the address_length attribute (currently set to 5)")
        if pipe_number < 2:
            if not pipe_number:
                self._pipe0_read_addr = address
            self._reg_write_bytes(0x0A + pipe_number, address)
        else:
            self._reg_write(0x0A + pipe_number, address[0])
        self._reg_write(2, self._reg_read(2) | (1 << pipe_number))
        self._reg_write(0x11 + pipe_number, self._payload_length)

    @property
    def listen(self):
        return (self._reg_read(0) & 3) == 3

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
            self._reg_write_bytes(0x0A, self._pipe0_read_addr)
        self._reg_write(0, self._reg_read(0) & 0xFC | 3)
        time.sleep(0.00015)
        self.flush_rx()
        self.clear_status_flags(True, False, False)
        self.ce_pin.value = 1
        time.sleep(0.00013)

    def _stop_listening(self):
        if self.ce_pin.value:
            self.ce_pin.value = 0
        self._reg_write(0, self._reg_read(0) & 0xFE)
        time.sleep(0.00016)

    def any(self):
        if self._reg_read(0x1D) & 4:
            return self._reg_read(0x60)
        if self.irq_dr:
            return self._reg_read(0x11 + ((self._status & 0xE) >> 1))
        return 0

    def recv(self):
        pl_wid = self.any()
        result = self._reg_read_bytes(0x61, pl_wid)
        self.clear_status_flags(True, False, False)
        return result

    def send(self, buf, ask_no_ack=False, force_retry=0):
        self.ce_pin.value = 0
        self.flush_tx()
        if isinstance(buf, (list, tuple)):
            result = []
            for i, b in enumerate(buf):
                if not b or len(b) > 32:
                    raise ValueError(
                        "buf (item {} in the list/tuple) must be a"
                        " buffer protocol object with length in range [1, 32]" % i)
            for i, b in enumerate(buf):
                result.append(self.send(b, ask_no_ack, force_retry))
            return result
        if not buf or len(buf) > 32:
            raise ValueError(
                "buf must be a buffer protocol object with length in range [1, 32]")
        arc_d = self._reg_read(4)
        need_ack = bool((arc_d & 0xF) and not ask_no_ack)
        t_ack = 0
        if need_ack:
            t_ack = 329 / 250000
        t_retry = ((arc_d >> 4) * 250 + 380) * (arc_d & 0xF) / 1000000
        timeout = (
            (((8 * (len(buf) + 8)) + 9) / 250000)
            + (1 + need_ack) * 0.00013 + 0.0000082 + t_retry + t_ack)
        self.write(buf, ask_no_ack)
        time.sleep(0.00001)
        self.ce_pin.value = 0
        start = time.monotonic()
        while not (self._status & 0x30) and (time.monotonic() - start) < timeout:
            self.update()
        if need_ack and self.irq_df:
            for _ in range(force_retry):
                result = self.resend()
                if result is None or result:
                    break
        else:
            result = self.irq_ds
            if self._reg_read(0x1D) & 2 and self.irq_dr and not ask_no_ack:
                result = self.recv()
            self.clear_status_flags(False)
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
        self._reg_write(7, (data_recv << 6) | (data_sent << 5) | (data_fail << 4))

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        config = self._reg_read(0) & 0x0F
        config |= (not data_fail << 4) | (not data_sent << 5) | (not data_recv << 6)
        self._reg_write(0, config)

    @property
    def dynamic_payloads(self):
        return bool(self._reg_read(0x1D) & 4)

    @dynamic_payloads.setter
    def dynamic_payloads(self, enable):
        assert isinstance(enable, (bool, int))
        features = self._reg_read(0x1D)
        if bool(features & 4) != enable:
            features = (features & 3) | (enable << 2)
            self._reg_write(0x1D, features)
        self._reg_write(0x1C, 0x3F if enable else 0)

    @property
    def payload_length(self):
        return self._payload_length

    @payload_length.setter
    def payload_length(self, length):
        # max payload size is 32 bytes
        if not length or length <= 32:
            self._payload_length = length
        else:
            raise ValueError("{}: payload length can only be in range [1, 32] bytes" % length)

    @property
    def arc(self):
        return self._reg_read(4) & 0x0F

    @arc.setter
    def arc(self, count):
        if 0 <= count <= 15:
            setup_retr = self._reg_read(4)
            if setup_retr & 0x0F != count:
                setup_retr = (setup_retr & 0xF0) | count
                self._reg_write(4, setup_retr)
        else:
            raise ValueError("automatic re-transmit count must in range [0, 15]")

    @property
    def ard(self):
        return ((self._reg_read(4) & 0xF0) >> 4) * 250 + 250

    @ard.setter
    def ard(self, delta_t):
        if 250 <= delta_t <= 4000 and delta_t % 250 == 0:
            setup_retr = self._reg_read(4)
            if ((setup_retr & 0xF0) >> 4) * 250 + 250 != delta_t:
                setup_retr = (int((delta_t - 250) / 250) << 4) | (setup_retr & 0x0F)
                self._reg_write(4, setup_retr)
        else:
            raise ValueError(
                "automatic re-transmit delay must be a multiple of 250 in range [250,4000]")

    @property
    def ack(self):
        return bool((self._reg_read(0x1D) & 6) and self._reg_read(1))

    @ack.setter
    def ack(self, enable):
        assert isinstance(enable, (bool, int))
        features = self._reg_read(0x1D) & 5
        if enable:
            self._reg_write(1, 0x3F)
            self._reg_write(0x1C, 0x3F)
            features = (features & 3) | 4
        features |= (2 if enable else 0)
        self._reg_write(0x1D, features)

    def load_ack(self, buf, pipe_number):
        if pipe_number < 0 or pipe_number > 5:
            raise ValueError("pipe number must be in range [0, 5]")
        if not buf or len(buf) > 32:
            raise ValueError(
                "buf must be a buffer protocol object with length in range [1, 32]")
        if not self._reg_read(0x1D) & 2:
            self.ack = True
        if not self._status & 1:
            self._reg_write_bytes(0xA8 | pipe_number, buf)
            return True
        return False

    @property
    def data_rate(self):
        rf_setup = self._reg_read(6) & 0x28
        return (2 if rf_setup == 8 else 250) if rf_setup else 1

    @data_rate.setter
    def data_rate(self, speed):
        if speed in (1, 2, 250):
            speed = 0 if speed == 1 else (8 if speed == 2 else 0x20)
            rf_setup = self._reg_read(6)
            if ((2 if rf_setup == 8 else 250) if rf_setup else 1) != speed:
                rf_setup = (rf_setup & 0xD7) | speed
                self._reg_write(6, rf_setup)
        else:
            raise ValueError(
                "data rate must be one of the following ([M,M,K]bps): 1, 2, 250")

    @property
    def channel(self):
        return self._reg_read(5)

    @channel.setter
    def channel(self, channel):
        if 0 <= channel <= 125:
            self._reg_write(5, channel)
        else:
            raise ValueError("channel acn only be set in range [0,125]")

    @property
    def power(self):
        return bool(self._reg_read(0) & 2)

    @power.setter
    def power(self, is_on):
        assert isinstance(is_on, (bool, int))
        config = self._reg_read(0)
        if bool(config & 2) != is_on:
            config = (config & 0x7D) | (is_on << 1)
            self._reg_write(0, config)
            # power up/down takes < 150 µs + 4 µs
            time.sleep(0.00016)

    @property
    def pa_level(self):
        rf_setup = self._reg_read(6)
        return (3 - ((rf_setup & 6) >> 1)) * -6

    @pa_level.setter
    def pa_level(self, power):
        if power in (-18, -12, -6, 0):
            power = (3 - int(power / -6)) * 2
            rf_setup = (self._reg_read(6) & 0xF9) | power
            self._reg_write(6, rf_setup)
        else:
            raise ValueError(
                "power amplitude must be one of the following (dBm): -18, -12, -6, 0")

    def update(self):
        self._reg_write(0xFF)

    def resend(self):
        result = False
        if not self._reg_read(0x17) & 0x10:
            self.clear_status_flags(False)
            self._reg_write(0xE3)
            arc_d = self._reg_read(4)
            t_retry = ((arc_d >> 4) * 250 + 380) * (arc_d & 0xF) / 1000000
            timeout = (329 / 125000 + 0.0002682 + t_retry)
            self.ce_pin.value = 0
            self.ce_pin.value = 1
            time.sleep(0.00001)
            self.ce_pin.value = 0
            start = time.monotonic()
            while not (self._status & 0x30) and (time.monotonic() - start) < timeout:
                self.update()
            result = self.irq_ds
            if self._reg_read(0x1D) & 2 and self.irq_dr:
                result = self.recv()
            self.clear_status_flags(False)
        return result

    def write(self, buf, ask_no_ack=False):
        if not buf or len(buf) > 32:
            raise ValueError(
                "buf must be a buffer protocol object with length in range [1, 32]")
        self.clear_status_flags(False)
        config = self._reg_read(0)
        if config & 3 != 2:
            self._reg_write(0, (config & 0x7C) | 2)
            time.sleep(0.00016)
        if not self.dynamic_payloads:
            if len(buf) < self.payload_length:
                for _ in range(self.payload_length - len(buf)):
                    buf += b"\x00"
            elif len(buf) > self.payload_length:
                buf = buf[: self.payload_length]
        self._reg_write_bytes(0xA0 | (ask_no_ack << 4), buf)
        self.ce_pin.value = 1

    def flush_rx(self):
        self._reg_write(0xE2)

    def flush_tx(self):
        self._reg_write(0xE1)
