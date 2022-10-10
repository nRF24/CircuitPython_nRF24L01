"""Monkeypatch for converting SPI transaction into logging functions that store
registers in a dict."""
import logging
from typing import Union, Tuple
import pytest
from circuitpython_nrf24l01.rf24 import (
    RF24,
    address_repr,
)
from circuitpython_nrf24l01.fake_ble import FakeBLE
from circuitpython_nrf24l01.rf24_network import RF24Network
from circuitpython_nrf24l01.rf24_mesh import RF24Mesh

# pylint: disable=redefined-outer-name


class RegisterError(Exception):
    """Exception for when register offset does not exist."""


class RegisterReadOnly(RegisterError):
    """Exception when register offset is not or'd with 0x20 for write operation."""


class RadioState:
    """A minimal state machine for use with a fake SPI interface object."""

    registers = {
        0: bytearray([0]),  # CONFIG
        1: bytearray([0]),  # AUTO_ACK
        2: bytearray([0]),  # OPEN_PIPES
        3: bytearray([3]),  # ADDRESS_LENGTH
        4: bytearray([0]),  # SETUP_RETR
        5: bytearray([2]),  # CHANNEL
        6: bytearray([0]),  # RF_PA_RATE
        7: bytearray([4]),  # STATUS
        8: bytearray([0]),  # OBSERVE_TX
        9: bytearray([0]),  # RPD
        0x0A: bytearray(b"\xE7" * 5),  # RX_ADDR_P0
        0x0B: bytearray(b"\xC2" * 5),  # RX_ADDR_P1
        0x0C: bytearray(b"\xC3"),  # RX_ADDR_P2
        0x0D: bytearray(b"\xC4"),  # RX_ADDR_P3
        0x0E: bytearray(b"\xC5"),  # RX_ADDR_P4
        0x0F: bytearray(b"\xC6"),  # RX_ADDR_P5
        0x10: bytearray(b"\xE7" * 5),  # TX_ADDRESS
        0x11: bytearray([32]),  # RX_PL_LENG P0
        0x12: bytearray([32]),  # RX_PL_LENG P1
        0x13: bytearray([32]),  # RX_PL_LENG P2
        0x14: bytearray([32]),  # RX_PL_LENG P3
        0x15: bytearray([32]),  # RX_PL_LENG P4
        0x16: bytearray([32]),  # RX_PL_LENG P5
        0x17: bytearray([0]),  # FIFO_STATUS
        0x1C: bytearray([0]),  # DYN_PL_LEN
        0x1D: bytearray([0]),  # TX_FEATURE
    }

    # SPI commands
    rx_fifo = []  # command 0x61
    tx_fifo = []  # commands 0xA0, 0xB0, 0xA8 + pipe number
    logger = logging.getLogger("nRF24L01")

    def __init__(self):
        self.commands = {
            0x60: RadioState.get_pl_width,
            0x61: RadioState.read_payload,
            0xA0: RadioState.write_payload,
            0xB0: RadioState.write_payload,
            0xA8: RadioState.write_payload,
            0xA9: RadioState.write_payload,
            0xAA: RadioState.write_payload,
            0xAB: RadioState.write_payload,
            0xAC: RadioState.write_payload,
            0xAD: RadioState.write_payload,
            0xE1: RadioState.flush_tx,
            0xE2: RadioState.flush_rx,
            0xE3: RadioState.non_op,  # reuse TX command only consumed for testing
            0xFF: RadioState.non_op,
        }

    @staticmethod
    def read_payload(master_out_buf):
        """Read payload from state machine's RX FIFO.
        For simplicity, this doesn't pop payloads from the FIFO."""
        if RadioState.rx_fifo:
            RadioState.logger.debug(
                "Requesting %d bytes from the RX FIFO", len(master_out_buf)
            )
            ret_val = bytearray(b"".join(RadioState.rx_fifo))
            size = min(len(ret_val), len(master_out_buf))
            # NOTE: all tests that use the RX FIFO should set Payload length for pipe 0
            rx_pl_width = RadioState.registers[0x11][0]  # RX_PL_LENG P0
            RadioState.logger.debug("Putting %d back into RX FIFO", len(ret_val[size:]))
            RadioState.logger.debug("    Starting at offset %d", size)
            RadioState.rx_fifo = [
                ret_val[i : i + rx_pl_width]
                for i in range(size, len(ret_val), rx_pl_width)
            ]
            RadioState.logger.debug(
                "RX FIFO is now [%s]",
                ", ".join([f"{len(x)} bytes" for x in RadioState.rx_fifo]),
            )
            if not RadioState.rx_fifo:
                RadioState.flush_rx()  # set other register data appropriately
            else:
                RadioState.registers[7][0] &= 0xF1
                RadioState.registers[7][0] |= 4  # say payload is from pipe 1
                RadioState.registers[0x17][0] &= 0xF0
                if len(RadioState.rx_fifo) >= 3:
                    RadioState.registers[0x17][0] |= 2
            return (
                RadioState.registers[7]
                + ret_val[:size]
                + bytearray(b"." * (len(master_out_buf) - size))
            )
        return RadioState.registers[7] + (b"." * len(master_out_buf))

    @staticmethod
    def write_payload(payload):
        """Write payload to state machine's TX FIFO."""
        RadioState.tx_fifo.append(payload)
        RadioState.registers[0x17][0] &= 0xCF
        if len(RadioState.tx_fifo) >= 3:
            RadioState.registers[0x17][0] |= 0x20
            RadioState.registers[7][0] |= 1
        return RadioState.registers[7] + (b"\0" * len(payload))

    @staticmethod
    def get_pl_width(*_):
        """Get dynamic payload length (agnostic to pipe number in testing)."""
        if RadioState.rx_fifo:
            return RadioState.registers[7] + bytearray([len(RadioState.rx_fifo[0])])
        return RadioState.registers[7] + b"\0"

    @staticmethod
    def non_op(*_):
        """Mock a non-operation command."""
        return RadioState.registers[7]

    @staticmethod
    def flush_tx(*_):
        """Flush the state machine's TX FIFO."""
        RadioState.tx_fifo.clear()
        RadioState.registers[7][0] &= 0xFE
        RadioState.registers[0x17][0] &= 0xCF
        RadioState.registers[0x17][0] |= 0x10
        return RadioState.registers[7]

    @staticmethod
    def flush_rx(*_):
        """Flush the state machine's RX FIFO."""
        RadioState.rx_fifo.clear()
        RadioState.registers[7][0] |= 0x0E
        RadioState.registers[0x17][0] &= 0xF0
        RadioState.registers[0x17][0] |= 1
        return RadioState.registers[7]

    def __getitem__(self, __offset: int) -> bytearray:
        register = __offset & 0x1F
        ret_val = self.registers[7] + self.registers[register]
        self.logger.info(
            "SPI read %02X -> %s", register, address_repr(ret_val, False, " ")
        )
        return ret_val

    def __setitem__(self, __offset, value):
        cmd_bits = __offset & 0xE0
        # self.logger.debug("offset: %02X, cmd_bits: %02X", __offset, cmd_bits)
        if cmd_bits == 0x20 or not cmd_bits:
            if not cmd_bits:
                # self.logger.debug("register %02X is a read register operation.", __offset)
                raise RegisterReadOnly(
                    "writing a register requires the 0x20 bit asserted"
                )
            register = __offset & 0x1F
            if register == 7:
                # STATUS register bits 4-7 are write-able (bits 0-3 are read-only)
                # since bits 4-7 don't stick (used to clear IRQ), then we use the value as
                # a mask for testing
                self.registers[7][0] &= ~value[0]
            else:
                self.registers[register] = value
            self.logger.info(
                "SPI write %02X -> %s", register, address_repr(value, False, " ")
            )
        elif __offset not in self.registers:
            self.logger.info(
                "SPI command %02X (STATUS: %02X)", __offset, RadioState.registers[7][0]
            )
            # SPI commands get special treatment since they aren't actual registers
            raise RegisterError("no such register at offset {}".format(__offset))
        # If we got here, then there was an unsupported offset specified.
        # For testing, we ignore the 0x50 command (from non-plus variants/clones).


