"""Рабочая область заметок и быстрых записей.

Входные данные:
    Тексты заметок, фильтры и пользовательские события.

Выходные данные:
    Обновлённые заметки и визуальные карточки.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Any, Union, Dict

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QTimer, QObject, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QToolButton,
    QButtonGroup,
    QLineEdit,
    QListView,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QAbstractItemView,
    QTextEdit,
    QMenu,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QStackedWidget,
    QFileDialog,
    QMessageBox,
)

from mindnavigator.transfer.collections import CsvTransferError, CsvTransferService
from mindnavigator.storage import get_database
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.workspaces.csv_transfer import (
    NOTES_CSV_FIELDS,
    export_notes_rows,
    import_notes_rows,
)

import sys
_storage_get_database = get_database

def get_database():
    for module_name in ("mindnavigator.workspaces.notes", "mindnavigator.workspaces.notes.module_impl"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()

from .note_item import NoteItem
from .note_category_row import NoteCategoryRow
from .note_workspace_state import NoteWorkspaceState
from .note_roles import NoteRoles






NoteRow = Union[NoteItem, NoteCategoryRow]






def normalize_note_body(text: str) -> str:
    raw = text or ""
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def note_preview_line(preview: str) -> str:
    """Возвращает компактное однострочное превью заметки для списка навигации."""
    normalized = normalize_note_body(preview)
    for raw_line in normalized.split("\n"):
        line = " ".join(raw_line.strip().split())
        if line:
            return line
    return "Нет краткого описания."


def normalize_note_category(project: str) -> str:
    value = (project or "").strip()
    return value if value else "Без проекта"


def group_notes_by_category(notes: List[NoteItem]) -> List[NoteRow]:
    groups: Dict[str, List[NoteItem]] = {}
    for note in notes:
        groups.setdefault(normalize_note_category(note.project), []).append(note)
    rows: List[NoteRow] = []
    for category in sorted(groups.keys(), key=lambda value: (value == "Без проекта", value.lower())):
        rows.append(NoteCategoryRow(category))
        rows.extend(groups[category])
    return rows
