.. |internal_use| replace:: is meant for library internal usage.
.. |uint16_t| replace:: This value is truncated to a 2-byte unsigned `int`.
.. |can_be_blank| replace:: These parameters can be left unspecified to create a blank
    object that can be augmented after instantiation.
.. |unpacked_buf| replace:: The buffer to unpack. All resulting data is stored in the
    objects attributes accordingly.

Network Data Structures
=======================

.. automodule:: circuitpython_nrf24l01.network.structs

.. versionadded:: 2.1.0

Header
-----------------

.. autoclass:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader

    :param to_node: The :ref:`Logical Address <logical address>` designating the
        message's destination.
    :param message_type: A 1-byte `int` representing the `message_type`. If a
        `str` is passed, then the first character's numeric ASCII representation is
        used.

    .. note:: |can_be_blank|

.. autoattribute:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader.to_node

    Describes the message destination using a :ref:`Logical Address <logical address>`.

.. autoattribute:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader.from_node

    Describes the message origin using a :ref:`Logical Address <logical address>`.

.. autoattribute:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader.message_type

    This `int` must be less than 256. When set using a `str`, this attribute's `int` value is
    derived from the ASCII number of the string's first character (see :py:func:`ord()`).
    Non-ASCII characters' values are truncated to 1 byte (see :py:meth:`str.isascii()`). A blank
    `str` sets this attribute's value to ``0``.

    .. hint::
        Users are encouraged to specify a number in range [0, 127] (basically less
        than or equal to `MAX_USR_DEF_MSG_TYPE`) as there are
        `Reserved Message Types <constants.html#reserved-network-message-types>`_.

.. autoattribute:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader.frame_id

    The sequential identifying number for the frame (relative to the originating
    network node). Each sequential frame's ID is incremented, but frames containing
    fragmented messages have the same ID number.

.. autoattribute:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader.reserved

    This will be the sequential ID number for fragmented messages, but on the last message
    fragment, this will be the `message_type`. `RF24Mesh` will also use this attribute to
    hold a newly assigned network :ref:`Logical Address <logical address>` for
    `MESH_ADDR_RESPONSE` messages.

.. automethod:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader.unpack

    This function |internal_use|

    :param buffer: |unpacked_buf|
    :Returns: `True` if successful; otherwise `False`.

.. automethod:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader.pack

    :Returns: The entire header as a `bytes` object.

.. automethod:: circuitpython_nrf24l01.network.structs.RF24NetworkHeader.to_string

Frame
-----------------

.. autoclass:: circuitpython_nrf24l01.network.structs.RF24NetworkFrame

    This is used for either a single fragment of an individually large message (greater than 24
    bytes) or a single message that is less than 25 bytes.

    :param header: The header describing the frame's `message`.
    :param message: The actual `message` containing the payload
        or a fragment of a payload.

    .. note:: |can_be_blank|

.. autoattribute:: circuitpython_nrf24l01.network.structs.RF24NetworkFrame.header
.. autoattribute:: circuitpython_nrf24l01.network.structs.RF24NetworkFrame.message

    This attribute is typically a `bytearray` or `bytes` object.

.. automethod:: circuitpython_nrf24l01.network.structs.RF24NetworkFrame.unpack

    This function |internal_use|

    :param buffer: |unpacked_buf|
    :Returns: `True` if successful; otherwise `False`.

.. automethod:: circuitpython_nrf24l01.network.structs.RF24NetworkFrame.pack

    :Returns:  The entire object as a `bytes` object.

.. automethod:: circuitpython_nrf24l01.network.structs.RF24NetworkFrame.is_ack_type

    This function  |internal_use|

FrameQueue
-----------------

.. autoclass:: circuitpython_nrf24l01.network.structs.FrameQueue

    :param queue: To move (not copy) the contents of another
        `FrameQueue` based object, you can pass the object to this parameter. Doing so
        will also copy the object's `max_queue_size` attribute.

.. autoattribute:: circuitpython_nrf24l01.network.structs.FrameQueue.max_queue_size
.. automethod:: circuitpython_nrf24l01.network.structs.FrameQueue.enqueue

    :Returns: `True` if the frame was added to the queue, or `False` if it was not.

.. automethod:: circuitpython_nrf24l01.network.structs.FrameQueue.dequeue
.. automethod:: circuitpython_nrf24l01.network.structs.FrameQueue.peek
.. automethod:: circuitpython_nrf24l01.network.structs.FrameQueue.__len__

    For use with Python's builtin :func:`len()`.

FrameQueueFrag
-----------------

.. autoclass:: circuitpython_nrf24l01.network.structs.FrameQueueFrag
    :show-inheritance:

    .. note:: This class will only cache 1 fragmented message at a time. If parts of
        the fragmented message are missing (or duplicate fragments are received), then
        the fragment is discarded. If a new fragmented message is received (before a
        previous fragmented message is completed and reassembled), then the cache
        is reused for the new fragmented message to avoid memory leaks.

Logical Address Validation
--------------------------

.. autofunction:: circuitpython_nrf24l01.network.structs.is_address_valid

    :param address: The :ref:`Logical Address <Logical Address>` to validate.

    :Returns:
        `True` if the given address can be used as a `node_address` or `to_node`
        destination. Otherwise, this function returns `False`.

        .. warning::
            Please note that this function also allows the value :python:`0o100` to validate
            because it is used as the `NETWORK_MULTICAST_ADDR` for multicasted messages.
            Technically, :python:`0o100` is an invalid address.
