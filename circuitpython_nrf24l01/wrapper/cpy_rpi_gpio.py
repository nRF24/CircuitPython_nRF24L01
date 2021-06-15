"""This module contains a wrapper class for RPi.GPIO as digitalio.DigitalInOut"""
from typing import Union
import RPi.GPIO as GPIO


class RPiDIO:
    """A wrapper for the RPi.GPIO bcm-scheme pins"""
    def __init__(self, pin_numb: int) -> None:
        self._pin = int(pin_numb)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.OUT)

    # pylint: disable=unused-argument
    def switch_to_output(self, pull: any=None, value: bool=False) -> None:
        """ change pin to an output """
        GPIO.setup(self._pin, GPIO.OUT, initial=value)

    def switch_to_input(self, pull: any=None) -> None:
        """ change pin to an input """
        GPIO.setup(self._pin, GPIO.IN)

    @property
    def value(self) -> bool:
        """The current state of the pin (`True/HIGH or `False`/LOW)"""
        return GPIO.input(self._pin)

    @value.setter
    def value(self, val: Union[int, bool]) -> None:
        GPIO.output(self._pin, bool(val))

    def __del__(self) -> None:
        del self._pin
        GPIO.cleanup()
