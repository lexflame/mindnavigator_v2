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
from typing import Dict, List, Union, Optional, Set, Tuple, Any, cast

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QPoint, QAbstractListModel, QAbstractItemModel, QModelIndex, QEvent, QDate, QTime, QMimeData, QItemSelectionModel
from PySide6.QtGui import QAction, QPainter, QColor, QFont, QFontMetrics, QCursor, QPixmap, QShortcut, QKeySequence, QPalette, QMouseEvent
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QDateEdit, QTimeEdit, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle,
    QCheckBox, QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QAbstractItemView, QPlainTextEdit, QScrollArea, QStyleOptionViewItem,
    QStackedWidget, QTableWidget, QTableWidgetItem, QSpinBox, QHeaderView, QFileDialog
)

from mindnavigator.csv_transfer import CsvTransferError, CsvTransferService
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
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace
from mindnavigator.workspaces.csv_workspace_transfer import (
    TASKS_CSV_FIELDS,
    export_tasks_rows,
    import_tasks_rows,
)

WEEKDAY_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
_PARENT_UNSET = object()

ATTACHMENT_KIND_LABELS = {
    "note": "Заметка",
    "idea": "Идея",
    "object": "Объект",
    "map": "Карта",
    "marker": "Метка карты",
    "file": "Файл",
    "image": "Изображение",
}
ATTACHMENT_KIND_ORDER = ("note", "idea", "object", "map", "marker", "file", "image")
_URL_RE = re.compile(r"(https?://[^\s<>'\"()]+)")
_FENCED_CODE_RE = re.compile(r"```([^\n`]*)\n?(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_INLINE_CODE_STYLE = (
    "font-family:'Consolas','Courier New',monospace;"
    "background:#1f2228;"
    "color:#f0f0f0;"
    "padding:1px 5px;"
    "border-radius:5px;"
    "border:1px solid #5a5f66;"
)
_BLOCK_CODE_STYLE = (
    "font-family:'Consolas','Courier New',monospace;"
    "background:#171a20;"
    "border:1px solid #5a5f66;"
    "border-radius:8px;"
    "padding:5px;"
    "margin:6px 0;"
    "white-space:pre-wrap;"
)
_BLOCK_CODE_LANG_STYLE = "color:#7d828a;font-size:10px;margin:2px 0 2px 2px;"
_LINK_STYLE = "color:#6ECBFF;text-decoration:none;"
_COPY_CODE_BUTTON_STYLE = (
    "QToolButton {"
    "background:#2a2d34;"
    "color:#d7dae0;"
    "border:1px solid #5a5f66;"
    "border-radius:5px;"
    "padding:2px 8px;"
    "}"
    "QToolButton:hover {"
    "background:#343841;"
    "}"
)


def attachment_kind_label(kind: str) -> str:
    return ATTACHMENT_KIND_LABELS.get(kind, kind)


def _linkify_escaped_text(escaped_text: str) -> str:
    def replace_url(match: re.Match[str]) -> str:
        url = match.group(1)
        return f"<a href='{url}' style=\"{_LINK_STYLE}\">{url}</a>"

    return _URL_RE.sub(replace_url, escaped_text)


def _extract_markdown_code_blocks(text: str) -> list[str]:
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[str] = []
    for match in _FENCED_CODE_RE.finditer(raw):
        block = (match.group(2) or "").strip("\n")
        if block:
            blocks.append(block)
    return blocks


def _copy_markdown_code_blocks_to_clipboard(code_blocks: list[str]) -> None:
    if not code_blocks:
        return
    QApplication.clipboard().setText("\n\n".join(code_blocks))


def _configure_markdown_preview_label(value_label: QLabel) -> None:
    value_label.setWordWrap(True)
    value_label.setTextFormat(Qt.TextFormat.RichText)
    value_label.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextBrowserInteraction
        | Qt.TextInteractionFlag.TextSelectableByMouse
    )
    value_label.setOpenExternalLinks(True)


def _build_markdown_preview_widget(text: str, parent: Optional[QWidget] = None) -> QWidget:
    container = QWidget(parent)
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(4)

    value_label = QLabel(_linkify_description_text(text))
    _configure_markdown_preview_label(value_label)
    container_layout.addWidget(value_label)

    code_blocks = _extract_markdown_code_blocks(text)
    if not code_blocks:
        return container

    copy_row = QHBoxLayout()
    copy_row.setContentsMargins(0, 0, 0, 0)
    copy_row.addStretch(1)
    copy_button = QToolButton(container)
    copy_button.setText("Копировать код")
    copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
    copy_button.setStyleSheet(_COPY_CODE_BUTTON_STYLE)
    blocks_to_copy = tuple(code_blocks)
    copy_button.clicked.connect(
        lambda _checked=False, blocks=blocks_to_copy: _copy_markdown_code_blocks_to_clipboard(list(blocks))
    )
    copy_row.addWidget(copy_button)
    container_layout.addLayout(copy_row)
    return container


def _render_inline_description_html(text: str) -> str:
    rendered: list[str] = []
    cursor = 0
    for match in _INLINE_CODE_RE.finditer(text):
        plain_text = text[cursor:match.start()]
        if plain_text:
            escaped_plain = html.escape(plain_text)
            linked_plain = _linkify_escaped_text(escaped_plain)
            rendered.append(linked_plain.replace("\n", "<br>"))

        inline_code = html.escape(match.group(1) or "")
        rendered.append(f"<code style=\"{_INLINE_CODE_STYLE}\">{inline_code}</code>")
        cursor = match.end()

    tail_text = text[cursor:]
    if tail_text:
        escaped_tail = html.escape(tail_text)
        linked_tail = _linkify_escaped_text(escaped_tail)
        rendered.append(linked_tail.replace("\n", "<br>"))
    return "".join(rendered)


def _linkify_description_text(text: str) -> str:
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return "—"

    rendered: list[str] = []
    cursor = 0
    for match in _FENCED_CODE_RE.finditer(raw):
        plain_text = raw[cursor:match.start()]
        if plain_text:
            rendered.append(_render_inline_description_html(plain_text))

        language = (match.group(1) or "").strip()
        code_body = html.escape(match.group(2) or "")
        if language:
            rendered.append(
                f"<div style=\"{_BLOCK_CODE_LANG_STYLE}\">{html.escape(language)}</div>"
            )
        rendered.append(
            f"<pre style=\"{_BLOCK_CODE_STYLE}\"><code>{code_body}</code></pre>"
        )
        cursor = match.end()

    tail_text = raw[cursor:]
    if tail_text:
        rendered.append(_render_inline_description_html(tail_text))
    return "".join(rendered)


def should_show_today_badge(header_day: date) -> bool:
    return header_day == date.today()


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
    marker_color: str = ""
    marker_theme: str = ""


@dataclass(frozen=True)
class HeaderRow:
    day: date


@dataclass(frozen=True)
class SortHeaderRow:
    pass


Row = Union[TaskRow, HeaderRow, SortHeaderRow]


class TaskRoles:
    RowType = Qt.ItemDataRole.UserRole + 1  # header | task
    Day = Qt.ItemDataRole.UserRole + 2
    TimeText = Qt.ItemDataRole.UserRole + 3
    Title = Qt.ItemDataRole.UserRole + 4
    Description = Qt.ItemDataRole.UserRole + 5
    Priority = Qt.ItemDataRole.UserRole + 6
    Done = Qt.ItemDataRole.UserRole + 7
    TaskId = Qt.ItemDataRole.UserRole + 8
    SortKey = Qt.ItemDataRole.UserRole + 9
    SortDirection = Qt.ItemDataRole.UserRole + 10
    DisplayTime = Qt.ItemDataRole.UserRole + 11
    ProjectTitle = Qt.ItemDataRole.UserRole + 12
    Expanded = Qt.ItemDataRole.UserRole + 13
    HasSubtasks = Qt.ItemDataRole.UserRole + 14
    SubtasksExpanded = Qt.ItemDataRole.UserRole + 15
    SubtaskDepth = Qt.ItemDataRole.UserRole + 16
    ProjectArea = Qt.ItemDataRole.UserRole + 17
    AttachmentSummary = Qt.ItemDataRole.UserRole + 18
    RecurrenceKind = Qt.ItemDataRole.UserRole + 19
    CompletionDelayMinutes = Qt.ItemDataRole.UserRole + 20
    ParentTaskId = Qt.ItemDataRole.UserRole + 21
    MarkerColor = Qt.ItemDataRole.UserRole + 22
    MarkerTheme = Qt.ItemDataRole.UserRole + 23


