Network Topology
================

Network Levels
****************

Each network is arranged in a tree where the master node (designated with the
:ref:`Logical Address <logical address>` ``0o0``) is always the top of the tree.

All network nodes in the following graphs are labeled with :ref:`Logical Addresses <logical address>`.

.. graphviz::
    :caption: Network Level 0 - the highest level - (demonstrating all possible children)

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
        "0o21" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o31" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o41" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o51" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o12" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o22" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o32" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o42" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o52" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o1" -> "0o11"  [arrowhead=none color="#FEFEFE"];
        "0o1" -> "0o21"  [arrowhead=none color="#FEFEFE"];
        "0o1" -> "0o31"  [arrowhead=none color="#FEFEFE"];
        "0o1" -> "0o41"  [arrowhead=none color="#FEFEFE"];
        "0o1" -> "0o51"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o12"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o22"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o32"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o42"  [arrowhead=none color="#FEFEFE"];
        "0o2" -> "0o52"  [arrowhead=none color="#FEFEFE"];
    }

.. graphviz::
    :caption: Network Level 2 (demonstrating only 2 child nodes as parents)

    digraph "NetworkTopology2" {
        bgcolor="#39393988";
        "0o21" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o31" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o121" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o221" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o321" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o421" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o521" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o131" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o231" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o331" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o431" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o531" [fontcolor="#FEFEFE" color="#FEFEFE"];
        "0o21" -> "0o121"  [arrowhead=none color="#FEFEFE"];
        "0o21" -> "0o221"  [arrowhead=none color="#FEFEFE"];
        "0o21" -> "0o321"  [arrowhead=none color="#FEFEFE"];
        "0o21" -> "0o421"  [arrowhead=none color="#FEFEFE"];
        "0o21" -> "0o521"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o131"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o231"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o331"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o431"  [arrowhead=none color="#FEFEFE"];
        "0o31" -> "0o531"  [arrowhead=none color="#FEFEFE"];
    }

Hopefully, you can see the pattern by now. There can be up to a maximum of 4 network levels (that's
0-3 ordered from highest to lowest).

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

Translating Logical to Physical
-------------------------------

Before translating the Logical address, a single byte is used reptitively as the
base case for all bytes of any Physical Address. This byte is the `address_prefix`
attribute in the `RF24Network` class.

The `RF24Network` class also has a predefined list of bytes used for translating
unique Logical addresses into unique Physical addresses. This list is called
`address_suffix`.

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
        3, ``CC CC CC 3C Ce``
        4, ``CC CC CC 3C 3E``
        5, ``CC CC CC 3C E3``

    The Logical address of the master node's second child: ``0o2``

    .. csv-table::
        :header: "pipe", "Phsyical Address (hexadecimal)"
        :width: 10
        :widths: 1, 9

        1, ``CC CC CC 33 3C``
        2, ``CC CC CC 33 33``
        3, ``CC CC CC 33 Ce``
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
