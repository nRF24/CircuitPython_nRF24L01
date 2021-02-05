
Using logger(s)
================

Each `RF24` based object comes with compatibility with python's stanard
logging library. For CircuitPython, the :py:mod:`adafruit_logging` module must
exist in your CIRCUITPY drive's ``lib`` folder.

If the logging module is found:

1. The logging level is set to ``logging.INFO``
2. All library :py:func:`print()` calls will use the logger instantaited and
   accessed by the class's
   :attr:`~circuitpython_nrf24l01.rf24.RF24.logger` attribute.


logger
------

.. autoattribute:: circuitpython_nrf24l01.rf24.RF24.logger

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

      >>> from circuitpython_nrf24l01.fake_ble import FakeBLE
      >>> nrf = FakeBLE(None, None, None)  # Shim created; autmatically uses DEBUG
      >>> nrf.logger.setLevel(20)  # set back to default INFO
      >>> nrf.logger.info("Shims are useful with pytest")
      INFO:Fake_BLE:Shims are useful with pytest

Each RF24 class is layerd so that lgging mesages can be filtered out. In addition to the usual ``CRITICAL``, ``ERROR``, ``WARNING``,  & ``INFO`` levels, the following ``DEBUG`` values are supported by the corresponding object.

.. csv-table::
    :header: ``level``, Description
    :widths: 3, 12

    ``10``, "Basic module debug."
    ``11``, "general debug prompts specific to `RF24Network` or `FakeBLE`"
    ``12``, "minimal debug prompts specific to `RF24Network`"
    ``13``, "show fragmentation debug prompts specific to `RF24Network`"
    ``14``, "show level 2 of fragmentation debug prompts specific to `RF24Network`"

