"""Workspace for thematic collections and cross-links between items."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput  # type: ignore
    from PySide6.QtMultimediaWidgets import QVideoWidget  # type: ignore

    _MULTIMEDIA_AVAILABLE = True
except Exception:
    QMediaPlayer = None
    QAudioOutput = None
    QVideoWidget = None
    _MULTIMEDIA_AVAILABLE = False

from mindnavigator.collections_importer import FolderCollectionImporter
from mindnavigator.storage import (
    CollectionCategoryData,
    CollectionEntryData,
    CollectionItemData,
    CollectionRelationData,
    get_database,
)
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND

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


class _EntryThumbSignals(QObject):
    ready = Signal(int, str)


class _EntryThumbWorker(QRunnable):
    def __init__(
        self,
        entry_id: int,
        source_path: str,
        thumb_path: Path,
        size: QSize,
        signals: _EntryThumbSignals,
        kind: str,
    ):
        super().__init__()
        self.entry_id = entry_id
        self.source_path = source_path
        self.thumb_path = thumb_path
        self.size = size
        self.signals = signals
        self.kind = kind

    def run(self) -> None:
        try:
            if self.thumb_path.exists():
                self.signals.ready.emit(self.entry_id, str(self.thumb_path))
                return
            if self.kind == "video":
                image = self._load_video_frame()
            else:
                image = QImage(self.source_path)
            if image.isNull():
                return
            scaled = image.scaled(self.size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = max(0, (scaled.width() - self.size.width()) // 2)
            y = max(0, (scaled.height() - self.size.height()) // 2)
            cropped = scaled.copy(x, y, self.size.width(), self.size.height())
            self.thumb_path.parent.mkdir(parents=True, exist_ok=True)
            cropped.save(str(self.thumb_path), "PNG")
            self.signals.ready.emit(self.entry_id, str(self.thumb_path))
        except Exception:
            return

    def _load_video_frame(self) -> QImage:
        try:
            import cv2  # type: ignore
        except Exception:
            return QImage()
        cap = cv2.VideoCapture(self.source_path)
        if not cap.isOpened():
            return QImage()
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return QImage()
        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            return QImage()
        h, w, _ = frame.shape
        bytes_per_line = 3 * w
        return QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()


class CollectionMediaPreviewDialog(QDialog):
    def __init__(
        self,
        entries: List[CollectionEntryData],
        start_index: int,
        parent=None,
    ):
        super().__init__(parent)
        self._entries = entries
        self._index = max(0, min(start_index, len(entries) - 1))
        self.setWindowTitle("Просмотр")
        self.setMinimumSize(720, 520)
        self.setFocusPolicy(Qt.StrongFocus)
        self.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.title_label = QLabel("")
        self.title_label.setObjectName("CollectionPreviewTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.content = QLabel()
        self.content.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.content, 1)

        nav = QHBoxLayout()
        self.prev_btn = QToolButton()
        self.prev_btn.setText("◀")
        self.prev_btn.clicked.connect(self._show_prev)
        self.next_btn = QToolButton()
        self.next_btn.setText("▶")
        self.next_btn.clicked.connect(self._show_next)
        nav.addWidget(self.prev_btn)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

        self._player = None
        self._audio = None
        self._video_widget = None

        self._update_content()

        self.setStyleSheet(
            """
            QDialog {
                background: #0f1115;
            }
            QLabel#CollectionPreviewTitle {
                color: #f0f0f0;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel {
                color: #cfcfcf;
            }
            """
        )

    def _show_image(self, path: Path) -> None:
        if not path.is_file():
            self.content.setText("Изображение недоступно.")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.content.setText("Изображение недоступно.")
            return
        self._set_pixmap(pixmap)

    def _show_video(self, path: Path) -> None:
        if not path.is_file():
            self.content.setText("Видео недоступно.")
            return
        if _MULTIMEDIA_AVAILABLE and QVideoWidget is not None and QMediaPlayer is not None:
            self._video_widget = QVideoWidget()
            self._audio = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setVideoOutput(self._video_widget)
            self._player.setAudioOutput(self._audio)
            self._player.setSource(QUrl.fromLocalFile(str(path)))
            self.layout().replaceWidget(self.content, self._video_widget)
            self.content.deleteLater()
            self.content = self._video_widget
            self._player.play()
        else:
            self.content.setText("Проигрывание видео недоступно.")

    def _show_document(self, path: Path) -> None:
        if not path.is_file():
            self.content.setText("Документ недоступен.")
            return
        try:
            from mindnavigator.workspaces.objects_workspace import extract_text_from_document
        except Exception:
            self.content.setText("Предпросмотр документа недоступен.")
            return
        text = extract_text_from_document(path)
        if not text:
            self.content.setText("Не удалось извлечь текст из документа.")
            return
        preview = "\n".join(text.splitlines()[:80])
        self.content.setText(preview)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if isinstance(self.content, QLabel) and self.content.pixmap():
            self._set_pixmap(self.content.pixmap())

    def _set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        target = self.content.size()
        scaled = pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.content.setPixmap(scaled)

    def closeEvent(self, event) -> None:
        if self._player:
            self._player.stop()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Left:
            self._show_prev()
            return
        if event.key() == Qt.Key_Right:
            self._show_next()
            return
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.KeyPress:
            self.keyPressEvent(event)
            return True
        return super().eventFilter(watched, event)

    def _show_prev(self) -> None:
        if not self._entries:
            return
        self._index = max(0, self._index - 1)
        self._update_content()

    def _show_next(self) -> None:
        if not self._entries:
            return
        self._index = min(len(self._entries) - 1, self._index + 1)
        self._update_content()

    def _update_content(self) -> None:
        if not self._entries:
            self.title_label.setText("Нет элементов")
            self.content.setText("Нет встроенного предпросмотра.")
            return
        entry = self._entries[self._index]
        self.title_label.setText(entry.rel_path)
        path = Path(entry.source_path)
        if self._player:
            self._player.stop()
        if self._video_widget:
            self.layout().replaceWidget(self._video_widget, self.content)
            self._video_widget.deleteLater()
            self._video_widget = None
            self.content = QLabel()
            self.content.setAlignment(Qt.AlignCenter)
            self.layout().insertWidget(1, self.content, 1)
        kind = FolderCollectionImporter.classify_extension(entry.ext)
        if kind == "document":
            self._show_document(path)
        elif kind == "image":
            self._show_image(path)
        elif kind == "video":
            self._show_video(path)
        else:
            self.content.setText("Нет встроенного предпросмотра.")


class CollectionItemEditDialog(QDialog):
    def __init__(
        self,
        item: Optional[CollectionItemData] = None,
        category_options: Optional[List[tuple[str, Optional[int]]]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("CollectionItemEditDialog")
        self.setWindowTitle("Создание элемента коллекции" if item is None else "Редактирование элемента коллекции")
        self.setMinimumSize(620, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Новый элемент коллекции" if item is None else "Редактирование элемента коллекции")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.title_edit = QLineEdit(item.title if item else "")
        self.title_edit.setPlaceholderText("Название")

        self.type_edit = QComboBox()
        for label, value in ENTITY_CHOICES:
            self.type_edit.addItem(label, value)
        if item is not None:
            idx = self.type_edit.findData(item.entity_type)
            if idx >= 0:
                self.type_edit.setCurrentIndex(idx)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Без категории", None)
        for label, value in category_options or []:
            self.category_combo.addItem(label, value)
        if item is not None:
            idx = self.category_combo.findData(item.category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

        self.topic_edit = QLineEdit(item.topic if item else "")
        self.topic_edit.setPlaceholderText("Тема (например: sci-fi, архитектура, индустриальный урбанизм)")

        self.image_url_edit = QLineEdit(item.image_url if item else "")
        self.image_url_edit.setPlaceholderText("Ссылка на изображение")

        self.source_url_edit = QLineEdit(item.source_url if item else "")
        self.source_url_edit.setPlaceholderText("Ссылка на источник")

        self.description_edit = QPlainTextEdit(item.description if item else "")
        self.description_edit.setPlaceholderText("Описание / заметка")
        self.description_edit.setMinimumHeight(130)

        form.addRow("Название", self.title_edit)
        form.addRow("Тип", self.type_edit)
        form.addRow("Тема", self.topic_edit)
        form.addRow("Изображение URL", self.image_url_edit)
        form.addRow("Источник URL", self.source_url_edit)
        form.addRow("Описание", self.description_edit)
        form.addRow("Категория", self.category_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_btn = buttons.button(QDialogButtonBox.Save)
        if save_btn is not None:
            save_btn.setText("Создать" if item is None else "Сохранить")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog#CollectionItemEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#CollectionItemEditDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#CollectionItemEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}
            QDialog#CollectionItemEditDialog QLineEdit,
            QDialog#CollectionItemEditDialog QPlainTextEdit,
            QDialog#CollectionItemEditDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QDialog#CollectionItemEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
            }}
            """
        )

    def _accept(self) -> None:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Проверка", "Введите название элемента.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "title": self.title_edit.text().strip(),
            "entity_type": self.type_edit.currentData(),
            "category_id": self.category_combo.currentData(),
            "topic": self.topic_edit.text().strip(),
            "image_url": self.image_url_edit.text().strip(),
            "source_url": self.source_url_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
        }


