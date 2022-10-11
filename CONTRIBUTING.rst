
Contributing Guidelines
=======================

Building the Documentation
--------------------------

To build library documentation, you need to install Graphviz and the documentation dependencies.

.. code-block:: shell

    pip install -r docs/requirements.txt

.. note::
    Installing graphviz differs depending on your platform.

    Linux users can simply,

    .. code-block:: shell

        sudo apt-get install graphviz

    Windows users will have to install the binaries from
    `the official Graphviz downloads <https://graphviz.org/download/#windows>`_. Just be sure that
    the installed ``bin`` folder is added to your environment's PATH variable.

Finally, build the documentation with Sphinx:

.. code-block:: shell

    sphinx-build -E -W docs docs/_build/html

The rendered HTML files should now be located in the ``docs/_build/html`` folder. Point your
internet browser to this path and check the changes have been rendered properly.

Linting the source code
-----------------------

.. _pre-commit: https://pre-commit.com/

This library uses pre-commit_ for some linting tools like

- `black <https://black.readthedocs.io/en/stable/>`_
- `pylint <https://pylint.pycqa.org/en/stable/>`_
- `mypy <https://mypy.readthedocs.io/en/stable/>`_

To use pre-commit_, you must install it and create the cached environments that it needs.

.. code-block:: shell

    pip install pre-commit
    pre-commit install

Now, every time you commit something it will run pre-commit_ on the changed files. You can also
run pre-commit_ on staged files:

.. code-block:: shell

    pre-commit run

Testing the source code
-----------------------

.. _pytest: https://docs.pytest.org/en/latest/
.. _coverage: https://coverage.readthedocs.io/en/latest/

Code coverage/testing is done with pytest_ and coverage_ libraries. Install these tools (and
this library's dependencies) with:

.. code-block:: shell

    pip install -r test/requirements.txt -r requirements.txt

Run the tests and collect the code coverage with:

.. code-block:: shell

    coverage run -m pytest