class ShimSpiDev:
    """A fake SPI device class used for testing."""

    def __init__(self):
        self.no_cs = True
        self.state = RadioState()

    def open(self, bus: int, device: int):
        """Mock init SPI bus with device CSN signal."""
        return (bus, device)

    def close(self):
        """Mock de-init SPI bus."""
        return

    def xfer2(self, out_buf: Union[bytes, bytearray], baud_rate: int) -> bytearray:
        """A mock function for a full duplex SPI transaction."""
        register = out_buf[0]
        assert baud_rate
        try:  # assume `register` is a write operation
            self.state[register] = bytearray(out_buf[1:])
            return self.state.registers[7]
        except RegisterReadOnly:  # `register` is a SPI read operation
            return self.state[register]
        except RegisterError:  # `register` is a SPI command
            if register in self.state.commands:
                return self.state.commands[register](out_buf[1:])
            return self.state.registers[7]


class ShimDigitalIO:
    """A pseudo DigitalInOut class for testing purposes."""

    def __init__(self) -> None:
        self.value = False

    def switch_to_output(self, value=False):
        """Dummy function"""
        self.value = value


@pytest.fixture
def spi_obj():
    """creates a dummy SPI object (used as pytest fixture)."""
    return (ShimSpiDev(), ShimDigitalIO(), ShimDigitalIO())


@pytest.fixture
def rf24_obj(spi_obj):
    """creates a RF24 object (used as pytest fixture)."""
    radio = RF24(*spi_obj)
    return radio


@pytest.fixture
def ble_obj(spi_obj: Tuple[ShimSpiDev, ShimDigitalIO, ShimDigitalIO]):
    """creates a RF24 object (used as pytest fixture)."""
    radio = FakeBLE(*spi_obj)
    return radio


@pytest.fixture
def net_obj(
    spi_obj: Tuple[ShimSpiDev, ShimDigitalIO, ShimDigitalIO],
    monkeypatch: pytest.MonkeyPatch,
    n_id: int = 0,
):
    """creates a RF24Network object (used as pytest fixture)."""
    network = RF24Network(*spi_obj, node_address=n_id)

    # pylint: disable=unused-argument
    def pseudo_send(buf, ask_no_ack=False, send_only=False):
        spi_obj[0].state.tx_fifo.append(buf)
        return True

    # pylint: enable=unused-argument

    monkeypatch.setattr(network._rf24, "send", pseudo_send)
    return network


@pytest.fixture
def mesh_obj(
    spi_obj: Tuple[ShimSpiDev, ShimDigitalIO, ShimDigitalIO],
    monkeypatch: pytest.MonkeyPatch,
    n_id: int = 0,
):
    """creates a RF24Mesh object (used as pytest fixture)."""
    mesh = RF24Mesh(*spi_obj, node_id=n_id)

    # pylint: disable=unused-argument
    def pseudo_send(buf, ask_no_ack=False, send_only=False):
        spi_obj[0].state.tx_fifo.append(buf)
        return True

    # pylint: enable=unused-argument

    monkeypatch.setattr(mesh._rf24, "send", pseudo_send)
    return mesh
