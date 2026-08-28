"""Pytest bootstrap.

Ensures the repository root is on ``sys.path`` so that the top-level
``search`` namespace package (which intentionally has no ``__init__.py``)
and its subpackages can be imported by tests regardless of pytest's import
mode. Markdown/JSON in ``materials/`` and ``index/`` remain the source of
truth; this file only affects the Python test runner.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
