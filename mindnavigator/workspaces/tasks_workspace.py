"""Рабочая область управления задачами.

Входные данные:
    Записи задач из базы данных, пользовательские события и вложения.

Выходные данные:
    Обновлённые данные задач, файлы вложений и UI-состояния.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import html
import json
from pathlib import Path
import re
from typing import Dict, List, Union, Optional, Set, Tuple

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QPoint, QAbstractListModel, QModelIndex, QEvent, QDate, QTime, QMimeData
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor, QPixmap, QShortcut, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QDateEdit, QTimeEdit, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle,
    QCheckBox, QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QAbstractItemView, QPlainTextEdit, QScrollArea,
    QStackedWidget, QTableWidget, QTableWidgetItem, QSpinBox, QHeaderView
)

try:
    from mindnavigator.storage import (
        CloudFileData,
        TaskAttachmentData,
        get_database,
        normalize_priority,
        validate_area,
        validate_time_text,
        validate_title,
    )
    from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
    from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
    from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace
except ModuleNotFoundError:
    from ..storage import (
        CloudFileData,
        TaskAttachmentData,
        get_database,
        normalize_priority,
        validate_area,
        validate_time_text,
        validate_title,
    )
    from ..ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
    from ..ui.styles import MATH_PHYS_BACKGROUND
    from ..ui.workspaces.base_workspace import BaseWorkspace

WEEKDAY_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
_PARENT_UNSET = object()

ATTACHMENT_KIND_LABELS = {
    "note": "Заметка",
    "object": "Объект",
    "map": "Карта",
    "marker": "Метка карты",
    "file": "Файл",
    "image": "Изображение",
}
ATTACHMENT_KIND_ORDER = ("note", "object", "map", "marker", "file", "image")
_URL_RE = re.compile(r"(https?://[^\s<>'\"()]+)")


def attachment_kind_label(kind: str) -> str:
    return ATTACHMENT_KIND_LABELS.get(kind, kind)


def _linkify_description_text(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "—"
    escaped = html.escape(raw)
    linked = _URL_RE.sub(r"<a href='\1'>\1</a>", escaped)
    return linked.replace("\n", "<br>")


@dataclass(frozen=True)
class TaskRow:
    id: int
    day: date
    time_text: str
    title: str
    description: str
    priority: str   # Low | Medium | High
    done: bool
    project_id: Optional[int] = None
    project_title: str = ""
    project_area: str = ""
    parent_id: Optional[int] = None
    recurrence_kind: str = ""
    recurrence_interval: int = 1
    completion_delay_minutes: int = 0


@dataclass(frozen=True)
class HeaderRow:
    day: date


@dataclass(frozen=True)
class SortHeaderRow:
    pass


Row = Union[TaskRow, HeaderRow, SortHeaderRow]


class TaskRoles:
    RowType = Qt.UserRole + 1  # header | task
    Day = Qt.UserRole + 2
    TimeText = Qt.UserRole + 3
    Title = Qt.UserRole + 4
    Description = Qt.UserRole + 5
    Priority = Qt.UserRole + 6
    Done = Qt.UserRole + 7
    TaskId = Qt.UserRole + 8
    SortKey = Qt.UserRole + 9
    SortDirection = Qt.UserRole + 10
    DisplayTime = Qt.UserRole + 11
    ProjectTitle = Qt.UserRole + 12
    Expanded = Qt.UserRole + 13
    HasSubtasks = Qt.UserRole + 14
    SubtasksExpanded = Qt.UserRole + 15
    SubtaskDepth = Qt.UserRole + 16
    ProjectArea = Qt.UserRole + 17
    AttachmentSummary = Qt.UserRole + 18
    RecurrenceKind = Qt.UserRole + 19
    CompletionDelayMinutes = Qt.UserRole + 20


class QuickProjectCreateDialog(QDialog):
    def __init__(self, parent=None):
        """Создает краткий диалог создания проекта."""
        super().__init__(parent)
        self.setWindowTitle("Создание проекта")
        self.setObjectName("QuickProjectCreateDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(560, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Создание проекта")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.area_edit = QComboBox()
        self.area_edit.setEditable(True)
        self.area_edit.addItems(get_database().project_areas())
        self.area_edit.setCurrentText("")
        if self.area_edit.lineEdit():
            self.area_edit.lineEdit().setPlaceholderText("Область проекта")

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название проекта")

        self.updated_edit = QDateEdit()
        self.updated_edit.setCalendarPopup(True)
        self.updated_edit.setDisplayFormat("dd.MM.yyyy")
        self.updated_edit.setKeyboardTracking(False)
        self.updated_edit.setDate(QDate.currentDate())

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["Low", "Medium", "High"])
        self.priority_edit.setCurrentText("Medium")

        form.addRow("Область", self.area_edit)
        form.addRow("Название", self.title_edit)
        form.addRow("Дата", self.updated_edit)
        form.addRow("Приоритет", self.priority_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#QuickProjectCreateDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#QuickProjectCreateDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#QuickProjectCreateDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _on_accept(self):
        """Проверяет ввод перед созданием проекта."""
        try:
            validate_area(self.area_edit.currentText())
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
            "area": self.area_edit.currentText().strip(),
            "title": self.title_edit.text().strip(),
            "updated": date(qd.year(), qd.month(), qd.day()),
            "priority": self.priority_edit.currentText().strip() or "Medium",
        }


class TasksModel(QAbstractListModel):
    def __init__(self, parent=None):
        """Создает модель данных задач для списка."""
        super().__init__(parent)
        self._db = get_database()
        self._all_rows: List[Row] = []
        self._rows: List[Row] = []
        self._task_depths: dict[int, int] = {}
        self._task_children: dict[int, List[TaskRow]] = {}
        self._filter_mode = "Все"      # Все | План | Сегодня | Выполнено | Отложенные
        self._search = ""
        self._focus_day: Optional[date] = None
        self._project_filter_id: Optional[int] = None
        self._priority_filter: Optional[str] = None
        self._sort_key = "priority"  # date | title | priority
        self._sort_asc = True
        self._drag_enabled = False
        self._expanded_task_ids: set[int] = set()
        self._collapsed_subtask_ids: set[int] = set()
        self._subtask_state_initialized: set[int] = set()
        self._reload_from_db()

    def _reload_from_db(self):
        """Обновляет список задач из базы данных."""
        tasks = self._db.fetch_tasks()
        self._all_rows = [
            TaskRow(
                t.id,
                t.day,
                t.time_text,
                t.title,
                t.description,
                t.priority,
                t.done,
                t.project_id,
                t.project_title,
                t.project_area,
                t.parent_id,
                t.recurrence_kind,
                t.recurrence_interval,
                t.completion_delay_minutes,
            )
            for t in tasks
        ]
        self._prune_state()
        self._rebuild()

    def refresh(self) -> None:
        """Перезагружает данные задач из базы."""
        self._reload_from_db()

    def _prune_state(self) -> None:
        """Очищает локальные состояния раскрытия для удаленных задач."""
        task_ids = {it.id for it in self._all_rows if isinstance(it, TaskRow)}
        self._expanded_task_ids &= task_ids
        self._collapsed_subtask_ids &= task_ids
        self._subtask_state_initialized &= task_ids

    def rowCount(self, parent=QModelIndex()) -> int:
        """Возвращает количество строк с учетом фильтрации."""
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int):
        """Отдает данные для делегата в зависимости от роли."""
        if not index.isValid():
            return None
        r = self._rows[index.row()]

        if role == TaskRoles.RowType:
            if isinstance(r, HeaderRow):
                return "header"
            if isinstance(r, SortHeaderRow):
                return "sort_header"
            return "task"

        if isinstance(r, HeaderRow):
            if role == TaskRoles.Day:
                return r.day
            if role == Qt.DisplayRole:
                return r.day.isoformat()
            return None

        if isinstance(r, SortHeaderRow):
            if role == TaskRoles.SortKey:
                return self._sort_key
            if role == TaskRoles.SortDirection:
                return "asc" if self._sort_asc else "desc"
            if role == Qt.DisplayRole:
                return "sort_header"
            return None

        if role == TaskRoles.TaskId:
            return r.id
        if role == TaskRoles.Day:
            return r.day
        if role == TaskRoles.TimeText:
            return r.time_text
        if role == TaskRoles.DisplayTime:
            return self._display_time_text(r)
        if role == TaskRoles.Title:
            return r.title
        if role == TaskRoles.Description:
            return r.description
        if role == TaskRoles.Priority:
            return r.priority
        if role == TaskRoles.Done:
            return r.done
        if role == TaskRoles.Expanded:
            return r.id in self._expanded_task_ids
        if role == TaskRoles.ProjectTitle:
            return r.project_title
        if role == TaskRoles.ProjectArea:
            return r.project_area
        if role == TaskRoles.HasSubtasks:
            return bool(self._task_children.get(r.id))
        if role == TaskRoles.SubtasksExpanded:
            return r.id not in self._collapsed_subtask_ids
        if role == TaskRoles.SubtaskDepth:
            return self._task_depths.get(r.id, 0)
        if role == TaskRoles.AttachmentSummary:
            return self._attachment_summary(r.id)
        if role == TaskRoles.RecurrenceKind:
            return r.recurrence_kind
        if role == TaskRoles.CompletionDelayMinutes:
            return r.completion_delay_minutes
        if role == Qt.DisplayRole:
            return r.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Задает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.NoItemFlags
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            flags = Qt.ItemIsEnabled
            if self._drag_enabled:
                flags |= Qt.ItemIsDropEnabled
            return flags
        if isinstance(r, SortHeaderRow):
            return Qt.ItemIsEnabled
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self._drag_enabled:
            flags |= Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        return flags

    def set_filter_mode(self, mode: str):
        """Устанавливает фильтр по режиму и пересобирает список."""
        self._filter_mode = mode
        self._drag_enabled = (mode == "План")
        self._rebuild()

    def filter_mode(self) -> str:
        """Возвращает текущий режим фильтра."""
        return self._filter_mode

    def set_search(self, text: str):
        """Обновляет строку поиска и пересобирает список."""
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_focus_day(self, d: Optional[date]):
        """Фиксирует конкретный день для отображения задач."""
        self._focus_day = d
        self._rebuild()

    def set_project_filter(self, project_id: Optional[int]):
        """Устанавливает фильтр по проекту."""
        self._project_filter_id = project_id
        self._rebuild()

    def set_priority_filter(self, priority: Optional[str]):
        """Устанавливает фильтр по приоритету."""
        self._priority_filter = priority
        self._rebuild()

    def add_task(
        self,
        title: str,
        day: date,
        time_text: str,
        priority: str,
        description: str = "",
        project_id: Optional[int] = None,
        recurrence_kind: str = "",
        recurrence_interval: int = 1,
    ):
        """Добавляет новую задачу и пересобирает текущий список."""
        task = self._db.create_task(
            title=title,
            description=description,
            day=day,
            time_text=time_text,
            priority=priority,
            project_id=project_id,
            parent_id=None,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
        )
        self._all_rows.append(
            TaskRow(
                task.id,
                task.day,
                task.time_text,
                task.title,
                task.description,
                task.priority,
                task.done,
                task.project_id,
                task.project_title,
                task.project_area,
                task.parent_id,
                task.recurrence_kind,
                task.recurrence_interval,
            )
        )
        self._rebuild()

    def set_sort(self, key: str):
        """Устанавливает сортировку для режима «Все»."""
        if key == self._sort_key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_key = key
            self._sort_asc = True
        self._rebuild()

    def task_at_row(self, row_idx: int) -> Optional[TaskRow]:
        """Возвращает задачу по индексу строки или None."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return None
        r = self._rows[row_idx]
        if isinstance(r, (HeaderRow, SortHeaderRow)):
            return None
        return r

    def update_task_by_row(
        self,
        row_idx: int,
        title: str,
        description: str,
        day: date,
        time_text: str,
        priority: str,
        done: bool,
        project_id: Optional[int],
        recurrence_kind: str,
        recurrence_interval: int,
    ):
        """Обновляет задачу по индексу строки."""
        r = self.task_at_row(row_idx)
        if r is None:
            return
        updated = self._db.update_task(
            task_id=r.id,
            title=title,
            description=description,
            day=day,
            time_text=time_text,
            priority=priority,
            done=done,
            project_id=project_id,
            parent_id=r.parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
        )
        priority_changed = r.priority != updated.priority
        cascade_needed = (
            (r.priority == "Отложенная" and updated.priority != "Отложенная")
            or (r.priority != "Отложенная" and updated.priority == "Отложенная")
        )
        if priority_changed and cascade_needed:
            self._reload_from_db()
            return

        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == r.id:
                it = TaskRow(
                    updated.id,
                    updated.day,
                    updated.time_text,
                    updated.title,
                    updated.description,
                    updated.priority,
                    updated.done,
                    updated.project_id,
                    updated.project_title,
                    updated.project_area,
                    updated.parent_id,
                    updated.recurrence_kind,
                    updated.recurrence_interval,
                )
            new_all.append(it)

        self._all_rows = new_all
        self._rebuild()

    def toggle_done_by_row(self, row_idx: int):
        """Переключает статус выполнения задачи по индексу строки."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, (HeaderRow, SortHeaderRow)):
            return

        new_done = not r.done
        self._db.set_task_done(r.id, new_done)
        self._reload_from_db()

    def delete_task_by_row(self, row_idx: int):
        """Удаляет задачу по индексу строки."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, (HeaderRow, SortHeaderRow)):
            return

        self._db.delete_task(r.id)
        self._reload_from_db()

    def move_task_to_day(self, task_id: int, new_day: date, parent_id=_PARENT_UNSET) -> bool:
        """Переносит задачу на новую дату."""
        task = next((it for it in self._all_rows if isinstance(it, TaskRow) and it.id == task_id), None)
        if task is None:
            return False
        if task.day == new_day and parent_id is _PARENT_UNSET:
            return False

        current_parent_id = task.parent_id if parent_id is _PARENT_UNSET else parent_id
        updated = self._db.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            day=new_day,
            time_text=task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=task.project_id,
            parent_id=current_parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
        )
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == task.id:
                it = TaskRow(
                    updated.id,
                    updated.day,
                    updated.time_text,
                    updated.title,
                    updated.description,
                    updated.priority,
                    updated.done,
                    updated.project_id,
                    updated.project_title,
                    updated.project_area,
                    updated.parent_id,
                    updated.recurrence_kind,
                    updated.recurrence_interval,
                )
            new_all.append(it)
        self._all_rows = new_all
        self._rebuild()
        return True

    def next_day_for_task(self, task: TaskRow) -> date:
        """Возвращает дату для переноса задачи на следующий рабочий день."""
        target = task.day + timedelta(days=1)
        if target.weekday() == 5:
            target += timedelta(days=2)
        elif target.weekday() == 6:
            target += timedelta(days=6)

        if self._tasks_count_on_day(target, exclude_task_id=task.id) > 4:
            target += timedelta(days=1)
        return target

    def move_task_to_parent(self, task_id: int, parent_id: Optional[int]) -> bool:
        """Переносит задачу в подзадачу или возвращает в корень."""
        task = next((it for it in self._all_rows if isinstance(it, TaskRow) and it.id == task_id), None)
        if task is None:
            return False
        if parent_id == task.id:
            return False

        parent_task = None
        if parent_id is not None:
            parent_task = next(
                (it for it in self._all_rows if isinstance(it, TaskRow) and it.id == parent_id),
                None,
            )
            if parent_task is None:
                return False
            if self._is_descendant(parent_id, task.id):
                return False

        updated = self._db.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            day=task.day,
            time_text=task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=task.project_id,
            parent_id=parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
        )
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == task.id:
                it = TaskRow(
                    updated.id,
                    updated.day,
                    updated.time_text,
                    updated.title,
                    updated.description,
                    updated.priority,
                    updated.done,
                    updated.project_id,
                    updated.project_title,
                    updated.project_area,
                    updated.parent_id,
                    updated.recurrence_kind,
                    updated.recurrence_interval,
                )
            new_all.append(it)
        self._all_rows = new_all
        self._rebuild()
        return True

    def _is_descendant(self, task_id: int, ancestor_id: int) -> bool:
        """Проверяет, является ли задача потомком другой."""
        parent_map = {
            it.id: it.parent_id for it in self._all_rows if isinstance(it, TaskRow)
        }
        current = parent_map.get(task_id)
        while current is not None:
            if current == ancestor_id:
                return True
            current = parent_map.get(current)
        return False

    def _tasks_count_on_day(self, day_value: date, exclude_task_id: Optional[int] = None) -> int:
        """Считает количество невыполненных задач на конкретный день."""
        count = 0
        for it in self._all_rows:
            if not isinstance(it, TaskRow):
                continue
            if exclude_task_id is not None and it.id == exclude_task_id:
                continue
            if it.day == day_value and not it.done:
                count += 1
        return count

    def _rebuild(self):
        """Пересобирает список задач с учетом фильтров и поиска."""
        today = date.today()

        def is_today(d: date) -> bool:
            """Проверяет, соответствует ли дата сегодняшнему дню."""
            return d == today

        search = self._search

        base_tasks: List[TaskRow] = []
        search_hits: set[int] = set()
        for it in self._all_rows:
            if not isinstance(it, TaskRow):
                continue

            if self._focus_day is not None and it.day != self._focus_day:
                continue

            if self._project_filter_id is not None and it.project_id != self._project_filter_id:
                continue

            if self._priority_filter is not None and it.priority != self._priority_filter:
                continue

            if self._filter_mode == "Сегодня":
                if not is_today(it.day):
                    continue
                if it.done:
                    continue
                if it.priority == "Отложенная":
                    continue
            elif self._filter_mode == "Все":
                if it.done:
                    continue
                if it.priority == "Отложенная":
                    continue
            elif self._filter_mode == "Выполнено":
                if not it.done:
                    continue
                if it.priority == "Отложенная":
                    continue
            elif self._filter_mode == "План":
                if it.done:
                    continue
                if it.priority == "Отложенная":
                    continue
            elif self._filter_mode == "Отложенные":
                if it.priority != "Отложенная":
                    continue

            base_tasks.append(it)
            if not search or search in it.title.lower():
                search_hits.add(it.id)

        def time_key(t: str):
            """Преобразует строку времени в ключ сортировки."""
            try:
                return datetime.strptime(t, "%H:%M").time()
            except Exception:
                return datetime.min.time()

        priority_order = {"high": 0, "medium": 1, "low": 2, "отложенная": 3}

        def sort_key(task: TaskRow):
            if self._sort_key == "title":
                return (task.title.lower(), task.day, time_key(task.time_text), task.id)
            if self._sort_key == "priority":
                if self._filter_mode == "Все":
                    return (priority_order.get(task.priority.lower(), 4), task.day, time_key(task.time_text), task.id)
                return (task.day, priority_order.get(task.priority.lower(), 4), time_key(task.time_text), task.id)
            return (task.day, time_key(task.time_text), task.id)

        task_ids = {t.id for t in base_tasks}
        children_map: dict[Optional[int], List[TaskRow]] = {}
        for task in base_tasks:
            parent_id = task.parent_id if task.parent_id in task_ids else None
            children_map.setdefault(parent_id, []).append(task)
        for parent_id, children in children_map.items():
            if parent_id is None or not children:
                continue
            if parent_id not in self._subtask_state_initialized:
                self._collapsed_subtask_ids.add(parent_id)
                self._subtask_state_initialized.add(parent_id)

        include_cache: dict[int, bool] = {}

        def should_include(task: TaskRow) -> bool:
            if not search:
                return True
            cached = include_cache.get(task.id)
            if cached is not None:
                return cached
            if task.id in search_hits:
                include_cache[task.id] = True
                return True
            for child in children_map.get(task.id, []):
                if should_include(child):
                    include_cache[task.id] = True
                    return True
            include_cache[task.id] = False
            return False

        def sorted_children(task: TaskRow) -> List[TaskRow]:
            children = [child for child in children_map.get(task.id, []) if should_include(child)]
            children.sort(key=sort_key, reverse=(self._filter_mode == "Все" and not self._sort_asc))
            return children

        new_rows: List[Row] = []
        self._task_children = {}
        self._task_depths = {}

        def append_task(task: TaskRow, depth: int) -> None:
            self._task_depths[task.id] = depth
            children = sorted_children(task)
            if children:
                self._task_children[task.id] = children
            new_rows.append(task)
            if task.id in self._collapsed_subtask_ids:
                return
            for child in children:
                append_task(child, depth + 1)

        if self._filter_mode == "Все":
            new_rows.append(SortHeaderRow())
            roots = [t for t in children_map.get(None, []) if should_include(t)]
            roots.sort(key=sort_key, reverse=not self._sort_asc)
            for root_task in roots:
                append_task(root_task, 0)
        else:
            current_day: Optional[date] = None
            roots = [t for t in children_map.get(None, []) if should_include(t)]
            roots.sort(key=sort_key)
            if self._filter_mode == "Выполнено":
                # Показываем свежие завершенные дни сверху, сохраняя порядок задач внутри дня.
                roots.sort(key=lambda task: task.day, reverse=True)
            for task in roots:
                if current_day != task.day:
                    current_day = task.day
                    new_rows.append(HeaderRow(current_day))
                append_task(task, 0)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()

    def _display_time_text(self, task: TaskRow) -> str:
        """Формирует отображаемое время с учетом режима."""
        if self._filter_mode == "Все":
            if task.time_text:
                return f"{task.time_text} · {task.day.isoformat()}"
            return task.day.isoformat()
        return task.time_text

    def _attachment_summary(self, task_id: int) -> List[str]:
        attachments = self._db.fetch_task_attachments(task_id)
        if not attachments:
            return []
        counts: Dict[str, int] = {}
        for attachment in attachments:
            counts[attachment.kind] = counts.get(attachment.kind, 0) + 1
        ordered = [kind for kind in ATTACHMENT_KIND_ORDER if kind in counts]
        ordered.extend(kind for kind in counts.keys() if kind not in ATTACHMENT_KIND_ORDER)
        summary = []
        for kind in ordered:
            label = attachment_kind_label(kind)
            count = counts[kind]
            if count > 1:
                summary.append(f"{label} ×{count}")
            else:
                summary.append(label)
        return summary

    def toggle_expanded_by_row(self, row_idx: int) -> None:
        """Переключает раскрытие задачи по индексу строки."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        if task.id in self._expanded_task_ids:
            self._expanded_task_ids.remove(task.id)
        else:
            self._expanded_task_ids.add(task.id)
        idx = self.index(row_idx)
        if idx.isValid():
            self.dataChanged.emit(idx, idx, [TaskRoles.Expanded, Qt.SizeHintRole])

    def toggle_subtasks_expanded_by_row(self, row_idx: int) -> None:
        """Переключает раскрытие списка подзадач."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        if task.id in self._collapsed_subtask_ids:
            self._collapsed_subtask_ids.remove(task.id)
        else:
            self._collapsed_subtask_ids.add(task.id)
        self._rebuild()

    def mimeTypes(self) -> List[str]:
        """Возвращает поддерживаемые типы данных для drag and drop."""
        return ["application/x-mindnavigator-task-id"]

    def mimeData(self, indexes) -> QMimeData:
        """Создает mime-данные для перетаскивания задачи."""
        mime_data = QMimeData()
        if not indexes:
            return mime_data
        idx = indexes[0]
        task = self.task_at_row(idx.row())
        if task is None:
            return mime_data
        mime_data.setData("application/x-mindnavigator-task-id", str(task.id).encode("utf-8"))
        return mime_data

    def supportedDropActions(self) -> Qt.DropActions:
        """Разрешает перенос с изменением позиции."""
        return Qt.MoveAction

    def dropMimeData(self, data, action, row, column, parent) -> bool:
        """Обрабатывает перенос задачи между днями."""
        if action == Qt.IgnoreAction:
            return True
        if not self._drag_enabled:
            return False
        if not data.hasFormat("application/x-mindnavigator-task-id"):
            return False

        task_id_bytes = data.data("application/x-mindnavigator-task-id")
        try:
            task_id = int(bytes(task_id_bytes).decode("utf-8"))
        except ValueError:
            return False

        target_row = row
        if target_row < 0 and parent.isValid():
            target_row = parent.row()
        if target_row < 0:
            target_row = len(self._rows) - 1

        if target_row < 0 or target_row >= len(self._rows):
            return False

        target_item = self._rows[target_row]
        if isinstance(target_item, TaskRow):
            return self.move_task_to_parent(task_id, target_item.id)
        if isinstance(target_item, HeaderRow):
            return self.move_task_to_day(task_id, target_item.day, parent_id=None)

        target_day = self._drop_target_day(target_row)
        if target_day is None:
            return False

        return self.move_task_to_day(task_id, target_day, parent_id=None)

    def _drop_target_day(self, row_idx: int) -> Optional[date]:
        """Определяет дату для переноса по позиции drop."""
        if not self._rows:
            return None
        if row_idx >= len(self._rows):
            row_idx = len(self._rows) - 1

        for idx in range(row_idx, -1, -1):
            r = self._rows[idx]
            if isinstance(r, HeaderRow):
                return r.day
            if isinstance(r, TaskRow):
                return r.day
        return None


