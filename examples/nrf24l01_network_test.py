"""
An all-purpose example of using the nRF24L01 transceiver in a network of nodes.
"""
import time
import struct
from circuitpython_nrf24l01.network.constants import MAX_FRAG_SIZE, NETWORK_DEFAULT_ADDR

# import wrappers to imitate circuitPython's DigitalInOut
from circuitpython_nrf24l01.wrapper import DigitalInOut

# DigitalInOut is a wrapper for machine.Pin() on MicroPython
#   or simply digitalio.DigitalInOut on CircuitPython and Linux

IS_MESH = (
    (
        input(
            "    nrf24l01_network_test example\n"
            "Would you like to run as a mesh network node (y/n)? Defaults to 'Y' "
        )
        or "Y"
    )
    .upper()
    .startswith("Y")
)

# to use different addresses on a set of radios, we need a variable to
# uniquely identify which address this radio will use
THIS_NODE = 0
print(
    "Remember, the master node always uses `0` as the node_address and node_id."
    "Which node is this? Enter",
    end=" ",
)
if IS_MESH:
    # node_id must be less than 255
    THIS_NODE = int(input("a unique int. Defaults to '0' ") or "0") & 0xFF
else:
    # logical node_address is in octal
    THIS_NODE = int(input("'0', '1', or octal int. Defaults to '0' ") or "0", 8)

if IS_MESH:
    if not THIS_NODE:  # if this is not a mesh network master node
        from circuitpython_nrf24l01.rf24_mesh import RF24MeshNoMaster as Network
    else:
        from circuitpython_nrf24l01.rf24_mesh import RF24Mesh as Network
    print("Using RF24Mesh class")
else:
    from circuitpython_nrf24l01.rf24_network import RF24Network as Network

    # we need to construct frame headers for RF24Network.send()
    from circuitpython_nrf24l01.network.structs import RF24NetworkHeader

    # we need to construct entire frames for RF24Network.write() (not for this example)
    # from circuitpython_nrf24l01.network.structs import RF24NetworkFrame
    print("Using RF24Network class")

# default values that allow using no radio module (for testing only)
SPI_BUS = None
CSN_PIN = None
CE_PIN = None

try:  # on CircuitPython & Linux
    import board

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

except ImportError:  # on MicroPython
    import machine

    # the argument passed here changes according to the board used
    SPI_BUS = machine.SPI(1)

    # instantiate the integers representing micropython pins as
    # DigitalInOut compatible objects
    CSN_PIN = DigitalInOut(5)
    CE_PIN = DigitalInOut(4)

except NotImplementedError:  # running on PC (no GPIO)
    pass  # using a shim


# initialize this node as the network
nrf = Network(SPI_BUS, CSN_PIN, CE_PIN, THIS_NODE)

# TMRh20 examples use a channel 97 for RF24Mesh library
# TMRh20 examples use a channel 90 for RF24Network library
nrf.channel = 90 + IS_MESH * 7

# set the Power Amplifier level to -12 dBm since this test example is
# usually run with nRF24L01 transceivers in close proximity
nrf.pa_level = -12

# using the python keyword global is bad practice. Instead we'll use a 1 item
# list to store our number of the payloads sent
packets_sent = [0]

if THIS_NODE:  # if this node is not the network master node
    if IS_MESH:  # mesh nodes need to bond with the master node
        print("Connecting to mesh network...", end=" ")

        # get this node's assigned address and connect to network
        if nrf.renew_address() is None:
            print("failed. Please try again manually with `nrf.renew_address()`")
        else:
            print("assigned address:", oct(nrf.node_address))
else:
    print("Acting as network master node.")


