"""This file is for `sphinx-build` configuration"""
from importlib.metadata import version as get_version
import os
import sys
import time

sys.path.insert(0, os.path.abspath(".."))

# -- General configuration ------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_immaterial",
    "sphinx_immaterial.graphviz",
    "sphinx_immaterial.kbd_keys",
    "sphinx_social_cards",
]

# Uncomment the below if you use native CircuitPython modules such as
# digitalio, micropython and busio. List the modules you use. Without it, the
# autodoc module docs will fail to generate with a warning.
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "CircuitPython": ("https://circuitpython.readthedocs.io/en/latest/", None),
}

# ignore theme warning on windows about graphviz font metrics
graphviz_ignore_incorrect_font_metrics = True

html_baseurl = os.environ.get(
    "READTHEDOCS_CANONICAL_URL", "https://nrf24.github.io/CircuitPython_nRF24L01/"
)

# General information about the project.
project = "CircuitPython nRF24L01"
author = "Brendan Doherty"
# pylint: disable=redefined-builtin
copyright = f'{time.strftime("%Y", time.localtime())} {author}'
# pylint: enable=redefined-builtin

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
release = get_version("circuitpython-nrf24l01")
# The short X.Y version.
version = ".".join([str(x) for x in release.split(".")[:3]])

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    ".env",
    "CODE_OF_CONDUCT.md",
    "requirements.txt",
]

# The reST default role (used for this markup: `text`) to use for all
# documents.
default_role = "any"

rst_prolog = """
.. role:: python(code)
   :language: python
   :class: highlight
.. role:: cpp(code)
   :language: cpp
   :class: highlight
"""


# -- Options for sphinx_social_cards -------------------------------------------------
social_cards = {
    "site_url": html_baseurl,
    "description": (
        "A pure python driver library for the nRF24L01 transceivers on CircuitPython "
        "platforms."
    ),
    "image_paths": ["social_cards/images"],
    "cards_layout_dir": ["social_cards/layouts"],
    "cards_layout": "custom",
    "cards_layout_options": {
        "logo": {
            "image": "material/access-point",
            "color": "lime",
        },
        "background_color": "#2c2c2c",
        "background_image": "logo_large_no-bg.png",
        "color": "lime",
    },
    # "debug": {
    #     "enable": True,
    #     "color": "lime",
    # },
}

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_immaterial"
# Material theme options

html_theme_options = {
    "features": [
        # "navigation.expand",
        "navigation.tabs",
        # "toc.integrate",
        "navigation.sections",
        "navigation.instant",
        # "header.autohide",
        "navigation.top",
        # "search.highlight",
        "search.share",
        "navigation.tabs.sticky",
    ],
    "icon": {
        "repo": "fontawesome/brands/github",
    },
    "social": [
        {
            "icon": "fontawesome/brands/github",
            "link": "https://github.com/nRF24/CircuitPython_nRF24L01",
        },
        {
            "icon": "fontawesome/brands/python",
            "link": "https://pypi.org/project/circuitpython-nrf24l01/",
        },
        {
            "icon": "fontawesome/brands/discord",
            "link": "https://adafru.it/discord",
        },
        {
            "icon": "simple/adafruit",
            "link": "https://www.adafruit.com/",
        },
        {
            "icon": "simple/sparkfun",
            "link": "https://www.sparkfun.com/",
        },
        {
            "name": "CircuitPython Downloads",
            "icon": "octicons/download-24",
            "link": "https://circuitpython.org",
        },
    ],
    "palette": [
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "lime",
            "accent": "light-blue",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to light mode",
            },
        },
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "light-blue",
            "accent": "green",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to dark mode",
            },
        },
    ],
    # Set the repo location to get a badge with stats
    "site_url": html_baseurl,
    "repo_url": "https://github.com/nRF24/CircuitPython_nRF24L01/",
    "repo_name": "CircuitPython_nRF24L01",
    # If False, expand all TOC entries
    "globaltoc_collapse": False,
    "toc_title_is_page_title": True,
}

# turn off some features specific to sphinx-immaterial theme
object_description_options = [
    ("py:.*", dict(include_fields_in_toc=False, generate_synopses=None)),
    ("py:parameter", dict(include_in_toc=False)),
]

sphinx_immaterial_custom_admonitions = [
    {
        "name": "warning",
        "color": (255, 66, 66),
        "icon": "octicons/alert-24",
        "override": True,
    },
    {
        "name": "note",
        "icon": "octicons/pencil-24",
        "override": True,
    },
    {
        "name": "seealso",
        "color": (255, 66, 252),
        "icon": "octicons/eye-24",
        "title": "See Also",
        "override": True,
    },
    {
        "name": "hint",
        "icon": "material/school",
        "override": True,
    },
    {
        "name": "tip",
        "icon": "material/school",
        "override": True,
    },
    {
        "name": "important",
        "icon": "material/alert-decagram",
        "override": True,
    },
]

# python_strip_property_prefix = True
python_type_aliases = {
    "typing.Callable": "Callable",
}

# Set link name generated in the top bar.
html_title = "CircuitPython_nRF24L01"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = [
    "custom_material.css",
]

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#
html_favicon = "_static/new_favicon.ico"

# project logo
html_logo = "_static/Logo large.png"

# Output file base name for HTML help builder.
htmlhelp_basename = "nRF24L01_Library_doc"
