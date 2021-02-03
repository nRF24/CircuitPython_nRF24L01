"""A module to hold all usuall accesssible RF24 API via the RF24Network API"""
# pylint: disable=missing-docstring
from ..rf24 import RF24

class Radio:
    def __init__(self, spi, csn_pin, ce_pin, spi_frequency=10000000):
        self._radio = RF24(spi, csn_pin, ce_pin, spi_frequency=spi_frequency)

    @property
    def channel(self):
        return self._radio.channel

    @channel.setter
    def channel(self, val):
        self._radio.channel = val

    @property
    def dynamic_payloads(self):
        return self._radio.dynamic_payloads

    @dynamic_payloads.setter
    def dynamic_payloads(self, val):
        self._radio.dynamic_payloads = val

    def set_dynamic_payloads(self, enable, pipe=None):
        self._radio.set_dynamic_payloads(enable, pipe_number=pipe)

    def get_dynamic_payloads(self, pipe=None):
        return self._radio.get_dynamic_payloads(pipe)

    @property
    def listen(self):
        return self._radio.listen

    @listen.setter
    def listen(self, is_rx):
        self._radio.listen = is_rx

    @property
    def pa_level(self):
        return self._radio.pa_level

    @pa_level.setter
    def pa_level(self, val):
        self._radio.pa_level = val

    @property
    def is_lna_enabled(self):
        return self._radio.is_lna_enabled

    @property
    def data_rate(self):
        return self._radio.data_rate

    @data_rate.setter
    def data_rate(self, val):
        self._radio.data_rate = val

    @property
    def crc(self):
        return self._radio.crc

    @crc.setter
    def crc(self, val):
        self._radio.crc = val

    @property
    def ard(self):
        return self._radio.ard

    @ard.setter
    def ard(self, val):
        self._radio.ard = val

    @property
    def arc(self):
        return self._radio.arc

    @arc.setter
    def arc(self, val):
        self._radio.arc = val

    def get_auto_retries(self):
        return self._radio.get_auto_retries()

    def set_auto_retries(self, delay, count):
        self._radio.set_auto_retries(delay, count)

    @property
    def last_tx_arc(self):
        return self._radio.last_tx_arc

    @last_tx_arc.setter
    def last_tx_arc(self, val):
        self._radio.last_tx_arc = val

    def address(self, index=-1):
        return self._radio.address(index)

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        return self._radio.interrupt_config(data_recv, data_sent, data_fail)


# pylint: enable=missing-docstring
