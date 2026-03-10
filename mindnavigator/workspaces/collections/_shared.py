"""Workspace for thematic collections and cross-links between items."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, QSize, QUrl, QObject, QRunnable, QThreadPool, Signal, QPointF, QEvent
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QDesktopServices, QImage
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QMenu,
    QPlainTextEdit,
    QCheckBox,
    QSplitter,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QProgressDialog,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput  # type: ignore
    from PySide6.QtMultimediaWidgets import QVideoWidget  # type: ignore

    _MULTIMEDIA_AVAILABLE = True
except ImportError:
    QMediaPlayer = None
    QAudioOutput = None
    QVideoWidget = None
    _MULTIMEDIA_AVAILABLE = False

from mindnavigator.collections_importer import FolderCollectionImporter, list_files, scan_files
from mindnavigator.csv_transfer import CsvTransferError, CsvTransferService
from mindnavigator.storage import (
    CollectionCategoryData,
    CollectionEntryData,
    CollectionItemData,
    CollectionRelationData,
    get_database,
)
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
from mindnavigator.workspaces.csv_workspace_transfer import (
    COLLECTIONS_CSV_FIELDS,
    export_collections_rows,
    import_collections_rows,
)

import sys
_storage_get_database = get_database
_modal_show_dialog_standard = show_dialog_standard

def get_database():
    module = sys.modules.get("mindnavigator.workspaces.collections.module_impl")
    if module is not None:
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()


def show_dialog_standard(dialog, parent=None):
    module = sys.modules.get("mindnavigator.workspaces.collections.module_impl")
    if module is not None:
        override = getattr(module, "show_dialog_standard", None)
        if override is not None and override is not show_dialog_standard:
            return override(dialog, parent)
    return _modal_show_dialog_standard(dialog, parent)

from ._entry_thumb_signals import _EntryThumbSignals


ENTITY_LABELS = {
    "building": "Здание",
    "city": "Город",
    "film": "Фильм",
    "game": "Игра",
    "character": "Персонаж",
    "other": "Другое",
}

ENTITY_CHOICES = [
    ("Здание", "building"),
    ("Город", "city"),
    ("Фильм", "film"),
    ("Игра", "game"),
    ("Персонаж", "character"),
    ("Другое", "other"),
]

RELATION_TEMPLATE_CHOICES = [
    ("Авто", "__auto__"),
    ("здание=фильм", "здание=фильм"),
    ("город=фильм", "город=фильм"),
    ("здание=игра", "здание=игра"),
    ("Другое...", "__custom__"),
]

RELATION_TYPE_MAP = {
    frozenset(("building", "film")): "здание=фильм",
    frozenset(("city", "film")): "город=фильм",
    frozenset(("building", "game")): "здание=игра",
}


def normalize_collection_category_title(
    item: CollectionItemData,
    categories_by_id: Dict[int, CollectionCategoryData],
) -> str:
    if item.category_id is None:
        return "Без категории"
    category = categories_by_id.get(item.category_id)
    if category is None:
        return "Без категории"
    return category.title


def group_collection_items_by_category(
    items: List[CollectionItemData],
    categories_by_id: Dict[int, CollectionCategoryData],
) -> List[tuple[str, List[CollectionItemData]]]:
    groups: Dict[str, List[CollectionItemData]] = {}
    for item in items:
        groups.setdefault(normalize_collection_category_title(item, categories_by_id), []).append(item)
    ordered: List[tuple[str, List[CollectionItemData]]] = []
    for category in sorted(groups.keys(), key=lambda value: (value == "Без категории", value.lower())):
        values = sorted(groups[category], key=lambda row: (row.title.lower(), row.id))
        ordered.append((category, values))
    return ordered


def format_collection_item_row(
    item: CollectionItemData,
    categories_by_id: Dict[int, CollectionCategoryData],
) -> str:
    entity_label = ENTITY_LABELS.get(item.entity_type, item.entity_type)
    category_label = normalize_collection_category_title(item, categories_by_id)
    topic_label = f"#{item.topic}" if item.topic else "без темы"
    source_label = "источник" if item.source_url else "без ссылки"
    return f"{item.title}\n{entity_label} • {category_label} • {topic_label} • {source_label}"
