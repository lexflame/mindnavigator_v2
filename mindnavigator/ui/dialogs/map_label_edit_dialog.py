"""Modernized map label edit dialog and reusable chip inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QColorDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSpacerItem,
    QDoubleSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
from mindnavigator.storage import get_database
from mindnavigator.ui.dialogs.attach_file_select_nav import AttachFileSelectNav


@dataclass(frozen=True)
class ChipItem:
    id: int
    title: str


@dataclass(frozen=True)
class MapLabelEntitySource:
    label: str
    items: list
    label_fn: Callable[[object], str]


class FlowLayout(QLayout):
    """Flow layout with wrapping based on available width."""

    def __init__(self, parent=None, margin: int = 0, spacing: int = 8):
        super().__init__(parent)
        self._items: list = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item) -> None:  # noqa: N802 - Qt API
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802 - Qt API
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):  # noqa: N802 - Qt API
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + spacing
            if next_x - spacing > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + spacing
                next_x = x + hint.width() + spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()


class Chip(QWidget):
    removeRequested = Signal(int)

    def __init__(self, item: ChipItem, parent=None) -> None:
        super().__init__(parent)
        self._item = item
        self.setObjectName("Chip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 6, 2)
        layout.setSpacing(6)

        self.label = QLabel(item.title)
        self.label.setObjectName("ChipLabel")
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        remove_btn = QToolButton()
        remove_btn.setObjectName("ChipRemove")
        remove_btn.setText("✕")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setAutoRaise(True)
        remove_btn.clicked.connect(lambda: self.removeRequested.emit(item.id))

        layout.addWidget(self.label)
        layout.addWidget(remove_btn)

    @property
    def item(self) -> ChipItem:
        return self._item


class TagChipsInput(QWidget):
    itemsChanged = Signal(list)
    addRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[ChipItem] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.flow_container = QWidget()
        self.flow_container.setObjectName("ChipFlow")
        self.flow_layout = FlowLayout(self.flow_container, spacing=6)
        self.flow_container.setLayout(self.flow_layout)
        self.flow_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.add_button = QToolButton()
        self.add_button.setObjectName("ChipAddButton")
        self.add_button.setText("+")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.addRequested.emit)

        layout.addWidget(self.flow_container, 1)
        layout.addWidget(self.add_button, 0)

    def items(self) -> list[ChipItem]:
        return list(self._items)

    def set_items(self, items: Iterable[ChipItem]) -> None:
        self._items = list(items)
        self._rebuild()

    def add_items(self, items: Iterable[ChipItem]) -> None:
        existing = {item.id for item in self._items}
        for item in items:
            if item.id not in existing:
                self._items.append(item)
                existing.add(item.id)
        self._rebuild()

    def remove_item(self, item_id: int) -> None:
        self._items = [item for item in self._items if item.id != item_id]
        self._rebuild()

    def _rebuild(self) -> None:
        while self.flow_layout.count():
            child = self.flow_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()
        for item in self._items:
            chip = Chip(item, self.flow_container)
            chip.removeRequested.connect(self._on_chip_remove)
            self.flow_layout.addWidget(chip)
        self.itemsChanged.emit(self.items())

    def _on_chip_remove(self, item_id: int) -> None:
        self.remove_item(item_id)


class EntityPickerDialog(QDialog):
    def __init__(self, entity_type: str, fetch_fn: Callable[[str], list[ChipItem]], selected_ids=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("EntityPickerDialog")
        self.setWindowTitle(f"Выбор: {entity_type}")
        self.resize(520, 420)
        self._fetch_fn = fetch_fn
        self._selected_ids = set(selected_ids or [])
        self._items: list[ChipItem] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.textChanged.connect(self._reload)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Добавить")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(self.search_input)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog#EntityPickerDialog {
                background: #171a22;
                color: #d8d8d8;
            }
            QLineEdit {
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }
            QListWidget {
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 6px 8px;
            }
            QDialogButtonBox QPushButton {
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QDialogButtonBox QPushButton:hover {
                background: #34363b;
            }
            """
        )

        self._reload()

    def selected_items(self) -> list[ChipItem]:
        selected = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            data = item.data(Qt.UserRole)
            if not data:
                continue
            if item.checkState() == Qt.Checked:
                selected.append(data)
        return selected

    def _reload(self) -> None:
        query = self.search_input.text().strip().lower()
        self._items = self._fetch_fn(query)
        self.list_widget.clear()
        if not self._items:
            empty = QListWidgetItem("— нет элементов —")
            empty.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(empty)
            return
        for chip in self._items:
            entry = QListWidgetItem(chip.title)
            entry.setData(Qt.UserRole, chip)
            entry.setFlags(entry.flags() | Qt.ItemIsUserCheckable)
            entry.setCheckState(Qt.Checked if chip.id in self._selected_ids else Qt.Unchecked)
            self.list_widget.addItem(entry)


