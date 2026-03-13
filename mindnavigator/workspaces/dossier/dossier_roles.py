"""Qt roles for the Dossier workspace list model."""

from __future__ import annotations

from PySide6.QtCore import Qt


class DossierRoles:
    DossierId = Qt.ItemDataRole.UserRole + 1
    Kind = Qt.ItemDataRole.UserRole + 2
    Title = Qt.ItemDataRole.UserRole + 3
    Summary = Qt.ItemDataRole.UserRole + 4
    Description = Qt.ItemDataRole.UserRole + 5
    Status = Qt.ItemDataRole.UserRole + 6
    Rating = Qt.ItemDataRole.UserRole + 7
    Source = Qt.ItemDataRole.UserRole + 8
    Tags = Qt.ItemDataRole.UserRole + 9
    Metadata = Qt.ItemDataRole.UserRole + 10
    UpdatedAt = Qt.ItemDataRole.UserRole + 11


__all__ = ["DossierRoles"]
