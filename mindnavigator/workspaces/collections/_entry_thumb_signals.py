"""_EntryThumbSignals class module for collections workspace."""

from __future__ import annotations
from PySide6.QtCore import QObject, Signal

class _EntryThumbSignals(QObject):
    ready = Signal(int, str)

__all__ = ["_EntryThumbSignals"]
