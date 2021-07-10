Network Topology
================

Network Levels
****************

Each network is arranged in a tree where the master node (designated with the
Logical address ``0o0``) is always the top of the tree.

All network nodes in the following graphs are labeled with Logical addresses.

.. graphviz::
    :caption: Network Level 0 (demonstrating all possible children)

    digraph "NetworkTopology0" {
        bgcolor="#39393988"
        "0o0" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o1" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o2" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o3" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o4" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o5" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o0" -> "0o1"  [arrowhead=none color="#FEFEFE"];
        "0o0" -> "0o2"  [arrowhead=none color="#FEFEFE"];
        "0o0" -> "0o3"  [arrowhead=none color="#FEFEFE"];
        "0o0" -> "0o4"  [arrowhead=none color="#FEFEFE"];
        "0o0" -> "0o5"  [arrowhead=none color="#FEFEFE"];
    }

.. graphviz::
    :caption: Network Level 1 (demonstrating only 2 child nodes as parents)

    digraph "NetworkTopology1" {
        bgcolor="#39393988"
        "0o1" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o2" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o11" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o12" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o13" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o14" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o15" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o21" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o22" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o23" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o24" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o25" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o1" -> "0o11"  [arrowhead=none color="#FEFEFE"];
        "0o1" -> "0o12"  [arrowhead=none color="#FEFEFE"];
        "0o1" -> "0o13"  [arrowhead=none color="#FEFEFE"];
        "0o1" -> "0o14"  [arrowhead=none color="#FEFEFE"];
        "0o1" -> "0o15"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o21"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o22"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o23"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o24"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o25"  [arrowhead=none color="#FEFEFE"];
    }

.. graphviz::
    :caption: Network Level 2 (demonstrating only 2 child nodes as parents)

    digraph "NetworkTopology2" {
        bgcolor="#39393988";
        "0o21" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o31" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o211" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o212" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o213" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o214" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o215" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o311" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o312" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o313" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o314" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o315" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o21" -> "0o211"  [arrowhead=none color="#FEFEFE"];
        "0o21" -> "0o212"  [arrowhead=none color="#FEFEFE"];
        "0o21" -> "0o213"  [arrowhead=none color="#FEFEFE"];
        "0o21" -> "0o214"  [arrowhead=none color="#FEFEFE"];
        "0o21" -> "0o215"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o311"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o312"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o313"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o314"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o315"  [arrowhead=none color="#FEFEFE"];
    }

Hopefully, you can see the pattern by now. There can be up to a maximum of 4 network levels (that's 0-3).

Physical addresses vs Logical addresses
***************************************

- The Physical address is the 5-byte address assigned to the radio's data pipes.
- The Logical address is the 2-byte integer representing a network node.
  The Logical address uses an octal counting scheme.

Translating Logical to Physical
-------------------------------

Before translating the Logical address, a single byte is used reptitively as the
base case for all bytes of any Physical address. This byte is the `address_prefix`
attribute in the `RF24Network` class.

The `RF24Network` class also has a predefined list of bytes used for translating
unique Logical addresses into unique Physical addresses. This list is called
`address_suffix`.

For example:
    The logical address of the network's master node is ``0``. The radio's pipes
    1-5 start with the `address_prefix`. To make each pipe's Phsyical address unique
    to a child node's Physical address, the `address_suffix` is used.

    .. code-block:: text
        :caption: The Logical address of the master node: ``0o0``

        The resulting physical addresses of the master node's children:
        Physical address on pipe 1 is 0xCCCCCCCC3C using the parent's Logical address 0o0
        Physical address on pipe 2 is 0xCCCCCCCC33 using the parent's Logical address 0o0
        Physical address on pipe 3 is 0xCCCCCCCCCE using the parent's Logical address 0o0
        Physical address on pipe 4 is 0xCCCCCCCC3E using the parent's Logical address 0o0
        Physical address on pipe 5 is 0xCCCCCCCCE3 using the parent's Logical address 0o0

    .. code-block:: text
        :caption: The Logical address of the master node's first child: ``0o1``

        The resulting physical addresses of the master node's first child's children:
        Physical address on pipe 1 is 0xCCCCCC3C3C using the parent's Logical address 0o1
        Physical address on pipe 2 is 0xCCCCCC3C33 using the parent's Logical address 0o1
        Physical address on pipe 3 is 0xCCCCCC3CCe using the parent's Logical address 0o1
        Physical address on pipe 4 is 0xCCCCCC3C3E using the parent's Logical address 0o1
        Physical address on pipe 5 is 0xCCCCCC3CE3 using the parent's Logical address 0o1

    .. code-block:: text
        :caption: The Logical address of the master node's second child: ``0o2``

        The resulting physical addresses of the master node's second child's children:
        Physical address on pipe 1 is 0xCCCCCC333C using the parent's Logical address 0o2
        Physical address on pipe 2 is 0xCCCCCC3333 using the parent's Logical address 0o2
        Physical address on pipe 3 is 0xCCCCCC33Ce using the parent's Logical address 0o2
        Physical address on pipe 4 is 0xCCCCCC333E using the parent's Logical address 0o2
        Physical address on pipe 5 is 0xCCCCCC33E3 using the parent's Logical address 0o2

    .. code-block:: text
        :caption:  The Logical address of the master node's first child's first child: ``0o11``

        The resulting physical addresses of the master node's first child's first child's children:
        Physical address on pipe 1 is 0xCCCC3C3C3C using the parent's Logical address 0o11
        Physical address on pipe 2 is 0xCCCC3C3C33 using the parent's Logical address 0o11
        Physical address on pipe 3 is 0xCCCC3C3CCe using the parent's Logical address 0o11
        Physical address on pipe 4 is 0xCCCC3C3C3E using the parent's Logical address 0o11
        Physical address on pipe 5 is 0xCCCC3C3CE3 using the parent's Logical address 0o11
