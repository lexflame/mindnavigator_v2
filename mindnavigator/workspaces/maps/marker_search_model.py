"""MarkerSearchModel class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
class MarkerSearchModel(QAbstractListModel):
    MarkerRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        # Инициализируем модель для поиска маркеров.
        super().__init__(parent)
        # Список результатов поиска на карте.
        self._items: List[Any] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        # Количество строк зависит от списка маркеров.
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        # Возвращаем строку отображения и сам результат поиска.
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(item, dict):
                return item.get("display", "")
            title = getattr(item, "name", "") or "Метка"
            marker_type = getattr(item, "type", "") or "—"
            return f"{title} · {marker_type} ({getattr(item, 'x', 0):.0f}, {getattr(item, 'y', 0):.0f})"
        if role == self.MarkerRole:
            return item
        return None

    def set_markers(self, markers: List[Any]) -> None:
        # Полностью обновляем модель списка результатов поиска.
        self.beginResetModel()
        self._items = list(markers)
        self.endResetModel()

__all__ = ["MarkerSearchModel"]
