"""ObjectRoles class module for objects workspace."""

from __future__ import annotations
from PySide6.QtCore import Qt

class ObjectRoles:
    RowType = Qt.ItemDataRole.UserRole + 1
    Id = Qt.ItemDataRole.UserRole + 2
    Title = Qt.ItemDataRole.UserRole + 3
    Catalog = Qt.ItemDataRole.UserRole + 4
    ObjectType = Qt.ItemDataRole.UserRole + 5
    Status = Qt.ItemDataRole.UserRole + 6
    Description = Qt.ItemDataRole.UserRole + 7

__all__ = ["ObjectRoles"]
