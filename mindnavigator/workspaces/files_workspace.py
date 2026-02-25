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

from mindnavigator.collections_importer import FolderCollectionImporter
from mindnavigator.storage import CloudFileData, Database, default_db_path, get_database
from mindnavigator.ui.dialogs.collection_category_dialog import CollectionCategorySelectDialog
from mindnavigator.ui.dialogs.collection_import_dialog import CollectionImportDialog
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.workspaces.objects_workspace import DOC_EXTENSIONS, extract_text_from_document


HASH_RE = re.compile(r"[a-fA-F0-9]{32,64}")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}


@dataclass(frozen=True)
class ScanSummary:
    total: int
    valid: int
    invalid: int
    skipped: int


class CloudScanWorker(QObject):
    progress = Signal(str, int, int)
    error = Signal(str)
    finished = Signal(ScanSummary)

    def __init__(self, root_path: Path) -> None:
        super().__init__()
        self._root = root_path
        self._db = Database(default_db_path())

    def run(self) -> None:
        if not self._root.exists() or not self._root.is_dir():
            self.error.emit("Каталог облака не найден. Проверьте путь в настройках.")
            self.finished.emit(ScanSummary(0, 0, 0, 0))
            return

        files = [p for p in self._root.rglob("*") if p.is_file()]
        total = len(files)
        valid = 0
        invalid = 0
        skipped = 0
        rel_paths: List[str] = []

        for idx, file_path in enumerate(files, start=1):
            try:
                checksum = self._hash_file(file_path)
            except OSError:
                skipped += 1
                self.progress.emit(
                    f"{file_path.name} — ошибка чтения файла",
                    idx,
                    total,
                )
                continue

            rel_path = file_path.relative_to(self._root).as_posix()
            rel_paths.append(rel_path)
            hash_value = self._hash_from_path(rel_path)
            is_valid = bool(hash_value) and checksum == hash_value.lower()
            description = self._description_from_path(rel_path)
            is_image = self._is_image(file_path)

            self._db.upsert_cloud_file(
                rel_path=rel_path,
                name=file_path.name,
                description=description,
                checksum=checksum,
                hash_value=hash_value or "",
                size=file_path.stat().st_size,
                is_image=is_image,
                valid=is_valid,
            )

            if is_valid:
                valid += 1
                status = "OK"
            else:
                invalid += 1
                status = "НЕ СОВПАДАЕТ"

            self.progress.emit(f"{rel_path} — {status}", idx, total)

        self._db.remove_missing_cloud_files(rel_paths)
        self.progress.emit("Переиндексация базы данных...", total, total)
        self._db.reindex()
        self.progress.emit("Переиндексация базы данных завершена.", total, total)
        self.finished.emit(ScanSummary(total, valid, invalid, skipped))

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        digest = sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _hash_from_path(rel_path: str) -> Optional[str]:
        match = HASH_RE.search(rel_path)
        return match.group(0) if match else None

    @staticmethod
    def _description_from_path(rel_path: str) -> str:
        path = Path(rel_path)
        folder_parts = list(path.parent.parts) if path.parent != Path(".") else []
        stem = path.stem
        stem = HASH_RE.sub("", stem).replace("__", " ").strip(" -_")
        description_text = " / ".join(part for part in [*folder_parts, stem] if part)
        payload = {
            "text": description_text,
            "folders": folder_parts,
            "stem": stem,
            "extension": path.suffix.lower(),
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _is_image(file_path: Path) -> bool:
        if file_path.suffix.lower() in IMAGE_EXTENSIONS:
            return True
        mime = mimetypes.guess_type(file_path.name)[0] or ""
        return mime.startswith("image/")


class ImagePreviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        images: List[CloudFileData],
        start_index: int,
        cloud_root: Path,
        description_formatter,
    ) -> None:
        super().__init__(parent)
        self._images = images
        self._current_index = max(0, min(start_index, len(images) - 1))
        self._cloud_root = cloud_root
        self._format_description = description_formatter
        self._pixmap_cache: Dict[str, QPixmap] = {}

        self.setWindowTitle("Просмотр изображения")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.path_label = QLabel()
        self.path_label.setObjectName("FilesImagePath")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setObjectName("FilesImagePreview")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.description_label = QLabel()
        self.description_label.setObjectName("FilesImageDescription")
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label.setWordWrap(True)

        layout.addWidget(self.path_label)
        layout.addWidget(self.image_label, 1)
        layout.addWidget(self.description_label)

        self.setStyleSheet(
            """
            QDialog {
                background: #0f1115;
            }
            QLabel#FilesImagePath {
                color: #f0f0f0;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#FilesImagePreview {
                color: #9aa0a6;
            }
            QLabel#FilesImageDescription {
                color: #e0e0e0;
                background: rgba(30, 33, 39, 0.85);
                border: 1px solid #2f333b;
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 12px;
            }
            """
        )

        self._update_image()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Left:
            self._show_previous()
            return
        if event.key() == Qt.Key_Right:
            self._show_next()
            return
        if event.key() == Qt.Key_Escape:
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
            self.path_label.setText("Нет изображений")
            self.description_label.setText("")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображения отсутствуют")
            return

        current = self._images[self._current_index]
        self.path_label.setText(current.rel_path)
        self.description_label.setText(self._format_description(current.description))

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
        scaled = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")


