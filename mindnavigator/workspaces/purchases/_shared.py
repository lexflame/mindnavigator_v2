"""Workspace покупок (каркас UI для списка товаров)."""

from __future__ import annotations

import json
from typing import Callable, Optional

from datetime import datetime, timezone

from PySide6.QtCore import Qt, QRunnable, QThreadPool, Signal, QObject
import qtawesome as qta

from PySide6.QtGui import QAction, QDesktopServices, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QMessageBox,
    QFileDialog,
    QInputDialog,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QDialog,
    QMenu,
)
from PySide6.QtCore import QUrl

from mindnavigator.storage import get_database
from mindnavigator.spaceenity.http_client import HttpClient, HttpClientError
from mindnavigator.transfer.shop import ShopParseService, build_default_parsers
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay
from mindnavigator.ui.dialogs.purchase_add_dialog import PurchaseAddByUrlDialog
from mindnavigator.ui.dialogs.purchase_edit_dialog import PurchaseEditDialog
from mindnavigator.ui.dialogs.purchase_compare_dialog import PurchaseCompareDialog
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace

import sys
_storage_get_database = get_database

def get_database():
    module = sys.modules.get("mindnavigator.workspaces.purchases.module_impl")
    if module is not None:
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()

from ._shop_parse_worker_signals import _ShopParseWorkerSignals
