# Configuration file for the Sphinx documentation builder.
#
# This project's API docs are generated entirely from docstrings attached to
# the compiled physicellpy extension module (the third argument to each
# pybind11 .def(...) call in physicell_bindings.cpp / microenvironment_bindings.cpp
# / physimess_bindings.cpp). sphinx.ext.autodoc introspects those __doc__
# strings the same way it would for a pure-Python module -- no separate stub
# generation step is needed -- but that means `import physicellpy` must
# actually succeed at doc-build time. On ReadTheDocs, .readthedocs.yaml's
# `python: install: - method: pip path: .` builds and installs the real C++
# extension (via this project's scikit-build-core + CMake build) into the
# docs venv before Sphinx runs.

project = "physicellpy"
copyright = "2026, Randy Heiland"
author = "Randy Heiland"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

# pybind11 classes/functions don't carry the source-line metadata autodoc's
# "bysource" ordering relies on -- alphabetical (the default) is what you
# actually get for a compiled extension either way.
autodoc_member_order = "alphabetical"

exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
