# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Generate modules:
#  sphinx-apidoc -o ./src/modules/ ../src/ska_mid_dish_manager/

import os
import sys

# WORKAROUND: https://github.com/sphinx-doc/sphinx/issues/9243
import sphinx.builders.html
import sphinx.builders.latex
import sphinx.builders.texinfo
import sphinx.builders.text
import sphinx.ext.autodoc

# This is an elaborate hack to insert write property into _all_
# mock decorators. It is needed for getting @attribute to build
# in mocked out tango.server
# see https://github.com/sphinx-doc/sphinx/issues/6709
from sphinx.ext.autodoc.mock import _MockObject


def call_mock(self, *args, **kw):
    from types import FunctionType, MethodType

    if args and type(args[0]) in [type, FunctionType, MethodType]:
        # Appears to be a decorator, pass through unchanged
        args[0].write = lambda x: x
        return args[0]
    return self


_MockObject.__call__ = call_mock
# hack end

# lines 13-37 copied from ska-low-mccs conf.py

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath("../../src"))

# adapted from ska-low-mccs conf.py
# pylint: disable=invalid-name
autodoc_mock_imports = [
    "numpy",
    "astropy",
    "transitions",
    "networkx",
    "ska_control_model",
    "ska_tango_base",
    "tango",
    "rule_engine",
]

autodoc_default_options = {
    "members": True,
    "special-members": "__init__",
}


# -- Project information -----------------------------------------------------

project = "SKA Mid Dish Manager"
copyright = "2024, KAROO Team"
author = "KAROO Team"

# The full version, including alpha/beta/rc tags
release = "7.1.0"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.todo",
    "sphinx_tabs.tabs",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.plantuml",
    "sphinx_copybutton",
]
autoclass_content = "class"
plantuml_syntax_error_image = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = [".rst"]

# The master toctree document.
master_doc = "index"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "ska_ser_sphinx_theme"

html_context = {}
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = []
