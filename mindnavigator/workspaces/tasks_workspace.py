"""Compatibility alias for legacy tasks workspace module path."""

from importlib import import_module as _import_module
import sys as _sys

_sys.modules[__name__] = _import_module(".tasks.workspace", __package__)
