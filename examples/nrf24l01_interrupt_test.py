"""
Simple example of detecting (and verifying) the IRQ (interrupt) pin on the
nRF24L01
    .. note:: this script uses the non-blocking `write()` function because
        the function `send()` clears the IRQ flags upon returning
"""
import time
import board
import digitalio

# if running this on a ATSAMD21 M0 based board
# from circuitpython_nrf24l01.rf24_lite import RF24
from circuitpython_nrf24l01.rf24 import RF24

# select your digital input pin that's connected to the IRQ pin on the nRF4L01
irq_pin = digitalio.DigitalInOut(board.D12)
irq_pin.switch_to_input()  # make sure its an input object
# change these (digital output) pins accordingly
ce = digitalio.DigitalInOut(board.D4)
csn = digitalio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI()  # init spi bus object

# we'll be using the dynamic payload size feature (enabled by default)
# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce)

# this example uses the ACK payload to trigger the IRQ pin active for
# the "on data received" event
nrf.ack = True  # enable ACK payloads

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12

# address needs to be in a buffer protocol object (bytearray is preferred)
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


def _ping_and_prompt():
    """transmit 1 payload, wait till irq_pin goes active, print IRQ status
    flags."""
    ce.value = 1  # tell the nRF24L01 to prepare sending a single packet
    time.sleep(0.00001)  # mandatory 10 microsecond pulse starts transmission
    ce.value = 0  # end 10 us pulse; use only 1 buffer from TX FIFO
    while irq_pin.value:  # IRQ pin is active when LOW
        pass
    print("IRQ pin went active LOW.")
    nrf.update()  # update irq_d? status flags
    print(
        "\tirq_ds: {}, irq_dr: {}, irq_df: {}".format(
            nrf.irq_ds, nrf.irq_dr, nrf.irq_df
        )
    )


def master():
    """Transmits 3 times: successfully receive ACK payload first, successfully
    transmit on second, and intentionally fail transmit on the third"""
    nrf.listen = False  # ensures the nRF24L01 is in TX mode
    # NOTE nrf.write() internally calls nrf.clear_status_flags() first

    # load 2 buffers into the TX FIFO; write_only=True leaves CE pin LOW
    nrf.write(b"Ping ", write_only=True)
    nrf.write(b"Pong ", write_only=True)

    # on data ready test
    print("\nConfiguring IRQ pin to only ignore 'on data sent' event")
    nrf.interrupt_config(data_sent=False)
    print("    Pinging slave node for an ACK payload...", end=" ")
    _ping_and_prompt()  # CE pin is managed by this function
    print(
        "\t'on data ready' event test{}successful".format(
            " " if nrf.irq_dr else " un"
        )
    )

    # on data sent test
    print("\nConfiguring IRQ pin to only ignore 'on data ready' event")
    nrf.interrupt_config(data_recv=False)
    print("    Pinging slave node again...             ", end=" ")
    _ping_and_prompt()  # CE pin is managed by this function
    print(
        "\t'on data sent' event test{}successful".format(
            " " if nrf.irq_ds else " un"
        )
    )

    # trigger slave node to exit by filling the slave node's RX FIFO
    print("\nSending one extra payload to fill RX FIFO on slave node.")
    if nrf.send(b"Radio", send_only=True):
        # when send_only parameter is True, send() ignores RX FIFO usage
        if nrf.fifo(False, False):  # is RX FIFO full?
            print("Slave node should not be listening anymore.")
        else:
            print(
                "transmission succeeded, "
                "but slave node might still be listening"
            )
    else:
        print("Slave node was unresponsive.")

    # on data fail test
    print("\nConfiguring IRQ pin to go active for all events.")
    nrf.interrupt_config()
    print("    Sending a ping to inactive slave node...", end=" ")
    nrf.flush_tx()  # just in case any previous tests failed
    nrf.write(b"Dummy", write_only=True)  # CE pin is left LOW
    _ping_and_prompt()  # CE pin is managed by this function
    print(
        "\t'on data failed' event test{}successful".format(
            " " if nrf.irq_df else " un"
        )
    )
    nrf.flush_tx()  # flush artifact payload in TX FIFO from last test
    # all 3 ACK payloads received were 4 bytes each, and RX FIFO is full
    # so, fetching 12 bytes from the RX FIFO also flushes RX FIFO
    print("\nComplete RX FIFO:", nrf.read(12))


def slave(timeout=6):  # will listen for 6 seconds before timing out
    """Only listen for 3 payload from the master node"""
    # setup radio to recieve pings, fill TX FIFO with ACK payloads
    nrf.load_ack(b"Yak ", 1)
    nrf.load_ack(b"Back", 1)
    nrf.load_ack(b" ACK", 1)
    nrf.listen = True  # start listening & clear irq_dr flag
    start_timer = time.monotonic()  # start timer now
    while not nrf.fifo(0, 0) and time.monotonic() - start_timer < timeout:
        # if RX FIFO is not full and timeout is not reached, then keep going
        pass
    nrf.listen = False  # put nRF24L01 in Standby-I mode when idling
    if not nrf.fifo(False, True):  # if RX FIFO is not empty
        # all 3 payloads received were 5 bytes each, and RX FIFO is full
        # so, fetching 15 bytes from the RX FIFO also flushes RX FIFO
        print("Complete RX FIFO:", nrf.read(15))
    nrf.flush_tx()  # discard any pending ACK payloads


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
        master()
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = False
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


print(
    "    nRF24L01 Interrupt pin test\n"
    "    Make sure the IRQ pin is connected to the MCU"
)

if __name__ == "__main__":
    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = False
else:
    print("    Run slave() on receiver\n    Run master() on transmitter")
