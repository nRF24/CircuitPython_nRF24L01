# pylint: disable=invalid-name,too-few-public-methods
"""This file is for `sphinx-build` configuration"""
import os
import sys


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
    "sphinx.ext.graphviz",
    "sphinx_immaterial"
    # "rst2pdf.pdfbuilder",  # for local pdf builder support
]

# Uncomment the below if you use native CircuitPython modules such as
# digitalio, micropython and busio. List the modules you use. Without it, the
# autodoc module docs will fail to generate with a warning.
autodoc_mock_imports = ["digitalio", "busio", "usb_hid", "microcontroller", "logging"]
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "CircuitPython": ("https://circuitpython.readthedocs.io/en/latest/", None),
    "Adafruit_logging": (
        "https://circuitpython.readthedocs.io/projects/logging/en/latest/",
        None,
    ),
}

html_baseurl = "https://circuitpython-nrf24l01.readthedocs.io/"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
# pylint: disable=redefined-builtin
copyright = "2019 Brendan Doherty"
# pylint: enable=redefined-builtin
project = "nRF24L01 Library"
author = "Brendan Doherty"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = "2.1.0"
# The full version, including alpha/beta/rc tags.
release = "2.1.0"

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

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# If this is True, todo emits a warning for each TODO entries. The default is False.
todo_emit_warnings = False

napoleon_numpy_docstring = False

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
    "repo_url": "https://github.com/nRF24/CircuitPython_nRF24L01/",
    "repo_name": "CircuitPython_nRF24L01",
    "repo_type": "github",
    # Visible levels of the global TOC; -1 means unlimited
    "globaltoc_depth": -1,
    # If False, expand all TOC entries
    "globaltoc_collapse": False,
    # If True, show hidden TOC entries
    "globaltoc_includehidden": True,
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
    "dark_material.css",
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
# html_copy_source = True
# html_show_sourcelink = True

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    #
    # The paper size ('letterpaper' or 'a4paper').
    'papersize': 'letterpaper',
    #
    # The font size ('10pt', '11pt' or '12pt').
    'pointsize': '10pt',
    #
    # Additional stuff for the LaTeX preamble.
    'preamble': '',
    #
    # Latex figure (float) alignment
    'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        "nRF24L01Library.tex",
        "nRF24L01 Library Documentation",
        author,
        "manual",
    ),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, "nRF24L01library", "nRF24L01 Library Documentation", [author], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "nRF24L01Library",
        " nRF24L01 Library Documentation",
        author,
        "nRF24L01Library",
        "nRF24L01 on CircuitPython devices.",
        "Wireless",
    ),
]

# ---Options for PDF output-----------------------------------------
# requires `rst2pdf` module which is not builtin to Python 3.4 nor
# readthedocs.org's docker)

# pdf_documents = [
#     (
#         "index",
#         u"CircuitPython-nRF24L01",
#         u"CircuitPython-nRF24L01 library documentation",
#         u"Brendan Doherty",
#     ),
# ]
