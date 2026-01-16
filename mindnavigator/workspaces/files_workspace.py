from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import mimetypes
import json
import re
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QObject, Qt, QThread, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
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
)

import qtawesome as qta

from mindnavigator.storage import CloudFileData, Database, default_db_path, get_database


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

    def _hash_file(self, file_path: Path) -> str:
        digest = sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _hash_from_path(self, rel_path: str) -> Optional[str]:
        match = HASH_RE.search(rel_path)
        return match.group(0) if match else None

    def _description_from_path(self, rel_path: str) -> str:
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

    def _is_image(self, file_path: Path) -> bool:
        if file_path.suffix.lower() in IMAGE_EXTENSIONS:
            return True
        mime = mimetypes.guess_type(file_path.name)[0] or ""
        return mime.startswith("image/")


class FileWorkspace(QWidget):
    """Рабочая область для синхронизации файлов облака."""

    CLOUD_STORAGE_KEY = "cloud_storage_path"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._scan_thread: Optional[QThread] = None
        self._scan_worker: Optional[CloudScanWorker] = None
        self._all_cloud_files: List[CloudFileData] = []
        self._cloud_files: List[CloudFileData] = []
        self._folder_index: Dict[str, Dict[str, object]] = {}
        self._tree_items: Dict[str, QTreeWidgetItem] = {}
        self._current_folder = ""
        self._project_filter_id: Optional[int] = None
        self._icon_cache: Dict[str, QIcon] = {}
        self._icon_folder = qta.icon("fa5s.folder", color="#d0a93e")
        self._icon_file_generic = qta.icon("fa5s.file", color="#cfcfcf")
        self._icon_file_image = qta.icon("fa5s.file-image", color="#6ab7ff")
        self._build_ui()
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

        self.status_label = QLabel("Синхронизация не запускалась.")
        self.status_label.setObjectName("FilesSyncStatus")

        self.mode_group = QButtonGroup(self)
        self.log_mode_button = QPushButton("Логи")
        self.log_mode_button.setCheckable(True)
        self.log_mode_button.setChecked(True)
        self.log_mode_button.setObjectName("FilesModeButton")
        self.nav_mode_button = QPushButton("Навигация")
        self.nav_mode_button.setCheckable(True)
        self.nav_mode_button.setObjectName("FilesModeButton")

        self.mode_group.addButton(self.log_mode_button, 0)
        self.mode_group.addButton(self.nav_mode_button, 1)
        self.mode_group.idClicked.connect(self._switch_mode)

        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(6)
        mode_layout.addWidget(self.log_mode_button)
        mode_layout.addWidget(self.nav_mode_button)

        header.addWidget(self.sync_button, 0, Qt.AlignLeft)
        header.addWidget(self.status_label, 1, Qt.AlignLeft)
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
        self.empty_label.setAlignment(Qt.AlignCenter)
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

        layout.addLayout(header)
        layout.addWidget(self.mode_stack, 1)

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

    def _file_matches_project(self, item: CloudFileData, project) -> bool:
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

    def _build_folder_index(self, files: List[CloudFileData]) -> Dict[str, Dict[str, object]]:
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
        root_item = QTreeWidgetItem(["Облако"])
        root_item.setData(0, Qt.UserRole, "")
        self.folder_tree.addTopLevelItem(root_item)
        self._tree_items[""] = root_item
        self._populate_tree(root_item, "")
        root_item.setExpanded(True)
        self.folder_tree.setCurrentItem(root_item)

    def _populate_tree(self, parent_item: QTreeWidgetItem, folder_path: str) -> None:
        data = self._folder_index.get(folder_path, {})
        folders = sorted(data.get("folders", set()))
        for child_path in folders:
            name = child_path.split("/")[-1]
            child_item = QTreeWidgetItem([name])
            child_item.setData(0, Qt.UserRole, child_path)
            parent_item.addChild(child_item)
            self._tree_items[child_path] = child_item
            self._populate_tree(child_item, child_path)

    def _on_tree_selection(self, current: Optional[QTreeWidgetItem], _previous: Optional[QTreeWidgetItem]) -> None:
        if not current:
            return
        folder_path = current.data(0, Qt.UserRole) or ""
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
        folders = sorted(data.get("folders", set()))
        files = sorted(data.get("files", []), key=lambda item: item.name.lower())
        cloud_root = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="").strip()
        cloud_root_path = Path(cloud_root) if cloud_root else None
        for child_path in folders:
            name = child_path.split("/")[-1]
            item = QListWidgetItem(name)
            item.setIcon(self._icon_folder)
            item.setData(Qt.UserRole, ("folder", child_path))
            item.setToolTip(name)
            self.file_grid.addItem(item)
        for file_item in files:
            description = self._format_description(file_item.description)
            size = self._format_size(file_item.size)
            label = f"{file_item.name}\n{size} • {description}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, ("file", file_item.rel_path))
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

    def _format_size(self, size: int) -> str:
        size = max(0, int(size))
        if size < 1024:
            return f"{size} Б"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} КБ"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} МБ"
        return f"{size / (1024 * 1024 * 1024):.1f} ГБ"

    def _on_file_grid_double_clicked(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        if payload[0] == "folder":
            self._select_folder(payload[1])

    def _select_folder(self, folder_path: str) -> None:
        tree_item = self._tree_items.get(folder_path)
        if tree_item:
            self.folder_tree.setCurrentItem(tree_item)

    def _show_file_context_menu(self, position) -> None:
        item = self.file_grid.itemAt(position)
        if item is None:
            return
        payload = item.data(Qt.UserRole)
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
        else:
            placeholder_action = transfer_menu.addAction("Нет действий")
            placeholder_action.setEnabled(False)

        menu.exec(self.file_grid.mapToGlobal(position))

    def _copy_path(self, rel_path: str) -> None:
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

    def _format_description(self, raw_description: str) -> str:
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
        self.status_label.setText(
            "Синхронизация и переиндексация завершены: "
            f"{summary.valid} OK, {summary.invalid} ошибок, {summary.skipped} пропущено."
        )
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

    def _append_log(self, message: str) -> None:
        self.log_output.appendPlainText(message)
