"""wrappers for CirrcuitPython API over MicroPython's API"""
from machine import Pin  # pylint: disable=import-error
# pylint: disable=too-few-public-methods,missing-class-docstring

class DriveMode:
    PUSH_PULL = Pin.PULL_HOLD
    OPEN_DRAIN = Pin.OPEN_DRAIN

class Pull:
    UP = Pin.PULL_UP  # pylint: disable=invalid-name
    DOWN = Pin.PULL_DOWN
# pylint: enable=missing-class-docstring


class DigitalInOut:
    """A class to control micropython's :py:class:`~machine.Pin` object like
    a circuitpython DigitalInOut object
    :param ~machine.Pin pin: the digital pin alias.
    """
    def __init__(self, pin_number):
        self._pin = Pin(pin_number, Pin.IN)

    def deinit(self):
        """ deinitialize the GPIO pin """
        # deinit() not implemented in micropython
        # avoid raising a NotImplemented Error
        pass  # pylint: disable=unnecessary-pass

    def switch_to_output(self, pull=None, value=False):
        """ change pin into output """
        if pull is None:
            self._pin.init(Pin.OUT, value=value)
        elif pull in (Pull.UP, Pull.DOWN):
            self._pin.init(Pin.OUT, pull=pull, value=value)
        else:
            raise AttributeError("pull parameter is unrecognized")

    def switch_to_input(self, pull=None):  # pylint: disable=unused-argument
        """ change pin into input """
        self._pin.init(Pin.IN)

    @property
    def value(self):
        """ the value of the pin """
        return self._pin.value()

    @value.setter
    def value(self, val):
        self._pin.value(val)

    def __del__(self):
        del self._pin