"""wrapped driver for RPi.GPIO as DigitalIO"""

import RPi.GPIO as GPIO


class DigitalInOut:
    """A wrapper for the RPi.GPIO bcm-scheme pins"""
    def __init__(self, pin_numb):
        self._pin = pin_numb
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin_numb, GPIO.OUT)

    # pylint: disable=unused-argument
    def switch_to_output(self, pull=None, value=False):
        """ change pin to an output """
        GPIO.setup(self._pin, GPIO.OUT, initial=value)

    def switch_to_input(self, pull=None):
        """ change pin to an input """
        GPIO.setup(self._pin, GPIO.IN)

    @property
    def value(self):
        """The current state of the pin (`True/HIGH or `False`/LOW)"""
        return GPIO.input(self._pin)

    @value.setter
    def value(self, val):
        GPIO.output(self._pin, bool(val))

    def __del__(self):
        del self._pin
        GPIO.cleanup()
