"""ProjectRoles class module for projects workspace."""

from __future__ import annotations
from PySide6.QtCore import Qt

class ProjectRoles:
    RowType = int(Qt.ItemDataRole.UserRole) + 1   # header | project
    Area = int(Qt.ItemDataRole.UserRole) + 2
    Title = int(Qt.ItemDataRole.UserRole) + 3
    Updated = int(Qt.ItemDataRole.UserRole) + 4
    Priority = int(Qt.ItemDataRole.UserRole) + 5
    Archived = int(Qt.ItemDataRole.UserRole) + 6
    ProjectId = int(Qt.ItemDataRole.UserRole) + 7
    UpdatedDate = int(Qt.ItemDataRole.UserRole) + 8
    Depth = int(Qt.ItemDataRole.UserRole) + 9
    HasChildren = int(Qt.ItemDataRole.UserRole) + 10
    IsCollapsed = int(Qt.ItemDataRole.UserRole) + 11
    MarkerColor = int(Qt.ItemDataRole.UserRole) + 12
    MarkerTheme = int(Qt.ItemDataRole.UserRole) + 13
    AttachmentSummary = int(Qt.ItemDataRole.UserRole) + 14
    RepositoryCatalog = int(Qt.ItemDataRole.UserRole) + 15

__all__ = ["ProjectRoles"]
