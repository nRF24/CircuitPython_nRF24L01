"""
Simple example of using the library to transmit
and retrieve custom automatic acknowledgment payloads.
"""
import time
import board
from digitalio import DigitalInOut

# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# invalid default values for scoping
SPI_BUS, CSN_PIN, CE_PIN = (None, None, None)

try:  # on Linux
    import spidev

    SPI_BUS = spidev.SpiDev()  # for a faster interface on linux
    CSN_PIN = 0  # use CE0 on default bus (even faster than using any pin)
    CE_PIN = DigitalInOut(board.D22)  # using pin gpio22 (BCM numbering)

except ImportError:  # on CircuitPython only
    # using board.SPI() automatically selects the MCU's
    # available SPI pins, board.SCK, board.MOSI, board.MISO
    SPI_BUS = board.SPI()  # init spi bus object

    # change these (digital output) pins accordingly
    CE_PIN = DigitalInOut(board.D4)
    CSN_PIN = DigitalInOut(board.D5)


# initialize the nRF24L01 on the spi bus object
nrf = RF24(SPI_BUS, CSN_PIN, CE_PIN)
# On Linux, csn value is a bit coded
#                 0 = bus 0, CE0  # SPI bus 0 is enabled by default
#                10 = bus 1, CE0  # enable SPI bus 2 prior to running this
#                21 = bus 2, CE1  # enable SPI bus 1 prior to running this

# the custom ACK payload feature is disabled by default
# NOTE the the custom ACK payload feature will be enabled
# automatically when you call load_ack() passing:
# a buffer protocol object (bytearray) of
# length ranging [1,32]. And pipe number always needs
# to be an int ranging [0, 5]

# to enable the custom ACK payload feature
nrf.ack = True  # False disables again

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12

# addresses needs to be in a buffer protocol object (bytearray)
address = [b"1Node", b"2Node"]

# to use different addresses on a pair of radios, we need a variable to
# uniquely identify which address this radio will use to transmit
# 0 uses address[0] to transmit, 1 uses address[1] to transmit
radio_number = bool(
    int(input("Which radio is this? Enter '0' or '1'. Defaults to '0' ") or 0)
)

# set TX address of RX node into the TX pipe
nrf.open_tx_pipe(address[radio_number])  # always uses pipe 0

# set RX address of TX node into an RX pipe
nrf.open_rx_pipe(1, address[not radio_number])  # using pipe 1

# using the python keyword global is bad practice. Instead we'll use a 1 item
# list to store our integer number for the payloads' counter
counter = [0]


def master(count=5):  # count = 5 will only transmit 5 packets
    """Transmits a payload every second and prints the ACK payload"""
    nrf.listen = False  # put radio in TX mode

    while count:
        # construct a payload to send
        # add b"\0" as a c-string NULL terminating char
        buffer = b"Hello \0" + bytes([counter[0]])
        start_timer = time.monotonic_ns()  # start timer
        result = nrf.send(buffer)  # save the response (ACK payload)
        end_timer = time.monotonic_ns()  # stop timer
        if result:
            # print the received ACK that was automatically
            # fetched and saved to "result" via send()
            # print timer results upon transmission success
            print(
                "Transmission successful! Time to transmit:",
                int((end_timer - start_timer) / 1000),
                "us. Sent: {}{}".format(buffer[:6].decode("utf-8"), counter[0]),
                end=" ",
            )
            if isinstance(result, bool):
                print("Received an empty ACK packet")
            else:
                # result[:6] truncates c-string NULL termiating char
                # received counter is a unsigned byte, thus result[7:8][0]
                print(
                    "Received: {}{}".format(result[:6].decode("utf-8"), result[7:8][0])
                )
            counter[0] += 1  # increment payload counter
        elif not result:
            print("send() failed or timed out")
        time.sleep(1)  # let the RX node prepare a new ACK payload
        count -= 1


def slave(timeout=6):
    """Prints the received value and sends an ACK payload"""
    nrf.listen = True  # put radio into RX mode, power it up

    # setup the first transmission's ACK payload
    # add b"\0" as a c-string NULL terminating char
    buffer = b"World \0" + bytes([counter[0]])
    # we must set the ACK payload data and corresponding
    # pipe number [0, 5]. We'll be acknowledging pipe 1
    nrf.load_ack(buffer, 1)  # load ACK for first response

    start = time.monotonic()  # start timer
    while (time.monotonic() - start) < timeout:
        if nrf.available():
            # grab information about the received payload
            length, pipe_number = (nrf.any(), nrf.pipe)
            # retreive the received packet's payload
            received = nrf.read()
            # increment counter from received payload
            # received counter is a unsigned byte, thus result[7:8][0]
            counter[0] = received[7:8][0] + 1
            # the [:6] truncates the c-string NULL termiating char
            print(
                "Received {} bytes on pipe {}:".format(length, pipe_number),
                "{}{}".format(received[:6].decode("utf-8"), received[7:8][0]),
                "Sent: {}{}".format(buffer[:6].decode("utf-8"), buffer[7:8][0]),
            )
            start = time.monotonic()  # reset timer
            buffer = b"World \0" + bytes([counter[0]])  # build new ACK
            nrf.load_ack(buffer, 1)  # load ACK for next response

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False  # put radio in TX mode
    nrf.flush_tx()  # flush any ACK payloads that remain


def set_role():
    """Set the role using stdin stream. Timeout arg for slave() can be
    specified using a space delimiter (e.g. 'R 10' calls `slave(10)`)
    """
    user_input = (
        input(
            "*** Enter 'R' for receiver role.\n"
            "*** Enter 'T' for transmitter role.\n"
            "*** Enter 'Q' to quit example.\n"
        )
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("R"):
        slave(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("T"):
        master(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = False
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nRF24L01 ACK Payload test")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = False
else:
    print("    Run slave() on receiver\n    Run master() on transmitter")
