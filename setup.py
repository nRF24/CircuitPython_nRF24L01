"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
import os
import platform
from codecs import open as open_codec  # To use a consistent encoding
from setuptools import setup, find_packages


ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
REPO = "https://github.com/nRF24/CircuitPython_nRF24L01"
DEPS = ["adafruit-blinka", "adafruit-circuitpython-busdevice", "typing-extensions"]
sys_desc = platform.uname()
if sys_desc[0].title() == "Linux" and sys_desc[4].lower().startswith("arm"):
    DEPS.append("spidev")

# Get the long description from the README file
with open_codec(os.path.join(ROOT_DIR, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="circuitpython-nrf24l01",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    python_requires=">=3.7",
    description="Circuitpython driver library for the nRF24L01 transceiver",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Brendan Doherty",
    author_email="2bndy5@gmail.com",
    install_requires=DEPS,
    license="MIT",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="adafruit blinka circuitpython nrf24l01 nRF24L01+"
    " raspberry pi driver radio transceiver",
    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    # TODO: IF LIBRARY FILES ARE A PACKAGE FOLDER,
    #       CHANGE `py_modules=['...']` TO `packages=['...']`
    packages=find_packages(),
    # Specify your homepage URL for your project here
    url=REPO,
    # Extra links for the sidebar on pypi
    project_urls={
        "Documentation": "http://circuitpython-nrf24l01.rtfd.io",
    },
    download_url="{}/releases".format(REPO),
)
