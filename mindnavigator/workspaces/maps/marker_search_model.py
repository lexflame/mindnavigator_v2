"""MarkerSearchModel class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
class MarkerSearchModel(QAbstractListModel):
    MarkerRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        # Инициализируем модель для поиска маркеров.
        super().__init__(parent)
        # Список маркеров для поиска.
        self._items: List[Marker] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        # Количество строк зависит от списка маркеров.
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        # Возвращаем строку отображения и сам маркер.
        if not index.isValid():
            return None
        marker = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            title = marker.name or "Метка"
            marker_type = marker.type or "—"
            return f"{title} · {marker_type} ({marker.x:.0f}, {marker.y:.0f})"
        if role == self.MarkerRole:
            return marker
        return None

    def set_markers(self, markers: List[Marker]) -> None:
        # Полностью обновляем модель списка маркеров.
        self.beginResetModel()
        self._items = list(markers)
        self.endResetModel()

__all__ = ["MarkerSearchModel"]
