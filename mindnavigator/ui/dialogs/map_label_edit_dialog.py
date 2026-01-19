"""Диалог редактирования метки на карте и связанных сущностей.

Входные данные:
    Данные метки, изображения и связанные сущности.

Выходные данные:
    Обновлённые атрибуты метки и ссылки на сущности.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QGuiApplication, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QAbstractItemView,
    QDialog,
    QColorDialog,
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mindnavigator.storage import get_database
from mindnavigator.ui.dialogs.attach_file_select_nav import AttachFileSelectNav
from mindnavigator.ui.dialogs.entity_picker_dialog import ChipItem, EntityPickerDialog
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND

import qtawesome as qta


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

    def expandingDirections(self) -> Qt.Orientations:
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
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # Кнопка удаления чипа.
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
        self.flow_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Кнопка добавления новых чипов.
        self.add_button = QToolButton()
        self.add_button.setObjectName("ChipAddButton")
        self.add_button.setText("+")
        self.add_button.setCursor(Qt.PointingHandCursor)
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
        self.label.setTextFormat(Qt.RichText)
        self.label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.label.setOpenExternalLinks(False)
        self.label.setText(f"<a href='{item.link}'>{item.title}</a>")
        self.label.linkActivated.connect(self.linkActivated.emit)

        # Кнопка удаления привязки.
        remove_btn = QToolButton()
        remove_btn.setObjectName("EntityChipRemove")
        remove_btn.setText("✕")
        remove_btn.setCursor(Qt.PointingHandCursor)
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
        self.flow_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("EntityLinksSearch")
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.setClearButtonEnabled(False)
        self.search_input.textChanged.connect(self.searchChanged.emit)

        # Кнопка очистки.
        self.clear_button = QToolButton()
        self.clear_button.setObjectName("EntityLinksClear")
        self.clear_button.setIcon(qta.icon("fa5s.times", color="#cfcfcf"))
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setAutoRaise(True)
        self.clear_button.clicked.connect(self._on_clear_requested)

        layout.addWidget(self.icon_label, 0, Qt.AlignVCenter)
        layout.addWidget(self.flow_container, 1)
        layout.addWidget(self.clear_button, 0, Qt.AlignVCenter)

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
            QEvent.Resize,
            QEvent.Move,
            QEvent.Show,
            QEvent.FontChange,
            QEvent.StyleChange,
            QEvent.ScreenChangeInternal,
        }:
            self._sync_popup()
        return super().eventFilter(watched, event)

    def _configure_popup(self) -> None:
        # Базовая настройка popup подсказок.
        if not self._popup:
            return
        self._popup.setObjectName("CompleterPopup")
        self._popup.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._popup.setTextElideMode(Qt.ElideRight)
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
        self.setAlignment(Qt.AlignCenter)
        self._has_image = False
        self._placeholder = "Перетащите изображение\\nили выберите файл"
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
        self._db = get_database()
        self._marker = marker
        self._entity_sources = entity_sources
        self._dirty = False
        self._resize_requested = False
        self._image_path = ""
        self._image_icon: QIcon | None = None
        self._parent_path = ""
        self._size_range = size_range
        self._link_inputs: dict[str, EntityLinksInput] = {}
        self._link_title_maps: dict[str, dict[str, int]] = {}
        self._popup_syncs: list[CompleterPopupSync] = []
        self._loading = True

        # Настройки окна.
        self.setWindowTitle("Метка на карте")
        self.resize(1100, 760)
        self.setMinimumSize(840, 520)

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
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_save)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_save)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.reject)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        # При показе разворачиваем и вписываем диалог в экран.
        super().showEvent(event)
        if not self.isMaximized():
            self.showMaximized()
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
        # Основной контейнер с левой и правой панелями.
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
        # Левая панель с превью изображения и выбором цвета.
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
        # Правая панель с секциями формы.
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
        # Секция основных параметров метки.
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
            # Настраиваем автодополнение по типу.
            completer = QCompleter(sorted({t for t in type_suggestions if t}), self)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.type_combo.setCompleter(completer)
            self._register_completer_popup(self.type_combo.lineEdit(), completer)

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
        # Секция привязанных сущностей.
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
            # Создаем поле привязки для каждой сущности.
            link_input = EntityLinksInput(source.placeholder, source.icon_name)
            link_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            link_input.itemsChanged.connect(lambda _items, k=key: self._mark_dirty())
            link_input.clearRequested.connect(lambda k=key: self._clear_links(k))
            link_input.linkActivated.connect(self._open_link)
            link_input.search_input.returnPressed.connect(
                lambda k=key, field=link_input: self._open_picker(k, field.search_input.text())
            )

            if key == "file":
                # Для файлов открываем отдельный пикер.
                link_input.search_input.setReadOnly(True)
                link_input.search_input.setPlaceholderText("Выбрать файл…")
                link_input.search_input.setCursor(Qt.PointingHandCursor)

                def _open_file_dialog(event, k=key, field=link_input.search_input):
                    # Обработчик клика для открытия файла.
                    if event.button() == Qt.LeftButton:
                        self._open_picker(k)
                    QLineEdit.mousePressEvent(field, event)

                link_input.search_input.mousePressEvent = _open_file_dialog
            else:
                # Для остальных сущностей используем автодополнение.
                labels = {source.label_fn(item): item.id for item in source.items}
                self._link_title_maps[key] = labels
                completer = QCompleter(list(labels.keys()), link_input.search_input)
                completer.setCaseSensitivity(Qt.CaseInsensitive)
                completer.setFilterMode(Qt.MatchContains)
                completer.activated[str].connect(lambda text, k=key: self._add_link_from_title(k, text))
                link_input.search_input.setCompleter(completer)
                self._register_completer_popup(link_input.search_input, completer)

            self._link_inputs[key] = link_input
            chips_label = QLabel(source.label)
            chips_label.setObjectName("MapLabelFormLabel")
            form.addRow(chips_label, link_input)

        layout.addLayout(form)
        return section

    def _build_section_text(self) -> QWidget:
        # Секция описания и важных заметок.
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
            QWidget#EntityLinksInput {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 10px;
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
            QAbstractItemView#CompleterPopup QScrollBar:vertical {{
                width: 8px;
                margin: 4px 2px;
                background: transparent;
            }}
            QAbstractItemView#CompleterPopup QScrollBar::handle:vertical {{
                background: #3a3d44;
                border-radius: 4px;
                min-height: 24px;
            }}
            QAbstractItemView#CompleterPopup QScrollBar::handle:vertical:hover {{
                background: #4a4d56;
            }}
            QAbstractItemView#CompleterPopup QScrollBar::add-line:vertical,
            QAbstractItemView#CompleterPopup QScrollBar::sub-line:vertical {{
                height: 0px;
                width: 0px;
                background: transparent;
            }}
            QAbstractItemView#CompleterPopup QScrollBar::add-page:vertical,
            QAbstractItemView#CompleterPopup QScrollBar::sub-page:vertical {{
                background: transparent;
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
        margin = 0 if self.windowState() & Qt.WindowMaximized else 24
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
        self._set_color(self._marker.color)
        self.desc_edit.setPlainText(self._marker.description or "")
        self.important_edit.setPlainText(self._marker.properties or "")

        self._set_links("task", self._marker.task_ids)
        self._set_links("project", self._marker.project_ids)
        self._set_links("note", self._marker.note_ids)
        self._set_links("object", self._marker.object_ids)
        self._set_links("file", self._marker.file_ids)
        self._set_links("map", self._marker.map_ids)
        self._set_links("marker", self._marker.marker_ids)

        self._update_counters()
        self._load_image_preview(self._marker.image_path)

    def _set_links(self, key: str, selected_ids: list[int]) -> None:
        # Заполняем привязки для указанной сущности.
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

    def _wire_dirty_tracking(self) -> None:
        # Подключаем обработчики изменения полей.
        self.name_edit.textChanged.connect(self._mark_dirty)
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

    def _mark_dirty(self) -> None:
        # Фиксируем наличие несохраненных изменений.
        if self._loading:
            return
        if not self._dirty:
            self._dirty = True
            self.dirty_indicator.setVisible(True)

    def _on_save(self) -> None:
        # Валидируем данные и сохраняем новый объект метки.
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Проверка", "Название метки не может быть пустым.")
            return
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
            self.important_edit.toPlainText().strip(),
            chip_ids("task"),
            chip_ids("project"),
            chip_ids("note"),
            chip_ids("object"),
            chip_ids("file"),
            chip_ids("map"),
            chip_ids("marker"),
            self._image_path,
        )
        self._dirty = False
        self.accept()

    def reject(self) -> None:
        # Подтверждение выхода при несохраненных изменениях.
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
        # Запрашиваем режим изменения размера и сохраняем.
        self._resize_requested = True
        self._on_save()

    def _pick_color(self) -> None:
        # Открываем диалог выбора цвета.
        color = QColorDialog.getColor(self._selected_color, self, "Цвет метки")
        if color.isValid():
            self._set_color(color)
            self._mark_dirty()

    def _set_color(self, color: QColor) -> None:
        # Применяем выбранный цвет к превью.
        self._selected_color = color
        self.color_preview.setStyleSheet(
            f"background: {color.name()}; border: 1px solid #2a2b2f; border-radius: 6px;"
        )

    def _load_image_preview(self, image_path: str) -> None:
        # Загружаем превью изображения по пути.
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
        scaled = pixmap.scaled(self.preview.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
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
        if dialog.exec() != QDialog.Accepted:
            return
        rel_path = dialog.selected_rel_path()
        if not rel_path:
            return
        self._set_cloud_image(rel_path, dialog.selected_icon())

    def _set_cloud_image(self, rel_path: str, icon: QIcon | None) -> None:
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
        # Выбираем родительский каталог для метки.
        path = QFileDialog.getExistingDirectory(self, "Выберите каталог")
        if path:
            self._parent_path = path
            display = self._elide_path(path)
            self.parent_path_edit.setText(display)
            self.parent_path_edit.setToolTip(path)
            self._mark_dirty()

    def _elide_path(self, path: str) -> str:
        # Обрезаем длинный путь с помощью эллипсиса.
        metrics = QFontMetrics(self.parent_path_edit.font())
        width = max(120, self.parent_path_edit.width() - 40)
        return metrics.elidedText(path, Qt.ElideMiddle, width)

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
        if parent and hasattr(parent, "_open_attachment_view"):
            parent._open_attachment_view(kind, parsed_id)

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
        if dialog.exec() == QDialog.Accepted:
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
        if dialog.exec() != QDialog.Accepted:
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
