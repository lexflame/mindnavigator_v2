"""Рабочая область для управления объектами и их файлами.

Входные данные:
    Данные объектов, вложенные документы/изображения и события пользователя.

Выходные данные:
    Обновлённые записи объектов и результаты обработки файлов.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import html
import re
import zipfile
from typing import List, Optional, Any, Union, Dict
from PySide6.QtCore import Qt, QSize, QRect, QModelIndex, QAbstractListModel
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPixmap, QImageReader
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QToolButton,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QSplitter,
    QTextEdit,
    QPlainTextEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QMessageBox,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
)

from mindnavigator.transfer.collections import CsvTransferError, CsvTransferService
from mindnavigator.storage import ObjectData, ObjectImageData, get_database
from mindnavigator.ui.modals import show_dialog_standard
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.workspaces.csv_transfer import (
    OBJECTS_CSV_FIELDS,
    export_objects_rows,
    import_objects_rows,
)

import sys
_storage_get_database = get_database

def get_database():
    for module_name in ("mindnavigator.workspaces.objects", "mindnavigator.workspaces.objects.module_impl"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()

from .object_row import ObjectRow
from .object_category_row import ObjectCategoryRow
from .object_roles import ObjectRoles



DOC_EXTENSIONS = {".doc", ".docx", ".txt"}






ObjectListRow = Union[ObjectRow, ObjectCategoryRow]




def normalize_object_category(catalog: str) -> str:
    value = (catalog or "").strip()
    if not value:
        return "Без каталога"
    return value.split("/", 1)[0].strip() or "Без каталога"


def group_objects_by_category(items: List[ObjectRow]) -> List[ObjectListRow]:
    groups: Dict[str, List[ObjectRow]] = {}
    for item in items:
        groups.setdefault(normalize_object_category(item.catalog), []).append(item)
    rows: List[ObjectListRow] = []
    for category in sorted(groups.keys(), key=lambda value: (value == "Без каталога", value.lower())):
        rows.append(ObjectCategoryRow(category))
        rows.extend(groups[category])
    return rows


def object_preview_line(description: str) -> str:
    """Возвращает компактное превью первой непустой строки описания объекта."""
    normalized = (description or "").replace("\r\n", "\n").replace("\r", "\n")
    for raw_line in normalized.split("\n"):
        preview = " ".join(raw_line.strip().split())
        if preview:
            return preview
    return "Описание пока не добавлено."














def _load_scaled_pixmap(file_path: Path, size: QSize) -> QPixmap:
    if not file_path.is_file():
        return QPixmap()
    reader = QImageReader(str(file_path))
    reader.setAutoTransform(True)
    if size.isValid():
        reader.setScaledSize(size)
    image = reader.read()
    if image.isNull():
        return QPixmap()
    return QPixmap.fromImage(image)


def extract_text_from_document(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        return _read_text_file(file_path)
    if suffix == ".docx":
        return _read_docx(file_path)
    if suffix == ".doc":
        return _read_doc_binary(file_path)
    return ""


def _read_text_file(file_path: Path) -> str:
    for encoding in ("utf-8", "cp1251", "latin-1"):
        try:
            return file_path.read_text(encoding=encoding)
        except (UnicodeDecodeError, OSError):
            continue
    try:
        return file_path.read_text(errors="ignore")
    except OSError:
        return ""


def _read_docx(file_path: Path) -> str:
    try:
        with zipfile.ZipFile(file_path) as archive:
            data = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile, OSError):
        return ""
    xml_text = data.decode("utf-8", errors="ignore")
    xml_text = xml_text.replace("</w:p>", "\n")
    xml_text = re.sub(r"<[^>]+>", " ", xml_text)
    xml_text = html.unescape(xml_text)
    return _clean_extracted_text(xml_text)


def _read_doc_binary(file_path: Path) -> str:
    try:
        data = file_path.read_bytes()
    except OSError:
        return ""
    text_candidates = []
    for encoding in ("utf-8", "cp1251", "latin-1"):
        decoded = data.decode(encoding, errors="ignore")
        text_candidates.append(decoded)
    best = max(text_candidates, key=_score_text)
    return _clean_extracted_text(best)


def _score_text(text: str) -> int:
    return len(re.findall(r"[A-Za-zА-Яа-я0-9]", text))


def _clean_extracted_text(text: str) -> str:
    cleaned = re.sub(r"[^\S\n]+", " ", text)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    cleaned = cleaned.replace("\x00", " ")
    return cleaned.strip()