def is_marker_only_task_update(previous: TaskRow, updated: TaskRow) -> bool:
    """Возвращает True, если изменились только свойства маркера."""
    marker_changed = (
        previous.marker_color != updated.marker_color
        or previous.marker_theme != updated.marker_theme
    )
    if not marker_changed:
        return False
    return (
        previous.id == updated.id
        and previous.day == updated.day
        and previous.time_text == updated.time_text
        and previous.title == updated.title
        and previous.description == updated.description
        and previous.priority == updated.priority
        and previous.done == updated.done
        and previous.project_id == updated.project_id
        and previous.project_title == updated.project_title
        and previous.project_area == updated.project_area
        and previous.parent_id == updated.parent_id
        and previous.recurrence_kind == updated.recurrence_kind
        and previous.recurrence_interval == updated.recurrence_interval
        and previous.completion_delay_minutes == updated.completion_delay_minutes
    )


def blend_task_row_background(base: QColor, marker_color: str, selected: bool) -> QColor:
    """Подмешивает цвет маркера в фон строки, включая выделенную строку."""
    tint = QColor((marker_color or "").strip())
    if not tint.isValid():
        return base
    marker_weight = 0.22 if selected else 0.35
    base_weight = 1.0 - marker_weight
    return QColor(
        int(base.red() * base_weight + tint.red() * marker_weight),
        int(base.green() * base_weight + tint.green() * marker_weight),
        int(base.blue() * base_weight + tint.blue() * marker_weight),
    )


