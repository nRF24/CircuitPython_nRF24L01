"""
An all-purpose example of using the nRF24L01 transceiver in a network of nodes.
"""
import time
import struct
import board
from digitalio import DigitalInOut
from circuitpython_nrf24l01.network.constants import MAX_FRAG_SIZE, NETWORK_DEFAULT_ADDR

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
    "\nWhich node is this? Enter",
    end=" ",
)
if IS_MESH:
    # node_id must be less than 256
    THIS_NODE = int(input("a unique int. Defaults to '0' ") or "0") & 0xFF
else:
    # logical node_address is in octal
    THIS_NODE = int(input("an octal int. Defaults to '0' ") or "0", 8)

if IS_MESH:
    if THIS_NODE:  # if this is not a mesh network master node
        from circuitpython_nrf24l01.rf24_mesh import RF24MeshNoMaster as Network
    else:
        from circuitpython_nrf24l01.rf24_mesh import RF24Mesh as Network
    print("Using RF24Mesh{} class".format("" if not THIS_NODE else "NoMaster"))
else:
    from circuitpython_nrf24l01.rf24_network import RF24Network as Network

    # we need to construct frame headers for RF24Network.send()
    from circuitpython_nrf24l01.network.structs import RF24NetworkHeader

    # we need to construct entire frames for RF24Network.write() (not for this example)
    # from circuitpython_nrf24l01.network.structs import RF24NetworkFrame
    print("Using RF24Network class")

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


# initialize this node as the network
nrf = Network(SPI_BUS, CSN_PIN, CE_PIN, THIS_NODE)

# TMRh20 examples use channel 97 for RF24Mesh library
# TMRh20 examples use channel 90 for RF24Network library
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


def idle(timeout: int = 30, strict_timeout: bool = False):
    """Listen for any payloads and print the transaction

    :param int timeout: The number of seconds to wait (with no transmission)
        until exiting function.
    :param bool strict_timeout: If set to True, then the timer is not reset when
        processing incoming traffic
    """
    print("idling for", timeout, "seconds")
    start_timer = time.monotonic()
    while (time.monotonic() - start_timer) < timeout:
        nrf.update()  # keep the network layer current
        while nrf.available():
            if not strict_timeout:
                start_timer = time.monotonic()  # reset timer
            frame = nrf.read()
            message_len = len(frame.message)
            print("Received payload", end=" ")
            # TMRh20 examples only use 1 or 2 long ints as small messages
            if message_len < MAX_FRAG_SIZE and message_len % 4 == 0:
                # if not a large fragmented message and multiple of 4 bytes
                fmt = "<" + "L" * int(message_len / 4)
                print(struct.unpack(fmt, bytes(frame.message)), end=" ")
            print(frame.header.to_string(), "length", message_len)


def emit(
    node: int = not THIS_NODE, frag: bool = False, count: int = 5, interval: int = 1
):
    """Transmits 1 (or 2) integers or a large buffer

    :param int node: The target node for network transmissions.
        If using RF24Mesh, this is a unique node_id.
        If using RF24Network, this is the node's logical address.
    :param bool frag: Only use fragmented messages?
    :param int count: The max number of messages to transmit.
    :param int interval: time (in seconds) between transmitting messages.
    """
    while count:
        idle(interval, True)  # idle till its time to emit
        count -= 1
        packets_sent[0] += 1
        # TMRh20's RF24Mesh examples use 1 long int containing a timestamp (in ms)
        message = struct.pack("<L", int(time.monotonic() * 1000))
        if frag:
            message = bytes(
                range((packets_sent[0] + MAX_FRAG_SIZE) % nrf.max_message_length)
            )
        elif not IS_MESH:  # if using RF24Network
            # TMRh20's RF24Network examples use 2 long ints, so add another
            message += struct.pack("<L", packets_sent[0])
        result = False
        start = time.monotonic_ns()
        # pylint: disable=no-value-for-parameter
        if IS_MESH:  # send() is a little different for RF24Mesh vs RF24Network
            result = nrf.send(node, "M", message)
        else:
            result = nrf.send(RF24NetworkHeader(node, "T"), message)
        # pylint: enable=no-value-for-parameter
        end = time.monotonic_ns()
        print(
            "Sending {} (len {})...".format(packets_sent[0], len(message)),
            "ok." if result else "failed.",
            "Transmission took {} ms".format(int((end - start) / 1000000)),
        )


def set_role():
    """Set the role using stdin stream. Timeout arg for idle() can be
    specified using a space delimiter (e.g. 'I 10' calls `idle(10)`)
    """
    prompt = (
        "*** Enter 'I' for idle role.\n"
        "*** Enter 'E <node number>' for emitter role.\n"
        "*** Enter 'E <node number> 1' to emit fragmented messages.\n"
    )
    if IS_MESH and THIS_NODE:
        if nrf.node_address == NETWORK_DEFAULT_ADDR:
            prompt += "!!! Mesh node not connected.\n"
        prompt += "*** Enter 'C' to connect to to mesh master node.\n"
    user_input = (input(prompt + "*** Enter 'Q' to quit example.\n") or "?").split()
    if user_input[0].upper().startswith("C"):
        print("Connecting to mesh network...", end=" ")
        result = nrf.renew_address(*[int(x) for x in user_input[1:2]]) is not None
        print(("assigned address " + oct(nrf.node_address)) if result else "failed.")
        return True
    if user_input[0].upper().startswith("I"):
        idle(*[int(x) for x in user_input[1:3]])
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
