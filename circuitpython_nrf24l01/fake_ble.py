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

Original research was done by `Dmitry Grinberg and his write-up (including C source code) can be found here <http://dmitry.gr/index.php?r=05.Projects&proj=11.%20Bluetooth%20LE%20fakery>`_  As this technique can prove invaluable in certain project designs, the code here is simply ported to work on CircuitPython.

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
import time
from .rf24 import RF24

def _swap_bits(orig):
    """reverse bit order into LSbit to MSBit"""
    reverse = 0
    while orig:
        reverse <<= 1
        reverse |= orig & 1
        orig >>= 1
    return reverse # we're done here

def _reverse_bits(orig):
    r = b''
    for byte in list(orig):
        r += bytes([_swap_bits(byte)])
    return r

def _make_CRC(data):
    """use this to create the 3 byte-long CRC data. returns a bytearray"""
    # uint8_t v, t, d;
    # while( len-- ) {
    #     d = *data++;
    #     for( v = 0; v < 8; v++, d >>= 1 ) {
    #         t = dst[0] >> 7;
    #         dst[0] <<= 1;
    #         if( dst[1] & 0x80 ) {
    #             dst[0] |= 1;
    #         }
    #         dst[1] <<= 1;
    #         if( dst[2] & 0x80 ) {
    #             dst[1] |= 1;
    #         }
    #         dst[2] <<= 1;
    #         if( t != (d&1) ) {
    #             dst[2] ^= 0x5B;
    #             dst[1] ^= 0x06;
    dst = [0x55, 0x55, 0x55]
    for d in list(data):
        for _ in range(8):
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
            d >>= 1
    return dst

def _ble_whitening(data, whiten_coef):
    """for "whiten"ing the BLE packet data according to expected parameters"""
    # uint8_t  m;
    # while(len--){
    #     for(m = 1; m; m <<= 1){
    #         if(whitenCoeff & 0x80){
    #             whitenCoeff ^= 0x11;
    #             (*data) ^= m;
    #         }
    #         whitenCoeff <<= 1;
    #     }
    #     data++;
    result = b''
    for d in list(data): # for every byte
        for i in range(8):
            if whiten_coef & 0x80:
                whiten_coef ^= 0x11
                d ^= 1 << i
            whiten_coef <<= 1
        result += bytes([d])
    return result

