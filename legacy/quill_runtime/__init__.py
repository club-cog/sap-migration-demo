"""Quill runtime: a small Python interpreter that emulates the legacy RiskDB engine.

Exists only so the reference outputs in ``legacy/reference_outputs`` can be regenerated
for this demo. Not a production component.
"""

from .errors import QuillError
from .interpreter import Interpreter, format_value

__all__ = ["Interpreter", "QuillError", "format_value"]
