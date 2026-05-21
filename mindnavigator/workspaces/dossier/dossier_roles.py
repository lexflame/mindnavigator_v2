"""Qt roles for the Dossier workspace list model."""

from __future__ import annotations

from PySide6.QtCore import Qt


class DossierRoles:
    RowType = Qt.ItemDataRole.UserRole + 1
    DossierId = Qt.ItemDataRole.UserRole + 2
    Kind = Qt.ItemDataRole.UserRole + 3
    Title = Qt.ItemDataRole.UserRole + 4
    Summary = Qt.ItemDataRole.UserRole + 5
    Description = Qt.ItemDataRole.UserRole + 6
    Status = Qt.ItemDataRole.UserRole + 7
    Rating = Qt.ItemDataRole.UserRole + 8
    Source = Qt.ItemDataRole.UserRole + 9
    Tags = Qt.ItemDataRole.UserRole + 10
    Metadata = Qt.ItemDataRole.UserRole + 11
    UpdatedAt = Qt.ItemDataRole.UserRole + 12
    GroupLabel = Qt.ItemDataRole.UserRole + 13
    GroupCount = Qt.ItemDataRole.UserRole + 14
    CoverImage = Qt.ItemDataRole.UserRole + 15
    LinkCount = Qt.ItemDataRole.UserRole + 16
    OutputSummary = Qt.ItemDataRole.UserRole + 17
    PreviewText = Qt.ItemDataRole.UserRole + 18


__all__ = ["DossierRoles"]
