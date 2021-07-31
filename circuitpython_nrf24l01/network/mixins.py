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
"""A module to hold all usuall accesssible RF24 API via the RF24Network API"""
# pylint: disable=missing-docstring
import time
from ..rf24 import RF24, address_repr
from .structs import RF24NetworkFrame, FrameQueueFrag

logging = None  # pylint: disable=invalid-name
try:
    import logging
    logging.basicConfig()
except ImportError:
    try:
        import adafruit_logging as logging
    except ImportError:
        pass  # proceed without logging capability


class LoggerMixin:
    def __init__(self):
        self._logger = None
        if logging is not None:
            self._logger = logging.getLogger(type(self).__name__)

    @property
    def logger(self):
        """Get/Set the current ``Logger()``."""
        return self._logger

    @logger.setter
    def logger(self, val):
        if logging is not None and isinstance(val, logging.Logger):
            self._logger = val

    def _log(self, level, prompt):
        if self._logger is not None:
            self._logger.log(level, prompt)


class NetworkMixin(LoggerMixin):
    def __init__(self, spi, csn, ce_pin, spi_frequency=10000000):
        self._rf24 = RF24(spi, csn, ce_pin, spi_frequency=spi_frequency)
        super().__init__()
        # setup private members
        self._multicast_level = 0
        self._addr = 0
        self._addr_mask = 0
        self._addr_mask_inverted = 0
        self._multicast_relay = False
        self._frag_enabled = True

        #: The timeout (in milliseconds) to wait for successful transmission.
        self.tx_timeout = 25
        #: The timeout (in milliseconds) to wait for transmission's `NETWORK_ACK`.
        self.route_timeout = 3 * self.tx_timeout
        #: enable/disable (`True`/`False`) multicasting
        self.allow_multicast = True
        self.ret_sys_msg = False  #: Force `update()` to return on system message types.
        self.network_flags = 0  #: Flags that affect Network node behavior.
        self.max_message_length = 144  #: The maximum length of a frame's message.
        #: The queue (FIFO) of recieved frames for this node
        self.queue = FrameQueueFrag()
        self.queue.max_message_length = self.max_message_length
        #: A buffer containing the last frame received by the network node
        self.frame_cache = RF24NetworkFrame()
        self.address_suffix = [0xC3, 0x3C, 0x33, 0xCE, 0x3E, 0xE3]
        """Each byte in this list corresponds to the unique byte per pipe and child
        node."""
        self.address_prefix = 0xCC
        """The byte used for all pipes' address' bytes before mutating with
        `address_suffix`."""

    def __enter__(self):
        self.node_address = self._addr
        self._rf24.__enter__()
        self._rf24.listen = True
        return self

    def __exit__(self, *exc):
        return self._rf24.__exit__()

    def print_details(self, dump_pipes=False, network_only=False):
        if not network_only:
            self._rf24.print_details(False)
        print(
            "Network frame_cache contents:\n    Header is {}. Message contains:\n\t"
            "{}".format(
                self.frame_cache.header.to_string(),
                "an empty buffer"
                if not self.frame_cache.message
                else address_repr(self.frame_cache.message, False, " "),
            )
        )
        print(
            "Network flags______________0b{}".format(
                ("0" * (4 - (len(bin(self.network_flags)) - 2)))
                + bin(self.network_flags)[2:]
            )
        )
        print("Return on system messages__{}".format(bool(self.ret_sys_msg)))
        print("Allow network multicasts___{}".format(bool(self.allow_multicast)))
        print(
            "Multicast relay____________{}".format(
                "Enabled" if self._multicast_relay else "Disabled"
            )
        )
        print(
            "Network fragmentation______{}".format(
                "Enabled" if self._frag_enabled else "Disabled"
            )
        )
        print("Network max message length_{} bytes".format(self.max_message_length))
        print("Network TX timeout_________{} milliseconds".format(self.tx_timeout))
        print("Network Rounting timeout___{} milliseconds".format(self.route_timeout))
        print("Network node address_______{}".format(oct(self._addr)))
        if dump_pipes:
            self._rf24.print_pipes()

    def _tx_standby(self, delta_time):
        """``delta_time`` is in milliseconds"""
        result = False
        timeout = delta_time * 1000000 + time.monotonic_ns()
        while not result and time.monotonic_ns() < timeout:
            result = self._rf24.resend(send_only=True)
        return result

    @property
    def power(self):
        return self._rf24.power

    @power.setter
    def power(self, val):
        self._rf24.power = val

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

    def print_pipes(self):
        return self._rf24.print_pipes()
