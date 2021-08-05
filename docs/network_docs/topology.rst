Network Topology
================

Network Levels
****************

Because of the hardware limitation's of the nRF24L01 transceiver, each network
is arranged in a levels where a parent can have up to 5 children. And each child can also have
up to 5 other children. This is not limitless because this network is designed for low-memory
devices. Consequently, all node's :ref:`Logical Address <logical address>` are limited to 12-bit
integers and use an octal counting scheme.

- The master node (designated with the :ref:`Logical Address <logical address>` ``0o0``)
  is always the only node in the lowest level (denoted as level 0).
- Child nodes are designated by the most significant octal digit in their
  :ref:`Logical Address <Logical Address>`. A child node address' least significant digits are
  the inherited address of it's parent node. Nodes on level 1 only have 1 digit because they are
  children of the master node.

.. graphviz::

    graph network_hierarchy {
        bgcolor="#323232A1"
        newrank=true
        // ratio="0.65"
        node [
            fontcolor="#FEFEFE"
            fontsize=14
            fontname=Arial
        ]
        pad="0"
        margin="0"
        subgraph cluster_hierarchy {
            bgcolor="#24242400"
            color="#24242400"
            node [
                style=filled
                color="#FEFEFE7f"
            ]
            edge [color="#FEFEFE" style="setlinewidth(2)"]
            subgraph lvl_0 {
                "0o0" [
                    shape="circle"
                    style="radial"
                    fillcolor="0.85:#018268;0:#000"
                ]
            }
            subgraph lvl_1 {
                node [fillcolor="#3E0180"]
                "0o1" "0o2" "0o3" "0o4" "0o5"
            }
            subgraph lvl_2 {
                node [fillcolor="#014B80"]
                "0o14" "0o24" "0o34" "0o44" "0o54"
            }
            subgraph lvl_3 {
                node [fillcolor="#0E6902"]
                "0o124" "0o224" "0o324" "0o424" "0o524"
            }
            subgraph lvl_4 {
                node [fillcolor="#80010B"]
                "0o1324" "0o2324" "0o3324" "0o4324" "0o5324"
            }
            "0o0" -- "0o4" -- "0o24" -- "0o324" -- "0o1324"
            "0o0" -- "0o1"; "0o0" -- "0o2"; "0o0" -- "0o3"; "0o0" -- "0o5"
            "0o4" -- "0o14"; "0o4" -- "0o34"; "0o4" -- "0o44"; "0o4" -- "0o54"
            "0o24" -- "0o124"; "0o24" -- "0o224"; "0o24" -- "0o424"; "0o24" -- "0o524"
            "0o324" -- "0o2324"; "0o324" -- "0o3324"; "0o324" -- "0o4324"; "0o324" -- "0o5324"
        }
        subgraph cluster_legend {
            bgcolor="#242424"
            color="#24242400"
            "Legend" [
                color="#FEF9A9"
                shape=plain
                margin=0
                label=<
                        <TABLE CELLBORDER="0" CELLSPACING="8">
                            <TR>
                                <TD BORDER="1" SIDES="B" COLSPAN="3">Legend</TD>
                            </TR>
                            <TR>
                                <TD>Network Level 0</TD>
                                <TD BORDER="1" STYLE="rounded,radial" BGCOLOR="#000:#018268">        </TD>
                            </TR>
                            <TR>
                                <TD>Network Level 1</TD>
                                <TD BORDER="1" STYLE="rounded" BGCOLOR="#3E0180">        </TD>
                            </TR>
                            <TR>
                                <TD>Network Level 2</TD>
                                <TD BORDER="1" STYLE="rounded" BGCOLOR="#014B80">        </TD>
                            </TR>
                            <TR>
                                <TD>Network Level 3</TD>
                                <TD BORDER="1" STYLE="rounded" BGCOLOR="#0E6902">        </TD>
                            </TR>
                            <TR>
                                <TD>Network Level 4</TD>
                                <TD BORDER="1" STYLE="rounded" BGCOLOR="#80010B">        </TD>
                            </TR>
                            <TR>
                                <TD BORDER="1" SIDES="T" COLSPAN="3">Nodes are labeled<BR/>in octal numbers</TD>
                            </TR>
                        </TABLE>
                >
            ]
        }
    }

Hopefully, you should see the pattern. There can be up to a maximum of 5 network levels (that's
0-4 ordered from lowest to highest).

A single network can potentially have a maximum of 781 nodes (all operating on the same
:attr:`~circuitpython_nrf24l01.rf24.RF24.channel`), but for readability reasons, the following
graph only demonstrates

- the master node (level 0) and it's 5 children (level 1)
- level 2 only shows the 1\ :sup:`st` and 2\ :sup:`nd` children of parents on level 1
- level 3 only shows the 3\ :sup:`rd` and 4\ :sup:`th` children of parents on level 2
- level 4 only shows the 5\ :sup:`th` children of parents on level 3


