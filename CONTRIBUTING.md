Before opening a Pull Request, be sure to the "master" branch,
1. Make sure all line endings in \*.py and \*.rst files use only LF (`\n`) and not CRLF (`\r\n`). Especially if you are working from windows.
2. If you made any documentation changes, you should verify, that they render properly as [instructed in the bottom of the documentation's landing page](https://circuitpython-nrf24l01.readthedocs.io/en/latest/#sphinx-documentation).

The "Build CI" github action workflow will also make sure the above stipulations have been adhered to.

It would also help to have a detailed description of the changes in the Pull Request if it is more than 1 or 2 lines of differences.