class FakeBLE(RF24):
    """Per the limitations of this technique, only power amplifier level is available for configuration when advertising BLE data.

    :param ~busio.SPI spi: The object for the SPI bus that the nRF24L01 is connected to.

        .. tip:: This object is meant to be shared amongst other driver classes (like adafruit_mcp3xxx.mcp3008 for example) that use the same SPI bus. Otherwise, multiple devices on the same SPI bus with different spi objects may produce errors or undesirable behavior.

    :param ~digitalio.DigitalInOut csn: The digital output pin that is connected to the nRF24L01's CSN (Chip Select Not) pin. This is required.
    :param ~digitalio.DigitalInOut ce: The digital output pin that is connected to the nRF24L01's CE (Chip Enable) pin. This is required.
    :param bytearray name: This will be the nRF24L01-emulated BLE device's broadcasted name. This is option and defaults to `None` to allow for larger paylaods because the name's byte length borrows from the same buffer space that the payload data occupies. See `name` attribute for more details.
    :param int pa_level: This parameter controls the RF power amplifier setting of transmissions. Options are ``0`` (dBm), ``-6`` (dBm), ``-12`` (dBm), or ``-18`` (dBm). This can be changed at any time by using the `pa_level` attribute.

    """
    def __init__(self, spi, csn, ce, name=None, pa_level=0):
        super(FakeBLE, self).__init__(spi, csn, ce, pa_level=pa_level, crc=0, dynamic_payloads=False, arc=0, address_length=4, ask_no_ack=False, irq_DF=False)
        self._chan = 0
        self.name = name

    @property
    def name(self):
        """Represents the emulated BLE device name during braodcasts. must be a buffer protocol object (`bytearray`) , and can be any length (less than 14) of UTF-8 freindly characters.

        .. note:: the BLE device's name will occupy the same space as your TX data. While space is limited to 32 bytes on the nRF24L01, actual usable BLE TX data = 16 - (name length  + 2). The other 16 bytes available on the nRF24L01 TX FIFO buffer are reserved for the [arbitrary] MAC address and other BLE related stuff.
        """
        return self._ble_name[2:] if self._ble_name is not None else None

    @name.setter
    def name(self, n):
        if n is not None and 1 <= len(n) <= 12: # max defined by 1 byte payload data requisite
            self._ble_name = bytes([len(n) + 1]) + b'\x08' + n
        else:
            self._ble_name = None # name will not be advertised

    def _chan_hop(self):
        self._chan = (self._chan + 1) if (self._chan + 1) < 3 else 0
        self.channel = 26 if self._chan == 1 else (80 if self._chan == 2 else 2)

    def send(self, buf):
        """This blocking function is used to transmit payload.

        :returns: Nothing as every transmission will register as a success under these required settings.

        :param bytearray buf: The payload to transmit. This bytearray must have a length greater than 0 and less than 20, otherwise a `ValueError` exception is thrown. This can also be a list or tuple of payloads (`bytearray`); in which case, all items in the list/tuple are processed for consecutive transmissions.

            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is less than the `payload_length` attribute, then this bytearray is padded with zeros until its length is equal to the `payload_length` attribute.
            - If the `dynamic_payloads` attribute is disabled and this bytearray's length is greater than `payload_length` attribute, then this bytearray's length is truncated to equal the `payload_length` attribute.

        .. note:: If the name of the emulated BLE device is also to be braodcast, then the 'name' attribute should be set prior to calling `send()`
        """
        self.ce.value = 0 # ensure power down/standby-I for proper manipulation of PWR_UP & PRIM_RX bits in CONFIG register
        self.flush_tx()
        self.clear_status_flags(False) # clears TX related flags only
        # max payload_length = 32 - 14(header, MAC, & CRC) - 2(container header) - 3(BLE flags) = 13 - (BLE name length + 2 if any)
        if not buf or len(buf) > (13 - (len(self._ble_name) if self._ble_name is not None else 0)):
            raise ValueError("buf must be a buffer protocol object with a byte length of\nat least 1 and no greater than 13 - {} = {}".format((len(self._ble_name) if self._ble_name is not None else 0), 13 - (len(self._ble_name) if self._ble_name is not None else 0)))

        # BLE payload = 1 byte[header] + 1 byte[payload length] + 6 byte[MAC address] + containers + 3 byte[CRC]
        # header == PDU type, given MAC address is random/arbitrary; type == 0x42 for Android or 0x40 for iPhone
        # containers = 1 byte[length] + 1 byte[type] + data; the 1 byte about container's length excludes only itself

        payload = b'\x42' # init payload buffer with header type byte

        # payload length excludes the header, itself, and crc lengths
        payload += bytes([len(buf) + 3 (len(self._ble_name) if self._ble_name is not None else 0)])
        payload += b'\x11\x22\x33\x44\x55\x66' # a bogus MAC address
        # payload will have at least 2 containers: 3 bytes of flags (required for BLE discoverable), & at least (1+2) byte of data
        payload += b'\x02\x01\x06' # BLE flags for discoverability and non-pairable etc
        # payload will also have to fit the optional BLE device name as a seperate container ([name length + 2] bytes)
        if self._ble_name is not None:
            payload += self._ble_name
        payload += (bytes([len(buf) + 1]) + b'\xFF' + buf) # append the data container
        # crc is generated from b'\x55\x55\x55' about everything except itself
        payload += _reverse_bits(_make_CRC(payload))
        self._chan_hop() # cycle to next BLE channel per specs
        # the whiten_coef value we need is the BLE channel (37,38, or 39) left shifted one
        whiten_coef = 37 + self._chan
        whiten_coef = _swap_bits(whiten_coef) | 2
        self.write(_reverse_bits(_ble_whitening(payload, whiten_coef))) # init using non-blocking helper
        time.sleep(0.00001) # ensure CE pulse is >= 10 µs
        # pulse is stopped here; the nRF24L01 only handles the top level payload in the FIFO.
        self.ce.value = 0 # go to Standby-I power mode (power attribute still == True)

        # T_upload is done before timeout begins (after payload write action AKA upload)
        timeout = (((8 * (5 + len(payload))) + 9) / 125000) + 0.0002682
        start = time.monotonic()
        while not self.irq_DS and (time.monotonic() - start) < timeout:
            self.update() # perform Non-operation command to get status byte (should be faster)
            # print('status: DR={} DS={} DF={}'.format(self.irq_DR, self.irq_DS, self.irq_DF))
        self.clear_status_flags(False) # only TX related IRQ flags

    # Altering all the following settings is disabled
    def open_tx_pipe(self):
        super(FakeBLE, self).open_tx_pipe(_reverse_bits(b'\x8E\x89\xBE\xD6')) # proper address for BLE advertisments

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