.. graphviz::

    graph network_levels {
        layout=twopi
        bgcolor="#323232A1"
        ratio="0.825"
        node [
            style=filled
            fontcolor="#FEFEFE"
            color="#FEFEFE7f"
            fontsize=14
            fontname=Arial
        ]
        edge [color="#FEFEFE" style="setlinewidth(2)"]
        ranksep="0.85:0.9:0.95:1.1"
        subgraph lvl_0 {
            "0o0" [
                root=true
                shape="circle"
                style="radial"
                fillcolor="0.9:#018268;0:#000"
            ]
        }
        subgraph lvl_1 {
            node [fillcolor="#3E0180"]
            "0o1" "0o2" "0o3" "0o4" "0o5"
        }
        subgraph lvl_2 {
            node [fillcolor="#014B80"]
            "0o11" "0o21" "0o12" "0o22" "0o13" "0o23" "0o14" "0o24" "0o15" "0o25"
        }
        subgraph lvl_3 {
            node [fillcolor="#0E6902"]
            "0o311" "0o411" "0o321" "0o421" "0o312" "0o412" "0o322" "0o422" "0o313" "0o413"
            "0o323" "0o423" "0o314" "0o414" "0o324" "0o424" "0o315" "0o415" "0o325" "0o425"
        }
        subgraph lvl_4 {
            node [fillcolor="#80010B"]
            "0o5311" "0o5411" "0o5321" "0o5312" "0o5421" "0o5313" "0o5314" "0o5315" "0o5322"
            "0o5323" "0o5324" "0o5325" "0o5412" "0o5423" "0o5422" "0o5413" "0o5414" "0o5424"
            "0o5415" "0o5425"
        }
        "0o0" -- "0o1" -- "0o11" -- "0o311" -- "0o5311"
        "0o0" -- "0o2" -- "0o12" -- "0o312" -- "0o5312"
        "0o0" -- "0o3" -- "0o13" -- "0o313" -- "0o5313"
        "0o0" -- "0o4" -- "0o14" -- "0o314" -- "0o5314"
        "0o0" -- "0o5" -- "0o15" -- "0o315" -- "0o5315"
        "0o1" -- "0o21" -- "0o321" -- "0o5321"
        "0o2" -- "0o22" -- "0o322" -- "0o5322"
        "0o3" -- "0o23" -- "0o323" -- "0o5323"
        "0o4" -- "0o24" -- "0o324" -- "0o5324"
        "0o5" -- "0o25" -- "0o325" -- "0o5325"
        "0o11" -- "0o411" -- "0o5411"
        "0o21" -- "0o421" -- "0o5421"
        "0o12" -- "0o412" -- "0o5412"
        "0o22" -- "0o422" -- "0o5422"
        "0o13" -- "0o413" -- "0o5413"
        "0o23" -- "0o423" -- "0o5423"
        "0o14" -- "0o414" -- "0o5414"
        "0o24" -- "0o424" -- "0o5424"
        "0o15" -- "0o415" -- "0o5415"
        "0o25" -- "0o425" -- "0o5425"
    }

.. _Physical Address:
.. _Logical Address:

Physical addresses vs Logical addresses
***************************************

- The Physical address is the 5-byte address assigned to the radio's data pipes.
- The Logical address is the 12-bit integer representing a network node.
  The Logical address uses an octal counting scheme. A valid Logical Address must only
  contain octal digits in range [1, 5]. The master node is the exception for it uses the
  number ``0``

  .. tip::
      Use the `is_address_valid()` function to programatically check a Logical Address for validity.

.. note::
    Remember that the nRF24L01 only has 6 data pipes for which to receive or transmit.
    Since only data pipe 0 can be used to transmit, the other other data pipes 1-5 are
    devoted to receiving transmissions from children.

Translating Logical to Physical
-------------------------------

Before translating the Logical address, a single byte is used reptitively as the
base case for all bytes of any Physical Address. This byte is the `address_prefix`
attribute (stored as a mutable `bytearray`) in the `RF24Network` class. By default the
`address_prefix` has a single byte value of ``b"0xCC"``.

The `RF24Network` class also has a predefined list of bytes used for translating
unique Logical addresses into unique Physical addresses. This list is called
`address_suffix` (also stored as a mutable `bytearray`). By default the `address_suffix`
has 6-byte value of ``b"\xC3\x3C\x33\xCE\x3E\xE3"`` where the order of bytes pertains to the
data pipe number and child node's most significant byte in its Physical Address.

For example:
    The Logical Address of the network's master node is ``0``. The radio's pipes
    1-5 start with the `address_prefix`. To make each pipe's Phsyical address unique
    to a child node's Physical address, the `address_suffix` is used.

    The Logical address of the master node: ``0o0``

    .. csv-table::
        :header: "pipe", "Phsyical Address (hexadecimal)"
        :width: 10
        :widths: 1, 9

        1, ``CC CC CC CC 3C``
        2, ``CC CC CC CC 33``
        3, ``CC CC CC CC CE``
        4, ``CC CC CC CC 3E``
        5, ``CC CC CC CC E3``

    The Logical address of the master node's first child: ``0o1``

    .. csv-table::
        :header: "pipe", "Phsyical Address (hexadecimal)"
        :width: 10
        :widths: 1, 9

        1, ``CC CC CC 3C 3C``
        2, ``CC CC CC 3C 33``
        3, ``CC CC CC 3C CE``
        4, ``CC CC CC 3C 3E``
        5, ``CC CC CC 3C E3``

    The Logical address of the master node's second child: ``0o2``

    .. csv-table::
        :header: "pipe", "Phsyical Address (hexadecimal)"
        :width: 10
        :widths: 1, 9

        1, ``CC CC CC 33 3C``
        2, ``CC CC CC 33 33``
        3, ``CC CC CC 33 CE``
        4, ``CC CC CC 33 3E``
        5, ``CC CC CC 33 E3``

    The Logical address of the master node's third child's second child's first child: ``0o123``

    .. csv-table::
        :header: "pipe", "Phsyical Address (hexadecimal)"
        :width: 10
        :widths: 1, 9

        1, ``CC 3C 33 CE 3C``
        2, ``CC 3C 33 CE 33``
        3, ``CC 3C 33 CE CE``
        4, ``CC 3C 33 CE 3E``
        5, ``CC 3C 33 CE E3``
