"""
Example of library usage for streaming multiple payloads.
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

# uncomment the following 2 lines for compatibility with TMRh20 library
# nrf.allow_ask_no_ack = False
nrf.dynamic_payloads = False


def make_buffers(size=32):
    """return a list of payloads"""
    buffers = []
    # we'll use `size` for the number of payloads in the list and the
    # payloads' length
    for i in range(size):
        # prefix payload with a sequential letter to indicate which
        # payloads were lost (if any)
        buff = bytes([i + (65 if 0 <= i < 26 else 71)])
        for j in range(size - 1):
            char = j >= (size - 1) / 2 + abs((size - 1) / 2 - i)
            char |= j < (size - 1) / 2 - abs((size - 1) / 2 - i)
            buff += bytes([char + 48])
        buffers.append(buff)
        del buff
    return buffers


def master(count=1, size=32):  # count = 5 will transmit the list 5 times
    """Transmits multiple payloads using `RF24.send()` and `RF24.resend()`."""
    buffers = make_buffers(size)  # make a list of payloads
    nrf.listen = False  # ensures the nRF24L01 is in TX mode
    successful = 0  # keep track of success rate
    for _ in range(count):
        start_timer = time.monotonic_ns()  # start timer
        # NOTE force_retry=2 internally invokes `RF24.resend()` 2 times at
        # most for payloads that fail to transmit.
        result = nrf.send(buffers, force_retry=2)  # result is a list
        end_timer = time.monotonic_ns()  # end timer
        print("Transmission took", (end_timer - start_timer) / 1000, "us")
        for r in result:  # tally the resulting success rate
            successful += 1 if r else 0
    print(
        "successfully sent {}%".format(successful / (size * count) * 100),
        "({}/{})".format(successful, size * count),
    )


def master_fifo(count=1, size=32):
    """Similar to the `master()` above except this function uses the full
    TX FIFO and `RF24.write()` instead of `RF24.send()`"""
    buf = make_buffers(size)  # make a list of payloads
    nrf.listen = False  # ensures the nRF24L01 is in TX mode
    for cnt in range(count):  # transmit the same payloads this many times
        nrf.flush_tx()  # clear the TX FIFO so we can use all 3 levels
        # NOTE the write_only parameter does not initiate sending
        buf_iter = 0  # iterator of payloads for the while loop
        failures = 0  # keep track of manual retries
        start_timer = time.monotonic_ns()  # start timer
        while buf_iter < size:  # cycle through all the payloads
            nrf.ce_pin = False
            while buf_iter < size and nrf.write(buf[buf_iter], write_only=1):
                # NOTE write() returns False if TX FIFO is already full
                buf_iter += 1  # increment iterator of payloads
            nrf.ce_pin = True
            while not nrf.fifo(True, True):  # updates irq_df flag
                if nrf.irq_df:
                    # reception failed; we need to reset the irq_rf flag
                    nrf.ce_pin = False  # fall back to Standby-I mode
                    failures += 1  # increment manual retries
                    nrf.clear_status_flags()  # clear the irq_df flag
                    if failures > 99 and buf_iter < 7 and cnt < 2:
                        # we need to prevent an infinite loop
                        print(
                            "Make sure slave() node is listening."
                            " Quiting master_fifo()"
                        )
                        buf_iter = size + 1  # be sure to exit the while loop
                        nrf.flush_tx()  # discard all payloads in TX FIFO
                    else:
                        nrf.ce_pin = True  # start re-transmitting
        nrf.ce_pin = False
        end_timer = time.monotonic_ns()  # end timer
        print(
            "Transmission took {} us".format((end_timer - start_timer) / 1000),
            "with {} failures detected.".format(failures),
        )


def slave(timeout=5):
    """Stops listening after a `timeout` with no response"""
    nrf.listen = True  # put radio into RX mode and power up
    count = 0  # keep track of the number of received payloads
    start_timer = time.monotonic()  # start timer
    while time.monotonic() < start_timer + timeout:
        if nrf.available():
            count += 1
            # retreive the received packet's payload
            buffer = nrf.read()  # clears flags & empties RX FIFO
            print("Received:", buffer, "-", count)
            start_timer = time.monotonic()  # reset timer on every RX payload

    # recommended behavior is to keep in TX mode while idle
    nrf.listen = False  # put the nRF24L01 is in TX mode


def set_role():
    """Set the role using stdin stream. Timeout arg for slave() can be
    specified using a space delimiter (e.g. 'R 10' calls `slave(10)`)
    """
    user_input = (
        input(
            "*** Enter 'R' for receiver role.\n"
            "*** Enter 'T' for transmitter role (using 1 level  of the TX FIFO).\n"
            "*** Enter 'F' for transmitter role (using all 3 levels of the TX FIFO).\n"
            "*** Enter 'Q' to quit example.\n"
        )
        or "?"
    )
    user_input = user_input.split()
    if user_input[0].upper().startswith("R"):
        slave(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("T"):
        master(*[int(x) for x in user_input[1:3]])
        return True
    if user_input[0].upper().startswith("F"):
        master_fifo(*[int(x) for x in user_input[1:3]])
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = False
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print("    nRF24L01 Stream test")

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = False
else:
    print("    Run slave() on receiver")
    print("    Run master() on transmitter to use 1 level of the TX FIFO")
    print("    Run master_fifo() on transmitter to use all 3 levels of the TX FIFO")
