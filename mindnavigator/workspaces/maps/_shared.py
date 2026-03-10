"""Рабочая область управления картами и метками.

Входные данные:
    Данные карт, изображения, координаты меток и пользовательские события.

Выходные данные:
    Обновлённые карты, метки и визуальные представления.
"""

from __future__ import annotations

import html
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any

import qtawesome as qta
from PySide6.QtCore import (
    Qt, QSize, QRect, QAbstractListModel, QModelIndex, QPoint, QPointF, QRectF, Signal, QTimer, QEvent
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QFont,
    QFontMetrics,
    QFontMetricsF,
    QPixmap,
    QPen,
    QCursor,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QLineEdit, QListView, QStyledItemDelegate, QSpinBox, QStyle,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QStackedWidget, QMenu,
    QFileDialog, QProgressBar, QSizePolicy, QSpacerItem,
    QPushButton, QScrollArea, QColorDialog, QSplitter, QStyleOptionViewItem
)
from shiboken6 import isValid

from mindnavigator.storage import CloudFileData, get_database as _storage_get_database
from mindnavigator.spaceenity.marker_types import (
    default_marker_type,
    marker_type_for_color,
    marker_type_icon,
    marker_type_options,
    marker_type_pixmap,
)
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
from mindnavigator.ui.dialogs.map_label_edit_dialog import MapLabelEditDialog, MapLabelEntitySource
from mindnavigator.spaceenity.resources import resource_path


def _parse_marker_properties_blob(raw: str) -> tuple[str, list[tuple[str, str]]]:
    text = (raw or "").strip()
    if not text:
        return "", []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text, []
    if not isinstance(data, dict):
        return text, []
    important = str(data.get("important") or "").strip()
    custom_fields: list[tuple[str, str]] = []
    fields_raw = data.get("custom_fields")
    if isinstance(fields_raw, list):
        for item in fields_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            value = str(item.get("value") or "").strip()
            if not name and not value:
                continue
            custom_fields.append((name, value))
    return important, custom_fields


def _format_marker_properties_text(raw: str) -> str:
    important, custom_fields = _parse_marker_properties_blob(raw)
    lines: List[str] = []
    if important:
        lines.append(important)
    for name, value in custom_fields:
        if name and value:
            lines.append(f"{name}: {value}")
        elif name:
            lines.append(name)
        elif value:
            lines.append(value)
    if not lines:
        return "—"
    return "\n".join(lines)


def get_database():
    module = sys.modules.get("mindnavigator.workspaces.maps.module_impl")
    if module is not None:
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()

from .map_overlay import MapOverlay
from .map_roles import MapRoles
from .map_row import MapRow
from .map_tool import MapTool, marker_drag_allowed
from .marker import Marker

__all__ = [name for name in globals() if not name.startswith("__")]
