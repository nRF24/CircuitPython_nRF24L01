
Using logger(s)
================

The `RF24Network` object comes with compatibility with python's standard
logging library. For CircuitPython, the :py:mod:`adafruit_logging` module must
exist in your CIRCUITPY drive's ``lib`` folder.

If the logging module is found:

1. The logging level is set to ``logging.INFO``
2. All internal calls to :py:func:`print()` will use the logger instantaited and
   accessed by the class's `logger` attribute.


logger
------

.. autoattribute:: circuitpython_nrf24l01.network.rf24_network.RF24Network.logger

    Internally, only this object's ``log()`` & ``setLevel()`` methods are used.

    .. seealso::
        Review the `logging standard library <https://docs.python.org/3/library/logging.html>`_.

        For CircuitPython firmware, review `Adafruit's learning guide about adding handlers <https://learn.adafruit.com/a-logger-for-circuitpython/adding-handlers>`_.

logging_levels
--------------

Internally the :attr:`~circuitpython_nrf24l01.rf24.RF24.logger` uses
different levels of logging. The default is ``INFO``.

- If the ``spi``, ``ce``, & ``csn`` are all passed as `None` type
  objects, then the ``DEBUG`` level is default.

  .. code-block:: python

      >>> from circuitpython_nrf24l01.network.rf24_network import RF24Network
      >>> nrf = RF24Network(None, None, None)  # Shim created; autmatically uses DEBUG
      >>> nrf.logger.setLevel(20)  # set back to default INFO
      >>> nrf.logger.info("Shims are useful with pytest")
      INFO:RF24Network:Shims are useful with pytest

Logging mesages can be filtered using logging levels. In addition to the usual ``CRITICAL``, ``ERROR``, ``WARNING``,  & ``INFO`` levels, the following ``DEBUG`` values are supported by the corresponding object.

.. csv-table::
    :header: ``level``, Description
    :widths: 3, 12

    ``11``, "general debug prompts specific to `RF24Network`"
    ``12``, "minimal debug prompts specific to `RF24Network`"
    ``13``, "show fragmentation debug prompts specific to `RF24Network`"
    ``14``, "show advanced fragmentation debug prompts specific to `RF24Network`"
