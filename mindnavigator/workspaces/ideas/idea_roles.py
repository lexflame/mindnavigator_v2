"""IdeaRoles class module for ideas workspace."""

from __future__ import annotations
from PySide6.QtCore import Qt

class IdeaRoles:
    RowType = Qt.ItemDataRole.UserRole + 1
    IdeaId = Qt.ItemDataRole.UserRole + 2
    Title = Qt.ItemDataRole.UserRole + 3
    Summary = Qt.ItemDataRole.UserRole + 4
    Body = Qt.ItemDataRole.UserRole + 5
    Status = Qt.ItemDataRole.UserRole + 6
    Type = Qt.ItemDataRole.UserRole + 7
    ValueScore = Qt.ItemDataRole.UserRole + 8
    EffortScore = Qt.ItemDataRole.UserRole + 9
    ProjectTitle = Qt.ItemDataRole.UserRole + 10
    Archived = Qt.ItemDataRole.UserRole + 11

__all__ = ["IdeaRoles"]
