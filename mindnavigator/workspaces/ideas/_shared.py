"""Рабочая область идей (IdeasWorkspace).

Входные данные:
    Список идей из базы данных, фильтры и действия пользователя.

Выходные данные:
    Обновленные записи идей и отображение карточек/инспектора.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Any, List, Union, Dict

from PySide6.QtCore import Qt, QSize, QAbstractListModel, QModelIndex
from PySide6.QtGui import QAction, QPainter, QColor, QFont, QCursor, QPixmap, QImageReader
from PySide6.QtWidgets import (
    QAbstractItemView,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QSplitter,
    QTabWidget,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QComboBox,
    QSpinBox,
    QToolButton,
    QCheckBox,
    QSizePolicy,
    QMenu,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from mindnavigator.transfer.collections import CsvTransferError, CsvTransferService
from mindnavigator.storage import IdeaImageData, get_database
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace
from mindnavigator.workspaces.csv_transfer import (
    IDEAS_CSV_FIELDS,
    export_ideas_rows,
    import_ideas_rows,
)

import sys
_storage_get_database = get_database

def get_database():
    for module_name in ("mindnavigator.workspaces.ideas", "mindnavigator.workspaces.ideas.module_impl"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()

from .idea_item import IdeaItem
from .idea_category_row import IdeaCategoryRow
from .idea_roles import IdeaRoles



IDEA_TYPES = [
    ("Все", None),
    ("Feature", "feature"),
    ("Story", "story"),
    ("Art", "art"),
    ("Research", "research"),
    ("Tech", "tech"),
    ("Other", "other"),
]

STATUS_LABELS = {
    "inbox": "Входящие",
    "work": "В работе",
    "ripe": "Созрела",
    "done": "Готово",
    "archived": "Архив",
}

TYPE_LABELS = {
    "feature": "Feature",
    "story": "Story",
    "art": "Art",
    "research": "Research",
    "tech": "Tech",
    "other": "Other",
}






IdeaRow = Union[IdeaItem, IdeaCategoryRow]


def normalize_idea_category(status: str, labels: Optional[Dict[str, str]] = None) -> str:
    value = (status or "").strip().lower()
    effective_labels = labels or STATUS_LABELS
    return effective_labels.get(value, value.capitalize() if value else "Без статуса")


def group_ideas_by_category(
    items: List[IdeaItem],
    labels: Optional[Dict[str, str]] = None,
    order: Optional[Dict[str, int]] = None,
) -> List[IdeaRow]:
    groups: Dict[str, List[IdeaItem]] = {}
    for item in items:
        groups.setdefault(normalize_idea_category(item.status, labels), []).append(item)
    display_order = order or {}
    rows: List[IdeaRow] = []
    for category in sorted(
        groups.keys(),
        key=lambda value: (display_order.get(value, 999), value.lower()),
    ):
        rows.append(IdeaCategoryRow(category))
        rows.extend(groups[category])
    return rows


def idea_preview_line(summary: str, body_md: str) -> str:
    """Возвращает компактное превью идеи из summary или текста описания."""
    sources = [summary or "", body_md or ""]
    for source in sources:
        normalized = source.replace("\r\n", "\n").replace("\r", "\n")
        for raw_line in normalized.split("\n"):
            line = " ".join(raw_line.strip().split())
            if line:
                return line
    return "Нет превью идеи."
