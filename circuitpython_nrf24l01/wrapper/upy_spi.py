
# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
This module adds MicroPython supportvia a wrapper class that adds
context management to a `machine.SPI` object.
"""
from . import DigitalInOut

class SPIDevice:
    """
    Represents a single SPI device and manages locking the bus and the device
    address.

    :param ~machine.SPI spi: The SPI bus the device is on
    :param ~machine.Pin chip_select: The chip select pin number.
    :param int extra_clocks: The minimum number of clock cycles to cycle the
        bus after CS is high. (Used for SD cards.)

    Example:

    .. code-block:: python

        from machine import SPI
        from circuitpython_nrf24l01.upy_wrapper import SPIDevice, DigitalInOut

        spi_bus = machine.SPI(SCK, MOSI, MISO)
        cs = DigitalInOut(10)
        device = SPIDevice(spi_bus, cs)
        bytes_read = bytearray(4)
        # The object assigned to spi in the with statements below
        # is the original spi_bus object. We are using the machine.SPI
        # operations machine.SPI.readinto() and machine.SPI.write().
        with device as spi:
            spi.readinto(bytes_read)
        # A second transaction
        with device as spi:
            spi.write(bytes_read)
    """

    def __init__(self,
            spi,
            chip_select=None,
            *,
            baudrate=100000,
            polarity=0,
            phase=0,
            extra_clocks=0
        ):
        self.spi = spi
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase
        self.extra_clocks = extra_clocks
        self.chip_select = chip_select
        if isinstance(chip_select, int):
            self.chip_select = DigitalInOut(chip_select)
        if self.chip_select:
            self.chip_select.switch_to_output(value=True)

    def __enter__(self):
        self.spi.init(
            baudrate=self.baudrate, polarity=self.polarity, phase=self.phase
        )
        if self.chip_select:
            self.chip_select.value = False
        return self.spi

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.chip_select:
            self.chip_select.value = True
        if self.extra_clocks > 0:
            buf = bytearray([0xFF])
            clocks = self.extra_clocks // 8
            if self.extra_clocks % 8 != 0:
                clocks += 1
            for _ in range(clocks):
                self.spi.write(buf)
        self.spi.deinit()
        return False