class ImageDropLabel(QLabel):
    imageDropped = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("ImageDrop")
        self.setAlignment(Qt.AlignCenter)
        self._has_image = False
        self._placeholder = "Перетащите изображение\\nили выберите файл"
        self.setText(self._placeholder)

    def has_image(self) -> bool:
        return self._has_image

    def set_image(self, pixmap: QPixmap | None) -> None:
        self._has_image = pixmap is not None and not pixmap.isNull()
        if self._has_image:
            self.setPixmap(pixmap)
            self.setText("")
        else:
            self.setPixmap(QPixmap())
            self.setText(self._placeholder)
        self.update()

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt API
        urls = event.mimeData().urls()
        if not urls:
            return
        local = urls[0].toLocalFile()
        if local:
            self.imageDropped.emit(local)


class MapLabelEditDialog(QDialog):
    def __init__(
        self,
        marker,
        entity_sources: dict[str, MapLabelEntitySource],
        type_suggestions: list[str] | None = None,
        mode: str = "edit",
        size_range: tuple[float, float] = (2.0, 240.0),
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MapLabelEditDialog")
        self._db = get_database()
        self._marker = marker
        self._entity_sources = entity_sources
        self._dirty = False
        self._resize_requested = False
        self._image_path = ""
        self._image_icon: QIcon | None = None
        self._parent_path = ""
        self._size_range = size_range
        self._chip_inputs: dict[str, TagChipsInput] = {}
        self._loading = True

        self.setWindowTitle("Метка на карте")
        self.resize(1100, 760)
        self.setMinimumSize(840, 520)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        header = self._build_header(mode)
        body = self._build_body(type_suggestions or [])

        root_layout.addWidget(header)
        root_layout.addWidget(body, 1)

        self._apply_styles()
        self._sync_from_marker()
        self._wire_dirty_tracking()
        self._loading = False

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_save)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_save)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.reject)

    def result_marker(self):
        return self._marker

    def resize_requested(self) -> bool:
        return self._resize_requested

    def image_path(self) -> str:
        return self._image_path

    def parent_path(self) -> str:
        return self._parent_path

    def _build_header(self, mode: str) -> QWidget:
        header = QFrame()
        header.setObjectName("MapLabelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(12)

        title = QLabel("Метка на карте" if mode == "edit" else "Новая метка")
        title.setObjectName("MapLabelTitle")

        self.dirty_indicator = QLabel("●")
        self.dirty_indicator.setObjectName("MapLabelDirty")
        self.dirty_indicator.setVisible(False)
        self.dirty_indicator.setToolTip("Есть несохранённые изменения")

        header_layout.addWidget(title)
        header_layout.addWidget(self.dirty_indicator)
        header_layout.addItem(QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("MapLabelPrimary")
        self.save_button.clicked.connect(self._on_save)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)

        close_button = QToolButton()
        close_button.setObjectName("MapLabelClose")
        close_button.setText("✕")
        close_button.clicked.connect(self.reject)

        header_layout.addWidget(self.save_button)
        header_layout.addWidget(self.cancel_button)
        header_layout.addWidget(close_button)

        return header

    def _build_body(self, type_suggestions: list[str]) -> QWidget:
        body = QFrame()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        left = self._build_left_panel()
        right = self._build_right_panel(type_suggestions)

        body_layout.addWidget(left, 0)
        body_layout.addWidget(right, 1)
        return body

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("MapLabelCard")
        panel.setFixedWidth(300)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(10)

        preview_label = QLabel("Превью")
        preview_label.setObjectName("MapLabelSectionTitle")

        self.preview = ImageDropLabel()
        self.preview.setFixedHeight(168)
        self.preview.imageDropped.connect(self._on_image_drop)

        preview_btn_row = QHBoxLayout()
        self.choose_image_btn = QToolButton()
        self.choose_image_btn.setText("Выбрать изображение…")
        self.choose_image_btn.clicked.connect(self._choose_image)
        self.clear_image_btn = QToolButton()
        self.clear_image_btn.setText("Очистить")
        self.clear_image_btn.clicked.connect(self._clear_image)
        preview_btn_row.addWidget(self.choose_image_btn)
        preview_btn_row.addWidget(self.clear_image_btn)

        self.image_hint = QLabel("Нет изображения")
        self.image_hint.setObjectName("MapLabelHint")

        color_label = QLabel("Цвет метки")
        color_label.setObjectName("MapLabelSectionTitle")
        self.color_preview = QLabel()
        self.color_preview.setObjectName("MapLabelColorPreview")
        self.color_preview.setFixedSize(28, 28)
        self.color_button = QToolButton()
        self.color_button.setText("Выбрать…")
        self.color_button.clicked.connect(self._pick_color)

        color_row = QHBoxLayout()
        color_row.addWidget(self.color_preview)
        color_row.addWidget(self.color_button)
        color_row.addStretch(1)

        panel_layout.addWidget(preview_label)
        panel_layout.addWidget(self.preview)
        panel_layout.addLayout(preview_btn_row)
        panel_layout.addWidget(self.image_hint)
        panel_layout.addSpacing(6)
        panel_layout.addWidget(color_label)
        panel_layout.addLayout(color_row)
        panel_layout.addStretch(1)
        return panel

    def _build_right_panel(self, type_suggestions: list[str]) -> QWidget:
        container = QFrame()
        container.setObjectName("MapLabelFormContainer")
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(16)

        form_layout.addWidget(self._build_section_main(type_suggestions))
        form_layout.addWidget(self._build_section_links())
        form_layout.addWidget(self._build_section_text())
        form_layout.addStretch(1)
        return container

    def _build_section_main(self, type_suggestions: list[str]) -> QWidget:
        section = QFrame()
        section.setObjectName("MapLabelSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Основное")
        title.setObjectName("MapLabelSectionTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название метки")

        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems(sorted({t for t in type_suggestions if t}))
        self.type_combo.setInsertPolicy(QComboBox.NoInsert)
        if type_suggestions:
            completer = QCompleter(sorted({t for t in type_suggestions if t}), self)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.type_combo.setCompleter(completer)

        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(*self._size_range)
        self.size_spin.setDecimals(1)
        self.size_spin.setSingleStep(0.5)
        self.size_hint = QLabel("px / ед.")
        self.size_hint.setObjectName("MapLabelHint")

        size_row = QHBoxLayout()
        size_row.addWidget(self.size_spin)
        size_row.addWidget(self.size_hint)
        size_row.addStretch(1)
        self.resize_btn = QToolButton()
        self.resize_btn.setText("Изменить размер…")
        self.resize_btn.clicked.connect(self._request_resize)
        size_row.addWidget(self.resize_btn)
        size_widget = QWidget()
        size_widget.setLayout(size_row)

        self.parent_path_edit = QLineEdit()
        self.parent_path_edit.setReadOnly(True)
        self.parent_path_edit.setPlaceholderText("Каталог не выбран")
        self.parent_path_edit.setToolTip("Каталог не выбран")
        self.parent_btn = QToolButton()
        self.parent_btn.setText("Выбрать…")
        self.parent_btn.clicked.connect(self._pick_parent_folder)
        parent_row = QHBoxLayout()
        parent_row.addWidget(self.parent_path_edit)
        parent_row.addWidget(self.parent_btn)
        parent_widget = QWidget()
        parent_widget.setLayout(parent_row)

        name_label = QLabel("Название")
        name_label.setObjectName("MapLabelFormLabel")
        type_label = QLabel("Тип")
        type_label.setObjectName("MapLabelFormLabel")
        size_label = QLabel("Размер")
        size_label.setObjectName("MapLabelFormLabel")
        parent_label = QLabel("Родительский каталог")
        parent_label.setObjectName("MapLabelFormLabel")

        form.addRow(name_label, self.name_edit)
        form.addRow(type_label, self.type_combo)
        form.addRow(size_label, size_widget)
        form.addRow(parent_label, parent_widget)

        layout.addLayout(form)
        return section

    def _build_section_links(self) -> QWidget:
        section = QFrame()
        section.setObjectName("MapLabelSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Привязки")
        title.setObjectName("MapLabelSectionTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)

        for key, source in self._entity_sources.items():
            chips = TagChipsInput()
            chips.addRequested.connect(lambda _checked=False, k=key: self._open_picker(k))
            chips.itemsChanged.connect(lambda _items, k=key: self._mark_dirty())
            self._chip_inputs[key] = chips
            chips_label = QLabel(source.label)
            chips_label.setObjectName("MapLabelFormLabel")
            form.addRow(chips_label, chips)

        layout.addLayout(form)
        return section

    def _build_section_text(self) -> QWidget:
        section = QFrame()
        section.setObjectName("MapLabelSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Текст")
        title.setObjectName("MapLabelSectionTitle")
        layout.addWidget(title)

        desc_label = QLabel("Описание")
        desc_label.setObjectName("MapLabelFieldLabel")
        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setPlaceholderText("Описание метки…")
        self.desc_counter = QLabel("0")
        self.desc_counter.setObjectName("MapLabelHint")

        layout.addWidget(desc_label)
        layout.addWidget(self.desc_edit)
        layout.addWidget(self.desc_counter)

        important_wrap = QFrame()
        important_wrap.setObjectName("MapLabelImportant")
        important_layout = QVBoxLayout(important_wrap)
        important_layout.setContentsMargins(10, 8, 10, 8)
        important_layout.setSpacing(6)

        important_header = QHBoxLayout()
        important_icon = QLabel("⚑")
        important_icon.setObjectName("MapLabelImportantIcon")
        important_label = QLabel("Важные пометки")
        important_label.setObjectName("MapLabelFieldLabel")
        important_header.addWidget(important_icon)
        important_header.addWidget(important_label)
        important_header.addStretch(1)

        self.important_edit = QPlainTextEdit()
        self.important_edit.setPlaceholderText("Ключевые пометки, инструкции, теги…")
        self.important_counter = QLabel("0")
        self.important_counter.setObjectName("MapLabelHint")

        important_layout.addLayout(important_header)
        important_layout.addWidget(self.important_edit)
        important_layout.addWidget(self.important_counter)

        layout.addWidget(important_wrap)
        return section

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QDialog#MapLabelEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QFrame#MapLabelHeader {{
                background: rgba(20, 22, 30, 0.92);
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }}
            QLabel#MapLabelTitle {{
                color: #f0f0f0;
                font-size: 16px;
                font-weight: 600;
            }}
            QLabel#MapLabelDirty {{
                color: #f1c24d;
                font-size: 14px;
            }}
            QFrame#MapLabelCard, QFrame#MapLabelSection {{
                background: rgba(22, 24, 32, 0.92);
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }}
            QLabel#MapLabelSectionTitle {{
                color: #d9d9d9;
                font-weight: 600;
            }}
            QLabel#MapLabelFieldLabel {{
                color: #b9bcc4;
            }}
            QLabel#MapLabelFormLabel {{
                color: #b9bcc4;
            }}
            QLabel#MapLabelHint {{
                color: #8e919a;
                font-size: 11px;
            }}
            QToolButton, QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
            QToolButton:hover, QPushButton:hover {{
                background: #34363b;
            }}
            QPushButton#MapLabelPrimary {{
                background: #3b4a7a;
                border: 1px solid #4b5c90;
            }}
            QPushButton#MapLabelPrimary:hover {{
                background: #475a91;
            }}
            QToolButton#MapLabelClose {{
                padding: 4px 8px;
                min-width: 28px;
            }}
            QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 14px;
            }}
            QLabel#MapLabelColorPreview {{
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}
            QLabel#ImageDrop {{
                border: 1px dashed #3a3b40;
                border-radius: 8px;
                color: #8e919a;
                background: #1b1d24;
            }}
            QFrame#MapLabelImportant {{
                border-left: 3px solid #d59d35;
                background: rgba(29, 31, 39, 0.85);
                border-radius: 8px;
            }}
            QWidget#ChipFlow {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
                padding: 4px;
            }}
            QWidget#Chip {{
                background: #2a2f36;
                border: 1px solid #3a3f46;
                border-radius: 12px;
            }}
            QLabel#ChipLabel {{
                color: #d7d7d7;
            }}
            QToolButton#ChipRemove {{
                background: transparent;
                border: none;
                color: #b0b0b0;
                padding: 0px;
            }}
            QToolButton#ChipRemove:hover {{
                color: #f1c24d;
            }}
            QToolButton#ChipAddButton {{
                min-width: 28px;
                padding: 4px 8px;
            }}
            """
        )

    def _sync_from_marker(self) -> None:
        self.name_edit.setText(self._marker.name)
        if self._marker.type:
            idx = self.type_combo.findText(self._marker.type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            else:
                self.type_combo.setCurrentText(self._marker.type)
        self.size_spin.setValue(float(self._marker.size))
        self._set_color(self._marker.color)
        self.desc_edit.setPlainText(self._marker.description or "")
        self.important_edit.setPlainText(self._marker.properties or "")

        self._set_chips("task", self._marker.task_ids)
        self._set_chips("project", self._marker.project_ids)
        self._set_chips("note", self._marker.note_ids)
        self._set_chips("object", self._marker.object_ids)
        self._set_chips("file", self._marker.file_ids)

        self._update_counters()
        self._load_image_preview(self._marker.image_path)

    def _set_chips(self, key: str, selected_ids: list[int]) -> None:
        source = self._entity_sources.get(key)
        chips = self._chip_inputs.get(key)
        if not source or not chips:
            return
        lookup = {item.id: source.label_fn(item) for item in source.items}
        items = [ChipItem(item_id, lookup.get(item_id, f"#{item_id}")) for item_id in selected_ids]
        chips.set_items(items)

    def _wire_dirty_tracking(self) -> None:
        self.name_edit.textChanged.connect(self._mark_dirty)
        self.type_combo.currentTextChanged.connect(self._mark_dirty)
        self.size_spin.valueChanged.connect(self._mark_dirty)
        self.parent_path_edit.textChanged.connect(self._mark_dirty)
        self.desc_edit.textChanged.connect(self._on_text_change)
        self.important_edit.textChanged.connect(self._on_text_change)

    def _on_text_change(self) -> None:
        self._mark_dirty()
        self._update_counters()

    def _update_counters(self) -> None:
        self.desc_counter.setText(f"{len(self.desc_edit.toPlainText())} символов")
        self.important_counter.setText(f"{len(self.important_edit.toPlainText())} символов")

    def _mark_dirty(self) -> None:
        if self._loading:
            return
        if not self._dirty:
            self._dirty = True
            self.dirty_indicator.setVisible(True)

    def _on_save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Проверка", "Название метки не может быть пустым.")
            return
        marker = self._marker
        def chip_ids(key: str) -> list[int]:
            chips = self._chip_inputs.get(key)
            return [item.id for item in chips.items()] if chips else []

        self._marker = marker.__class__(
            marker.id,
            name,
            marker.x,
            marker.y,
            self._selected_color,
            self.type_combo.currentText().strip(),
            float(self.size_spin.value()),
            self.desc_edit.toPlainText().strip(),
            self.important_edit.toPlainText().strip(),
            chip_ids("task"),
            chip_ids("project"),
            chip_ids("note"),
            chip_ids("object"),
            chip_ids("file"),
            self._image_path,
        )
        self._dirty = False
        self.accept()

    def reject(self) -> None:
        if self._dirty:
            confirm = QMessageBox.question(
                self,
                "Несохранённые изменения",
                "Есть несохранённые изменения. Закрыть?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
        super().reject()

    def _request_resize(self) -> None:
        self._resize_requested = True
        self._on_save()

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(self._selected_color, self, "Цвет метки")
        if color.isValid():
            self._set_color(color)
            self._mark_dirty()

    def _set_color(self, color: QColor) -> None:
        self._selected_color = color
        self.color_preview.setStyleSheet(
            f"background: {color.name()}; border: 1px solid #2a2b2f; border-radius: 6px;"
        )

    def _load_image_preview(self, image_path: str) -> None:
        self._image_path = (image_path or "").strip()
        self._image_icon = None
        pixmap = self._pixmap_from_image_path(self._image_path)
        if pixmap is not None:
            scaled = pixmap.scaled(
                self.preview.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            self.preview.set_image(scaled)
        else:
            self.preview.set_image(None)
        self._update_image_hint()

    def _pixmap_from_image_path(self, image_path: str) -> QPixmap | None:
        if not image_path:
            return None
        path = Path(image_path)
        file_path = path if path.is_file() else None
        if file_path is None:
            cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
            if cloud_root:
                cloud_candidate = Path(cloud_root) / image_path
                if cloud_candidate.is_file():
                    file_path = cloud_candidate
        if not file_path:
            return None
        pixmap = QPixmap(str(file_path))
        if pixmap.isNull():
            return None
        return pixmap

    def _clear_image(self) -> None:
        self._image_path = ""
        self._image_icon = None
        self.preview.set_image(None)
        self._update_image_hint()
        self._mark_dirty()

    def _set_image(self, file_path: str) -> None:
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Изображение", "Не удалось загрузить изображение.")
            return
        scaled = pixmap.scaled(self.preview.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.preview.set_image(scaled)
        self._image_path = file_path
        self._image_icon = None
        self._update_image_hint()
        self._mark_dirty()

    def _on_image_drop(self, file_path: str) -> None:
        self._set_image(file_path)

    def _update_image_hint(self) -> None:
        if self._image_path:
            path = Path(self._image_path)
            self.image_hint.setText(path.name)
            self.image_hint.setToolTip(str(path))
        else:
            self.image_hint.setText("Нет изображения")
            self.image_hint.setToolTip("")

    def _choose_image(self) -> None:
        dialog = AttachFileSelectNav(self)
        if dialog.exec() != QDialog.Accepted:
            return
        rel_path = dialog.selected_rel_path()
        if not rel_path:
            return
        self._set_cloud_image(rel_path, dialog.selected_icon())

    def _set_cloud_image(self, rel_path: str, icon: QIcon | None) -> None:
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "Изображение", "Путь к облаку не задан.")
            return
        file_path = Path(cloud_root) / rel_path
        if file_path.is_file():
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.preview.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                self.preview.set_image(scaled)
                self._image_path = rel_path
                self._image_icon = icon
                self._update_image_hint()
                self._mark_dirty()
                return
        if icon is not None:
            fallback = icon.pixmap(self.preview.size())
            if not fallback.isNull():
                self.preview.set_image(fallback)
                self._image_path = rel_path
                self._image_icon = icon
                self._update_image_hint()
                self._mark_dirty()
                return
        QMessageBox.warning(self, "Изображение", "Не удалось загрузить файл из облака.")

    def _pick_parent_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Выберите каталог")
        if path:
            self._parent_path = path
            display = self._elide_path(path)
            self.parent_path_edit.setText(display)
            self.parent_path_edit.setToolTip(path)
            self._mark_dirty()

    def _elide_path(self, path: str) -> str:
        metrics = QFontMetrics(self.parent_path_edit.font())
        width = max(120, self.parent_path_edit.width() - 40)
        return metrics.elidedText(path, Qt.ElideMiddle, width)

    def _open_picker(self, key: str) -> None:
        source = self._entity_sources.get(key)
        chips = self._chip_inputs.get(key)
        if not source or not chips:
            return

        def fetch_fn(query: str) -> list[ChipItem]:
            items = []
            for item in source.items:
                title = source.label_fn(item)
                if query and query not in title.lower():
                    continue
                items.append(ChipItem(item.id, title))
            return items

        dialog = EntityPickerDialog(source.label, fetch_fn, [item.id for item in chips.items()], self)
        if dialog.exec() == QDialog.Accepted:
            chips.add_items(dialog.selected_items())
            self._mark_dirty()