def format_task_list_title(task_id: object, title: str) -> str:
    """Builds the visible task title used by the tasks list UI."""
    base_title = (title or "").strip()
    if not base_title:
        base_title = "Без названия"
    try:
        normalized_task_id = int(cast(Any, task_id))
    except (TypeError, ValueError):
        return base_title
    if normalized_task_id <= 0:
        return base_title
    return f"MN-{normalized_task_id}: {base_title}"


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
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
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

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
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
                t.marker_color,
                t.marker_theme,
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

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
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
            if role == Qt.ItemDataRole.DisplayRole:
                return r.day.isoformat()
            return None

        if isinstance(r, SortHeaderRow):
            if role == TaskRoles.SortKey:
                return self._sort_key
            if role == TaskRoles.SortDirection:
                return "asc" if self._sort_asc else "desc"
            if role == Qt.ItemDataRole.DisplayRole:
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
        if role == TaskRoles.ParentTaskId:
            return r.parent_id
        if role == TaskRoles.MarkerColor:
            return r.marker_color
        if role == TaskRoles.MarkerTheme:
            return r.marker_theme
        if role == Qt.ItemDataRole.DisplayRole:
            return format_task_list_title(r.id, r.title)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Задает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
            if self._drag_enabled:
                flags |= Qt.ItemFlags(Qt.ItemFlag.ItemIsDropEnabled)
            return flags
        if isinstance(r, SortHeaderRow):
            return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags |= Qt.ItemFlag.ItemIsSelectable
        if self._drag_enabled:
            flags |= Qt.ItemFlag.ItemIsDragEnabled
            flags |= Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def set_filter_mode(self, mode: str):
        """Устанавливает фильтр по режиму и перестраивает список."""
        self._filter_mode = mode
        self._drag_enabled = (mode == "План")
        self._rebuild()

    def filter_mode(self) -> str:
        """Возвращает текущий режим фильтра."""
        return self._filter_mode

    def set_search(self, text: str):
        """Обновляет строку поиска и перестраивает список."""
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
        parent_id: Optional[int] = None,
        recurrence_kind: str = "",
        recurrence_interval: int = 1,
        marker_color: str = "",
        marker_theme: str = "",
    ):
        """Добавляет новую задачу и перестраивает текущий список."""
        task = self._db.create_task(
            title=title,
            description=description,
            day=day,
            time_text=time_text,
            priority=priority,
            project_id=project_id,
            parent_id=parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
            marker_color=marker_color,
            marker_theme=marker_theme,
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
                task.completion_delay_minutes,
                task.marker_color,
                task.marker_theme,
            )
        )
        self._rebuild()

    def quick_add_subtask(self, parent_task_id: int) -> None:
        parent_task = next(
            (it for it in self._all_rows if isinstance(it, TaskRow) and it.id == parent_task_id),
            None,
        )
        if parent_task is None:
            return
        self.add_task(
            title="Новая подзадача",
            description="",
            day=parent_task.day,
            time_text=parent_task.time_text,
            priority=parent_task.priority or "Medium",
            project_id=parent_task.project_id,
            parent_id=parent_task.id,
            recurrence_kind="",
            recurrence_interval=1,
            marker_color=parent_task.marker_color,
            marker_theme=parent_task.marker_theme,
        )

    def quick_add_task_for_day(self, target_day: date) -> None:
        self.add_task(
            title="Новая задача",
            description="",
            day=target_day,
            time_text="",
            priority="Medium",
        )

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
        marker_color: str = "",
        marker_theme: str = "",
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
            marker_color=marker_color,
            marker_theme=marker_theme,
        )
        priority_changed = r.priority != updated.priority
        cascade_needed = (
            (r.priority == "Отложенная" and updated.priority != "Отложенная")
            or (r.priority != "Отложенная" and updated.priority == "Отложенная")
        )
        if priority_changed and cascade_needed:
            self._reload_from_db()
            return

        updated_row = TaskRow(
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
            updated.completion_delay_minutes,
            updated.marker_color,
            updated.marker_theme,
        )
        self._all_rows = [
            updated_row if isinstance(it, TaskRow) and it.id == r.id else it
            for it in self._all_rows
        ]

        if is_marker_only_task_update(r, updated_row):
            changed_row_idx = -1
            new_rows: List[Row] = []
            for idx, it in enumerate(self._rows):
                if isinstance(it, TaskRow) and it.id == r.id:
                    changed_row_idx = idx
                    new_rows.append(updated_row)
                else:
                    new_rows.append(it)
            self._rows = new_rows
            if changed_row_idx >= 0:
                idx = self.index(changed_row_idx, 0)
                if idx.isValid():
                    self.dataChanged.emit(
                        idx,
                        idx,
                        [
                            TaskRoles.MarkerColor,
                            TaskRoles.MarkerTheme,
                            TaskRoles.ProjectTitle,
                            Qt.ItemDataRole.DisplayRole,
                        ],
                    )
                    return
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
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
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
                    updated.completion_delay_minutes,
                    updated.marker_color,
                    updated.marker_theme,
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

        target_project_id = task.project_id
        if parent_id is not None:
            parent_task = next(
                (it for it in self._all_rows if isinstance(it, TaskRow) and it.id == parent_id),
                None,
            )
            if parent_task is None:
                return False
            if self._is_descendant(parent_id, task.id):
                return False
            target_project_id = self._resolve_top_parent_project_id(parent_task)

        updated = self._db.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            day=task.day,
            time_text=task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=target_project_id,
            parent_id=parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
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
                    updated.completion_delay_minutes,
                    updated.marker_color,
                    updated.marker_theme,
                )
            new_all.append(it)
        self._all_rows = new_all
        self._rebuild()
        return True

    def task_by_id(self, task_id: int) -> Optional[TaskRow]:
        """Возвращает задачу по идентификатору или None."""
        return next((it for it in self._all_rows if isinstance(it, TaskRow) and it.id == task_id), None)

    def _resolve_top_parent_project_id(self, parent_task: TaskRow) -> Optional[int]:
        """Возвращает project_id верхнего родителя в цепочке parent_id."""
        by_id = {it.id: it for it in self._all_rows if isinstance(it, TaskRow)}
        current = parent_task
        seen: set[int] = set()
        while current.parent_id is not None and current.parent_id in by_id and current.id not in seen:
            seen.add(current.id)
            current = by_id[current.parent_id]
        return current.project_id

    def move_task_to_parent_schedule(self, task_id: int, parent_task_id: int) -> bool:
        """Переносит задачу на дату и время родительской задачи."""
        task = self.task_by_id(task_id)
        parent_task = self.task_by_id(parent_task_id)
        if task is None or parent_task is None:
            return False
        if task.id == parent_task.id:
            return False
        if task.day == parent_task.day and task.time_text == parent_task.time_text:
            return False

        updated = self._db.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            day=parent_task.day,
            time_text=parent_task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=task.project_id,
            parent_id=task.parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
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
                    updated.completion_delay_minutes,
                    updated.marker_color,
                    updated.marker_theme,
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
        """Перестраивает список задач с учетом фильтров и поиска."""
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
            except ValueError:
                return datetime.min.time()

        priority_order = {"high": 0, "medium": 1, "low": 2, "отложенная": 3}

        def sort_key(task_item: TaskRow):
            if self._sort_key == "title":
                return task_item.title.lower(), task_item.day, time_key(task_item.time_text), task_item.id
            if self._sort_key == "priority":
                if self._filter_mode == "Все":
                    return (
                        priority_order.get(task_item.priority.lower(), 4),
                        task_item.day,
                        time_key(task_item.time_text),
                        task_item.id,
                    )
                return (
                    task_item.day,
                    priority_order.get(task_item.priority.lower(), 4),
                    time_key(task_item.time_text),
                    task_item.id,
                )
            return task_item.day, time_key(task_item.time_text), task_item.id

        task_ids = {t.id for t in base_tasks}
        children_map: dict[Optional[int], List[TaskRow]] = {}
        for base_task in base_tasks:
            parent_id = base_task.parent_id if base_task.parent_id in task_ids else None
            children_map.setdefault(parent_id, []).append(base_task)
        for parent_id, parent_children in children_map.items():
            if parent_id is None or not parent_children:
                continue
            if parent_id not in self._subtask_state_initialized:
                self._collapsed_subtask_ids.add(parent_id)
                self._subtask_state_initialized.add(parent_id)

        include_cache: dict[int, bool] = {}

        def should_include(task_item: TaskRow) -> bool:
            if not search:
                return True
            cached = include_cache.get(task_item.id)
            if cached is not None:
                return cached
            if task_item.id in search_hits:
                include_cache[task_item.id] = True
                return True
            for child in children_map.get(task_item.id, []):
                if should_include(child):
                    include_cache[task_item.id] = True
                    return True
            include_cache[task_item.id] = False
            return False

        def sorted_children(task_item: TaskRow) -> List[TaskRow]:
            children = [child for child in children_map.get(task_item.id, []) if should_include(child)]
            children.sort(key=sort_key, reverse=(self._filter_mode == "Все" and not self._sort_asc))
            return children

        new_rows: List[Row] = []
        self._task_children = {}
        self._task_depths = {}

        def append_task(task_item: TaskRow, depth: int) -> None:
            self._task_depths[task_item.id] = depth
            child_rows = sorted_children(task_item)
            if child_rows:
                self._task_children[task_item.id] = child_rows
            new_rows.append(task_item)
            if task_item.id in self._collapsed_subtask_ids:
                return
            for child in child_rows:
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
                roots.sort(key=lambda task_item: task_item.day, reverse=True)
            for root_task in roots:
                if current_day != root_task.day:
                    current_day = root_task.day
                    new_rows.append(HeaderRow(current_day))
                append_task(root_task, 0)

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
            self.dataChanged.emit(idx, idx, [TaskRoles.Expanded, Qt.ItemDataRole.SizeHintRole])

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

    def supportedDropActions(self) -> Qt.DropAction:
        """Разрешает перенос с изменением позиции."""
        return Qt.DropAction.MoveAction

    def dropMimeData(self, data, action, row, column, parent) -> bool:
        """Обрабатывает перенос задачи между днями."""
        if action == Qt.DropAction.IgnoreAction:
            return True
        if not self._drag_enabled:
            return False
        if not data.hasFormat("application/x-mindnavigator-task-id"):
            return False

        task_id_bytes = data.data("application/x-mindnavigator-task-id")
        try:
            task_id_payload = bytes(task_id_bytes.data())
            task_id = int(task_id_payload.decode("utf-8"))
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
        self.setWindowState(self.windowState() | Qt.WindowState.WindowFullScreen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setObjectName("TaskImagePreviewLabel")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        if event.key() == Qt.Key.Key_Left:
            self._show_previous()
            return
        if event.key() == Qt.Key.Key_Right:
            self._show_next()
            return
        if event.key() == Qt.Key.Key_Escape:
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
        scaled = pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
        scroll.setFrameShape(QFrame.Shape.NoFrame)
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
        desc_layout.addWidget(desc_title)
        desc_layout.addWidget(_build_markdown_preview_widget(task.description, desc_block))
        content_layout.addWidget(desc_block)

        props_block = QFrame()
        props_block.setObjectName("TaskDetailsProps")
        props_layout = QVBoxLayout(props_block)
        props_layout.setContentsMargins(14, 12, 14, 12)
        props_title = QLabel("Свойства")
        props_title.setObjectName("TaskDetailsSectionTitle")
        props_layout.addWidget(props_title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
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
        ideas = self._db.fetch_ideas(archived=True)
        objects = self._db.fetch_objects()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        cloud_files = self._db.fetch_cloud_files()
        self._notes_by_id = {note.id: note for note in notes}
        self._ideas_by_id = {idea.id: idea for idea in ideas}
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
            link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            link_label.setOpenExternalLinks(False)
            link_label.linkActivated.connect(lambda _link, att=attachment: self._open_attachment(att))

            row_layout.addWidget(kind_label)
            row_layout.addWidget(link_label, 1)
            self.attachments_list.addWidget(row)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    @staticmethod
    def _cloud_file_link_text(file_item) -> str:
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
        if attachment.kind == "idea":
            idea = self._ideas_by_id.get(attachment.ref_id)
            if not idea:
                return "Идея не найдена"
            if idea.project_title:
                return f"{idea.title} · {idea.project_title}"
            return idea.title
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
        if attachment.kind == "idea":
            idea = self._ideas_by_id.get(attachment.ref_id)
            if not idea:
                QMessageBox.warning(self, "Вложения", "Идея не найдена.")
                return
            rows = [
                ("Название", idea.title),
                ("Проект", idea.project_title or "—"),
                ("Тип", idea.type or "—"),
                ("Статус", idea.status or "—"),
                ("Ценность", str(idea.value_score)),
                ("Сложность", str(idea.effort_score)),
                ("Источник", idea.source or "—"),
                ("Обновлено", idea.updated_at.strftime("%d.%m.%Y %H:%M")),
                ("Кратко", idea.summary or "—"),
                ("Описание", idea.body_md or "—"),
            ]
            self._open_info_dialog("Идея", rows, wrap_rows={"Кратко", "Описание"})
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
                ("Плитки", f"{map_item.tiles_w} × {map_item.tiles_h}"),
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
            if label in wrap_rows:
                value_label = _build_markdown_preview_widget(value, dialog)
            else:
                value_label = QLabel(value or "—")
            form.addRow(label, value_label)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
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
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
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
        self.project_create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.day_edit.setDate(QDate(task.day.year, task.day.month, task.day.day))
        self.day_edit.setKeyboardTracking(False)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(9, 0))
        self.time_edit.setKeyboardTracking(False)

        self.time_toggle = QCheckBox("Указать")
        self.time_toggle.setCursor(Qt.CursorShape.PointingHandCursor)

        if task.time_text:
            try:
                parsed = datetime.strptime(task.time_text, "%H:%M").time()
                self.time_edit.setTime(QTime(parsed.hour, parsed.minute))
                self.time_toggle.setChecked(True)
            except ValueError:
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
        self.recurrence_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
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

        self.marker_color_edit = QComboBox()
        self.marker_color_edit.addItem("Нет", "")
        self.marker_color_edit.addItem("Синий", "#2f6edb")
        self.marker_color_edit.addItem("Зеленый", "#2f9f63")
        self.marker_color_edit.addItem("Оранжевый", "#d68a2f")
        self.marker_color_edit.addItem("Красный", "#b74a4a")
        self.marker_color_edit.addItem("Фиолетовый", "#6b5ad4")
        marker_color_idx = self.marker_color_edit.findData((task.marker_color or "").strip())
        if marker_color_idx >= 0:
            self.marker_color_edit.setCurrentIndex(marker_color_idx)

        self.marker_theme_edit = QComboBox()
        self.marker_theme_edit.addItem("Нет", "")
        self.marker_theme_edit.addItem("Фильмы", "movies")
        self.marker_theme_edit.addItem("Игры", "games")
        self.marker_theme_edit.addItem("Книги", "books")
        self.marker_theme_edit.addItem("Музыка", "music")
        self.marker_theme_edit.addItem("Работа", "work")
        self.marker_theme_edit.addItem("Личное", "personal")
        self.marker_theme_edit.addItem("Разработка", "dev")
        marker_theme_idx = self.marker_theme_edit.findData((task.marker_theme or "").strip().lower())
        if marker_theme_idx >= 0:
            self.marker_theme_edit.setCurrentIndex(marker_theme_idx)

        self.done_edit = QCheckBox("Выполнено")
        self.done_edit.setChecked(task.done)

        form.addRow("Название", self.title_edit)
        form.addRow("Описание", self.description_edit)
        form.addRow("Проект", project_row)
        form.addRow("Дата и время", time_block)
        form.addRow("Повтор", recurrence_row)
        form.addRow("Приоритет", self.priority_edit)
        form.addRow("Маркер (цвет)", self.marker_color_edit)
        form.addRow("Тема маркера", self.marker_theme_edit)
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
        self.attachments_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_accept)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self._on_accept)

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
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
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
        ideas = self._db.fetch_ideas(archived=True)
        objects = self._db.fetch_objects()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        cloud_files = self._db.fetch_cloud_files()
        self._notes_by_id = {note.id: note for note in notes}
        self._ideas_by_id = {idea.id: idea for idea in ideas}
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
            link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            link_label.setOpenExternalLinks(False)
            link_label.linkActivated.connect(lambda _link, att=attachment: self._open_attachment(att))

            remove_btn = QToolButton()
            remove_btn.setObjectName("TaskAttachmentRemove")
            remove_btn.setIcon(qta.icon("fa5s.times", color="#cfcfcf"))
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(lambda _checked=False, att=attachment: self._remove_attachment(att))

            row_layout.addWidget(kind_label)
            row_layout.addWidget(link_label, 1)
            row_layout.addWidget(remove_btn)
            self.attachments_list.addWidget(row)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    @staticmethod
    def _attachment_kind_label(kind: str) -> str:
        return attachment_kind_label(kind)

    @staticmethod
    def _cloud_file_link_text(file_item) -> str:
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
        if attachment.kind == "idea":
            idea = self._ideas_by_id.get(attachment.ref_id)
            if not idea:
                return "Идея не найдена"
            if idea.project_title:
                return f"{idea.title} · {idea.project_title}"
            return idea.title
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
            ("Идея", "idea"),
            ("Объект", "object"),
            ("Карта", "map"),
            ("Метка карты", "marker"),
            ("Файл", "file"),
            ("Изображение", "image"),
        ]
        for label, key in kind_items:
            kind_combo.addItem(label, key)

        item_combo = QComboBox()

        def fill_items(selected_kind: str) -> None:
            item_combo.clear()
            if selected_kind == "note":
                for note_row in sorted(self._notes_by_id.values(), key=lambda note: note.title.lower()):
                    row_label = f"{note_row.title} · {note_row.project}" if note_row.project else note_row.title
                    item_combo.addItem(row_label, note_row.id)
            elif selected_kind == "idea":
                for idea_row in sorted(self._ideas_by_id.values(), key=lambda idea: idea.title.lower()):
                    row_label = (
                        f"{idea_row.title} · {idea_row.project_title}" if idea_row.project_title else idea_row.title
                    )
                    item_combo.addItem(row_label, idea_row.id)
            elif selected_kind == "object":
                for object_row in sorted(self._objects_by_id.values(), key=lambda obj: obj.title.lower()):
                    row_label = f"{object_row.title} · {object_row.catalog}" if object_row.catalog else object_row.title
                    item_combo.addItem(row_label, object_row.id)
            elif selected_kind == "map":
                for map_row in sorted(self._maps_by_id.values(), key=lambda map_item: map_item.title.lower()):
                    row_label = f"{map_row.title} · {map_row.project}" if map_row.project else map_row.title
                    item_combo.addItem(row_label, map_row.id)
            elif selected_kind == "marker":
                markers = sorted(self._markers_by_id.values(), key=lambda marker_row: marker_row.name.lower())
                for marker in markers:
                    map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else ""
                    marker_label = f"{marker.name} · {map_title}" if map_title else marker.name
                    item_combo.addItem(marker_label, marker.id)
            elif selected_kind in {"file", "image"}:
                files = [
                    file_row
                    for file_row in self._cloud_files_by_id.values()
                    if file_row.is_image == (selected_kind == "image")
                ]
                files = sorted(files, key=lambda file_row: file_row.name.lower())
                for file_row in files:
                    item_combo.addItem(self._cloud_file_link_text(file_row), file_row.id)
            if item_combo.count() == 0:
                item_combo.addItem("— нет доступных —", None)

        kind_combo.currentIndexChanged.connect(lambda idx: fill_items(kind_combo.currentData()))
        fill_items(kind_combo.currentData())

        form.addRow("Тип", kind_combo)
        form.addRow("Элемент", item_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
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

        if dialog.exec() != QDialog.DialogCode.Accepted:
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
        if attachment.kind == "idea":
            idea = self._ideas_by_id.get(attachment.ref_id)
            if not idea:
                QMessageBox.warning(self, "Вложения", "Идея не найдена.")
                return
            rows = [
                ("Название", idea.title),
                ("Проект", idea.project_title or "—"),
                ("Тип", idea.type or "—"),
                ("Статус", idea.status or "—"),
                ("Ценность", str(idea.value_score)),
                ("Сложность", str(idea.effort_score)),
                ("Источник", idea.source or "—"),
                ("Обновлено", idea.updated_at.strftime("%d.%m.%Y %H:%M")),
                ("Кратко", idea.summary or "—"),
                ("Описание", idea.body_md or "—"),
            ]
            self._open_info_dialog("Идея", rows, wrap_rows={"Кратко", "Описание"})
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
                ("Плитки", f"{map_item.tiles_w} × {map_item.tiles_h}"),
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
            if label in wrap_rows:
                value_label = _build_markdown_preview_widget(value, dialog)
            else:
                value_label = QLabel(value or "—")
            form.addRow(label, value_label)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
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
            "marker_color": self.marker_color_edit.currentData() or "",
            "marker_theme": self.marker_theme_edit.currentData() or "",
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
            save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
            if save_button is not None:
                save_button.setText("Создать")
        self.title_edit.setFocus()


class TasksItemDelegate(QStyledItemDelegate):
    ROW_H = 42
    HEADER_H = 32
    TIME_W = 140
    PROJECT_W = 420
    TEXT_V_PAD = 8
    TEXT_GAP = 6
    ROW_H_EXPANDED_MIN = 82
    TAG_H = 20
    TAG_PAD_X = 8
    TAG_GAP = 6
    TAG_LINE_GAP = 6
    PARENT_MOVE_BUTTON_H = 22
    PARENT_MOVE_BUTTON_PAD_X = 10
    PARENT_MOVE_BUTTON_GAP = 8

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

    @staticmethod
    def _tasks_model(model: QAbstractItemModel | None) -> Optional[TasksModel]:
        if isinstance(model, TasksModel):
            return model
        return None

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Возвращает размер строки списка."""
        option_rect = getattr(option, "rect", QRect())
        row_type = index.data(TaskRoles.RowType)
        if row_type in ("header", "sort_header"):
            return QSize(option_rect.width(), self.HEADER_H)
        expanded = bool(index.data(TaskRoles.Expanded))
        if not expanded:
            return QSize(option_rect.width(), self.ROW_H)

        title = index.data(Qt.ItemDataRole.DisplayRole) or ""
        description = index.data(TaskRoles.Description) or ""
        depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
        has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
        layout = self._row_layout(option_rect, depth, has_subtasks)
        text_width = max(10, layout["title"].width())

        title_metrics = QFontMetrics(self._font)
        desc_metrics = QFontMetrics(self._font_small)
        title_height = title_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextFlag.TextWordWrap, title).height()
        desc_height = 0
        if description:
            desc_height = desc_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextFlag.TextWordWrap, description).height()

        tags = index.data(TaskRoles.AttachmentSummary) or []
        total_height = title_height + desc_height
        if description:
            total_height += self.TEXT_GAP
        if tags:
            total_height += self.TEXT_GAP + self._tags_height(tags, text_width)
        total_height += self.TEXT_V_PAD * 2
        total_height = max(total_height, self.ROW_H_EXPANDED_MIN)
        return QSize(option_rect.width(), total_height)

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
            painter.drawText(rect.adjusted(self.TAG_PAD_X, 0, -self.TAG_PAD_X, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, tag)
            x += tag_width + self.TAG_GAP

    def _header_quick_rect(
        self,
        row_rect: QRect,
        header_text: str,
        include_today_badge: bool = False,
    ) -> QRect:
        metrics = QFontMetrics(self._font_header)
        text_left = row_rect.left() + 10
        text_width = metrics.horizontalAdvance(header_text)
        today_badge_width = metrics.horizontalAdvance("СЕГОДНЯ") if include_today_badge else 0
        quick_width = 116
        quick_height = row_rect.height() - 12
        quick_x = text_left + text_width + 14 + today_badge_width
        max_right = row_rect.right() - 12
        if quick_x + quick_width > max_right:
            quick_x = max(text_left + 10, max_right - quick_width)
        return QRect(quick_x, row_rect.top() + 6, quick_width, quick_height)

    @staticmethod
    def _task_quick_rect(layout: dict, row_rect: QRect) -> QRect:
        quick_width = 22
        quick_height = row_rect.height() - 14
        toggle_rect = layout.get("subtask_toggle")
        if isinstance(toggle_rect, QRect) and not toggle_rect.isNull():
            anchor_left = toggle_rect.left()
        else:
            doc_rect = layout.get("doc")
            anchor_left = doc_rect.left() if isinstance(doc_rect, QRect) else row_rect.left() + 80
        quick_x = max(row_rect.left() + 8, anchor_left - quick_width - 4)
        return QRect(quick_x, row_rect.top() + 7, quick_width, quick_height)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Рисует строку задачи или заголовок дня."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        row_type = index.data(TaskRoles.RowType)
        r = getattr(option, "rect", QRect())
        option_state = getattr(option, "state", QStyle.StateFlag.State_None)

        if row_type == "header":
            d: date = index.data(TaskRoles.Day)
            txt = self._format_header(d)
            show_today = should_show_today_badge(d)
            painter.fillRect(r, self.C_BG)

            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            quick_rect = self._header_quick_rect(r, txt, include_today_badge=show_today)
            text_rect = QRect(r.left() + 10, r.top(), quick_rect.left() - r.left() - 18, r.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, txt)

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
                painter.drawText(today_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "СЕГОДНЯ")

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            if option_state & QStyle.StateFlag.State_MouseOver:
                painter.setPen(self.C_BORDER)
                painter.setBrush(QColor("#1f2227"))
                painter.drawRoundedRect(quick_rect, 4, 4)
                painter.setFont(self._font_small)
                painter.setPen(self.C_DIM)
                painter.drawText(quick_rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Добавить задачу")
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
            painter.drawText(layout["date"], Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"Дата {arrow}" if sort_key == "date" else "Дата")
            painter.drawText(layout["title"], Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"Название {arrow}" if sort_key == "title" else "Название")
            painter.drawText(layout["priority"], Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                             f"Приоритет {arrow}" if sort_key == "priority" else "Приоритет")

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.restore()
            return

        day: date = index.data(TaskRoles.Day)
        time_text: str = index.data(TaskRoles.DisplayTime) or ""
        title: str = index.data(Qt.ItemDataRole.DisplayRole) or ""
        description: str = index.data(TaskRoles.Description) or ""
        project_title: str = index.data(TaskRoles.ProjectTitle) or ""
        project_area: str = index.data(TaskRoles.ProjectArea) or ""
        recurrence_kind: str = (index.data(TaskRoles.RecurrenceKind) or "").strip().lower()
        marker_color: str = (index.data(TaskRoles.MarkerColor) or "").strip()
        marker_theme: str = (index.data(TaskRoles.MarkerTheme) or "").strip()
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
        selected = bool(option_state & QStyle.StateFlag.State_Selected)
        if selected:
            bg = QColor("#343844")
        bg = blend_task_row_background(bg, marker_color, selected=selected)

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
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, time_text)

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
            if marker_theme:
                display_project = f"{display_project} · {marker_theme.upper()}"
            elided_project = QFontMetrics(self._font_small).elidedText(
                display_project,
                Qt.TextElideMode.ElideRight,
                project_rect.width(),
            )
            painter.drawText(project_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_project)

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
        parent_move_rect, parent_move_target, parent_move_text = self._parent_schedule_action(index, r)
        title_content_rect = title_rect
        if not parent_move_rect.isNull():
            title_content_rect = title_rect.adjusted(0, 0, -(parent_move_rect.width() + self.PARENT_MOVE_BUTTON_GAP), 0)
        quick_rect = self._task_quick_rect(layout, r)
        if expanded:
            title_box = QRect(
                title_content_rect.left(),
                r.top() + self.TEXT_V_PAD,
                title_content_rect.width(),
                r.height() - self.TEXT_V_PAD * 2,
            )
            painter.drawText(title_box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, title)

            title_metrics = QFontMetrics(self._font)
            title_height = title_metrics.boundingRect(
                0, 0, title_content_rect.width(), 1000, Qt.TextFlag.TextWordWrap, title
            ).height()
            current_y = r.top() + self.TEXT_V_PAD + title_height

            if completion_delay_text:
                delay_box = QRect(
                    title_content_rect.left(),
                    current_y + self.TEXT_GAP,
                    title_content_rect.width(),
                    title_metrics.height(),
                )
                painter.setPen(self.C_OVERDUE)
                painter.drawText(delay_box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, completion_delay_text)
                painter.setPen(title_color)
                current_y += self.TEXT_GAP + title_metrics.height()

            if description:
                desc_box = QRect(
                    title_content_rect.left(),
                    current_y + self.TEXT_GAP,
                    title_content_rect.width(),
                    r.height() - self.TEXT_V_PAD * 2 - title_height - self.TEXT_GAP,
                )
                painter.setFont(self._font_small)
                painter.setPen(self.C_DIM if not overdue else self.C_OVERDUE)
                painter.drawText(desc_box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, description)
                painter.setFont(self._font)
                desc_metrics = QFontMetrics(self._font_small)
                desc_height = desc_metrics.boundingRect(
                    0, 0, title_content_rect.width(), 1000, Qt.TextFlag.TextWordWrap, description
                ).height()
                current_y += self.TEXT_GAP + desc_height

            tags = index.data(TaskRoles.AttachmentSummary) or []
            if tags:
                current_y += self.TEXT_GAP
                self._draw_tags(painter, QPoint(title_content_rect.left(), current_y), title_content_rect.width(), tags)
        else:
            title_metrics = QFontMetrics(self._font)
            if completion_delay_text:
                delay_text = f" {completion_delay_text}"
                delay_width = title_metrics.horizontalAdvance(delay_text)
                title_width = max(40, title_content_rect.width() - delay_width)
                title_part = title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, title_width)
                title_part_rect = QRect(title_content_rect.left(), title_content_rect.top(), title_width, title_content_rect.height())
                delay_part_rect = QRect(
                    title_part_rect.right(),
                    title_content_rect.top(),
                    title_content_rect.width() - title_width,
                    title_content_rect.height(),
                )
                painter.setPen(title_color)
                painter.drawText(title_part_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title_part)
                painter.setPen(self.C_OVERDUE)
                painter.drawText(delay_part_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, delay_text)
                painter.setPen(title_color)
            else:
                elided = title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, title_content_rect.width())
                painter.drawText(title_content_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)

        if not parent_move_rect.isNull() and parent_move_target is not None:
            painter.setPen(QColor("#8a6a15"))
            painter.setBrush(QColor("#f2c14e"))
            painter.drawRoundedRect(parent_move_rect, 6, 6)
            painter.setFont(self._font_small)
            painter.setPen(QColor("#2d250f"))
            text_rect = parent_move_rect.adjusted(
                self.PARENT_MOVE_BUTTON_PAD_X,
                0,
                -self.PARENT_MOVE_BUTTON_PAD_X,
                0,
            )
            text = QFontMetrics(self._font_small).elidedText(parent_move_text, Qt.TextElideMode.ElideRight, text_rect.width())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        # --- PRIORITY BLOCK (fixed layout) ---
        value_text = "OVERDUE" if overdue else priority
        value_color = self.C_OVERDUE if overdue else self._prio_color(priority)

        # Жёсткая сетка справа
        icon_w = 18
        value_w = 72
        gap = 10
        label_w = pr_rect.width() - value_w - icon_w - gap

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
        # painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "приоритет")

        # value
        painter.setPen(value_color)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, value_text)

        # icon
        self._icon_fire.paint(painter, icon_rect)

        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 5, menu_rect.center().y() - 7, 14, 14))
        if option_state & QStyle.StateFlag.State_MouseOver:
            painter.setPen(self.C_BORDER)
            painter.setBrush(QColor("#1f2227"))
            painter.drawRoundedRect(quick_rect, 4, 4)
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_small)
            painter.drawText(quick_rect, Qt.AlignmentFlag.AlignCenter, "+")

        painter.restore()

    def editorEvent(
        self,
        event: QEvent,
        model: QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        """Обрабатывает клики по флажку и меню строки."""
        row_type = index.data(TaskRoles.RowType)
        if row_type == "sort_header":
            if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                layout = self._row_layout(getattr(option, "rect", QRect()))
                tasks_model = self._tasks_model(model)
                if layout["title"].contains(pos):
                    if tasks_model is not None:
                        tasks_model.set_sort("title")
                    return True
                if layout["date"].contains(pos):
                    if tasks_model is not None:
                        tasks_model.set_sort("date")
                    return True
                if layout["priority"].contains(pos):
                    if tasks_model is not None:
                        tasks_model.set_sort("priority")
                    return True
            return False
        if row_type == "header":
            if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                r = getattr(option, "rect", QRect())
                header_day = index.data(TaskRoles.Day)
                header_text = self._format_header(header_day) if isinstance(header_day, date) else ""
                quick_rect = self._header_quick_rect(
                    r,
                    header_text,
                    include_today_badge=(
                        isinstance(header_day, date) and should_show_today_badge(header_day)
                    ),
                )
                tasks_model = self._tasks_model(model)
                if quick_rect.contains(pos) and tasks_model is not None:
                    target_day = index.data(TaskRoles.Day)
                    if isinstance(target_day, date):
                        tasks_model.quick_add_task_for_day(target_day)
                        return True
            return False
        if row_type != "task":
            return False

        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            r = getattr(option, "rect", QRect())
            tasks_model = self._tasks_model(model)
            if tasks_model is None:
                return False

            depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
            has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
            layout = self._row_layout(r, depth, has_subtasks)
            cb_rect = layout["checkbox"]
            tomorrow_rect = layout["tomorrow"]
            menu_rect = layout["menu"]
            toggle_rect = layout.get("subtask_toggle")
            parent_move_rect, parent_move_target, _ = self._parent_schedule_action(index, r)
            quick_rect = self._task_quick_rect(layout, r)

            if has_subtasks and toggle_rect and toggle_rect.contains(pos):
                tasks_model.toggle_subtasks_expanded_by_row(index.row())
                return True

            if tomorrow_rect.contains(pos):
                task = tasks_model.task_at_row(index.row())
                if task is not None:
                    new_day = tasks_model.next_day_for_task(task)
                    tasks_model.move_task_to_day(task.id, new_day)
                return True

            if not parent_move_rect.isNull() and parent_move_target is not None and parent_move_rect.contains(pos):
                task = tasks_model.task_at_row(index.row())
                if task is not None:
                    tasks_model.move_task_to_parent_schedule(task.id, parent_move_target.id)
                return True

            if cb_rect.contains(pos):
                # confirm только если ставим done=True
                currently_done = bool(index.data(TaskRoles.Done))
                if not currently_done:
                    option_widget = getattr(option, "widget", None)
                    parent = option_widget if isinstance(option_widget, QWidget) else None
                    dialog = ConfirmDialog(
                        "Подтверждение",
                        "Пометить задачу выполненной?",
                        parent=parent,
                        confirm_text="Да",
                        cancel_text="Отмена",
                    )
                    if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
                        return True  # событие обработали, но действие отменили

                tasks_model.toggle_done_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True
            if quick_rect.contains(pos):
                task = tasks_model.task_at_row(index.row())
                if task is not None:
                    tasks_model.quick_add_subtask(task.id)
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
        if show_dialog_standard(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        m = index.model()
        tasks_model = self._tasks_model(m)
        if tasks_model is not None:
            tasks_model.delete_task_by_row(index.row())

    def _edit_task(self, index: QModelIndex):
        """Открывает диалог редактирования задачи."""
        tasks_model = self._tasks_model(index.model())
        if tasks_model is None:
            return

        task = tasks_model.task_at_row(index.row())
        if task is None:
            return

        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = TaskEditDialog(task, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        try:
            tasks_model.update_task_by_row(
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
                marker_color=values["marker_color"],
                marker_theme=values["marker_theme"],
            )
        except ValueError as exc:
            QMessageBox.warning(parent or self.parent(), "Проверка", str(exc))

    def edit_task(self, index: QModelIndex) -> None:
        self._edit_task(index)

    def _open_task_view(self, index: QModelIndex) -> None:
        tasks_model = self._tasks_model(index.model())
        if tasks_model is None:
            return
        task = tasks_model.task_at_row(index.row())
        if task is None:
            return
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = TaskDetailsDialog(task, parent=parent)
        show_dialog_standard(dialog, parent)

    def open_task_view(self, index: QModelIndex) -> None:
        self._open_task_view(index)

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

    @staticmethod
    def _is_overdue(d: date, done: bool) -> bool:
        """Проверяет, просрочена ли задача."""
        return (d < date.today()) and (not done)

    @staticmethod
    def _format_header(d: date) -> str:
        """Формирует подпись для заголовка дня."""
        wd = WEEKDAY_RU[d.weekday()]
        return f"{d.isoformat()} — {wd}"

    def format_header(self, d: date) -> str:
        return self._format_header(d)

    @staticmethod
    def _format_completion_delay(delay_minutes: int) -> str:
        """Формирует подпись расхождения по факту выполнения."""
        minutes = max(0, int(delay_minutes or 0))
        days = minutes // (24 * 60)
        hours = (minutes % (24 * 60)) // 60
        return f"(Просрочена: {days}д {hours}ч)"

    def _parent_schedule_action(self, index: QModelIndex, row_rect: QRect) -> Tuple[QRect, Optional[TaskRow], str]:
        """Возвращает геометрию и данные кнопки переноса на срок родителя."""
        parent_id = index.data(TaskRoles.ParentTaskId)
        if parent_id is None:
            return QRect(), None, ""

        done = bool(index.data(TaskRoles.Done))
        task_day: date = index.data(TaskRoles.Day)
        if not self._is_overdue(task_day, done):
            return QRect(), None, ""

        model = index.model()
        tasks_model = self._tasks_model(model)
        if tasks_model is None:
            return QRect(), None, ""
        parent_task = tasks_model.task_by_id(parent_id)
        if parent_task is None:
            return QRect(), None, ""
        if self._is_overdue(parent_task.day, parent_task.done):
            return QRect(), None, ""

        depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
        has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
        expanded = bool(index.data(TaskRoles.Expanded))
        layout = self._row_layout(row_rect, depth, has_subtasks)
        title_rect = layout["title"]
        text = self._format_parent_schedule_text(parent_task)
        rect = self._parent_schedule_button_rect(title_rect, text, expanded)
        if rect.isNull():
            return QRect(), None, ""
        return rect, parent_task, text

    @staticmethod
    def _format_parent_schedule_text(parent_task: TaskRow) -> str:
        if parent_task.time_text:
            return f"Перенести на {parent_task.day.isoformat()} {parent_task.time_text}"
        return f"Перенести на {parent_task.day.isoformat()}"

    def _parent_schedule_button_rect(self, title_rect: QRect, text: str, expanded: bool) -> QRect:
        """Строит прямоугольник кнопки переноса справа от заголовка."""
        available_width = title_rect.width() - 20
        if available_width < 160:
            return QRect()
        metrics = QFontMetrics(self._font_small)
        target_width = metrics.horizontalAdvance(text) + self.PARENT_MOVE_BUTTON_PAD_X * 2
        button_width = min(max(180, target_width), min(420, available_width))
        button_height = self.PARENT_MOVE_BUTTON_H
        x = title_rect.right() - button_width
        if expanded:
            y = title_rect.top() + self.TEXT_V_PAD
        else:
            y = title_rect.center().y() - (button_height // 2)
        return QRect(x, y, button_width, button_height)

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
        quick_rect = QRect()
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
            "quick": quick_rect,
            "menu": menu_rect,
        }

    def row_layout(self, rect: QRect, depth: int = 0, has_subtasks: bool = False) -> dict:
        return self._row_layout(rect, depth, has_subtasks)


class TasksWorkspace(BaseWorkspace):
    """Рабочая область задач: панель управления и список с группировкой."""

    workspace_id = "tasks"
    workspace_title = "Задачи"
    GANTT_DAY_START_HOUR = 8
    GANTT_DAY_END_HOUR = 22

    def __init__(self, parent=None):
        """Создает интерфейс рабочей области задач."""
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self._focus_day = date.today()
        self._applying_filters = False
        self._gantt_mode = False
        self._smooth_scroll_controllers: list[object] = []
        self.new_title = None
        self.new_day = None
        self.new_time = None
        self.new_time_toggle = None
        self.new_priority = None
        self.btn_add = None
        self.list = None
        self.model = None
        self.delegate = None
        self._sticky_header = None
        self.content_stack = None
        self.gantt_page = None
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
            QLabel#TasksStickyHeader {
                background: #16171a;
                color: #8a8a8a;
                border-bottom: 1px solid #3a3b40;
                font-size: 9pt;
                font-weight: 600;
                padding: 0 10px;
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

    def create_actions(self) -> dict[str, QAction]:
        action_export = QAction("Экспорт", self)
        action_export.triggered.connect(self._export_tasks_csv)
        action_import = QAction("Импорт", self)
        action_import.triggered.connect(self._import_tasks_csv)
        return {
            "export": action_export,
            "import": action_import,
        }

    def build_toolbar(self, actions: dict[str, QAction]) -> None:
        while self.toolbar_layout.count():
            item = self.toolbar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.toolbar_layout.addStretch(1)
        for action in actions.values():
            button = QToolButton()
            button.setDefaultAction(action)
            self.toolbar_layout.addWidget(button)

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
        today = datetime.now().date()
        self.new_day.setDate(QDate(today.year, today.month, today.day))
        self.new_day.setToolTip("Дата выполнения (можно выбрать в календаре или ввести вручную)")
        self.new_day.setKeyboardTracking(False)

        self.new_time = QTimeEdit()
        self.new_time.setDisplayFormat("HH:mm")
        self.new_time.setFixedWidth(90)
        self.new_time.setTime(QTime.currentTime())
        self.new_time.setKeyboardTracking(False)

        self.new_time_toggle = QCheckBox("Время")
        self.new_time_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)

        create_layout.addWidget(self.new_title, 1)
        create_layout.addWidget(datetime_block)
        create_layout.addWidget(self.new_priority)
        create_layout.addWidget(self.btn_add)

        content_layout.addWidget(create)

        self.list = QListView()
        self.list.setObjectName("TasksList")
        self.list.setUniformItemSizes(False)
        self.list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.list.setMouseTracking(True)
        self.list.viewport().setMouseTracking(True)

        self.model = TasksModel(self)
        self.list.setModel(self.model)

        self.delegate = TasksItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)
        self._sticky_header = QLabel(self.list.viewport())
        self._sticky_header.setObjectName("TasksStickyHeader")
        self._sticky_header.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._sticky_header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._sticky_header.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._sticky_header.hide()

        self.btn_add.clicked.connect(self._on_create_task)
        self.new_title.returnPressed.connect(self._on_create_task)
        self.list.viewport().installEventFilter(self)

        selection_model = self.list.selectionModel()
        selection_model.selectionChanged.connect(lambda *_: self.update_action_states())
        selection_model.currentChanged.connect(lambda *_: self.update_action_states())
        self.model.modelReset.connect(self.update_action_states)
        self.model.layoutChanged.connect(self.update_action_states)
        self.model.modelReset.connect(self._update_sticky_day_header)
        self.model.layoutChanged.connect(self._update_sticky_day_header)
        self.model.rowsInserted.connect(lambda *_: self._update_sticky_day_header())
        self.model.rowsRemoved.connect(lambda *_: self._update_sticky_day_header())
        self.list.verticalScrollBar().valueChanged.connect(lambda *_: self._update_sticky_day_header())

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.list)
        self.gantt_page = self._build_gantt_page()
        self.content_stack.addWidget(self.gantt_page)
        self.content_stack.setCurrentWidget(self.list)
        content_layout.addWidget(self.content_stack, 1)
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.list),
            attach_smooth_scroll(self.gantt_table),
        ]
        self._update_sticky_day_header()

        self.set_content(content)

    def _build_gantt_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.gantt_hint = QLabel("Режим Gantt: прогноз длительности строится автоматически и сохраняется.")
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
        self.gantt_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.gantt_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table_palette = self.gantt_table.palette()
        table_palette.setColor(QPalette.ColorRole.Base, QColor("#16171a"))
        table_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1b1c20"))
        table_palette.setColor(QPalette.ColorRole.Text, QColor("#cfcfcf"))
        table_palette.setColor(QPalette.ColorRole.Mid, QColor("#3a3b40"))
        table_palette.setColor(QPalette.ColorRole.Highlight, QColor("#4f7ecf"))
        self.gantt_table.setPalette(table_palette)
        self.gantt_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.gantt_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.gantt_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
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
                    painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, label)

            start_clamped = min(max(self._start, self._day_start), self._day_end)
            end_clamped = min(max(self._end, self._day_start), self._day_end)
            if end_clamped <= start_clamped:
                return

            x1 = r.left() + int((start_clamped - self._day_start) / span * r.width())
            x2 = r.left() + int((end_clamped - self._day_start) / span * r.width())
            bar_w = max(2, x2 - x1)
            bar = QRect(x1, r.top() + 1, bar_w, max(2, baseline_y - r.top() - 1))
            painter.setPen(Qt.PenStyle.NoPen)
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
            b.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.btn_prev_day.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_day.setAutoRaise(True)

        self.btn_next_day = QToolButton()
        self.btn_next_day.setIcon(qta.icon("fa5s.chevron-right", color="#cfcfcf"))
        self.btn_next_day.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_day.setAutoRaise(True)

        self.btn_gantt = QToolButton()
        self.btn_gantt.setText("Gantt")
        self.btn_gantt.setCheckable(True)
        self.btn_gantt.setCursor(Qt.CursorShape.PointingHandCursor)
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

    def _export_tasks_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Tasks",
            "tasks_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_tasks_rows(self._db.fetch_tasks())
        if not rows:
            self.set_status("Нет данных для экспорта")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=TASKS_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Tasks", f"Export failed: {exc}")
            return
        self.set_status("Экспорт завершен")

    def _import_tasks_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Tasks",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Tasks", f"Import failed: {exc}")
            return
        result = import_tasks_rows(self._db, rows)
        self.refresh()
        self.set_status(f"Импорт завершен: {result.imported}, пропущено: {result.skipped}")

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
                mode_raw = filters.get("mode")
                mode = mode_raw if isinstance(mode_raw, str) else None
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
        model = getattr(self, "model", None)
        if model is None:
            return []
        index = self._selected_task_index()
        if index is None:
            return []
        if hasattr(model, "task_at_row"):
            task = model.task_at_row(index.row())
            return [task] if task else []
        return []

    def _selected_task_index(self) -> Optional[QModelIndex]:
        list_widget = getattr(self, "list", None)
        if not isinstance(list_widget, QListView):
            return None
        index = list_widget.currentIndex()
        if not index.isValid():
            return None
        if index.data(TaskRoles.RowType) != "task":
            return None
        return index

    def _index_for_task_id(self, task_id: int) -> Optional[QModelIndex]:
        if not hasattr(self, "model"):
            return None
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            if not index.isValid():
                continue
            if index.data(TaskRoles.RowType) != "task":
                continue
            if index.data(TaskRoles.TaskId) == task_id:
                return index
        return None

    def focus_task(self, task_id: int) -> bool:
        index = self._index_for_task_id(task_id)
        if index is None:
            if self._gantt_mode:
                self._gantt_mode = False
                self.btn_gantt.blockSignals(True)
                self.btn_gantt.setChecked(False)
                self.btn_gantt.blockSignals(False)
                self.content_stack.setCurrentWidget(self.list)
            self._apply_tab("plan")
            self.model.set_project_filter(None)
            self.model.set_priority_filter(None)
            self.model.set_search("")
            self.cmb_priority.setCurrentText("Любой")
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)
            index = self._index_for_task_id(task_id)
        if index is None:
            return False

        self.content_stack.setCurrentWidget(self.list)
        self.list.setCurrentIndex(index)
        selection_model = self.list.selectionModel()
        if selection_model is not None:
            selection_model.select(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )
            selection_model.setCurrentIndex(
                index,
                QItemSelectionModel.SelectionFlag.Current,
            )
        self.list.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
        self.list.setFocus(Qt.FocusReason.OtherFocusReason)
        return True

    def _edit_selected_task(self) -> None:
        index = self._selected_task_index()
        if index is None:
            return
        self.delegate.edit_task(index)

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
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        model = index.model()
        if hasattr(model, "delete_task_by_row"):
            model.delete_task_by_row(index.row())

    def _shift_day(self, delta: int):
        """Сдвигает фокусную дату на указанное число дней."""
        self._focus_day = self._focus_day + timedelta(days=delta)
        self._update_day_label()
        self._update_sticky_day_header()
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
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
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
                marker_color=values["marker_color"],
                marker_theme=values["marker_theme"],
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        if self._gantt_mode and values["day"] == self._focus_day:
            self._refresh_gantt_day()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.list.viewport() and event.type() == QEvent.Type.Resize:
            self._update_sticky_day_header()
        if obj is self.list.viewport() and event.type() == QEvent.Type.MouseButtonDblClick:
            if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                index = self.list.indexAt(pos)
                if not index.isValid() or index.data(TaskRoles.RowType) != "task":
                    return False
                rect = self.list.visualRect(index)
                depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
                has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
                layout = self.delegate.row_layout(rect, depth, has_subtasks)
                if has_subtasks and layout["title"].contains(pos):
                    self.model.toggle_subtasks_expanded_by_row(index.row())
                elif layout["doc"].contains(pos):
                    self.delegate.open_task_view(index)
                else:
                    if has_subtasks:
                        self.model.toggle_subtasks_expanded_by_row(index.row())
                    else:
                        self.delegate.open_task_view(index)
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

    @staticmethod
    def _tab_from_mode(mode: Optional[str]) -> str:
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
        self._update_sticky_day_header()

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
        self._update_sticky_day_header()

    def _is_sticky_header_enabled(self) -> bool:
        return (
            not self._gantt_mode
            and self.content_stack.currentWidget() is self.list
        )

    def _update_sticky_day_header(self) -> None:
        if not hasattr(self, "_sticky_header"):
            return
        if not self._is_sticky_header_enabled():
            self._sticky_header.hide()
            return

        row_count = self.model.rowCount()
        if row_count <= 0:
            self._sticky_header.hide()
            return

        top_index = self.list.indexAt(QPoint(2, 2))
        if not top_index.isValid():
            top_index = self.model.index(0, 0)
            if not top_index.isValid():
                self._sticky_header.hide()
                return
        top_row = top_index.row()

        active_row = -1
        active_day: Optional[date] = None
        for row in range(top_row, -1, -1):
            idx = self.model.index(row, 0)
            if idx.data(TaskRoles.RowType) == "header":
                active_row = row
                active_day = idx.data(TaskRoles.Day)
                break
        if active_row < 0 or active_day is None:
            self._sticky_header.hide()
            return

        active_index = self.model.index(active_row, 0)
        active_rect = self.list.visualRect(active_index)
        if active_row == top_row and active_rect.top() >= 0:
            self._sticky_header.hide()
            return

        text = self.delegate.format_header(active_day)
        if active_day == date.today():
            text = f"{text}  СЕГОДНЯ"
        self._sticky_header.setText(text)

        next_header_top: Optional[int] = None
        for row in range(active_row + 1, row_count):
            idx = self.model.index(row, 0)
            if idx.data(TaskRoles.RowType) == "header":
                rect = self.list.visualRect(idx)
                if rect.isValid() and not rect.isEmpty():
                    next_header_top = rect.top()
                    break
        header_h = self.delegate.HEADER_H
        y = 0
        if next_header_top is not None and next_header_top < header_h:
            y = next_header_top - header_h

        self._sticky_header.setGeometry(0, y, self.list.viewport().width(), header_h)
        self._sticky_header.raise_()
        self._sticky_header.show()

    @staticmethod
    def _estimate_task_minutes(task) -> int:
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
            "исследование", "архитектура", "интеграция", "рефакторинг", "оптимизация",
            "debug", "тест", "документация", "design", "api", "sql",
            "миграция", "парсинг", "настройка", "синхрон",
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
            self.gantt_hint.setText("На выбранный день нет активных задач для диаграммы Gantt.")
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
            f"Gantt на {self._focus_day.isoformat()}: {len(tasks)} задач, {total_minutes} мин (~{total_hours:.1f} ч)."
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
            self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
            self.list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        else:
            self.list.setDragEnabled(False)
            self.list.setAcceptDrops(False)
            self.list.setDropIndicatorShown(False)
            self.list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
