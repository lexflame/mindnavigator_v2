"""MapsModel class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
class MapsModel(QAbstractListModel):
    def __init__(self, parent=None):
        # Инициализируем модель списка карт.
        super().__init__(parent)
        # Основные структуры для хранения исходных и отфильтрованных данных.
        self._items: List[MapRow] = []
        self._all_items: List[MapRow] = []
        self._search = ""
        self._project_filter: Optional[str] = None
        self._db = get_database()
        # Загружаем данные при старте модели.
        self._load_maps()

    def _load_maps(self) -> None:
        # Забираем карты из базы и сохраняем в локальный список.
        maps = self._db.fetch_maps()
        self._all_items = [
            MapRow(
                item.id,
                item.title,
                item.description,
                item.project,
                item.tiles_path,
                item.tiles_h,
                item.tiles_w,
            )
            for item in maps
        ]
        # Пересобираем список с учетом фильтров.
        self._rebuild()

    def rowCount(self, parent=QModelIndex()) -> int:
        # Для дочерних индексов список не поддерживается.
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        # Возвращаем данные по ролям для списка.
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role == MapRoles.Title:
            return item.title
        if role == MapRoles.Description:
            return item.description
        if role == MapRoles.Id:
            return item.id
        if role == MapRoles.Project:
            return item.project
        if role == MapRoles.TilesPath:
            return item.tiles_path
        if role == MapRoles.TilesHeight:
            return item.tiles_h
        if role == MapRoles.TilesWidth:
            return item.tiles_w
        if role == Qt.ItemDataRole.DisplayRole:
            return item.title
        return None

    def add_map(
        self,
        title: str,
        description: str,
        project: str,
        tiles_path: str,
        tiles_h: int,
        tiles_w: int,
    ) -> None:
        # Нормализуем ввод и проверяем обязательные поля.
        title = (title or "").strip()
        if not title:
            return
        try:
            # Создаем карту в базе.
            created = self._db.create_map(title, description, project, tiles_path, tiles_h, tiles_w)
        except ValueError:
            return
        # Добавляем новую карту в локальный список и пересобираем фильтры.
        self._all_items.append(
            MapRow(
                created.id,
                created.title,
                created.description,
                created.project,
                created.tiles_path,
                created.tiles_h,
                created.tiles_w,
            )
        )
        self._rebuild()

    def update_map(
        self,
        map_id: int,
        title: str,
        description: str,
        project: str,
        tiles_path: str,
        tiles_h: int,
        tiles_w: int,
    ) -> None:
        # Нормализуем название и валидируем ввод.
        title = (title or "").strip()
        if not title:
            return
        try:
            # Обновляем запись в базе.
            updated_map = self._db.update_map(map_id, title, description, project, tiles_path, tiles_h, tiles_w)
        except ValueError:
            return
        # Пересоздаем список с обновленным элементом.
        updated = []
        for item in self._all_items:
            if item.id == map_id:
                updated.append(
                    MapRow(
                        updated_map.id,
                        updated_map.title,
                        updated_map.description,
                        updated_map.project,
                        updated_map.tiles_path,
                        updated_map.tiles_h,
                        updated_map.tiles_w,
                    )
                )
            else:
                updated.append(item)
        self._all_items = updated
        # Перестраиваем отображаемый список.
        self._rebuild()

    def set_search(self, text: str) -> None:
        # Обновляем строку поиска и фильтруем список.
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_project_filter(self, project: Optional[str]) -> None:
        # Сохраняем фильтр по проекту и обновляем отображение.
        self._project_filter = project
        self._rebuild()

    def _rebuild(self) -> None:
        # Применяем текущие фильтры поиска и проекта.
        search = self._search
        project = self._project_filter
        items = []
        for item in self._all_items:
            if project and item.project != project:
                continue
            if search:
                hay = f"{item.title} {item.description} {item.project}".lower()
                if search not in hay:
                    continue
            items.append(item)

        # Обновляем модель через reset, чтобы корректно перерисовать список.
        self.beginResetModel()
        self._items = items
        self.endResetModel()

__all__ = ["MapsModel"]
