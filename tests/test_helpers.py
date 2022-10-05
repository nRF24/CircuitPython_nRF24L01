"""tests related to helper functions."""
from pathlib import Path
from typing import Union, Dict
import pytest
from circuitpython_nrf24l01.rf24 import address_repr
from circuitpython_nrf24l01.network.mixins import _lvl_2_addr
from circuitpython_nrf24l01.rf24_mesh import RF24Mesh


@pytest.mark.parametrize(
    "addr,expected", [(b"1Node", "65646F4E31"), (b"\0\xFF\1", "01FF00")]
)
def test_addr_repr(addr: Union[bytes, bytearray], expected: str):
    """test address_repr()"""
    assert expected == address_repr(addr)


@pytest.mark.parametrize(
    "lvl,expected", [(0, 0), (1, 0o1), (2, 0o10), (3, 0o100), (4, 0o1000)]
)
def test_lvl_mask(lvl: int, expected: int):
    """test _lvl_2_addr()"""
    assert expected == _lvl_2_addr(lvl)


@pytest.mark.parametrize("dhcp_dict", [{2: 0o5}])
@pytest.mark.parametrize("as_binary", [True, False])
def test_dhcp_persistence(
    dhcp_dict: Dict[int, int],
    as_binary: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """test DHCP persistence in RF24Mesh (using a dummy class)"""

    class Dummy:
        """A dummy class to mimic dhcp_dict manipulations in RF24Mesh class."""

        def __init__(self, dhcp: Dict[int, int]):
            self.dhcp_dict = dhcp

        def set_address(
            self, node_id: int, node_address: int, search_by_address: bool = False
        ):
            """Forwards to Rf24Mesh.set_address() using this instance obj (self)."""
            RF24Mesh.set_address(self, node_id, node_address, search_by_address)

    dummy = Dummy(dhcp_dict)
    monkeypatch.chdir(str(tmp_path))
    dummy.set_address(0, 0)
    if as_binary:
        RF24Mesh.save_dhcp(dummy, "dhcplist.txt", as_bin=as_binary)
        RF24Mesh.load_dhcp(dummy, "dhcplist.txt", as_bin=as_binary)
    else:
        RF24Mesh.save_dhcp(dummy)
        RF24Mesh.load_dhcp(dummy)
    # merge dict entries
    dhcp_dict[0] = 0
    assert dummy.dhcp_dict == dhcp_dict
