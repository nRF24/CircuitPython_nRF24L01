"""
Example of library driving the nRF24L01 to communicate with a nRF24L01 driven by
the TMRh20 Arduino library. The Arduino program/sketch that this example was
designed for is named GettingStarted_HandlingData.ino and can be found in the "RF24"
examples after the TMRh20 library is installed from the Arduino Library Manager.
"""
import time
import struct
import board
import digitalio as dio
# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# addresses needs to be in a buffer protocol object (bytearray)
address = [b"1Node", b"2Node"]

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D4)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)
nrf.dynamic_payloads = False  # the default in the TMRh20 arduino library

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12

# change this variable to oppose the corresponding variable in the
# TMRh20 library's GettingStarted_HandlingData.ino example
radioNumber = True


# Create a data structure for transmitting and receiving data
# pylint: disable=too-few-public-methods
class DataStruct:
    """A data structure to hold transmitted values as the
    'HandlingData' part of the TMRh20 library example"""
    time = 0  # in milliseconds (used as start of timer)
    value = 1.22  # incremented  by 0.01 with every transmission
# pylint: enable=too-few-public-methods

myData = DataStruct()


def master(count=5):  # count = 5 will only transmit 5 packets
    """Transmits an arbitrary unsigned long value every second"""
    # set address of TX node into a RX pipe, and
    # set address of RX node into a TX pipe
    if radioNumber:
        nrf.open_rx_pipe(1, address[0])
        nrf.open_tx_pipe(address[1])
    else:
        nrf.open_rx_pipe(1, address[1])
        nrf.open_tx_pipe(address[0])
    nrf.listen = False  # ensures the nRF24L01 is in TX mode
    while count:
        print("Now Sending")
        myData.time = int(time.monotonic_ns() / 1000)  # start timer
        # use struct.pack to packetize your data into a usable payload
        # '<' means little endian byte order.
        # 'L' means a single 4 byte unsigned long value.
        # 'f' means a single 4 byte float value.
        buffer = struct.pack("<Lf", myData.time, myData.value)
        # send the payload. send_only=1 is default behavior in TMRh20 library
        result = nrf.send(buffer, send_only=1)
        if not result:
            print("send() failed or timed out")
        else:  # sent successful; listen for a response
            nrf.listen = True  # get nRF24L01 ready to receive a response
            timeout = True  # used to determine if response timed out
            while time.monotonic() * 1000 - myData.time < 200:
                # the arbitrary 200 ms timeout value is also used in the
                # TMRh20 library's GettingStarted_HandlingData sketch
                if nrf.update() and nrf.pipe is not None:
                    end_timer = time.monotonic_ns() / 1000  # end timer
                    rx = nrf.recv(32)  # 32 mimics behavior in TMRh20 library
                    rx = struct.unpack("<Lf", rx[:8])
                    myData.value = rx[1]  # save the new float value
                    timeout = False  # skips timeout prompt
                    # print total time to send and receive data
                    print(
                        "Sent {} Got Response: {}".format(
                            struct.unpack("<Lf", buffer),
                            rx
                        )
                    )
                    print("Round-trip delay:", end_timer - myData.time, "us")
                    break
            if timeout:
                print("failed to get a response; timed out")
            nrf.listen = False  # put the nRF24L01 back in TX mode
        count -= 1
        time.sleep(1)


def slave(count=3):
    """Polls the radio and prints the received value. This method expires
    after 6 seconds of no received transmission"""
    # set address of TX node into a RX pipe, and
    # set address of RX node into a TX pipe
    if radioNumber:
        nrf.open_rx_pipe(1, address[0])
        nrf.open_tx_pipe(address[1])
    else:
        nrf.open_rx_pipe(1, address[1])
        nrf.open_tx_pipe(address[0])
    nrf.listen = True  # put radio into RX mode and power up
    myData.time = time.monotonic() * 1000  # in milliseconds
    while count and (time.monotonic() * 1000 - myData.time) < 6000:
        if nrf.update() and nrf.pipe is not None:
            # clear flags & fetch 1 payload in RX FIFO
            buffer = nrf.recv(32)  # 32 mimics behavior in TMRh20 library
            # increment floating value as part of the "HandlingData" test
            myData.value = struct.unpack("<f", buffer[4:8])[0] + 0.01
            nrf.listen = False  # ensures the nRF24L01 is in TX mode
            myData.time = time.monotonic() * 1000
            # echo buffer[:4] appended with incremented float
            # send_only=True is the default behavior in TMRh20 library
            result = nrf.send(
                buffer[:4] + struct.pack("<f", myData.value),
                send_only=True
            )
            end_timer = time.monotonic() * 1000  # in milliseconds
            # expecting an unsigned long & a float, thus the
            # string format "<Lf"; buffer[:8] ignores the padded 0s
            buffer = struct.unpack("<L", buffer[:4])
            # print the unsigned long and float data sent in the response
            print("Responding: {}, {}".format(buffer[0], myData.value))
            if not result:
                print("response failed or timed out")
            else:
                # print timer results on transmission success
                print(
                    "successful response took {} ms".format(
                        end_timer - myData.time
                    )
                )
            # this will listen indefinitely till counter == 0
            count -= 1
            nrf.listen = True  # put nRF24L01 back into RX mode
    # recommended behavior is to keep in TX mode when in idle
    nrf.listen = False  # put the nRF24L01 in TX mode + Standby-I power state


print(
    """\
    nRF24L01 communicating with an Arduino running the\n\
    TMRh20 library's "GettingStarted_HandlingData.ino" example.\n\
    Run slave() to receive\n\
    Run master() to transmit\n\

    radioNumber is {}. Change this variable to oppose the TMRh20\n\
    example's radioNumber value.""".format(radioNumber)
)
