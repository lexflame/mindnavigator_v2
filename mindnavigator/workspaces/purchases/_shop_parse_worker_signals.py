"""_ShopParseWorkerSignals class module for purchases workspace."""

from __future__ import annotations
from PySide6.QtCore import Signal, QObject

class _ShopParseWorkerSignals(QObject):
    progress = Signal(int, int)
    message = Signal(str)
    finished = Signal()

__all__ = ["_ShopParseWorkerSignals"]
