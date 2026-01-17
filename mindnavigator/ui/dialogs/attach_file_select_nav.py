"""Dialog for selecting files from FileWorkspace navigation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mindnavigator.storage import CloudFileData, get_database


class AttachFileSelectNav(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выбор файла")
        self.resize(900, 620)
        self.setMinimumSize(720, 520)

        self._db = get_database()
        self._files: List[CloudFileData] = []
        self._folder_index: Dict[str, Dict[str, object]] = {}
        self._tree_items: Dict[str, QTreeWidgetItem] = {}
        self._current_folder = ""
        self._selected_rel_path: Optional[str] = None
        self._selected_icon: Optional[QIcon] = None
        self._icon_cache: Dict[str, QIcon] = {}
        self._icon_folder = qta.icon("fa5s.folder", color="#d0a93e")
        self._icon_file_generic = qta.icon("fa5s.file", color="#cfcfcf")
        self._icon_file_image = qta.icon("fa5s.file-image", color="#6ab7ff")

        self._build_ui()
        self._load_files()

    def selected_rel_path(self) -> Optional[str]:
        return self._selected_rel_path

    def selected_icon(self) -> Optional[QIcon]:
        return self._selected_icon

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        self.path_label = QLabel("Облако")
        self.count_label = QLabel("")
        header_layout.addWidget(self.path_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.count_label)

        self.empty_label = QLabel("В базе нет файлов. Запустите синхронизацию.")
        self.empty_label.setAlignment(Qt.AlignCenter)

        self.content_frame = QWidget()
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter()
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.currentItemChanged.connect(self._on_tree_selection)

        self.file_grid = QListWidget()
        self.file_grid.setViewMode(QListWidget.IconMode)
        self.file_grid.setResizeMode(QListWidget.Adjust)
        self.file_grid.setMovement(QListWidget.Static)
        self.file_grid.setSpacing(12)
        self.file_grid.setIconSize(QSize(64, 64))
        self.file_grid.setGridSize(QSize(150, 120))
        self.file_grid.setWordWrap(True)
        self.file_grid.setSelectionMode(QAbstractItemView.SingleSelection)
        self.file_grid.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.file_grid.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_grid.currentItemChanged.connect(self._on_grid_selection)
        self.file_grid.itemDoubleClicked.connect(self._on_grid_double_clicked)

        self.splitter.addWidget(self.folder_tree)
        self.splitter.addWidget(self.file_grid)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        content_layout.addWidget(self.splitter, 1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

        layout.addWidget(header)
        layout.addWidget(self.empty_label, 1)
        layout.addWidget(self.content_frame, 1)
        layout.addWidget(self.buttons)

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background: #171a20;
                color: #e6e6e6;
            }
            QLabel {
                color: #d7d7d7;
            }
            QListWidget, QTreeWidget {
                background: #1b1d22;
                border: 1px solid #2f3136;
                border-radius: 8px;
                color: #d6d6d6;
                font-size: 11px;
            }
            QListWidget::item:selected, QTreeWidget::item:selected {
                background: #2c313a;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 6px;
            }
            """
        )

    def _load_files(self) -> None:
        self._files = list(self._db.fetch_cloud_files())
        self._folder_index = self._build_folder_index(self._files)
        self._rebuild_navigation()

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
        has_data = bool(self._files)
        self.empty_label.setVisible(not has_data)
        self.content_frame.setVisible(has_data)
        if not has_data:
            return

        self.folder_tree.clear()
        self.file_grid.clear()
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

    def _on_tree_selection(
        self,
        current: Optional[QTreeWidgetItem],
        _previous: Optional[QTreeWidgetItem],
    ) -> None:
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
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        cloud_root_path = Path(cloud_root) if cloud_root else None

        for child_path in folders:
            name = child_path.split("/")[-1]
            item = QListWidgetItem(name)
            item.setIcon(self._icon_folder)
            item.setData(Qt.UserRole, ("folder", child_path))
            item.setToolTip(name)
            self.file_grid.addItem(item)

        for file_item in files:
            label = file_item.name
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, ("file", file_item.rel_path, file_item))
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

    def _on_grid_selection(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
        if current is None:
            self._selected_rel_path = None
            self._selected_icon = None
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return
        payload = current.data(Qt.UserRole)
        if not payload:
            self._selected_rel_path = None
            self._selected_icon = None
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return
        if payload[0] == "folder":
            self._selected_rel_path = None
            self._selected_icon = None
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return

        rel_path = payload[1]
        file_item = payload[2]
        self._selected_rel_path = rel_path
        self._selected_icon = self._file_icon_for(file_item, self._cloud_root_path())
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def _on_grid_double_clicked(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        if payload[0] == "folder":
            self._select_folder(payload[1])
        else:
            self._selected_rel_path = payload[1]
            file_item = payload[2]
            self._selected_icon = self._file_icon_for(file_item, self._cloud_root_path())
            self._accept()

    def _select_folder(self, folder_path: str) -> None:
        tree_item = self._tree_items.get(folder_path)
        if tree_item:
            self.folder_tree.setCurrentItem(tree_item)

    def _cloud_root_path(self) -> Optional[Path]:
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        return Path(cloud_root) if cloud_root else None

    def _accept(self) -> None:
        if not self._selected_rel_path:
            return
        self.accept()
