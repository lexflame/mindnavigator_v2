"""Рабочая область управления проектами.

Входные данные:
    Данные проектов и фильтры пользовательского интерфейса.

Выходные данные:
    Обновлённые записи проектов и визуальные карточки.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import subprocess
from typing import Dict, List, Union, Optional, Any, cast
import json

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QEvent, QDate
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle, QDialog,
    QAbstractItemView, QStyleOptionViewItem,
    QDialogButtonBox, QFormLayout, QMessageBox, QDateEdit, QCheckBox, QFileDialog
)

from mindnavigator.csv_transfer import CsvTransferError, CsvTransferService
from mindnavigator.storage import (
    format_project_date,
    get_database,
    normalize_priority,
    validate_area,
    validate_title,
)
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
from mindnavigator.workspaces.csv_workspace_transfer import (
    PROJECTS_CSV_FIELDS,
    export_projects_rows,
    import_projects_rows,
)

# ProjectsWorkspace — UI-близнец TasksWorkspace:
# - та же структура верхней панели
# - тот же подход к группировке (заголовки + строки)
# - QListView + делегат ради скорости


@dataclass(frozen=True)
class ProjectRow:
    id: int
    area: str               # group header key
    title: str
    updated: date
    priority: str           # Low | Medium | High
    archived: bool
    parent_project_id: Optional[int] = None
    default_task_priority: str = ""
    force_recurrence_kind: str = ""
    linked_map_id: Optional[int] = None
    linked_note_id: Optional[int] = None
    linked_object_id: Optional[int] = None
    marker_color: str = ""
    marker_theme: str = ""
    repository_catalog: str = ""


@dataclass(frozen=True)
class HeaderRow:
    area: str


Row = Union[ProjectRow, HeaderRow]

PROJECT_PRIORITY_SEQUENCE = ("Low", "Medium", "High")
ATTACHMENT_BADGE_ORDER = ("note", "idea", "object", "map", "marker", "file", "image")
ATTACHMENT_BADGE_LABELS = {
    "note": "NOTE",
    "idea": "IDEA",
    "object": "OBJECT",
    "map": "MAP",
    "marker": "MARK",
    "file": "FILE",
    "image": "IMG",
}
ATTACHMENT_BADGE_COLORS = {
    "note": QColor("#3b82f6"),
    "idea": QColor("#a855f7"),
    "object": QColor("#14b8a6"),
    "map": QColor("#f59e0b"),
    "marker": QColor("#ef4444"),
    "file": QColor("#64748b"),
    "image": QColor("#22c55e"),
}


@dataclass(frozen=True)
class RepositoryProbeState:
    available: bool
    branch_name: str = ""
    has_local_changes: bool = False
    message: str = ""


class RepositoryProbe:
    def inspect(self, repository_catalog: str) -> RepositoryProbeState:
        repo_path = (repository_catalog or "").strip()
        if not repo_path:
            return RepositoryProbeState(False, message="Каталог репозитория не указан.")
        path = Path(repo_path)
        if not path.exists() or not path.is_dir():
            return RepositoryProbeState(False, message="Каталог репозитория не найден.")
        try:
            branch_proc = subprocess.run(
                ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return RepositoryProbeState(False, message=str(exc))
        if branch_proc.returncode != 0:
            error_text = (branch_proc.stderr or "").strip() or "Невозможно определить ветку репозитория."
            return RepositoryProbeState(False, message=error_text)
        branch_name = (branch_proc.stdout or "").strip() or "(detached)"
        try:
            status_proc = subprocess.run(
                ["git", "-C", str(path), "status", "--porcelain"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return RepositoryProbeState(False, message=str(exc))
        if status_proc.returncode != 0:
            error_text = (status_proc.stderr or "").strip() or "Невозможно получить состояние репозитория."
            return RepositoryProbeState(False, message=error_text)
        has_changes = bool((status_proc.stdout or "").strip())
        return RepositoryProbeState(True, branch_name=branch_name, has_local_changes=has_changes)


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


class ProjectsModel(QAbstractListModel):
    def __init__(self, parent=None):
        """Создает модель данных проектов."""
        super().__init__(parent)
        self._db = get_database()
        self._all_rows: List[Row] = []
        self._rows: List[Row] = []
        self._project_title_cache: Dict[int, str] = {}
        self._project_depth_cache: Dict[int, int] = {}
        self._project_has_children_cache: Dict[int, bool] = {}
        self._project_attachment_summary: Dict[int, List[tuple[str, int]]] = {}
        self._attachment_summary_dirty = True
        self._repository_probe = RepositoryProbe()
        self._collapsed_project_ids: set[int] = set()
        self._collapsed_state_key = "projects_workspace.collapsed_ids"
        self._load_collapsed_state()
        self._filter_mode = "Все"      # Все | Активные | Архив
        self._search = ""
        self._area_focus: Optional[str] = None
        self._task_filter_id: Optional[int] = None
        self._priority_filter: Optional[str] = None
        self._reload_from_db()

    def _reload_from_db(self):
        """Обновляет список проектов из базы данных."""
        projects = self._db.fetch_projects()
        self._all_rows = [
            ProjectRow(
                p.id,
                p.area,
                p.title,
                p.updated,
                p.priority,
                p.archived,
                p.parent_project_id,
                p.default_task_priority,
                p.force_recurrence_kind,
                p.linked_map_id,
                p.linked_note_id,
                p.linked_object_id,
                p.marker_color,
                p.marker_theme,
                p.repository_catalog,
            )
            for p in projects
        ]
        valid_ids = {p.id for p in projects}
        before = set(self._collapsed_project_ids)
        self._collapsed_project_ids = {pid for pid in self._collapsed_project_ids if pid in valid_ids}
        if before != self._collapsed_project_ids:
            self._save_collapsed_state()
        self._attachment_summary_dirty = True
        self._rebuild()

    def refresh(self) -> None:
        """Перезагружает данные проектов из базы."""
        self._reload_from_db()

    def rowCount(self, parent=QModelIndex()) -> int:
        """Возвращает количество строк в модели."""
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(
        self,
        index: QModelIndex,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        """Отдает данные для делегата по ролям."""
        if not index.isValid():
            return None
        r = self._rows[index.row()]

        if role == ProjectRoles.RowType:
            return "header" if isinstance(r, HeaderRow) else "project"

        if isinstance(r, HeaderRow):
            if role == ProjectRoles.Area:
                return r.area
            if role == Qt.ItemDataRole.DisplayRole:
                return r.area
            return None

        if role == ProjectRoles.ProjectId:
            return r.id
        if role == ProjectRoles.Area:
            return r.area
        if role == ProjectRoles.Title:
            return r.title
        if role == ProjectRoles.Updated:
            return format_project_date(r.updated)
        if role == ProjectRoles.UpdatedDate:
            return r.updated
        if role == ProjectRoles.Priority:
            return r.priority
        if role == ProjectRoles.Archived:
            return r.archived
        if role == ProjectRoles.Depth:
            return self._project_depth_cache.get(r.id, 0)
        if role == ProjectRoles.HasChildren:
            return self._project_has_children_cache.get(r.id, False)
        if role == ProjectRoles.IsCollapsed:
            return r.id in self._collapsed_project_ids
        if role == ProjectRoles.MarkerColor:
            return r.marker_color
        if role == ProjectRoles.MarkerTheme:
            return r.marker_theme
        if role == ProjectRoles.AttachmentSummary:
            return self._project_attachment_summary.get(r.id, [])
        if role == ProjectRoles.RepositoryCatalog:
            return r.repository_catalog
        if role == Qt.ItemDataRole.DisplayRole:
            return r.title
        return None

    def toggle_project_collapsed(self, project_id: int) -> None:
        if project_id in self._collapsed_project_ids:
            self._collapsed_project_ids.remove(project_id)
        else:
            self._collapsed_project_ids.add(project_id)
        self._save_collapsed_state()
        self._rebuild()

    def toggle_project_collapsed_by_row(self, row_idx: int) -> None:
        row = self.project_at_row(row_idx)
        if row is None:
            return
        if not self._project_has_children_cache.get(row.id, False):
            return
        self.toggle_project_collapsed(row.id)

    def _load_collapsed_state(self) -> None:
        raw = self._db.get_setting(self._collapsed_state_key, "[]")
        try:
            payload = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            payload = []
        self._collapsed_project_ids = {int(v) for v in payload if isinstance(v, int)}

    def _save_collapsed_state(self) -> None:
        payload = sorted(self._collapsed_project_ids)
        self._db.set_setting(self._collapsed_state_key, json.dumps(payload, ensure_ascii=False))

    def flags(self, index: QModelIndex) -> Any:
        """Устанавливает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            return Qt.ItemFlag.ItemIsEnabled
        flags = cast(Any, Qt.ItemFlag.ItemIsEnabled)
        flags |= Qt.ItemFlag.ItemIsSelectable
        flags |= Qt.ItemFlag.ItemIsDragEnabled
        flags |= Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def move_project_by_drop(
        self,
        source_project_id: int,
        target_project_id: int,
        drop_after: bool,
        as_child: bool,
    ) -> bool:
        """Перемещает проект относительно target в пределах его sibling-группы."""
        projects = self._db.fetch_projects()
        by_id = {p.id: p for p in projects}
        source = by_id.get(source_project_id)
        target = by_id.get(target_project_id)
        if source is None or target is None:
            return False
        if source_project_id == target_project_id:
            return False

        if as_child:
            try:
                self._db.move_project(source_project_id, target_project_id, None)
            except ValueError:
                return False
            self.refresh()
            return True

        parent_id = target.parent_project_id
        siblings = self._db.fetch_project_children(parent_id)
        sibling_ids = [p.id for p in siblings if p.id != source_project_id]
        if target_project_id not in sibling_ids:
            return False
        index = sibling_ids.index(target_project_id)
        if drop_after:
            index += 1
        try:
            self._db.move_project(source_project_id, parent_id, index)
        except ValueError:
            return False
        self.refresh()
        return True

    def set_filter_mode(self, mode: str):
        """Обновляет режим фильтрации."""
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        """Устанавливает строку поиска."""
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_area_focus(self, area: Optional[str]):
        """Фиксирует активную область проектов."""
        self._area_focus = area
        self._rebuild()

    def set_task_filter(self, task_id: Optional[int]):
        """Фильтрует проекты по выбранной задаче."""
        self._task_filter_id = task_id
        self._rebuild()

    def set_priority_filter(self, priority: Optional[str]) -> None:
        if priority is None:
            self._priority_filter = None
        else:
            self._priority_filter = normalize_priority(priority)
        self._rebuild()

    def add_project(
        self,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool,
        parent_project_id: Optional[int] = None,
        default_task_priority: str = "",
        force_recurrence_kind: str = "",
        linked_map_id: Optional[int] = None,
        linked_note_id: Optional[int] = None,
        linked_object_id: Optional[int] = None,
        marker_color: str = "",
        marker_theme: str = "",
        repository_catalog: str = "",
    ):
        """Добавляет новый проект и пересобирает список."""
        project = self._db.create_project(
            area=area,
            title=title,
            updated=updated,
            priority=priority,
            archived=archived,
            parent_project_id=parent_project_id,
            default_task_priority=default_task_priority,
            force_recurrence_kind=force_recurrence_kind,
            linked_map_id=linked_map_id,
            linked_note_id=linked_note_id,
            linked_object_id=linked_object_id,
            marker_color=marker_color,
            marker_theme=marker_theme,
            repository_catalog=repository_catalog,
        )
        self._all_rows.append(
            ProjectRow(
                project.id,
                project.area,
                project.title,
                project.updated,
                project.priority,
                project.archived,
                project.parent_project_id,
                project.default_task_priority,
                project.force_recurrence_kind,
                project.linked_map_id,
                project.linked_note_id,
                project.linked_object_id,
                project.marker_color,
                project.marker_theme,
                project.repository_catalog,
            )
        )
        self._attachment_summary_dirty = True
        self._rebuild()

    def quick_add_project(
        self,
        area: str,
        parent_project_id: Optional[int] = None,
        title: str = "Новый проект",
    ) -> None:
        self.add_project(
            area=area,
            title=title,
            updated=date.today(),
            priority="Medium",
            archived=False,
            parent_project_id=parent_project_id,
        )

    def area_has_active(self, area: str) -> bool:
        """Проверяет наличие активных проектов в области."""
        return any(
            isinstance(it, ProjectRow) and it.area == area and not it.archived
            for it in self._all_rows
        )

    def set_area_archived(self, area: str, archived: bool):
        """Архивирует или восстанавливает все проекты области."""
        self._db.set_projects_archived_for_area(area, archived)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.area == area:
                it = ProjectRow(
                    it.id,
                    it.area,
                    it.title,
                    it.updated,
                    it.priority,
                    archived,
                    it.parent_project_id,
                    it.default_task_priority,
                    it.force_recurrence_kind,
                    it.linked_map_id,
                    it.linked_note_id,
                    it.linked_object_id,
                    it.marker_color,
                    it.marker_theme,
                    it.repository_catalog,
                )
            new_all.append(it)
        self._all_rows = new_all
        self._rebuild()

    def delete_area(self, area: str):
        """Удаляет все проекты в области."""
        self._db.delete_projects_by_area(area)
        self._all_rows = [
            it for it in self._all_rows if not (isinstance(it, ProjectRow) and it.area == area)
        ]
        if self._area_focus == area:
            self._area_focus = None
        self._attachment_summary_dirty = True
        self._rebuild()

    def rename_area(self, area: str, new_area: str):
        """Переименовывает область проектов."""
        self._db.rename_project_area(area, new_area)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.area == area:
                it = ProjectRow(
                    it.id,
                    new_area,
                    it.title,
                    it.updated,
                    it.priority,
                    it.archived,
                    it.parent_project_id,
                    it.default_task_priority,
                    it.force_recurrence_kind,
                    it.linked_map_id,
                    it.linked_note_id,
                    it.linked_object_id,
                    it.marker_color,
                    it.marker_theme,
                    it.repository_catalog,
                )
            new_all.append(it)
        self._all_rows = new_all
        if self._area_focus == area:
            self._area_focus = new_area
        self._attachment_summary_dirty = True
        self._rebuild()

    def project_at_row(self, row_idx: int) -> Optional[ProjectRow]:
        """Возвращает проект по индексу строки или None."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return None
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return None
        return r

    def update_project_by_row(
        self,
        row_idx: int,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool,
        parent_project_id: Optional[int] = None,
        default_task_priority: str = "",
        force_recurrence_kind: str = "",
        linked_map_id: Optional[int] = None,
        linked_note_id: Optional[int] = None,
        linked_object_id: Optional[int] = None,
        marker_color: str = "",
        marker_theme: str = "",
        repository_catalog: str = "",
    ):
        """Обновляет проект по индексу строки."""
        r = self.project_at_row(row_idx)
        if r is None:
            return
        updated_project = self._db.update_project(
            project_id=r.id,
            area=area,
            title=title,
            updated=updated,
            priority=priority,
            archived=archived,
            parent_project_id=parent_project_id,
            default_task_priority=default_task_priority,
            force_recurrence_kind=force_recurrence_kind,
            linked_map_id=linked_map_id,
            linked_note_id=linked_note_id,
            linked_object_id=linked_object_id,
            marker_color=marker_color,
            marker_theme=marker_theme,
            repository_catalog=repository_catalog,
        )

        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.id == r.id:
                it = ProjectRow(
                    updated_project.id,
                    updated_project.area,
                    updated_project.title,
                    updated_project.updated,
                    updated_project.priority,
                    updated_project.archived,
                    updated_project.parent_project_id,
                    updated_project.default_task_priority,
                    updated_project.force_recurrence_kind,
                    updated_project.linked_map_id,
                    updated_project.linked_note_id,
                    updated_project.linked_object_id,
                    updated_project.marker_color,
                    updated_project.marker_theme,
                    updated_project.repository_catalog,
                )
            new_all.append(it)

        self._all_rows = new_all
        self._attachment_summary_dirty = True
        self._rebuild()

    def cycle_priority_by_row(self, row_idx: int) -> None:
        project_row = self.project_at_row(row_idx)
        if project_row is None:
            return
        current = normalize_priority(project_row.priority)
        if current not in PROJECT_PRIORITY_SEQUENCE:
            next_priority = "Medium"
        else:
            next_index = (PROJECT_PRIORITY_SEQUENCE.index(current) + 1) % len(PROJECT_PRIORITY_SEQUENCE)
            next_priority = PROJECT_PRIORITY_SEQUENCE[next_index]
        updated_project = self._db.update_project(
            project_id=project_row.id,
            area=project_row.area,
            title=project_row.title,
            updated=project_row.updated,
            priority=next_priority,
            archived=project_row.archived,
            parent_project_id=project_row.parent_project_id,
            default_task_priority=project_row.default_task_priority,
            force_recurrence_kind=project_row.force_recurrence_kind,
            linked_map_id=project_row.linked_map_id,
            linked_note_id=project_row.linked_note_id,
            linked_object_id=project_row.linked_object_id,
            marker_color=project_row.marker_color,
            marker_theme=project_row.marker_theme,
            repository_catalog=project_row.repository_catalog,
        )
        new_all: List[Row] = []
        for row in self._all_rows:
            if isinstance(row, ProjectRow) and row.id == project_row.id:
                row = ProjectRow(
                    updated_project.id,
                    updated_project.area,
                    updated_project.title,
                    updated_project.updated,
                    updated_project.priority,
                    updated_project.archived,
                    updated_project.parent_project_id,
                    updated_project.default_task_priority,
                    updated_project.force_recurrence_kind,
                    updated_project.linked_map_id,
                    updated_project.linked_note_id,
                    updated_project.linked_object_id,
                    updated_project.marker_color,
                    updated_project.marker_theme,
                    updated_project.repository_catalog,
                )
            new_all.append(row)
        self._all_rows = new_all
        self._rebuild()

    def repository_probe_by_row(self, row_idx: int) -> RepositoryProbeState:
        project_row = self.project_at_row(row_idx)
        if project_row is None:
            return RepositoryProbeState(False, message="Проект не найден.")
        return self._repository_probe.inspect(project_row.repository_catalog)

    def toggle_archive_by_row(self, row_idx: int):
        """Переключает архивный статус проекта по строке."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return

        new_archived = not r.archived
        self._db.set_project_archived(r.id, new_archived)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.id == r.id:
                it = ProjectRow(
                    it.id,
                    it.area,
                    it.title,
                    it.updated,
                    it.priority,
                    new_archived,
                    it.parent_project_id,
                    it.default_task_priority,
                    it.force_recurrence_kind,
                    it.linked_map_id,
                    it.linked_note_id,
                    it.linked_object_id,
                    it.marker_color,
                    it.marker_theme,
                    it.repository_catalog,
                )
            new_all.append(it)

        self._all_rows = new_all
        self._rebuild()

    def delete_project_by_row(self, row_idx: int):
        """Удаляет проект по индексу строки."""
        r = self.project_at_row(row_idx)
        if r is None:
            return
        self._db.delete_project(r.id)
        self._all_rows = [it for it in self._all_rows if not (isinstance(it, ProjectRow) and it.id == r.id)]
        self._attachment_summary_dirty = True
        self._rebuild()

    def _rebuild(self):
        """Пересобирает список проектов с учетом фильтров."""
        self._rebuild_project_title_cache()
        if self._attachment_summary_dirty:
            self._rebuild_attachment_summary_cache()
        search = self._search
        task_project_id = None
        if self._task_filter_id is not None:
            for task in self._db.fetch_tasks():
                if task.id == self._task_filter_id:
                    task_project_id = task.project_id
                    break

        projects: List[ProjectRow] = []
        project_map = {
            row.id: row for row in self._all_rows
            if isinstance(row, ProjectRow)
        }

        def is_hidden_by_collapsed_parent(project: ProjectRow) -> bool:
            parent_id = project.parent_project_id
            seen: set[int] = set()
            while isinstance(parent_id, int) and parent_id not in seen:
                if parent_id in self._collapsed_project_ids:
                    return True
                seen.add(parent_id)
                parent = project_map.get(parent_id)
                if parent is None:
                    break
                parent_id = parent.parent_project_id
            return False
        for it in self._all_rows:
            if not isinstance(it, ProjectRow):
                continue

            if self._task_filter_id is not None:
                if task_project_id is None or it.id != task_project_id:
                    continue

            if self._area_focus is not None and it.area != self._area_focus:
                continue
            if self._priority_filter is not None and normalize_priority(it.priority) != self._priority_filter:
                continue

            if self._filter_mode in ("Все", "Активные") and it.archived:
                continue
            if self._filter_mode == "Архив" and not it.archived:
                continue

            display_title = self._project_title_cache.get(it.id, it.title).lower()
            if search and search not in it.title.lower() and search not in display_title and search not in it.area.lower():
                continue
            if is_hidden_by_collapsed_parent(it):
                continue

            projects.append(it)

        priority_order = {"High": 0, "Medium": 1, "Low": 2, "Отложенная": 3}

        def priority_key(priority: str) -> int:
            return priority_order[normalize_priority(priority)]

        projects.sort(
            key=lambda x: (
                x.area.lower(),
                priority_key(x.priority),
                self._project_title_cache.get(x.id, x.title).lower(),
                x.id,
            )
        )

        new_rows: List[Row] = []
        cur: Optional[str] = None
        for p in projects:
            if cur != p.area:
                cur = p.area
                new_rows.append(HeaderRow(cur))
            new_rows.append(p)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()

    def _rebuild_project_title_cache(self) -> None:
        project_map = {
            row.id: row for row in self._all_rows
            if isinstance(row, ProjectRow)
        }
        cache: Dict[int, str] = {}
        depth_cache: Dict[int, int] = {}
        has_children_cache: Dict[int, bool] = {}

        for project_row in project_map.values():
            has_children_cache[project_row.id] = False
        for project_row in project_map.values():
            if project_row.parent_project_id in project_map:
                has_children_cache[project_row.parent_project_id] = True

        def resolve_title(node: ProjectRow, seen: Optional[set[int]] = None) -> str:
            cached = cache.get(node.id)
            if cached is not None:
                return cached

            seen_set = seen or set()
            if node.id in seen_set:
                cache[node.id] = node.title
                return node.title

            if node.parent_project_id is None:
                cache[node.id] = node.title
                return node.title

            parent = project_map.get(node.parent_project_id)
            if parent is None:
                cache[node.id] = node.title
                return node.title

            nested = f"{resolve_title(parent, seen_set | {node.id})} / {node.title}"
            cache[node.id] = nested
            return nested

        def resolve_depth(node: ProjectRow, seen: Optional[set[int]] = None) -> int:
            cached = depth_cache.get(node.id)
            if cached is not None:
                return cached
            seen_set = seen or set()
            if node.id in seen_set:
                depth_cache[node.id] = 0
                return 0
            if node.parent_project_id is None:
                depth_cache[node.id] = 0
                return 0
            parent = project_map.get(node.parent_project_id)
            if parent is None:
                depth_cache[node.id] = 0
                return 0
            depth = resolve_depth(parent, seen_set | {node.id}) + 1
            depth_cache[node.id] = depth
            return depth

        for project_row in project_map.values():
            resolve_title(project_row)
            resolve_depth(project_row)

        self._project_title_cache = cache
        self._project_depth_cache = depth_cache
        self._project_has_children_cache = has_children_cache

    def _rebuild_attachment_summary_cache(self) -> None:
        project_map = {
            row.id: row for row in self._all_rows
            if isinstance(row, ProjectRow)
        }
        children_map: Dict[int, List[int]] = {}
        for project_row in project_map.values():
            parent_id = project_row.parent_project_id
            if isinstance(parent_id, int) and parent_id in project_map:
                children_map.setdefault(parent_id, []).append(project_row.id)

        direct_counts: Dict[int, Dict[str, int]] = {}
        for task in self._db.fetch_tasks():
            project_id = task.project_id
            if not isinstance(project_id, int):
                continue
            attachments = self._db.fetch_task_attachments(task.id)
            if not attachments:
                continue
            project_counts = direct_counts.setdefault(project_id, {})
            for attachment in attachments:
                kind = (attachment.kind or "").strip().lower()
                if not kind:
                    continue
                project_counts[kind] = project_counts.get(kind, 0) + 1

        aggregate_cache: Dict[int, Dict[str, int]] = {}

        def aggregate(project_id: int, seen: set[int]) -> Dict[str, int]:
            cached = aggregate_cache.get(project_id)
            if cached is not None:
                return cached
            if project_id in seen:
                return {}
            counts = dict(direct_counts.get(project_id, {}))
            for child_id in children_map.get(project_id, []):
                child_counts = aggregate(child_id, seen | {project_id})
                for kind, value in child_counts.items():
                    counts[kind] = counts.get(kind, 0) + value
            aggregate_cache[project_id] = counts
            return counts

        summary_cache: Dict[int, List[tuple[str, int]]] = {}
        for project_id in project_map.keys():
            counts = aggregate(project_id, set())
            if not counts:
                continue
            ordered_kinds = [kind for kind in ATTACHMENT_BADGE_ORDER if kind in counts]
            ordered_kinds.extend(
                kind for kind in sorted(counts.keys())
                if kind not in ATTACHMENT_BADGE_ORDER
            )
            badges = [
                (kind, int(counts[kind]))
                for kind in ordered_kinds
                if int(counts.get(kind, 0)) > 0
            ]
            if badges:
                summary_cache[project_id] = badges

        self._project_attachment_summary = summary_cache
        self._attachment_summary_dirty = False


