"""List model for Dossier rows."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .dossier_roles import DossierRoles


class DossierListModel(QAbstractListModel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[DossierData] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == DossierRoles.DossierId:
            return item.id
        if role == DossierRoles.Kind:
            return item.kind
        if role == DossierRoles.Title:
            return item.title
        if role == DossierRoles.Summary:
            return item.summary
        if role == DossierRoles.Description:
            return item.description
        if role == DossierRoles.Status:
            return item.status
        if role == DossierRoles.Rating:
            return item.rating
        if role == DossierRoles.Source:
            return item.source
        if role == DossierRoles.Tags:
            return list(item.tags)
        if role == DossierRoles.Metadata:
            return dict(item.metadata)
        if role == DossierRoles.UpdatedAt:
            return item.updated_at
        if role == Qt.ItemDataRole.DisplayRole:
            return item.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

    def set_items(self, items: list[DossierData]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def item_at(self, row: int) -> Optional[DossierData]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def index_for_id(self, dossier_id: int) -> QModelIndex:
        for row, item in enumerate(self._items):
            if item.id == dossier_id:
                return self.index(row, 0)
        return QModelIndex()


__all__ = ["DossierListModel"]
