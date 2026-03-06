"""Compatibility alias for legacy settings workspace module path."""

from importlib import import_module as _import_module
import sys as _sys

_sys.modules[__name__] = _import_module(".settings.workspace", __package__)
