"""Рабочая область для файлов и сканирования изображений.

Входные данные:
    Файлы изображений, результаты распознавания и события пользователя.

Выходные данные:
    Превью изображений, результаты сканирования и данные вложений.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import mimetypes
import json
import re
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QObject, Qt, QThread, Signal, QSize, QUrl
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QStackedWidget,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QButtonGroup,
    QListView,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QApplication,
    QMenu,
    QMessageBox,
    QDialog,
    QProgressDialog,
    QToolButton,
    QGridLayout,
)

import qtawesome as qta

from mindnavigator.collections_importer import list_files, scan_files
from mindnavigator.storage import CloudFileData, Database, default_db_path, get_database
from mindnavigator.ui.dialogs.collection_category_dialog import CollectionCategorySelectDialog
from mindnavigator.ui.dialogs.collection_import_dialog import CollectionImportDialog
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.workspaces.objects_workspace import DOC_EXTENSIONS, extract_text_from_document

import sys
_storage_get_database = get_database

def get_database():
    module = sys.modules.get("mindnavigator.workspaces.files.module_impl")
    if module is not None:
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()

from .scan_summary import ScanSummary



HASH_RE = re.compile(r"[a-fA-F0-9]{32,64}")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
