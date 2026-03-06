"""Workspace module alias for purchases workspace implementation."""

from importlib import import_module as _import_module
import sys as _sys

_sys.modules[__name__] = _import_module(".module_impl", __package__)