def collect_task_image_attachments(
    attachments: List[TaskAttachmentData],
    cloud_files_by_id: Dict[int, CloudFileData],
) -> List[CloudFileData]:
    images: List[CloudFileData] = []
    for attachment in attachments:
        if attachment.kind != "image":
            continue
        file_item = cloud_files_by_id.get(attachment.ref_id)
        if file_item and file_item.is_image:
            images.append(file_item)
    return images


class TaskImagePreviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        images: List[CloudFileData],
        start_index: int,
        cloud_root: Path,
    ) -> None:
        super().__init__(parent)
        self._images = images
        self._current_index = max(0, min(start_index, len(images) - 1))
        self._cloud_root = cloud_root
        self._pixmap_cache: Dict[str, QPixmap] = {}

        self.setObjectName("TaskImagePreview")
        self.setWindowTitle("Просмотр изображения")
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setObjectName("TaskImagePreviewLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label, 1)

        self.setStyleSheet(
            """
            QDialog#TaskImagePreview {
                background: #0f1115;
            }
            QLabel#TaskImagePreviewLabel {
                color: #9aa0a6;
            }
            """
        )

        self._update_image()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Left:
            self._show_previous()
            return
        if event.key() == Qt.Key_Right:
            self._show_next()
            return
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_pixmap()

    def _show_previous(self) -> None:
        if not self._images:
            return
        self._current_index = max(0, self._current_index - 1)
        self._update_image()

    def _show_next(self) -> None:
        if not self._images:
            return
        self._current_index = min(len(self._images) - 1, self._current_index + 1)
        self._update_image()

    def _update_image(self) -> None:
        if not self._images:
            self.setWindowTitle("Просмотр изображения")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображения отсутствуют")
            return

        current = self._images[self._current_index]
        self.setWindowTitle(f"{current.name} ({self._current_index + 1}/{len(self._images)})")
        file_path = self._cloud_root / current.rel_path
        if not file_path.is_file():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображение недоступно")
            return

        cache_key = current.rel_path
        pixmap = self._pixmap_cache.get(cache_key)
        if pixmap is None:
            pixmap = QPixmap(str(file_path))
            self._pixmap_cache[cache_key] = pixmap
        self._update_pixmap(pixmap)

    def _update_pixmap(self, pixmap: Optional[QPixmap] = None) -> None:
        if pixmap is None:
            current = self._images[self._current_index] if self._images else None
            if not current:
                return
            pixmap = self._pixmap_cache.get(current.rel_path)
        if not pixmap or pixmap.isNull():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображение недоступно")
            return
        target_size = self.image_label.size()
        scaled = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")


class TaskDetailsDialog(QDialog):
    def __init__(self, task: TaskRow, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Подробности задачи")
        self.setObjectName("TaskDetailsDialog")
        self.setMinimumWidth(760)
        self.setMinimumHeight(680)

        self._db = get_database()
        self._task = task
        self._attachments: List = []
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._maps_by_id = {}
        self._markers_by_id = {}
        self._cloud_files_by_id = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_label = QLabel(task.title)
        title_label.setObjectName("TaskDetailsTitle")
        status_label = QLabel("Выполнено" if task.done else "В работе")
        status_label.setObjectName("TaskDetailsStatus")
        header.addWidget(title_label, 1)
        header.addWidget(status_label)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("TaskDetailsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QFrame()
        content.setObjectName("TaskDetailsContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        desc_block = QFrame()
        desc_block.setObjectName("TaskDetailsDescription")
        desc_layout = QVBoxLayout(desc_block)
        desc_layout.setContentsMargins(14, 12, 14, 12)
        desc_title = QLabel("Описание")
        desc_title.setObjectName("TaskDetailsSectionTitle")
        desc_text = QLabel(_linkify_description_text(task.description))
        desc_text.setWordWrap(True)
        desc_text.setTextFormat(Qt.RichText)
        desc_text.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.TextSelectableByMouse)
        desc_text.setOpenExternalLinks(True)
        desc_layout.addWidget(desc_title)
        desc_layout.addWidget(desc_text)
        content_layout.addWidget(desc_block)

        props_block = QFrame()
        props_block.setObjectName("TaskDetailsProps")
        props_layout = QVBoxLayout(props_block)
        props_layout.setContentsMargins(14, 12, 14, 12)
        props_title = QLabel("Свойства")
        props_title.setObjectName("TaskDetailsSectionTitle")
        props_layout.addWidget(props_title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)

        time_text = task.time_text or "—"
        project_text = "—"
        if task.project_title:
            project_text = f"{task.project_area} · {task.project_title}" if task.project_area else task.project_title
        parent_title = "—"
        if task.parent_id is not None:
            parent_title = self._task_title(task.parent_id)
        recurrence_text = "—"
        if task.recurrence_kind:
            labels = {"daily": "Ежедневно", "weekly": "Еженедельно", "monthly": "Ежемесячно"}
            base = labels.get(task.recurrence_kind, task.recurrence_kind)
            if task.recurrence_interval > 1:
                recurrence_text = f"{base}, интервал {task.recurrence_interval}"
            else:
                recurrence_text = base

        form.addRow("ID", QLabel(str(task.id)))
        form.addRow("Дата", QLabel(task.day.isoformat()))
        form.addRow("Время", QLabel(time_text))
        form.addRow("Приоритет", QLabel(task.priority or "—"))
        form.addRow("Статус", QLabel("Выполнено" if task.done else "В работе"))
        form.addRow("Проект", QLabel(project_text))
        form.addRow("Родитель", QLabel(parent_title))
        form.addRow("Повтор", QLabel(recurrence_text))
        props_layout.addLayout(form)
        content_layout.addWidget(props_block)

        attachments_block = QFrame()
        attachments_block.setObjectName("TaskDetailsAttachments")
        attachments_layout = QVBoxLayout(attachments_block)
        attachments_layout.setContentsMargins(14, 12, 14, 12)
        attachments_layout.setSpacing(10)

        attachments_title = QLabel("Вложения")
        attachments_title.setObjectName("TaskDetailsSectionTitle")
        attachments_layout.addWidget(attachments_title)

        self.attachments_list = QVBoxLayout()
        self.attachments_list.setSpacing(6)
        attachments_layout.addLayout(self.attachments_list)
        content_layout.addWidget(attachments_block)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh_attachments()

        self.setStyleSheet(f"""
            QDialog#TaskDetailsDialog {{
                {MATH_PHYS_BACKGROUND}
                border: 1px solid #25272c;
                border-radius: 12px;
            }}
            QDialog#TaskDetailsDialog QLabel {{
                color: #cfcfcf;
            }}
            QLabel#TaskDetailsTitle {{
                color: #f2f2f2;
                font-size: 22px;
                font-weight: 600;
            }}
            QLabel#TaskDetailsStatus {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 12px;
                padding: 6px 12px;
                color: #d8d8d8;
            }}
            QLabel#TaskDetailsSectionTitle {{
                color: #f2f2f2;
                font-weight: 600;
            }}
            QScrollArea#TaskDetailsScroll {{
                background: transparent;
            }}
            QScrollArea#TaskDetailsScroll QWidget {{
                background: transparent;
            }}
            QFrame#TaskDetailsContent {{
                background: transparent;
            }}
            QFrame#TaskDetailsDescription,
            QFrame#TaskDetailsProps,
            QFrame#TaskDetailsAttachments {{
                background: #1c1d22;
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }}
            QFrame#TaskDetailsAttachments QFrame#TaskAttachmentRow {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}
            QDialog#TaskDetailsDialog QLabel#TaskAttachmentKind {{
                color: #cfcfcf;
            }}
            QDialog#TaskDetailsDialog QLabel#TaskAttachmentLink {{
                color: #6ab7ff;
            }}
            QDialog#TaskDetailsDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 8px;
            }}
            QDialog#TaskDetailsDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _task_title(self, task_id: int) -> str:
        tasks = self._db.fetch_tasks()
        for task in tasks:
            if task.id == task_id:
                return task.title
        return "—"

    def _load_attachment_sources(self) -> None:
        notes = self._db.fetch_notes()
        objects = self._db.fetch_objects()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        cloud_files = self._db.fetch_cloud_files()
        self._notes_by_id = {note.id: note for note in notes}
        self._objects_by_id = {item.id: item for item in objects}
        self._maps_by_id = {item.id: item for item in maps}
        self._markers_by_id = {item.id: item for item in markers}
        self._cloud_files_by_id = {item.id: item for item in cloud_files}

    def _refresh_attachments(self) -> None:
        self._load_attachment_sources()
        self._attachments = self._db.fetch_task_attachments(self._task.id)
        self._clear_layout(self.attachments_list)
        if not self._attachments:
            empty = QLabel("Нет вложений")
            empty.setStyleSheet("color: #8a8a8a;")
            self.attachments_list.addWidget(empty)
            return
        for attachment in self._attachments:
            row = QFrame()
            row.setObjectName("TaskAttachmentRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)

            kind_label = QLabel(attachment_kind_label(attachment.kind))
            kind_label.setObjectName("TaskAttachmentKind")
            link_text = self._attachment_display_text(attachment)
            link_label = QLabel(f"<a href='{attachment.id}'>{link_text}</a>")
            link_label.setObjectName("TaskAttachmentLink")
            link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            link_label.setOpenExternalLinks(False)
            link_label.linkActivated.connect(lambda _link, att=attachment: self._open_attachment(att))

            row_layout.addWidget(kind_label)
            row_layout.addWidget(link_label, 1)
            self.attachments_list.addWidget(row)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _cloud_file_link_text(self, file_item) -> str:
        description = (file_item.description or "").strip()
        if description:
            try:
                payload = json.loads(description)
            except json.JSONDecodeError:
                return description
            if isinstance(payload, dict):
                text = (payload.get("text") or "").strip()
                if text:
                    return text
        return file_item.name

    def _attachment_display_text(self, attachment) -> str:
        if attachment.kind == "note":
            note = self._notes_by_id.get(attachment.ref_id)
            return note.title if note else "Заметка не найдена"
        if attachment.kind == "object":
            obj = self._objects_by_id.get(attachment.ref_id)
            return obj.title if obj else "Объект не найден"
        if attachment.kind == "map":
            map_item = self._maps_by_id.get(attachment.ref_id)
            return map_item.title if map_item else "Карта не найдена"
        if attachment.kind == "marker":
            marker = self._markers_by_id.get(attachment.ref_id)
            if not marker:
                return "Метка не найдена"
            map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else ""
            if map_title:
                return f"{marker.name} · {map_title}"
            return marker.name
        if attachment.kind in {"file", "image"}:
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            return self._cloud_file_link_text(file_item) if file_item else "Файл не найден"
        return "Вложение"

    def _open_attachment(self, attachment) -> None:
        if attachment.kind == "image":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Вложения", "Файл изображения не найден.")
                return
            self._open_image_preview(file_item)
            return
        if attachment.kind == "file":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Вложения", "Файл не найден.")
                return
            self._open_file_info(file_item)
            return
        if attachment.kind == "note":
            note = self._notes_by_id.get(attachment.ref_id)
            if not note:
                QMessageBox.warning(self, "Вложения", "Заметка не найдена.")
                return
            rows = [
                ("Название", note.title),
                ("Проект", note.project or "—"),
                ("Обновлено", note.updated.strftime("%d.%m.%Y %H:%M")),
                ("Теги", ", ".join(note.tags) if note.tags else "—"),
                ("Избранное", "Да" if note.favorite else "Нет"),
                ("Вложения", "Да" if note.attachment else "Нет"),
                ("Описание", note.preview or "—"),
            ]
            self._open_info_dialog("Заметка", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "object":
            obj = self._objects_by_id.get(attachment.ref_id)
            if not obj:
                QMessageBox.warning(self, "Вложения", "Объект не найден.")
                return
            rows = [
                ("Название", obj.title),
                ("Каталог", obj.catalog or "—"),
                ("Тип", obj.object_type or "—"),
                ("Статус", obj.status or "—"),
                ("Создан", obj.created_at or "—"),
                ("Обновлен", obj.updated_at or "—"),
                ("Описание", obj.description or "—"),
            ]
            self._open_info_dialog("Объект", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "map":
            map_item = self._maps_by_id.get(attachment.ref_id)
            if not map_item:
                QMessageBox.warning(self, "Вложения", "Карта не найдена.")
                return
            rows = [
                ("Название", map_item.title),
                ("Проект", map_item.project or "—"),
                ("Описание", map_item.description or "—"),
                ("Тайлы", f"{map_item.tiles_w} × {map_item.tiles_h}"),
            ]
            self._open_info_dialog("Карта", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "marker":
            marker = self._markers_by_id.get(attachment.ref_id)
            if not marker:
                QMessageBox.warning(self, "Вложения", "Метка не найдена.")
                return
            map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else "—"
            rows = [
                ("Название", marker.name),
                ("Карта", map_title),
                ("Тип", marker.type),
                ("Координаты", f"{marker.x:.0f}, {marker.y:.0f}"),
                ("Описание", marker.description or "—"),
                ("Свойства", marker.properties or "—"),
            ]
            self._open_info_dialog("Метка карты", rows, wrap_rows={"Описание", "Свойства"})

    def _open_info_dialog(self, title: str, rows: List[Tuple[str, str]], wrap_rows: Optional[Set[str]] = None) -> None:
        dialog = QDialog(self)
        dialog.setObjectName("TaskAttachmentInfoDialog")
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        wrap_rows = wrap_rows or set()
        for label, value in rows:
            value_label = QLabel(value or "—")
            if label in wrap_rows:
                value_label.setWordWrap(True)
            form.addRow(label, value_label)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setStyleSheet(f"""
            QDialog#TaskAttachmentInfoDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#TaskAttachmentInfoDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#TaskAttachmentInfoDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)
        show_dialog_standard(dialog, self)

    def _open_file_info(self, file_item) -> None:
        description = self._cloud_file_link_text(file_item)
        rows = [
            ("Название", file_item.name),
            ("Путь", file_item.rel_path),
            ("Описание", description),
            ("Размер", f"{file_item.size} байт"),
        ]
        self._open_info_dialog("Файл", rows, wrap_rows={"Путь", "Описание"})

    def _open_image_preview(self, file_item) -> None:
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "Изображение", "Папка облачного хранилища не настроена.")
            return
        images = collect_task_image_attachments(self._attachments, self._cloud_files_by_id)
        if not images:
            QMessageBox.warning(self, "Изображение", "Привязанные изображения не найдены.")
            return
        try:
            start_index = next(idx for idx, item in enumerate(images) if item.id == file_item.id)
        except StopIteration:
            start_index = 0
        dialog = TaskImagePreviewDialog(
            self,
            images=images,
            start_index=start_index,
            cloud_root=Path(cloud_root),
        )
        show_dialog_standard(dialog, self)


class TaskEditDialog(QDialog):
    _SIZE_SETTING_KEY = "ui.task_edit_dialog_size"

    def __init__(self, task: TaskRow, parent=None):
        """Создает диалог редактирования задачи."""
        super().__init__(parent)
        self.setWindowTitle("Редактирование задачи")
        self.setObjectName("TaskEditDialog")
        self.setProperty("dialog_category", "keep_size")
        self.setMinimumWidth(460)
        self.setMinimumHeight(420)
        self._db = get_database()
        self._restore_saved_size()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Редактирование задачи")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit(task.title)
        self.title_edit.setPlaceholderText("Название задачи")

        self.description_edit = QPlainTextEdit(task.description)
        self.description_edit.setPlaceholderText("Описание задачи")
        self.description_edit.setMinimumHeight(90)

        self.project_edit = QComboBox()
        self._populate_projects(task.project_id)

        self.project_create_btn = QToolButton()
        self.project_create_btn.setText("+")
        self.project_create_btn.setFixedSize(24, 24)
        self.project_create_btn.setCursor(Qt.PointingHandCursor)
        self.project_create_btn.setToolTip("Создать проект")
        self.project_create_btn.clicked.connect(self._open_project_create_dialog)

        project_row = QWidget()
        project_row_layout = QHBoxLayout(project_row)
        project_row_layout.setContentsMargins(0, 0, 0, 0)
        project_row_layout.setSpacing(6)
        project_row_layout.addWidget(self.project_create_btn)
        project_row_layout.addWidget(self.project_edit, 1)

        self.day_edit = QDateEdit()
        self.day_edit.setCalendarPopup(True)
        self.day_edit.setDisplayFormat("yyyy-MM-dd")
        self.day_edit.setDate(task.day)
        self.day_edit.setKeyboardTracking(False)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(9, 0))
        self.time_edit.setKeyboardTracking(False)

        self.time_toggle = QCheckBox("Указать")
        self.time_toggle.setCursor(Qt.PointingHandCursor)

        if task.time_text:
            try:
                parsed = datetime.strptime(task.time_text, "%H:%M").time()
                self.time_edit.setTime(QTime(parsed.hour, parsed.minute))
                self.time_toggle.setChecked(True)
            except Exception:
                self.time_toggle.setChecked(False)
        else:
            self.time_toggle.setChecked(False)

        self.time_edit.setEnabled(self.time_toggle.isChecked())
        self.time_toggle.toggled.connect(self.time_edit.setEnabled)

        time_block = QFrame()
        time_block.setObjectName("TaskDateTimeBlock")
        time_block_layout = QHBoxLayout(time_block)
        time_block_layout.setContentsMargins(8, 4, 8, 4)
        time_block_layout.setSpacing(6)
        time_block_layout.addWidget(self.day_edit)
        time_block_layout.addWidget(self.time_toggle)
        time_block_layout.addWidget(self.time_edit)

        self.recurrence_toggle = QCheckBox("По расписанию")
        self.recurrence_toggle.setCursor(Qt.PointingHandCursor)
        self.recurrence_type_edit = QComboBox()
        self.recurrence_type_edit.addItem("Ежедневно", "daily")
        self.recurrence_type_edit.addItem("Еженедельно", "weekly")
        self.recurrence_type_edit.addItem("Ежемесячно", "monthly")
        recurrence_idx = self.recurrence_type_edit.findData(task.recurrence_kind)
        if recurrence_idx >= 0:
            self.recurrence_type_edit.setCurrentIndex(recurrence_idx)
        self.recurrence_toggle.setChecked(bool(task.recurrence_kind))
        self.recurrence_type_edit.setEnabled(self.recurrence_toggle.isChecked())
        self.recurrence_toggle.toggled.connect(self.recurrence_type_edit.setEnabled)

        recurrence_row = QWidget()
        recurrence_layout = QHBoxLayout(recurrence_row)
        recurrence_layout.setContentsMargins(0, 0, 0, 0)
        recurrence_layout.setSpacing(6)
        recurrence_layout.addWidget(self.recurrence_toggle)
        recurrence_layout.addWidget(self.recurrence_type_edit, 1)

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["Low", "Medium", "High", "Отложенная"])
        self.priority_edit.setCurrentText(task.priority or "Medium")

        self.done_edit = QCheckBox("Выполнено")
        self.done_edit.setChecked(task.done)

        form.addRow("Название", self.title_edit)
        form.addRow("Описание", self.description_edit)
        form.addRow("Проект", project_row)
        form.addRow("Дата и время", time_block)
        form.addRow("Повтор", recurrence_row)
        form.addRow("Приоритет", self.priority_edit)
        form.addRow("", self.done_edit)

        layout.addLayout(form)

        self._task_id = task.id
        self._attachments: List = []
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._maps_by_id = {}
        self._markers_by_id = {}
        self._cloud_files_by_id = {}

        attachments_frame = QFrame()
        attachments_frame.setObjectName("TaskAttachments")
        attachments_layout = QVBoxLayout(attachments_frame)
        attachments_layout.setContentsMargins(12, 10, 12, 10)
        attachments_layout.setSpacing(8)

        attachments_header = QHBoxLayout()
        attachments_title = QLabel("Вложения")
        attachments_title.setObjectName("TaskAttachmentsTitle")
        self.attachments_add_btn = QToolButton()
        self.attachments_add_btn.setText("Добавить")
        self.attachments_add_btn.setCursor(Qt.PointingHandCursor)
        self.attachments_add_btn.clicked.connect(self._open_attachment_dialog)
        attachments_header.addWidget(attachments_title)
        attachments_header.addStretch(1)
        attachments_header.addWidget(self.attachments_add_btn)
        attachments_layout.addLayout(attachments_header)

        self.attachments_list = QVBoxLayout()
        self.attachments_list.setSpacing(6)
        attachments_layout.addLayout(self.attachments_list)
        layout.addWidget(attachments_frame)

        self._load_attachment_sources()
        self._refresh_attachments()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_accept)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_accept)

        self.setStyleSheet(f"""
            QDialog#TaskEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#TaskEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#TaskEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#TaskEditDialog QLineEdit,
            QDialog#TaskEditDialog QPlainTextEdit,
            QDialog#TaskEditDialog QComboBox,
            QDialog#TaskEditDialog QDateEdit,
            QDialog#TaskEditDialog QTimeEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#TaskEditDialog QPlainTextEdit {{
                padding: 8px 10px;
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QDateEdit,
            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QTimeEdit {{
                background: transparent;
                border: none;
                padding: 6px 6px;
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QCheckBox {{
                color: #cfcfcf;
                padding: 0 6px;
            }}

            QDialog#TaskEditDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView {{
                background: #1c1d22;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                selection-background-color: #2f3238;
                selection-color: #f2f2f2;
                outline: none;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView::item {{
                padding: 6px 10px;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView::item:selected {{
                background: #2f3238;
                color: #f2f2f2;
            }}

            QDialog#TaskEditDialog QCheckBox {{
                color: #cfcfcf;
                padding: 4px 0;
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}

            QDialog#TaskEditDialog QToolButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
            }}

            QDialog#TaskEditDialog QToolButton:hover {{
                background: #34363b;
            }}

            QDialog#TaskEditDialog QFrame#TaskAttachments {{
                background: #1c1d22;
                border: 1px solid #2a2b2f;
                border-radius: 8px;
            }}

            QDialog#TaskEditDialog QLabel#TaskAttachmentsTitle {{
                color: #f2f2f2;
                font-weight: 600;
            }}

            QDialog#TaskEditDialog QFrame#TaskAttachmentRow {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}

            QDialog#TaskEditDialog QLabel#TaskAttachmentKind {{
                color: #cfcfcf;
            }}

            QDialog#TaskEditDialog QLabel#TaskAttachmentLink {{
                color: #6ab7ff;
            }}

            QDialog#TaskEditDialog QToolButton#TaskAttachmentRemove {{
                background: transparent;
                border: none;
                padding: 4px;
            }}
        """)

    def _restore_saved_size(self) -> None:
        raw = self._db.get_setting(self._SIZE_SETTING_KEY, default="").strip()
        if not raw:
            return
        width_str, separator, height_str = raw.partition("x")
        if not separator:
            return
        try:
            width = int(width_str)
            height = int(height_str)
        except ValueError:
            return
        self.resize(max(width, self.minimumWidth()), max(height, self.minimumHeight()))

    def _save_current_size(self) -> None:
        size = self.size()
        self._db.set_setting(self._SIZE_SETTING_KEY, f"{size.width()}x{size.height()}")

    def closeEvent(self, event) -> None:
        self._save_current_size()
        super().closeEvent(event)

    def _populate_projects(self, selected_id: Optional[int] = None) -> None:
        self.project_edit.blockSignals(True)
        self.project_edit.clear()
        self.project_edit.addItem("Без проекта", None)
        projects = get_database().fetch_projects()
        projects_by_id = {project.id: project for project in projects}
        title_cache: Dict[int, str] = {}

        def full_title(project_id: int, seen: Optional[set[int]] = None) -> str:
            cached = title_cache.get(project_id)
            if cached is not None:
                return cached
            project = projects_by_id.get(project_id)
            if project is None:
                return ""
            seen_set = seen or set()
            if project_id in seen_set:
                title_cache[project_id] = project.title
                return project.title
            if project.parent_project_id is None:
                title_cache[project_id] = project.title
                return project.title
            parent_title = full_title(project.parent_project_id, seen_set | {project_id})
            resolved = f"{parent_title} / {project.title}" if parent_title else project.title
            title_cache[project_id] = resolved
            return resolved
        priority_order = {"High": 0, "Medium": 1, "Low": 2, "Отложенная": 3}
        projects.sort(
            key=lambda project: (
                project.area.lower(),
                priority_order.get(normalize_priority(project.priority), 4),
                full_title(project.id).lower(),
                project.id,
            )
        )
        for project in projects:
            if project.archived:
                continue
            title = full_title(project.id)
            self.project_edit.addItem(f"{project.area} · {title}", project.id)
        if selected_id is not None:
            idx = self.project_edit.findData(selected_id)
            if idx >= 0:
                self.project_edit.setCurrentIndex(idx)
        self.project_edit.blockSignals(False)

    def _open_project_create_dialog(self) -> None:
        dialog = QuickProjectCreateDialog(parent=self)
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        values = dialog.values()
        try:
            created = get_database().create_project(
                area=values["area"],
                title=values["title"],
                updated=values["updated"],
                priority=values["priority"],
                archived=False,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self._populate_projects(created.id)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Проверка", "Введите название задачи.")
            return
        time_text = self._current_time_text()
        try:
            validate_time_text(time_text)
            normalize_priority(self.priority_edit.currentText())
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self.accept()

    def _current_time_text(self) -> str:
        if not self.time_toggle.isChecked():
            return ""
        return self.time_edit.time().toString("HH:mm")

    def _load_attachment_sources(self) -> None:
        notes = self._db.fetch_notes()
        objects = self._db.fetch_objects()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        cloud_files = self._db.fetch_cloud_files()
        self._notes_by_id = {note.id: note for note in notes}
        self._objects_by_id = {item.id: item for item in objects}
        self._maps_by_id = {item.id: item for item in maps}
        self._markers_by_id = {item.id: item for item in markers}
        self._cloud_files_by_id = {item.id: item for item in cloud_files}

    def _refresh_attachments(self) -> None:
        self._load_attachment_sources()
        self._attachments = self._db.fetch_task_attachments(self._task_id)
        self._clear_layout(self.attachments_list)
        if not self._attachments:
            empty = QLabel("Нет вложений")
            empty.setStyleSheet("color: #8a8a8a;")
            self.attachments_list.addWidget(empty)
            return
        for attachment in self._attachments:
            row = QFrame()
            row.setObjectName("TaskAttachmentRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)

            kind_label = QLabel(self._attachment_kind_label(attachment.kind))
            kind_label.setObjectName("TaskAttachmentKind")
            link_text = self._attachment_display_text(attachment)
            link_label = QLabel(f"<a href='{attachment.id}'>{link_text}</a>")
            link_label.setObjectName("TaskAttachmentLink")
            link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            link_label.setOpenExternalLinks(False)
            link_label.linkActivated.connect(lambda _link, att=attachment: self._open_attachment(att))

            remove_btn = QToolButton()
            remove_btn.setObjectName("TaskAttachmentRemove")
            remove_btn.setIcon(qta.icon("fa5s.times", color="#cfcfcf"))
            remove_btn.setCursor(Qt.PointingHandCursor)
            remove_btn.clicked.connect(lambda _checked=False, att=attachment: self._remove_attachment(att))

            row_layout.addWidget(kind_label)
            row_layout.addWidget(link_label, 1)
            row_layout.addWidget(remove_btn)
            self.attachments_list.addWidget(row)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _attachment_kind_label(self, kind: str) -> str:
        return attachment_kind_label(kind)

    def _cloud_file_link_text(self, file_item) -> str:
        description = (file_item.description or "").strip()
        if description:
            try:
                payload = json.loads(description)
            except json.JSONDecodeError:
                return description
            if isinstance(payload, dict):
                text = (payload.get("text") or "").strip()
                if text:
                    return text
        return file_item.name

    def _attachment_display_text(self, attachment) -> str:
        if attachment.kind == "note":
            note = self._notes_by_id.get(attachment.ref_id)
            return note.title if note else "Заметка не найдена"
        if attachment.kind == "object":
            obj = self._objects_by_id.get(attachment.ref_id)
            return obj.title if obj else "Объект не найден"
        if attachment.kind == "map":
            map_item = self._maps_by_id.get(attachment.ref_id)
            return map_item.title if map_item else "Карта не найдена"
        if attachment.kind == "marker":
            marker = self._markers_by_id.get(attachment.ref_id)
            if not marker:
                return "Метка не найдена"
            map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else ""
            if map_title:
                return f"{marker.name} · {map_title}"
            return marker.name
        if attachment.kind in {"file", "image"}:
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            return self._cloud_file_link_text(file_item) if file_item else "Файл не найден"
        return "Вложение"

    def _open_attachment_dialog(self) -> None:
        self._load_attachment_sources()
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить вложение")
        dialog.setObjectName("TaskAttachmentDialog")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        kind_combo = QComboBox()
        kind_items = [
            ("Заметка", "note"),
            ("Объект", "object"),
            ("Карта", "map"),
            ("Метка карты", "marker"),
            ("Файл", "file"),
            ("Изображение", "image"),
        ]
        for label, key in kind_items:
            kind_combo.addItem(label, key)

        item_combo = QComboBox()

        def fill_items(kind: str) -> None:
            item_combo.clear()
            items = []
            if kind == "note":
                items = sorted(self._notes_by_id.values(), key=lambda item: item.title.lower())
                for item in items:
                    label = f"{item.title} · {item.project}" if item.project else item.title
                    item_combo.addItem(label, item.id)
            elif kind == "object":
                items = sorted(self._objects_by_id.values(), key=lambda item: item.title.lower())
                for item in items:
                    label = f"{item.title} · {item.catalog}" if item.catalog else item.title
                    item_combo.addItem(label, item.id)
            elif kind == "map":
                items = sorted(self._maps_by_id.values(), key=lambda item: item.title.lower())
                for item in items:
                    label = f"{item.title} · {item.project}" if item.project else item.title
                    item_combo.addItem(label, item.id)
            elif kind == "marker":
                markers = sorted(self._markers_by_id.values(), key=lambda item: item.name.lower())
                for marker in markers:
                    map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else ""
                    label = f"{marker.name} · {map_title}" if map_title else marker.name
                    item_combo.addItem(label, marker.id)
            elif kind in {"file", "image"}:
                files = [item for item in self._cloud_files_by_id.values() if item.is_image == (kind == "image")]
                files = sorted(files, key=lambda item: item.name.lower())
                for item in files:
                    item_combo.addItem(self._cloud_file_link_text(item), item.id)
            if item_combo.count() == 0:
                item_combo.addItem("— нет доступных —", None)

        kind_combo.currentIndexChanged.connect(lambda idx: fill_items(kind_combo.currentData()))
        fill_items(kind_combo.currentData())

        form.addRow("Тип", kind_combo)
        form.addRow("Элемент", item_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setStyleSheet(f"""
            QDialog#TaskAttachmentDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#TaskAttachmentDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#TaskAttachmentDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QDialog#TaskAttachmentDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)

        if dialog.exec() != QDialog.Accepted:
            return
        kind = kind_combo.currentData()
        ref_id = item_combo.currentData()
        if ref_id is None:
            QMessageBox.warning(self, "Вложения", "Нет доступных элементов для добавления.")
            return
        self._db.add_task_attachment(self._task_id, kind, ref_id)
        self._refresh_attachments()

    def _remove_attachment(self, attachment) -> None:
        self._db.delete_task_attachment(attachment.id)
        self._refresh_attachments()

    def _open_attachment(self, attachment) -> None:
        if attachment.kind == "image":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Вложения", "Файл изображения не найден.")
                return
            self._open_image_preview(file_item)
            return
        if attachment.kind == "file":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Вложения", "Файл не найден.")
                return
            self._open_file_info(file_item)
            return
        if attachment.kind == "note":
            note = self._notes_by_id.get(attachment.ref_id)
            if not note:
                QMessageBox.warning(self, "Вложения", "Заметка не найдена.")
                return
            rows = [
                ("Название", note.title),
                ("Проект", note.project or "—"),
                ("Обновлено", note.updated.strftime("%d.%m.%Y %H:%M")),
                ("Теги", ", ".join(note.tags) if note.tags else "—"),
                ("Избранное", "Да" if note.favorite else "Нет"),
                ("Вложения", "Да" if note.attachment else "Нет"),
                ("Описание", note.preview or "—"),
            ]
            self._open_info_dialog("Заметка", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "object":
            obj = self._objects_by_id.get(attachment.ref_id)
            if not obj:
                QMessageBox.warning(self, "Вложения", "Объект не найден.")
                return
            rows = [
                ("Название", obj.title),
                ("Каталог", obj.catalog or "—"),
                ("Тип", obj.object_type or "—"),
                ("Статус", obj.status or "—"),
                ("Создан", obj.created_at or "—"),
                ("Обновлен", obj.updated_at or "—"),
                ("Описание", obj.description or "—"),
            ]
            self._open_info_dialog("Объект", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "map":
            map_item = self._maps_by_id.get(attachment.ref_id)
            if not map_item:
                QMessageBox.warning(self, "Вложения", "Карта не найдена.")
                return
            rows = [
                ("Название", map_item.title),
                ("Проект", map_item.project or "—"),
                ("Описание", map_item.description or "—"),
                ("Тайлы", f"{map_item.tiles_w} × {map_item.tiles_h}"),
            ]
            self._open_info_dialog("Карта", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "marker":
            marker = self._markers_by_id.get(attachment.ref_id)
            if not marker:
                QMessageBox.warning(self, "Вложения", "Метка не найдена.")
                return
            map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else "—"
            rows = [
                ("Название", marker.name),
                ("Карта", map_title),
                ("Тип", marker.type),
                ("Координаты", f"{marker.x:.0f}, {marker.y:.0f}"),
                ("Описание", marker.description or "—"),
                ("Свойства", marker.properties or "—"),
            ]
            self._open_info_dialog("Метка карты", rows, wrap_rows={"Описание", "Свойства"})

    def _open_info_dialog(self, title: str, rows: List[Tuple[str, str]], wrap_rows: Optional[Set[str]] = None) -> None:
        dialog = QDialog(self)
        dialog.setObjectName("TaskAttachmentInfoDialog")
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        wrap_rows = wrap_rows or set()
        for label, value in rows:
            value_label = QLabel(value or "—")
            if label in wrap_rows:
                value_label.setWordWrap(True)
            form.addRow(label, value_label)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setStyleSheet(f"""
            QDialog#TaskAttachmentInfoDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#TaskAttachmentInfoDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#TaskAttachmentInfoDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)
        show_dialog_standard(dialog, self)

    def _open_file_info(self, file_item) -> None:
        description = self._cloud_file_link_text(file_item)
        rows = [
            ("Название", file_item.name),
            ("Путь", file_item.rel_path),
            ("Описание", description),
            ("Размер", f"{file_item.size} байт"),
        ]
        self._open_info_dialog("Файл", rows, wrap_rows={"Путь", "Описание"})

    def _open_image_preview(self, file_item) -> None:
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "Изображение", "Папка облачного хранилища не настроена.")
            return
        images = collect_task_image_attachments(self._attachments, self._cloud_files_by_id)
        if not images:
            QMessageBox.warning(self, "Изображение", "Привязанные изображения не найдены.")
            return
        try:
            start_index = next(idx for idx, item in enumerate(images) if item.id == file_item.id)
        except StopIteration:
            start_index = 0
        dialog = TaskImagePreviewDialog(
            self,
            images=images,
            start_index=start_index,
            cloud_root=Path(cloud_root),
        )
        show_dialog_standard(dialog, self)

    def values(self):
        """Возвращает текущие значения формы в виде словаря."""
        qd = self.day_edit.date()
        day = date(qd.year(), qd.month(), qd.day())
        time_text = self._current_time_text()
        return {
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "day": day,
            "time_text": time_text,
            "priority": self.priority_edit.currentText().strip() or "Medium",
            "done": self.done_edit.isChecked(),
            "project_id": self.project_edit.currentData(),
            "recurrence_kind": self.recurrence_type_edit.currentData() if self.recurrence_toggle.isChecked() else "",
            "recurrence_interval": 1,
        }


class TaskCreateDialog(TaskEditDialog):
    _SIZE_SETTING_KEY = "ui.task_create_dialog_size"

    def __init__(self, parent=None):
        task = TaskRow(
            id=0,
            day=date.today(),
            time_text="",
            title="",
            description="",
            priority="Medium",
            done=False,
            project_id=None,
            project_title="",
            project_area="",
            parent_id=None,
        )
        super().__init__(task, parent=parent)
        self.setWindowTitle("Создание задачи")
        title_labels = self.findChildren(QLabel, "DialogTitle")
        if title_labels:
            title_labels[0].setText("Создание задачи")
        self.done_edit.hide()
        attachments_frame = self.findChild(QFrame, "TaskAttachments")
        if attachments_frame is not None:
            attachments_frame.hide()
        buttons = self.findChild(QDialogButtonBox)
        if buttons is not None:
            save_button = buttons.button(QDialogButtonBox.Save)
            if save_button is not None:
                save_button.setText("Создать")
        self.title_edit.setFocus()


class TasksItemDelegate(QStyledItemDelegate):
    ROW_H = 42
    HEADER_H = 32
    TIME_W = 140
    PROJECT_W = 320
    TEXT_VPAD = 8
    TEXT_GAP = 6
    ROW_H_EXPANDED_MIN = 82
    TAG_H = 20
    TAG_PAD_X = 8
    TAG_GAP = 6
    TAG_LINE_GAP = 6

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#cfcfcf")
    C_DIM = QColor("#8a8a8a")
    C_TODAY = QColor("#f2a23a")

    C_OVERDUE = QColor("#c84b4b")
    C_HIGH = QColor("#d94f4f")
    C_MED = QColor("#d0a93e")
    C_LOW = QColor("#4caf50")
    C_DEFER = QColor("#6f7a87")

    def __init__(self, parent=None):
        """Инициализирует делегат отрисовки строк задач."""
        super().__init__(parent)
        self._icon_doc = qta.icon("fa5s.file-alt", color="#cfcfcf")
        self._icon_grip = qta.icon("fa5s.grip-lines", color="#8a8a8a")
        self._icon_menu = qta.icon("fa5s.ellipsis-v", color="#cfcfcf")
        self._icon_fire = qta.icon("fa5s.fire", color="#d0a93e")
        self._icon_tomorrow = qta.icon("ph.arrow-u-right-down-bold", color="#cfcfcf")
        self._icon_subtask_open = qta.icon("fa5s.chevron-down", color="#8a8a8a")
        self._icon_subtask_closed = qta.icon("fa5s.chevron-right", color="#8a8a8a")

        self._font = QFont()
        self._font.setPointSize(10)

        self._font_small = QFont()
        self._font_small.setPointSize(9)

        self._font_header = QFont()
        self._font_header.setPointSize(9)
        self._font_header.setBold(True)

    def sizeHint(self, option, index):
        """Возвращает размер строки списка."""
        row_type = index.data(TaskRoles.RowType)
        if row_type in ("header", "sort_header"):
            return QSize(option.rect.width(), self.HEADER_H)
        expanded = bool(index.data(TaskRoles.Expanded))
        if not expanded:
            return QSize(option.rect.width(), self.ROW_H)

        title = index.data(TaskRoles.Title) or ""
        description = index.data(TaskRoles.Description) or ""
        depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
        has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
        layout = self._row_layout(option.rect, depth, has_subtasks)
        text_width = max(10, layout["title"].width())

        title_metrics = QFontMetrics(self._font)
        desc_metrics = QFontMetrics(self._font_small)
        title_height = title_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextWordWrap, title).height()
        desc_height = 0
        if description:
            desc_height = desc_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextWordWrap, description).height()

        tags = index.data(TaskRoles.AttachmentSummary) or []
        total_height = title_height + desc_height
        if description:
            total_height += self.TEXT_GAP
        if tags:
            total_height += self.TEXT_GAP + self._tags_height(tags, text_width)
        total_height += self.TEXT_VPAD * 2
        total_height = max(total_height, self.ROW_H_EXPANDED_MIN)
        return QSize(option.rect.width(), total_height)

    def _tags_height(self, tags: List[str], max_width: int) -> int:
        if not tags:
            return 0
        metrics = QFontMetrics(self._font_small)
        line_width = 0
        lines = 1
        for tag in tags:
            tag_width = metrics.horizontalAdvance(tag) + self.TAG_PAD_X * 2
            if line_width > 0 and line_width + tag_width > max_width:
                lines += 1
                line_width = 0
            line_width += tag_width + self.TAG_GAP
        return lines * self.TAG_H + (lines - 1) * self.TAG_LINE_GAP

    def _draw_tags(self, painter: QPainter, start: QPoint, max_width: int, tags: List[str]) -> None:
        if not tags:
            return
        metrics = QFontMetrics(self._font_small)
        x = start.x()
        y = start.y()
        painter.setFont(self._font_small)
        for tag in tags:
            tag_width = metrics.horizontalAdvance(tag) + self.TAG_PAD_X * 2
            if x > start.x() and x + tag_width > start.x() + max_width:
                x = start.x()
                y += self.TAG_H + self.TAG_LINE_GAP
            rect = QRect(x, y, tag_width, self.TAG_H)
            painter.setPen(QColor("#3a3b40"))
            painter.setBrush(QColor("#1f2227"))
            painter.drawRoundedRect(rect, 8, 8)
            painter.setPen(self.C_DIM)
            painter.drawText(rect.adjusted(self.TAG_PAD_X, 0, -self.TAG_PAD_X, 0), Qt.AlignVCenter | Qt.AlignLeft, tag)
            x += tag_width + self.TAG_GAP

    def paint(self, painter: QPainter, option, index: QModelIndex):
        """Рисует строку задачи или заголовок дня."""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        row_type = index.data(TaskRoles.RowType)
        r = option.rect

        if row_type == "header":
            d: date = index.data(TaskRoles.Day)
            txt = self._format_header(d)
            model = index.model()
            is_plan = False
            if hasattr(model, "filter_mode"):
                is_plan = model.filter_mode() == "План"
            show_today = is_plan and d == date.today()
            painter.fillRect(r, self.C_BG)

            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            text_rect = r.adjusted(10, 0, -10, 0)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, txt)

            if show_today:
                metrics = QFontMetrics(self._font_header)
                base_width = metrics.horizontalAdvance(txt)
                today_rect = QRect(
                    text_rect.left() + base_width + 6,
                    text_rect.top(),
                    text_rect.width() - base_width - 6,
                    text_rect.height(),
                )
                painter.setPen(self.C_TODAY)
                painter.drawText(today_rect, Qt.AlignVCenter | Qt.AlignLeft, "СЕГОДНЯ")

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.restore()
            return
        if row_type == "sort_header":
            sort_key = index.data(TaskRoles.SortKey) or "date"
            sort_dir = index.data(TaskRoles.SortDirection) or "asc"
            arrow = "▲" if sort_dir == "asc" else "▼"
            painter.fillRect(r, self.C_BG)

            layout = self._row_layout(r)
            painter.setFont(self._font_header)
            painter.setPen(self.C_DIM)
            painter.drawText(layout["date"], Qt.AlignVCenter | Qt.AlignLeft,
                             f"Дата {arrow}" if sort_key == "date" else "Дата")
            painter.drawText(layout["title"], Qt.AlignVCenter | Qt.AlignLeft,
                             f"Название {arrow}" if sort_key == "title" else "Название")
            painter.drawText(layout["priority"], Qt.AlignVCenter | Qt.AlignRight,
                             f"Приоритет {arrow}" if sort_key == "priority" else "Приоритет")

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.restore()
            return

        day: date = index.data(TaskRoles.Day)
        time_text: str = index.data(TaskRoles.DisplayTime) or ""
        title: str = index.data(TaskRoles.Title) or ""
        description: str = index.data(TaskRoles.Description) or ""
        project_title: str = index.data(TaskRoles.ProjectTitle) or ""
        project_area: str = index.data(TaskRoles.ProjectArea) or ""
        recurrence_kind: str = (index.data(TaskRoles.RecurrenceKind) or "").strip().lower()
        priority: str = index.data(TaskRoles.Priority) or "Medium"
        done: bool = bool(index.data(TaskRoles.Done))
        completion_delay_minutes = max(0, int(index.data(TaskRoles.CompletionDelayMinutes) or 0))
        overdue = self._is_overdue(day, done)
        show_completion_delay = done and completion_delay_minutes > 4 * 60
        completion_delay_text = self._format_completion_delay(completion_delay_minutes) if show_completion_delay else ""
        expanded = bool(index.data(TaskRoles.Expanded))
        has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
        subtasks_expanded = bool(index.data(TaskRoles.SubtasksExpanded))
        depth = int(index.data(TaskRoles.SubtaskDepth) or 0)

        bg = self.C_ROW if (index.row() % 2 == 0) else self.C_ROW_ALT
        if option.state & QStyle.State_Selected:
            bg = QColor("#343844")

        painter.fillRect(r, bg)
        painter.setPen(self.C_BORDER)
        painter.drawRect(r.adjusted(0, 0, -1, -1))

        layout = self._row_layout(r, depth, has_subtasks)
        cy = r.center().y()

        grip_rect = layout["grip"]
        self._icon_grip.paint(painter, grip_rect)

        cb_rect = layout["checkbox"]
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#16171a"))
        painter.drawRect(cb_rect)

        if done:
            painter.setPen(QColor("#cfcfcf"))
            painter.drawLine(cb_rect.left() + 3, cb_rect.center().y(),
                             cb_rect.center().x() - 1, cb_rect.bottom() - 3)
            painter.drawLine(cb_rect.center().x() - 1, cb_rect.bottom() - 3,
                             cb_rect.right() - 2, cb_rect.top() + 3)

        painter.setFont(self._font_small)
        painter.setPen(self.C_OVERDUE if overdue else self.C_DIM)
        time_rect = layout["date"]
        painter.drawText(time_rect, Qt.AlignVCenter | Qt.AlignLeft, time_text)

        tomorrow_rect = layout["tomorrow"]
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(tomorrow_rect)
        self._icon_tomorrow.paint(painter, QRect(tomorrow_rect.left() + 3, tomorrow_rect.top() + 3, 14, 14))

        project_rect = layout["project"]
        if project_title:
            painter.setFont(self._font_small)
            painter.setPen(self.C_DIM)
            display_project = f"{project_area} / {project_title}" if project_area else project_title
            if recurrence_kind in {"daily", "weekly", "monthly"}:
                display_project = f"{display_project} · REC"
            elided_project = QFontMetrics(self._font_small).elidedText(
                display_project,
                Qt.ElideRight,
                project_rect.width(),
            )
            painter.drawText(project_rect, Qt.AlignVCenter | Qt.AlignLeft, elided_project)

        icon_rect = layout["doc"]
        self._icon_doc.paint(painter, icon_rect)

        if has_subtasks:
            toggle_rect = layout["subtask_toggle"]
            toggle_icon = self._icon_subtask_open if subtasks_expanded else self._icon_subtask_closed
            toggle_icon.paint(painter, toggle_rect)

        painter.setFont(self._font)
        if done:
            title_color = self.C_DIM
        elif overdue:
            title_color = self.C_OVERDUE
        else:
            title_color = self.C_TEXT
        painter.setPen(title_color)

        menu_rect = layout["menu"]
        pr_rect = layout["priority"]
        title_rect = layout["title"]
        if expanded:
            title_box = QRect(
                title_rect.left(),
                r.top() + self.TEXT_VPAD,
                title_rect.width(),
                r.height() - self.TEXT_VPAD * 2,
            )
            painter.drawText(title_box, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, title)

            title_metrics = QFontMetrics(self._font)
            title_height = title_metrics.boundingRect(
                0, 0, title_rect.width(), 1000, Qt.TextWordWrap, title
            ).height()
            current_y = r.top() + self.TEXT_VPAD + title_height

            if completion_delay_text:
                delay_box = QRect(
                    title_rect.left(),
                    current_y + self.TEXT_GAP,
                    title_rect.width(),
                    title_metrics.height(),
                )
                painter.setPen(self.C_OVERDUE)
                painter.drawText(delay_box, Qt.AlignLeft | Qt.AlignTop, completion_delay_text)
                painter.setPen(title_color)
                current_y += self.TEXT_GAP + title_metrics.height()

            if description:
                desc_box = QRect(
                    title_rect.left(),
                    current_y + self.TEXT_GAP,
                    title_rect.width(),
                    r.height() - self.TEXT_VPAD * 2 - title_height - self.TEXT_GAP,
                )
                painter.setFont(self._font_small)
                painter.setPen(self.C_DIM if not overdue else self.C_OVERDUE)
                painter.drawText(desc_box, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, description)
                painter.setFont(self._font)
                desc_metrics = QFontMetrics(self._font_small)
                desc_height = desc_metrics.boundingRect(
                    0, 0, title_rect.width(), 1000, Qt.TextWordWrap, description
                ).height()
                current_y += self.TEXT_GAP + desc_height

            tags = index.data(TaskRoles.AttachmentSummary) or []
            if tags:
                current_y += self.TEXT_GAP
                self._draw_tags(painter, QPoint(title_rect.left(), current_y), title_rect.width(), tags)
        else:
            title_metrics = QFontMetrics(self._font)
            if completion_delay_text:
                delay_text = f" {completion_delay_text}"
                delay_width = title_metrics.horizontalAdvance(delay_text)
                title_width = max(40, title_rect.width() - delay_width)
                title_part = title_metrics.elidedText(title, Qt.ElideRight, title_width)
                title_part_rect = QRect(title_rect.left(), title_rect.top(), title_width, title_rect.height())
                delay_part_rect = QRect(
                    title_part_rect.right(),
                    title_rect.top(),
                    title_rect.width() - title_width,
                    title_rect.height(),
                )
                painter.setPen(title_color)
                painter.drawText(title_part_rect, Qt.AlignVCenter | Qt.AlignLeft, title_part)
                painter.setPen(self.C_OVERDUE)
                painter.drawText(delay_part_rect, Qt.AlignVCenter | Qt.AlignLeft, delay_text)
                painter.setPen(title_color)
            else:
                elided = title_metrics.elidedText(title, Qt.ElideRight, title_rect.width())
                painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        # --- PRIORITY BLOCK (fixed layout) ---
        value_text = "OVERDUE" if overdue else priority
        value_color = self.C_OVERDUE if overdue else self._prio_color(priority)

        # Жёсткая сетка справа
        icon_w = 18
        value_w = 72
        gap = 10
        label_w = pr_rect.width() - value_w - icon_w - gap

        label_rect = QRect(
            pr_rect.left(),
            pr_rect.top(),
            label_w,
            pr_rect.height()
        )

        value_rect = QRect(
            pr_rect.left() + label_w,
            pr_rect.top(),
            value_w,
            pr_rect.height()
        )

        icon_rect = QRect(
            pr_rect.right() - icon_w,
            cy - 8,
            16,
            16
        )

        painter.setFont(self._font_small)

        # label
        painter.setPen(self.C_DIM)
        # painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignRight, "приоритет")

        # value
        painter.setPen(value_color)
        painter.drawText(value_rect, Qt.AlignVCenter | Qt.AlignRight, value_text)

        # icon
        self._icon_fire.paint(painter, icon_rect)

        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 5, menu_rect.center().y() - 7, 14, 14))

        painter.restore()

    def editorEvent(self, event, model, option, index):
        """Обрабатывает клики по чекбоксу и меню строки."""
        row_type = index.data(TaskRoles.RowType)
        if row_type == "sort_header":
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                pos = event.position().toPoint()
                layout = self._row_layout(option.rect)
                if layout["title"].contains(pos):
                    if hasattr(model, "set_sort"):
                        model.set_sort("title")
                    return True
                if layout["date"].contains(pos):
                    if hasattr(model, "set_sort"):
                        model.set_sort("date")
                    return True
                if layout["priority"].contains(pos):
                    if hasattr(model, "set_sort"):
                        model.set_sort("priority")
                    return True
            return False
        if row_type != "task":
            return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            r = option.rect

            depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
            has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
            layout = self._row_layout(r, depth, has_subtasks)
            cb_rect = layout["checkbox"]
            tomorrow_rect = layout["tomorrow"]
            menu_rect = layout["menu"]
            toggle_rect = layout.get("subtask_toggle")

            if has_subtasks and toggle_rect and toggle_rect.contains(pos):
                if hasattr(model, "toggle_subtasks_expanded_by_row"):
                    model.toggle_subtasks_expanded_by_row(index.row())
                return True

            if tomorrow_rect.contains(pos):
                task = model.task_at_row(index.row()) if hasattr(model, "task_at_row") else None
                if task is not None and hasattr(model, "next_day_for_task"):
                    new_day = model.next_day_for_task(task)
                    model.move_task_to_day(task.id, new_day)
                return True

            if cb_rect.contains(pos):
                # confirm только если ставим done=True
                currently_done = bool(index.data(TaskRoles.Done))
                if not currently_done:
                    parent = option.widget if isinstance(option.widget, QWidget) else None
                    dialog = ConfirmDialog(
                        "Подтверждение",
                        "Пометить задачу выполненной?",
                        parent=parent,
                        confirm_text="Да",
                        cancel_text="Отмена",
                    )
                    if exec_with_overlay(dialog, parent) != QDialog.Accepted:
                        return True  # событие обработали, но действие отменили

                model.toggle_done_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True

        return False

    def _show_row_menu(self, index: QModelIndex):
        """Отображает контекстное меню строки."""
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
        act_open = menu.addAction("Открыть")
        menu.addSeparator()
        act_edit = menu.addAction("Редактировать")
        # menu.addAction("Проект")
        menu.addSeparator()
        act_del = menu.addAction("Удалить")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_open:
            self._open_task_view(index)
            return
        if chosen == act_edit:
            self._edit_task(index)
            return
        if chosen != act_del:
            return

        # confirm delete
        title = index.data(TaskRoles.Title) or "задачу"
        parent = menu.parentWidget() or None
        dialog = ConfirmDialog(
            "Удалить задачу",
            f"Удалить задачу:\n«{title}» ?",
            parent=parent,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, parent) != QDialog.Accepted:
            return

        m = index.model()
        if hasattr(m, "delete_task_by_row"):
            m.delete_task_by_row(index.row())

    def _edit_task(self, index: QModelIndex):
        """Открывает диалог редактирования задачи."""
        model = index.model()
        if not hasattr(model, "task_at_row"):
            return

        task = model.task_at_row(index.row())
        if task is None:
            return

        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = TaskEditDialog(task, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.Accepted:
            return

        values = dialog.values()
        if hasattr(model, "update_task_by_row"):
            try:
                model.update_task_by_row(
                    index.row(),
                    title=values["title"],
                    description=values["description"],
                    day=values["day"],
                    time_text=values["time_text"],
                    priority=values["priority"],
                    done=values["done"],
                    project_id=values["project_id"],
                    recurrence_kind=values["recurrence_kind"],
                    recurrence_interval=values["recurrence_interval"],
                )
            except ValueError as exc:
                QMessageBox.warning(parent or self.parent(), "Проверка", str(exc))

    def _open_task_view(self, index: QModelIndex) -> None:
        model = index.model()
        if not hasattr(model, "task_at_row"):
            return
        task = model.task_at_row(index.row())
        if task is None:
            return
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = TaskDetailsDialog(task, parent=parent)
        show_dialog_standard(dialog, parent)

    def _prio_color(self, p: str) -> QColor:
        """Возвращает цвет для приоритета."""
        p = (p or "").lower()
        if p == "high":
            return self.C_HIGH
        if p == "low":
            return self.C_LOW
        if p == "отложенная":
            return self.C_DEFER
        return self.C_MED

    def _is_overdue(self, d: date, done: bool) -> bool:
        """Проверяет, просрочена ли задача."""
        return (d < date.today()) and (not done)

    def _format_header(self, d: date) -> str:
        """Формирует подпись для заголовка дня."""
        wd = WEEKDAY_RU[d.weekday()]
        return f"{d.isoformat()} — {wd}"

    def _format_completion_delay(self, delay_minutes: int) -> str:
        """Формирует подпись расхождения по факту выполнения."""
        minutes = max(0, int(delay_minutes or 0))
        days = minutes // (24 * 60)
        hours = (minutes % (24 * 60)) // 60
        return f"(Просрочена: {days}д {hours}ч)"

    def _row_layout(self, r: QRect, depth: int = 0, has_subtasks: bool = False) -> dict:
        """Возвращает прямоугольники основных колонок строки."""
        x = r.left() + 10
        cy = r.center().y()

        grip_rect = QRect(x, cy - 8, 16, 16)
        x += 22

        cb_rect = QRect(x, cy - 7, 14, 14)
        x += 22

        tomorrow_rect = QRect(x, cy - 8, 20, 20)
        x += 28

        time_rect = QRect(x, r.top(), self.TIME_W, r.height())
        x += self.TIME_W + 6

        project_rect = QRect(x, r.top(), self.PROJECT_W, r.height())
        x += self.PROJECT_W + 6

        indent = max(0, depth) * 14
        x += indent

        toggle_w = 16 if has_subtasks else 0
        toggle_rect = QRect(x, cy - 8, toggle_w, 16)
        if has_subtasks:
            x += toggle_w + 4

        doc_rect = QRect(x, cy - 8, 16, 16)
        x += 22

        right_pad = 20
        menu_w = 30
        pr_w = 140
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 6, menu_w, r.height() - 12)
        pr_rect = QRect(menu_rect.left() - pr_w - 8, r.top(), pr_w, r.height())
        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())

        return {
            "grip": grip_rect,
            "checkbox": cb_rect,
            "tomorrow": tomorrow_rect,
            "date": time_rect,
            "project": project_rect,
            "subtask_toggle": toggle_rect,
            "doc": doc_rect,
            "title": title_rect,
            "priority": pr_rect,
            "menu": menu_rect,
        }


