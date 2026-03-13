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

from mindnavigator.transfer.collections import CsvTransferError, CsvTransferService
from mindnavigator.storage import (
    format_project_date,
    get_database,
    normalize_priority,
    validate_area,
    validate_title,
)
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
from mindnavigator.workspaces.csv_transfer import (
    PROJECTS_CSV_FIELDS,
    export_projects_rows,
    import_projects_rows,
)

import sys
_storage_get_database = get_database

def get_database():
    for module_name in ("mindnavigator.workspaces.projects", "mindnavigator.workspaces.projects.module_impl"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()

from .project_row import ProjectRow
from .header_row import HeaderRow
from .repository_probe_state import RepositoryProbeState
from .project_roles import ProjectRoles


# ProjectsWorkspace — UI-близнец TasksWorkspace:
# - та же структура верхней панели
# - тот же подход к группировке (заголовки + строки)
# - QListView + делегат ради скорости






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
