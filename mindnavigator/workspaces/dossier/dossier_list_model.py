"""List model for Dossier rows."""

from __future__ import annotations

from dataclasses import dataclass

from ._shared import *  # noqa: F401,F403
from .dossier_roles import DossierRoles


@dataclass(frozen=True)
class DossierGroupRow:
    label: str
    count: int


class DossierListModel(QAbstractListModel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[DossierData] = []
        self._rows: list[DossierData | DossierGroupRow] = []
        self._group_by = "none"
        self._link_counts: dict[int, int] = {}
        self._output_summaries: dict[int, str] = {}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        if role == DossierRoles.RowType:
            return "group" if isinstance(row, DossierGroupRow) else "dossier"
        if isinstance(row, DossierGroupRow):
            if role == DossierRoles.GroupLabel:
                return row.label
            if role == DossierRoles.GroupCount:
                return row.count
            if role in (DossierRoles.Title, Qt.ItemDataRole.DisplayRole):
                return row.label
            return None

        item = row
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
        if role == DossierRoles.CoverImage:
            return item.cover_image
        if role == DossierRoles.LinkCount:
            return self._link_counts.get(item.id, 0)
        if role == DossierRoles.OutputSummary:
            return self._output_summaries.get(item.id, "нет")
        if role == DossierRoles.PreviewText:
            return dossier_preview_text(item)
        if role == Qt.ItemDataRole.DisplayRole:
            return item.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        row = self._rows[index.row()]
        if isinstance(row, DossierGroupRow):
            return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

    def set_items(
        self,
        items: list[DossierData],
        *,
        group_by: str = "none",
        link_counts: Optional[dict[int, int]] = None,
        output_summaries: Optional[dict[int, str]] = None,
    ) -> None:
        self.beginResetModel()
        self._items = list(items)
        self._group_by = group_by
        self._link_counts = dict(link_counts or {})
        self._output_summaries = dict(output_summaries or {})
        self._rows = self._build_rows(self._items, group_by=group_by)
        self.endResetModel()

    def item_at(self, row: int) -> Optional[DossierData]:
        if 0 <= row < len(self._rows):
            item = self._rows[row]
            if isinstance(item, DossierData):
                return item
        return None

    def index_for_id(self, dossier_id: int) -> QModelIndex:
        for row, item in enumerate(self._rows):
            if isinstance(item, DossierData) and item.id == dossier_id:
                return self.index(row, 0)
        return QModelIndex()

    def first_item_index(self) -> QModelIndex:
        for row, item in enumerate(self._rows):
            if isinstance(item, DossierData):
                return self.index(row, 0)
        return QModelIndex()

    @staticmethod
    def _build_rows(items: list[DossierData], *, group_by: str) -> list[DossierData | DossierGroupRow]:
        normalized_group = (group_by or "none").strip().lower()
        if normalized_group == "none":
            return list(items)

        grouped: dict[str, list[DossierData]] = {}
        labels: dict[str, str] = {}
        for item in items:
            group_key, group_label = DossierListModel._group_for_item(item, normalized_group)
            grouped.setdefault(group_key, []).append(item)
            labels[group_key] = group_label

        rows: list[DossierData | DossierGroupRow] = []
        for group_key in sorted(grouped.keys(), key=lambda value: DossierListModel._group_sort_key(normalized_group, value)):
            values = grouped[group_key]
            rows.append(DossierGroupRow(label=labels[group_key], count=len(values)))
            rows.extend(values)
        return rows

    @staticmethod
    def _group_for_item(item: DossierData, group_by: str) -> tuple[str, str]:
        if group_by == "kind":
            return item.kind, dossier_kind_label(item.kind)
        if group_by == "status":
            return item.status, dossier_status_label(item.status)
        if group_by == "rating":
            rating_key = str(item.rating) if item.rating is not None else "none"
            return rating_key, dossier_rating_label(item.rating)
        return "all", "Все досье"

    @staticmethod
    def _group_sort_key(group_by: str, value: str) -> tuple[object, ...]:
        if group_by == "kind":
            order = [option_value for _, option_value in DOSSIER_KIND_OPTIONS if option_value is not None]
            return (order.index(value) if value in order else len(order), value)
        if group_by == "status":
            order = [option_value for _, option_value in DOSSIER_STATUS_OPTIONS if option_value is not None]
            return (order.index(value) if value in order else len(order), value)
        if group_by == "rating":
            if value == "none":
                return (999, value)
            try:
                return (-int(value), value)
            except ValueError:
                return (998, value)
        return (value,)


__all__ = ["DossierGroupRow", "DossierListModel"]
