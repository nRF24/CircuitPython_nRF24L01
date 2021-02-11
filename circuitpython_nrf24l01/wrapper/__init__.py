"""import only accessible API wrappers"""


# for linux only
from .cpy_spidev import SPIDevCtx
__all__ = ["DigitalInOut", "SPIDevice", "SPIDevCtx"]
try:  # check for MicroPython's machine.Pin
    from .upy_pin import DigitalInOut
    from .upy_spi import SPIDevice
except ImportError:  # must be on linux or CircuitPython compatible
    from adafruit_bus_device.spi_device import SPIDevice
    try:  # check for RPi.GPIO library (if on RPi)
        from .cpy_rpi_gpio import DigitalInOut
    except ImportError:
        from digitalio import DigitalInOut
