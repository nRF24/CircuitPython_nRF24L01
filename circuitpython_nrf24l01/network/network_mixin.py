"""A module to hold all usuall accesssible RF24 API via the RF24Network API"""
# pylint: disable=missing-docstring
from ..rf24 import RF24, logging


class RadioMixin:
    def __init__(self, spi, csn, ce_pin, spi_frequency=10000000):
        self._rf24 = RF24(spi, csn, ce_pin, spi_frequency=spi_frequency)
        self._logger = None
        if self._rf24.logger is not None:
            self._rf24.logger.setLevel(logging.INFO)  # ignore DEBUG from RF24
            self._logger = logging.getLogger(type(self).__name__)
            self._logger.setLevel(logging.DEBUG if spi is None else logging.INFO)
        super().__init__()

    @property
    def logger(self):
        """Get/Set the current ``Logger()``."""
        return self._logger

    @logger.setter
    def logger(self, val):
        if logging is not None and isinstance(val, logging.Logger):
            self._logger = val

    def _log(self, level, prompt, force_print=False):
        if self.logger is not None:
            self.logger.log(level, prompt)
        elif force_print:
            print(prompt)

    @property
    def channel(self):
        return self._rf24.channel

    @channel.setter
    def channel(self, val):
        self._rf24.channel = val

    @property
    def dynamic_payloads(self):
        return self._rf24.dynamic_payloads

    @dynamic_payloads.setter
    def dynamic_payloads(self, val):
        self._rf24.dynamic_payloads = val

    def set_dynamic_payloads(self, enable, pipe=None):
        self._rf24.set_dynamic_payloads(enable, pipe_number=pipe)

    def get_dynamic_payloads(self, pipe=None):
        return self._rf24.get_dynamic_payloads(pipe)

    @property
    def listen(self):
        return self._rf24.listen

    @listen.setter
    def listen(self, is_rx):
        self._rf24.listen = is_rx

    @property
    def pa_level(self):
        return self._rf24.pa_level

    @pa_level.setter
    def pa_level(self, val):
        self._rf24.pa_level = val

    @property
    def is_lna_enabled(self):
        return self._rf24.is_lna_enabled

    @property
    def data_rate(self):
        return self._rf24.data_rate

    @data_rate.setter
    def data_rate(self, val):
        self._rf24.data_rate = val

    @property
    def crc(self):
        return self._rf24.crc

    @crc.setter
    def crc(self, val):
        self._rf24.crc = val

    @property
    def ard(self):
        return self._rf24.ard

    @ard.setter
    def ard(self, val):
        self._rf24.ard = val

    @property
    def arc(self):
        return self._rf24.arc

    @arc.setter
    def arc(self, val):
        self._rf24.arc = val

    def get_auto_retries(self):
        return self._rf24.get_auto_retries()

    def set_auto_retries(self, delay, count):
        self._rf24.set_auto_retries(delay, count)

    @property
    def last_tx_arc(self):
        return self._rf24.last_tx_arc

    def address(self, index=-1):
        return self._rf24.address(index)

    def interrupt_config(self, data_recv=True, data_sent=True, data_fail=True):
        return self._rf24.interrupt_config(data_recv, data_sent, data_fail)


# pylint: enable=missing-docstring