class CollectionRelationDialog(QDialog):
    def __init__(self, source_item: CollectionItemData, candidates: List[CollectionItemData], parent=None):
        super().__init__(parent)
        self.setObjectName("CollectionRelationDialog")
        self.setWindowTitle("Создать связь")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"Связать: {source_item.title}")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._source_item = source_item
        self._candidates_by_id: Dict[int, CollectionItemData] = {}
        self.target_combo = QComboBox()
        for item in candidates:
            label = f"{ENTITY_LABELS.get(item.entity_type, item.entity_type)} · {item.title}"
            self.target_combo.addItem(label, item.id)
            self._candidates_by_id[item.id] = item

        self.template_combo = QComboBox()
        for label, value in RELATION_TEMPLATE_CHOICES:
            self.template_combo.addItem(label, value)
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.target_combo.currentIndexChanged.connect(self._sync_template_for_selection)

        self.kind_edit = QLineEdit("")
        self.kind_edit.setPlaceholderText("Произвольный тип связи")
        self.kind_edit.setEnabled(False)

        form.addRow("Связать с", self.target_combo)
        form.addRow("Шаблон связи", self.template_combo)
        form.addRow("Пользовательский тип", self.kind_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_btn = buttons.button(QDialogButtonBox.Save)
        if save_btn is not None:
            save_btn.setText("Создать связь")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog#CollectionRelationDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#CollectionRelationDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#CollectionRelationDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 16px;
                font-weight: 600;
            }}
            QDialog#CollectionRelationDialog QLineEdit,
            QDialog#CollectionRelationDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QDialog#CollectionRelationDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
            }}
            """
        )
        self._sync_template_for_selection()

    def _accept(self) -> None:
        if self.target_combo.currentData() is None:
            QMessageBox.warning(self, "Связи", "Выберите элемент для связи.")
            return
        self.accept()

    def values(self) -> dict:
        template_value = self.template_combo.currentData()
        if template_value == "__auto__":
            relation_kind = self._suggest_template_for_current_target() or "="
        elif template_value == "__custom__":
            relation_kind = self.kind_edit.text().strip() or "="
        else:
            relation_kind = template_value
        return {
            "target_id": self.target_combo.currentData(),
            "relation_kind": relation_kind,
        }

    def _suggest_template_for_current_target(self) -> str:
        target_id = self.target_combo.currentData()
        target_item = self._candidates_by_id.get(target_id)
        if target_item is None:
            return "="
        key = frozenset((self._source_item.entity_type, target_item.entity_type))
        return RELATION_TYPE_MAP.get(key, "=")

    def _sync_template_for_selection(self) -> None:
        if self.template_combo.currentData() == "__auto__":
            self.kind_edit.setText(self._suggest_template_for_current_target())

    def _on_template_changed(self) -> None:
        value = self.template_combo.currentData()
        if value == "__custom__":
            self.kind_edit.setEnabled(True)
            if not self.kind_edit.text().strip():
                self.kind_edit.setText("=")
        elif value == "__auto__":
            self.kind_edit.setEnabled(False)
            self.kind_edit.setText(self._suggest_template_for_current_target())
        else:
            self.kind_edit.setEnabled(False)
            self.kind_edit.setText(value)


class CollectionsWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = get_database()
        self._items: List[CollectionItemData] = []
        self._items_by_id: Dict[int, CollectionItemData] = {}
        self._categories: List[CollectionCategoryData] = []
        self._categories_by_id: Dict[int, CollectionCategoryData] = {}
        self._relations: List[CollectionRelationData] = []
        self._entries: List[CollectionEntryData] = []
        self._entries_by_id: Dict[int, CollectionEntryData] = {}
        self._current_item_id: Optional[int] = None
        self._thumb_size = QSize(56, 56)
        self._entry_thumb_size = QSize(72, 72)
        self._thumb_cache: Dict[str, QIcon] = {}
        self._thumb_pending_urls: set[str] = set()
        self._thumb_loader = QNetworkAccessManager(self)
        self._thumb_loader.finished.connect(self._on_thumb_loaded)
        self._entry_thumb_dir = Path.home() / ".mindnavigator" / "collection_thumbs"
        self._entry_thumb_signals = _EntryThumbSignals()
        self._entry_thumb_signals.ready.connect(self._on_entry_thumb_ready)
        self._entry_thumb_pool = QThreadPool(self)
        self._build_ui()
        self.refresh_collections()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Коллекции")
        title.setObjectName("CollectionsTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по коллекциям...")
        self.search_edit.textChanged.connect(self.refresh_collections)

        self.topic_filter = QComboBox()
        self.topic_filter.currentIndexChanged.connect(self.refresh_collections)

        self.type_filter = QComboBox()
        self.type_filter.addItem("Все типы", "")
        for label, value in ENTITY_CHOICES:
            self.type_filter.addItem(label, value)
        self.type_filter.currentIndexChanged.connect(self.refresh_collections)

        self.include_subcategories = QCheckBox("Включая подкатегории")
        self.include_subcategories.setChecked(True)
        self.include_subcategories.stateChanged.connect(self.refresh_collections)

        self.add_button = QToolButton()
        self.add_button.setText("Добавить")
        self.add_button.clicked.connect(self._add_item)

        header.addWidget(self.search_edit)
        header.addWidget(self.topic_filter)
        header.addWidget(self.type_filter)
        header.addWidget(self.include_subcategories)
        header.addWidget(self.add_button)
        layout.addLayout(header)

        splitter = QSplitter()

        category_panel = QFrame()
        category_layout = QVBoxLayout(category_panel)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(6)
        category_label = QLabel("Категории")
        category_label.setObjectName("CollectionsCategoriesTitle")
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_tree.customContextMenuRequested.connect(self._open_category_menu)
        self.category_tree.currentItemChanged.connect(lambda *_: self.refresh_collections())
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_tree, 1)

        list_panel = QFrame()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)
        self.items_list = QListWidget()
        self.items_list.setIconSize(self._thumb_size)
        self.items_list.currentItemChanged.connect(self._on_item_selected)
        list_layout.addWidget(self.items_list, 1)

        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        self.details_title = QLabel("Выберите элемент")
        self.details_title.setObjectName("CollectionsDetailsTitle")
        self.details_type = QLabel("")
        self.details_category = QLabel("")
        self.details_topic = QLabel("")
        self.details_links = QLabel("")
        self.details_links.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.details_links.setOpenExternalLinks(True)
        self.details_description = QLabel("")
        self.details_description.setWordWrap(True)

        actions = QHBoxLayout()
        self.edit_button = QToolButton()
        self.edit_button.setText("Редактировать")
        self.edit_button.clicked.connect(self._edit_current_item)
        self.delete_button = QToolButton()
        self.delete_button.setText("Удалить")
        self.delete_button.clicked.connect(self._delete_current_item)
        self.refresh_import_button = QToolButton()
        self.refresh_import_button.setText("Обновить из папки")
        self.refresh_import_button.clicked.connect(self._update_from_folder)
        self.link_button = QToolButton()
        self.link_button.setText("Создать связь")
        self.link_button.clicked.connect(self._add_relation)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.refresh_import_button)
        actions.addWidget(self.link_button)
        actions.addStretch(1)
        actions.addWidget(self.delete_button)

        rel_title = QLabel("Перекрестные связи")
        rel_title.setObjectName("CollectionsRelationsTitle")
        self.relations_list = QListWidget()
        self.remove_relation_button = QToolButton()
        self.remove_relation_button.setText("Удалить выбранную связь")
        self.remove_relation_button.clicked.connect(self._remove_relation)

        entries_title = QLabel("Элементы коллекции")
        entries_title.setObjectName("CollectionsRelationsTitle")
        entries_filters = QHBoxLayout()
        self.filter_images = QCheckBox("Изображения")
        self.filter_images.setChecked(True)
        self.filter_images.stateChanged.connect(self._refresh_entries)
        self.filter_videos = QCheckBox("Видео")
        self.filter_videos.setChecked(True)
        self.filter_videos.stateChanged.connect(self._refresh_entries)
        self.filter_docs = QCheckBox("Документы")
        self.filter_docs.setChecked(True)
        self.filter_docs.stateChanged.connect(self._refresh_entries)
        self.filter_other = QCheckBox("Прочее")
        self.filter_other.setChecked(True)
        self.filter_other.stateChanged.connect(self._refresh_entries)
        self.group_by_folder = QCheckBox("Группировать по подпапкам")
        self.group_by_folder.setChecked(False)
        self.group_by_folder.stateChanged.connect(self._refresh_entries)
        entries_filters.addWidget(self.filter_images)
        entries_filters.addWidget(self.filter_videos)
        entries_filters.addWidget(self.filter_docs)
        entries_filters.addWidget(self.filter_other)
        entries_filters.addStretch(1)
        entries_filters.addWidget(self.group_by_folder)

        self.entries_list = QListWidget()
        self.entries_list.setIconSize(self._entry_thumb_size)
        self.entries_list.itemDoubleClicked.connect(self._open_entry)

        right_layout.addWidget(self.details_title)
        right_layout.addWidget(self.details_type)
        right_layout.addWidget(self.details_category)
        right_layout.addWidget(self.details_topic)
        right_layout.addWidget(self.details_links)
        right_layout.addWidget(self.details_description)
        right_layout.addLayout(actions)
        right_layout.addWidget(rel_title)
        right_layout.addWidget(self.relations_list, 1)
        right_layout.addWidget(self.remove_relation_button, 0, Qt.AlignRight)
        right_layout.addWidget(entries_title)
        right_layout.addLayout(entries_filters)
        right_layout.addWidget(self.entries_list, 2)

        splitter.addWidget(category_panel)
        splitter.addWidget(list_panel)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 3)
        layout.addWidget(splitter, 1)

        self._set_action_state(False)
        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QLabel#CollectionsTitle {
                color: #e6e6e6;
                font-size: 20px;
                font-weight: 600;
            }
            QLabel#CollectionsCategoriesTitle {
                color: #d8d8d8;
                font-size: 13px;
                font-weight: 600;
            }
            QTreeWidget {
                background: #14171c;
                border: 1px solid #2f333b;
                border-radius: 10px;
                color: #e6e6e6;
            }
            QTreeWidget::item {
                padding: 6px 10px;
            }
            QTreeWidget::item:selected {
                background: #2d3440;
            }
            QListWidget {
                background: #14171c;
                border: 1px solid #2f333b;
                border-radius: 10px;
                color: #e6e6e6;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid #21242b;
            }
            QListWidget::item:selected {
                background: #2d3440;
            }
            QLineEdit, QComboBox {
                background: #1f232a;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e6e6e6;
                min-height: 26px;
            }
            QCheckBox {
                color: #d8d8d8;
            }
            QToolButton {
                background: #232831;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px 12px;
                color: #e6e6e6;
            }
            QLabel#CollectionsDetailsTitle {
                color: #ffffff;
                font-size: 17px;
                font-weight: 600;
            }
            QLabel#CollectionsRelationsTitle {
                color: #d8d8d8;
                font-size: 13px;
                font-weight: 600;
            }
            """
        )

    def _set_action_state(self, has_selection: bool) -> None:
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.refresh_import_button.setEnabled(has_selection)
        self.link_button.setEnabled(has_selection)
        self.remove_relation_button.setEnabled(has_selection)
        if not has_selection:
            self.details_title.setText("Выберите элемент")
            self.details_type.setText("")
            self.details_category.setText("")
            self.details_topic.setText("")
            self.details_links.setText("")
            self.details_description.setText("")
            self.relations_list.clear()
            self.entries_list.clear()
            self._entries = []
            self._entries_by_id = {}

    def _refresh_entries(self) -> None:
        if self._current_item_id is None:
            self.entries_list.clear()
            return
        self._entries = self._db.fetch_collection_entries(self._current_item_id)
        self._entries_by_id = {entry.id: entry for entry in self._entries}
        allow_kinds = set()
        if self.filter_images.isChecked():
            allow_kinds.add("image")
        if self.filter_videos.isChecked():
            allow_kinds.add("video")
        if self.filter_docs.isChecked():
            allow_kinds.add("document")
        if self.filter_other.isChecked():
            allow_kinds.add("other")

        def allowed(entry: CollectionEntryData) -> bool:
            kind = FolderCollectionImporter.classify_extension(entry.ext)
            return kind in allow_kinds

        entries = [entry for entry in self._entries if allowed(entry)]
        self.entries_list.blockSignals(True)
        self.entries_list.clear()
        if self.group_by_folder.isChecked():
            groups: Dict[str, List[CollectionEntryData]] = {}
            for entry in entries:
                folder = str(Path(entry.rel_path).parent)
                if folder == ".":
                    folder = "Корень"
                groups.setdefault(folder, []).append(entry)
            for folder in sorted(groups.keys()):
                header = QListWidgetItem(folder)
                header.setFlags(Qt.ItemIsEnabled)
                header.setData(Qt.UserRole, ("header", folder))
                self.entries_list.addItem(header)
                for entry in groups[folder]:
                    self._add_entry_item(entry)
        else:
            for entry in entries:
                self._add_entry_item(entry)
        self.entries_list.blockSignals(False)

        if not entries:
            empty = QListWidgetItem("Нет элементов по текущим фильтрам.")
            empty.setFlags(Qt.ItemIsEnabled)
            empty.setData(Qt.UserRole, ("empty", None))
            self.entries_list.addItem(empty)

    def _add_entry_item(self, entry: CollectionEntryData) -> None:
        label = entry.rel_path
        if entry.is_missing:
            label = f"[нет файла] {label}"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, ("entry", entry.id))
        kind = FolderCollectionImporter.classify_extension(entry.ext)
        icon = self._entry_icon_for(entry, kind)
        item.setIcon(icon)
        if entry.is_missing:
            item.setForeground(QColor("#8b8b8b"))
        self.entries_list.addItem(item)

    def _entry_icon_for(self, entry: CollectionEntryData, kind: str) -> QIcon:
        if kind in {"image", "video"} and entry.source_path:
            thumb_path = self._entry_thumb_path(entry)
            if thumb_path.exists():
                return QIcon(str(thumb_path))
            worker = _EntryThumbWorker(
                entry.id,
                entry.source_path,
                thumb_path,
                self._entry_thumb_size,
                self._entry_thumb_signals,
                kind,
            )
            self._entry_thumb_pool.start(worker)
            return self._entry_placeholder_icon(kind)
        return self._entry_placeholder_icon(kind)

    def _entry_thumb_path(self, entry: CollectionEntryData) -> Path:
        safe_name = str(entry.id)
        return self._entry_thumb_dir / f"{safe_name}.png"

    def _entry_placeholder_icon(self, kind: str) -> QIcon:
        key = f"__entry_{kind}__"
        cached = self._thumb_cache.get(key)
        if cached is not None:
            return cached
        color = {
            "image": "#2d6cdf",
            "video": "#c26b1d",
            "document": "#2f8f5b",
            "other": "#5a5f6b",
        }.get(kind, "#5a5f6b")
        pixmap = QPixmap(self._entry_thumb_size)
        pixmap.fill(QColor(color))
        painter = QPainter(pixmap)
        painter.setPen(Qt.white)
        painter.drawRect(0, 0, self._entry_thumb_size.width() - 1, self._entry_thumb_size.height() - 1)
        painter.setBrush(Qt.white)
        if kind == "video":
            w = self._entry_thumb_size.width()
            h = self._entry_thumb_size.height()
            points = [
                (w * 0.38, h * 0.28),
                (w * 0.38, h * 0.72),
                (w * 0.72, h * 0.5),
            ]
            painter.drawPolygon([QPointF(x, y) for x, y in points])
        elif kind == "document":
            w = self._entry_thumb_size.width()
            h = self._entry_thumb_size.height()
            rect_w = w * 0.5
            rect_h = h * 0.6
            x = (w - rect_w) / 2
            y = (h - rect_h) / 2
            painter.drawRect(int(x), int(y), int(rect_w), int(rect_h))
        painter.end()
        icon = QIcon(pixmap)
        self._thumb_cache[key] = icon
        return icon

    def _on_entry_thumb_ready(self, entry_id: int, thumb_path: str) -> None:
        for row in range(self.entries_list.count()):
            item = self.entries_list.item(row)
            payload = item.data(Qt.UserRole)
            if not payload or payload[0] != "entry":
                continue
            if payload[1] == entry_id:
                item.setIcon(QIcon(thumb_path))
                break

    def _open_entry(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.UserRole)
        if not payload or payload[0] != "entry":
            return
        entry = self._entries_by_id.get(payload[1])
        if entry is None:
            return
        if entry.is_missing:
            QMessageBox.information(self, "Коллекции", "Файл помечен как отсутствующий.")
            return
        path = Path(entry.source_path)
        if not path.exists():
            QMessageBox.warning(self, "Коллекции", "Файл не найден.")
            return
        kind = FolderCollectionImporter.classify_extension(entry.ext)
        if kind in {"image", "video", "document"}:
            media_entries = [
                e
                for e in self._entries
                if FolderCollectionImporter.classify_extension(e.ext) in {"image", "video", "document"}
                and not e.is_missing
            ]
            try:
                start_index = next(i for i, e in enumerate(media_entries) if e.id == entry.id)
            except StopIteration:
                start_index = 0
            dialog = CollectionMediaPreviewDialog(media_entries, start_index=start_index, parent=self)
            dialog.exec()
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _selected_category_id(self) -> Optional[int]:
        if not hasattr(self, "category_tree"):
            return None
        item = self.category_tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.UserRole)

    def _category_children_map(self) -> Dict[Optional[int], List[CollectionCategoryData]]:
        children: Dict[Optional[int], List[CollectionCategoryData]] = {}
        for category in self._categories:
            children.setdefault(category.parent_id, []).append(category)
        for values in children.values():
            values.sort(key=lambda c: (c.sort_index, c.title.lower(), c.id))
        return children

    def _category_descendants(self, category_id: int) -> List[int]:
        children_map = self._category_children_map()
        result: List[int] = []
        stack = [category_id]
        while stack:
            current = stack.pop()
            for child in children_map.get(current, []):
                result.append(child.id)
                stack.append(child.id)
        return result

    def _category_filter_ids(self) -> Optional[List[int]]:
        category_id = self._selected_category_id()
        if category_id is None:
            return None
        if self.include_subcategories.isChecked():
            return [category_id] + self._category_descendants(category_id)
        return [category_id]

    def _category_options(self) -> List[tuple[str, Optional[int]]]:
        path_map = self._category_path_map()
        options = [(path, cat_id) for cat_id, path in path_map.items()]
        options.sort(key=lambda pair: pair[0].lower())
        return options

    def _category_path_map(self) -> Dict[int, str]:
        result: Dict[int, str] = {}
        for category in self._categories:
            parts = [category.title]
            parent_id = category.parent_id
            while parent_id is not None and parent_id in self._categories_by_id:
                parent = self._categories_by_id[parent_id]
                parts.append(parent.title)
                parent_id = parent.parent_id
            result[category.id] = " / ".join(reversed(parts))
        return result

    def _refresh_categories(self, selected_category_id: Optional[int]) -> None:
        self._categories = self._db.fetch_collection_categories()
        self._categories_by_id = {cat.id: cat for cat in self._categories}
        self._rebuild_category_tree(selected_category_id)

    def _find_category_tree_item(self, root: QTreeWidgetItem, category_id: int) -> Optional[QTreeWidgetItem]:
        if root.data(0, Qt.UserRole) == category_id:
            return root
        for idx in range(root.childCount()):
            child = root.child(idx)
            found = self._find_category_tree_item(child, category_id)
            if found is not None:
                return found
        return None

    def _rebuild_category_tree(self, selected_category_id: Optional[int]) -> None:
        if not hasattr(self, "category_tree"):
            return
        self.category_tree.blockSignals(True)
        self.category_tree.clear()
        root = QTreeWidgetItem(["Все коллекции"])
        root.setData(0, Qt.UserRole, None)
        self.category_tree.addTopLevelItem(root)
        children_map = self._category_children_map()

        def add_children(parent_item: QTreeWidgetItem, parent_id: Optional[int]) -> None:
            for category in children_map.get(parent_id, []):
                item = QTreeWidgetItem([category.title])
                item.setData(0, Qt.UserRole, category.id)
                parent_item.addChild(item)
                add_children(item, category.id)

        add_children(root, None)
        self.category_tree.expandToDepth(1)
        target_item = root
        if selected_category_id is not None:
            found = self._find_category_tree_item(root, selected_category_id)
            if found is not None:
                target_item = found
        self.category_tree.setCurrentItem(target_item)
        self.category_tree.blockSignals(False)

    def _open_category_menu(self, pos) -> None:
        item = self.category_tree.itemAt(pos)
        current_id = item.data(0, Qt.UserRole) if item is not None else None
        menu = QMenu(self)
        create_action = menu.addAction("Создать категорию")
        create_child_action = menu.addAction("Создать подкатегорию")
        rename_action = menu.addAction("Переименовать")
        move_action = menu.addAction("Переместить")
        delete_action = menu.addAction("Удалить")
        if item is None:
            create_child_action.setEnabled(False)
            rename_action.setEnabled(False)
            move_action.setEnabled(False)
            delete_action.setEnabled(False)
        elif current_id is None:
            create_child_action.setEnabled(True)
            rename_action.setEnabled(False)
            move_action.setEnabled(False)
            delete_action.setEnabled(False)
        action = menu.exec(self.category_tree.mapToGlobal(pos))
        if action is None:
            return
        if action == create_action:
            self._create_category(parent_id=None)
        elif action == create_child_action and current_id is not None:
            self._create_category(parent_id=current_id)
        elif action == rename_action and current_id is not None:
            self._rename_category(current_id)
        elif action == move_action and current_id is not None:
            self._move_category(current_id)
        elif action == delete_action and current_id is not None:
            self._delete_category(current_id)

    def _create_category(self, parent_id: Optional[int]) -> None:
        title, ok = QInputDialog.getText(self, "Категории", "Название категории:")
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        try:
            self._db.create_collection_category(title, parent_id=parent_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории", str(exc))
            return
        self.refresh_collections()

    def _rename_category(self, category_id: int) -> None:
        category = self._categories_by_id.get(category_id)
        if category is None:
            return
        title, ok = QInputDialog.getText(self, "Категории", "Новое название:", text=category.title)
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        try:
            self._db.update_collection_category_title(category_id, title)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории", str(exc))
            return
        self.refresh_collections()

    def _move_category(self, category_id: int) -> None:
        excluded = {category_id, *self._category_descendants(category_id)}
        options: List[tuple[str, Optional[int]]] = [("Корень", None)]
        for label, cat_id in self._category_options():
            if cat_id in excluded:
                continue
            options.append((label, cat_id))
        labels = [label for label, _ in options]
        choice, ok = QInputDialog.getItem(self, "Категории", "Новый родитель:", labels, 0, False)
        if not ok:
            return
        new_parent_id = dict(options).get(choice)
        if new_parent_id == category_id:
            return
        try:
            self._db.move_collection_category(category_id, new_parent_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории", str(exc))
            return
        self.refresh_collections()

    def _delete_category(self, category_id: int) -> None:
        category = self._categories_by_id.get(category_id)
        if category is None:
            return
        dialog = ConfirmDialog(
            "Удалить категорию",
            f"Удалить категорию «{category.title}»?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, self) != QDialog.Accepted:
            return
        try:
            self._db.delete_collection_category(category_id)
        except ValueError:
            dialog = ConfirmDialog(
                "Категория не пуста",
                "Перенести подкатегории и коллекции в корень и удалить категорию?",
                parent=self,
                confirm_text="Перенести и удалить",
                cancel_text="Отмена",
            )
            if show_dialog_standard(dialog, self) != QDialog.Accepted:
                return
            self._db.delete_collection_category(
                category_id,
                move_children_to_root=True,
                move_items_to_root=True,
            )
        self.refresh_collections()

    def refresh_collections(self) -> None:
        selected_id = self._current_item_id
        selected_category_id = self._selected_category_id()
        self._refresh_categories(selected_category_id)
        topics = self._db.fetch_collection_topics()
        current_topic = self.topic_filter.currentData() if self.topic_filter.count() else ""
        self.topic_filter.blockSignals(True)
        self.topic_filter.clear()
        self.topic_filter.addItem("Все темы", "")
        for topic in topics:
            self.topic_filter.addItem(topic, topic)
        idx = self.topic_filter.findData(current_topic)
        if idx >= 0:
            self.topic_filter.setCurrentIndex(idx)
        self.topic_filter.blockSignals(False)

        self._items = self._db.fetch_collection_items(
            search_text=self.search_edit.text(),
            topic=self.topic_filter.currentData() or None,
            entity_type=self.type_filter.currentData() or None,
            category_ids=self._category_filter_ids(),
        )
        self._items_by_id = {item.id: item for item in self._items}

        self.items_list.blockSignals(True)
        self.items_list.clear()
        for item in self._items:
            label = f"{ENTITY_LABELS.get(item.entity_type, item.entity_type)} · {item.title}"
            if item.topic:
                label = f"{label}\n#{item.topic}"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.UserRole, item.id)
            list_item.setIcon(self._placeholder_icon())
            list_item.setSizeHint(QSize(220, 64))
            self.items_list.addItem(list_item)
            self._load_thumbnail(item.id, item.image_url)
        self.items_list.blockSignals(False)

        if not self._items:
            self._current_item_id = None
            self._set_action_state(False)
            return

        select_row = 0
        if selected_id is not None:
            for row in range(self.items_list.count()):
                if self.items_list.item(row).data(Qt.UserRole) == selected_id:
                    select_row = row
                    break
        self.items_list.setCurrentRow(select_row)
        self._on_item_selected(self.items_list.currentItem(), None)

    def _on_item_selected(self, current: Optional[QListWidgetItem], _previous) -> None:
        if current is None:
            self._current_item_id = None
            self._set_action_state(False)
            return
        item_id = current.data(Qt.UserRole)
        item = self._items_by_id.get(item_id)
        if item is None:
            self._set_action_state(False)
            return

        self._current_item_id = item.id
        self.details_title.setText(item.title)
        category_title = "—"
        if item.category_id is not None:
            category = self._categories_by_id.get(item.category_id)
            if category is not None:
                category_title = category.title
        self.details_category.setText(f"Категория: {category_title}")
        self.details_type.setText(f"Тип: {ENTITY_LABELS.get(item.entity_type, item.entity_type)}")
        self.details_topic.setText(f"Тема: {item.topic or '—'}")
        links: List[str] = []
        if item.source_url:
            links.append(f"<a href='{item.source_url}'>Источник</a>")
        if item.image_url:
            links.append(f"<a href='{item.image_url}'>Изображение</a>")
        self.details_links.setText(" · ".join(links) if links else "Ссылки: —")
        self.details_description.setText(item.description or "Описание не задано.")

        self._relations = self._db.fetch_collection_relations(item.id)
        self.relations_list.clear()
        all_items = {it.id: it for it in self._db.fetch_collection_items()}
        for rel in self._relations:
            other_id = rel.right_item_id if rel.left_item_id == item.id else rel.left_item_id
            other = all_items.get(other_id)
            if other is None:
                continue
            text = f"{item.title} {rel.relation_kind} {other.title}"
            row = QListWidgetItem(text)
            row.setData(Qt.UserRole, rel.id)
            self.relations_list.addItem(row)
        self._set_action_state(True)
        self._refresh_entries()

    def _add_item(self) -> None:
        dialog = CollectionItemEditDialog(parent=self, category_options=self._category_options())
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        try:
            self._db.create_collection_item(**dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self.refresh_collections()

    def _current_item(self) -> Optional[CollectionItemData]:
        if self._current_item_id is None:
            return None
        return next((item for item in self._items if item.id == self._current_item_id), None)

    def _edit_current_item(self) -> None:
        item = self._current_item()
        if item is None:
            return
        dialog = CollectionItemEditDialog(item=item, parent=self, category_options=self._category_options())
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        try:
            self._db.update_collection_item(item.id, **dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self.refresh_collections()

    def _delete_current_item(self) -> None:
        item = self._current_item()
        if item is None:
            return
        dialog = ConfirmDialog(
            "Удалить элемент",
            f"Удалить элемент «{item.title}» и все его связи?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, self) != QDialog.Accepted:
            return
        self._db.delete_collection_item(item.id)
        self.refresh_collections()

    def _update_from_folder(self) -> None:
        item = self._current_item()
        if item is None:
            return
        folder_path = (item.source_folder_path or "").strip()
        if not folder_path:
            QMessageBox.information(self, "Коллекции", "У этой коллекции нет исходной папки.")
            return
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            QMessageBox.warning(self, "Коллекции", "Папка коллекции недоступна.")
            return
        options = {}
        if item.import_options_json:
            try:
                options = json.loads(item.import_options_json)
            except json.JSONDecodeError:
                options = {}
        include_subfolders = bool(options.get("include_subfolders", True))
        importer = FolderCollectionImporter()
        files, list_errors = importer.list_files(folder, include_subfolders=include_subfolders)
        if not self._confirm_large_folder(len(files)):
            return
        entries, errors = self._scan_with_progress(importer, folder, files)
        errors = list_errors + errors
        payload = [
            {
                "source_path": entry.source_path,
                "rel_path": entry.rel_path,
                "title": entry.title,
                "ext": entry.ext,
                "mime": entry.mime,
                "size_bytes": entry.size_bytes,
                "meta_json": entry.meta_json,
            }
            for entry in entries
        ]
        self._db.sync_collection_entries(item.id, payload)
        if not payload:
            QMessageBox.information(
                self,
                "Коллекции",
                "Папка пуста. Коллекция обновлена без элементов.",
            )
        if errors:
            self._report_import_errors(errors, "Обновление коллекции")
        self._refresh_entries()

    def _confirm_large_folder(self, total: int) -> bool:
        if total <= 2000:
            return True
        if total >= 10000:
            QMessageBox.warning(
                self,
                "Коллекции",
                "В папке более 10k файлов. Обновление может занять длительное время.",
            )
        dialog = ConfirmDialog(
            "Большая папка",
            f"В папке {total} файлов. Продолжить импорт?",
            parent=self,
            confirm_text="Продолжить",
            cancel_text="Отмена",
        )
        return show_dialog_standard(dialog, self) == QDialog.Accepted

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
            handle.write(f"\n[{datetime.utcnow().isoformat(timespec='seconds')}] {context}\n")
            for line in errors:
                handle.write(f"{line}\n")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Коллекции")
        box.setText(f"Обновление завершено с ошибками ({len(errors)}).")
        box.setInformativeText(f"Лог: {log_path}")
        open_btn = box.addButton("Открыть лог", QMessageBox.ActionRole)
        box.addButton("Ок", QMessageBox.AcceptRole)
        box.exec()
        if box.clickedButton() == open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path)))

    def _add_relation(self) -> None:
        item = self._current_item()
        if item is None:
            return
        candidates = [it for it in self._db.fetch_collection_items() if it.id != item.id]
        if not candidates:
            QMessageBox.information(self, "Связи", "Нет доступных элементов для связывания.")
            return
        dialog = CollectionRelationDialog(item, candidates, parent=self)
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        values = dialog.values()
        try:
            self._db.create_collection_relation(item.id, int(values["target_id"]), values["relation_kind"])
        except ValueError as exc:
            QMessageBox.warning(self, "Связи", str(exc))
            return
        self.refresh_collections()

    def _remove_relation(self) -> None:
        if self._current_item_id is None:
            return
        current = self.relations_list.currentItem()
        if current is None:
            QMessageBox.information(self, "Связи", "Выберите связь для удаления.")
            return
        relation_id = current.data(Qt.UserRole)
        self._db.delete_collection_relation(int(relation_id))
        self.refresh_collections()

    def focus_item(self, item_id: int) -> None:
        self.refresh_collections()
        for row in range(self.items_list.count()):
            item = self.items_list.item(row)
            if item.data(Qt.UserRole) == item_id:
                self.items_list.setCurrentRow(row)
                self._on_item_selected(item, None)
                break

    def _placeholder_icon(self) -> QIcon:
        key = "__placeholder__"
        cached = self._thumb_cache.get(key)
        if cached is not None:
            return cached
        pixmap = QPixmap(self._thumb_size)
        pixmap.fill(QColor("#1f232a"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#3a3f4a"))
        painter.drawRect(0, 0, self._thumb_size.width() - 1, self._thumb_size.height() - 1)
        painter.end()
        icon = QIcon(pixmap)
        self._thumb_cache[key] = icon
        return icon

    def _load_thumbnail(self, item_id: int, image_url: str) -> None:
        url = (image_url or "").strip()
        if not url:
            return
        if url in self._thumb_cache:
            self._apply_thumbnail_icon(item_id, self._thumb_cache[url])
            return
        if url in self._thumb_pending_urls:
            return
        qurl = QUrl.fromUserInput(url)
        if not qurl.isValid() or qurl.isEmpty():
            return
        request = QNetworkRequest(qurl)
        reply = self._thumb_loader.get(request)
        reply.setProperty("collection_item_id", item_id)
        reply.setProperty("thumb_url", url)
        self._thumb_pending_urls.add(url)

    def _on_thumb_loaded(self, reply: QNetworkReply) -> None:
        url = str(reply.property("thumb_url") or "").strip()
        item_id = int(reply.property("collection_item_id") or 0)
        if url:
            self._thumb_pending_urls.discard(url)
        icon: Optional[QIcon] = None
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll().data()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled = pixmap.scaled(
                    self._thumb_size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                cropped = QPixmap(self._thumb_size)
                cropped.fill(Qt.transparent)
                painter = QPainter(cropped)
                x = (scaled.width() - self._thumb_size.width()) // 2
                y = (scaled.height() - self._thumb_size.height()) // 2
                painter.drawPixmap(-x, -y, scaled)
                painter.end()
                icon = QIcon(cropped)
        if icon is not None:
            if url:
                self._thumb_cache[url] = icon
            if item_id:
                self._apply_thumbnail_icon(item_id, icon)
        reply.deleteLater()

    def _apply_thumbnail_icon(self, item_id: int, icon: QIcon) -> None:
        for row in range(self.items_list.count()):
            item = self.items_list.item(row)
            if item.data(Qt.UserRole) == item_id:
                item.setIcon(icon)
                break
