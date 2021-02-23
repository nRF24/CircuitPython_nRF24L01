"""This module contains a wrapper class for `spidev.SpiDev` in CPython on Linux"""


class SPIDevCtx:
    """A wrapper class to allow using the spidev module on linux and
    circuitpython's API and context manager."""

    def __init__(self, spi, csn, spi_frequency=10000000):
        self._spi = spi
        self._baudrate = spi_frequency
        self._no_cs = False
        self._bus, self._dev = (0, 0)
        self._csn = csn
        if isinstance(csn, int):
            self._bus, self._dev = (int(csn / 10), csn % 10)
        else:
            self._no_cs = True
            if isinstance(csn, (tuple, list)):
                self._bus, self._dev = (int(csn[0] / 10), csn[0] % 10)
                self._csn = csn[1]
            self._csn.switch_to_output()

    def __enter__(self):
        self._spi.open(self._bus, self._dev)
        self._spi.no_cs = self._no_cs
        if self._no_cs:
            self._csn.value = 0
        return self

    def __exit__(self, *excs):
        if self._no_cs:
            self._csn.value = 1
        self._spi.close()
        return False

    def write_readinto(self, out_buf, in_buf):
        """wraps ``spidev.SpiDev.xfer2()`` into MicroPython compatible
        ``spi.write_readinto()`` calls.

        .. warning:: The ``in_buf`` parameter must be a mutable bytearray.
        """
        in_buf[:] = bytearray(self._spi.xfer2(out_buf, self._baudrate))
