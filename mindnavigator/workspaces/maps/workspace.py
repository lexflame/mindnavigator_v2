"""Workspace module alias for maps workspace implementation."""

import sys as _sys

from . import module_impl as _module_impl

_sys.modules[__name__] = _module_impl
