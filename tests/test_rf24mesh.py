"""Test RF24Mesh class"""
from pathlib import Path
from typing import Dict
import pytest
from circuitpython_nrf24l01.rf24_mesh import RF24Mesh
from circuitpython_nrf24l01.network.constants import NETWORK_DEFAULT_ADDR


@pytest.mark.parametrize("dhcp_dict", [{2: 0o5}])
@pytest.mark.parametrize("as_binary", [True, False])
def test_dhcp_persistence(
    dhcp_dict: Dict[int, int],
    as_binary: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mesh_obj: RF24Mesh,
):
    """test DHCP persistence in RF24Mesh (using a dummy class)"""

    monkeypatch.chdir(str(tmp_path))
    for key, val in dhcp_dict.items():
        mesh_obj.set_address(key, val)
    if as_binary:
        mesh_obj.save_dhcp("dhcplist.txt", as_bin=as_binary)
        mesh_obj.load_dhcp("dhcplist.txt", as_bin=as_binary)
    else:
        mesh_obj.save_dhcp()
        mesh_obj.load_dhcp()
    assert mesh_obj.dhcp_dict == dhcp_dict


@pytest.mark.parametrize("_id", [2, 255, 450])
def test_node_id(mesh_obj: RF24Mesh, _id: int):
    """test node_id attribute"""
    mesh_obj.node_id = _id
    assert mesh_obj.node_id == (_id & 0xFF)


def test_print_details(mesh_obj: RF24Mesh, capsys: pytest.CaptureFixture):
    """verify DHCP list is included with print_details()."""
    mesh_obj.set_address(2, 0o5)
    mesh_obj.print_details(dump_pipes=True, network_only=True)
    out, _ = capsys.readouterr()
    assert "DHCP List" in out


@pytest.mark.parametrize("enable", [True, False])
def test_allow_children(mesh_obj: RF24Mesh, enable: bool):
    """test allow_children attribute"""
    mesh_obj.allow_children = enable
    assert mesh_obj.allow_children is enable


def test_release_address(mesh_obj: RF24Mesh):
    """test release_address()"""
    assert mesh_obj.release_address()
    assert mesh_obj.node_address == NETWORK_DEFAULT_ADDR
    assert not mesh_obj.release_address()


@pytest.mark.parametrize(
    "buf_size", [4, 125, pytest.param(145, marks=pytest.mark.xfail)]
)
def test_write(mesh_obj: RF24Mesh, buf_size: int):
    """test write()"""
    assert mesh_obj.write(0o2, "T", b"\0" * buf_size)
