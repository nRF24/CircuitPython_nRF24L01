"""wrappers for MicroPython's machine.Pin as CircuitPython's digitalio  API"""
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
    a circuitpython DigitalInOut object.

    :param int pin: The digital pin number to alias.
    """

    def __init__(self, pin_number):
        self._pin = Pin(pin_number, Pin.IN)

    def deinit(self):
        """deinitialize the GPIO pin"""
        # deinit() not implemented in micropython
        # avoid raising a NotImplemented Error
        pass  # pylint: disable=unnecessary-pass

    def switch_to_output(self, pull=None, value=False):
        """change pin into output"""
        if pull is None:
            self._pin.init(Pin.OUT, value=value)
        elif pull in (Pull.UP, Pull.DOWN):
            self._pin.init(Pin.OUT, pull=pull, value=value)
        else:
            raise AttributeError("pull parameter is unrecognized")

    def switch_to_input(self, pull=None):  # pylint: disable=unused-argument
        """change pin into input"""
        self._pin.init(Pin.IN)

    @property
    def value(self) -> bool:
        """the value of the pin"""
        return self._pin.value()

    @value.setter
    def value(self, val):
        self._pin.value(val)

    def __del__(self):
        del self._pin
