"""
Example of using the library manually send Acknowledgement (ACK)
messages without using the nRF24L01's ACK payloads feature.
"""
import time
import board
import digitalio

# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# change these (digital output) pins accordingly
ce = digitalio.DigitalInOut(board.D4)
csn = digitalio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

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
# nrf.open_rx_pipe(2, address[radio_number])  # for getting responses on pipe 2

# using the python keyword global is bad practice. Instead we'll use a 1 item
# list to store our integer number for the payloads' counter
counter = [0]

# uncomment the following 3 lines for compatibility with TMRh20 library
# nrf.allow_ask_no_ack = False
# nrf.dynamic_payloads = False
# nrf.payload_length = 8


def master(count=5):  # count = 5 will only transmit 5 packets
    """Transmits an arbitrary unsigned long value every second"""
    nrf.listen = False  # ensures the nRF24L01 is in TX mode
    while count:
        # construct a payload to send
        # add b"\0" as a c-string NULL terminating char
        buffer = b"Hello \0" + bytes([counter[0]])
        start_timer = time.monotonic_ns()  # start timer
        result = nrf.send(buffer)  # save the response (ACK payload)
        if not result:
            print("send() failed or timed out")
        else:  # sent successful; listen for a response
            nrf.listen = True  # get radio ready to receive a response
            timeout = time.monotonic_ns() + 200000000  # set sentinal for timeout
            while not nrf.available() and time.monotonic_ns() < timeout:
                # this loop hangs for 200 ms or until response is received
                pass
            nrf.listen = False  # put the radio back in TX mode
            end_timer = time.monotonic_ns()  # stop timer
            print(
                "Transmission successful! Time to transmit: "
                "{} us. Sent: {}{}".format(
                    int((end_timer - start_timer) / 1000),
                    buffer[:6].decode("utf-8"),
                    counter[0],
                ),
                end=" ",
            )
            if nrf.pipe is None:  # is there a payload?
                # nrf.pipe is also updated using `nrf.listen = False`
                print("Received no response.")
            else:
                length = nrf.any()  # reset with read()
                pipe_number = nrf.pipe  # reset with read()
                received = nrf.read()  # grab the response
                # save new counter from response
                counter[0] = received[7:8][0]
                print(
                    "Receieved {} bytes with pipe {}: {}{}".format(
                        length,
                        pipe_number,
                        bytes(received[:6]).decode("utf-8"),  # convert to str
                        counter[0],
                    )
                )
        count -= 1
        # make example readable in REPL by slowing down transmissions
        time.sleep(1)


def slave(timeout=6):
    """Polls the radio and prints the received value. This method expires
    after 6 seconds of no received transmission"""
    nrf.listen = True  # put radio into RX mode and power up
    start_timer = time.monotonic()  # used as a timeout
    while (time.monotonic() - start_timer) < timeout:
        if nrf.available():
            length = nrf.any()  # grab payload length info
            pipe = nrf.pipe  # grab pipe number info
            received = nrf.read(length)  # clears info from any() and nrf.pipe
            # increment counter before sending it back in responding payload
            counter[0] = received[7:8][0] + 1
            nrf.listen = False  # put the radio in TX mode
            result = False
            ack_timeout = time.monotonic_ns() + 200000000
            while not result and time.monotonic_ns() < ack_timeout:
                # try to send reply for 200 milliseconds (at most)
                result = nrf.send(b"World \0" + bytes([counter[0]]))
            nrf.listen = True  # put the radio back in RX mode
            print(
                "Received {} on pipe {}: {}{} Sent:".format(
                    length,
                    pipe,
                    bytes(received[:6]).decode("utf-8"),  # convert to str
                    received[7:8][0],
                ),
                end=" ",
            )
            if not result:
                print("Response failed or timed out")
            else:
                print("World", counter[0])
            start_timer = time.monotonic()  # reset timeout

    # recommended behavior is to keep in TX mode when in idle
    nrf.listen = False  # put the nRF24L01 in TX mode + Standby-I power state


def set_role():
    """Set the role using stdin stream. Timeout arg for slave() can be
    specified using a space delimiter (e.g. 'R 10' calls `slave(10)`)

    :return:
        - True when role is complete & app should continue running.
        - False when app should exit
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
        if len(user_input) > 1:
            slave(int(user_input[1]))
        else:
            slave()
        return True
    if user_input[0].upper().startswith("T"):
        if len(user_input) > 1:
            master(int(user_input[1]))
        else:
            master()
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = False
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nRF24L01 manual ACK example")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = False
else:
    print("    Run slave() on receiver\n    Run master() on transmitter")
