"""Import wrappers where applicable/available. This script tries to find:

1. MicroPython's `machine.Pin()`
2. ``RPi.GPIO`` for use with DigitalIO and ``spidev`` for CPython on Linux
3. Falls back to CircuitPython API for either MCUs or Linux SoC modules
   without the above libraries present.

Logging can be achieved by having `adafruit_logging` module or
MicroPython ``logging`` module present in the MCU's ``lib`` folder.
"""
from .wrapper import DigitalInOut, SPIDevice, SPIDevCtx
logging = None  # pylint: disable=invalid-name
try:
    import logging

    logging.basicConfig()
except ImportError:
    try:
        import adafruit_logging as logging
    except ImportError:
        pass  # print("nrf24l01: Logging disabled")


def address_repr(addr):
    """Convert a bytearray into a hexlified string (in big endian)."""
    rev_str = ""
    for char in range(len(addr) - 1, -1, -1):
        rev_str += ("" if addr[char] > 0x0F else "0") + hex(addr[char])[2:]
    return rev_str

# pylint: disable=missing-class-docstring

class CEMixin:
    def __init__(self, ce_pin):
        self._ce_pin = ce_pin
        if ce_pin is not None:
            if not isinstance(ce_pin, DigitalInOut):
                self._ce_pin = DigitalInOut(ce_pin)
            self._ce_pin.switch_to_output(value=False)  # pre-empt standby-I mode
        super().__init__()

    @property
    def ce_pin(self):
        """control the CE pin (for adbanced usage)"""
        return self._ce_pin.value if self._ce_pin is not None else False

    @ce_pin.setter
    def ce_pin(self, val):
        if self._ce_pin is not None:
            self._ce_pin.value = val


class HWMixin(CEMixin):
    def __init__(self, spi, csn, ce_pin, spi_frequency):
        self._spi = None
        if spi is not None:
            if type(spi).__name__.startswith("SpiDev"):
                self._spi = SPIDevCtx(spi, csn, spi_frequency=spi_frequency)
            else:
                if type(csn).__name__.startswith("Pin"):
                    csn = DigitalInOut(csn)
                self._spi = SPIDevice(
                    spi, chip_select=csn, baudrate=spi_frequency, extra_clocks=8
                )
        self._status = 0  # status byte returned on all SPI transactions
        super().__init__(ce_pin)

    # pylint: disable=no-member
    def _reg_read(self, reg):
        in_buf = bytearray([0, 0])
        out_buf = bytes([reg, 0])
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

    def _reg_write(self, reg, value=None):
        out_buf = bytes([reg])
        if value is not None:
            out_buf = bytes([0x20 | reg, value])
        in_buf = bytearray(len(out_buf))
        with self._spi as spi:
            spi.write_readinto(out_buf, in_buf)
        self._status = in_buf[0]

    # pylint: enable=no-member


class HWLogMixin(HWMixin):
    def __init__(self, spi, csn, ce_pin, spi_frequency):
        super().__init__(spi, csn, ce_pin, spi_frequency)
        self._logger = None
        if logging is not None:
            self._logger = logging.getLogger(type(self).__name__)
            self._logger.setLevel(logging.DEBUG if spi is None else logging.INFO)

    @property
    def logger(self):
        """Get/Set the current ``Logger()``."""
        return self._logger

    @logger.setter
    def logger(self, val):
        if logging is not None and isinstance(val, logging.Logger):
            self._logger = val

    def _log(self, level, prompt, force_print=False):
        if self.logger is not None:
            self.logger.log(level, prompt)
        elif force_print:
            print(prompt)

    def _reg_read(self, reg):
        result = 0 if self._spi is None else super()._reg_read(reg)
        if self.logger is not None:
            self._log(
                10, "SPI reading 1 byte  from {} {}".format(hex(reg), hex(result))
            )
        return result

    def _reg_read_bytes(self, reg, buf_len=5):
        result = bytearray([0] * buf_len)
        if self._spi is not None:
            result = super()._reg_read_bytes(reg, buf_len=buf_len)
        if self.logger is not None:
            self._log(10, "SPI reading {} bytes from {} {}".format(
                buf_len, hex(reg), "0x" + address_repr(result)
            ))
        return result

    def _reg_write_bytes(self, reg, out_buf):
        if self.logger is not None:
            prompt = "SPI writing {} bytes to {} {}".format(
                len(out_buf), hex(reg), "0x" + address_repr(out_buf)
            )
            self._log(10, prompt)
        if self._spi is not None:
            super()._reg_write_bytes(reg, out_buf)

    def _reg_write(self, reg, value=None):
        if self.logger is not None and reg != 0xFF:
            prompt = "SPI writing "
            if value is not None:
                prompt += "1 byte  to {} {}".format(hex(reg), hex(value))
            else:
                prompt += "command {}".format(hex(reg))
            self._log(10, prompt)
        if self._spi is not None:
            super()._reg_write(reg, value)
