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
import sys
from typing import Callable, Dict, List, Union, Optional, Set, Tuple, Any, cast

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QPoint, QAbstractListModel, QAbstractItemModel, QModelIndex, QEvent, QDate, QTime, QMimeData, QItemSelectionModel, QVariantAnimation, QEasingCurve, Signal, QObject, QUrl
from PySide6.QtGui import QAction, QPainter, QColor, QFont, QFontMetrics, QCursor, QPixmap, QShortcut, QKeySequence, QPalette, QMouseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QDateEdit, QTimeEdit, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle,
    QCheckBox, QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QAbstractItemView, QPlainTextEdit, QScrollArea, QStyleOptionViewItem,
    QStackedWidget, QTableWidget, QTableWidgetItem, QSpinBox, QHeaderView, QFileDialog, QListWidget, QListWidgetItem
)

from mindnavigator.transfer.collections import CsvTransferError, CsvTransferService
from mindnavigator.storage import (
    BOARD_COLUMN_COMPLETED,
    BOARD_COLUMN_DEFERRED,
    BOARD_COLUMN_IN_PROGRESS,
    BOARD_COLUMN_QUEUE,
    BOARD_COLUMNS,
    CloudFileData,
    DEFERRED_PRIORITY,
    TaskAttachmentData,
    get_database as _storage_get_database,
    normalize_board_column,
    normalize_priority,
    validate_area,
    validate_time_text,
    validate_title,
)
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace
from mindnavigator.workspaces.csv_transfer import (
    TASKS_CSV_FIELDS,
    export_tasks_rows,
    import_tasks_rows,
)

WEEKDAY_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
_PARENT_UNSET = object()

ATTACHMENT_KIND_LABELS = {
    "task": "Задача",
    "note": "Заметка",
    "idea": "Идея",
    "object": "Объект",
    "map": "Карта",
    "marker": "Метка карты",
    "file": "Файл",
    "image": "Изображение",
}
ATTACHMENT_KIND_ORDER = ("task", "note", "idea", "object", "map", "marker", "file", "image")
_URL_RE = re.compile(r"(https?://[^\s<>'\"()]+)")
_TASK_REFERENCE_RE = re.compile(r"(?<![A-Za-z0-9_])(?P<label>(?:MN-|#)(?P<id>\d+))(?![A-Za-z0-9_])", re.IGNORECASE)
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
    def replace_task_reference(match: re.Match[str]) -> str:
        task_id = int(match.group("id"))
        label = match.group("label")
        return f"<a href='task:{task_id}' style=\"{_LINK_STYLE}\">{label}</a>"

    def replace_url(match: re.Match[str]) -> str:
        url = match.group(1)
        return f"<a href='{url}' style=\"{_LINK_STYLE}\">{url}</a>"

    rendered: list[str] = []
    cursor = 0
    for match in _URL_RE.finditer(escaped_text):
        plain = escaped_text[cursor:match.start()]
        if plain:
            rendered.append(_TASK_REFERENCE_RE.sub(replace_task_reference, plain))
        rendered.append(replace_url(match))
        cursor = match.end()
    tail = escaped_text[cursor:]
    if tail:
        rendered.append(_TASK_REFERENCE_RE.sub(replace_task_reference, tail))
    return "".join(rendered)


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


def _handle_markdown_preview_link(
    link: str,
    task_link_opener: Optional[Callable[[int], bool]] = None,
) -> None:
    if link.startswith("task:"):
        if task_link_opener is None:
            return
        try:
            task_id = int(link.split(":", 1)[1])
        except ValueError:
            return
        task_link_opener(task_id)
        return
    QDesktopServices.openUrl(QUrl(link))


def _build_markdown_preview_widget(
    text: str,
    parent: Optional[QWidget] = None,
    task_link_opener: Optional[Callable[[int], bool]] = None,
) -> QWidget:
    container = QWidget(parent)
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(4)

    value_label = QLabel(_linkify_description_text(text))
    _configure_markdown_preview_label(value_label)
    if task_link_opener is not None:
        value_label.setOpenExternalLinks(False)
        value_label.linkActivated.connect(
            lambda link, current_opener=task_link_opener: _handle_markdown_preview_link(link, current_opener)
        )
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


def extract_task_reference_ids(*texts: str) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for text in texts:
        for match in _TASK_REFERENCE_RE.finditer(text or ""):
            task_id = int(match.group("id"))
            if task_id <= 0 or task_id in seen:
                continue
            seen.add(task_id)
            result.append(task_id)
    return result


