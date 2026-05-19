"""Диалог редактирования метки на карте и связанных сущностей.

Входные данные:
    Данные метки, изображения и связанные сущности.

Выходные данные:
    Обновлённые атрибуты метки и ссылки на сущности.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics, QGuiApplication, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSpacerItem,
    QDoubleSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)

from mindnavigator.storage import get_database
from mindnavigator.spaceenity.marker_types import (
    marker_type_by_key,
    marker_type_for_color,
    marker_type_icon,
    marker_type_options,
    marker_type_pixmap,
)
from mindnavigator.ui.dialogs.attach_file_select_nav import AttachFileSelectNav
from mindnavigator.ui.dialogs.entity_picker_dialog import ChipItem, EntityPickerDialog
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND

import qtawesome as qta


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
    fields_raw = data.get("custom_fields")
    custom_fields: list[tuple[str, str]] = []
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


def _serialize_marker_properties_blob(important: str, custom_fields: list[tuple[str, str]]) -> str:
    clean_important = (important or "").strip()
    cleaned_fields = []
    for name, value in custom_fields:
        n = (name or "").strip()
        v = (value or "").strip()
        if not n and not v:
            continue
        cleaned_fields.append({"name": n, "value": v})
    if not cleaned_fields:
        return clean_important
    payload = {
        "important": clean_important,
        "custom_fields": cleaned_fields,
    }
    return json.dumps(payload, ensure_ascii=False)


@dataclass(frozen=True)
class MapLabelEntitySource:
    label: str
    items: list
    label_fn: Callable[[object], str]
    placeholder: str
    icon_name: str
    item_prefix: str


class FlowLayout(QLayout):
    """Flow layout with wrapping based on available width."""

    def __init__(self, parent=None, margin: int = 0, spacing: int = 8):
        # Инициализируем потоковую раскладку.
        super().__init__(parent)
        # Список элементов и параметры отступов.
        self._items: list = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item) -> None:  # noqa: N802 - Qt API
        # Добавляем элемент в потоковую раскладку.
        self._items.append(item)

    def count(self) -> int:
        # Количество элементов в раскладке.
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802 - Qt API
        # Получаем элемент по индексу.
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):  # noqa: N802 - Qt API
        # Удаляем и возвращаем элемент по индексу.
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        # Направления, в которых раскладка может расширяться.
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        # Высота зависит от ширины.
        return True

    def heightForWidth(self, width: int) -> int:
        # Рассчитываем высоту для заданной ширины.
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        # Применяем геометрию и раскладываем элементы.
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        # Предпочтительный размер равен минимальному.
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        # Рассчитываем минимальный размер с учетом полей.
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        # Раскладываем элементы по строкам, перенося при необходимости.
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + spacing
            if next_x - spacing > rect.right() and line_height > 0:
                # Переносим на новую строку.
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
        # Инициализируем чип с данными элемента.
        super().__init__(parent)
        # Сохраняем элемент и создаем визуальный чип.
        self._item = item
        self.setObjectName("Chip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 6, 2)
        layout.setSpacing(6)

        # Текст чипа.
        self.label = QLabel(item.title)
        self.label.setObjectName("ChipLabel")
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # Кнопка удаления чипа.
        remove_btn = QToolButton()
        remove_btn.setObjectName("ChipRemove")
        remove_btn.setText("✕")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setAutoRaise(True)
        remove_btn.clicked.connect(lambda: self.removeRequested.emit(item.id))

        layout.addWidget(self.label)
        layout.addWidget(remove_btn)

    @property
    def item(self) -> ChipItem:
        # Возвращаем связанный элемент.
        return self._item


@dataclass(frozen=True)
class EntityLinkItem:
    id: int
    title: str
    link: str


class TagChipsInput(QWidget):
    itemsChanged = Signal(list)
    addRequested = Signal()

    def __init__(self, parent=None) -> None:
        # Инициализируем контейнер чипов.
        super().__init__(parent)
        # Список выбранных элементов.
        self._items: list[ChipItem] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Контейнер с потоковой раскладкой чипов.
        self.flow_container = QWidget()
        self.flow_container.setObjectName("ChipFlow")
        self.flow_layout = FlowLayout(self.flow_container, spacing=6)
        self.flow_container.setLayout(self.flow_layout)
        self.flow_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Кнопка добавления новых чипов.
        self.add_button = QToolButton()
        self.add_button.setObjectName("ChipAddButton")
        self.add_button.setText("+")
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self.addRequested.emit)

        layout.addWidget(self.flow_container, 1)
        layout.addWidget(self.add_button, 0)

    def items(self) -> list[ChipItem]:
        # Возвращаем копию списка элементов.
        return list(self._items)

    def set_items(self, items: Iterable[ChipItem]) -> None:
        # Полностью заменяем список чипов.
        self._items = list(items)
        self._rebuild()

    def add_items(self, items: Iterable[ChipItem]) -> None:
        # Добавляем новые элементы без дубликатов.
        existing = {item.id for item in self._items}
        for item in items:
            if item.id not in existing:
                self._items.append(item)
                existing.add(item.id)
        self._rebuild()

    def remove_item(self, item_id: int) -> None:
        # Удаляем элемент по идентификатору.
        self._items = [item for item in self._items if item.id != item_id]
        self._rebuild()

    def _rebuild(self) -> None:
        # Перестраиваем визуальное представление чипов.
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
        # Обработчик удаления чипа.
        self.remove_item(item_id)


class LinkChip(QWidget):
    removeRequested = Signal(int)
    linkActivated = Signal(str)

    def __init__(self, item: EntityLinkItem, parent=None) -> None:
        # Инициализируем чип привязки сущности.
        super().__init__(parent)
        # Сохраняем данные ссылки и создаем чип.
        self._item = item
        self.setObjectName("EntityChip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 6, 2)
        layout.setSpacing(6)

        # Текстовая ссылка.
        self.label = QLabel(item.title)
        self.label.setObjectName("EntityChipLabel")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.label.setOpenExternalLinks(False)
        self.label.setText(f"<a href='{item.link}'>{item.title}</a>")
        self.label.linkActivated.connect(self.linkActivated.emit)

        # Кнопка удаления привязки.
        remove_btn = QToolButton()
        remove_btn.setObjectName("EntityChipRemove")
        remove_btn.setText("✕")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setAutoRaise(True)
        remove_btn.clicked.connect(lambda: self.removeRequested.emit(item.id))

        layout.addWidget(self.label)
        layout.addWidget(remove_btn)

    @property
    def item(self) -> EntityLinkItem:
        # Возвращаем связанную сущность.
        return self._item


class EntityLinksInput(QWidget):
    itemsChanged = Signal(list)
    searchChanged = Signal(str)
    clearRequested = Signal()
    addRequested = Signal()
    linkActivated = Signal(str)

    def __init__(self, placeholder: str, icon_name: str, parent=None) -> None:
        # Инициализируем поле привязок сущностей.
        super().__init__(parent)
        # Список выбранных привязок.
        self._items: list[EntityLinkItem] = []

        self.setObjectName("EntityLinksInput")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("EntityLinksIcon")
        icon = qta.icon(icon_name, color="#cfcfcf")
        self.icon_label.setPixmap(icon.pixmap(18, 18))
        self.icon_label.setFixedSize(20, 20)

        # Контейнер с чипами привязок.
        self.flow_container = QWidget()
        self.flow_container.setObjectName("EntityChipFlow")
        self.flow_layout = FlowLayout(self.flow_container, spacing=6)
        self.flow_container.setLayout(self.flow_layout)
        self.flow_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("EntityLinksSearch")
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.setClearButtonEnabled(False)
        self.search_input.textChanged.connect(self.searchChanged.emit)

        # Кнопка добавления.
        self.add_button = QToolButton()
        self.add_button.setObjectName("EntityLinksAdd")
        self.add_button.setIcon(qta.icon("fa5s.plus", color="#cfcfcf"))
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.setAutoRaise(True)
        self.add_button.setToolTip("Добавить привязки")
        self.add_button.clicked.connect(self.addRequested.emit)

        # Кнопка очистки.
        self.clear_button = QToolButton()
        self.clear_button.setObjectName("EntityLinksClear")
        self.clear_button.setIcon(qta.icon("fa5s.times", color="#cfcfcf"))
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setAutoRaise(True)
        self.clear_button.clicked.connect(self._on_clear_requested)

        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.flow_container, 1)
        layout.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.clear_button, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_items(self, items: Iterable[EntityLinkItem]) -> None:
        # Полностью заменяем список привязок.
        self._items = list(items)
        self._rebuild()

    def items(self) -> list[EntityLinkItem]:
        # Возвращаем копию списка привязок.
        return list(self._items)

    def add_items(self, items: Iterable[EntityLinkItem]) -> None:
        # Добавляем новые привязки без повторов.
        existing = {item.id for item in self._items}
        for item in items:
            if item.id not in existing:
                self._items.append(item)
                existing.add(item.id)
        self._rebuild()

    def remove_item(self, item_id: int) -> None:
        # Удаляем привязку по id.
        self._items = [item for item in self._items if item.id != item_id]
        self._rebuild()

    def clear_items(self) -> None:
        # Очищаем список привязок.
        if not self._items:
            return
        self._items = []
        self._rebuild()

    def clear_search(self) -> None:
        # Очищаем поле поиска без сигналов.
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

    def _rebuild(self) -> None:
        # Перерисовываем список чипов и поле ввода.
        while self.flow_layout.count():
            child = self.flow_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()
        for item in self._items:
            chip = LinkChip(item, self.flow_container)
            chip.removeRequested.connect(self._on_chip_remove)
            chip.linkActivated.connect(self.linkActivated.emit)
            self.flow_layout.addWidget(chip)
        self.flow_layout.addWidget(self.search_input)
        self.itemsChanged.emit(self.items())

    def _on_chip_remove(self, item_id: int) -> None:
        # Обработчик удаления чипа.
        self.remove_item(item_id)

    def _on_clear_requested(self) -> None:
        # Сигнал на очистку всех привязок.
        self.clearRequested.emit()


class CompleterPopupSync(QObject):
    def __init__(self, line_edit: QLineEdit, completer: QCompleter, max_visible_items: int = 8) -> None:
        # Инициализируем синхронизацию popup подсказок.
        super().__init__(line_edit)
        # Сохраняем источники и настраиваем popup.
        self._line_edit = line_edit
        self._completer = completer
        self._popup = completer.popup()
        self._max_visible_items = max_visible_items
        self._configure_popup()
        self._line_edit.installEventFilter(self)
        if self._popup:
            self._popup.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        # Отслеживаем изменения размеров/позиции для синхронизации popup.
        if watched in (self._line_edit, self._popup) and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.ScreenChangeInternal,
        }:
            self._sync_popup()
        return super().eventFilter(watched, event)

    def _configure_popup(self) -> None:
        # Базовая настройка popup подсказок.
        if not self._popup:
            return
        self._popup.setObjectName("CompleterPopup")
        self._popup.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._popup.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._popup.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._completer.setMaxVisibleItems(self._max_visible_items)
        self._sync_popup()

    def _sync_popup(self) -> None:
        # Синхронизируем ширину и позицию popup.
        if not self._popup:
            return
        width = self._line_edit.width()
        if width > 0:
            self._popup.setFixedWidth(width)
        if self._popup.isVisible():
            global_pos = self._line_edit.mapToGlobal(QPoint(0, self._line_edit.height()))
            self._popup.move(global_pos)
        self._update_max_height()

    def _update_max_height(self) -> None:
        # Ограничиваем высоту списка подсказок.
        if not self._popup:
            return
        row_height = self._popup.sizeHintForRow(0)
        if row_height > 0:
            padding = self._popup.frameWidth() * 2 + 4
            self._popup.setMaximumHeight(row_height * self._max_visible_items + padding)


class ImageDropLabel(QLabel):
    imageDropped = Signal(str)

    def __init__(self, parent=None) -> None:
        # Инициализируем label с поддержкой drag-n-drop.
        super().__init__(parent)
        # Включаем drag-n-drop и готовим плейсхолдер.
        self.setAcceptDrops(True)
        self.setObjectName("ImageDrop")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._has_image = False
        self._placeholder = "Перетащите изображение сюда\\nили выберите файл"
        self.setText(self._placeholder)

    def has_image(self) -> bool:
        # Проверяем наличие изображения.
        return self._has_image

    def set_image(self, pixmap: QPixmap | None) -> None:
        # Устанавливаем изображение или плейсхолдер.
        self._has_image = pixmap is not None and not pixmap.isNull()
        if self._has_image:
            self.setPixmap(pixmap)
            self.setText("")
        else:
            self.setPixmap(QPixmap())
            self.setText(self._placeholder)
        self.update()

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt API
        # Разрешаем перетаскивание файлов.
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt API
        # Принимаем файл и отправляем сигнал с путем.
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
        # Инициализируем диалог редактирования метки.
        super().__init__(parent)
        # Сохраняем исходные данные и состояние диалога.
        self.setObjectName("MapLabelEditDialog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._db = get_database()
        self._marker = marker
        self._entity_sources = entity_sources
        self._dirty = False
        self._resize_requested = False
        self._image_path = ""
        self._image_icon: Optional[QIcon] = None
        self._parent_path = ""
        self._size_range = size_range
        self._marker_type_options = marker_type_options()
        self._link_inputs: dict[str, EntityLinksInput] = {}
        self._link_title_maps: dict[str, dict[str, int]] = {}
        self._popup_syncs: list[CompleterPopupSync] = []
        self._loading = True
        self._dialog_mode = mode
        self._name_error_text = "Название обязательно"
        self._link_state_widgets: dict[str, tuple[QWidget, EntityLinksInput]] = {}

        # Настройки окна.
        self.setWindowTitle("Метка на карте")
        self.resize(1512, 838)
        self.setMinimumSize(780, 500)

        # Корневая компоновка.
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Собираем заголовок и основное тело.
        header = self._build_header(mode)
        body = self._build_body(type_suggestions or [])

        root_layout.addWidget(header)
        root_layout.addWidget(body, 1)

        # Применяем стили, наполняем форму и подключаем трекинг изменений.
        self._apply_styles()
        self._sync_from_marker()
        self._wire_dirty_tracking()
        self._loading = False

        # Горячие клавиши диалога.
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_save)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self._on_save)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.reject)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        # При показе разворачиваем и вписываем диалог в экран.
        super().showEvent(event)
        self._fit_to_screen()

    def result_marker(self):
        # Возвращаем обновленный объект маркера.
        return self._marker

    def resize_requested(self) -> bool:
        # Флаг запроса режима изменения размера.
        return self._resize_requested

    def image_path(self) -> str:
        # Текущий путь изображения.
        return self._image_path

    def parent_path(self) -> str:
        # Выбранный родительский каталог.
        return self._parent_path

    def _build_header(self, mode: str) -> QWidget:
        # Заголовок с кнопками сохранения/закрытия.
        header = QFrame()
        header.setObjectName("MapLabelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(12)

        self.header_title = QLabel("Метка на карте" if mode == "edit" else "Новая метка")
        self.header_title.setObjectName("MapLabelTitle")

        self.dirty_indicator = QLabel("•")
        self.dirty_indicator.setObjectName("MapLabelDirty")
        self.dirty_indicator.setVisible(False)
        self.dirty_indicator.setToolTip("Есть несохранённые изменения")

        header_layout.addWidget(self.header_title)
        header_layout.addWidget(self.dirty_indicator)
        header_layout.addItem(
            QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("MapLabelPrimary")
        self.save_button.clicked.connect(self._on_save)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)

        self.close_button = QToolButton()
        self.close_button.setObjectName("MapLabelClose")
        self.close_button.setText("×")
        self.close_button.clicked.connect(self.reject)

        header_layout.addWidget(self.save_button)
        header_layout.addWidget(self.cancel_button)
        header_layout.addWidget(self.close_button)

        return header

    def _build_body(self, type_suggestions: list[str]) -> QWidget:
        self.form_scroll = QScrollArea()
        self.form_scroll.setObjectName("MapLabelFormScroll")
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        body.setObjectName("MapLabelBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(14)
        top_row.setAlignment(Qt.AlignmentFlag.AlignTop)
        top_row.addWidget(self._build_left_panel(), 0, Qt.AlignmentFlag.AlignTop)
        top_row.addWidget(self._build_section_main(type_suggestions), 1, Qt.AlignmentFlag.AlignTop)

        body_layout.addLayout(top_row)
        body_layout.addWidget(self._build_section_links())
        body_layout.addWidget(self._build_section_text())
        body_layout.addWidget(self._build_section_additional_properties())
        body_layout.addStretch(1)

        self.form_scroll.setWidget(body)
        return self.form_scroll

    def _build_left_panel(self) -> QWidget:
        # Левая карточка с внешним видом маркера.
        panel = QFrame()
        panel.setObjectName("MapLabelCard")
        panel.setMinimumWidth(320)
        panel.setMaximumWidth(360)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(12)

        title = QLabel("Внешний вид")
        title.setObjectName("MapLabelSectionTitle")

        self.preview = ImageDropLabel()
        self.preview.setMinimumHeight(188)
        self.preview.imageDropped.connect(self._on_image_drop)

        preview_btn_row = QHBoxLayout()
        preview_btn_row.setSpacing(8)
        self.choose_image_btn = QToolButton()
        self.choose_image_btn.setText("Выбрать изображение")
        self.choose_image_btn.clicked.connect(self._choose_image)
        self.clear_image_btn = QToolButton()
        self.clear_image_btn.setText("Очистить")
        self.clear_image_btn.clicked.connect(self._clear_image)
        preview_btn_row.addWidget(self.choose_image_btn, 1)
        preview_btn_row.addWidget(self.clear_image_btn, 0)

        self.image_hint = QLabel("Нет изображения")
        self.image_hint.setObjectName("MapLabelHint")

        marker_type_label = QLabel("Тип метки")
        marker_type_label.setObjectName("MapLabelFieldLabel")
        self.marker_type_preview = QLabel()
        self.marker_type_preview.setObjectName("MapLabelMarkerPreview")
        self.marker_type_preview.setFixedSize(36, 36)
        self.marker_type_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.marker_type_combo = QComboBox()
        self.marker_type_combo.setObjectName("MapLabelMarkerType")
        self.marker_type_combo.setIconSize(QSize(20, 20))
        for option in self._marker_type_options:
            self.marker_type_combo.addItem(marker_type_icon(option), option.label, option.key)
        self.marker_type_combo.currentIndexChanged.connect(self._on_marker_type_changed)

        marker_type_row = QHBoxLayout()
        marker_type_row.addWidget(self.marker_type_preview)
        marker_type_row.addWidget(self.marker_type_combo, 1)

        divider = QFrame()
        divider.setObjectName("MapLabelDivider")
        divider.setFrameShape(QFrame.Shape.HLine)

        self.marker_type_summary = QLabel()
        self.marker_type_summary.setObjectName("MapLabelHint")
        self.marker_type_summary.setWordWrap(True)

        panel_layout.addWidget(title)
        panel_layout.addWidget(self.preview)
        panel_layout.addLayout(preview_btn_row)
        panel_layout.addWidget(self.image_hint)
        panel_layout.addWidget(divider)
        panel_layout.addWidget(marker_type_label)
        panel_layout.addLayout(marker_type_row)
        panel_layout.addWidget(self.marker_type_summary)
        panel_layout.addStretch(1)
        return panel

    def _build_section_main(self, type_suggestions: list[str]) -> QWidget:
        # Секция основных параметров метки.
        section = QFrame()
        section.setObjectName("MapLabelSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Основное")
        title.setObjectName("MapLabelSectionTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setHorizontalSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название маркера")
        self.name_error_label = QLabel(self._name_error_text)
        self.name_error_label.setObjectName("MapLabelError")
        self.name_error_label.setVisible(False)
        name_wrap = QWidget()
        name_layout = QVBoxLayout(name_wrap)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(4)
        name_layout.addWidget(self.name_edit)
        name_layout.addWidget(self.name_error_label)

        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems(sorted({t for t in type_suggestions if t}))
        self.type_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if type_suggestions:
            # Настраиваем автодополнение по типу.
            completer = QCompleter(sorted({t for t in type_suggestions if t}), self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.type_combo.setCompleter(completer)
            self._register_completer_popup(self.type_combo.lineEdit(), completer)

        self.size_spin = QDoubleSpinBox()
        min_size, max_size = self._size_range
        self.size_spin.setRange(min_size, max_size)
        self.size_spin.setDecimals(1)
        self.size_spin.setSingleStep(0.5)
        self.size_hint = QLabel("px / ед.")
        self.size_hint.setObjectName("MapLabelHint")

        size_row = QHBoxLayout()
        size_row.addWidget(self.size_spin)
        size_row.addWidget(self.size_hint)
        size_row.addStretch(1)
        self.resize_btn = QToolButton()
        self.resize_btn.setText("Изменить на карте")
        self.resize_btn.setToolTip("Закрыть форму и перейти к интерактивному изменению размера на карте")
        self.resize_btn.clicked.connect(self._request_resize)
        size_row.addWidget(self.resize_btn)
        size_widget = QWidget()
        size_widget.setLayout(size_row)

        self.parent_path_edit = QLineEdit()
        self.parent_path_edit.setReadOnly(True)
        self.parent_path_edit.setPlaceholderText("Каталог не выбран")
        self.parent_path_edit.setToolTip("Каталог не выбран")
        self.parent_btn = QToolButton()
        self.parent_btn.setText("Выбрать")
        self.parent_btn.clicked.connect(self._pick_parent_folder)
        self.parent_clear_btn = QToolButton()
        self.parent_clear_btn.setText("Очистить")
        self.parent_clear_btn.clicked.connect(self._clear_parent_path)
        parent_row = QHBoxLayout()
        parent_row.setSpacing(8)
        parent_row.addWidget(self.parent_path_edit)
        parent_row.addWidget(self.parent_btn)
        parent_row.addWidget(self.parent_clear_btn)
        parent_widget = QWidget()
        parent_widget.setLayout(parent_row)

        name_label = QLabel("Название *")
        name_label.setObjectName("MapLabelFormLabel")
        type_label = QLabel("Тип объекта")
        type_label.setObjectName("MapLabelFormLabel")
        size_label = QLabel("Размер на карте")
        size_label.setObjectName("MapLabelFormLabel")
        parent_label = QLabel("Родительский каталог")
        parent_label.setObjectName("MapLabelFormLabel")

        form.addRow(name_label, name_wrap)
        form.addRow(type_label, self.type_combo)
        form.addRow(size_label, size_widget)
        form.addRow(parent_label, parent_widget)

        layout.addLayout(form)
        return section

    def _build_section_links(self) -> QWidget:
        # Секция связей с вкладками по типам сущностей.
        section = QFrame()
        section.setObjectName("MapLabelSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Связи")
        title.setObjectName("MapLabelSectionTitle")
        layout.addWidget(title)

        self.links_tabs = QTabWidget()
        self.links_tabs.setObjectName("MapLabelLinksTabs")
        self.links_tabs.setDocumentMode(True)

        for key, source in self._entity_sources.items():
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(10)

            toolbar = QHBoxLayout()
            toolbar.setContentsMargins(0, 0, 0, 0)
            toolbar.setSpacing(8)
            helper = QLabel(f"Связанные {source.label.lower()}")
            helper.setObjectName("MapLabelHint")
            add_button = QToolButton()
            add_button.setObjectName("MapLabelInlineAdd")
            add_button.setText("+ Добавить")
            add_button.clicked.connect(lambda _checked=False, k=key: self._open_picker(k))
            toolbar.addWidget(helper)
            toolbar.addStretch(1)
            toolbar.addWidget(add_button)

            empty_state = QFrame()
            empty_state.setObjectName("MapLabelEmptyState")
            empty_layout = QVBoxLayout(empty_state)
            empty_layout.setContentsMargins(16, 14, 16, 14)
            empty_layout.setSpacing(4)
            empty_title, empty_body = self._link_empty_text(source.label)
            empty_title_label = QLabel(empty_title)
            empty_title_label.setObjectName("MapLabelEmptyTitle")
            empty_body_label = QLabel(empty_body)
            empty_body_label.setObjectName("MapLabelHint")
            empty_body_label.setWordWrap(True)
            empty_layout.addWidget(empty_title_label)
            empty_layout.addWidget(empty_body_label)

            link_input = EntityLinksInput(self._link_search_placeholder(source.label), source.icon_name)
            link_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            link_input.add_button.hide()
            link_input.itemsChanged.connect(lambda _items, k=key: self._on_links_changed(k))
            link_input.clearRequested.connect(lambda k=key: self._clear_links(k))
            link_input.linkActivated.connect(self._open_link)
            link_input.search_input.returnPressed.connect(
                lambda k=key, field=link_input: self._open_picker(k, field.search_input.text())
            )

            if key == "file":
                link_input.search_input.setReadOnly(True)
                link_input.search_input.setPlaceholderText("Выбрать файл")
                link_input.search_input.setCursor(Qt.CursorShape.PointingHandCursor)

                def _open_file_dialog(event, k=key, field=link_input.search_input):
                    if event.button() == Qt.MouseButton.LeftButton:
                        self._open_picker(k)
                    QLineEdit.mousePressEvent(field, event)

                link_input.search_input.mousePressEvent = _open_file_dialog
            else:
                labels = {source.label_fn(item): item.id for item in source.items}
                self._link_title_maps[key] = labels
                completer = QCompleter(list(labels.keys()), link_input.search_input)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                completer.activated[str].connect(lambda text, k=key: self._add_link_from_title(k, text))
                link_input.search_input.setCompleter(completer)
                self._register_completer_popup(link_input.search_input, completer)

                def _open_picker_on_empty_click(event, field=link_input.search_input, opener=add_button):
                    if event.button() == Qt.MouseButton.LeftButton and not field.text().strip():
                        opener.click()
                        return
                    QLineEdit.mousePressEvent(field, event)

                link_input.search_input.mousePressEvent = _open_picker_on_empty_click

            page_layout.addLayout(toolbar)
            page_layout.addWidget(empty_state)
            page_layout.addWidget(link_input)
            self.links_tabs.addTab(page, source.label)
            self._link_inputs[key] = link_input
            self._link_state_widgets[key] = (empty_state, link_input)

        layout.addWidget(self.links_tabs)
        return section

    def _build_section_text(self) -> QWidget:
        # Секция описания и важных заметок.
        section = QFrame()
        section.setObjectName("MapLabelSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Описание и заметки")
        title.setObjectName("MapLabelSectionTitle")
        layout.addWidget(title)

        fields_row = QHBoxLayout()
        fields_row.setContentsMargins(0, 0, 0, 0)
        fields_row.setSpacing(12)

        desc_wrap = QFrame()
        desc_wrap.setObjectName("MapLabelInnerPanel")
        desc_layout = QVBoxLayout(desc_wrap)
        desc_layout.setContentsMargins(12, 12, 12, 12)
        desc_layout.setSpacing(8)
        desc_label = QLabel("Описание")
        desc_label.setObjectName("MapLabelFieldLabel")
        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setPlaceholderText("Описание объекта на карте...")
        self.desc_counter = QLabel("0")
        self.desc_counter.setObjectName("MapLabelHint")
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.desc_edit)
        desc_layout.addWidget(self.desc_counter)

        important_wrap = QFrame()
        important_wrap.setObjectName("MapLabelInnerPanel")
        important_layout = QVBoxLayout(important_wrap)
        important_layout.setContentsMargins(12, 12, 12, 12)
        important_layout.setSpacing(8)
        important_label = QLabel("Важные пометки")
        important_label.setObjectName("MapLabelFieldLabel")
        self.important_edit = QPlainTextEdit()
        self.important_edit.setPlaceholderText("Критичные сведения, предупреждения, сюжетные детали...")
        self.important_counter = QLabel("0")
        self.important_counter.setObjectName("MapLabelHint")
        important_layout.addWidget(important_label)
        important_layout.addWidget(self.important_edit)
        important_layout.addWidget(self.important_counter)

        fields_row.addWidget(desc_wrap, 1)
        fields_row.addWidget(important_wrap, 1)
        layout.addLayout(fields_row)
        return section

    def _build_section_additional_properties(self) -> QWidget:
        section = QFrame()
        section.setObjectName("MapLabelSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        title = QLabel("Дополнительные свойства")
        title.setObjectName("MapLabelSectionTitle")
        self.custom_add_btn = QToolButton()
        self.custom_add_btn.setText("+ Добавить поле")
        self.custom_add_btn.clicked.connect(lambda: self._add_custom_field_row(mark_dirty=True))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.custom_add_btn)

        custom_wrap = QFrame()
        custom_wrap.setObjectName("MapLabelInnerPanel")
        custom_layout = QVBoxLayout(custom_wrap)
        custom_layout.setContentsMargins(12, 12, 12, 12)
        custom_layout.setSpacing(8)

        self.custom_fields_layout = QVBoxLayout()
        self.custom_fields_layout.setSpacing(6)
        self.custom_fields_placeholder = QLabel("Нет дополнительных свойств")
        self.custom_fields_placeholder.setObjectName("MapLabelHint")
        self.custom_fields_layout.addWidget(self.custom_fields_placeholder)
        self._custom_field_rows: list[tuple[QWidget, QLineEdit, QLineEdit]] = []

        custom_layout.addLayout(self.custom_fields_layout)
        layout.addLayout(header)
        layout.addWidget(custom_wrap)
        return section

    def _add_custom_field_row(self, name: str = "", value: str = "", mark_dirty: bool = False) -> None:
        row = QWidget()
        row.setObjectName("MapLabelCustomRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Ключ")
        value_edit = QLineEdit(value)
        value_edit.setPlaceholderText("Значение")
        remove_btn = QToolButton()
        remove_btn.setText("×")
        remove_btn.setToolTip("Удалить поле")
        remove_btn.clicked.connect(lambda: self._remove_custom_field_row(row))
        name_edit.textChanged.connect(self._on_text_change)
        value_edit.textChanged.connect(self._on_text_change)

        row_layout.addWidget(name_edit, 1)
        row_layout.addWidget(value_edit, 2)
        row_layout.addWidget(remove_btn, 0)

        if self.custom_fields_placeholder is not None:
            self.custom_fields_placeholder.hide()
        self.custom_fields_layout.addWidget(row)
        self._custom_field_rows.append((row, name_edit, value_edit))
        if mark_dirty:
            self._mark_dirty()

    def _remove_custom_field_row(self, row_widget: QWidget) -> None:
        kept_rows = []
        for row, name_edit, value_edit in self._custom_field_rows:
            if row is row_widget:
                row.deleteLater()
            else:
                kept_rows.append((row, name_edit, value_edit))
        self._custom_field_rows = kept_rows
        if not self._custom_field_rows and self.custom_fields_placeholder is not None:
            self.custom_fields_placeholder.show()
        self._mark_dirty()

    def _clear_custom_field_rows(self) -> None:
        for row, _, _ in self._custom_field_rows:
            row.deleteLater()
        self._custom_field_rows = []
        if self.custom_fields_placeholder is not None:
            self.custom_fields_placeholder.show()

    def _collect_custom_fields(self) -> list[tuple[str, str]]:
        fields: list[tuple[str, str]] = []
        for _row, name_edit, value_edit in self._custom_field_rows:
            name = name_edit.text().strip()
            value = value_edit.text().strip()
            if not name and not value:
                continue
            fields.append((name, value))
        return fields

    @staticmethod
    def _link_empty_text(label: str) -> tuple[str, str]:
        singular_map = {
            "Задачи": "задач",
            "Проекты": "проектов",
            "Заметки": "заметок",
            "Объекты": "объектов",
            "Файлы": "файлов",
            "Карты": "карт",
            "Метки": "меток",
        }
        hint_map = {
            "Задачи": "Свяжите задачу, чтобы быстро переходить к нужной работе.",
            "Проекты": "Свяжите проект, чтобы видеть, к чему относится маркер.",
            "Заметки": "Свяжите заметку, чтобы держать контекст рядом с картой.",
            "Объекты": "Свяжите объект, чтобы сохранить связь с базой сущностей.",
            "Файлы": "Добавьте файл, если к маркеру нужен референс или вложение.",
            "Карты": "Свяжите другую карту для быстрых переходов по локациям.",
            "Метки": "Свяжите другие метки, чтобы зафиксировать отношения на карте.",
        }
        normalized = singular_map.get(label, label.lower())
        return (f"Нет связанных {normalized}", hint_map.get(label, "Нет связанных элементов"))

    @staticmethod
    def _link_search_placeholder(label: str) -> str:
        placeholder_map = {
            "Задачи": "Найти или выбрать задачу",
            "Проекты": "Найти или выбрать проект",
            "Заметки": "Найти или выбрать заметку",
            "Объекты": "Найти или выбрать объект",
            "Файлы": "Выбрать файл",
            "Карты": "Найти или выбрать карту",
            "Метки": "Найти или выбрать метку",
        }
        return placeholder_map.get(label, "Найти или выбрать элемент")

    def _apply_styles(self) -> None:
        # Устанавливаем стили для диалога.
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
            QFrame#MapLabelBody {{
                background: transparent;
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
            QLabel#MapLabelError {{
                color: #e07a7a;
                font-size: 11px;
            }}
            QLabel#MapLabelHint {{
                color: #8e919a;
                font-size: 11px;
            }}
            QLabel#MapLabelEmptyTitle {{
                color: #e5e7ec;
                font-weight: 600;
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
            QLabel#MapLabelMarkerPreview {{
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}
            QFrame#MapLabelDivider {{
                color: #2a2b2f;
            }}
            QLabel#ImageDrop {{
                border: 1px dashed #3a3b40;
                border-radius: 8px;
                color: #8e919a;
                background: #1b1d24;
            }}
            QFrame#MapLabelInnerPanel {{
                background: rgba(25, 27, 35, 0.88);
                border: 1px solid #2a2b2f;
                border-radius: 8px;
            }}
            QFrame#MapLabelEmptyState {{
                background: rgba(25, 27, 35, 0.88);
                border: 1px solid #2f3340;
                border-radius: 8px;
            }}
            QWidget#MapLabelCustomRow QLineEdit {{
                min-height: 24px;
            }}
            QLineEdit[invalid="true"] {{
                border: 1px solid #e07a7a;
                background: rgba(82, 33, 33, 0.35);
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
            QWidget#EntityLinksInput {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }}
            QScrollArea#MapLabelFormScroll {{
                background: transparent;
                border: none;
            }}
            QScrollArea#MapLabelFormScroll > QWidget {{
                background: transparent;
            }}
            QScrollArea#MapLabelFormScroll QWidget#qt_scrollarea_viewport {{
                background: transparent;
            }}
            QScrollArea#MapLabelFormScroll > QWidget > QWidget {{
                background: transparent;
            }}
            QWidget#MapLabelFormContainer {{
                background: transparent;
            }}
            QWidget#EntityChipFlow {{
                background: transparent;
            }}
            QWidget#EntityChip {{
                background: #2a2f36;
                border: 1px solid #3a3f46;
                border-radius: 12px;
            }}
            QLabel#EntityChipLabel {{
                color: #d7d7d7;
            }}
            QToolButton#EntityChipRemove {{
                background: transparent;
                border: none;
                color: #b0b0b0;
                padding: 0px;
            }}
            QToolButton#EntityChipRemove:hover {{
                color: #f1c24d;
            }}
            QLineEdit#EntityLinksSearch {{
                background: transparent;
                border: none;
                padding: 4px 2px;
                color: #e6e6e6;
                min-width: 160px;
            }}
            QToolButton#EntityLinksClear {{
                background: transparent;
                border: none;
                padding: 2px;
            }}
            QToolButton#EntityLinksAdd {{
                background: transparent;
                border: none;
                padding: 2px;
            }}
            QTabWidget#MapLabelLinksTabs::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: rgba(31, 33, 40, 0.95);
                color: #c9ced7;
                border: 1px solid #2f333d;
                padding: 8px 14px;
                min-width: 110px;
            }}
            QTabBar::tab:selected {{
                background: #3b4a7a;
                color: #f2f4ff;
                border-color: #4b5c90;
            }}
            QAbstractItemView#CompleterPopup {{
                background: #1f2026;
                color: #e6e6e6;
                border: 1px solid #2d3036;
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}
            QAbstractItemView#CompleterPopup::item {{
                padding: 6px 10px;
                border-radius: 6px;
            }}
            QAbstractItemView#CompleterPopup::item:hover {{
                background: #2b2f36;
            }}
            QAbstractItemView#CompleterPopup::item:selected {{
                background: #3a4356;
                color: #f2f4ff;
            }}
            """
        )

    def _register_completer_popup(self, line_edit: QLineEdit | None, completer: QCompleter) -> None:
        # Регистрируем синхронизацию popup подсказок.
        if not line_edit:
            return
        self._popup_syncs.append(CompleterPopupSync(line_edit, completer))

    def _fit_to_screen(self) -> None:
        # Подгоняем окно под размеры экрана.
        screen = self.screen() or QGuiApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        margin = 0 if self.windowState() & Qt.WindowState.WindowMaximized else 24
        max_width = max(available.width() - margin, 320)
        max_height = max(available.height() - margin, 240)
        self.setMaximumSize(max_width, max_height)
        if self.minimumWidth() > max_width or self.minimumHeight() > max_height:
            self.setMinimumSize(
                min(self.minimumWidth(), max_width),
                min(self.minimumHeight(), max_height),
            )
        if self.width() > max_width or self.height() > max_height:
            self.resize(min(self.width(), max_width), min(self.height(), max_height))
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        if frame.left() < available.left():
            frame.moveLeft(available.left())
        if frame.top() < available.top():
            frame.moveTop(available.top())
        if frame.right() > available.right():
            frame.moveRight(available.right())
        if frame.bottom() > available.bottom():
            frame.moveBottom(available.bottom())
        self.move(frame.topLeft())

    def _sync_from_marker(self) -> None:
        # Заполняем форму данными текущей метки.
        self.name_edit.setText(self._marker.name)
        if self._marker.type:
            idx = self.type_combo.findText(self._marker.type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            else:
                self.type_combo.setCurrentText(self._marker.type)
        self.size_spin.setValue(float(self._marker.size))
        marker_type = marker_type_for_color(self._marker.color)
        type_index = self.marker_type_combo.findData(marker_type.key)
        if type_index >= 0:
            self.marker_type_combo.setCurrentIndex(type_index)
        self._set_marker_type(marker_type)
        self.desc_edit.setPlainText(self._marker.description or "")
        important, custom_fields = _parse_marker_properties_blob(self._marker.properties or "")
        self.important_edit.setPlainText(important)
        self._clear_custom_field_rows()
        for name, value in custom_fields:
            self._add_custom_field_row(name, value)
        self._set_parent_path(self._marker.parent_path)

        self._set_links("task", self._marker.task_ids)
        self._set_links("project", self._marker.project_ids)
        self._set_links("note", self._marker.note_ids)
        self._set_links("object", self._marker.object_ids)
        self._set_links("file", self._marker.file_ids)
        self._set_links("map", self._marker.map_ids)
        self._set_links("marker", self._marker.marker_ids)

        self._update_counters()
        self._load_image_preview(self._marker.image_path)
        for key in self._link_inputs:
            self._update_link_state(key)
        self._set_name_error(None)
        self._set_dirty(False)
        self._refresh_header_title()

    def _set_links(self, key: str, selected_ids: list[int]) -> None:
        # Заполняем связи для указанной сущности.
        source = self._entity_sources.get(key)
        link_input = self._link_inputs.get(key)
        if not source or not link_input:
            return
        lookup = {item.id: source.label_fn(item) for item in source.items}
        items = [
            EntityLinkItem(item_id, lookup.get(item_id, f"#{item_id}"), f"{source.item_prefix}:{item_id}")
            for item_id in selected_ids
        ]
        link_input.set_items(items)

    def _on_links_changed(self, key: str) -> None:
        self._update_link_state(key)
        self._mark_dirty()

    def _update_link_state(self, key: str) -> None:
        widgets = self._link_state_widgets.get(key)
        if not widgets:
            return
        empty_state, link_input = widgets
        has_items = bool(link_input.items())
        empty_state.setVisible(not has_items)

    def _wire_dirty_tracking(self) -> None:
        # Подключаем обработчики изменения полей.
        self.name_edit.textChanged.connect(self._on_name_changed)
        self.type_combo.currentTextChanged.connect(self._mark_dirty)
        self.size_spin.valueChanged.connect(self._mark_dirty)
        self.parent_path_edit.textChanged.connect(self._mark_dirty)
        self.desc_edit.textChanged.connect(self._on_text_change)
        self.important_edit.textChanged.connect(self._on_text_change)

    def _on_text_change(self) -> None:
        # При изменении текста обновляем счетчики.
        self._mark_dirty()
        self._update_counters()

    def _update_counters(self) -> None:
        # Обновляем счетчики символов.
        self.desc_counter.setText(f"{len(self.desc_edit.toPlainText())} символов")
        self.important_counter.setText(f"{len(self.important_edit.toPlainText())} символов")

    def _on_name_changed(self, text: str) -> None:
        self._refresh_header_title()
        if text.strip():
            self._set_name_error(None)
        self._mark_dirty()

    def _refresh_header_title(self) -> None:
        marker_name = self.name_edit.text().strip() if hasattr(self, "name_edit") else ""
        marker_name = marker_name or "Без названия"
        base = "Метка на карте" if self._dialog_mode == "edit" else "Новая метка"
        suffix = " *" if self._dirty else ""
        title = f"{base} • {marker_name}{suffix}"
        if hasattr(self, "header_title"):
            self.header_title.setText(title)
        self.setWindowTitle(title)

    def _set_name_error(self, message: str | None) -> None:
        invalid = bool(message)
        self.name_edit.setProperty("invalid", invalid)
        self.name_edit.style().unpolish(self.name_edit)
        self.name_edit.style().polish(self.name_edit)
        self.name_error_label.setVisible(invalid)
        self.name_error_label.setText(message or self._name_error_text)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.dirty_indicator.setVisible(dirty)
        self._refresh_header_title()

    def _mark_dirty(self) -> None:
        # Фиксируем наличие несохраненных изменений.
        if self._loading:
            return
        if not self._dirty:
            self._set_dirty(True)

    def _on_save(self) -> None:
        # Валидируем данные и сохраняем новый объект метки.
        name = self.name_edit.text().strip()
        if not name:
            self._set_name_error(self._name_error_text)
            self.name_edit.setFocus(Qt.FocusReason.OtherFocusReason)
            self.name_edit.selectAll()
            return
        self._set_name_error(None)
        marker = self._marker

        def chip_ids(key: str) -> list[int]:
            # Собираем id привязанных чипов.
            link_input = self._link_inputs.get(key)
            return [item.id for item in link_input.items()] if link_input else []

        self._marker = marker.__class__(
            marker.id,
            name,
            marker.x,
            marker.y,
            self._selected_color,
            self.type_combo.currentText().strip(),
            float(self.size_spin.value()),
            self.desc_edit.toPlainText().strip(),
            _serialize_marker_properties_blob(
                self.important_edit.toPlainText().strip(),
                self._collect_custom_fields(),
            ),
            chip_ids("task"),
            chip_ids("project"),
            chip_ids("note"),
            chip_ids("object"),
            chip_ids("file"),
            chip_ids("map"),
            chip_ids("marker"),
            self._parent_path,
            self._image_path,
        )
        self._set_dirty(False)
        self.accept()

    def _on_marker_type_changed(self, _index: int) -> None:
        # Обновляем тип маркера по выбору пользователя.
        key = self.marker_type_combo.currentData()
        self._set_marker_type(marker_type_by_key(key), mark_dirty=True)

    def _set_marker_type(self, option, mark_dirty: bool = False) -> None:
        # Применяем выбранный тип маркера к превью и цвету.
        self._selected_color = option.color
        pixmap = marker_type_pixmap(option, self.marker_type_preview.size())
        if pixmap is not None:
            self.marker_type_preview.setPixmap(pixmap)
            self.marker_type_preview.setText("")
        else:
            self.marker_type_preview.setPixmap(QPixmap())
            self.marker_type_preview.setText(option.label)
        self.marker_type_preview.setToolTip(option.label)
        if hasattr(self, "marker_type_summary"):
            self.marker_type_summary.setText(f"Иконка и цвет на карте определяются типом: {option.label}.")
        if mark_dirty:
            self._mark_dirty()

    def reject(self) -> None:
        # Подтверждение выхода при несохраненных изменениях.
        if self._dirty:
            confirm = QMessageBox.question(
                self,
                "Несохранённые изменения",
                "Есть несохранённые изменения. Закрыть?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        super().reject()

    def _request_resize(self) -> None:
        # Запрашиваем режим изменения размера и сохраняем.
        self._resize_requested = True
        self._on_save()

    def _load_image_preview(self, image_path: str) -> None:
        # Загружаем превью изображения по пути.
        self._image_path = (image_path or "").strip()
        self._image_icon = None
        pixmap = self._pixmap_from_image_path(self._image_path)
        if pixmap is not None:
            scaled = pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview.set_image(scaled)
        else:
            self.preview.set_image(None)
        self._update_image_hint()

    def _pixmap_from_image_path(self, image_path: str) -> QPixmap | None:
        # Получаем QPixmap из локального пути или облачного хранилища.
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
        # Очищаем изображение и обновляем состояние.
        self._image_path = ""
        self._image_icon = None
        self.preview.set_image(None)
        self._update_image_hint()
        self._mark_dirty()

    def _set_image(self, file_path: str) -> None:
        # Загружаем выбранное изображение по локальному пути.
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Изображение", "Не удалось загрузить изображение.")
            return
        scaled = pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self.preview.set_image(scaled)
        self._image_path = file_path
        self._image_icon = None
        self._update_image_hint()
        self._mark_dirty()

    def _on_image_drop(self, file_path: str) -> None:
        # Обработчик drag-n-drop изображений.
        self._set_image(file_path)

    def _update_image_hint(self) -> None:
        # Обновляем подпись под превью.
        if self._image_path:
            path = Path(self._image_path)
            self.image_hint.setText(path.name)
            self.image_hint.setToolTip(str(path))
        else:
            self.image_hint.setText("Нет изображения")
            self.image_hint.setToolTip("")

    def _choose_image(self) -> None:
        # Открываем навигатор выбора файла из облака.
        dialog = AttachFileSelectNav(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rel_path = dialog.selected_rel_path()
        if not rel_path:
            return
        self._set_cloud_image(rel_path, dialog.selected_icon())

    def _set_cloud_image(self, rel_path: str, icon: Optional[QIcon]) -> None:
        # Загружаем изображение из облачного хранилища или используем иконку.
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
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
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
        # Выбираем родительский каталог для метки.
        path = QFileDialog.getExistingDirectory(self, "Выберите каталог")
        if path:
            self._set_parent_path(path)
            self._mark_dirty()

    def _clear_parent_path(self) -> None:
        if not self._parent_path:
            return
        self._set_parent_path("")
        self._mark_dirty()

    def _set_parent_path(self, path: str) -> None:
        # Обновляем отображение пути родительского каталога.
        cleaned = (path or "").strip()
        self._parent_path = cleaned
        if hasattr(self, "parent_clear_btn"):
            self.parent_clear_btn.setEnabled(bool(cleaned))
        if cleaned:
            display = self._elide_path(cleaned)
            self.parent_path_edit.setText(display)
            self.parent_path_edit.setToolTip(cleaned)
        else:
            self.parent_path_edit.setText("")
            self.parent_path_edit.setToolTip("Каталог не выбран")

    def _elide_path(self, path: str) -> str:
        # Обрезаем длинный путь с помощью эллипсиса.
        metrics = QFontMetrics(self.parent_path_edit.font())
        width = max(120, self.parent_path_edit.width() - 40)
        return metrics.elidedText(path, Qt.TextElideMode.ElideMiddle, width)

    def _clear_links(self, key: str) -> None:
        # Очищаем привязки для конкретной сущности.
        link_input = self._link_inputs.get(key)
        if not link_input:
            return
        link_input.clear_items()
        link_input.clear_search()
        self._mark_dirty()

    def _add_link_from_title(self, key: str, title: str) -> None:
        # Добавляем привязку по выбранному названию.
        source = self._entity_sources.get(key)
        link_input = self._link_inputs.get(key)
        if not source or not link_input:
            return
        item_id = self._link_title_maps.get(key, {}).get(title)
        if item_id is None:
            return
        link_input.add_items([EntityLinkItem(item_id, title, f"{source.item_prefix}:{item_id}")])
        link_input.clear_search()
        self._mark_dirty()

    def _open_link(self, link: str) -> None:
        # Переходим к просмотру привязанной сущности.
        if ":" not in link:
            return
        kind, item_id = link.split(":", 1)
        try:
            parsed_id = int(item_id)
        except ValueError:
            return
        parent = self.parent()
        if parent is None:
            return
        open_attachment_view = getattr(parent, "open_attachment_view", None) or getattr(parent, "_open_attachment_view", None)
        if callable(open_attachment_view):
            open_attachment_view(kind, parsed_id)

    def _open_picker(self, key: str, query: str = "") -> None:
        # Открываем общий диалог выбора сущностей.
        source = self._entity_sources.get(key)
        link_input = self._link_inputs.get(key)
        if not source or not link_input:
            return
        if key == "file":
            self._open_file_picker(source, link_input)
            return

        def fetch_fn(search_query: str) -> list[ChipItem]:
            # Функция выборки для диалога по запросу.
            items = []
            normalized = search_query.strip().lower()
            for item in source.items:
                title = source.label_fn(item)
                if normalized and normalized not in title.lower():
                    continue
                items.append(ChipItem(item.id, title))
            return items

        dialog = EntityPickerDialog(
            source.label,
            fetch_fn,
            [item.id for item in link_input.items()],
            self,
            initial_query=query,
            anchor_widget=link_input,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_add = [
                EntityLinkItem(item.id, item.title, f"{source.item_prefix}:{item.id}")
                for item in dialog.selected_items()
            ]
            link_input.add_items(to_add)
            link_input.clear_search()
            self._mark_dirty()

    def _open_file_picker(self, source: MapLabelEntitySource, link_input: EntityLinksInput) -> None:
        # Открываем файл-пикер и добавляем выбранный файл.
        dialog = AttachFileSelectNav(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rel_path = dialog.selected_rel_path()
        if not rel_path:
            return
        normalized = rel_path.strip().strip("/")
        matched = next(
            (item for item in source.items if (item.rel_path or "").strip().strip("/") == normalized),
            None,
        )
        if not matched:
            QMessageBox.warning(self, "Файлы", "Файл не найден в базе.")
            return
        link_input.add_items(
            [EntityLinkItem(matched.id, source.label_fn(matched), f"{source.item_prefix}:{matched.id}")]
        )
        link_input.clear_search()
        self._mark_dirty()

