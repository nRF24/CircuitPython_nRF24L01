"""
Use the circuitpython_nrf24l01 library to transfer a file wirelessly.
"""
import sys
import time
import argparse
import board
from circuitpython_nrf24l01.rf24 import RF24

# import wrappers to imitate circuitPython's DigitalInOut
from circuitpython_nrf24l01.wrapper import RPiDIO, DigitalInOut

# RPiDIO is wrapper for RPi.GPIO on Linux
# DigitalInOut is a wrapper for machine.Pin() on MicroPython
#   or simply digitalio.DigitalInOut on CircuitPython and Linux

spi = None  # scoped placeholder

# change these (digital output) pins accordingly
ce_pin = DigitalInOut(board.D4)
csn = DigitalInOut(board.D5)

try:  # on Linux
    import spidev

    spi = spidev.SpiDev()  # for a faster interface on linux
    csn = 0  # use CE0 on default bus (even faster than using any pin)
    if RPiDIO is not None:  # RPi.GPIO lib is present
        # RPi.GPIO is faster than CircuitPython on Linux
        ce_pin = RPiDIO(22)  # using pin gpio22 (BCM numbering)

except ImportError:  # on CircuitPython only
    # using board.SPI() automatically selects the MCU's
    # available SPI pins, board.SCK, board.MOSI, board.MISO
    spi = board.SPI()  # init spi bus object

# initialize the nRF24L01 on the spi bus object
nrf = RF24(spi, csn, ce_pin)
# On Linux using SpiDev, csn value has a coded meaning:
#                 0 = bus 0, CE0 ; SPI bus 0 is enabled by default
#                10 = bus 1, CE0 ; enable SPI bus 2 prior to running this
#                21 = bus 2, CE1 ; enable SPI bus 1 prior to running this

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument(
    "-r",
    "--role",
    default=0,
    type=int,
    choices=range(2),
    help="'1' specifies the TX role. '0' specifies the RX role.",
)
parser.add_argument(
    "-f",
    "--file",
    default=None,
    type=str,
    help="the path and name of the file to transfer.",
)
parser.add_argument(
    "-x",
    "--express",
    default=False,
    type=bool,
    help="Defaults to False. Set to True to use all 3 levels of TX FIFO.",
)


PL_SIZE = 32


def make_buffers(f_name, buffer):
    """Return a list of payloads sliced from a ``buffer``"""
    if len(f_name) > PL_SIZE:
        f_name = f_name[:26] + "_1" + f_name[-4:]
    buffers = [bytes(f_name.encode("utf-8"))]
    for i in range(0, len(buffer), PL_SIZE):
        end_slice = len(buffer) if i + PL_SIZE > len(buffer) else i + PL_SIZE
        buffers.append(buffer[i:end_slice])
    print("{} bytes split into {} payloads".format(len(buffer), len(buffers)))
    return buffers


def master(buffers):
    """Transmits multiple payloads using `send()` and `resend()`."""
    result = []
    start_timer = time.monotonic()
    with nrf:
        nrf.listen = False  # ensures the nRF24L01 is in TX mode
        result = nrf.send(buffers, force_retry=3)
    end_timer = time.monotonic()
    print("Transmission took", end_timer - start_timer, "s")

    successful = 0  # keep track of success rate
    for r in result:  # tally the resulting success rate
        successful += 1 if r else 0
    print(
        "successfully sent {}% ({}/{}) of {}".format(
            successful / (len(buffers)) * 100,
            successful,
            len(buffers),
            buffers[0].decode("utf-8"),
        )
    )


def master_fifo(f_name):
    """Similar to the `master()` above except this function uses the full
    TX FIFO and `RF24.write()` instead of `RF24.send()`"""
    failures = 0  # keep track of manual retries
    start_timer = 0
    max_len = 0
    with open(f_name, "rb") as file_in:
        max_len = file_in.seek(0, 2)  # get max len of file
        file_in.seek(0)  # reset position to beginning of file
        buf = f_name.encode("utf-8")  # tell slave file's name w/ 1st payload
        with nrf:
            nrf.listen = False  # ensures the nRF24L01 is in TX mode
            nrf.flush_tx()  # clear the TX FIFO so we can use all 3 levels
            start_timer = time.monotonic()  # start timer
            while file_in.tell() < max_len:  # cycle through the file
                nrf.ce_pin = False
                while file_in.tell() < max_len and nrf.write(buf, write_only=1):
                    # NOTE write() returns False if TX FIFO is already full
                    buf = file_in.read(32)
                    # if dynamic payloads are disabled, uncomment the next 2 lines
                    # if len(buf) < 32:
                    #     nrf.set_payload_length(len(buf), 0)
                nrf.ce_pin = True
                while not nrf.fifo(True, True):  # updates irq_df flag
                    if nrf.irq_df:
                        # reception failed; we need to reset the irq_rf flag
                        nrf.ce_pin = False  # fall back to Standby-I mode
                        failures += 1  # increment manual retries
                        nrf.clear_status_flags()  # clear the irq_df flag
                        if failures > 99 and file_in.tell() < (7 * PL_SIZE):
                            # we need to prevent an infinite loop
                            file_in.seek(max_len)  # be sure to exit the while loop
                            nrf.flush_tx()  # discard all payloads in TX FIFO
                        else:
                            nrf.ce_pin = True  # start re-transmitting
    end_timer = time.monotonic()  # end timer
    print(
        "Transmission of {} bytes took {} s with {} failures detected"
        ".".format(max_len, end_timer - start_timer, failures)
    )


def slave(timeout=30):
    """Stops listening after a `timeout` with no response"""
    count = 0  # keep track of the number of received payloads
    file_buf = bytearray()
    file_dets = None
    with nrf:
        nrf.listen = True  # put radio into RX mode and power up
        start_timer = time.monotonic()  # start timer
        while time.monotonic() < start_timer + timeout:
            if nrf.available():
                if not count:
                    file_dets = nrf.read().decode("utf-8")
                    print("Receiving file:", file_dets)
                else:
                    buf = nrf.read()
                    file_buf += buf
                    print("Received: {} payloads".format(count), end="\r")
                count += 1
                start_timer = time.monotonic()  # reset timer on every RX payload
    print("Received: {} payloads".format(count))
    if file_dets:
        with open(file_dets, "wb") as output:
            output.write(file_buf)


if __name__ == "__main__":

    args = parser.parse_args()  # parse any CLI args

    print(sys.argv[0])  # print tool name

    if args.file is None and args.role:
        print("no file designated for transfer.")
        parser.print_help()
        sys.exit()
    elif args.file is not None and not args.role:
        print("setting role to TX")
        args.role = 1

    # addresses needs to be in a buffer protocol object (bytearray)
    address = [b"1wifi", b"2wifi"]

    # set TX address of RX node into the TX pipe
    nrf.open_tx_pipe(address[args.role])  # always uses pipe 0

    # set RX address of TX node into an RX pipe
    nrf.open_rx_pipe(1, address[not args.role])  # using pipe 1

    # change data rate to 2 million bits per second (Mbps)
    nrf.data_rate = 2

    # uncomment the following 2 lines for compatibility with TMRh20 library
    # nrf.allow_ask_no_ack = False
    # nrf.dynamic_payloads = False

    try:
        if bool(args.role):
            if not args.express:
                file_bin = bytearray()
                with open(args.file, "rb", buffering=0) as src:
                    file_bin = src.readall()
                master(make_buffers(args.file, file_bin))
            else:
                master_fifo(args.file)
        else:
            slave()
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Exiting...")
        nrf.power = False
