"""IdeasListModel class module for ideas workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class IdeasListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ideas: list[IdeaItem] = []
        self._rows: list[IdeaRow] = []
        self._status_titles: dict[str, str] = {}
        self._status_order: dict[str, int] = {}

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == IdeaRoles.RowType:
            return "category" if isinstance(row, IdeaCategoryRow) else "idea"
        if isinstance(row, IdeaCategoryRow):
            if role == IdeaRoles.Title:
                return row.category
            if role == Qt.ItemDataRole.DisplayRole:
                return row.category
            return None
        item = row
        if role == IdeaRoles.IdeaId:
            return item.id
        if role == IdeaRoles.Title:
            return item.title
        if role == IdeaRoles.Summary:
            return item.summary
        if role == IdeaRoles.Body:
            return item.body_md
        if role == IdeaRoles.Status:
            return item.status
        if role == IdeaRoles.Type:
            return item.idea_type
        if role == IdeaRoles.ValueScore:
            return item.value_score
        if role == IdeaRoles.EffortScore:
            return item.effort_score
        if role == IdeaRoles.ProjectTitle:
            return item.project_title
        if role == IdeaRoles.Archived:
            return item.archived
        if role == IdeaRoles.OutputLabel:
            return item.output_label
        if role == IdeaRoles.RelationsCount:
            return item.relations_count
        if role == IdeaRoles.MaterialsCount:
            return item.materials_count
        if role == IdeaRoles.UpdatedLabel:
            return item.updated_label
        if role == Qt.ItemDataRole.DisplayRole:
            return item.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        row = self._rows[index.row()]
        if isinstance(row, IdeaCategoryRow):
            return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags |= Qt.ItemFlag.ItemIsSelectable
        return flags

    def set_items(
        self,
        items: list[IdeaItem],
        *,
        status_titles: Optional[dict[str, str]] = None,
        status_order: Optional[dict[str, int]] = None,
    ) -> None:
        self.beginResetModel()
        self._ideas = items
        self._status_titles = dict(status_titles or {})
        self._status_order = dict(status_order or {})
        display_order = {
            title: self._status_order.get(code, 999)
            for code, title in self._status_titles.items()
        }
        self._rows = group_ideas_by_category(items, self._status_titles, display_order)
        self.endResetModel()

    def item_at(self, row: int) -> Optional[IdeaItem]:
        if 0 <= row < len(self._rows):
            idea_row = self._rows[row]
            if isinstance(idea_row, IdeaItem):
                return idea_row
        return None

    def index_for_id(self, idea_id: int) -> QModelIndex:
        for row, item in enumerate(self._rows):
            if isinstance(item, IdeaItem) and item.id == idea_id:
                return self.index(row)
        return QModelIndex()

    def first_idea_index(self, status: Optional[str] = None) -> QModelIndex:
        normalized_status = (status or "").strip().lower()
        for row, item in enumerate(self._rows):
            if not isinstance(item, IdeaItem):
                continue
            if normalized_status and (item.status or "").strip().lower() != normalized_status:
                continue
            return self.index(row)
        return QModelIndex()

    def next_idea_index(self, idea_id: int, status: Optional[str] = None) -> QModelIndex:
        normalized_status = (status or "").strip().lower()
        seen_current = False
        for row, item in enumerate(self._rows):
            if not isinstance(item, IdeaItem):
                continue
            if not seen_current:
                if item.id == idea_id:
                    seen_current = True
                continue
            if normalized_status and (item.status or "").strip().lower() != normalized_status:
                continue
            return self.index(row)
        return QModelIndex()

    def statuses(self) -> List[str]:
        return sorted(
            {(item.status or "").strip().lower() for item in self._ideas if (item.status or "").strip()},
            key=lambda value: (
                self._status_order.get(value, 999),
                value,
            ),
        )

__all__ = ["IdeasListModel"]
