"""import only accessible API wrappers"""
from .cpy_spidev import SPIDevCtx  # for linux only

RPiDIO = None  # pylint: disable=invalid-name
try:  # check for MicroPython's machine.Pin
    from .upy_pin import DigitalInOut
    from .upy_spi import SPIDevice
except ImportError:  # must be on linux or CircuitPython compatible
    from digitalio import DigitalInOut
    from adafruit_bus_device.spi_device import SPIDevice
    try:  # check for RPi.GPIO library (if on RPi)
        from .cpy_rpi_gpio import RPiDIO
    except ImportError:
        pass

__all__ = ["DigitalInOut", "SPIDevice", "SPIDevCtx", "RPiDIO"]
