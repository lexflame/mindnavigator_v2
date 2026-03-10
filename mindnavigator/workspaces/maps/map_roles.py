"""MapRoles class module for maps workspace."""

from __future__ import annotations

from PySide6.QtCore import Qt

class MapRoles:
    Id = Qt.ItemDataRole.UserRole + 1
    Title = Qt.ItemDataRole.UserRole + 2
    Description = Qt.ItemDataRole.UserRole + 3
    Project = Qt.ItemDataRole.UserRole + 4
    TilesPath = Qt.ItemDataRole.UserRole + 5
    TilesHeight = Qt.ItemDataRole.UserRole + 6
    TilesWidth = Qt.ItemDataRole.UserRole + 7

__all__ = ["MapRoles"]