APP_DAY_START_HOUR = 6


def app_today(now: datetime | None = None) -> date:
    current = now or datetime.now()
    if current.hour < APP_DAY_START_HOUR:
        current = current - timedelta(days=1)
    return current.date()


def should_show_today_badge(header_day: date) -> bool:
    return header_day == app_today()


def _tokenize_text_for_match(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zА-Яа-я0-9]+", (text or "").lower())
    return [token for token in tokens if len(token) >= 2]

def _is_opening_task_quote(previous_char: str) -> bool:
    if not previous_char:
        return True
    if previous_char.isspace():
        return True
    return previous_char in "([{-–—/:;"


def task_quote_for_insert(text: str, insert_pos: int) -> str:
    previous_char = text[insert_pos - 1] if insert_pos > 0 else ""
    return "«" if _is_opening_task_quote(previous_char) else "»"


def normalize_task_text_quotes(text: str) -> str:
    raw = text or ""
    if '"' not in raw:
        return raw
    normalized: list[str] = []
    for char in raw:
        if char == '"':
            previous_char = normalized[-1] if normalized else ""
            normalized.append("«" if _is_opening_task_quote(previous_char) else "»")
            continue
        normalized.append(char)
    return "".join(normalized)


class _TaskQuoteAutoReplaceFilter(QObject):
    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self._widget = widget
        self._applying_plain_text = False
        if isinstance(widget, QLineEdit):
            widget.textEdited.connect(self._normalize_line_edit)
        elif isinstance(widget, QPlainTextEdit):
            widget.textChanged.connect(self._normalize_plain_text_edit)

    def _normalize_line_edit(self, text: str) -> None:
        line_edit = self._widget
        if not isinstance(line_edit, QLineEdit):
            return
        normalized = normalize_task_text_quotes(text)
        if normalized == text:
            return
        cursor_pos = line_edit.cursorPosition()
        line_edit.setText(normalized)
        line_edit.setCursorPosition(min(cursor_pos, len(normalized)))

    def _normalize_plain_text_edit(self) -> None:
        plain_text_edit = self._widget
        if not isinstance(plain_text_edit, QPlainTextEdit) or self._applying_plain_text:
            return
        text = plain_text_edit.toPlainText()
        normalized = normalize_task_text_quotes(text)
        if normalized == text:
            return
        cursor = plain_text_edit.textCursor()
        cursor_pos = cursor.position()
        self._applying_plain_text = True
        try:
            plain_text_edit.setPlainText(normalized)
        finally:
            self._applying_plain_text = False
        cursor = plain_text_edit.textCursor()
        cursor.setPosition(min(cursor_pos, len(normalized)))
        plain_text_edit.setTextCursor(cursor)

    def eventFilter(self, obj, event) -> bool:
        return super().eventFilter(obj, event)


def attach_task_quote_autoreplace(*widgets: QWidget) -> list[QObject]:
    filters: list[QObject] = []
    for widget in widgets:
        filter_obj = _TaskQuoteAutoReplaceFilter(widget)
        filters.append(filter_obj)
    return filters


def get_database():
    for module_name in ("mindnavigator.workspaces.tasks", "mindnavigator.workspaces.tasks.module_impl"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()


from .header_row import HeaderRow
from .sort_header_row import SortHeaderRow
from .task_roles import TaskRoles
from .task_row import TaskRow

Row = Union[TaskRow, HeaderRow, SortHeaderRow]

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
        and previous.started_at == updated.started_at
        and previous.finished_at == updated.finished_at
        and previous.actual_minutes == updated.actual_minutes
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

__all__ = [name for name in globals() if not name.startswith("__")]
__all__.extend([
    "_PARENT_UNSET",
    "_URL_RE",
    "_FENCED_CODE_RE",
    "_INLINE_CODE_RE",
    "_INLINE_CODE_STYLE",
    "_BLOCK_CODE_STYLE",
    "_BLOCK_CODE_LANG_STYLE",
    "_LINK_STYLE",
    "_COPY_CODE_BUTTON_STYLE",
    "_linkify_escaped_text",
    "_extract_markdown_code_blocks",
    "_copy_markdown_code_blocks_to_clipboard",
    "_configure_markdown_preview_label",
    "_handle_markdown_preview_link",
    "_build_markdown_preview_widget",
    "_render_inline_description_html",
    "_linkify_description_text",
    "extract_task_reference_ids",
    "_tokenize_text_for_match",
    "_TaskQuoteAutoReplaceFilter",
])
