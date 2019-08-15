# The MIT License (MIT)
#
# Copyright (c) 2019 Brendan Doherty
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
"""
===========================================
circuitpython_nrf24l01.fake_ble - FakeBLE
===========================================

This module uses the RF24 module to make the nRF24L01 imitate a Bluetooth-Low-Emissions (BLE) beacon. A BLE beacon can send (referred to as advertise) data to any BLE compatible device (ie smart devices with Bluetooth 4.0 or later) that is listening.

Original research was done by Dmitry Grinberg and his write-up (including C source code) can be found `here <http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_  As this technique can prove invaluable in certain project designs, the code here is simply ported to work on CircuitPython.

.. important:: Because the nRF24L01 wasn't designed for BLE advertising, it has some limitations that helps to be aware of.

    1. the maximum payload length is shortened to 19 bytes
    2. the channels that BLE use are limited to the following three: 2.402 GHz, 2.426 GHz, and 2.480 GHz
    3. CRC is disabled in the nRF24L01 firmware as BLE requires 3 bytes and nRF24L01 only handles 2. Thus we have augmented the required 3 bytes of CRC into the payload.
    4. address length of BLE packet only uses 4 bytes, so we have set that acccordingly.
    5. the automatic acknowledgment feature of the nRF24L01 is useless when tranmitting to BLE devices, thus it is disabled as well as automatic re-transmit and custom ACK payloads (both depend on the automatic acknowledgments feature)
    6. the dynamic payloads feature of the nRF24L01 isn't compatible with BLE specifications. Thus we have disabled it in the nRF24L01 firmware and incorporated dynamic payloads properly into he payload data
    7. BLE specifications only allow using 1 Mbps RF data rate, so that too has been hard coded.
    8. both the "on data sent" & "on data ready" events control the interrupt (IRQ) pin; the other event, "on data fail", is ignored because it will never get thrown with "auto_ack" off. However the interrupt settings can be modified AFTER instantiation

"""
import time, math
from circuitpython_nrf24l01.rf24 import RF24

def _swap_bits(orig):
    """this is broken"""
    reverse = 0
    # start from MSBit of MSByte; go to LSBit of LSByte
    max_shift = ((math.floor(orig / 16) + bool(orig % 16)) * 3)
    mask = 1 << max_shift
    for every_half_byte in range(int(orig / 16) + bool(orig % 16)):
        for bit in range(4): # take on 1 bit at a time
            mask >>= 1
            # invert_shift = max_shift - (bit + every_half_byte * 3)
            reverse |= bool(orig & mask)
    return reverse # we're done here

def _make_CRC(data):
    """use this to create the 3 byte-long CRC data. returns a bytearray

    .. code::
        original_func(data, len, dst):
        v, t, d
        while(len--):
            d = *data++
            for(v = 0; v < 8; v++, d >>= 1):
                t = dst[0] >> 7
                dst[0] <<= 1
                if(dst[1] & 0x80):
                    dst[0] |= 1
                dst[1] <<= 1
                if(dst[2] & 0x80):
                    dst[1] |= 1
                dst[2] <<= 1
                if(t != (d & 1)):
                    dst[2] ^= 0x5B
                    dst[1] ^= 0x06

    """
    pass