class TasksWorkspace(BaseWorkspace):
    """Рабочая область задач: панель управления и список с группировкой."""

    workspace_id = "tasks"
    workspace_title = "Задачи"
    GANTT_DAY_START_HOUR = 8
    GANTT_DAY_END_HOUR = 22

    def __init__(self, parent=None):
        """Создает интерфейс рабочей области задач."""
        self._focus_day = date.today()
        self._applying_filters = False
        self._gantt_mode = False
        super().__init__(parent)
        self.setObjectName("TasksWorkspace")
        self.search_input.setPlaceholderText("Поиск…")

        self._build_filters()
        self.build_content()

        self._update_day_label()
        self._apply_tab("plan")
        self.update_action_states()

        self.setStyleSheet("""
            QWidget#TasksWorkspace { background: #16171a; }


            QFrame#TasksCreateBar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QFrame#TasksCreateBar QLineEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                color: #e6e6e6;
            }

            QFrame#TasksCreateBar QComboBox {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock {
                background: #131417;
                border: 1px solid #2a2b2f;
                border-radius: 8px;
            }

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QDateEdit,
            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QTimeEdit {
                background: transparent;
                border: none;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QCheckBox {
                color: #cfcfcf;
                padding: 0 6px;
            }

            QFrame#TasksCreateBar QToolButton {
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QFrame#TasksCreateBar QToolButton:hover { background: #34363b; }

            QToolButton {
                color: #cfcfcf;
                border: none;
                padding: 6px 8px;
            }
            QToolButton:checked {
                background: #2a2b2f;
            }

            QLabel#TasksDayLabel {
                color: #cfcfcf;
                padding: 0px 6px;
            }

            QComboBox, QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
            }

            QListView#TasksList {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }

            QTableWidget#TasksGanttTable {
                background: #16171a;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                gridline-color: #2a2b2f;
                alternate-background-color: #1b1c20;
                selection-background-color: #2f3238;
                selection-color: #f2f2f2;
            }

            QTableWidget#TasksGanttTable::item {
                padding: 4px 6px;
            }

            QTableWidget#TasksGanttTable QHeaderView::section {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 4px 6px;
            }

            QTableWidget#TasksGanttTable QTableCornerButton::section {
                background: #202127;
                border: 1px solid #2a2b2f;
            }

            QTableWidget#TasksGanttTable QSpinBox {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 2px 6px;
            }

            QTableWidget#TasksGanttTable QSpinBox::up-button,
            QTableWidget#TasksGanttTable QSpinBox::down-button {
                background: #2a2b2f;
                border-left: 1px solid #3a3b40;
                width: 14px;
            }

            QTableWidget#TasksGanttTable QSpinBox::up-button:hover,
            QTableWidget#TasksGanttTable QSpinBox::down-button:hover {
                background: #34363b;
            }

            QLabel#TasksGanttHint {
                color: #aeb3bf;
                padding: 2px 4px;
            }
        """)

    def build_content(self) -> None:
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        create = QFrame()
        create.setObjectName("TasksCreateBar")
        create_layout = QHBoxLayout(create)
        create_layout.setContentsMargins(10, 8, 10, 8)
        create_layout.setSpacing(8)

        self.new_title = QLineEdit()
        self.new_title.setPlaceholderText("Название задачи…")

        self.new_day = QDateEdit()
        self.new_day.setCalendarPopup(True)
        self.new_day.setDisplayFormat("yyyy-MM-dd")
        self.new_day.setFixedWidth(140)
        self.new_day.setDate(datetime.now().date())
        self.new_day.setToolTip("Дата выполнения (можно выбрать в календаре или ввести вручную)")
        self.new_day.setKeyboardTracking(False)

        self.new_time = QTimeEdit()
        self.new_time.setDisplayFormat("HH:mm")
        self.new_time.setFixedWidth(90)
        self.new_time.setTime(QTime.currentTime())
        self.new_time.setKeyboardTracking(False)

        self.new_time_toggle = QCheckBox("Время")
        self.new_time_toggle.setCursor(Qt.PointingHandCursor)
        self.new_time_toggle.setChecked(False)
        self.new_time.setEnabled(False)
        self.new_time_toggle.toggled.connect(self.new_time.setEnabled)

        datetime_block = QFrame()
        datetime_block.setObjectName("TasksDateTimeBlock")
        datetime_layout = QHBoxLayout(datetime_block)
        datetime_layout.setContentsMargins(6, 2, 6, 2)
        datetime_layout.setSpacing(6)
        datetime_layout.addWidget(self.new_day)
        datetime_layout.addWidget(self.new_time_toggle)
        datetime_layout.addWidget(self.new_time)

        self.new_priority = QComboBox()
        self.new_priority.setFixedWidth(110)
        self.new_priority.addItems(["Low", "Medium", "High", "Отложенная"])
        self.new_priority.setCurrentText("Medium")

        self.btn_add = QToolButton()
        self.btn_add.setText("Создать")
        self.btn_add.setCursor(Qt.PointingHandCursor)

        create_layout.addWidget(self.new_title, 1)
        create_layout.addWidget(datetime_block)
        create_layout.addWidget(self.new_priority)
        create_layout.addWidget(self.btn_add)

        content_layout.addWidget(create)

        self.list = QListView()
        self.list.setObjectName("TasksList")
        self.list.setUniformItemSizes(False)
        self.list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SingleSelection)
        self.list.setDragDropMode(QAbstractItemView.NoDragDrop)

        self.model = TasksModel(self)
        self.list.setModel(self.model)

        self.delegate = TasksItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        self.btn_add.clicked.connect(self._on_create_task)
        self.new_title.returnPressed.connect(self._on_create_task)
        self.list.viewport().installEventFilter(self)

        selection_model = self.list.selectionModel()
        selection_model.selectionChanged.connect(lambda *_: self.update_action_states())
        selection_model.currentChanged.connect(lambda *_: self.update_action_states())
        self.model.modelReset.connect(self.update_action_states)
        self.model.layoutChanged.connect(self.update_action_states)

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.list)
        self.gantt_page = self._build_gantt_page()
        self.content_stack.addWidget(self.gantt_page)
        self.content_stack.setCurrentWidget(self.list)
        content_layout.addWidget(self.content_stack, 1)

        self.set_content(content)

    def _build_gantt_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.gantt_hint = QLabel("Режим Гант: прогноз длительности строится автоматически и сохраняется.")
        self.gantt_hint.setObjectName("TasksGanttHint")
        self.gantt_hint.setWordWrap(True)
        layout.addWidget(self.gantt_hint)

        self.gantt_table = QTableWidget(0, 6, page)
        self.gantt_table.setObjectName("TasksGanttTable")
        self.gantt_table.setHorizontalHeaderLabels(
            ["Задача", "Срок", "Старт", "Финиш", "Лента", "Минуты"]
        )
        self.gantt_table.verticalHeader().setVisible(False)
        self.gantt_table.setAlternatingRowColors(True)
        self.gantt_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.gantt_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table_palette = self.gantt_table.palette()
        table_palette.setColor(QPalette.Base, QColor("#16171a"))
        table_palette.setColor(QPalette.AlternateBase, QColor("#1b1c20"))
        table_palette.setColor(QPalette.Text, QColor("#cfcfcf"))
        table_palette.setColor(QPalette.Mid, QColor("#3a3b40"))
        table_palette.setColor(QPalette.Highlight, QColor("#4f7ecf"))
        self.gantt_table.setPalette(table_palette)
        self.gantt_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.gantt_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.gantt_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.gantt_table, 1)
        return page

    class _GanttBarWidget(QWidget):
        def __init__(self, start_minutes: int, end_minutes: int, day_start: int, day_end: int, parent=None):
            super().__init__(parent)
            self._start = int(start_minutes)
            self._end = int(end_minutes)
            self._day_start = int(day_start)
            self._day_end = int(day_end)
            self.setMinimumHeight(18)

        def paintEvent(self, event):
            super().paintEvent(event)
            painter = QPainter(self)
            r = self.rect().adjusted(2, 3, -2, -3)
            if r.width() <= 0 or r.height() <= 0:
                return

            pal = self.palette()
            border_color = pal.mid().color()
            track_color = pal.alternateBase().color()
            accent_color = pal.highlight().color()
            label_color = pal.text().color()
            label_color.setAlpha(140)
            minor_tick_color = pal.mid().color()
            minor_tick_color.setAlpha(120)
            if track_color.lightness() > 120:
                border_color = QColor("#3a3b40")
                track_color = QColor("#1f2227")
                accent_color = QColor("#4f7ecf")
                label_color = QColor("#8a8d95")
                minor_tick_color = QColor("#43464d")

            painter.setPen(border_color)
            painter.setBrush(track_color)
            painter.drawRoundedRect(r, 4, 4)

            # Почасовая сетка и подписи времени (каждые 2 часа).
            span = max(1, self._day_end - self._day_start)
            baseline_y = r.bottom() - 9
            for hour in range(self._day_start // 60, self._day_end // 60 + 1):
                minute_mark = hour * 60
                x = r.left() + int((minute_mark - self._day_start) / span * r.width())
                strong_tick = (hour % 2 == 0) or (minute_mark == self._day_start) or (minute_mark == self._day_end)
                tick_color = border_color if strong_tick else minor_tick_color
                painter.setPen(tick_color)
                painter.drawLine(x, r.top() + 1, x, baseline_y)
                if strong_tick:
                    label = f"{hour:02d}"
                    label_rect = QRect(x - 10, baseline_y + 1, 20, 8)
                    painter.setPen(label_color)
                    painter.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop, label)

            start_clamped = min(max(self._start, self._day_start), self._day_end)
            end_clamped = min(max(self._end, self._day_start), self._day_end)
            if end_clamped <= start_clamped:
                return

            x1 = r.left() + int((start_clamped - self._day_start) / span * r.width())
            x2 = r.left() + int((end_clamped - self._day_start) / span * r.width())
            bar_w = max(2, x2 - x1)
            bar = QRect(x1, r.top() + 1, bar_w, max(2, baseline_y - r.top() - 1))
            painter.setPen(Qt.NoPen)
            painter.setBrush(accent_color)
            painter.drawRoundedRect(bar, 4, 4)

    def _build_filters(self) -> None:
        while self.filter_layout.count():
            item = self.filter_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str, tab_value: str) -> QToolButton:
            b = QToolButton()
            b.setText(text)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setAutoRaise(True)
            b.setProperty("tab", tab_value)
            self.tabs_group.addButton(b)
            b.clicked.connect(lambda checked=False, value=tab_value: self.set_filter("tab", value))
            return b

        self.tab_all = tab_btn("Все", "all")
        self.tab_plan = tab_btn("План", "plan")
        self.tab_today = tab_btn("Сегодня", "today")
        self.tab_done = tab_btn("Выполнено", "done")
        self.tab_deferred = tab_btn("Отложенные", "deferred")
        self.tab_plan.setChecked(True)

        self.btn_prev_day = QToolButton()
        self.btn_prev_day.setIcon(qta.icon("fa5s.chevron-left", color="#cfcfcf"))
        self.btn_prev_day.setCursor(Qt.PointingHandCursor)
        self.btn_prev_day.setAutoRaise(True)

        self.btn_next_day = QToolButton()
        self.btn_next_day.setIcon(qta.icon("fa5s.chevron-right", color="#cfcfcf"))
        self.btn_next_day.setCursor(Qt.PointingHandCursor)
        self.btn_next_day.setAutoRaise(True)

        self.btn_gantt = QToolButton()
        self.btn_gantt.setText("Гант")
        self.btn_gantt.setCheckable(True)
        self.btn_gantt.setCursor(Qt.PointingHandCursor)
        self.btn_gantt.setAutoRaise(True)
        self.btn_gantt.setVisible(False)

        self.lbl_day = QLabel()
        self.lbl_day.setObjectName("TasksDayLabel")

        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Любой", "Low", "Medium", "High", "Отложенная"])
        self.cmb_priority.setFixedWidth(110)

        self.filter_layout.addWidget(self.tab_all)
        self.filter_layout.addWidget(self.tab_plan)
        self.filter_layout.addWidget(self.tab_today)
        self.filter_layout.addWidget(self.tab_done)
        self.filter_layout.addWidget(self.tab_deferred)
        self.filter_layout.addSpacing(12)
        self.filter_layout.addWidget(self.btn_prev_day)
        self.filter_layout.addWidget(self.lbl_day)
        self.filter_layout.addWidget(self.btn_next_day)
        self.filter_layout.addWidget(self.btn_gantt)
        self.filter_layout.addSpacing(12)
        self.filter_layout.addStretch(1)
        self.filter_layout.addWidget(self.cmb_priority)
        self._relocate_search()

        self.btn_prev_day.clicked.connect(lambda: self._shift_day(-1))
        self.btn_next_day.clicked.connect(lambda: self._shift_day(+1))
        self.btn_gantt.toggled.connect(self._set_gantt_mode)
        self.cmb_priority.currentTextChanged.connect(self._on_priority_filter_changed)

    def _relocate_search(self) -> None:
        """Перемещает строку поиска в панель фильтров."""
        self.search_row.setVisible(False)
        search_layout = self.search_row.layout()
        if search_layout is not None:
            search_layout.removeWidget(self.search_input)
            search_layout.removeWidget(self.clear_button)
        self.search_input.setFixedWidth(260)
        self.filter_layout.addWidget(self.search_input)
        self.filter_layout.addWidget(self.clear_button)

    def refresh(self) -> None:
        """Перезагружает список задач из базы."""
        self.model.refresh()
        if self._gantt_mode:
            self._refresh_gantt_day()

    def on_enter(self, context: dict | None = None) -> None:
        super().on_enter(context)

    def apply_query(self, query: str) -> None:
        priority_value = self.cmb_priority.currentText() if hasattr(self, "cmb_priority") else "Любой"
        priority = None if priority_value == "Любой" else priority_value
        self.model.set_priority_filter(priority)
        self.model.set_search(query)

    def apply_filters(self, filters: Dict[str, object]) -> None:
        self._applying_filters = True
        try:
            tab = filters.get("tab")
            if not tab:
                mode = filters.get("mode")
                if mode:
                    tab = self._tab_from_mode(mode)
                else:
                    tab = "plan"
            focus_day = filters.get("focus_day")
            project_id = filters.get("project_id")
            priority = filters.get("priority")
            if isinstance(focus_day, str):
                try:
                    focus_day = date.fromisoformat(focus_day)
                except ValueError:
                    focus_day = None
            if isinstance(focus_day, date):
                self._focus_day = focus_day
            self._apply_tab(tab, focus_day=focus_day)
            self.model.set_project_filter(project_id)
            self.model.set_priority_filter(priority if isinstance(priority, str) else None)
            if priority:
                self.cmb_priority.setCurrentText(priority)
            else:
                self.cmb_priority.setCurrentText("Любой")
        finally:
            self._applying_filters = False

    def get_selection(self) -> List[TaskRow]:
        index = self._selected_task_index()
        if index is None:
            return []
        if hasattr(self.model, "task_at_row"):
            task = self.model.task_at_row(index.row())
            return [task] if task else []
        return []

    def _selected_task_index(self) -> Optional[QModelIndex]:
        if not hasattr(self, "list"):
            return None
        index = self.list.currentIndex()
        if not index.isValid():
            return None
        if index.data(TaskRoles.RowType) != "task":
            return None
        return index

    def _edit_selected_task(self) -> None:
        index = self._selected_task_index()
        if index is None:
            return
        self.delegate._edit_task(index)

    def _delete_selected_task(self) -> None:
        index = self._selected_task_index()
        if index is None:
            return
        title = index.data(TaskRoles.Title) or "задачу"
        dialog = ConfirmDialog(
            "Удалить задачу",
            f"Удалить задачу:\n«{title}» ?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        model = index.model()
        if hasattr(model, "delete_task_by_row"):
            model.delete_task_by_row(index.row())

    def _shift_day(self, delta: int):
        """Сдвигает фокусную дату на указанное число дней."""
        self._focus_day = self._focus_day + timedelta(days=delta)
        self._update_day_label()
        if self._gantt_mode:
            self._remember_filter("focus_day", self._focus_day.isoformat())
            self._refresh_gantt_day()
            return
        if not self._applying_filters:
            self._filters["focus_day"] = self._focus_day.isoformat()
            self.set_filter("tab", "all")
        else:
            self._apply_tab("all", focus_day=self._focus_day)

    def _update_day_label(self):
        """Обновляет подпись текущего дня."""
        wd = WEEKDAY_RU[self._focus_day.weekday()]
        self.lbl_day.setText(f"{self._focus_day.isoformat()} ({wd})")

    def _on_create_task(self):
        """Создает задачу из формы и очищает ввод."""
        title = self.new_title.text().strip()
        if not title:
            return

        qd = self.new_day.date()
        d = date(qd.year(), qd.month(), qd.day())

        pr = self.new_priority.currentText().strip() or "Medium"
        time_text = ""
        if self.new_time_toggle.isChecked():
            time_text = self.new_time.time().toString("HH:mm")

        try:
            self.model.add_task(title=title, day=d, time_text=time_text, priority=pr)
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return

        if self._gantt_mode and d == self._focus_day:
            self._refresh_gantt_day()

        self.new_title.clear()
        self.new_title.setFocus()

    def open_create_task_dialog(self) -> None:
        dialog = TaskCreateDialog(parent=self)
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        values = dialog.values()
        try:
            self.model.add_task(
                title=values["title"],
                description=values["description"],
                day=values["day"],
                time_text=values["time_text"],
                priority=values["priority"],
                project_id=values["project_id"],
                recurrence_kind=values["recurrence_kind"],
                recurrence_interval=values["recurrence_interval"],
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        if self._gantt_mode and values["day"] == self._focus_day:
            self._refresh_gantt_day()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.list.viewport() and event.type() == QEvent.MouseButtonDblClick:
            if event.button() == Qt.LeftButton:
                pos = event.position().toPoint()
                index = self.list.indexAt(pos)
                if not index.isValid() or index.data(TaskRoles.RowType) != "task":
                    return False
                rect = self.list.visualRect(index)
                depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
                has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
                layout = self.delegate._row_layout(rect, depth, has_subtasks)
                if has_subtasks and layout["title"].contains(pos):
                    self.model.toggle_subtasks_expanded_by_row(index.row())
                elif layout["doc"].contains(pos):
                    self.delegate._open_task_view(index)
                else:
                    if has_subtasks:
                        self.model.toggle_subtasks_expanded_by_row(index.row())
                    else:
                        self.delegate._open_task_view(index)
                return True
        return super().eventFilter(obj, event)

    def set_project_filter(self, project_id: Optional[int]):
        """Обновляет фильтр по проекту."""
        if self._applying_filters:
            self.model.set_project_filter(project_id)
            return
        self._remember_filter("project_id", project_id)
        self.model.set_project_filter(project_id)

    def refresh_tasks(self) -> None:
        """Перезагружает список задач из базы."""
        self.model.refresh()

    def _tab_from_mode(self, mode: Optional[str]) -> str:
        if mode == "Сегодня":
            return "today"
        if mode == "Выполнено":
            return "done"
        if mode == "План":
            return "plan"
        if mode == "Отложенные":
            return "deferred"
        return "all"

    def _apply_tab(self, tab: Optional[str], focus_day: Optional[date] = None) -> None:
        if tab == "today":
            self._apply_mode("Сегодня")
        elif tab == "done":
            self._apply_mode("Выполнено")
        elif tab == "plan":
            self._apply_mode("План")
        elif tab == "deferred":
            self._apply_mode("Отложенные")
        else:
            self._apply_mode("Все", focus_day=focus_day)

    def _apply_mode(self, mode: str, focus_day: Optional[date] = None) -> None:
        if mode == "Сегодня":
            if self._gantt_mode:
                self.btn_gantt.setChecked(False)
            self.model.set_filter_mode("Сегодня")
            self._focus_day = date.today()
            self.model.set_focus_day(self._focus_day)
            self._set_drag_drop_state(False)
            self.btn_gantt.setVisible(False)
            self.tab_today.setChecked(True)
        elif mode == "Выполнено":
            if self._gantt_mode:
                self.btn_gantt.setChecked(False)
            self.model.set_filter_mode("Выполнено")
            self.model.set_focus_day(None)
            self._set_drag_drop_state(False)
            self.btn_gantt.setVisible(False)
            self.tab_done.setChecked(True)
        elif mode == "План":
            self.model.set_filter_mode("План")
            self.btn_gantt.setVisible(True)
            if self._gantt_mode:
                self.model.set_focus_day(self._focus_day)
                self._set_drag_drop_state(False)
                self.content_stack.setCurrentWidget(self.gantt_page)
                self._refresh_gantt_day()
            else:
                self.model.set_focus_day(None)
                self._set_drag_drop_state(True)
                self.content_stack.setCurrentWidget(self.list)
            if hasattr(self, "tab_plan"):
                self.tab_plan.setChecked(True)
        elif mode == "Отложенные":
            if self._gantt_mode:
                self.btn_gantt.setChecked(False)
            self.model.set_filter_mode("Отложенные")
            self.model.set_focus_day(None)
            self._set_drag_drop_state(False)
            self.btn_gantt.setVisible(False)
            if hasattr(self, "tab_deferred"):
                self.tab_deferred.setChecked(True)
        else:
            if self._gantt_mode:
                self.btn_gantt.setChecked(False)
            self.model.set_filter_mode("Все")
            if focus_day is not None:
                self._focus_day = focus_day
            self.model.set_focus_day(self._focus_day)
            self._set_drag_drop_state(False)
            self.btn_gantt.setVisible(False)
            self.tab_all.setChecked(True)
        self._update_day_label()

    def _remember_filter(self, key: str, value: Optional[object]) -> None:
        if value is None:
            self._filters.pop(key, None)
        else:
            self._filters[key] = value
        self.save_state()

    def _on_priority_filter_changed(self, value: str) -> None:
        if self._applying_filters:
            return
        priority = None if value == "Любой" else value
        self._remember_filter("priority", priority)
        self.model.set_priority_filter(priority)
        if self._gantt_mode:
            self._refresh_gantt_day()

    def _set_gantt_mode(self, enabled: bool) -> None:
        plan_mode = self.model.filter_mode() == "План"
        if enabled and not plan_mode:
            self.btn_gantt.blockSignals(True)
            self.btn_gantt.setChecked(False)
            self.btn_gantt.blockSignals(False)
            return
        self._gantt_mode = bool(enabled and plan_mode)
        if self._gantt_mode:
            self.model.set_filter_mode("План")
            self.model.set_focus_day(self._focus_day)
            self._set_drag_drop_state(False)
            self.content_stack.setCurrentWidget(self.gantt_page)
            self._refresh_gantt_day()
        else:
            if plan_mode:
                self.model.set_filter_mode("План")
                self.model.set_focus_day(None)
                self._set_drag_drop_state(True)
            self.content_stack.setCurrentWidget(self.list)

    def _estimate_task_minutes(self, task) -> int:
        text = f"{task.title} {task.description or ''}".lower()
        words = len((task.description or "").split())
        base = 50
        if task.priority == "High":
            base = 90
        elif task.priority == "Low":
            base = 35
        elif task.priority == "Отложенная":
            base = 25
        complexity_markers = [
            "исслед", "архитект", "интеграц", "рефактор", "оптимизац",
            "debug", "тест", "докум", "design", "api", "sql",
            "миграц", "парсер", "настро", "синхрон",
        ]
        marker_hits = sum(1 for marker in complexity_markers if marker in text)
        raw = base + words * 2 + marker_hits * 15
        return max(15, min(8 * 60, int(round(raw / 5.0) * 5)))

    @staticmethod
    def _parse_task_datetime(task_day: date, time_text: str) -> datetime:
        if time_text:
            try:
                return datetime.strptime(f"{task_day.isoformat()} {time_text}", "%Y-%m-%d %H:%M")
            except ValueError:
                pass
        return datetime.combine(task_day, datetime.min.time())

    def _refresh_gantt_day(self) -> None:
        db = get_database()
        priority_value = self.cmb_priority.currentText() if hasattr(self, "cmb_priority") else "Любой"
        priority_filter = None if priority_value == "Любой" else priority_value
        tasks = [
            task
            for task in db.fetch_tasks()
            if task.day == self._focus_day
            and not task.done
            and task.priority != "Отложенная"
            and (priority_filter is None or task.priority == priority_filter)
        ]
        tasks.sort(key=lambda task: (self._parse_task_datetime(task.day, task.time_text), task.id))

        predicted = 0
        for task in tasks:
            if not task.gantt_forecasted or task.gantt_estimate_minutes <= 0:
                db.set_task_gantt_estimate(task.id, self._estimate_task_minutes(task), forecasted=True)
                predicted += 1
        if predicted:
            tasks = [
                task
                for task in db.fetch_tasks()
                if task.day == self._focus_day
                and not task.done
                and task.priority != "Отложенная"
                and (priority_filter is None or task.priority == priority_filter)
            ]
            tasks.sort(key=lambda task: (self._parse_task_datetime(task.day, task.time_text), task.id))

        self.gantt_table.setRowCount(0)
        if not tasks:
            self.gantt_hint.setText("На выбранный день нет активных задач для диаграммы Ганта.")
            return

        cursor = datetime.combine(self._focus_day, datetime.strptime("09:00", "%H:%M").time())
        total_minutes = 0
        day_start_minutes = self.GANTT_DAY_START_HOUR * 60
        day_end_minutes = self.GANTT_DAY_END_HOUR * 60
        self.gantt_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            pref_dt = self._parse_task_datetime(task.day, task.time_text)
            start_dt = max(cursor, pref_dt)
            estimate = max(15, int(task.gantt_estimate_minutes or 0))
            end_dt = start_dt + timedelta(minutes=estimate)
            cursor = end_dt
            total_minutes += estimate

            self.gantt_table.setItem(row, 0, QTableWidgetItem(task.title))
            self.gantt_table.setItem(row, 1, QTableWidgetItem(task.time_text or "—"))
            self.gantt_table.setItem(row, 2, QTableWidgetItem(start_dt.strftime("%H:%M")))
            self.gantt_table.setItem(row, 3, QTableWidgetItem(end_dt.strftime("%H:%M")))

            start_minutes = start_dt.hour * 60 + start_dt.minute
            end_minutes = end_dt.hour * 60 + end_dt.minute
            bar_widget = self._GanttBarWidget(
                start_minutes=start_minutes,
                end_minutes=end_minutes,
                day_start=day_start_minutes,
                day_end=day_end_minutes,
                parent=self.gantt_table,
            )
            self.gantt_table.setCellWidget(row, 4, bar_widget)
            self.gantt_table.setRowHeight(row, 34)

            minutes_spin = QSpinBox(self.gantt_table)
            minutes_spin.setRange(5, 8 * 60)
            minutes_spin.setSingleStep(5)
            minutes_spin.setValue(estimate)
            minutes_spin.setEnabled(bool(task.gantt_forecasted))
            minutes_spin.valueChanged.connect(
                lambda value, task_id=task.id: self._on_gantt_minutes_changed(task_id, value)
            )
            self.gantt_table.setCellWidget(row, 5, minutes_spin)

        total_hours = total_minutes / 60.0
        self.gantt_hint.setText(
            f"Гант на {self._focus_day.isoformat()}: {len(tasks)} задач, {total_minutes} мин (~{total_hours:.1f} ч)."
        )

    def _on_gantt_minutes_changed(self, task_id: int, minutes: int) -> None:
        get_database().set_task_gantt_estimate(task_id, minutes, forecasted=True)
        self._refresh_gantt_day()

    def _set_drag_drop_state(self, enabled: bool):
        """Включает или выключает drag and drop списка."""
        if enabled:
            self.list.setDragEnabled(True)
            self.list.setAcceptDrops(True)
            self.list.setDropIndicatorShown(True)
            self.list.setDefaultDropAction(Qt.MoveAction)
            self.list.setDragDropMode(QAbstractItemView.DragDrop)
        else:
            self.list.setDragEnabled(False)
            self.list.setAcceptDrops(False)
            self.list.setDropIndicatorShown(False)
            self.list.setDragDropMode(QAbstractItemView.NoDragDrop)