def emit(node=not THIS_NODE, frag=False, count=5, interval=1):
    """Transmits 1 (or 2) integers or a large buffer

    :param int node: The target node for network transmissions.
        If using RF24Mesh, this is a unique node_id.
        If using RF24Network, this is the node's logical address.
    :param bool frag: Only use fragmented messages?
    :param int count: The max number of messages to transmit.
    :param int interval: time (in seconds) between transmitting messages.
    """
    failures = 0
    start_timer = time.monotonic()
    while failures < 6 and count:
        nrf.update()  # keep the network layer current
        now = time.monotonic()
        if now >= start_timer + interval:  # its time to emmit
            start_timer = now
            count -= 1
            packets_sent[0] += 1
            #TMRh20's RF24Mesh examples use 1 long int containing a timestamp (in ms)
            message = struct.pack("<L", int(now * 1000))
            if frag:
                message = bytes(
                    range((packets_sent[0] + MAX_FRAG_SIZE) % nrf.max_message_length)
                )
            elif not IS_MESH:  # if using RF24Network
                # TMRh20's RF24Network examples use 2 long ints, so add another
                message += struct.pack("<L", packets_sent[0])
            result = False
            start = time.monotonic_ns()
            if IS_MESH:  # send() is a little different for RF24Mesh vs RF24Network
                result = nrf.send(node, "M", message)
            else:
                result = nrf.send(RF24NetworkHeader(node, "T"), message)
            end = time.monotonic_ns()
            failures += not result
            print(
                "Sending {} (len {})...".format(packets_sent[0], len(message)),
                "ok." if result else "failed.",
                "Transmission took %d ms" % int((end - start) / 1000000),
            )


def idle(timeout=30):
    """Listen for any payloads and print the transaction

    :param int timeout: The number of seconds to wait (with no transmission)
        until exiting function.
    """
    start_timer = time.monotonic()
    while (time.monotonic() - start_timer) < timeout:
        nrf.update()  # keep the network layer current
        while nrf.available():
            start_timer = time.monotonic()  # reset timer
            payload = nrf.read()
            payload_len = len(payload.message)
            print("Received payload", end=" ")
            # TMRh20 examples only use 1 or 2 long ints as small messages
            if payload_len < MAX_FRAG_SIZE and payload_len % 4 == 0:
                # if not a large fragmented message and multiple of 4 bytes
                fmt = "<" + "L" * int(payload_len / 4)
                print(struct.unpack(fmt, bytes(payload.message)), end=" ")
            print(payload.header.to_string(), "length", payload_len)


def set_role():
    """Set the role using stdin stream. Timeout arg for idle() can be
    specified using a space delimiter (e.g. 'I 10' calls `idle(10)`)
    """
    prompt = (
        "*** Enter 'I' for idle role.\n"
        "*** Enter 'E <node number>' for emitter role.\n"
        "*** Enter 'E <node number> 1' to emit fragmented messages.\n"
    )
    if IS_MESH and nrf.node_address == NETWORK_DEFAULT_ADDR:
        prompt = (
            "*** Mesh node not connected.\n"
            "*** Enter 'C' to connect to to master node.\n"
            "*** Enter 'C <timeout seconds>' to change the timeout value.\n"
        )
    user_input = input(prompt + "*** Enter 'Q' to quit example.\n") or "?"
    user_input = user_input.split()
    if user_input[0].upper().startswith("C"):
        print("Connecting to mesh network...", end=" ")
        result = nrf.renew_address(int(user_input[1])) is not None
        print(("assigned address " + oct(nrf.node_address)) if result else "failed.")
        return True
    if user_input[0].upper().startswith("I"):
        idle(*[int(x) for x in user_input[1:2]])
        return True
    if user_input[0].upper().startswith("E"):
        emit(*[int(x) for x in user_input[1:5]])
        return True
    if user_input[0].upper().startswith("Q"):
        nrf.power = 0
        return False
    print(user_input[0], "is an unrecognized input. Please try again.")
    return set_role()


if __name__ == "__main__":

    try:
        while set_role():
            pass  # continue example until 'Q' is entered
    except KeyboardInterrupt:
        print(" Keyboard Interrupt detected. Powering down radio...")
        nrf.power = 0
elif nrf.node_address != NETWORK_DEFAULT_ADDR:
    print("    Run emit(<node number>) to transmit.")
    print("    Run idle() to receive or forward messages in the network.")
    print("    Pass keyword arg `frag=True` to emit() fragmented messages.")
