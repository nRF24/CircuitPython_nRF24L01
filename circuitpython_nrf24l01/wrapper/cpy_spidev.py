# The MIT License (MIT)
#
# Copyright (c) 2020 Brendan Doherty
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
"""This module contains a wrapper class for `spidev.SpiDev` in CPython on Linux"""


class SPIDevCtx:
    """A wrapper class to allow using the spidev module on linux and
    circuitpython's API and context manager.

    :param ~spidev.SpiDev spi: The instance of a ``SpiDev`` object.
    :param int,list,tuple csn: The CE pin number (``0``, ``1``, or ``2``) to
        use as the SPI device's CSN pin. For advanced users, a `list` or `tuple`
        can instead be used to specify a bus number and a pin number that isn't
        controlled by the SPIDEV kernel. Where index ``0`` is the bus number
        multiplied by 10, and index ``1`` is the pin number.
    :param int spi_frequency: the SPI frequency to use for the SPI device.
        Defaults to 10MHz.
    """

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

    def write_readinto(self, out_buf, in_buf, in_end: int = None, out_end: int = None):
        """wraps ``spidev.SpiDev.xfer2()`` into MicroPython compatible
        ``spi.write_readinto()`` calls.

        .. warning:: The ``in_buf`` parameter must be a mutable `bytearray`.
            The ``out_buf`` can be either a `bytes` or `bytearray` object.
        """
        out_end = out_end if out_end is not None else len(out_buf)
        in_end = in_end if in_end is not None else len(in_buf)
        in_buf[:in_end] = bytearray(self._spi.xfer2(out_buf[:out_end], self._baudrate))
