"""NoteRoles class module for notes workspace."""

from __future__ import annotations
from PySide6.QtCore import Qt

class NoteRoles:
    RowType = Qt.ItemDataRole.UserRole + 1
    NoteId = Qt.ItemDataRole.UserRole + 2
    Title = Qt.ItemDataRole.UserRole + 3
    Preview = Qt.ItemDataRole.UserRole + 4
    Tags = Qt.ItemDataRole.UserRole + 5
    Updated = Qt.ItemDataRole.UserRole + 6
    Project = Qt.ItemDataRole.UserRole + 7
    Favorite = Qt.ItemDataRole.UserRole + 8
    Attachment = Qt.ItemDataRole.UserRole + 9
    Locked = Qt.ItemDataRole.UserRole + 10

__all__ = ["NoteRoles"]
