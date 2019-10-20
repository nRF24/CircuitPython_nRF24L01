"""module managment for the circuitpython-nrf24l01 package"""

from .rf24 import RF24
from .fake_ble import FakeBLE

__all__ = ['RF24', 'FakeBLE']