class FakeBLE(RF24):
    """Per the limitations of this technique, only power amplifier level is available for configuration when advertising BLE data.

    :param ~busio.SPI spi: The object for the SPI bus that the nRF24L01 is connected to.

        .. tip:: This object is meant to be shared amongst other driver classes (like adafruit_mcp3xxx.mcp3008 for example) that use the same SPI bus. Otherwise, multiple devices on the same SPI bus with different spi objects may produce errors or undesirable behavior.

    :param ~digitalio.DigitalInOut csn: The digital output pin that is connected to the nRF24L01's CSN (Chip Select Not) pin. This is required.
    :param ~digitalio.DigitalInOut ce: The digital output pin that is connected to the nRF24L01's CE (Chip Enable) pin. This is required.
    :param int pa_level: This parameter controls the RF power amplifier setting of transmissions. Options are ``0`` (dBm), ``-6`` (dBm), ``-12`` (dBm), or ``-18`` (dBm). This can be changed at any time by using the `pa_level` attribute.

    """
    def __init__(self, spi, csn, ce, pa_level=0):
        super(FakeBLE, self).__init__(spi, csn, ce, pa_level=pa_level, crc=0, dynamic_payloads=False, arc=0, address_length=4, ask_no_ack=False, irq_DF=False)

    def send(self, buf):
        """This blocking function is used to transmit payload.

        :returns: Nothing as every transmission will register as a success under these required settings.

        :param bytearray buf: The payload to transmit. This bytearray must have a length greater than 0 and less than 20, otherwise a `ValueError` exception is thrown. This can also be a list or tuple of payloads (`bytearray`); in which case, all items in the list/tuple are processed for consecutive transmissions.

            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.


        """
        self.ce.value = 0 # ensure power down/standby-I for proper manipulation of PWR_UP & PRIM_RX bits in CONFIG register
        self.flush_tx()
        self.clear_status_flags(False) # clears TX related flags only
        if not buf or len(buf) > 20:
            raise ValueError("buf must be a buffer protocol object with a byte length of\nat least 1 and no greater than 20")

        # TODO implement proper packet manipulation here

        self.write(buf) # init using non-blocking helper
        time.sleep(0.00001) # ensure CE pulse is >= 10 µs
        # pulse is stopped here; the nRF24L01 only handles the top level payload in the FIFO.
        self.ce.value = 0 # go to Standby-I power mode (power attribute still == True)

        # T_upload is done before timeout begins (after payload write action AKA upload)
        timeout = (1 + bool(self.auto_ack)) * (((8 * (1 + self._addr_len + len(buf) + (max(0, ((self._config & 12) >> 2) - 1)))) + 9) / (((2000000 if self._rf_setup & 0x28 == 8 else 250000) if self._rf_setup & 0x28 else 1000000) / 8)) + ((2 + bool(self.auto_ack)) * 0.00013) + (0.0000082 if not self._rf_setup & 0x28 else 0.000006) + ((((self._setup_retr & 0xf0) >> 4) * 250 + 380) * (self._setup_retr & 0x0f) / 1000000)
        start = time.monotonic()
        while not self.irq_DS and (time.monotonic() - start) < timeout:
            self.update() # perform Non-operation command to get status byte (should be faster)
            # print('status: DR={} DS={} DF={}'.format(self.irq_DR, self.irq_DS, self.irq_DF))
        self.clear_status_flags(False) # only TX related IRQ flags

    def write(self, buf=None):
        """This non-blocking function (when used as alternative to `send()`) is meant for asynchronous applications and can only handle one payload at a time as it is a helper function to `send()`.

        :param bytearray buf: The payload to transmit. This bytearray must have a length greater than 0 and less than 32 bytes, otherwise a `ValueError` exception is thrown.

            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.

        This function isn't completely non-blocking as we still need to wait just under 5 ms for the CSN pin to settle (allowing a clean SPI transaction).

        .. note:: The nRF24L01 doesn't initiate sending until a mandatory minimum 10 µs pulse on the CE pin is acheived. That pulse is initiated before this function exits. However, we have left that 10 µs wait time to be managed by the MCU in cases of asychronous application, or it is managed by using `send()` instead of this function. If the CE pin remains HIGH for longer than 10 µs, then the nRF24L01 will continue to transmit all payloads found in the TX FIFO buffer.

        .. warning:: A note paraphrased from the `nRF24L01+ Specifications Sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_:

            It is important to NEVER to keep the nRF24L01+ in TX mode for more than 4 ms at a time. If the [`auto_ack` and `dynamic_payloads`] features are enabled, nRF24L01+ is never in TX mode longer than 4 ms.

        .. tip:: Use this function at your own risk. Because of the underlying `"Enhanced ShockBurst Protocol" <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1132607>`_, disobeying the 4 ms rule is easily avoided if you enable the `dynamic_payloads` and `auto_ack` attributes. Alternatively, you MUST use interrupt flags/IRQ pin with user defined timer(s) to AVOID breaking the 4 ms rule. If the `nRF24L01+ Specifications Sheet explicitly states this <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1121422>`_, we have to assume radio damage or misbehavior as a result of disobeying the 4 ms rule. See also `table 18 in the nRF24L01 specification sheet <https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf#G1123001>`_ for calculating necessary transmission time (these calculations are used in the `send()` function).

        """
        if not buf or len(buf) > 20:
            raise ValueError("buf must be a buffer protocol object with a byte length of\nat least 1 and no greater than 20")

        if not self.power or (super(FakeBLE, self)._config & 1): # ready radio if it isn't yet
            super(FakeBLE, self)._config = (self._reg_read(0) & 0x7c) | 2 # also ensures tx mode
            self._reg_write(0, super(FakeBLE, self)._config)
            # power up/down takes < 150 µs + 4 µs
            time.sleep(0.00016)

        # now upload the payload accordingly
        # 0xA0 = W_TX_PAYLOAD; this command works with auto_ack on or off
        self._reg_write_bytes(0xA0, buf) # write appropriate command with payload

        # enable radio comms so it can send the data by starting the mandatory minimum 10 µs pulse on CE. Let send() measure this pulse for blocking reasons
        self.ce.value = 1 # re-used payloads start with this as well
        # radio will automatically go to standby-II after transmission while CE is still HIGH only if dynamic_payloads and auto_ack are enabled

    # Altering all the following settings is disabled
    @address_length.setter
    def address_length(self, t):
        super(FakeBLE, self).address_length = (4 + t * 0)

    @listen.setter
    def listen(self, rx):
        if self.listening or rx:
            self._stop_listening()

    @data_rate.setter
    def data_rate(self, t):
        super(FakeBLE, self).data_rate = (1 + t * 0)

    @dynamic_payloads.setter
    def dynamic_payloads(self, t):
        super(FakeBLE, self).dynamic_payloads = (False & t)

    @auto_ack.setter
    def auto_ack(self, t):
        super(FakeBLE, self).auto_ack = (False & t)

    @ack.setter
    def ack(self, t):
        super(FakeBLE, self).ack = (False & t)

    @crc.setter
    def crc(self, t):
        super(FakeBLE, self).crc = (0 * t)

    @arc.setter
    def arc(self, t):
        super(FakeBLE, self).arc = (t * 0)
