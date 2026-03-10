"""ObjectsModel class module for objects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class ObjectsModel(QAbstractListModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._all_items: List[ObjectRow] = []
        self._items: List[ObjectRow] = []
        self._rows: List[ObjectListRow] = []
        self._catalog_filter: Optional[str] = None
        self._project_filter_id: Optional[int] = None
        self._task_filter_id: Optional[int] = None
        self._marker_filter_id: Optional[int] = None
        self._search = ""
        self._load_objects()

    def _load_objects(self) -> None:
        objects = self._db.fetch_objects()
        self._all_items = [
            ObjectRow(
                obj.id,
                obj.title,
                obj.catalog,
                obj.object_type,
                obj.status,
                obj.description,
            )
            for obj in objects
        ]
        self._rebuild()

    def reload(self) -> None:
        self._load_objects()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == ObjectRoles.RowType:
            return "category" if isinstance(row, ObjectCategoryRow) else "object"
        if isinstance(row, ObjectCategoryRow):
            if role == ObjectRoles.Title:
                return row.category
            if role == Qt.ItemDataRole.DisplayRole:
                return row.category
            return None
        item = row
        if role == ObjectRoles.Id:
            return item.id
        if role == ObjectRoles.Title:
            return item.title
        if role == ObjectRoles.Catalog:
            return item.catalog
        if role == ObjectRoles.ObjectType:
            return item.object_type
        if role == ObjectRoles.Status:
            return item.status
        if role == ObjectRoles.Description:
            return item.description
        if role == Qt.ItemDataRole.DisplayRole:
            return item.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        row = self._rows[index.row()]
        if isinstance(row, ObjectCategoryRow):
            return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags |= Qt.ItemFlag.ItemIsSelectable
        return flags

    def set_search(self, text: str) -> None:
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_catalog_filter(self, catalog: Optional[str]) -> None:
        self._catalog_filter = catalog
        self._rebuild()

    def set_project_filter(self, project_id: Optional[int]) -> None:
        self._project_filter_id = project_id
        if project_id is not None:
            self._task_filter_id = None
            self._marker_filter_id = None
        self._rebuild()

    def set_task_filter(self, task_id: Optional[int]) -> None:
        self._task_filter_id = task_id
        if task_id is not None:
            self._project_filter_id = None
            self._marker_filter_id = None
        self._rebuild()

    def set_marker_filter(self, marker_id: Optional[int]) -> None:
        self._marker_filter_id = marker_id
        if marker_id is not None:
            self._project_filter_id = None
            self._task_filter_id = None
        self._rebuild()

    def catalogs(self) -> List[str]:
        catalogs = {item.catalog for item in self._all_items if item.catalog}
        return sorted(catalogs)

    def add_object(self, obj: ObjectData) -> None:
        self._all_items.insert(
            0,
            ObjectRow(
                obj.id,
                obj.title,
                obj.catalog,
                obj.object_type,
                obj.status,
                obj.description,
            ),
        )
        self._rebuild()

    def update_object(self, obj: ObjectData) -> None:
        updated: List[ObjectRow] = []
        for item in self._all_items:
            if item.id == obj.id:
                updated.append(
                    ObjectRow(
                        obj.id,
                        obj.title,
                        obj.catalog,
                        obj.object_type,
                        obj.status,
                        obj.description,
                    )
                )
            else:
                updated.append(item)
        self._all_items = updated
        self._rebuild()

    def delete_object(self, object_id: int) -> None:
        self._all_items = [item for item in self._all_items if item.id != object_id]
        self._rebuild()

    def object_at(self, row: int) -> Optional[ObjectRow]:
        if row < 0 or row >= len(self._rows):
            return None
        row_item = self._rows[row]
        if isinstance(row_item, ObjectRow):
            return row_item
        return None

    def row_for_object_id(self, object_id: int) -> Optional[int]:
        for index, item in enumerate(self._rows):
            if isinstance(item, ObjectRow) and item.id == object_id:
                return index
        return None

    def _rebuild(self) -> None:
        search = self._search
        catalog = self._catalog_filter
        object_ids = None
        if self._marker_filter_id is not None or self._project_filter_id is not None or self._task_filter_id is not None:
            object_ids = set()
            for marker in self._db.fetch_map_markers():
                if not marker.object_ids:
                    continue
                if self._marker_filter_id is not None:
                    if marker.id == self._marker_filter_id:
                        object_ids.update(marker.object_ids)
                elif self._project_filter_id is not None:
                    if self._project_filter_id in marker.project_ids:
                        object_ids.update(marker.object_ids)
                elif self._task_filter_id is not None:
                    if self._task_filter_id in marker.task_ids:
                        object_ids.update(marker.object_ids)
        items: List[ObjectRow] = []
        for item in self._all_items:
            if object_ids is not None and item.id not in object_ids:
                continue
            if catalog:
                if item.catalog != catalog and not item.catalog.startswith(f"{catalog}/"):
                    continue
            if search:
                hay = f"{item.title} {item.catalog} {item.object_type} {item.status} {item.description}".lower()
                if search not in hay:
                    continue
            items.append(item)
        items.sort(
            key=lambda object_row: (
                normalize_object_category(object_row.catalog).lower(),
                object_row.title.lower(),
                object_row.id,
            )
        )

        self.beginResetModel()
        self._items = items
        self._rows = group_objects_by_category(items)
        self.endResetModel()

__all__ = ["ObjectsModel"]