class ProjectsItemDelegate(QStyledItemDelegate):
    ROW_H = 42
    HEADER_H = 32

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#cfcfcf")
    C_DIM = QColor("#8a8a8a")

    C_ARCH = QColor("#6f7a87")
    C_HIGH = QColor("#d94f4f")
    C_MED = QColor("#d0a93e")
    C_LOW = QColor("#4caf50")
    C_DEFER = QColor("#6f7a87")

    def __init__(self, parent=None):
        """Инициализирует делегат отрисовки проектов."""
        super().__init__(parent)
        self._icon_folder = qta.icon("fa5s.folder-open", color="#cfcfcf")
        self._icon_grip = qta.icon("fa5s.grip-lines", color="#8a8a8a")
        self._icon_menu = qta.icon("fa5s.ellipsis-v", color="#cfcfcf")
        self._icon_pin = qta.icon("fa5s.thumbtack", color="#d0a93e")
        self._icon_tree_open = qta.icon("fa5s.chevron-down", color="#8a8a8a")
        self._icon_tree_closed = qta.icon("fa5s.chevron-right", color="#8a8a8a")

        self._font = QFont()
        self._font.setPointSize(10)

        self._font_small = QFont()
        self._font_small.setPointSize(9)

        self._font_header = QFont()
        self._font_header.setPointSize(9)
        self._font_header.setBold(True)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Возвращает размер строки списка."""
        opt = cast(Any, option)
        rect = opt.rect
        width = rect.width() if rect is not None else 0
        row_type = index.data(ProjectRoles.RowType)
        if row_type == "header":
            return QSize(width, self.HEADER_H)
        return QSize(width, self.ROW_H)

    def _area_quick_rect(self, row_rect: QRect, area: str) -> QRect:
        left_pad = 0
        menu_w = max(18, row_rect.height())
        text_left = row_rect.left() + left_pad + menu_w + 8
        quick_w = 112
        quick_h = row_rect.height()
        area_w = QFontMetrics(self._font_header).horizontalAdvance(area or "")
        quick_x = text_left + area_w + 12
        max_right = row_rect.right() - 12
        if quick_x + quick_w > max_right:
            quick_x = max(text_left + 10, max_right - quick_w)
        return QRect(quick_x, row_rect.top(), quick_w, quick_h)

    def _project_quick_rect(self, title_rect: QRect, display_title: str) -> QRect:
        quick_w = 120
        quick_h = title_rect.height() - 14
        title_w = QFontMetrics(self._font).horizontalAdvance(display_title or "")
        quick_x = title_rect.left() + title_w + 10
        max_x = title_rect.right() - quick_w
        if quick_x > max_x:
            quick_x = max(title_rect.left(), max_x)
        return QRect(quick_x, title_rect.top() + 7, quick_w, quick_h)

    @staticmethod
    def _project_priority_rect(pr_rect: QRect, row_rect: QRect) -> QRect:
        priority_width = min(76, max(54, pr_rect.width() // 2))
        return QRect(pr_rect.left(), row_rect.top(), priority_width, row_rect.height())

    def _draw_attachment_badges(
        self,
        painter: QPainter,
        row_rect: QRect,
        attachment_summary: List[tuple[str, int]],
    ) -> None:
        if not attachment_summary:
            return
        metrics = QFontMetrics(self._font_small)
        badge_height = 18
        gap = 6
        max_width = max(80, row_rect.width() - 80)
        entries: List[tuple[str, QColor]] = []
        for kind, count in attachment_summary:
            label = ATTACHMENT_BADGE_LABELS.get(kind, (kind or "item").upper())
            text = f"{label} {count}" if count > 1 else label
            color = ATTACHMENT_BADGE_COLORS.get(kind, QColor("#475569"))
            entries.append((text, color))

        def total_width(items: List[tuple[str, QColor]]) -> int:
            if not items:
                return 0
            widths = [max(28, metrics.horizontalAdvance(text) + 12) for text, _ in items]
            return sum(widths) + gap * (len(widths) - 1)

        hidden = 0
        while len(entries) > 1 and total_width(entries) > max_width:
            hidden += 1
            entries.pop()
        if hidden:
            entries.append((f"+{hidden}", QColor("#374151")))

        widths = [max(28, metrics.horizontalAdvance(text) + 12) for text, _ in entries]
        total = sum(widths) + gap * (len(widths) - 1)
        x = row_rect.center().x() - total // 2
        y = row_rect.center().y() - badge_height // 2
        for idx, (text, color) in enumerate(entries):
            width = widths[idx]
            badge_rect = QRect(x, y, width, badge_height)
            painter.setPen(self.C_BORDER)
            painter.setBrush(color)
            painter.drawRoundedRect(badge_rect, 8, 8)
            luminance = color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
            painter.setPen(QColor("#111827") if luminance >= 160 else QColor("#f8fafc"))
            painter.setFont(self._font_small)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)
            x += width + gap

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Рисует строку проекта или заголовок области."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        row_type = index.data(ProjectRoles.RowType)
        opt = cast(Any, option)
        r = opt.rect
        state = opt.state

        if row_type == "header":
            area: str = index.data(ProjectRoles.Area) or ""
            painter.fillRect(r, self.C_BG)
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            left_pad = 0
            menu_w = max(18, r.height())
            menu_rect = QRect(r.left() + left_pad, r.top(), menu_w, r.height())
            quick_rect = self._area_quick_rect(r, area)
            text_rect = QRect(menu_rect.right() + 8, r.top(), quick_rect.left() - menu_rect.right() - 12, r.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, area)
            if state & QStyle.StateFlag.State_MouseOver:
                painter.setPen(self.C_BORDER)
                painter.setBrush(QColor("#1f2227"))
                painter.drawRoundedRect(quick_rect, 4, 4)
                painter.setPen(self.C_DIM)
                painter.setFont(self._font_small)
                painter.drawText(quick_rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "+ Проект")
            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.setPen(self.C_BORDER)
            painter.setBrush(QColor("#1f2227"))
            painter.drawRect(menu_rect)
            self._icon_menu.paint(
                painter,
                QRect(menu_rect.center().x() - 7, menu_rect.center().y() - 7, 14, 14),
            )
            painter.restore()
            return

        title: str = index.data(ProjectRoles.Title) or ""
        updated: str = index.data(ProjectRoles.Updated) or ""
        priority: str = index.data(ProjectRoles.Priority) or "Medium"
        archived: bool = bool(index.data(ProjectRoles.Archived))
        depth: int = int(index.data(ProjectRoles.Depth) or 0)
        has_children: bool = bool(index.data(ProjectRoles.HasChildren))
        is_collapsed: bool = bool(index.data(ProjectRoles.IsCollapsed))
        marker_color: str = (index.data(ProjectRoles.MarkerColor) or "").strip()
        marker_theme: str = (index.data(ProjectRoles.MarkerTheme) or "").strip()

        bg = self.C_ROW if (index.row() % 2 == 0) else self.C_ROW_ALT
        if state & QStyle.StateFlag.State_Selected:
            bg = QColor("#343844")
        elif marker_color:
            tint = QColor(marker_color)
            if tint.isValid():
                bg = QColor(
                    int(bg.red() * 0.65 + tint.red() * 0.35),
                    int(bg.green() * 0.65 + tint.green() * 0.35),
                    int(bg.blue() * 0.65 + tint.blue() * 0.35),
                )

        painter.fillRect(r, bg)
        painter.setPen(self.C_BORDER)
        painter.drawRect(r.adjusted(0, 0, -1, -1))

        x = r.left() + 10
        cy = r.center().y()

        grip_rect = QRect(x, cy - 8, 16, 16)
        self._icon_grip.paint(painter, grip_rect)
        x += 22

        # archive checkbox-like indicator
        box_rect = QRect(x, cy - 7, 14, 14)
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#16171a"))
        painter.drawRect(box_rect)

        if archived:
            painter.setPen(QColor("#cfcfcf"))
            painter.drawLine(box_rect.left() + 3, box_rect.center().y(),
                             box_rect.center().x() - 1, box_rect.bottom() - 3)
            painter.drawLine(box_rect.center().x() - 1, box_rect.bottom() - 3,
                             box_rect.right() - 2, box_rect.top() + 3)

        x += 22

        icon_rect = QRect(x, cy - 8, 16, 16)
        self._icon_folder.paint(painter, icon_rect)
        x += 22

        depth = max(0, min(depth, 6))
        x += depth * 14

        marker_rect = QRect(x, cy - 8, 16, 16)
        if has_children:
            marker_icon = self._icon_tree_closed if is_collapsed else self._icon_tree_open
            marker_icon.paint(painter, marker_rect)
        else:
            painter.setFont(self._font_small)
            painter.setPen(self.C_DIM)
            painter.drawText(marker_rect, Qt.AlignmentFlag.AlignCenter, ".")
        x += 18

        painter.setFont(self._font)
        painter.setPen(self.C_TEXT if not archived else self.C_DIM)

        right_pad = 8
        menu_w = max(18, r.height())
        quick_w = 120
        pr_w = 160
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top(), menu_w, r.height())
        quick_rect = QRect(menu_rect.left() - quick_w - 8, r.top(), quick_w, r.height())
        pr_rect = QRect(quick_rect.left() - pr_w - 8, r.top(), pr_w, r.height())

        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())
        display_title = f"{title} · {marker_theme.upper()}" if marker_theme else title
        quick_rect = self._project_quick_rect(title_rect, display_title)
        title_text_rect = QRect(
            title_rect.left(),
            title_rect.top(),
            max(10, quick_rect.left() - title_rect.left() - 8),
            title_rect.height(),
        )
        elided = QFontMetrics(self._font).elidedText(
            display_title,
            Qt.TextElideMode.ElideRight,
            title_text_rect.width(),
        )
        painter.drawText(title_text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)

        raw_attachment_summary = index.data(ProjectRoles.AttachmentSummary) or []
        attachment_summary: List[tuple[str, int]] = []
        for entry in raw_attachment_summary:
            if not isinstance(entry, (tuple, list)) or len(entry) != 2:
                continue
            kind = (str(entry[0]) or "").strip().lower()
            try:
                count = int(entry[1])
            except (TypeError, ValueError):
                continue
            if kind and count > 0:
                attachment_summary.append((kind, count))
        if state & QStyle.StateFlag.State_MouseOver and attachment_summary:
            self._draw_attachment_badges(painter, r, attachment_summary)

        pr_color = self.C_ARCH if archived else self._prio_color(priority)
        painter.setFont(self._font_small)
        painter.setPen(pr_color)

        pin_w = 16
        priority_gap = 8
        pin_gap = 10
        priority_rect = self._project_priority_rect(pr_rect, r)
        date_rect = QRect(
            priority_rect.right() + priority_gap,
            r.top(),
            pr_rect.width() - priority_rect.width() - priority_gap - pin_w - pin_gap,
            r.height(),
        )

        painter.drawText(priority_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                         priority if not archived else "ARCH")

        painter.setPen(self.C_DIM)
        painter.drawText(date_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                         f"обновл. {updated}")

        pin_rect = QRect(pr_rect.right() - pin_w, cy - 8, pin_w, 16)
        self._icon_pin.paint(painter, pin_rect)

        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 7, menu_rect.center().y() - 7, 14, 14))
        if state & QStyle.StateFlag.State_MouseOver:
            painter.setPen(self.C_BORDER)
            painter.setBrush(QColor("#1f2227"))
            painter.drawRoundedRect(quick_rect, 4, 4)
            painter.setPen(self.C_DIM)
            painter.drawText(quick_rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "+ Подпроект")

        painter.restore()

    def editorEvent(
        self,
        event: QEvent,
        model: QAbstractListModel,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        """Обрабатывает клики по индикатору архивации и меню."""
        row_type = index.data(ProjectRoles.RowType)
        if row_type == "header":
            if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
                if event.button() != Qt.MouseButton.LeftButton:
                    return False
                pos = event.position().toPoint()
                opt = cast(Any, option)
                r = opt.rect
                left_pad = 0
                menu_w = max(18, r.height())
                menu_rect = QRect(r.left() + left_pad, r.top(), menu_w, r.height())
                area = index.data(ProjectRoles.Area) or ""
                quick_rect = self._area_quick_rect(r, area)
                if menu_rect.contains(pos):
                    self._show_area_menu(index)
                    return True
                if quick_rect.contains(pos):
                    area = index.data(ProjectRoles.Area) or ""
                    if hasattr(model, "quick_add_project"):
                        typed_model = cast(ProjectsModel, model)
                        typed_model.quick_add_project(area=area, title="Новый проект")
                        self._refresh_area_combo(area)
                    return True
            return False

        if row_type != "project":
            return False

        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            pos = event.position().toPoint()
            opt = cast(Any, option)
            r = opt.rect
            cy = r.center().y()

            x = r.left() + 10
            x += 22
            box_side = max(18, r.height())
            box_rect = QRect(x, r.top(), box_side, r.height())
            x += box_side + 8
            x += 22
            depth: int = int(index.data(ProjectRoles.Depth) or 0)
            depth = max(0, min(depth, 6))
            x += depth * 14
            marker_rect = QRect(x, cy - 8, 16, 16)

            right_pad = 8
            menu_w = max(18, r.height())
            quick_w = 120
            menu_rect = QRect(r.right() - right_pad - menu_w, r.top(), menu_w, r.height())
            quick_rect = QRect(menu_rect.left() - quick_w - 8, r.top(), quick_w, r.height())
            pr_w = 160
            pr_rect = QRect(quick_rect.left() - pr_w - 8, r.top(), pr_w, r.height())
            priority_rect = self._project_priority_rect(pr_rect, r)
            title_rect = QRect(x + 18, r.top(), pr_rect.left() - (x + 18) - 10, r.height())
            title = index.data(ProjectRoles.Title) or ""
            marker_theme = (index.data(ProjectRoles.MarkerTheme) or "").strip()
            display_title = f"{title} В· {marker_theme.upper()}" if marker_theme else title
            quick_rect = self._project_quick_rect(title_rect, display_title)

            if marker_rect.contains(pos):
                if hasattr(model, "toggle_project_collapsed_by_row"):
                    model.toggle_project_collapsed_by_row(index.row())
                    return True

            if box_rect.contains(pos):
                typed_model = cast(ProjectsModel, model)
                typed_model.toggle_archive_by_row(index.row())
                return True
            if priority_rect.contains(pos):
                typed_model = cast(ProjectsModel, model)
                typed_model.cycle_priority_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True
            if quick_rect.contains(pos):
                project_id = index.data(ProjectRoles.ProjectId)
                area = index.data(ProjectRoles.Area) or ""
                if isinstance(project_id, int) and hasattr(model, "quick_add_project"):
                    typed_model = cast(ProjectsModel, model)
                    typed_model.quick_add_project(
                        area=area,
                        parent_project_id=project_id,
                        title="Новый подпроект",
                    )
                    self._refresh_area_combo(area)
                return True

        return False

    def _show_row_menu(self, index: QModelIndex):
        """Показывает контекстное меню проекта."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #1f2227;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #2b2f36;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2b2f;
                margin: 4px 8px;
            }
        """)
        act_edit = menu.addAction("Редактировать")
        act_repository_status = menu.addAction("Статус репозитория")
        menu.addSeparator()
        archived = bool(index.data(ProjectRoles.Archived))
        act_archive = menu.addAction("Восстановить" if archived else "Архивировать")
        act_delete = menu.addAction("Удалить")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit:
            self._edit_project(index)
            return
        if chosen == act_repository_status:
            self._show_repository_status(index, menu.parentWidget() or None)
            return
        if chosen == act_archive:
            model = index.model()
            if hasattr(model, "toggle_archive_by_row"):
                typed_model = cast(ProjectsModel, model)
                typed_model.toggle_archive_by_row(index.row())
            return
        if chosen != act_delete:
            return

        title = index.data(ProjectRoles.Title) or "проект"
        parent = menu.parentWidget() or None
        dialog = ConfirmDialog(
            "Удалить проект",
            f"Удалить проект:\n«{title}» ?",
            parent=parent,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        model = index.model()
        if hasattr(model, "delete_project_by_row"):
            model.delete_project_by_row(index.row())
            self._refresh_area_combo()

    def _show_repository_status(self, index: QModelIndex, parent: Optional[QWidget]) -> None:
        model = index.model()
        if not isinstance(model, ProjectsModel):
            QMessageBox.information(parent or self.parent(), "Репозиторий проекта", "Модель проекта недоступна.")
            return
        state = model.repository_probe_by_row(index.row())
        repository_catalog = (index.data(ProjectRoles.RepositoryCatalog) or "").strip()
        if not state.available:
            details = state.message or "Статус репозитория недоступен."
            if repository_catalog:
                details = f"Каталог: {repository_catalog}\n{details}"
            QMessageBox.information(parent or self.parent(), "Репозиторий проекта", details)
            return
        dirty_text = "изменения есть" if state.has_local_changes else "чисто"
        message = (
            f"Каталог: {repository_catalog}\n"
            f"Ветка: {state.branch_name}\n"
            f"Состояние: {dirty_text}"
        )
        QMessageBox.information(parent or self.parent(), "Репозиторий проекта", message)

    def _show_area_menu(self, index: QModelIndex):
        """Показывает меню действий области проектов."""
        area = index.data(ProjectRoles.Area) or ""
        model = index.model()
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #1f2227;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #2b2f36;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2b2f;
                margin: 4px 8px;
            }
        """)
        act_edit = menu.addAction("Редактировать")
        menu.addSeparator()
        has_active = True
        if hasattr(model, "area_has_active"):
            has_active = model.area_has_active(area)
        act_archive = menu.addAction("Архивировать" if has_active else "Восстановить")
        act_delete = menu.addAction("Удалить")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit:
            self._edit_area(area, model)
            return
        if chosen == act_archive:
            if hasattr(model, "set_area_archived"):
                model.set_area_archived(area, archived=has_active)
                self._refresh_area_combo(area)
            return
        if chosen != act_delete:
            return

        parent = menu.parentWidget() or None
        dialog = ConfirmDialog(
            "Удалить область",
            f"Удалить все проекты в области:\n«{area}» ?",
            parent=parent,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        if hasattr(model, "delete_area"):
            model.delete_area(area)
            self._refresh_area_combo()

    def _edit_area(self, area: str, model):
        """Открывает диалог редактирования области проектов."""
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = ProjectAreaEditDialog(area, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        if hasattr(model, "rename_area"):
            try:
                model.rename_area(area, values["area"])
                self._refresh_area_combo(values["area"])
            except ValueError as exc:
                QMessageBox.warning(parent or self.parent(), "Проверка", str(exc))

    def _edit_project(self, index: QModelIndex):
        """Открывает диалог редактирования проекта."""
        raw_model = index.model()
        if not isinstance(raw_model, ProjectsModel):
            return

        model = raw_model
        project = model.project_at_row(index.row())
        if project is None:
            return

        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = ProjectEditDialog(project, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        if hasattr(model, "update_project_by_row"):
            try:
                model.update_project_by_row(
                    index.row(),
                    area=values["area"],
                    title=values["title"],
                    updated=values["updated"],
                    priority=values["priority"],
                    archived=values["archived"],
                    parent_project_id=values["parent_project_id"],
                    default_task_priority=values["default_task_priority"],
                    force_recurrence_kind=values["force_recurrence_kind"],
                    linked_map_id=values["linked_map_id"],
                    linked_note_id=values["linked_note_id"],
                    linked_object_id=values["linked_object_id"],
                    marker_color=values["marker_color"],
                    marker_theme=values["marker_theme"],
                    repository_catalog=values["repository_catalog"],
                )
                self._refresh_area_combo(values["area"])
            except ValueError as exc:
                QMessageBox.warning(parent or self.parent(), "Проверка", str(exc))

    def _refresh_area_combo(self, selected: Optional[str] = None):
        """Просит рабочую область обновить список областей."""
        widget = self.parent()
        while widget is not None:
            if hasattr(widget, "_refresh_area_combo"):
                widget._refresh_area_combo(selected)
                break
            widget = widget.parent()

    def _prio_color(self, p: str) -> QColor:
        """Возвращает цвет для приоритета проекта."""
        p = (p or "").lower()
        if p == "high":
            return self.C_HIGH
        if p == "low":
            return self.C_LOW
        if p == "отложенная":
            return self.C_DEFER
        return self.C_MED


class ProjectEditDialog(QDialog):
    def __init__(self, project: Optional[ProjectRow] = None, parent=None):
        """Создает диалог создания или редактирования проекта."""
        super().__init__(parent)
        is_new = project is None
        self._project = project
        self._db = get_database()
        self.setWindowTitle("Создание проекта" if is_new else "Редактирование проекта")
        self.setObjectName("ProjectEditDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(640, 660)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Создание проекта" if is_new else "Редактирование проекта")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.area_edit = QLineEdit(project.area if project else "")
        self.area_edit.setPlaceholderText("Область проекта")

        self.title_edit = QLineEdit(project.title if project else "")
        self.title_edit.setPlaceholderText("Название проекта")

        self.updated_edit = QDateEdit()
        self.updated_edit.setCalendarPopup(True)
        self.updated_edit.setDisplayFormat("dd.MM.yyyy")
        self.updated_edit.setKeyboardTracking(False)
        self.updated_edit.setDate(QDate.currentDate())
        if project:
            self.updated_edit.setDate(QDate(project.updated.year, project.updated.month, project.updated.day))

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["Low", "Medium", "High"])
        self.priority_edit.setCurrentText(project.priority if project else "Medium")
        self.parent_project_edit = QComboBox()
        self.parent_project_edit.addItem("None", None)
        for item in self._db.fetch_projects():
            if project and item.id == project.id:
                continue
            self.parent_project_edit.addItem(f"{item.area} / {item.title}", item.id)
        parent_idx = self.parent_project_edit.findData(project.parent_project_id if project else None)
        if parent_idx >= 0:
            self.parent_project_edit.setCurrentIndex(parent_idx)

        self.default_task_priority_edit = QComboBox()
        self.default_task_priority_edit.addItem("None", "")
        self.default_task_priority_edit.addItem("Low", "Low")
        self.default_task_priority_edit.addItem("Medium", "Medium")
        self.default_task_priority_edit.addItem("High", "High")
        default_priority = (project.default_task_priority if project else "") or ""
        default_prio_idx = self.default_task_priority_edit.findData(default_priority)
        if default_prio_idx >= 0:
            self.default_task_priority_edit.setCurrentIndex(default_prio_idx)

        self.force_recurrence_kind_edit = QComboBox()
        self.force_recurrence_kind_edit.addItem("None", "")
        self.force_recurrence_kind_edit.addItem("Daily", "daily")
        self.force_recurrence_kind_edit.addItem("Weekly", "weekly")
        self.force_recurrence_kind_edit.addItem("Monthly", "monthly")
        recurrence_idx = self.force_recurrence_kind_edit.findData((project.force_recurrence_kind if project else "") or "")
        if recurrence_idx >= 0:
            self.force_recurrence_kind_edit.setCurrentIndex(recurrence_idx)

        self.linked_map_edit = QComboBox()
        self.linked_map_edit.addItem("None", None)
        for map_item in self._db.fetch_maps():
            self.linked_map_edit.addItem(map_item.title, map_item.id)
        linked_map_idx = self.linked_map_edit.findData(project.linked_map_id if project else None)
        if linked_map_idx >= 0:
            self.linked_map_edit.setCurrentIndex(linked_map_idx)

        self.linked_note_edit = QComboBox()
        self.linked_note_edit.addItem("None", None)
        for note_item in self._db.fetch_notes():
            self.linked_note_edit.addItem(note_item.title, note_item.id)
        linked_note_idx = self.linked_note_edit.findData(project.linked_note_id if project else None)
        if linked_note_idx >= 0:
            self.linked_note_edit.setCurrentIndex(linked_note_idx)

        self.linked_object_edit = QComboBox()
        self.linked_object_edit.addItem("None", None)
        for object_item in self._db.fetch_objects():
            self.linked_object_edit.addItem(object_item.title, object_item.id)
        linked_object_idx = self.linked_object_edit.findData(project.linked_object_id if project else None)
        if linked_object_idx >= 0:
            self.linked_object_edit.setCurrentIndex(linked_object_idx)

        self.marker_color_edit = QComboBox()
        self.marker_color_edit.addItem("None", "")
        self.marker_color_edit.addItem("Blue", "#4C78D0")
        self.marker_color_edit.addItem("Green", "#3FAF72")
        self.marker_color_edit.addItem("Orange", "#D68A3A")
        self.marker_color_edit.addItem("Red", "#C95656")
        self.marker_color_edit.addItem("Purple", "#8A63D2")
        marker_color_idx = self.marker_color_edit.findData((project.marker_color if project else "") or "")
        if marker_color_idx >= 0:
            self.marker_color_edit.setCurrentIndex(marker_color_idx)

        self.marker_theme_edit = QComboBox()
        self.marker_theme_edit.addItem("None", "")
        self.marker_theme_edit.addItem("Movies", "movies")
        self.marker_theme_edit.addItem("Games", "games")
        self.marker_theme_edit.addItem("Books", "books")
        self.marker_theme_edit.addItem("Music", "music")
        self.marker_theme_edit.addItem("Work", "work")
        self.marker_theme_edit.addItem("Personal", "personal")
        self.marker_theme_edit.addItem("Dev", "dev")
        marker_theme_idx = self.marker_theme_edit.findData((project.marker_theme if project else "") or "")
        if marker_theme_idx >= 0:
            self.marker_theme_edit.setCurrentIndex(marker_theme_idx)

        self.repository_catalog_edit = QLineEdit((project.repository_catalog if project else "") or "")
        self.repository_catalog_edit.setPlaceholderText("Путь к локальному репозиторию")

        self.archived_edit = QCheckBox("Архивировать")
        self.archived_edit.setChecked(project.archived if project else False)

        form.addRow("Область", self.area_edit)
        form.addRow("Название", self.title_edit)
        form.addRow("Дата обновления", self.updated_edit)
        form.addRow("Приоритет", self.priority_edit)
        form.addRow("Parent project", self.parent_project_edit)
        form.addRow("Task priority preset", self.default_task_priority_edit)
        form.addRow("Force recurrence", self.force_recurrence_kind_edit)
        form.addRow("Linked map", self.linked_map_edit)
        form.addRow("Linked note", self.linked_note_edit)
        form.addRow("Linked object", self.linked_object_edit)
        form.addRow("Маркер (цвет)", self.marker_color_edit)
        form.addRow("Тема маркера", self.marker_theme_edit)
        form.addRow("Каталог репозитория", self.repository_catalog_edit)
        form.addRow("", self.archived_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#ProjectEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#ProjectEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#ProjectEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#ProjectEditDialog QLineEdit,
            QDialog#ProjectEditDialog QComboBox,
            QDialog#ProjectEditDialog QDateEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#ProjectEditDialog QCheckBox {{
                color: #cfcfcf;
                padding: 4px 0;
            }}

            QDialog#ProjectEditDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#ProjectEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ProjectEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        try:
            validate_area(self.area_edit.text())
            validate_title(self.title_edit.text(), field_name="Название проекта")
            normalize_priority(self.priority_edit.currentText())
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return

        self.accept()

    def values(self) -> dict:
        """Возвращает значения формы проекта."""
        qd = self.updated_edit.date()
        return {
            "area": self.area_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "updated": date(qd.year(), qd.month(), qd.day()),
            "priority": self.priority_edit.currentText().strip() or "Medium",
            "parent_project_id": self.parent_project_edit.currentData(),
            "default_task_priority": self.default_task_priority_edit.currentData() or "",
            "force_recurrence_kind": self.force_recurrence_kind_edit.currentData() or "",
            "linked_map_id": self.linked_map_edit.currentData(),
            "linked_note_id": self.linked_note_edit.currentData(),
            "linked_object_id": self.linked_object_edit.currentData(),
            "marker_color": self.marker_color_edit.currentData() or "",
            "marker_theme": self.marker_theme_edit.currentData() or "",
            "repository_catalog": self.repository_catalog_edit.text().strip(),
            "archived": self.archived_edit.isChecked(),
        }


class ProjectAreaEditDialog(QDialog):
    def __init__(self, area: str, parent=None):
        """Создает диалог редактирования области проектов."""
        super().__init__(parent)
        self.setWindowTitle("Редактирование области")
        self.setObjectName("ProjectAreaEditDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(560, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Редактирование области")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.area_edit = QLineEdit(area)
        self.area_edit.setPlaceholderText("Область проекта")
        form.addRow("Область", self.area_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#ProjectAreaEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#ProjectAreaEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#ProjectAreaEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#ProjectAreaEditDialog QLineEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#ProjectAreaEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ProjectAreaEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        try:
            validate_area(self.area_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        """Возвращает значения формы области."""
        return {
            "area": self.area_edit.text().strip(),
        }


class _ProjectsListView(QListView):
    def __init__(self, owner: "ProjectsWorkspace"):
        super().__init__(owner)
        self._owner = owner
        self._drag_source_project_id: Optional[int] = None
        self._pressed_project_id: Optional[int] = None

    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        row_type = index.data(ProjectRoles.RowType) if index.isValid() else None
        project_id = index.data(ProjectRoles.ProjectId) if row_type == "project" else None
        self._pressed_project_id = project_id if isinstance(project_id, int) else None
        super().mousePressEvent(event)

    def startDrag(self, supported_actions):
        if isinstance(self._pressed_project_id, int):
            self._drag_source_project_id = self._pressed_project_id
        else:
            index = self.currentIndex()
            row_type = index.data(ProjectRoles.RowType)
            project_id = index.data(ProjectRoles.ProjectId) if row_type == "project" else None
            self._drag_source_project_id = project_id if isinstance(project_id, int) else None
        super().startDrag(supported_actions)
        self._pressed_project_id = None

    def dropEvent(self, event):
        source_id = self._drag_source_project_id
        if not isinstance(source_id, int):
            event.ignore()
            return

        point = event.position().toPoint()
        target_index = self.indexAt(point)
        if not target_index.isValid() or target_index.data(ProjectRoles.RowType) != "project":
            event.ignore()
            self._drag_source_project_id = None
            return

        target_id = target_index.data(ProjectRoles.ProjectId)
        if not isinstance(target_id, int):
            event.ignore()
            self._drag_source_project_id = None
            return

        rect = self.visualRect(target_index)
        margin = max(4, rect.height() // 4)
        drop_before_zone = point.y() <= rect.top() + margin
        drop_after_zone = point.y() >= rect.bottom() - margin
        drop_after = point.y() > rect.center().y()
        as_child = not drop_before_zone and not drop_after_zone

        if target_id == source_id:
            direction = 1 if drop_after else -1
            row = target_index.row() + direction
            fallback_id = None
            while 0 <= row < self.model().rowCount():
                idx = self.model().index(row, 0)
                if idx.data(ProjectRoles.RowType) == "project":
                    maybe_id = idx.data(ProjectRoles.ProjectId)
                    if isinstance(maybe_id, int) and maybe_id != source_id:
                        fallback_id = maybe_id
                        break
                row += direction
            if fallback_id is None:
                event.ignore()
                self._drag_source_project_id = None
                return
            target_id = fallback_id
            as_child = False

        ok = self._owner.handle_project_drop(source_id, target_id, drop_after, as_child)
        if ok:
            event.acceptProposedAction()
        else:
            event.ignore()
        self._drag_source_project_id = None


class ProjectsWorkspace(QWidget):
    def __init__(self, parent=None):
        """Создает рабочую область проектов."""
        super().__init__(parent)
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self.setObjectName("ProjectsWorkspace")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        top = QFrame()
        top.setObjectName("ProjectsTopbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str) -> QToolButton:
            """Создает кнопку вкладки фильтра."""
            tab_button = QToolButton()
            tab_button.setText(text)
            tab_button.setCheckable(True)
            tab_button.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_button.setAutoRaise(True)
            self.tabs_group.addButton(tab_button)
            return tab_button

        self.tab_all = tab_btn("Все")
        self.tab_active = tab_btn("Активные")
        self.tab_arch = tab_btn("Архив")
        self.tab_all.setChecked(True)

        top_layout.addWidget(self.tab_all)
        top_layout.addWidget(self.tab_active)
        top_layout.addWidget(self.tab_arch)

        top_layout.addSpacing(12)

        self.cmb_area = QComboBox()
        self.cmb_area.addItems(["Все области", *get_database().project_areas()])
        self.cmb_area.setFixedWidth(180)
        top_layout.addWidget(self.cmb_area)

        top_layout.addSpacing(12)

        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Любой", "Low", "Medium", "High"])
        self.cmb_priority.setFixedWidth(110)

        self.btn_create = QToolButton()
        self.btn_create.setText("Создать")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export = QToolButton()
        self.btn_export.setText("Экспорт")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import = QToolButton()
        self.btn_import.setText("Импорт")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_graph = QToolButton()
        self.btn_graph.setText("GRAPH")
        self.btn_graph.setCursor(Qt.CursorShape.PointingHandCursor)

        top_layout.addWidget(self.cmb_priority)
        top_layout.addWidget(self.btn_create)
        top_layout.addWidget(self.btn_export)
        top_layout.addWidget(self.btn_import)
        top_layout.addWidget(self.btn_graph)

        top_layout.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)
        top_layout.addWidget(self.search)

        root.addWidget(top)

        self.list = _ProjectsListView(self)
        self.list.setObjectName("ProjectsList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setDragEnabled(True)
        self.list.setAcceptDrops(True)
        self.list.setMouseTracking(True)
        self.list.viewport().setAcceptDrops(True)
        self.list.setDropIndicatorShown(True)
        root.addWidget(self.list, 1)

        self.model = ProjectsModel(self)
        self.list.setModel(self.model)

        self.delegate = ProjectsItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        for button in self.tabs_group.buttons():
            button.clicked.connect(self._on_tab_changed)

        self.search.textChanged.connect(self.model.set_search)
        self.cmb_area.currentTextChanged.connect(self._on_area_changed)
        self.cmb_priority.currentTextChanged.connect(self._on_priority_filter_changed)
        self.btn_create.clicked.connect(self._on_create_project)
        self.btn_export.clicked.connect(self._export_projects_csv)
        self.btn_import.clicked.connect(self._import_projects_csv)
        self.btn_graph.clicked.connect(self._on_graph_clicked)

        self.setStyleSheet("""
            QWidget#ProjectsWorkspace { background: #16171a; }

            QFrame#ProjectsTopbar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QToolButton {
                color: #cfcfcf;
                border: none;
                padding: 6px 8px;
            }
            QToolButton:checked { background: #2a2b2f; }

            QComboBox, QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
            }

            QListView#ProjectsList {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }
        """)

    def _on_tab_changed(self):
        """Обрабатывает переключение фильтров по статусу."""
        if self.tab_arch.isChecked():
            self.model.set_filter_mode("Архив")
        elif self.tab_active.isChecked():
            self.model.set_filter_mode("Активные")
        else:
            self.model.set_filter_mode("Все")

    def _on_area_changed(self, text: str):
        """Обновляет фильтрацию по области проекта."""
        if text == "Все области":
            self.model.set_area_focus(None)
        else:
            self.model.set_area_focus(text)

    def refresh_projects(self) -> None:
        """Перезагружает список проектов из базы."""
        self.model.refresh()

    def _export_projects_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Projects",
            "projects_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_projects_rows(self._db.fetch_projects())
        if not rows:
            QMessageBox.information(self, "Projects", "Нет данных для экспорта.")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=PROJECTS_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Projects", f"Export failed: {exc}")
            return
        QMessageBox.information(self, "Projects", "Экспорт завершен.")

    def _import_projects_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Projects",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Projects", f"Import failed: {exc}")
            return
        result = import_projects_rows(self._db, rows)
        self.refresh_projects()
        self._refresh_area_combo()
        QMessageBox.information(
            self,
            "Projects",
            f"Импорт завершен: {result.imported}, пропущено: {result.skipped}.",
        )

    def set_task_filter(self, task_id: Optional[int]) -> None:
        """Устанавливает фильтр по задаче для списка проектов."""
        self.model.set_task_filter(task_id)

    def handle_project_drop(
        self,
        source_project_id: int,
        target_project_id: int,
        drop_after: bool,
        as_child: bool,
    ) -> bool:
        ok = self.model.move_project_by_drop(source_project_id, target_project_id, drop_after, as_child)
        if not ok:
            return False
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            if index.data(ProjectRoles.ProjectId) == source_project_id:
                self.list.setCurrentIndex(index)
                break
        return True

    def _refresh_area_combo(self, selected: Optional[str] = None):
        """Обновляет список областей проектов."""
        current = selected or self.cmb_area.currentText()
        self.cmb_area.blockSignals(True)
        self.cmb_area.clear()
        self.cmb_area.addItems(["Все области", *get_database().project_areas()])
        if current:
            self.cmb_area.setCurrentText(current)
        if self.cmb_area.currentText() != current and current != "Все области":
            self.cmb_area.setCurrentText("Все области")
        self.cmb_area.blockSignals(False)

    def _on_create_project(self):
        """Открывает диалог создания проекта."""
        dialog = ProjectEditDialog(parent=self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        try:
            self.model.add_project(
                area=values["area"],
                title=values["title"],
                updated=values["updated"],
                priority=values["priority"],
                archived=values["archived"],
                parent_project_id=values["parent_project_id"],
                default_task_priority=values["default_task_priority"],
                force_recurrence_kind=values["force_recurrence_kind"],
                linked_map_id=values["linked_map_id"],
                linked_note_id=values["linked_note_id"],
                linked_object_id=values["linked_object_id"],
                marker_color=values["marker_color"],
                marker_theme=values["marker_theme"],
                repository_catalog=values["repository_catalog"],
            )
            self._refresh_area_combo(values["area"])
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))

    def _on_priority_filter_changed(self, value: str) -> None:
        priority = None if value == "Любой" else value
        self.model.set_priority_filter(priority)

    def _on_graph_clicked(self) -> None:
        QMessageBox.information(
            self,
            "Projects",
            "Режим GRAPH запланирован как отдельный PARTITION и будет закрыт отдельным шагом.",
        )