class FileWorkspace(QWidget):
    """Рабочая область для синхронизации файлов облака."""

    CLOUD_STORAGE_KEY = "cloud_storage_path"
    CLOUD_LAST_SYNC_KEY = "cloud_last_sync_at"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._smooth_scroll_controllers: list[object] = []
        self._scan_thread: Optional[QThread] = None
        self._scan_worker: Optional[CloudScanWorker] = None
        self._all_cloud_files: List[CloudFileData] = []
        self._cloud_files: List[CloudFileData] = []
        self._folder_index: Dict[str, Dict[str, object]] = {}
        self._tree_items: Dict[str, QTreeWidgetItem] = {}
        self._current_folder = ""
        self._project_filter_id: Optional[int] = None
        self._icon_cache: Dict[str, QIcon] = {}
        self._default_mode_applied = False
        self._icon_folder = qta.icon("fa5s.folder", color="#d0a93e")
        self._icon_file_generic = qta.icon("fa5s.file", color="#cfcfcf")
        self._icon_file_image = qta.icon("fa5s.file-image", color="#6ab7ff")
        self._build_ui()
        self._update_sync_status()
        self._load_cloud_files()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.sync_button = QPushButton("Синхронизация")
        self.sync_button.setObjectName("FilesSyncButton")
        self.sync_button.clicked.connect(self._start_sync)

        self.reindex_button = QPushButton("Переиндексация")
        self.reindex_button.setObjectName("FilesReindexButton")
        self.reindex_button.clicked.connect(self._run_reindex)

        self.status_label = QLabel("Синхронизация не запускалась.")
        self.status_label.setObjectName("FilesSyncStatus")

        self.mode_group = QButtonGroup(self)
        self.log_mode_button = QPushButton("Логи")
        self.log_mode_button.setCheckable(True)
        self.log_mode_button.setObjectName("FilesModeButton")
        self.nav_mode_button = QPushButton("Навигация")
        self.nav_mode_button.setCheckable(True)
        self.nav_mode_button.setChecked(True)
        self.nav_mode_button.setObjectName("FilesModeButton")

        self.mode_group.addButton(self.log_mode_button, 0)
        self.mode_group.addButton(self.nav_mode_button, 1)
        self.mode_group.idClicked.connect(self._switch_mode)

        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(6)
        mode_layout.addWidget(self.log_mode_button)
        mode_layout.addWidget(self.nav_mode_button)

        header.addWidget(self.sync_button, 0, Qt.AlignmentFlag.AlignLeft)
        header.addWidget(self.reindex_button, 0, Qt.AlignmentFlag.AlignLeft)
        header.addWidget(self.status_label, 1, Qt.AlignmentFlag.AlignLeft)
        header.addStretch(1)
        header.addLayout(mode_layout)

        self.mode_stack = QStackedWidget()

        sync_page = QWidget()
        sync_layout = QVBoxLayout(sync_page)
        sync_layout.setContentsMargins(0, 0, 0, 0)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("FilesSyncLog")
        self.log_output.setPlaceholderText("Здесь появятся результаты синхронизации…")
        sync_layout.addWidget(self.log_output, 1)

        nav_page = QWidget()
        nav_layout = QVBoxLayout(nav_page)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(12)

        nav_header = QHBoxLayout()
        nav_header.setSpacing(8)
        self.path_label = QLabel("Облако")
        self.path_label.setObjectName("FilesNavPath")
        self.count_label = QLabel("")
        self.count_label.setObjectName("FilesNavCount")
        nav_header.addWidget(self.path_label)
        nav_header.addStretch(1)
        nav_header.addWidget(self.count_label)

        self.navigation_stack = QStackedWidget()
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        self.empty_label = QLabel("В базе пока нет данных о файлах. Запустите синхронизацию.")
        self.empty_label.setObjectName("FilesNavEmpty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_label, 1)

        content_page = QWidget()
        content_layout = QVBoxLayout(content_page)
        content_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_splitter = QSplitter()
        self.nav_splitter.setObjectName("FilesNavSplitter")

        self.folder_tree = QTreeWidget()
        self.folder_tree.setObjectName("FilesNavTree")
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.currentItemChanged.connect(self._on_tree_selection)

        self.file_grid = QListWidget()
        self.file_grid.setObjectName("FilesNavGrid")
        self.file_grid.setViewMode(QListView.IconMode)
        self.file_grid.setResizeMode(QListView.Adjust)
        self.file_grid.setMovement(QListView.Static)
        self.file_grid.setSpacing(12)
        self.file_grid.setIconSize(QSize(64, 64))
        self.file_grid.setGridSize(QSize(150, 120))
        self.file_grid.setWordWrap(True)
        self.file_grid.setSelectionMode(QAbstractItemView.SingleSelection)
        self.file_grid.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.file_grid.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_grid.itemDoubleClicked.connect(self._on_file_grid_double_clicked)
        self.file_grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_grid.customContextMenuRequested.connect(self._show_file_context_menu)

        self.nav_splitter.addWidget(self.folder_tree)
        self.nav_splitter.addWidget(self.file_grid)
        self.nav_splitter.setStretchFactor(0, 1)
        self.nav_splitter.setStretchFactor(1, 2)
        content_layout.addWidget(self.nav_splitter, 1)

        self.navigation_stack.addWidget(empty_page)
        self.navigation_stack.addWidget(content_page)

        nav_layout.addLayout(nav_header)
        nav_layout.addWidget(self.navigation_stack, 1)

        self.mode_stack.addWidget(sync_page)
        self.mode_stack.addWidget(nav_page)
        self.mode_stack.setCurrentIndex(1)

        layout.addLayout(header)
        layout.addWidget(self.mode_stack, 1)
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.log_output),
            attach_smooth_scroll(self.folder_tree),
            attach_smooth_scroll(self.file_grid),
        ]

        self.setStyleSheet(
            """
            QLabel#FilesSyncStatus {
                color: #b7b7b7;
                font-size: 12px;
            }
            QPushButton#FilesSyncButton {
                background: #2a2d33;
                border: 1px solid #3a3d44;
                border-radius: 6px;
                padding: 6px 16px;
                color: #e0e0e0;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#FilesSyncButton:hover {
                background: #343841;
            }
            QPushButton#FilesSyncButton:disabled {
                background: #202225;
                color: #6f7278;
                border-color: #2b2d33;
            }
            QPushButton#FilesReindexButton {
                background: #24272e;
                border: 1px solid #353941;
                border-radius: 6px;
                padding: 6px 12px;
                color: #d0d0d0;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#FilesReindexButton:hover {
                background: #2f333b;
            }
            QPushButton#FilesReindexButton:disabled {
                background: #1f2024;
                color: #6f7278;
                border-color: #2b2d33;
            }
            QPlainTextEdit#FilesSyncLog {
                background: #1b1d22;
                border: 1px solid #2f3136;
                border-radius: 8px;
                color: #d6d6d6;
                padding: 10px;
                font-size: 11px;
            }
            QPushButton#FilesModeButton {
                background: #1f2126;
                border: 1px solid #30343b;
                border-radius: 6px;
                padding: 4px 12px;
                color: #cdd0d5;
                font-size: 11px;
            }
            QPushButton#FilesModeButton:checked {
                background: #2d3139;
                border-color: #3a3f48;
                color: #ffffff;
            }
            QLabel#FilesNavPath {
                color: #e0e0e0;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#FilesNavCount {
                color: #9aa0a6;
                font-size: 11px;
            }
            QLabel#FilesNavEmpty {
                color: #9aa0a6;
                font-size: 12px;
            }
            QTreeWidget#FilesNavTree, QListWidget#FilesNavGrid {
                background: #1b1d22;
                border: 1px solid #2f3136;
                border-radius: 8px;
                color: #d6d6d6;
                font-size: 11px;
            }
            QTreeWidget#FilesNavTree::item:selected,
            QListWidget#FilesNavGrid::item:selected {
                background: #2c313a;
                color: #ffffff;
            }
            QListWidget#FilesNavGrid::item {
                padding: 6px;
            }
            """
        )

    def _switch_mode(self, index: int) -> None:
        self.mode_stack.setCurrentIndex(index)

    def _load_cloud_files(self) -> None:
        self._all_cloud_files = self._db.fetch_cloud_files()
        self._apply_project_filter()

    def set_project_filter(self, project_id: Optional[int]) -> None:
        """Устанавливает фильтр по проекту для облачных файлов."""
        self._project_filter_id = project_id
        self._apply_project_filter()

    def _apply_project_filter(self) -> None:
        project = None
        if self._project_filter_id is not None:
            project = next(
                (p for p in self._db.fetch_projects() if p.id == self._project_filter_id),
                None,
            )
        if project is None:
            self._cloud_files = list(self._all_cloud_files)
        else:
            self._cloud_files = [
                item
                for item in self._all_cloud_files
                if self._file_matches_project(item, project)
            ]
        self._folder_index = self._build_folder_index(self._cloud_files)
        self._rebuild_navigation()

    @staticmethod
    def _file_matches_project(item: CloudFileData, project) -> bool:
        project_tokens = [project.title.lower(), project.area.lower()]
        rel_path = (item.rel_path or "").lower()
        if any(token and token in rel_path for token in project_tokens):
            return True
        description = (item.description or "").strip()
        if not description:
            return False
        try:
            payload = json.loads(description)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            folders = [str(part).lower() for part in payload.get("folders", [])]
            text = str(payload.get("text", "")).lower()
            for token in project_tokens:
                if token and (token in text or token in folders):
                    return True
        return False

    @staticmethod
    def _build_folder_index(files: List[CloudFileData]) -> Dict[str, Dict[str, object]]:
        index: Dict[str, Dict[str, object]] = {"": {"folders": set(), "files": []}}
        for item in files:
            rel_path = (item.rel_path or "").strip().strip("/")
            if not rel_path:
                continue
            parts = [part for part in rel_path.split("/") if part]
            if not parts:
                continue
            for idx in range(len(parts) - 1):
                folder_path = "/".join(parts[: idx + 1])
                parent_path = "/".join(parts[:idx])
                index.setdefault(parent_path, {"folders": set(), "files": []})
                index.setdefault(folder_path, {"folders": set(), "files": []})
                folders: Set[str] = index[parent_path]["folders"]  # type: ignore[assignment]
                folders.add(folder_path)
            parent_path = "/".join(parts[:-1])
            index.setdefault(parent_path, {"folders": set(), "files": []})
            files_list: List[CloudFileData] = index[parent_path]["files"]  # type: ignore[assignment]
            files_list.append(item)
        return index

    def _rebuild_navigation(self) -> None:
        has_data = bool(self._cloud_files)
        self.nav_mode_button.setEnabled(has_data)
        if not has_data:
            self.navigation_stack.setCurrentIndex(0)
            self.folder_tree.clear()
            self.file_grid.clear()
            self.path_label.setText("Облако")
            self.count_label.setText("")
            if self.mode_stack.currentIndex() == 1:
                self.log_mode_button.setChecked(True)
                self.mode_stack.setCurrentIndex(0)
            return

        self.navigation_stack.setCurrentIndex(1)
        self.folder_tree.clear()
        self._tree_items.clear()
        if not self._default_mode_applied:
            self.nav_mode_button.setChecked(True)
            self.mode_stack.setCurrentIndex(1)
            self._default_mode_applied = True
        root_item = QTreeWidgetItem(["Облако"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, "")
        self.folder_tree.addTopLevelItem(root_item)
        root_item.setIcon(0, self._icon_folder)
        self._tree_items[""] = root_item
        self._populate_tree(root_item, "")
        root_item.setExpanded(True)
        self.folder_tree.setCurrentItem(root_item)

    def _populate_tree(self, parent_item: QTreeWidgetItem, folder_path: str) -> None:
        data = self._folder_index.get(folder_path, {})
        folders_raw = data.get("folders")
        folders = sorted(folders_raw) if isinstance(folders_raw, set) else []
        for child_path in folders:
            name = child_path.split("/")[-1]
            child_item = QTreeWidgetItem([name])
            child_item.setData(0, Qt.ItemDataRole.UserRole, child_path)
            parent_item.addChild(child_item)
            child_item.setIcon(0, self._icon_folder)
            self._tree_items[child_path] = child_item
            self._populate_tree(child_item, child_path)

    def _on_tree_selection(self, current: Optional[QTreeWidgetItem], _previous: Optional[QTreeWidgetItem]) -> None:
        if not current:
            return
        folder_path = current.data(0, Qt.ItemDataRole.UserRole) or ""
        self._set_current_folder(folder_path)

    def _set_current_folder(self, folder_path: str) -> None:
        self._current_folder = folder_path
        if folder_path:
            self.path_label.setText(f"Облако / {' / '.join(folder_path.split('/'))}")
        else:
            self.path_label.setText("Облако")
        self._render_file_grid(folder_path)

    def _render_file_grid(self, folder_path: str) -> None:
        self.file_grid.clear()
        data = self._folder_index.get(folder_path, {})
        folders_raw = data.get("folders")
        folders = sorted(folders_raw) if isinstance(folders_raw, set) else []
        files_raw = data.get("files")
        files_source = files_raw if isinstance(files_raw, list) else []
        files = sorted(files_source, key=lambda cloud_file: cloud_file.name.lower())
        cloud_root = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="").strip()
        cloud_root_path = Path(cloud_root) if cloud_root else None
        collection_map = self._collection_folder_map(cloud_root_path)
        for child_path in folders:
            name = child_path.split("/")[-1]
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, ("folder", child_path))
            item.setToolTip(name)
            collection_id = None
            if cloud_root_path:
                full_path = (cloud_root_path / child_path).resolve()
                collection_id = collection_map.get(str(full_path))
            self.file_grid.addItem(item)
            self._attach_folder_widget(item, name, collection_id)
        for file_item in files:
            description = self._format_description(file_item.description)
            size = self._format_size(file_item.size)
            label = f"{file_item.name}\n{size} • {description}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, ("file", file_item.rel_path))
            item.setIcon(self._file_icon_for(file_item, cloud_root_path))
            item.setToolTip(file_item.rel_path)
            self.file_grid.addItem(item)
        self.count_label.setText(f"{len(folders)} папок, {len(files)} файлов")

    def _file_icon_for(self, file_item: CloudFileData, cloud_root: Optional[Path]) -> QIcon:
        ext = Path(file_item.name).suffix.lower()
        cache_key = ext or "file"
        if file_item.is_image and cloud_root:
            file_path = cloud_root / file_item.rel_path
            if file_path.is_file():
                pixmap = QPixmap(str(file_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.file_grid.iconSize(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    return QIcon(scaled)
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        icon = self._icon_file_generic
        if ext in {".doc", ".docx"}:
            icon = qta.icon("fa5s.file-word", color="#3a7bd5")
        elif ext in {".xls", ".xlsx"}:
            icon = qta.icon("fa5s.file-excel", color="#2e7d32")
        elif ext == ".pdf":
            icon = qta.icon("fa5s.file-pdf", color="#c62828")
        elif file_item.is_image:
            icon = self._icon_file_image

        self._icon_cache[cache_key] = icon
        return icon

    @staticmethod
    def _format_size(size: int) -> str:
        size = max(0, int(size))
        if size < 1024:
            return f"{size} Б"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} КБ"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} МБ"
        return f"{size / (1024 * 1024 * 1024):.1f} ГБ"

    def _on_file_grid_double_clicked(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not payload:
            return
        if payload[0] == "folder":
            self._select_folder(payload[1])
        elif payload[0] == "file":
            self._open_image_preview(payload[1])

    def _select_folder(self, folder_path: str) -> None:
        tree_item = self._tree_items.get(folder_path)
        if tree_item:
            self.folder_tree.setCurrentItem(tree_item)

    def _show_file_context_menu(self, position) -> None:
        item = self.file_grid.itemAt(position)
        if item is None:
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not payload:
            return

        menu = QMenu(self)
        item_type, rel_path = payload

        if item_type == "folder":
            open_action = menu.addAction("Открыть")
            open_action.triggered.connect(lambda: self._select_folder(rel_path))
        else:
            open_folder_action = menu.addAction("Открыть папку")
            open_folder_action.triggered.connect(lambda: self._open_parent_folder(rel_path))

        copy_action = menu.addAction("Копировать путь")
        copy_action.triggered.connect(lambda: self._copy_path(rel_path))

        transfer_menu = menu.addMenu("FileTransfer")
        if item_type == "folder":
            create_object_action = transfer_menu.addAction("Создать объект")
            create_object_action.triggered.connect(lambda: self._create_object_from_folder(rel_path))
            create_collection_action = transfer_menu.addAction("Создать коллекцию")
            create_collection_action.setToolTip("Создать коллекцию из выбранной папки")
            create_collection_action.triggered.connect(lambda: self._create_collection_from_folder(rel_path))
        else:
            if Path(rel_path).suffix.lower() in DOC_EXTENSIONS:
                import_note_action = transfer_menu.addAction("Импорт в заметку")
                import_note_action.triggered.connect(lambda: self._import_note_from_file(rel_path))
            else:
                placeholder_action = transfer_menu.addAction("Нет действий")
                placeholder_action.setEnabled(False)

        menu.exec(self.file_grid.mapToGlobal(position))

    @staticmethod
    def _copy_path(rel_path: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(rel_path)

    def _open_parent_folder(self, rel_path: str) -> None:
        folder_path = "/".join(Path(rel_path).parts[:-1])
        self._select_folder(folder_path)

    def _create_object_from_folder(self, rel_path: str) -> None:
        try:
            obj = self._db.create_object_from_folder_path(rel_path)
        except ValueError as exc:
            QMessageBox.warning(self, "FileTransfer", str(exc))
            return
        QMessageBox.information(
            self,
            "FileTransfer",
            f"Создан объект: {obj.title}",
        )

    def _create_collection_from_folder(self, rel_path: str) -> None:
        cloud_root = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "FileTransfer", "Путь к облаку не задан.")
            return
        folder_path = Path(cloud_root) / rel_path
        if not folder_path.exists() or not folder_path.is_dir():
            QMessageBox.warning(self, "FileTransfer", "Папка не найдена в облаке.")
            return

        category_dialog = CollectionCategorySelectDialog(
            self._db,
            self._db.fetch_collection_categories(),
            parent=self,
        )
        if exec_with_overlay(category_dialog, self) != QDialog.DialogCode.Accepted:
            return
        category_id = category_dialog.selected_category_id()

        import_dialog = CollectionImportDialog(default_title=folder_path.name or "Коллекция", parent=self)
        if exec_with_overlay(import_dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = import_dialog.values()
        title = values.get("title") or folder_path.name or "Коллекция"
        include_subfolders = bool(values.get("include_subfolders"))

        import_options = json.dumps({"include_subfolders": include_subfolders}, ensure_ascii=False)
        try:
            collection = self._db.create_collection_item(
                title=title,
                entity_type="other",
                category_id=category_id,
                source_folder_path=str(folder_path),
                import_options_json=import_options,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "FileTransfer", str(exc))
            return

        importer = FolderCollectionImporter()
        files, list_errors = list_files(folder_path, include_subfolders=include_subfolders)
        if not self._confirm_large_folder(len(files)):
            return
        items, errors = self._scan_with_progress(importer, folder_path, files)
        errors = list_errors + errors
        entries = [
            {
                "source_path": item.source_path,
                "rel_path": item.rel_path,
                "title": item.title,
                "ext": item.ext,
                "mime": item.mime,
                "size_bytes": item.size_bytes,
                "meta_json": item.meta_json,
            }
            for item in items
        ]
        if entries:
            self._db.create_collection_entries(collection.id, entries)
        else:
            QMessageBox.information(
                self,
                "FileTransfer",
                "Папка пуста. Коллекция создана без элементов.",
            )

        if errors:
            self._report_import_errors(errors, "FileTransfer импорт коллекции")

        QMessageBox.information(
            self,
            "FileTransfer",
            f"Создана коллекция: {collection.title}",
        )

    def _confirm_large_folder(self, total: int) -> bool:
        if total <= 2000:
            return True
        if total >= 10000:
            QMessageBox.warning(
                self,
                "FileTransfer",
                "В папке более 10k файлов. Импорт может занять длительное время.",
            )
        dialog = ConfirmDialog(
            "Большая папка",
            f"В папке {total} файлов. Продолжить импорт?",
            parent=self,
            confirm_text="Продолжить",
            cancel_text="Отмена",
        )
        return show_dialog_standard(dialog, self) == QDialog.DialogCode.Accepted

    def _scan_with_progress(
        self,
        importer: FolderCollectionImporter,
        folder_path: Path,
        files: List[Path],
    ) -> tuple[list, list]:
        progress = QProgressDialog("Сканирование файлов...", "Отмена", 0, max(1, len(files)), self)
        progress.setWindowTitle("Импорт коллекции")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModal)

        def progress_cb(index: int, total: int | None, _path: Path) -> None:
            progress.setMaximum(total or max(1, len(files)))
            progress.setValue(index)
            QApplication.processEvents()

        def cancel_cb() -> bool:
            return progress.wasCanceled()

        items, errors, cancelled = importer.scan_files(
            folder_path,
            files,
            progress_cb=progress_cb,
            cancel_cb=cancel_cb,
        )
        progress.close()
        if cancelled:
            return [], []
        return items, errors

    def _report_import_errors(self, errors: List[str], context: str) -> None:
        if not errors:
            return
        log_path = Path.home() / ".mindnavigator" / "collection_import_errors.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {context}\n")
            for line in errors:
                handle.write(f"{line}\n")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("FileTransfer")
        box.setText(f"Импорт завершен с ошибками ({len(errors)}).")
        box.setInformativeText(f"Лог: {log_path}")
        open_btn = box.addButton("Открыть лог", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Ок", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() == open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path)))

    def _import_note_from_file(self, rel_path: str) -> None:
        cloud_root = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "FileTransfer", "Путь к облаку не задан.")
            return
        file_path = Path(cloud_root) / rel_path
        if not file_path.is_file():
            QMessageBox.warning(self, "FileTransfer", "Файл не найден в облаке.")
            return
        text = extract_text_from_document(file_path)
        if not text:
            QMessageBox.warning(self, "FileTransfer", "Не удалось извлечь текст из файла.")
            return
        title = Path(rel_path).stem or "Импортированная заметка"
        note = self._db.create_note(title, text, [], "")
        QMessageBox.information(
            self,
            "FileTransfer",
            f"Создана заметка: {note.title}",
        )

    @staticmethod
    def _format_description(raw_description: str) -> str:
        description = (raw_description or "").strip()
        if not description:
            return "Без описания"
        try:
            payload = json.loads(description)
        except json.JSONDecodeError:
            return description
        if isinstance(payload, dict):
            text = (payload.get("text") or "").strip()
            if text:
                return text
        return description

    def _collection_folder_map(self, cloud_root: Optional[Path]) -> Dict[str, int]:
        if not cloud_root:
            return {}
        mapping: Dict[str, int] = {}
        for row in self._db.fetch_collection_source_folders():
            path = (row.get("source_folder_path") or "").strip()
            if not path:
                continue
            try:
                norm = str(Path(path).resolve())
            except (OSError, RuntimeError):
                norm = path
            mapping[norm] = int(row.get("id") or 0)
        return mapping

    def _attach_folder_widget(self, item: QListWidgetItem, name: str, collection_id: Optional[int]) -> None:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        icon_container = QWidget()
        grid = QGridLayout(icon_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(self.file_grid.iconSize())
        icon_pixmap = self._icon_folder.pixmap(self.file_grid.iconSize())
        icon_label.setPixmap(icon_pixmap)
        grid.addWidget(icon_label, 0, 0, Qt.AlignmentFlag.AlignCenter)

        if collection_id:
            dot = QToolButton()
            dot.setFixedSize(12, 12)
            dot.setToolTip("Открыть коллекцию")
            dot.setStyleSheet(
                """
                QToolButton {
                    background: #37c76b;
                    border: 1px solid #1f7f46;
                    border-radius: 6px;
                    padding: 0px;
                }
                QToolButton:hover {
                    background: #48d97b;
                }
                """
            )
            dot.clicked.connect(lambda _=None, cid=collection_id: self._open_collection(cid))
            grid.addWidget(dot, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("color: #d6d6d6;")

        layout.addWidget(icon_container)
        layout.addWidget(name_label)

        item.setSizeHint(self.file_grid.gridSize())
        self.file_grid.setItemWidget(item, widget)

    def _open_collection(self, collection_id: int) -> None:
        window = self.window()
        mode_name = getattr(window, "MODE_COLLECTIONS", "Коллекции")
        if hasattr(window, "set_mode"):
            window.set_mode(mode_name)
        if hasattr(window, "page_collections") and hasattr(window.page_collections, "focus_item"):
            window.page_collections.focus_item(int(collection_id))

    def _find_file_by_rel_path(self, rel_path: str) -> Optional[CloudFileData]:
        return next((item for item in self._cloud_files if item.rel_path == rel_path), None)

    def _current_folder_images(self) -> List[CloudFileData]:
        data = self._folder_index.get(self._current_folder, {})
        files_raw = data.get("files")
        files = files_raw if isinstance(files_raw, list) else []
        image_files = [item for item in files if item.is_image]
        return sorted(image_files, key=lambda item: item.name.lower())

    def _open_image_preview(self, rel_path: str) -> None:
        file_item = self._find_file_by_rel_path(rel_path)
        if not file_item or not file_item.is_image:
            return
        cloud_root = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "Просмотр изображения", "Путь к облаку не задан.")
            return
        images = self._current_folder_images()
        if not images:
            return
        try:
            start_index = next(idx for idx, item in enumerate(images) if item.rel_path == rel_path)
        except StopIteration:
            return
        dialog = ImagePreviewDialog(
            self,
            images=images,
            start_index=start_index,
            cloud_root=Path(cloud_root),
            description_formatter=self._format_description,
        )
        dialog.showFullScreen()
        dialog.exec()

    def _start_sync(self) -> None:
        cloud_path = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="").strip()
        if not cloud_path:
            self._append_log("Путь к облаку не задан. Настройте его в разделе «Настройки».")
            self.status_label.setText("Ожидание пути к облаку.")
            return

        if self._scan_thread and self._scan_thread.isRunning():
            return

        self.log_output.clear()
        self.sync_button.setDisabled(True)
        self.reindex_button.setDisabled(True)
        self.status_label.setText("Подготовка к синхронизации...")

        self._scan_thread = QThread(self)
        self._scan_worker = CloudScanWorker(Path(cloud_path))
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.finished.connect(self._cleanup_worker)

        self._scan_thread.start()

    def _on_scan_progress(self, message: str, current: int, total: int) -> None:
        self.status_label.setText(f"Сканирование: {current}/{total}")
        self._append_log(message)

    def _on_scan_error(self, message: str) -> None:
        self._append_log(message)
        self.status_label.setText(message)

    def _on_scan_finished(self, summary: ScanSummary) -> None:
        self.sync_button.setDisabled(False)
        self.reindex_button.setDisabled(False)
        self._store_last_sync()
        self.status_label.setText(self._build_sync_status_text(summary))
        self._append_log(
            "Итого: "
            f"{summary.total} файлов, {summary.valid} совпадений, {summary.invalid} расхождений."
        )
        self._load_cloud_files()

    def _cleanup_worker(self) -> None:
        if self._scan_worker:
            self._scan_worker.deleteLater()
        self._scan_worker = None
        self._scan_thread = None
        self.reindex_button.setDisabled(False)

    def _append_log(self, message: str) -> None:
        self.log_output.appendPlainText(message)

    def _run_reindex(self) -> None:
        if self._scan_thread and self._scan_thread.isRunning():
            self._append_log("Невозможно переиндексировать базу во время синхронизации.")
            return
        self.reindex_button.setDisabled(True)
        self.status_label.setText("Переиндексация базы данных...")
        self._append_log("Переиндексация базы данных...")
        try:
            self._db.reindex()
        finally:
            self.reindex_button.setDisabled(False)
        self._append_log("Переиндексация базы данных завершена.")
        self._load_cloud_files()
        self.status_label.setText(self._build_sync_status_text())

    def _build_sync_status_text(self, summary: Optional[ScanSummary] = None) -> str:
        last_sync = self._db.get_setting(self.CLOUD_LAST_SYNC_KEY, default="").strip()
        if last_sync:
            try:
                timestamp = last_sync.replace("T", " ").split(".")[0]
            except ValueError:
                timestamp = last_sync
            base = f"Последняя синхронизация: {timestamp}"
        else:
            base = "Синхронизация не запускалась."

        if summary:
            return (
                "Синхронизация завершена: "
                f"{summary.valid} OK, {summary.invalid} ошибок, {summary.skipped} пропущено. "
                f"{base}"
            )
        return base

    def _store_last_sync(self) -> None:
        timestamp = datetime.now().isoformat(timespec="seconds")
        self._db.set_setting(self.CLOUD_LAST_SYNC_KEY, timestamp)

    def _update_sync_status(self) -> None:
        self.status_label.setText(self._build_sync_status_text())
