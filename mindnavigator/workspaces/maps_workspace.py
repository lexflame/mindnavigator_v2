"""Рабочая область управления картами и метками.

Входные данные:
    Данные карт, изображения, координаты меток и пользовательские события.

Выходные данные:
    Обновлённые карты, метки и визуальные представления.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional

import qtawesome as qta
from PySide6.QtCore import (
    Qt, QSize, QRect, QAbstractListModel, QModelIndex, QPoint, QPointF, QRectF, Signal, QTimer, QEvent
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QFont,
    QFontMetrics,
    QFontMetricsF,
    QPixmap,
    QPen,
    QCursor,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QLineEdit, QListView, QStyledItemDelegate, QSpinBox, QStyle,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QStackedWidget, QMenu,
    QFileDialog, QDoubleSpinBox, QPlainTextEdit, QProgressBar,
    QListWidget, QListWidgetItem, QAbstractItemView, QSizePolicy, QSpacerItem,
    QPushButton, QScrollArea
)
from shiboken6 import isValid

from mindnavigator.storage import CloudFileData, get_database
from mindnavigator.marker_types import (
    default_marker_type,
    marker_type_for_color,
    marker_type_icon,
    marker_type_options,
    marker_type_pixmap,
)
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
from mindnavigator.ui.dialogs.map_label_edit_dialog import MapLabelEditDialog, MapLabelEntitySource
from mindnavigator.resources import resource_path


@dataclass(frozen=True)
class MapRow:
    id: int
    title: str
    description: str
    project: str
    tiles_path: str
    tiles_h: int
    tiles_w: int


class MapRoles:
    Id = Qt.UserRole + 1
    Title = Qt.UserRole + 2
    Description = Qt.UserRole + 3
    Project = Qt.UserRole + 4
    TilesPath = Qt.UserRole + 5
    TilesHeight = Qt.UserRole + 6
    TilesWidth = Qt.UserRole + 7


class MapsModel(QAbstractListModel):
    def __init__(self, parent=None):
        # Инициализируем модель списка карт.
        super().__init__(parent)
        # Основные структуры для хранения исходных и отфильтрованных данных.
        self._items: List[MapRow] = []
        self._all_items: List[MapRow] = []
        self._search = ""
        self._project_filter: Optional[str] = None
        self._db = get_database()
        # Загружаем данные при старте модели.
        self._load_maps()

    def _load_maps(self) -> None:
        # Забираем карты из базы и сохраняем в локальный список.
        maps = self._db.fetch_maps()
        self._all_items = [
            MapRow(
                item.id,
                item.title,
                item.description,
                item.project,
                item.tiles_path,
                item.tiles_h,
                item.tiles_w,
            )
            for item in maps
        ]
        # Пересобираем список с учетом фильтров.
        self._rebuild()

    def rowCount(self, parent=QModelIndex()) -> int:
        # Для дочерних индексов список не поддерживается.
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int):
        # Возвращаем данные по ролям для списка.
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role == MapRoles.Title:
            return item.title
        if role == MapRoles.Description:
            return item.description
        if role == MapRoles.Id:
            return item.id
        if role == MapRoles.Project:
            return item.project
        if role == MapRoles.TilesPath:
            return item.tiles_path
        if role == MapRoles.TilesHeight:
            return item.tiles_h
        if role == MapRoles.TilesWidth:
            return item.tiles_w
        if role == Qt.DisplayRole:
            return item.title
        return None

    def add_map(
        self,
        title: str,
        description: str,
        project: str,
        tiles_path: str,
        tiles_h: int,
        tiles_w: int,
    ) -> None:
        # Нормализуем ввод и проверяем обязательные поля.
        title = (title or "").strip()
        if not title:
            return
        try:
            # Создаем карту в базе.
            created = self._db.create_map(title, description, project, tiles_path, tiles_h, tiles_w)
        except ValueError:
            return
        # Добавляем новую карту в локальный список и пересобираем фильтры.
        self._all_items.append(
            MapRow(
                created.id,
                created.title,
                created.description,
                created.project,
                created.tiles_path,
                created.tiles_h,
                created.tiles_w,
            )
        )
        self._rebuild()

    def update_map(
        self,
        map_id: int,
        title: str,
        description: str,
        project: str,
        tiles_path: str,
        tiles_h: int,
        tiles_w: int,
    ) -> None:
        # Нормализуем название и валидируем ввод.
        title = (title or "").strip()
        if not title:
            return
        try:
            # Обновляем запись в базе.
            updated_map = self._db.update_map(map_id, title, description, project, tiles_path, tiles_h, tiles_w)
        except ValueError:
            return
        # Пересоздаем список с обновленным элементом.
        updated = []
        for item in self._all_items:
            if item.id == map_id:
                updated.append(
                    MapRow(
                        updated_map.id,
                        updated_map.title,
                        updated_map.description,
                        updated_map.project,
                        updated_map.tiles_path,
                        updated_map.tiles_h,
                        updated_map.tiles_w,
                    )
                )
            else:
                updated.append(item)
        self._all_items = updated
        # Перестраиваем отображаемый список.
        self._rebuild()

    def set_search(self, text: str) -> None:
        # Обновляем строку поиска и фильтруем список.
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_project_filter(self, project: Optional[str]) -> None:
        # Сохраняем фильтр по проекту и обновляем отображение.
        self._project_filter = project
        self._rebuild()

    def _rebuild(self) -> None:
        # Применяем текущие фильтры поиска и проекта.
        search = self._search
        project = self._project_filter
        items = []
        for item in self._all_items:
            if project and item.project != project:
                continue
            if search:
                hay = f"{item.title} {item.description} {item.project}".lower()
                if search not in hay:
                    continue
            items.append(item)

        # Обновляем модель через reset, чтобы корректно перерисовать список.
        self.beginResetModel()
        self._items = items
        self.endResetModel()


class MapsItemDelegate(QStyledItemDelegate):
    ROW_H = 112
    ROW_H_MIN = 124

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#e1e1e1")
    C_DIM = QColor("#9a9a9a")
    C_PILL = QColor("#1f2126")
    C_PILL_BORDER = QColor("#2d2f35")
    C_BTN = QColor("#23262c")
    C_BTN_BORDER = QColor("#343740")
    C_BTN_TEXT = QColor("#e0e0e0")

    def __init__(self, parent=None):
        # Инициализация делегата для отрисовки строк.
        super().__init__(parent)
        # Настраиваем шрифты для отдельных блоков строки.
        self._font_title = QFont()
        self._font_title.setPointSize(10)
        self._font_title.setBold(True)

        self._font_desc = QFont()
        self._font_desc.setPointSize(9)

        self._font_pill = QFont()
        self._font_pill.setPointSize(9)

        self._font_button = QFont()
        self._font_button.setPointSize(9)
        self._font_button.setBold(True)

        # Загружаем иконку карты.
        self._icon_map = qta.icon("fa5s.map-marked-alt", color="#cfcfcf")

    def sizeHint(self, option, index):
        # Высота строки зависит от длины описания.
        desc = index.data(MapRoles.Description) or ""
        layout = self._row_layout(option.rect)
        text_width = max(10, layout["text"].width())

        title_metrics = QFontMetrics(self._font_title)
        desc_metrics = QFontMetrics(self._font_desc)
        title_height = title_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextWordWrap, "X").height()
        desc_height = 0
        if desc:
            desc_height = desc_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextWordWrap, desc).height()

        total_height = title_height + desc_height + 96
        return QSize(option.rect.width(), max(self.ROW_H_MIN, total_height))

    def paint(self, painter: QPainter, option, index: QModelIndex):
        # Основная отрисовка карточки карты.
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        r = option.rect
        row_color = self.C_ROW_ALT if index.row() % 2 else self.C_ROW
        if option.state & QStyle.State_Selected:
            row_color = QColor("#34373e")

        painter.fillRect(r, self.C_BG)
        painter.fillRect(r.adjusted(6, 4, -6, -4), row_color)
        painter.setPen(self.C_BORDER)
        painter.drawRoundedRect(r.adjusted(6, 4, -6, -4), 6, 6)

        # Вычисляем layout и извлекаем данные.
        layout = self._row_layout(r)
        title = index.data(MapRoles.Title) or ""
        desc = index.data(MapRoles.Description) or ""
        project = index.data(MapRoles.Project) or ""
        tiles_h = index.data(MapRoles.TilesHeight) or 0
        tiles_w = index.data(MapRoles.TilesWidth) or 0

        icon_rect = layout["icon"]
        self._icon_map.paint(painter, icon_rect, Qt.AlignCenter)

        # Рисуем заголовок и описание.
        painter.setPen(self.C_TEXT)
        painter.setFont(self._font_title)
        painter.drawText(layout["title"], Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, title)

        if desc:
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_desc)
            painter.drawText(layout["desc"], Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, desc)

        # Дополнительные блоки и кнопки.
        self._draw_pill(painter, layout["project"], project)
        self._draw_pill(painter, layout["tiles"], f"Тайлы: {tiles_w}×{tiles_h}")
        self._draw_button(painter, layout["edit_btn"], "Редактировать свойства")
        self._draw_button(painter, layout["open_btn"], "Перейти к карте")

        painter.restore()

    def _row_layout(self, r: QRect) -> dict:
        # Рассчитываем положение и размеры всех блоков строки.
        left = r.left() + 14
        right = r.right() - 14
        top = r.top() + 10
        bottom = r.bottom() - 10
        icon_rect = QRect(left, top + 6, 18, 18)
        info_w = 210
        text_rect = QRect(left + 28, top, right - info_w - (left + 28), bottom - top)
        title_rect = QRect(text_rect.left(), text_rect.top(), text_rect.width(), 22)
        desc_rect = QRect(text_rect.left(), text_rect.top() + 24, text_rect.width(), text_rect.height() - 24)

        pill_x = right - info_w + 6
        pill_w = info_w - 12
        project_rect = QRect(pill_x, top, pill_w, 22)
        tiles_rect = QRect(pill_x, top + 28, pill_w, 22)
        edit_rect = QRect(pill_x, top + 56, pill_w, 22)
        open_rect = QRect(pill_x, top + 82, pill_w, 22)

        return {
            "icon": icon_rect,
            "text": text_rect,
            "title": title_rect,
            "desc": desc_rect,
            "project": project_rect,
            "tiles": tiles_rect,
            "edit_btn": edit_rect,
            "open_btn": open_rect,
        }

    def _draw_pill(self, painter: QPainter, rect: QRect, text: str) -> None:
        # Рисуем "плашку" с текстом.
        painter.save()
        painter.setPen(self.C_PILL_BORDER)
        painter.setBrush(self.C_PILL)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(self.C_TEXT)
        painter.setFont(self._font_pill)
        painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()

    def _draw_button(self, painter: QPainter, rect: QRect, text: str) -> None:
        # Рисуем псевдо-кнопку внутри делегата.
        painter.save()
        painter.setPen(self.C_BTN_BORDER)
        painter.setBrush(self.C_BTN)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(self.C_BTN_TEXT)
        painter.setFont(self._font_button)
        painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()


class MapsListView(QListView):
    editRequested = Signal(QModelIndex)
    openRequested = Signal(QModelIndex)

    def mousePressEvent(self, event):
        # Обрабатываем клики по кнопкам внутри делегата.
        index = self.indexAt(event.pos())
        if index.isValid():
            delegate = self.itemDelegate()
            if isinstance(delegate, MapsItemDelegate):
                rect = self.visualRect(index)
                layout = delegate._row_layout(rect)
                if layout["edit_btn"].contains(event.pos()):
                    self.editRequested.emit(index)
                    return
                if layout["open_btn"].contains(event.pos()):
                    self.openRequested.emit(index)
                    return
        # Передаем событие стандартной реализации.
        super().mousePressEvent(event)


class MapEditDialog(QDialog):
    def __init__(self, map_row: MapRow, parent=None):
        # Инициализируем диалог редактирования карты.
        super().__init__(parent)
        # Базовые настройки диалога.
        self.setWindowTitle("Редактирование карты")
        self.setObjectName("MapEditDialog")
        self.setMinimumWidth(460)
        self.setMinimumHeight(400)

        self._db = get_database()

        # Основная вертикальная компоновка.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Заголовок диалога.
        title_label = QLabel("Редактирование карты")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        # Форма с полями карты.
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit(map_row.title)
        self.title_edit.setPlaceholderText("Название карты")

        self.description_edit = QLineEdit(map_row.description)
        self.description_edit.setPlaceholderText("Описание карты")

        self.project_edit = QComboBox()
        self.project_edit.addItems(self._project_titles())
        idx = self.project_edit.findText(map_row.project)
        if idx >= 0:
            self.project_edit.setCurrentIndex(idx)

        self.tiles_path = QLineEdit(map_row.tiles_path)
        self.tiles_path.setPlaceholderText("Каталог хранения тайлов")

        self.tiles_path_btn = QToolButton()
        self.tiles_path_btn.setText("…")
        self.tiles_path_btn.setCursor(Qt.PointingHandCursor)
        self.tiles_path_btn.clicked.connect(self._on_pick_tiles_path)

        tiles_path_row = QFrame()
        tiles_path_row.setObjectName("MapTilesPathRow")
        tiles_path_layout = QHBoxLayout(tiles_path_row)
        tiles_path_layout.setContentsMargins(0, 0, 0, 0)
        tiles_path_layout.setSpacing(6)
        tiles_path_layout.addWidget(self.tiles_path, 1)
        tiles_path_layout.addWidget(self.tiles_path_btn)

        self.tiles_w = QSpinBox()
        self.tiles_w.setRange(1, 512)
        self.tiles_w.setValue(map_row.tiles_w)

        self.tiles_h = QSpinBox()
        self.tiles_h.setRange(1, 512)
        self.tiles_h.setValue(map_row.tiles_h)

        # Блок выбора размера тайлов.
        tiles_block = QFrame()
        tiles_block.setObjectName("MapTilesBlock")
        tiles_layout = QHBoxLayout(tiles_block)
        tiles_layout.setContentsMargins(8, 4, 8, 4)
        tiles_layout.setSpacing(8)
        tiles_layout.addWidget(QLabel("W"))
        tiles_layout.addWidget(self.tiles_w)
        tiles_layout.addWidget(QLabel("H"))
        tiles_layout.addWidget(self.tiles_h)

        form.addRow("Название", self.title_edit)
        form.addRow("Описание", self.description_edit)
        form.addRow("Проект", self.project_edit)
        form.addRow("Каталог хранения тайлов", tiles_path_row)
        form.addRow("Тайлы", tiles_block)

        layout.addLayout(form)

        # Кнопки сохранения/отмены.
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Стили диалога.
        self.setStyleSheet(f"""
            QDialog#MapEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#MapEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#MapEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#MapEditDialog QLineEdit,
            QDialog#MapEditDialog QComboBox,
            QDialog#MapEditDialog QSpinBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#MapEditDialog QFrame#MapTilesPathRow QToolButton {{
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e6e6e6;
            }}

            QDialog#MapEditDialog QFrame#MapTilesPathRow QToolButton:hover {{
                background: #34363b;
            }}

            QDialog#MapEditDialog QFrame#MapTilesBlock {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}

            QDialog#MapEditDialog QFrame#MapTilesBlock QSpinBox {{
                background: transparent;
                border: none;
                padding: 6px 6px;
            }}

            QDialog#MapEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#MapEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _project_titles(self) -> List[str]:
        # Список проектов для комбобокса.
        projects = get_database().fetch_projects()
        titles = sorted({p.title for p in projects})
        return titles or ["Без проекта"]

    def _cloud_storage_root(self) -> str:
        # Корневая папка облачного хранилища.
        return self._db.get_setting("cloud_storage_path", default="")

    def _on_pick_tiles_path(self) -> None:
        # Диалог выбора каталога с тайлами.
        current = self.tiles_path.text().strip()
        start_dir = current or self._cloud_storage_root() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выберите каталог хранения тайлов",
            start_dir,
        )
        if not selected:
            return
        self.tiles_path.setText(selected)

    def _on_accept(self):
        # Проверка обязательных полей перед сохранением.
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Проверка", "Введите название карты.")
            return
        self.accept()

    def values(self) -> dict:
        # Возвращаем значения формы в виде словаря.
        return {
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.text().strip(),
            "project": self.project_edit.currentText(),
            "tiles_path": self.tiles_path.text().strip(),
            "tiles_w": self.tiles_w.value(),
            "tiles_h": self.tiles_h.value(),
        }


class MapTool(Enum):
    SELECT = auto()
    ADD_MARKER = auto()
    ADD_REGION = auto()
    MEASURE = auto()


@dataclass(frozen=True)
class Marker:
    id: int
    name: str
    x: float
    y: float
    color: QColor
    type: str
    size: float
    description: str = ""
    properties: str = ""
    task_ids: List[int] = field(default_factory=list)
    project_ids: List[int] = field(default_factory=list)
    note_ids: List[int] = field(default_factory=list)
    object_ids: List[int] = field(default_factory=list)
    file_ids: List[int] = field(default_factory=list)
    map_ids: List[int] = field(default_factory=list)
    marker_ids: List[int] = field(default_factory=list)
    parent_path: str = ""
    image_path: str = ""


@dataclass(frozen=True)
class MapOverlay:
    id: int
    kind: str  # "region" | "path"
    points: List[QPointF]
    color: QColor
    title: str = ""


class MapImagePreviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        images: List[CloudFileData],
        start_index: int,
        cloud_root: Path,
    ) -> None:
        # Инициализация окна предпросмотра изображений.
        super().__init__(parent)
        # Данные изображений и кеш для быстрых переключений.
        self._images = images
        self._current_index = max(0, min(start_index, len(images) - 1))
        self._cloud_root = cloud_root
        self._pixmap_cache: Dict[str, QPixmap] = {}

        self.setObjectName("MapImagePreview")
        self.setWindowTitle("Просмотр изображения")

        # Компоновка диалога.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Виджет предпросмотра.
        self.image_label = QLabel()
        self.image_label.setObjectName("MapImagePreviewLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label, 1)

        # Стили диалога.
        self.setStyleSheet(
            """
            QDialog#MapImagePreview {
                background: #0f1115;
            }
            QLabel#MapImagePreviewLabel {
                color: #9aa0a6;
            }
            """
        )

        # Открываем в полноэкранном режиме и показываем стартовое изображение.
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)
        self._update_image()

    def keyPressEvent(self, event) -> None:
        # Навигация по изображением стрелками и выход по Esc.
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
        # При изменении размеров пересчитываем масштаб.
        super().resizeEvent(event)
        if hasattr(self, "image_label"):
            self._update_pixmap()

    def _show_previous(self) -> None:
        # Переход к предыдущему изображению.
        if not self._images:
            return
        self._current_index = max(0, self._current_index - 1)
        self._update_image()

    def _show_next(self) -> None:
        # Переход к следующему изображению.
        if not self._images:
            return
        self._current_index = min(len(self._images) - 1, self._current_index + 1)
        self._update_image()

    def _update_image(self) -> None:
        # Загружает текущий элемент и обновляет UI.
        if not self._images:
            self.setWindowTitle("Просмотр изображения")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображения отсутствуют")
            return

        # Подготовка текущего изображения.
        current = self._images[self._current_index]
        self.setWindowTitle(f"{current.name} ({self._current_index + 1}/{len(self._images)})")
        file_path = self._cloud_root / current.rel_path
        if not file_path.is_file():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображение недоступно")
            return

        # Используем кеш, чтобы ускорить переключения.
        cache_key = current.rel_path
        pixmap = self._pixmap_cache.get(cache_key)
        if pixmap is None:
            pixmap = QPixmap(str(file_path))
            self._pixmap_cache[cache_key] = pixmap
        self._update_pixmap(pixmap)

    def _update_pixmap(self, pixmap: Optional[QPixmap] = None) -> None:
        # Пересчитываем и применяем масштаб изображения.
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


class MapCanvas(QWidget):
    # Класс отрисовки маркеров на карте
    markerSelected = Signal(object)
    markerAdded = Signal(object)
    markerRemoved = Signal(int)
    markerUpdated = Signal(object)

    GRID_COLOR = QColor(70, 74, 82, 120)
    GRID_TEXT = QColor(150, 155, 160, 180)
    CREATE_DEFAULT_MARKER_SIZE = 60.0 # Изначальный размер маркера при создании
    DEFAULT_MARKER_SIZE = 8.0 
    MIN_MARKER_SIZE = 10.0
    MAX_MARKER_SIZE = 240.0
    RESIZE_FRAME_PADDING = 8.0
    HANDLE_PIXEL_SIZE = 12.0

    def __init__(self, parent=None):
        # Инициализация канвы карты.
        super().__init__(parent)
        # Настройки взаимодействия и базовых параметров карты.
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self._scale = 1.0
        self._absolute_min_scale = 0.1
        self._min_scale = 0.5
        self._max_scale = 6.0
        self._offset = QPointF(80, 60)
        self._panning = False
        self._last_pos = QPointF()
        self._grid_enabled = True
        self._tool = MapTool.SELECT
        self._background = QPixmap(resource_path("assets/splash.jpg"))
        self._tiles_path = ""
        self._tiles_w = 0
        self._tiles_h = 0
        self._tile_size = QSize(80, 80)
        self._map_pixmap = QPixmap()
        self._markers: List[Marker] = []
        self._next_id = 1
        self._selected: Optional[Marker] = None
        self._resize_marker_id: Optional[int] = None
        self._resize_handle_regions: Dict[str, QRectF] = {}
        self._active_resize_handle: Optional[str] = None
        self._resize_dragging = False
        self._resize_drag_offset = QPointF()
        self._resize_start_pos = QPointF()
        self._resize_start_rect = QRectF()
        self._resize_start_marker_size = 0.0
        self._preview_pos: Optional[QPointF] = None
        self._dragging_marker_id: Optional[int] = None
        self._tasks = []
        self._projects = []
        self._notes = []
        self._objects = []
        self._files = []
        self._maps = []
        self._marker_items = []
        self._tasks_by_id = {}
        self._projects_by_id = {}
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._files_by_id = {}
        self._maps_by_id = {}
        self._marker_items_by_id = {}
        self._marker_icon_cache: Dict[tuple[str, int], QPixmap] = {}
        self._overlays: List[MapOverlay] = []
        self._next_overlay_id = 1
        self._overlay_draft_points: List[QPointF] = []
        # Инициализируем стартовый набор маркеров.
        self._seed_markers()

    @staticmethod
    def default_markers() -> List[Marker]:
        # Базовые маркеры, используемые при первом открытии карты.
        marker_types = marker_type_options()
        blue = marker_types[0]
        green = marker_types[1]
        orange = marker_types[2]
        return [
            Marker(1, "Outpost", 320, 240, blue.color, "Base", MapCanvas.DEFAULT_MARKER_SIZE, "Опорный пункт"),
            Marker(2, "Echo", 520, 360, green.color, "Point", MapCanvas.DEFAULT_MARKER_SIZE, "Контрольная точка"),
            Marker(3, "Delta", 220, 420, orange.color, "Risk", MapCanvas.DEFAULT_MARKER_SIZE, "Зона риска"),
        ]

    def _seed_markers(self) -> None:
        # Заполняем список маркеров значениями по умолчанию.
        self._markers = self.default_markers()
        self._next_id = max((m.id for m in self._markers), default=0) + 1

    def set_markers(self, markers: List[Marker]) -> None:
        # Полностью заменяем список маркеров и сбрасываем выделение.
        self._markers = list(markers)
        self._selected = None
        self._resize_marker_id = None
        self._next_id = max((m.id for m in self._markers), default=0) + 1
        self.markerSelected.emit(None)
        self.update()

    def markers(self) -> List[Marker]:
        # Возвращаем копию списка маркеров.
        return list(self._markers)

    def set_overlays(self, overlays: List[MapOverlay]) -> None:
        # Полностью заменяем список геометрий карты.
        self._overlays = list(overlays)
        self._next_overlay_id = max((item.id for item in self._overlays), default=0) + 1
        self._overlay_draft_points = []
        self.update()

    def set_attachment_sources(self, tasks, projects, notes, objects, files, maps, markers) -> None:
        # Сохраняем источники данных и создаем словари быстрого доступа.
        self._tasks = list(tasks)
        self._projects = list(projects)
        self._notes = list(notes)
        self._objects = list(objects)
        self._files = list(files)
        self._maps = list(maps)
        self._marker_items = list(markers)
        self._tasks_by_id = {item.id: item for item in tasks}
        self._projects_by_id = {item.id: item for item in projects}
        self._notes_by_id = {item.id: item for item in notes}
        self._objects_by_id = {item.id: item for item in objects}
        self._files_by_id = {item.id: item for item in files}
        self._maps_by_id = {item.id: item for item in maps}
        self._marker_items_by_id = {item.id: item for item in markers}

    def _collect_image_attachments(self, fallback_item: CloudFileData) -> List[CloudFileData]:
        # Собираем изображения из привязанных файлов или fallback.
        if self._selected:
            images = [
                self._files_by_id[file_id]
                for file_id in self._selected.file_ids
                if file_id in self._files_by_id and self._files_by_id[file_id].is_image
            ]
            if images:
                return images
        return [fallback_item] if fallback_item.is_image else []

    def _open_image_attachment(self, file_item: CloudFileData) -> None:
        # Открываем диалог просмотра изображения для файлов/привязок.
        cloud_root = get_database().get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "Изображение", "Папка облачного хранилища не настроена.")
            return
        images = self._collect_image_attachments(file_item)
        if not images:
            QMessageBox.warning(self, "Изображение", "Привязанные изображения не найдены.")
            return
        try:
            start_index = next(idx for idx, item in enumerate(images) if item.id == file_item.id)
        except StopIteration:
            start_index = 0
        dialog = MapImagePreviewDialog(
            self,
            images=images,
            start_index=start_index,
            cloud_root=Path(cloud_root),
        )
        dialog.exec()

    def _open_attachment_view(self, kind: str, item_id: int) -> None:
        # Показываем диалог с данными привязанной сущности.
        sources = {
            "task": self._tasks_by_id,
            "project": self._projects_by_id,
            "note": self._notes_by_id,
            "object": self._objects_by_id,
            "file": self._files_by_id,
            "map": self._maps_by_id,
            "marker": self._marker_items_by_id,
        }
        item = sources.get(kind, {}).get(item_id)
        if not item:
            QMessageBox.warning(self, "Элемент не найден", "Не удалось найти выбранный элемент.")
            return

        # Создаем диалог и формируем содержание.
        dialog = QDialog(self)
        dialog.setObjectName("MapAttachmentDialog")
        dialog.setWindowTitle("Просмотр вложения")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        def add_row(label: str, value: str, wrap: bool = False) -> None:
            # Упрощенный конструктор строк формы.
            value_label = QLabel(value or "—")
            if wrap:
                value_label.setWordWrap(True)
            form.addRow(label, value_label)

        if kind == "task":
            dialog.setWindowTitle("Задача на карте")
            add_row("Название", item.title)
            add_row("Проект", item.project_title or "—")
            add_row("Дата", item.day.strftime("%d.%m.%Y") if item.day else "—")
            add_row("Время", item.time_text or "—")
            add_row("Приоритет", item.priority or "—")
            add_row("Статус", "Выполнена" if item.done else "В работе")
            add_row("Описание", item.description or "—", wrap=True)
        elif kind == "project":
            dialog.setWindowTitle("Проект на карте")
            add_row("Название", item.title)
            add_row("Область", item.area or "—")
            add_row(
                "Обновлен",
                item.updated.strftime("%d.%m.%Y") if item.updated else "—",
            )
            add_row("Приоритет", item.priority or "—")
            add_row("Архив", "Да" if item.archived else "Нет")
        elif kind == "note":
            dialog.setWindowTitle("Заметка на карте")
            add_row("Название", item.title)
            add_row("Проект", item.project or "—")
            updated = item.updated.strftime("%d.%m.%Y %H:%M") if isinstance(item.updated, datetime) else str(item.updated)
            add_row("Обновлено", updated)
            add_row("Теги", ", ".join(item.tags) if item.tags else "—")
            add_row("Избранное", "Да" if item.favorite else "Нет")
            add_row("Вложения", "Да" if item.attachment else "Нет")
            add_row("Описание", item.preview or "—", wrap=True)
        elif kind == "object":
            dialog.setWindowTitle("Объект на карте")
            add_row("Название", item.title)
            add_row("Каталог", item.catalog or "—")
            add_row("Тип", item.object_type or "—")
            add_row("Статус", item.status or "—")
            add_row("Создан", item.created_at or "—")
            add_row("Обновлен", item.updated_at or "—")
            add_row("Описание", item.description or "—", wrap=True)
        elif kind == "map":
            dialog.setWindowTitle("Карта")
            add_row("Название", item.title)
            add_row("Проект", item.project or "—")
            add_row("Описание", item.description or "—", wrap=True)
        elif kind == "marker":
            dialog.setWindowTitle("Метка карты")
            map_title = self._maps_by_id.get(item.map_id).title if item.map_id in self._maps_by_id else "—"
            add_row("Название", item.name)
            add_row("Карта", map_title)
        elif kind == "file":
            dialog.setWindowTitle("Файл на карте")
            if item.is_image:
                # Для изображений используем полноэкранный просмотр.
                self._open_image_attachment(item)
                return
            add_row("Название", item.name or "—")
            add_row("Путь", item.rel_path or "—", wrap=True)
            add_row("Описание", item.description or "—", wrap=True)
            add_row("Размер", f"{item.size:,} байт")
            add_row("Хэш", item.hash_value or "—", wrap=True)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        # Стилизация диалога.
        dialog.setStyleSheet(f"""
            QDialog#MapAttachmentDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#MapAttachmentDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#MapAttachmentDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)
        dialog.exec()


    def set_tool(self, tool: MapTool) -> None:
        # Переключаем активный инструмент на канве.
        self._tool = tool
        self._preview_pos = None
        if tool not in (MapTool.ADD_REGION, MapTool.MEASURE):
            self._overlay_draft_points = []
        self.update()

    def tool(self) -> MapTool:
        # Текущий активный инструмент.
        return self._tool

    def set_grid_enabled(self, enabled: bool) -> None:
        # Включаем или выключаем сетку и перерисовываем.
        self._grid_enabled = enabled
        self.update()

    def set_tiles(self, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        # Обновляем параметры тайлов и перестраиваем карту.
        self._tiles_path = (tiles_path or "").strip()
        self._tiles_h = max(0, int(tiles_h or 0))
        self._tiles_w = max(0, int(tiles_w or 0))
        self._load_tiles()
        self.reset_view()
        self.update()

    def reset_view(self) -> None:
        # Подгоняем масштаб под виджет и центрируем карту.
        fit_scale = self._fit_scale_to_view()
        self._min_scale = min(self._absolute_min_scale, fit_scale)
        self._scale = min(1.0, fit_scale) if fit_scale > 0 else 1.0
        self._offset = self._center_offset_for_scale(self._scale)

    def _content_bounds(self) -> QRectF:
        # Возвращаем границы содержимого, которое нужно вписать.
        map_bounds = self._map_bounds()
        if not map_bounds.isNull():
            return map_bounds
        if not self._background.isNull():
            return QRectF(QPointF(0, 0), self._background.size())
        return QRectF(0, 0, 1200, 800)

    def _fit_scale_to_view(self) -> float:
        # Рассчитываем масштаб, при котором контент помещается в виджет.
        bounds = self._content_bounds()
        if bounds.isNull():
            return 1.0
        padding = 40
        view_w = max(1, self.width() - padding)
        view_h = max(1, self.height() - padding)
        scale_x = view_w / bounds.width()
        scale_y = view_h / bounds.height()
        return max(0.01, min(scale_x, scale_y))

    def _center_offset_for_scale(self, scale: float) -> QPointF:
        # Вычисляем смещение, чтобы центр содержимого оказался в центре вида.
        bounds = self._content_bounds()
        center_world = bounds.center()
        view_center = QPointF(self.width() / 2, self.height() / 2)
        return view_center - center_world * scale

    def paintEvent(self, event):
        # Отрисовка содержимого канвы.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#1a1c20"))

        # Применяем трансформации для масштаба и смещения.
        painter.save()
        painter.translate(self._offset)
        painter.scale(self._scale, self._scale)

        # Основные слои: фон, сетка, маркеры, предпросмотр.
        self._draw_background(painter)
        if self._grid_enabled:
            self._draw_grid(painter)
        self._draw_overlays(painter)
        self._draw_markers(painter)
        if self._preview_pos and self._tool == MapTool.ADD_MARKER:
            self._draw_preview(painter)
        if self._tool in (MapTool.ADD_REGION, MapTool.MEASURE):
            self._draw_overlay_draft(painter)

        painter.restore()

    def resizeEvent(self, event):
        # Сохраняем мировую точку центра и корректируем масштаб после ресайза.
        world_center = self._map_to_world(QPointF(self.width() / 2, self.height() / 2))
        super().resizeEvent(event)
        fit_scale = self._fit_scale_to_view()
        self._min_scale = min(self._absolute_min_scale, fit_scale)
        if self._scale < self._min_scale:
            self._scale = self._min_scale
        self._offset = QPointF(self.width() / 2, self.height() / 2) - world_center * self._scale

    def _draw_background(self, painter: QPainter) -> None:
        # Отрисовываем загруженную карту или фон по умолчанию.
        if not self._map_pixmap.isNull():
            painter.setOpacity(1.0)
            painter.drawPixmap(QPointF(0, 0), self._map_pixmap)
            return
        if not self._map_bounds().isNull():
            painter.fillRect(self._map_bounds(), QColor("#3a3f36"))
            return
        if self._background.isNull():
            painter.fillRect(QRectF(0, 0, 1200, 800), QColor("#3a3f36"))
            return
        painter.setOpacity(0.9)
        painter.drawPixmap(QPointF(0, 0), self._background)
        painter.setOpacity(1.0)

    def _draw_grid(self, painter: QPainter) -> None:
        # Рисуем сетку поверх карты.
        spacing_x = max(1, self._tile_size.width())
        spacing_y = max(1, self._tile_size.height())
        rect = self._world_view_rect()
        map_bounds = self._map_bounds()
        if not map_bounds.isNull():
            rect = rect.intersected(map_bounds)
            if rect.isEmpty():
                return

        left = int(rect.left() // spacing_x * spacing_x)
        top = int(rect.top() // spacing_y * spacing_y)
        right = int(rect.right())
        bottom = int(rect.bottom())

        pen = QPen(self.GRID_COLOR)
        pen.setWidthF(1.0 / self._scale)
        painter.setPen(pen)

        # Основные линии сетки.
        for x in range(left, right + spacing_x, spacing_x):
            painter.drawLine(x, top, x, bottom)
        for y in range(top, bottom + spacing_y, spacing_y):
            painter.drawLine(left, y, right, y)

        # Подписи координат.
        painter.setPen(self.GRID_TEXT)
        painter.setFont(QFont("Segoe UI", 8))
        for x in range(left, right + spacing_x, spacing_x):
            painter.drawText(QPointF(x + 4, top + 14), f"{x}")
        for y in range(top, bottom + spacing_y, spacing_y):
            painter.drawText(QPointF(left + 4, y - 4), f"{y}")

    def _marker_icon_pixmap(self, marker: Marker, size: int) -> QPixmap | None:
        # Получаем иконку маркера с учетом выбранного типа.
        option = marker_type_for_color(marker.color)
        cache_key = (option.key, size)
        cached = self._marker_icon_cache.get(cache_key)
        if cached is not None:
            return cached
        pixmap = marker_type_pixmap(option, QSize(size, size))
        if pixmap is None:
            return None
        self._marker_icon_cache[cache_key] = pixmap
        return pixmap

    def _draw_markers(self, painter: QPainter) -> None:
        # Рисуем все маркеры и рамку выделения.
        self._resize_handle_regions = {}
        for marker in self._markers:
            is_selected = self._selected and marker.id == self._selected.id
            radius = marker.size + (2.0 if is_selected else 0.0)
            icon_size = max(12, int(marker.size * 2))
            icon_pixmap = self._marker_icon_pixmap(marker, icon_size)
            if icon_pixmap is not None:
                top_left = QPointF(marker.x - icon_size / 2, marker.y - icon_size / 2)
                painter.drawPixmap(top_left, icon_pixmap)
            else:
                painter.setBrush(marker.color)
                painter.setPen(QPen(QColor("#111111"), max(1.0, 1.0 / self._scale)))
                painter.drawEllipse(QPointF(marker.x, marker.y), radius, radius)
            if is_selected:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor("#dfe7f0"), max(1.0, 1.4 / self._scale)))
                painter.drawEllipse(QPointF(marker.x, marker.y), radius + 2, radius + 2)
            painter.setPen(QColor("#e5e5e5"))
            painter.setFont(QFont("Segoe UI", self._marker_label_font_size(marker)))
            painter.drawText(
                QPointF(marker.x + marker.size + 6.0, marker.y - (marker.size + 2.0)),
                marker.name,
            )
            # При активном режиме изменения размера рисуем ручки.
            if self._resize_marker_id == marker.id:
                self._draw_resize_handles(painter, marker)

    def _draw_overlays(self, painter: QPainter) -> None:
        # Отрисовываем полигоны областей и пути сообщения.
        for overlay in self._overlays:
            if len(overlay.points) < 2:
                continue
            pen = QPen(overlay.color, max(1.0, 2.0 / self._scale))
            painter.setPen(pen)
            if overlay.kind == "region":
                poly = QPolygonF(overlay.points)
                fill = QColor(overlay.color)
                fill.setAlpha(55)
                painter.setBrush(fill)
                painter.drawPolygon(poly)
            else:
                painter.setBrush(Qt.NoBrush)
                painter.drawPolyline(QPolygonF(overlay.points))

    def _draw_overlay_draft(self, painter: QPainter) -> None:
        # Отрисовываем черновую линию/область при режиме рисования.
        if not self._overlay_draft_points:
            return
        preview_color = QColor("#67b9ff") if self._tool == MapTool.MEASURE else QColor("#f2c26d")
        pen = QPen(preview_color, max(1.0, 2.0 / self._scale))
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        if len(self._overlay_draft_points) == 1:
            p = self._overlay_draft_points[0]
            painter.drawEllipse(p, 4.0 / self._scale, 4.0 / self._scale)
            return
        poly = QPolygonF(self._overlay_draft_points)
        if self._tool == MapTool.ADD_REGION and len(self._overlay_draft_points) >= 3:
            fill = QColor(preview_color)
            fill.setAlpha(40)
            painter.setBrush(fill)
            painter.drawPolygon(poly)
        else:
            painter.setBrush(Qt.NoBrush)
            painter.drawPolyline(poly)

    def _draw_preview(self, painter: QPainter) -> None:
        # Предпросмотр размещения нового маркера.
        if not self._preview_pos:
            return
        painter.setPen(QPen(QColor("#cfd8dc"), 1.0 / self._scale))
        painter.setBrush(QColor(200, 200, 200, 60))
        painter.drawEllipse(self._preview_pos, self.CREATE_DEFAULT_MARKER_SIZE, self.CREATE_DEFAULT_MARKER_SIZE)

    def _world_view_rect(self) -> QRectF:
        # Рассчитываем видимую область в мировых координатах.
        inv_scale = 1.0 / self._scale
        top_left = (QPointF(0, 0) - self._offset) * inv_scale
        bottom_right = (QPointF(self.width(), self.height()) - self._offset) * inv_scale
        return QRectF(top_left, bottom_right).normalized()

    def _map_to_world(self, pos: QPointF) -> QPointF:
        # Перевод координат из экранных в мировые.
        pos_f = QPointF(pos)
        return (pos_f - self._offset) / self._scale

    def _map_from_world(self, pos: QPointF) -> QPointF:
        # Перевод координат из мировых в экранные.
        return pos * self._scale + self._offset

    def _map_bounds(self) -> QRectF:
        # Границы карты на основе размера тайлов.
        if self._tiles_w <= 0 or self._tiles_h <= 0:
            return QRectF()
        width = self._tile_size.width() * self._tiles_w
        height = self._tile_size.height() * self._tiles_h
        return QRectF(0, 0, float(width), float(height))

    def _load_tiles(self) -> None:
        # Загружаем тайлы карты и собираем единый QPixmap.
        self._map_pixmap = QPixmap()
        base = Path(self._tiles_path)
        tile_size = QSize(0, 0)
        if self._tiles_w <= 0 or self._tiles_h <= 0:
            return
        if base and base.exists():
            for row in range(1, self._tiles_h + 1):
                for col in range(1, self._tiles_w + 1):
                    tile_path = base / f"{row}_{col}.png"
                    if not tile_path.exists():
                        continue
                    pixmap = QPixmap(str(tile_path))
                    if pixmap.isNull():
                        continue
                    tile_size = pixmap.size()
                    break
                if tile_size.width() > 0:
                    break
        if tile_size.isEmpty():
            # Если тайлы не найдены, используем размер по умолчанию.
            tile_size = QSize(80, 80)
        self._tile_size = tile_size
        map_width = tile_size.width() * self._tiles_w
        map_height = tile_size.height() * self._tiles_h
        if map_width <= 0 or map_height <= 0:
            return
        self._map_pixmap = QPixmap(map_width, map_height)
        self._map_pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(self._map_pixmap)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if base and base.exists():
            # Проходим по плиткам и рисуем их в общий холст.
            for row in range(1, self._tiles_h + 1):
                for col in range(1, self._tiles_w + 1):
                    tile_path = base / f"{row}_{col}.png"
                    if not tile_path.exists():
                        continue
                    pixmap = QPixmap(str(tile_path))
                    if pixmap.isNull():
                        continue
                    if pixmap.size() != tile_size:
                        pixmap = pixmap.scaled(tile_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    x = (col - 1) * tile_size.width()
                    y = (row - 1) * tile_size.height()
                    painter.drawPixmap(QPointF(x, y), pixmap)
        painter.end()

    def _marker_at(self, world_pos: QPointF) -> Optional[Marker]:
        # Проверяем попадание в маркер или его подпись.
        for marker in reversed(self._markers):
            dist = (QPointF(marker.x, marker.y) - world_pos)
            hit_radius = max(10.0, marker.size + 6.0)
            if dist.manhattanLength() <= hit_radius:
                return marker
            label_rect = self._marker_label_rect(marker)
            if label_rect.contains(world_pos):
                return marker
        return None

    def _marker_by_id(self, marker_id: int) -> Optional[Marker]:
        # Ищем маркер по идентификатору.
        for marker in self._markers:
            if marker.id == marker_id:
                return marker
        return None

    def _set_marker(self, updated: Marker) -> None:
        # Обновляем маркер в списке и уведомляем подписчиков.
        self._markers = [updated if m.id == updated.id else m for m in self._markers]
        self._selected = updated
        self.markerSelected.emit(updated)
        self.markerUpdated.emit(updated)
        self.update()

    def _draw_resize_handles(self, painter: QPainter, marker: Marker) -> None:
        # Рисуем рамку выделения и ручки изменения размера.
        selection_rect = self._selection_rect(marker)
        handle_size = max(8.0 / self._scale, self.HANDLE_PIXEL_SIZE / self._scale)
        half = handle_size / 2
        self._resize_handle_regions = {}

        pen = QPen(QColor("#67c7ff"), max(1.0, 2.0 / self._scale))
        painter.save()
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawRect(selection_rect)

        painter.setBrush(QColor("#2b2f36"))
        painter.setPen(QPen(QColor("#dfe7f0"), max(1.0, 1.2 / self._scale)))

        cx = selection_rect.center().x()
        cy = selection_rect.center().y()
        left = selection_rect.left()
        right = selection_rect.right()
        top = selection_rect.top()
        bottom = selection_rect.bottom()
        positions = {
            "nw": QPointF(left, top),
            "n": QPointF(cx, top),
            "ne": QPointF(right, top),
            "e": QPointF(right, cy),
            "se": QPointF(right, bottom),
            "s": QPointF(cx, bottom),
            "sw": QPointF(left, bottom),
            "w": QPointF(left, cy),
        }
        for name, center in positions.items():
            rect = QRectF(center.x() - half, center.y() - half, handle_size, handle_size)
            painter.drawRect(rect)
            self._resize_handle_regions[name] = rect
        painter.restore()

    def _marker_label_font_size(self, marker: Marker) -> float:
        # Размер шрифта подписи зависит от размера маркера.
        return max(6.0, 8.0 * (marker.size / self.DEFAULT_MARKER_SIZE))

    def _marker_label_rect(self, marker: Marker) -> QRectF:
        # Рассчитываем область, занимаемую подписью маркера.
        font = QFont("Segoe UI", self._marker_label_font_size(marker))
        metrics = QFontMetricsF(font)
        text = marker.name
        width = metrics.horizontalAdvance(text)
        height = metrics.height()
        pos = QPointF(marker.x + marker.size + 6.0, marker.y - (marker.size + 2.0))
        top = pos.y() - metrics.ascent()
        return QRectF(pos.x(), top, width, height)

    def _selection_rect(self, marker: Marker) -> QRectF:
        # Возвращаем квадратную рамку выделения вокруг маркера и подписи.
        marker_rect = QRectF(
            marker.x - marker.size,
            marker.y - marker.size,
            marker.size * 2.0,
            marker.size * 2.0,
        )
        label_rect = self._marker_label_rect(marker)
        combined = marker_rect.united(label_rect)
        padding = self.RESIZE_FRAME_PADDING / self._scale
        combined = combined.adjusted(-padding, -padding, padding, padding)
        size = max(combined.width(), combined.height())
        center = combined.center()
        return QRectF(center.x() - size / 2, center.y() - size / 2, size, size)

    def _resize_handle_at(self, world_pos: QPointF) -> Optional[str]:
        # Определяем, в какую ручку попадает курсор.
        for direction, rect in self._resize_handle_regions.items():
            if rect.contains(world_pos):
                return direction
        return None

    def _resize_handle_cursor(self, handle: str) -> Qt.CursorShape:
        # Возвращаем курсор для конкретной ручки изменения размера.
        if handle in ("nw", "se"):
            return Qt.SizeFDiagCursor
        if handle in ("ne", "sw"):
            return Qt.SizeBDiagCursor
        if handle in ("n", "s"):
            return Qt.SizeVerCursor
        if handle in ("e", "w"):
            return Qt.SizeHorCursor
        return Qt.SizeAllCursor

    def _resize_scale_delta(self, handle: str, delta: QPointF) -> float:
        # Преобразуем смещение мыши в изменение масштаба маркера.
        dirs = {
            "n": (0, -1),
            "s": (0, 1),
            "e": (1, 0),
            "w": (-1, 0),
            "nw": (-1, -1),
            "ne": (1, -1),
            "sw": (-1, 1),
            "se": (1, 1),
        }
        dir_x, dir_y = dirs.get(handle, (0, 0))
        if dir_x and dir_y:
            return max(delta.x() * dir_x, delta.y() * dir_y)
        if dir_x:
            return delta.x() * dir_x
        return delta.y() * dir_y

    def _enable_resize_mode(self, marker_id: int) -> None:
        # Включаем режим изменения размера выбранного маркера.
        marker = self._marker_by_id(marker_id)
        if not marker:
            return
        self._selected = marker
        self.markerSelected.emit(marker)
        self._resize_marker_id = marker_id
        self._active_resize_handle = None
        self._resize_dragging = False
        self.update()

    def _zoom_to_marker(self, marker: Marker) -> None:
        # Приближаем камеру к выбранному маркеру.
        target_scale = min(self._max_scale, max(self._min_scale, self._scale * 1.4))
        view_center = QPointF(self.width() / 2, self.height() / 2)
        self._scale = target_scale
        self._offset = view_center - QPointF(marker.x, marker.y) * self._scale
        self.update()

    def focus_on_marker(self, marker: Marker, zoom_boost: float = 4.0) -> None:
        # Центрируемся на маркере и увеличиваем масштаб.
        target_scale = min(self._max_scale, max(self._min_scale, self._scale + zoom_boost))
        view_center = QPointF(self.width() / 2, self.height() / 2)
        self._selected = marker
        self.markerSelected.emit(marker)
        self._scale = target_scale
        self._offset = view_center - QPointF(marker.x, marker.y) * self._scale
        self.setFocus(Qt.OtherFocusReason)
        self.update()

    def _adjust_marker_size(self, marker: Marker, delta: float) -> None:
        # Изменяем размер маркера в пределах допустимых значений.
        new_size = min(self.MAX_MARKER_SIZE, max(self.MIN_MARKER_SIZE, marker.size + delta))
        if new_size == marker.size:
            return
        self._set_marker(
            Marker(
                marker.id,
                marker.name,
                marker.x,
                marker.y,
                marker.color,
                marker.type,
                new_size,
                marker.description,
                marker.properties,
                marker.task_ids,
                marker.project_ids,
                marker.note_ids,
                marker.object_ids,
                marker.file_ids,
                marker.map_ids,
                marker.marker_ids,
                marker.parent_path,
                marker.image_path,
            )
        )

    def mousePressEvent(self, event):
        # Обработка кликов мыши на канве.
        if event.button() == Qt.RightButton:
            if self._tool in (MapTool.ADD_REGION, MapTool.MEASURE):
                if self._overlay_draft_points:
                    self._finalize_overlay()
                else:
                    self._open_context_menu(event.pos())
                return
            if event.modifiers() & Qt.ControlModifier:
                # Ctrl + ПКМ — открыть карточку выбранного маркера.
                world_pos = self._map_to_world(event.position())
                marker = self._marker_at(world_pos)
                if marker:
                    self._selected = marker
                    self.markerSelected.emit(marker)
                    self._view_marker(marker)
                return
            # Обычный ПКМ открывает контекстное меню.
            self._open_context_menu(event.pos())
            return

        if event.button() == Qt.LeftButton:
            if self._tool in (MapTool.ADD_REGION, MapTool.MEASURE):
                self._append_overlay_point(self._map_to_world(event.position()))
                return
            # ЛКМ — выбор, перемещение, добавление маркеров или панорамирование.
            world_pos = self._map_to_world(event.position())
            if self._resize_marker_id is not None:
                handle = self._resize_handle_at(world_pos)
                if handle:
                    marker = self._marker_by_id(self._resize_marker_id)
                    if marker:
                        self._active_resize_handle = handle
                        self._resize_start_pos = world_pos
                        self._resize_start_rect = self._selection_rect(marker)
                        self._resize_start_marker_size = marker.size
                    return
                # Если зажали рамку, включаем перемещение маркера.
                marker = self._marker_by_id(self._resize_marker_id)
                if marker and self._selection_rect(marker).contains(world_pos):
                    self._resize_dragging = True
                    self._resize_drag_offset = world_pos - QPointF(marker.x, marker.y)
                    return
                self._resize_marker_id = None
                self._active_resize_handle = None
            if self._tool == MapTool.ADD_MARKER:
                # Добавляем новый маркер.
                self._add_marker(world_pos)
                return
            marker = self._marker_at(world_pos)
            if marker:
                # Выделяем маркер и готовимся к перетаскиванию.
                self._selected = marker
                self.markerSelected.emit(marker)
                self._dragging_marker_id = marker.id
                self.update()
                return
            # Снимаем выделение и включаем панорамирование.
            self._selected = None
            self.markerSelected.emit(None)
            self._dragging_marker_id = None
            self._panning = True
            self._last_pos = event.position()
            self.update()

    def mouseMoveEvent(self, event):
        # Обработка движения мыши для ресайза, перетаскивания и панорамирования.
        if self._resize_marker_id is not None:
            world_pos = self._map_to_world(event.position())
            marker = self._marker_by_id(self._resize_marker_id)
            if marker and self._active_resize_handle:
                delta = world_pos - self._resize_start_pos
                size_delta = self._resize_scale_delta(self._active_resize_handle, delta)
                if self._resize_start_rect.width() > 0:
                    new_frame = max(8.0, self._resize_start_rect.width() + 2 * size_delta)
                    scale_factor = new_frame / self._resize_start_rect.width()
                    new_size = self._resize_start_marker_size * scale_factor
                    new_size = min(self.MAX_MARKER_SIZE, max(self.MIN_MARKER_SIZE, new_size))
                    updated = Marker(
                        marker.id,
                        marker.name,
                        marker.x,
                        marker.y,
                        marker.color,
                        marker.type,
                        new_size,
                        marker.description,
                        marker.properties,
                        marker.task_ids,
                        marker.project_ids,
                        marker.note_ids,
                        marker.object_ids,
                        marker.file_ids,
                        marker.map_ids,
                        marker.marker_ids,
                        marker.parent_path,
                        marker.image_path,
                    )
                    self._set_marker(updated)
                    return
            if marker and self._resize_dragging:
                # Перемещаем маркер в режиме изменения размера.
                new_center = world_pos - self._resize_drag_offset
                updated = Marker(
                    marker.id,
                    marker.name,
                    new_center.x(),
                    new_center.y(),
                    marker.color,
                    marker.type,
                    marker.size,
                    marker.description,
                    marker.properties,
                    marker.task_ids,
                    marker.project_ids,
                    marker.note_ids,
                    marker.object_ids,
                    marker.file_ids,
                    marker.map_ids,
                    marker.marker_ids,
                    marker.parent_path,
                    marker.image_path,
                )
                self._set_marker(updated)
                return
            if marker:
                # Обновляем курсор при наведении на ручки.
                handle = self._resize_handle_at(world_pos)
                if handle:
                    self.setCursor(self._resize_handle_cursor(handle))
                    return
                if self._selection_rect(marker).contains(world_pos):
                    self.setCursor(Qt.SizeAllCursor)
                    return
            self.unsetCursor()
        if self._dragging_marker_id is not None and self._tool == MapTool.SELECT:
            # Перетаскиваем выбранный маркер.
            world_pos = self._map_to_world(event.position())
            marker = self._marker_by_id(self._dragging_marker_id)
            if marker:
                updated = Marker(
                    marker.id,
                    marker.name,
                    world_pos.x(),
                    world_pos.y(),
                    marker.color,
                    marker.type,
                    marker.size,
                    marker.description,
                    marker.properties,
                    marker.task_ids,
                    marker.project_ids,
                    marker.note_ids,
                    marker.object_ids,
                    marker.file_ids,
                    marker.map_ids,
                    marker.marker_ids,
                    marker.parent_path,
                    marker.image_path,
                )
                self._set_marker(updated)
                return
        if self._panning:
            # Панорамируем карту.
            delta = event.position() - self._last_pos
            self._offset += delta
            self._last_pos = event.position()
            self.update()
            return
        if self._tool == MapTool.ADD_MARKER:
            # Обновляем предпросмотр при добавлении маркера.
            self._preview_pos = self._map_to_world(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        # Сбрасываем состояния после отпускания кнопки мыши.
        if event.button() == Qt.LeftButton:
            self._panning = False
            self._dragging_marker_id = None
            self._active_resize_handle = None
            self._resize_dragging = False

    def mouseDoubleClickEvent(self, event):
        # Двойной клик по маркеру — фокусируем и увеличиваем. В режимах рисования завершает контур.
        if event.button() == Qt.LeftButton:
            if self._tool in (MapTool.ADD_REGION, MapTool.MEASURE):
                self._append_overlay_point(self._map_to_world(event.position()))
                self._finalize_overlay()
                return
            world_pos = self._map_to_world(event.position())
            marker = self._marker_at(world_pos)
            if marker:
                self._selected = marker
                self.markerSelected.emit(marker)
                self._zoom_to_marker(marker)
                return
        super().mouseDoubleClickEvent(event)

    def _append_overlay_point(self, point: QPointF) -> None:
        # Добавляем вершину чернового контура.
        self._overlay_draft_points.append(point)
        self.update()

    def _finalize_overlay(self) -> None:
        # Завершаем построение области/пути и переносим в список геометрий.
        points = list(self._overlay_draft_points)
        if self._tool == MapTool.ADD_REGION and len(points) >= 3:
            overlay = MapOverlay(
                id=self._next_overlay_id,
                kind="region",
                points=points,
                color=QColor("#e2a84e"),
                title=f"Область {self._next_overlay_id}",
            )
            self._next_overlay_id += 1
            self._overlays.append(overlay)
        elif self._tool == MapTool.MEASURE and len(points) >= 2:
            overlay = MapOverlay(
                id=self._next_overlay_id,
                kind="path",
                points=points,
                color=QColor("#6cb5ff"),
                title=f"Путь {self._next_overlay_id}",
            )
            self._next_overlay_id += 1
            self._overlays.append(overlay)
        self._overlay_draft_points = []
        self.update()

    def wheelEvent(self, event):
        # Обрабатываем масштабирование и изменение размера маркера.
        if event.modifiers() & Qt.ControlModifier:
            cursor_pos = event.position()
            world_pos = self._map_to_world(cursor_pos)
            marker = self._marker_at(world_pos)
            if marker:
                # Ctrl + колесо меняет размер маркера.
                delta = 1.0 if event.angleDelta().y() > 0 else -1.0
                self._adjust_marker_size(marker, delta)
                return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1 / 1.15
        new_scale = max(self._min_scale, min(self._max_scale, self._scale * factor))
        if new_scale == self._scale:
            return
        cursor_pos = event.position()
        world_before = self._map_to_world(cursor_pos)
        self._scale = new_scale
        self._offset = cursor_pos - world_before * self._scale
        self.update()

    def _add_marker(self, world_pos: QPointF) -> None:
        # Создаем новый маркер с дефолтными параметрами.
        default_type = default_marker_type()
        marker = Marker(
            self._next_id,
            f"Marker {self._next_id}",
            float(world_pos.x()),
            float(world_pos.y()),
            default_type.color,
            "Point",
            self.CREATE_DEFAULT_MARKER_SIZE,
            "",
            "",
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            "",
            "",
        )
        self._next_id += 1
        self._markers.append(marker)
        self._selected = marker
        self.markerAdded.emit(marker)
        self.markerSelected.emit(marker)
        self._preview_pos = None
        self.update()

    def _remove_marker(self, marker: Marker) -> None:
        # Удаляем маркер и сбрасываем выделение при необходимости.
        self._markers = [m for m in self._markers if m.id != marker.id]
        self.markerRemoved.emit(marker.id)
        if self._selected and self._selected.id == marker.id:
            self._selected = None
            self.markerSelected.emit(None)
        self.update()

    def _edit_marker(self, marker: Marker) -> None:
        # Открываем диалог редактирования маркера.
        def task_label(item) -> str:
            # Отображение задачи в списке.
            return f"{item.title} · {item.project_title}" if item.project_title else item.title

        def project_label(item) -> str:
            # Отображение проекта в списке.
            return f"{item.title} · {item.area}" if item.area else item.title

        def note_label(item) -> str:
            # Отображение заметки в списке.
            return f"{item.title} · {item.project}" if item.project else item.title

        def object_label(item) -> str:
            # Отображение объекта в списке.
            return f"{item.title} · {item.catalog}" if item.catalog else item.title

        def file_label(item) -> str:
            # Отображение файла в списке.
            return item.name or item.rel_path

        def map_label(item) -> str:
            # Отображение карты в списке.
            return f"{item.title} · {item.project}" if item.project else item.title

        def marker_label(item) -> str:
            # Отображение метки в списке.
            map_title = self._maps_by_id.get(item.map_id).title if item.map_id in self._maps_by_id else ""
            return f"{item.name} · {map_title}" if map_title else item.name

        # Источники сущностей для привязок.
        entity_sources = {
            "task": MapLabelEntitySource(
                "Задачи",
                self._tasks,
                task_label,
                "Привязать задачу...",
                "fa5s.tasks",
                "task",
            ),
            "project": MapLabelEntitySource(
                "Проекты",
                self._projects,
                project_label,
                "Привязать проект...",
                "fa5s.folder-open",
                "project",
            ),
            "note": MapLabelEntitySource(
                "Заметки",
                self._notes,
                note_label,
                "Привязать заметку...",
                "fa5s.sticky-note",
                "note",
            ),
            "object": MapLabelEntitySource(
                "Объекты",
                self._objects,
                object_label,
                "Привязать объект...",
                "fa5s.cube",
                "object",
            ),
            "file": MapLabelEntitySource(
                "Файлы",
                self._files,
                file_label,
                "Привязать файл...",
                "fa5s.paperclip",
                "file",
            ),
            "map": MapLabelEntitySource(
                "Карты",
                self._maps,
                map_label,
                "Привязать карту...",
                "fa5s.map-marked-alt",
                "map",
            ),
            "marker": MapLabelEntitySource(
                "Метки",
                self._marker_items,
                marker_label,
                "Привязать метку...",
                "fa5s.map-pin",
                "marker",
            ),
        }
        type_suggestions = sorted({item.type for item in self._markers if item.type})

        # Создаем и показываем диалог редактирования.
        dialog = MapLabelEditDialog(
            marker,
            entity_sources,
            type_suggestions=type_suggestions,
            mode="edit",
            size_range=(self.MIN_MARKER_SIZE, self.MAX_MARKER_SIZE),
            parent=self,
        )

        # Пример использования результата: dialog.result_marker(), dialog.image_path(), dialog.parent_path().
        if dialog.exec() == QDialog.Accepted:
            updated = dialog.result_marker()
            self._set_marker(updated)
            if dialog.resize_requested():
                self._enable_resize_mode(updated.id)

    def _load_marker_preview(self, marker: Marker, target: QSize) -> QPixmap | None:
        # Загружаем превью изображения маркера для карточки.
        image_path = (marker.image_path or "").strip()
        if not image_path:
            return None
        path = Path(image_path)
        file_path = path if path.is_file() else None
        if file_path is None:
            cloud_root = get_database().get_setting("cloud_storage_path", default="").strip()
            if cloud_root:
                candidate = Path(cloud_root) / image_path
                if candidate.is_file():
                    file_path = candidate
        if not file_path:
            return None
        pixmap = QPixmap(str(file_path))
        if pixmap.isNull():
            return None
        return pixmap.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    def _view_marker(self, marker: Marker) -> None:
        # Показываем окно просмотра данных маркера.
        dialog = QDialog(self)
        dialog.setWindowTitle("Метка на карте")
        dialog.setObjectName("MapLabelViewDialog")
        dialog.resize(980, 680)
        dialog.setMinimumSize(760, 520)

        # Корневой layout диалога.
        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Заголовок с кнопками.
        header = QFrame()
        header.setObjectName("MapLabelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(12)

        title = QLabel("Метка на карте")
        title.setObjectName("MapLabelTitle")
        header_layout.addWidget(title)
        header_layout.addItem(QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        edit_btn = QPushButton("Редактировать")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.clicked.connect(lambda _checked=False: (dialog.accept(), self._edit_marker(marker)))

        close_btn = QToolButton()
        close_btn.setObjectName("MapLabelClose")
        close_btn.setText("✕")
        close_btn.clicked.connect(dialog.reject)

        header_layout.addWidget(edit_btn)
        header_layout.addWidget(close_btn)

        # Основное тело диалога.
        body = QFrame()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        left_panel = QFrame()
        left_panel.setObjectName("MapLabelCard")
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)

        preview_title = QLabel("Превью")
        preview_title.setObjectName("MapLabelSectionTitle")
        preview_label = QLabel("Нет изображения")
        preview_label.setObjectName("MapLabelPreview")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setFixedHeight(168)
        preview_size = QSize(left_panel.width() - 24, 168)
        preview_pixmap = self._load_marker_preview(marker, preview_size)
        if preview_pixmap is not None:
            preview_label.setPixmap(preview_pixmap)
            preview_label.setText("")
        elif marker.image_path:
            preview_label.setText("Изображение недоступно")
        if marker.image_path:
            preview_label.setToolTip(marker.image_path)

        marker_type_title = QLabel("Тип метки")
        marker_type_title.setObjectName("MapLabelSectionTitle")
        marker_type_preview = QLabel()
        marker_type_preview.setObjectName("MapLabelMarkerPreview")
        marker_type_preview.setFixedSize(28, 28)
        marker_type_preview.setAlignment(Qt.AlignCenter)
        marker_type_value = QLabel()
        marker_type_value.setObjectName("MapLabelValue")
        marker_type_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        marker_type = marker_type_for_color(marker.color)
        marker_type_value.setText(marker_type.label)
        marker_type_icon_pixmap = marker_type_pixmap(marker_type, marker_type_preview.size())
        if marker_type_icon_pixmap is not None:
            marker_type_preview.setPixmap(marker_type_icon_pixmap)
            marker_type_preview.setText("")
        else:
            marker_type_preview.setPixmap(QPixmap())
            marker_type_preview.setText(marker_type.label)

        marker_type_row = QHBoxLayout()
        marker_type_row.addWidget(marker_type_preview)
        marker_type_row.addWidget(marker_type_value)
        marker_type_row.addStretch(1)

        coords_title = QLabel("Координаты")
        coords_title.setObjectName("MapLabelSectionTitle")
        coords_value = QLabel(f"{marker.x:.0f}, {marker.y:.0f}")
        coords_value.setObjectName("MapLabelValue")
        coords_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        size_title = QLabel("Размер")
        size_title.setObjectName("MapLabelSectionTitle")
        size_value = QLabel(f"{marker.size:.1f}")
        size_value.setObjectName("MapLabelValue")
        size_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        left_layout.addWidget(preview_title)
        left_layout.addWidget(preview_label)
        left_layout.addWidget(marker_type_title)
        left_layout.addLayout(marker_type_row)
        left_layout.addSpacing(6)
        left_layout.addWidget(coords_title)
        left_layout.addWidget(coords_value)
        left_layout.addSpacing(6)
        left_layout.addWidget(size_title)
        left_layout.addWidget(size_value)
        left_layout.addStretch(1)

        # Правая панель с подробностями и привязками.
        right_panel = QFrame()
        right_panel.setObjectName("MapLabelFormContainer")
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        main_section = QFrame()
        main_section.setObjectName("MapLabelSection")
        main_layout = QVBoxLayout(main_section)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        main_title = QLabel("Основное")
        main_title.setObjectName("MapLabelSectionTitle")
        main_layout.addWidget(main_title)

        main_form = QFormLayout()
        main_form.setSpacing(10)
        main_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        main_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        name_label = QLabel("Название")
        name_label.setObjectName("MapLabelFormLabel")
        name_value = QLabel(marker.name)
        name_value.setObjectName("MapLabelValue")
        name_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        type_label = QLabel("Тип")
        type_label.setObjectName("MapLabelFormLabel")
        type_value = QLabel(marker.type or "—")
        type_value.setObjectName("MapLabelValue")
        type_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        main_form.addRow(name_label, name_value)
        main_form.addRow(type_label, type_value)
        main_layout.addLayout(main_form)

        # Секция привязок.
        links_section = QFrame()
        links_section.setObjectName("MapLabelSection")
        links_layout = QVBoxLayout(links_section)
        links_layout.setContentsMargins(12, 12, 12, 12)
        links_layout.setSpacing(10)
        links_title = QLabel("Привязки")
        links_title.setObjectName("MapLabelSectionTitle")
        links_layout.addWidget(links_title)
        links_form = QFormLayout()
        links_form.setSpacing(10)
        links_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)

        def handle_link(link: str) -> None:
            # Обрабатываем клики по ссылкам привязок.
            if ":" not in link:
                return
            kind, item_id = link.split(":", 1)
            try:
                parsed_id = int(item_id)
            except ValueError:
                return
            self._open_attachment_view(kind, parsed_id)

        def attachment_label(kind: str, item_ids: List[int], source: dict) -> QLabel:
            # Формируем HTML-ссылки для списка привязок.
            label = QLabel()
            label.setObjectName("MapLabelValue")
            label.setTextFormat(Qt.RichText)
            label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            label.setOpenExternalLinks(False)
            label.setStyleSheet(
                "QLabel a {"
                "background-color: #f1f3f6;"
                "border-radius: 4px;"
                "padding: 1px 4px;"
                "}"
            )
            if not item_ids:
                label.setText("—")
                return label
            links = []
            for item_id in item_ids:
                item = source.get(item_id)
                if not item:
                    links.append("не найдено")
                    continue
                title = getattr(item, "title", None) or getattr(item, "name", None) or getattr(item, "rel_path", "—")
                links.append(f'<a style="background:#CCC;border-radius:4px;" href="{kind}:{item_id}">{title}</a>')
            label.setText("<br>".join(links))
            label.linkActivated.connect(handle_link)
            return label

        task_link = attachment_label("task", marker.task_ids, self._tasks_by_id)
        project_link = attachment_label("project", marker.project_ids, self._projects_by_id)
        note_link = attachment_label("note", marker.note_ids, self._notes_by_id)
        object_link = attachment_label("object", marker.object_ids, self._objects_by_id)
        file_link = attachment_label("file", marker.file_ids, self._files_by_id)
        map_link = attachment_label("map", marker.map_ids, self._maps_by_id)
        marker_link = attachment_label("marker", marker.marker_ids, self._marker_items_by_id)

        def add_link_row(label_text: str, widget: QLabel) -> None:
            # Утилита для добавления строки формы.
            label = QLabel(label_text)
            label.setObjectName("MapLabelFormLabel")
            links_form.addRow(label, widget)

        add_link_row("Задачи", task_link)
        add_link_row("Проекты", project_link)
        add_link_row("Заметки", note_link)
        add_link_row("Объекты", object_link)
        add_link_row("Файлы", file_link)
        add_link_row("Карты", map_link)
        add_link_row("Метки", marker_link)

        links_layout.addLayout(links_form)

        # Секция текстовых полей.
        text_section = QFrame()
        text_section.setObjectName("MapLabelSection")
        text_layout = QVBoxLayout(text_section)
        text_layout.setContentsMargins(12, 12, 12, 12)
        text_layout.setSpacing(10)
        text_title = QLabel("Текст заметок")
        text_title.setObjectName("MapLabelSectionTitle")
        text_layout.addWidget(text_title)

        desc_label = QLabel("Описание")
        desc_label.setObjectName("MapLabelFieldLabel")
        desc_value = QLabel(marker.description or "—")
        desc_value.setObjectName("MapLabelValue")
        desc_value.setWordWrap(True)
        desc_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        props_wrap = QFrame()
        props_wrap.setObjectName("MapLabelImportant")
        props_layout = QVBoxLayout(props_wrap)
        props_layout.setContentsMargins(10, 8, 10, 8)
        props_layout.setSpacing(6)

        props_header = QHBoxLayout()
        props_icon = QLabel("⚑")
        props_icon.setObjectName("MapLabelImportantIcon")
        props_label = QLabel("Важные пометки")
        props_label.setObjectName("MapLabelFieldLabel")
        props_header.addWidget(props_icon)
        props_header.addWidget(props_label)
        props_header.addStretch(1)

        props_value = QLabel(marker.properties or "—")
        props_value.setObjectName("MapLabelValue")
        props_value.setWordWrap(True)
        props_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        props_layout.addLayout(props_header)
        props_layout.addWidget(props_value)

        text_layout.addWidget(desc_label)
        text_layout.addWidget(desc_value)
        text_layout.addWidget(props_wrap)

        right_layout.addWidget(main_section)
        right_layout.addWidget(links_section)
        right_layout.addWidget(text_section)
        right_layout.addStretch(1)

        body_layout.addWidget(left_panel, 0)
        body_layout.addWidget(right_panel, 1)

        root_layout.addWidget(header)
        root_layout.addWidget(body, 1)

        # Стили диалога просмотра.
        dialog.setStyleSheet(
            f"""
            QDialog#MapLabelViewDialog {{
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
            QLabel#MapLabelValue {{
                color: #a8abb3;
            }}
            QLabel#MapLabelValue a {{
                color: #a8abb3;
            }}
            QLabel#MapLabelPreview {{
                border: 1px dashed #3a3b40;
                border-radius: 8px;
                color: #8e919a;
                background: #1b1d24;
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
            QToolButton#MapLabelClose {{
                padding: 4px 8px;
                min-width: 28px;
            }}
            QLabel#MapLabelMarkerPreview {{
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}
            QFrame#MapLabelImportant {{
                border-left: 3px solid #d59d35;
                background: rgba(29, 31, 39, 0.85);
                border-radius: 8px;
            }}
            """
        )
        dialog.exec()

    def _open_context_menu(self, pos) -> None:
        # Контекстное меню для быстрых действий с маркером.
        world_pos = self._map_to_world(pos)
        marker = self._marker_at(world_pos)
        menu = QMenu(self)
        act_add = menu.addAction("Добавить маркер")
        act_view = menu.addAction("Просмотреть метку")
        type_menu = menu.addMenu("Тип маркера")
        type_actions = {}
        for option in marker_type_options():
            action = type_menu.addAction(marker_type_icon(option), option.label)
            type_actions[action] = option
        act_bigger = menu.addAction("Увеличить маркер")
        act_smaller = menu.addAction("Уменьшить маркер")
        act_resize = menu.addAction("Изменить размер")
        act_edit = menu.addAction("Редактировать маркер")
        act_delete = menu.addAction("Удалить маркер")
        act_view.setEnabled(marker is not None)
        type_menu.setEnabled(marker is not None)
        act_bigger.setEnabled(marker is not None)
        act_smaller.setEnabled(marker is not None)
        act_resize.setEnabled(marker is not None)
        act_edit.setEnabled(marker is not None)
        act_delete.setEnabled(marker is not None)
        chosen = menu.exec(QCursor.pos())
        if chosen == act_add:
            self._add_marker(world_pos)
        elif chosen == act_view and marker:
            self._view_marker(marker)
        elif chosen in type_actions and marker:
            option = type_actions[chosen]
            self._set_marker(
                Marker(
                    marker.id,
                    marker.name,
                    marker.x,
                    marker.y,
                    option.color,
                    marker.type,
                    marker.size,
                    marker.description,
                    marker.properties,
                    marker.task_ids,
                    marker.project_ids,
                    marker.note_ids,
                    marker.object_ids,
                    marker.file_ids,
                    marker.map_ids,
                    marker.marker_ids,
                    marker.parent_path,
                    marker.image_path,
                )
            )
        elif chosen == act_bigger and marker:
            self._adjust_marker_size(marker, 1.5)
        elif chosen == act_smaller and marker:
            self._adjust_marker_size(marker, -1.5)
        elif chosen == act_resize and marker:
            self._enable_resize_mode(marker.id)
        elif chosen == act_edit and marker:
            self._edit_marker(marker)
        elif chosen == act_delete and marker:
            self._remove_marker(marker)


class MarkerSearchModel(QAbstractListModel):
    MarkerRole = Qt.UserRole + 1

    def __init__(self, parent=None):
        # Инициализируем модель для поиска маркеров.
        super().__init__(parent)
        # Список маркеров для поиска.
        self._items: List[Marker] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        # Количество строк зависит от списка маркеров.
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int):
        # Возвращаем строку отображения и сам маркер.
        if not index.isValid():
            return None
        marker = self._items[index.row()]
        if role == Qt.DisplayRole:
            title = marker.name or "Метка"
            marker_type = marker.type or "—"
            return f"{title} · {marker_type} ({marker.x:.0f}, {marker.y:.0f})"
        if role == self.MarkerRole:
            return marker
        return None

    def set_markers(self, markers: List[Marker]) -> None:
        # Полностью обновляем модель списка маркеров.
        self.beginResetModel()
        self._items = list(markers)
        self.endResetModel()


class MapEditorWorkspace(QWidget):
    fullscreenToggled = Signal(bool)
    markersChanged = Signal()

    def __init__(self, parent=None):
        # Инициализируем рабочую область редактора карты.
        super().__init__(parent)
        # Основные параметры состояния редактора карты.
        self.setObjectName("MapEditorWorkspace")
        self._db = get_database()
        self._tasks_by_id = {}
        self._projects_by_id = {}
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._info_panel_was_visible = False
        self._fullscreen_active = False
        self._nav_collapsed = False
        self._current_map_id: Optional[int] = None
        self._info_marker_id: Optional[int] = None
        self._info_panel_default_width = 520
        self._info_panel_expanded_width = 600
        self._info_panel_fullscreen_ratio = 0.35

        # Корневая компоновка редактора.
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Левая панель с инструментами.
        self.toolbar = QFrame()
        self.toolbar.setObjectName("MapToolbar")
        self.toolbar.setFixedWidth(54)
        toolbar_layout = QVBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(6, 8, 6, 8)
        toolbar_layout.setSpacing(8)
        toolbar_layout.setAlignment(Qt.AlignTop)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        def tool_button(icon_name: str, tooltip: str, tool: Optional[MapTool]) -> QToolButton:
            # Вспомогательная функция для создания кнопки инструмента.
            btn = QToolButton()
            btn.setIcon(qta.icon(icon_name, color="#d7d7d7"))
            btn.setIconSize(QSize(20, 20))
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.PointingHandCursor)
            if tool is not None:
                self.tool_group.addButton(btn)
                btn.clicked.connect(lambda checked=False, t=tool: self._set_tool(t))
            return btn

        # Кнопки инструментов.
        self.btn_select = tool_button("fa5s.mouse-pointer", "Выбрать", MapTool.SELECT)
        self.btn_marker = tool_button("fa5s.map-marker-alt", "Добавить маркер", MapTool.ADD_MARKER)
        self.btn_region = tool_button("fa5s.draw-polygon", "Добавить регион", MapTool.ADD_REGION)
        self.btn_measure = tool_button("fa5s.ruler", "Рисовать путь", MapTool.MEASURE)
        self.btn_grid = tool_button("fa5s.border-all", "Сетка", None)
        self.btn_grid.setCheckable(True)
        self.btn_grid.setChecked(True)
        self.btn_grid.clicked.connect(lambda checked: self.canvas.set_grid_enabled(checked))

        self.btn_fullscreen = tool_button("fa5s.expand", "Полноэкранный режим", None)
        self.btn_fullscreen.setCheckable(True)
        self.btn_fullscreen.clicked.connect(self._on_fullscreen_toggled)

        self.btn_camera = tool_button("fa5s.camera", "Скриншот", None)
        self.btn_camera.setCheckable(False)

        self._tool_buttons = {
            MapTool.SELECT: self.btn_select,
            MapTool.ADD_MARKER: self.btn_marker,
            MapTool.ADD_REGION: self.btn_region,
            MapTool.MEASURE: self.btn_measure,
        }

        # Добавляем кнопки в тулбар.
        for btn in [
            self.btn_select,
            self.btn_marker,
            self.btn_region,
            self.btn_measure,
            self.btn_grid,
            self.btn_fullscreen,
            self.btn_camera,
        ]:
            toolbar_layout.addWidget(btn)

        # Центральная канва карты.
        self.canvas = MapCanvas()
        self.canvas.setObjectName("MapCanvas")
        self._load_attachment_sources()

        # Активируем инструмент выбора по умолчанию.
        self._set_tool(MapTool.SELECT)

        # Правая панель с краткой информацией по маркеру.
        self.info_panel = QFrame()
        self.info_panel.setObjectName("MapInfoPanel")
        self.info_panel.setFixedWidth(self._info_panel_default_width)
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(0)

        self.info_title = QLabel("Данные объекта")
        self.info_title.setObjectName("MapInfoTitle")
        info_layout.addWidget(self.info_title)

        self.info_scroll = QScrollArea()
        self.info_scroll.setObjectName("MapInfoScroll")
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setFrameShape(QFrame.NoFrame)
        self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        info_body = QWidget()
        info_body.setObjectName("FormBox")
        info_body_layout = QHBoxLayout(info_body)
        info_body_layout.setContentsMargins(0, 0, 0, 0)
        info_body_layout.setSpacing(12)

        self.info_scroll.setStyleSheet(
            """
            QWidget#FormBox {
                background: #24262c;
            }
            QScrollArea#MapInfoScroll {
                background: #24262c;
            }
            QWidget {
            }
            """
        )

        left_panel = QFrame()
        left_panel.setObjectName("MapInfoCard")
        left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        self.info_preview_title = QLabel("Превью")
        self.info_preview_title.setObjectName("MapInfoSectionTitle")
        self.info_preview = QLabel("Нет изображения")
        self.info_preview.setObjectName("MapInfoPreview")
        self.info_preview.setAlignment(Qt.AlignCenter)
        self.info_preview.setFixedHeight(140)

        self.info_marker_type_title = QLabel("Тип метки")
        self.info_marker_type_title.setObjectName("MapInfoSectionTitle")
        self.info_marker_type_preview = QLabel()
        self.info_marker_type_preview.setObjectName("MapInfoMarkerPreview")
        self.info_marker_type_preview.setFixedSize(28, 28)
        self.info_marker_type_preview.setAlignment(Qt.AlignCenter)
        self.info_marker_type_value = QLabel("—")
        self.info_marker_type_value.setObjectName("MapInfoValue")

        marker_type_row = QHBoxLayout()
        marker_type_row.setSpacing(8)
        marker_type_row.addWidget(self.info_marker_type_preview)
        marker_type_row.addWidget(self.info_marker_type_value)
        marker_type_row.addStretch(1)

        left_layout.addWidget(self.info_preview_title)
        left_layout.addWidget(self.info_preview)
        left_layout.addSpacing(6)
        left_layout.addWidget(self.info_marker_type_title)
        left_layout.addLayout(marker_type_row)
        left_layout.addStretch(1)

        right_panel = QFrame()
        right_panel.setObjectName("MapInfoFormContainer")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        main_section = QFrame()
        main_section.setObjectName("MapInfoSection")
        main_layout = QVBoxLayout(main_section)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        main_title = QLabel("Основное")
        main_title.setObjectName("MapInfoSectionTitle")
        main_layout.addWidget(main_title)

        main_form = QFormLayout()
        main_form.setSpacing(8)
        main_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.info_name = QLabel("—")
        self.info_type = QLabel("—")
        self.info_size = QLabel("—")
        self.info_coords = QLabel("—")
        self.info_parent = QLabel("—")
        for label in [self.info_name, self.info_type, self.info_size, self.info_coords, self.info_parent]:
            label.setObjectName("MapInfoValue")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        name_label = QLabel("Название")
        type_label = QLabel("Тип")
        size_label = QLabel("Размер")
        coords_label = QLabel("Координаты")
        parent_label = QLabel("Родительский каталог")
        for label in [name_label, type_label, size_label, coords_label, parent_label]:
            label.setObjectName("MapInfoFormLabel")

        main_form.addRow(name_label, self.info_name)
        main_form.addRow(type_label, self.info_type)
        main_form.addRow(size_label, self.info_size)
        main_form.addRow(coords_label, self.info_coords)
        main_form.addRow(parent_label, self.info_parent)
        main_layout.addLayout(main_form)

        links_section = QFrame()
        links_section.setObjectName("MapInfoSection")
        links_layout = QVBoxLayout(links_section)
        links_layout.setContentsMargins(12, 12, 12, 12)
        links_layout.setSpacing(8)

        links_title = QLabel("Привязки")
        links_title.setObjectName("MapInfoSectionTitle")
        links_layout.addWidget(links_title)

        links_form = QFormLayout()
        links_form.setSpacing(8)
        links_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.info_task = QLabel("—")
        self.info_project = QLabel("—")
        self.info_note = QLabel("—")
        self.info_object = QLabel("—")
        self.info_file = QLabel("—")
        self.info_map = QLabel("—")
        self.info_marker = QLabel("—")
        for label in [
            self.info_task,
            self.info_project,
            self.info_note,
            self.info_object,
            self.info_file,
            self.info_map,
            self.info_marker,
        ]:
            label.setObjectName("MapInfoValue")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info_file.setTextFormat(Qt.RichText)
        self.info_file.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.info_file.setOpenExternalLinks(False)
        self.info_file.linkActivated.connect(self._handle_info_link)

        task_label = QLabel("Задачи")
        project_label = QLabel("Проекты")
        note_label = QLabel("Заметки")
        object_label = QLabel("Объекты")
        file_label = QLabel("Файлы")
        map_label = QLabel("Карты")
        marker_label = QLabel("Метки")
        for label in [task_label, project_label, note_label, object_label, file_label, map_label, marker_label]:
            label.setObjectName("MapInfoFormLabel")

        links_form.addRow(task_label, self.info_task)
        links_form.addRow(project_label, self.info_project)
        links_form.addRow(note_label, self.info_note)
        links_form.addRow(object_label, self.info_object)
        links_form.addRow(file_label, self.info_file)
        links_form.addRow(map_label, self.info_map)
        links_form.addRow(marker_label, self.info_marker)
        links_layout.addLayout(links_form)

        text_section = QFrame()
        text_section.setObjectName("MapInfoSection")
        text_layout = QVBoxLayout(text_section)
        text_layout.setContentsMargins(12, 12, 12, 12)
        text_layout.setSpacing(8)

        text_title = QLabel("Пометки! - ВАЖНО")
        text_title.setObjectName("MapInfoSectionTitle")
        text_layout.addWidget(text_title)

        desc_label = QLabel("Текст пометок")
        desc_label.setObjectName("MapInfoFormLabel")
        self.info_description = QLabel("—")
        self.info_description.setObjectName("MapInfoText")
        self.info_description.setWordWrap(True)
        self.info_description.setTextInteractionFlags(Qt.TextSelectableByMouse)

        text_layout.addWidget(desc_label)
        text_layout.addWidget(self.info_description)

        important_wrap = QFrame()
        important_wrap.setObjectName("MapInfoImportant")
        important_layout = QVBoxLayout(important_wrap)
        important_layout.setContentsMargins(10, 8, 10, 8)
        important_layout.setSpacing(6)

        important_header = QHBoxLayout()
        important_icon = QLabel("⚑")
        important_icon.setObjectName("MapInfoImportantIcon")
        important_label = QLabel("Важные пометки")
        important_label.setObjectName("MapInfoFormLabel")
        important_header.addWidget(important_icon)
        important_header.addWidget(important_label)
        important_header.addStretch(1)

        self.info_important = QLabel("—")
        self.info_important.setObjectName("MapInfoText")
        self.info_important.setWordWrap(True)
        self.info_important.setTextInteractionFlags(Qt.TextSelectableByMouse)

        important_layout.addLayout(important_header)
        important_layout.addWidget(self.info_important)

        text_layout.addWidget(important_wrap)

        right_layout.addWidget(main_section)
        right_layout.addWidget(links_section)
        right_layout.addWidget(text_section)
        right_layout.addStretch(1)

        info_body_layout.addWidget(left_panel)
        info_body_layout.addWidget(right_panel, 1)

        self.info_scroll.setWidget(info_body)
        info_layout.addWidget(self.info_scroll)

        # Собираем основные панели.
        root.addWidget(self.toolbar)
        root.addWidget(self.canvas, 1)
        root.addWidget(self.info_panel)

        self.info_panel.hide()

        # Подключаем сигналы от канвы.
        self.canvas.markerSelected.connect(self._on_marker_selected)
        self.canvas.markerAdded.connect(self._on_marker_added)
        self.canvas.markerUpdated.connect(self._on_marker_updated)
        self.canvas.markerRemoved.connect(self._on_marker_removed)

        # Стили для редактора.
        self.setStyleSheet("""
            QWidget#MapEditorWorkspace {
                background: #15171b;
            }

            QFrame#MapToolbar {
                background: #1b1d22;
                border-right: 1px solid #2a2b2f;
            }

            QFrame#MapToolbar QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px;
            }

            QFrame#MapToolbar QToolButton:checked {
                background: #2a2d33;
                border: 1px solid #3a3b40;
            }

            QFrame#MapToolbar QToolButton:hover {
                background: #24262c;
            }

            QFrame#MapInfoPanel {
                background: rgba(20, 22, 30, 0.92);
                border-left: 1px solid #2a2b2f;
            }

            QScrollArea#MapInfoScroll {
                background: #24262c;
            }

            QFrame#MapInfoCard, QFrame#MapInfoSection {
                background: rgba(22, 24, 32, 0.92);
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }

            QLabel#MapInfoTitle {
                color: #f0f0f0;
                font-size: 15px;
                font-weight: 600;
            }

            QLabel#MapInfoSectionTitle {
                color: #d9d9d9;
                font-size: 12px;
                font-weight: 600;
            }

            QLabel#MapInfoFormLabel {
                color: #b9bcc4;
            }

            QLabel#MapInfoValue {
                color: #a8abb3;
                font-size: 12px;
            }

            QLabel#MapInfoText {
                color: #a8abb3;
                font-size: 12px;
            }

            QLabel#MapInfoPreview {
                border: 1px dashed #3a3b40;
                border-radius: 8px;
                color: #8e919a;
                background: #1b1d24;
            }

            QLabel#MapInfoMarkerPreview {
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }

            QFrame#MapInfoImportant {
                border-left: 3px solid #d59d35;
                background: rgba(29, 31, 39, 0.85);
                border-radius: 8px;
            }

            QLabel#MapInfoImportantIcon {
                color: #d59d35;
            }
        """)

    def _set_tool(self, tool: MapTool) -> None:
        # Активируем инструмент и обновляем состояние кнопок.
        button = self._tool_buttons.get(tool)
        if button is not None:
            button.setChecked(True)
        self.canvas.set_tool(tool)

    def set_fullscreen_state(self, enabled: bool) -> None:
        # Синхронизируем кнопку и скрываем/показываем инфо-панель.
        self.btn_fullscreen.blockSignals(True)
        self.btn_fullscreen.setChecked(enabled)
        self.btn_fullscreen.blockSignals(False)
        if self._fullscreen_active == enabled:
            return
        self._fullscreen_active = enabled
        if enabled:
            self._info_panel_was_visible = self.info_panel.isVisible()
        self._update_info_panel_width()
        if not enabled and self._info_panel_was_visible:
            self.info_panel.show()

    def set_nav_collapsed_state(self, collapsed: bool) -> None:
        # Обновляем ширину инфо-панели при сворачивании навигации.
        if self._nav_collapsed == collapsed:
            return
        self._nav_collapsed = collapsed
        self._update_info_panel_width()

    def _update_info_panel_width(self) -> None:
        # Подстраиваем ширину панели в зависимости от состояния навигации.
        if not self._info_widgets_alive():
            return
        if self._fullscreen_active:
            width = max(int(self.width() * self._info_panel_fullscreen_ratio), 1)
        else:
            width = self._info_panel_expanded_width if self._nav_collapsed else self._info_panel_default_width
        self.info_panel.setFixedWidth(width)
        if self._info_marker_id is not None:
            marker = self._markers_by_id.get(self._info_marker_id)
            if marker:
                self._update_info_preview(marker)

    def _on_fullscreen_toggled(self, checked: bool) -> None:
        # Пробрасываем сигнал о полноэкранном режиме.
        self.fullscreenToggled.emit(checked)

    def _on_marker_selected(self, marker: Optional[Marker]) -> None:
        # Отображаем данные выбранного маркера в правой панели.
        if not self._info_widgets_alive():
            return
        if not marker:
            self._info_marker_id = None
            self.info_panel.hide()
            return
        if self._fullscreen_active:
            self._update_info_panel_width()
        self.info_panel.show()
        self._apply_marker_info(marker)

    def _apply_marker_info(self, marker: Marker) -> None:
        # Обновляем значения в инфо-панели.
        if not self._info_widgets_alive():
            return
        self._info_marker_id = marker.id
        self.info_name.setText(self._format_value(marker.name))
        self.info_type.setText(self._format_value(marker.type))
        self.info_size.setText(f"{marker.size:.1f} px / ед.")
        self.info_coords.setText(f"{marker.x:.0f}, {marker.y:.0f}")
        self.info_parent.setText(self._format_value(marker.parent_path))
        self.info_task.setText(self._format_links(marker.task_ids, self._tasks_by_id))
        self.info_project.setText(self._format_links(marker.project_ids, self._projects_by_id))
        self.info_note.setText(self._format_links(marker.note_ids, self._notes_by_id))
        self.info_object.setText(self._format_links(marker.object_ids, self._objects_by_id))
        self.info_file.setText(self._format_file_links(marker.file_ids, self._files_by_id))
        self.info_map.setText(self._format_links(marker.map_ids, self._maps_by_id))
        self.info_marker.setText(self._format_links(marker.marker_ids, self._markers_by_id))
        self.info_description.setText(self._format_value(marker.description))
        self.info_important.setText(self._format_value(marker.properties))
        self._apply_marker_type_info(marker)
        self._update_info_preview(marker)

    def _apply_marker_type_info(self, marker: Marker) -> None:
        # Обновляем данные по типу маркера в инфо-панели.
        option = marker_type_for_color(marker.color)
        self.info_marker_type_value.setText(option.label)
        pixmap = marker_type_pixmap(option, self.info_marker_type_preview.size())
        if pixmap is not None:
            self.info_marker_type_preview.setPixmap(pixmap)
            self.info_marker_type_preview.setText("")
        else:
            self.info_marker_type_preview.setPixmap(QPixmap())
            self.info_marker_type_preview.setText(option.label)
        self.info_marker_type_preview.setToolTip(option.label)

    def _info_widgets_alive(self) -> bool:
        # Проверяем, что виджеты инфо-панели ещё существуют.
        return bool(
            isValid(self.info_panel)
            and isValid(self.info_name)
            and isValid(self.info_preview)
            and isValid(self.info_marker_type_preview)
        )

    def _update_info_preview(self, marker: Marker) -> None:
        # Обновляем превью изображения маркера.
        if not self._info_widgets_alive():
            return
        preview_size = QSize(
            max(self.info_preview.width(), 1),
            max(self.info_preview.height(), 1),
        )
        pixmap = self._load_marker_preview(marker, preview_size)
        if pixmap is not None:
            self.info_preview.setPixmap(pixmap)
            self.info_preview.setText("")
        else:
            self.info_preview.setPixmap(QPixmap())
            if marker.image_path:
                self.info_preview.setText("Изображение недоступно")
            else:
                self.info_preview.setText("Нет изображения")
        self.info_preview.setToolTip(marker.image_path or "")

    def _load_marker_preview(self, marker: Marker, target: QSize) -> QPixmap | None:
        # Загружаем превью изображения маркера для инфо-панели.
        image_path = (marker.image_path or "").strip()
        if not image_path:
            return None
        path = Path(image_path)
        file_path = path if path.is_file() else None
        if file_path is None:
            cloud_root = get_database().get_setting("cloud_storage_path", default="").strip()
            if cloud_root:
                candidate = Path(cloud_root) / image_path
                if candidate.is_file():
                    file_path = candidate
        if not file_path:
            return None
        pixmap = QPixmap(str(file_path))
        if pixmap.isNull():
            return None
        return pixmap.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    def resizeEvent(self, event) -> None:
        # Подстраиваем ширину панели в полноэкранном режиме.
        super().resizeEvent(event)
        if self._fullscreen_active:
            self._update_info_panel_width()

    def _load_attachment_sources(self) -> None:
        # Загружаем источники данных из базы и передаем их канве.
        tasks = self._db.fetch_tasks()
        projects = self._db.fetch_projects()
        notes = self._db.fetch_notes()
        objects = self._db.fetch_objects()
        files = self._db.fetch_cloud_files()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        self._tasks_by_id = {task.id: task for task in tasks}
        self._projects_by_id = {project.id: project for project in projects}
        self._notes_by_id = {note.id: note for note in notes}
        self._objects_by_id = {item.id: item for item in objects}
        self._files_by_id = {item.id: item for item in files}
        self._maps_by_id = {item.id: item for item in maps}
        self._markers_by_id = {item.id: item for item in markers}
        self.canvas.set_attachment_sources(tasks, projects, notes, objects, files, maps, markers)

    def load_map(self, map_id: int, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        # Загружаем карту и синхронизируем маркеры из базы.
        self._current_map_id = map_id
        self.canvas.set_tiles(tiles_path, tiles_h, tiles_w)
        markers = self._db.fetch_map_markers(map_id)
        if not markers:
            # Если маркеров нет, создаем дефолтные.
            defaults = self.canvas.default_markers()
            self.canvas.set_markers(defaults)
            for marker in defaults:
                self._sync_marker(marker)
            self.markersChanged.emit()
            return
        loaded = []
        # Преобразуем записи базы в объекты Marker.
        for marker in markers:
            loaded.append(
                Marker(
                    marker.id,
                    marker.name,
                    marker.x,
                    marker.y,
                    QColor(marker.color),
                    marker.type,
                    marker.size,
                    marker.description,
                    marker.properties,
                    marker.task_ids,
                    marker.project_ids,
                    marker.note_ids,
                    marker.object_ids,
                    marker.file_ids,
                    marker.map_ids,
                    marker.marker_ids,
                    marker.parent_path,
                    marker.image_path,
                )
            )
        self.canvas.set_markers(loaded)
        self.markersChanged.emit()

    def markers(self) -> List[Marker]:
        # Возвращаем текущие маркеры канвы.
        return self.canvas.markers()

    def focus_marker(self, marker: Marker, zoom_boost: float = 4.0) -> None:
        # Делегируем фокусировку на канву.
        self.canvas.focus_on_marker(marker, zoom_boost=zoom_boost)

    def _sync_marker(self, marker: Marker) -> None:
        # Сохраняем маркер в базе, если карта выбрана.
        if self._current_map_id is None:
            return
        self._db.upsert_map_marker(
            marker_id=marker.id,
            map_id=self._current_map_id,
            name=marker.name,
            x=marker.x,
            y=marker.y,
            color=marker.color.name(),
            marker_type=marker.type,
            size=marker.size,
            description=marker.description,
            properties=marker.properties,
            task_ids=marker.task_ids,
            project_ids=marker.project_ids,
            note_ids=marker.note_ids,
            object_ids=marker.object_ids,
            file_ids=marker.file_ids,
            map_ids=marker.map_ids,
            marker_ids=marker.marker_ids,
            parent_path=marker.parent_path,
            image_path=marker.image_path,
        )

    def _on_marker_added(self, marker: Marker) -> None:
        # Реакция на добавление маркера.
        self._sync_marker(marker)
        self.markersChanged.emit()
        if self.canvas.tool() == MapTool.ADD_MARKER:
            self._set_tool(MapTool.SELECT)

    def _on_marker_updated(self, marker: Marker) -> None:
        # Реакция на обновление маркера.
        self._sync_marker(marker)
        if self._info_marker_id == marker.id:
            self._apply_marker_info(marker)
        self.markersChanged.emit()

    def _on_marker_removed(self, marker_id: int) -> None:
        # Удаляем маркер из базы по идентификатору.
        if self._current_map_id is None:
            return
        self._db.delete_map_marker(marker_id)
        self.markersChanged.emit()

    def _format_value(self, value: str) -> str:
        # Приводим значение к отображаемому виду.
        text = (value or "").strip()
        return text if text else "—"

    def _format_links(self, item_ids: List[int], source: dict) -> str:
        # Формируем строку с названиями привязанных сущностей.
        if not item_ids:
            return "—"
        titles = []
        for item_id in item_ids:
            item = source.get(item_id)
            if not item:
                titles.append("не найдено")
                continue
            title = getattr(item, "title", None) or getattr(item, "name", None) or getattr(item, "rel_path", "—")
            titles.append(title)
        return ", ".join(titles)

    def _format_file_links(self, item_ids: List[int], source: dict) -> str:
        # Формируем кликабельные ссылки для изображений.
        if not item_ids:
            return "—"
        parts = []
        for item_id in item_ids:
            item = source.get(item_id)
            if not item:
                parts.append("не найдено")
                continue
            title = getattr(item, "title", None) or getattr(item, "name", None) or getattr(item, "rel_path", "—")
            safe_title = html.escape(title)
            if getattr(item, "is_image", False):
                parts.append(f'<a href="file:{item_id}">{safe_title}</a>')
            else:
                parts.append(safe_title)
        return "<br>".join(parts)

    def _handle_info_link(self, link: str) -> None:
        # Обрабатываем клики по ссылкам файлов в панели данных.
        if ":" not in link:
            return
        kind, item_id = link.split(":", 1)
        if kind != "file":
            return
        try:
            parsed_id = int(item_id)
        except ValueError:
            return
        self._open_attachment_view(kind, parsed_id)

    def _open_attachment_view(self, kind: str, item_id: int) -> None:
        # Делегируем открытие вложения канве карты.
        self.canvas._open_attachment_view(kind, item_id)


class MapsListWorkspace(QWidget):
    def __init__(self, parent=None):
        # Инициализируем рабочую область списка карт.
        super().__init__(parent)
        # Основные настройки рабочей области списка карт.
        self.setObjectName("MapsWorkspace")

        self._db = get_database()
        self._map_fullscreen_active = False

        # Вертикальная компоновка всего экрана.
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        # Страница со списком карт.
        list_page = QWidget()
        list_layout = QVBoxLayout(list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(10)

        # Блок создания новой карты.
        create = QFrame()
        create.setObjectName("MapsCreateBar")
        create_layout = QHBoxLayout(create)
        create_layout.setContentsMargins(10, 8, 10, 8)
        create_layout.setSpacing(8)

        self.new_title = QLineEdit()
        self.new_title.setPlaceholderText("Название карты…")

        self.new_desc = QLineEdit()
        self.new_desc.setPlaceholderText("Описание…")

        self.new_project = QComboBox()
        self.new_project.setFixedWidth(200)
        self._refresh_projects()

        self.new_tiles_path = QLineEdit()
        self.new_tiles_path.setPlaceholderText("Каталог хранения тайлов…")

        self.btn_tiles_path = QToolButton()
        self.btn_tiles_path.setText("…")
        self.btn_tiles_path.setCursor(Qt.PointingHandCursor)
        self.btn_tiles_path.clicked.connect(self._on_pick_tiles_path)

        # Блок выбора размеров тайлов.
        tiles_block = QFrame()
        tiles_block.setObjectName("MapsTilesBlock")
        tiles_layout = QHBoxLayout(tiles_block)
        tiles_layout.setContentsMargins(6, 2, 6, 2)
        tiles_layout.setSpacing(6)

        tiles_label = QLabel("Тайлы")
        tiles_label.setObjectName("MapsTilesLabel")

        self.tiles_w = QSpinBox()
        self.tiles_w.setRange(1, 512)
        self.tiles_w.setValue(24)
        self.tiles_w.setFixedWidth(70)

        self.tiles_h = QSpinBox()
        self.tiles_h.setRange(1, 512)
        self.tiles_h.setValue(18)
        self.tiles_h.setFixedWidth(70)

        tiles_layout.addWidget(tiles_label)
        tiles_layout.addWidget(QLabel("W"))
        tiles_layout.addWidget(self.tiles_w)
        tiles_layout.addWidget(QLabel("H"))
        tiles_layout.addWidget(self.tiles_h)

        self.btn_add = QToolButton()
        self.btn_add.setText("Создать")
        self.btn_add.setCursor(Qt.PointingHandCursor)

        create_layout.addWidget(self.new_title, 1)
        create_layout.addWidget(self.new_desc, 1)
        create_layout.addWidget(self.new_project)
        create_layout.addWidget(self.new_tiles_path, 1)
        create_layout.addWidget(self.btn_tiles_path)
        create_layout.addWidget(tiles_block)
        create_layout.addWidget(self.btn_add)

        list_layout.addWidget(create)

        # Верхняя панель фильтров.
        top = QFrame()
        top.setObjectName("MapsTopbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str) -> QToolButton:
            # Создает кнопку вкладки фильтра.
            b = QToolButton()
            b.setText(text)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setAutoRaise(True)
            self.tabs_group.addButton(b)
            return b

        self.tab_all = tab_btn("Все")
        self.tab_project = tab_btn("Проект")
        self.tab_all.setChecked(True)

        top_layout.addWidget(self.tab_all)
        top_layout.addWidget(self.tab_project)

        top_layout.addSpacing(12)

        self.filter_project = QComboBox()
        self.filter_project.setFixedWidth(200)
        self.filter_project.addItem("Все проекты")
        self.filter_project.addItems(self._project_titles())
        top_layout.addWidget(self.filter_project)

        top_layout.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)
        top_layout.addWidget(self.search)

        list_layout.addWidget(top)

        # Список карт.
        self.list = MapsListView()
        self.list.setObjectName("MapsList")
        self.list.setUniformItemSizes(False)
        self.list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SingleSelection)
        list_layout.addWidget(self.list, 1)

        self.model = MapsModel(self)
        self.list.setModel(self.model)

        self.delegate = MapsItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        for b in self.tabs_group.buttons():
            b.clicked.connect(self._on_tab_changed)

        self.search.textChanged.connect(self.model.set_search)
        self.filter_project.currentTextChanged.connect(self._on_project_changed)
        self.btn_add.clicked.connect(self._on_create_map)
        self.new_title.returnPressed.connect(self._on_create_map)
        self.list.editRequested.connect(self._on_edit_map)
        self.list.openRequested.connect(self._on_open_map)
        # Страница редактора карты.
        self.editor_workspace = MapEditorWorkspace()
        self.editor_workspace.fullscreenToggled.connect(self._on_map_fullscreen_toggled)
        self.editor_workspace.markersChanged.connect(self._refresh_marker_search)
        self.editor_header = QFrame()
        self.editor_header.setObjectName("MapEditorHeader")
        header_layout = QHBoxLayout(self.editor_header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        self.btn_back = QToolButton()
        self.btn_back.setText("Назад к списку")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(list_page))
        self.map_title = QLabel("Редактор карты")
        self.map_title.setObjectName("MapEditorTitle")
        header_layout.addWidget(self.btn_back)
        # Поиск по маркерам на карте.
        self.marker_search = QLineEdit()
        self.marker_search.setObjectName("MapMarkerSearch")
        self.marker_search.setPlaceholderText("Поиск меток…")
        self.marker_search.setFixedWidth(260)
        self.marker_search.setClearButtonEnabled(True)
        self.marker_search.installEventFilter(self)

        # Выпадающий список результатов поиска.
        self.marker_search_results = QListView(self)
        self.marker_search_results.setObjectName("MapMarkerSearchResults")
        self.marker_search_results.setFixedWidth(260)
        self.marker_search_results.setFixedHeight(180)
        self.marker_search_results.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.marker_search_results.setVisible(False)
        self.marker_search_results.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.marker_search_model = MarkerSearchModel(self.marker_search_results)
        self.marker_search_results.setModel(self.marker_search_model)

        search_container = QFrame()
        search_container.setObjectName("MapMarkerSearchContainer")
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        search_layout.addWidget(self.marker_search)
        header_layout.addWidget(search_container)
        header_layout.addWidget(self.map_title)
        header_layout.addStretch(1)

        self.marker_search.textChanged.connect(self._on_marker_search_changed)
        self.marker_search_results.clicked.connect(self._on_marker_search_selected)

        editor_page = QWidget()
        editor_layout = QVBoxLayout(editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)
        editor_layout.addWidget(self.editor_header)
        editor_layout.addWidget(self.editor_workspace, 1)

        self.stack.addWidget(list_page)
        self.stack.addWidget(editor_page)
        self.stack.setCurrentWidget(list_page)

        # Оверлей загрузки карты.
        self.loading_overlay = QFrame(self)
        self.loading_overlay.setObjectName("MapsLoadingOverlay")
        self.loading_overlay.setVisible(False)
        self.loading_overlay.setAttribute(Qt.WA_StyledBackground, True)
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.addStretch(1)

        overlay_card = QFrame()
        overlay_card.setObjectName("MapsLoadingCard")
        overlay_card_layout = QVBoxLayout(overlay_card)
        overlay_card_layout.setContentsMargins(24, 18, 24, 20)
        overlay_card_layout.setSpacing(12)

        self.loading_title = QLabel("Загрузка карты…")
        self.loading_title.setObjectName("MapsLoadingTitle")
        self.loading_hint = QLabel("Подготавливаем тайлы и маркеры")
        self.loading_hint.setObjectName("MapsLoadingHint")
        self.loading_hint.setAlignment(Qt.AlignCenter)

        self.loading_bar = QProgressBar()
        self.loading_bar.setObjectName("MapsLoadingBar")
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setFixedHeight(8)

        overlay_card_layout.addWidget(self.loading_title, alignment=Qt.AlignCenter)
        overlay_card_layout.addWidget(self.loading_hint, alignment=Qt.AlignCenter)
        overlay_card_layout.addWidget(self.loading_bar)

        overlay_layout.addWidget(overlay_card, alignment=Qt.AlignCenter)
        overlay_layout.addStretch(1)

        # Стили рабочей области.
        self.setStyleSheet("""
            QWidget#MapsWorkspace { background: #16171a; }

            QFrame#MapsCreateBar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QFrame#MapsCreateBar QLineEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                color: #e6e6e6;
            }

            QFrame#MapsCreateBar QComboBox {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#MapsCreateBar QFrame#MapsTilesBlock {
                background: #131417;
                border: 1px solid #2a2b2f;
                border-radius: 8px;
            }

            QFrame#MapsCreateBar QFrame#MapsTilesBlock QLabel {
                color: #cfcfcf;
                padding: 0 4px;
            }

            QFrame#MapsCreateBar QFrame#MapsTilesBlock QSpinBox {
                background: transparent;
                border: none;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#MapsCreateBar QToolButton {
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QFrame#MapsCreateBar QToolButton:hover { background: #34363b; }

            QFrame#MapsTopbar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QToolButton {
                color: #cfcfcf;
                border: none;
                padding: 6px 8px;
            }
            QToolButton:checked {
                background: #2a2b2f;
            }

            QComboBox, QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
            }

            QListView#MapsList {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }

            QFrame#MapEditorHeader {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }

            QFrame#MapEditorHeader QToolButton {
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
                color: #e6e6e6;
            }

            QLineEdit#MapMarkerSearch {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }

            QListView#MapMarkerSearchResults {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
                color: #e6e6e6;
            }

            QListView#MapMarkerSearchResults::item {
                padding: 6px 8px;
            }

            QListView#MapMarkerSearchResults::item:selected {
                background: #2a2b2f;
            }

            QLabel#MapEditorTitle {
                color: #e6e6e6;
                font-size: 14px;
                font-weight: 600;
            }

            QFrame#MapsLoadingOverlay {
                background: rgba(8, 9, 12, 0.75);
            }

            QFrame#MapsLoadingCard {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 12px;
            }

            QLabel#MapsLoadingTitle {
                color: #f2f2f2;
                font-size: 16px;
                font-weight: 600;
            }

            QLabel#MapsLoadingHint {
                color: #cfcfcf;
                font-size: 12px;
            }

            QProgressBar#MapsLoadingBar {
                background: #2a2b2f;
                border: none;
                border-radius: 4px;
            }

            QProgressBar#MapsLoadingBar::chunk {
                background: #5fa8ff;
                border-radius: 4px;
            }
        """)

    def resizeEvent(self, event):
        # Обновляем геометрию оверлея и позицию выпадающего списка.
        super().resizeEvent(event)
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.setGeometry(self.rect())
        if hasattr(self, "marker_search_results") and self.marker_search_results.isVisible():
            self._position_marker_search_results()

    def _project_titles(self) -> List[str]:
        # Получаем список названий проектов для фильтра.
        projects = get_database().fetch_projects()
        titles = sorted({p.title for p in projects})
        return titles

    def _refresh_projects(self) -> None:
        # Обновляем список проектов в комбобоксе создания.
        self.new_project.clear()
        titles = self._project_titles()
        self.new_project.addItems(titles or ["Без проекта"])

    def _cloud_storage_root(self) -> str:
        # Корневая папка облачного хранилища.
        return self._db.get_setting("cloud_storage_path", default="")

    def _on_pick_tiles_path(self) -> None:
        # Открываем диалог выбора каталога тайлов.
        current = self.new_tiles_path.text().strip()
        start_dir = current or self._cloud_storage_root() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выберите каталог хранения тайлов",
            start_dir,
        )
        if not selected:
            return
        self.new_tiles_path.setText(selected)

    def _on_tab_changed(self) -> None:
        # Применяем фильтрацию по вкладкам.
        if self.tab_project.isChecked():
            current = self.filter_project.currentText()
            if current != "Все проекты":
                self.model.set_project_filter(current)
                return
        self.model.set_project_filter(None)

    def _on_project_changed(self, text: str) -> None:
        # Реагируем на смену проекта в фильтре.
        if self.tab_project.isChecked() and text != "Все проекты":
            self.model.set_project_filter(text)
        else:
            self.model.set_project_filter(None)

    def set_project_filter(self, project: Optional[str]) -> None:
        """Устанавливает фильтр карт из внешней навигации."""
        # Синхронизируем фильтр и вкладки с внешним выбором.
        if project:
            self.tab_project.setChecked(True)
            idx = self.filter_project.findText(project)
            if idx >= 0:
                self.filter_project.setCurrentIndex(idx)
            else:
                self.filter_project.addItem(project)
                self.filter_project.setCurrentText(project)
            self.model.set_project_filter(project)
        else:
            self.tab_all.setChecked(True)
            self.filter_project.setCurrentIndex(0)
            self.model.set_project_filter(None)

    def _on_create_map(self) -> None:
        # Создаем карту по введенным данным.
        self.model.add_map(
            self.new_title.text(),
            self.new_desc.text(),
            self.new_project.currentText(),
            self.new_tiles_path.text(),
            self.tiles_h.value(),
            self.tiles_w.value(),
        )
        self.new_title.clear()
        self.new_desc.clear()
        self.new_tiles_path.clear()
        self.new_title.setFocus()

    def _on_edit_map(self, index: QModelIndex) -> None:
        # Открываем диалог редактирования выбранной карты.
        if not index.isValid():
            return
        map_row = MapRow(
            id=index.data(MapRoles.Id),
            title=index.data(MapRoles.Title) or "",
            description=index.data(MapRoles.Description) or "",
            project=index.data(MapRoles.Project) or "",
            tiles_path=index.data(MapRoles.TilesPath) or "",
            tiles_h=index.data(MapRoles.TilesHeight) or 0,
            tiles_w=index.data(MapRoles.TilesWidth) or 0,
        )
        dialog = MapEditDialog(map_row, parent=self)
        if dialog.exec() == QDialog.Accepted:
            values = dialog.values()
            self.model.update_map(
                map_row.id,
                values["title"],
                values["description"],
                values["project"],
                values["tiles_path"],
                values["tiles_h"],
                values["tiles_w"],
            )

    def _on_open_map(self, index: QModelIndex) -> None:
        # Открываем редактор карты и запускаем загрузку.
        if not index.isValid():
            return
        map_id = index.data(MapRoles.Id)
        title = index.data(MapRoles.Title) or "Карта"
        project = index.data(MapRoles.Project) or ""
        if project:
            self.map_title.setText(f"{title} · {project}")
            self.loading_title.setText(f"Загрузка карты «{title}»")
        else:
            self.map_title.setText(title)
            self.loading_title.setText(f"Загрузка карты «{title}»")
        self.stack.setCurrentIndex(1)
        self.marker_search.clear()
        self.marker_search_results.setVisible(False)
        tiles_path = index.data(MapRoles.TilesPath) or ""
        tiles_height = index.data(MapRoles.TilesHeight) or 0
        tiles_width = index.data(MapRoles.TilesWidth) or 0
        self._show_loading_overlay()
        QTimer.singleShot(
            0,
            lambda: self._load_map_with_overlay(
                map_id,
                tiles_path,
                tiles_height,
                tiles_width,
            ),
        )

    def _load_map_with_overlay(self, map_id: int, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        # Загружаем карту и скрываем оверлей после подготовки.
        self.editor_workspace.load_map(map_id, tiles_path, tiles_h, tiles_w)
        QTimer.singleShot(0, self._hide_loading_overlay)

    def _show_loading_overlay(self) -> None:
        # Показываем оверлей ожидания.
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.raise_()
        self.loading_overlay.setVisible(True)
        self.loading_overlay.repaint()

    def _hide_loading_overlay(self) -> None:
        # Скрываем оверлей ожидания.
        self.loading_overlay.setVisible(False)

    def _on_marker_search_changed(self, text: str) -> None:
        # Фильтруем маркеры по строке поиска.
        query = (text or "").strip()
        if not query:
            self.marker_search_model.set_markers([])
            self.marker_search_results.setVisible(False)
            return
        matches = self._filter_markers(query)
        self.marker_search_model.set_markers(matches)
        if matches:
            self._show_marker_search_results()
        else:
            self.marker_search_results.setVisible(False)

    def _refresh_marker_search(self) -> None:
        # Обновляем результаты поиска, если строка не пуста.
        text = self.marker_search.text()
        if text.strip():
            self._on_marker_search_changed(text)

    def _filter_markers(self, query: str) -> List[Marker]:
        # Возвращаем список маркеров, соответствующих запросу.
        needle = query.lower()
        matches = []
        for marker in self.editor_workspace.markers():
            hay = f"{marker.name} {marker.type} {marker.description} {marker.properties}".lower()
            if needle in hay:
                matches.append(marker)
        return matches

    def _on_marker_search_selected(self, index: QModelIndex) -> None:
        # Фокусируемся на выбранном маркере.
        marker = index.data(MarkerSearchModel.MarkerRole)
        if not marker:
            return
        self.editor_workspace.focus_marker(marker, zoom_boost=4.0)
        self.marker_search_results.setVisible(False)

    def _on_map_fullscreen_toggled(self, enabled: bool) -> None:
        # Переключаем полноэкранный режим у окна или локально.
        window = self.window()
        if window and hasattr(window, "set_map_fullscreen"):
            window.set_map_fullscreen(enabled)
        else:
            self.set_map_fullscreen_state(enabled)

    def set_map_fullscreen_state(self, enabled: bool) -> None:
        # Сохраняем локальное состояние полноэкранного режима.
        if self._map_fullscreen_active == enabled:
            return
        self._map_fullscreen_active = enabled
        self.editor_header.setVisible(True)
        if enabled:
            self.marker_search_results.setVisible(False)
        self.editor_workspace.set_fullscreen_state(enabled)

    def set_nav_collapsed_state(self, collapsed: bool) -> None:
        # Обновляем параметры редактора карты при сворачивании навигации.
        self.editor_workspace.set_nav_collapsed_state(collapsed)

    def _show_marker_search_results(self) -> None:
        # Показываем выпадающий список результатов.
        self._position_marker_search_results()
        self.marker_search_results.setVisible(True)
        self.marker_search_results.raise_()

    def _position_marker_search_results(self) -> None:
        # Позиционируем результаты под полем поиска.
        if not self.marker_search.isVisible():
            return
        self.marker_search_results.setFixedWidth(self.marker_search.width())
        global_pos = self.marker_search.mapToGlobal(QPoint(0, self.marker_search.height()))
        self.marker_search_results.move(global_pos)

    def _clear_marker_search(self) -> None:
        # Очищаем строку поиска и скрываем результаты.
        self.marker_search.clear()
        self.marker_search_results.setVisible(False)

    def eventFilter(self, obj, event) -> bool:
        # Обрабатываем Esc в поле поиска, чтобы скрыть результаты.
        if obj is self.marker_search and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                if self.marker_search.text().strip() or self.marker_search_results.isVisible():
                    self._clear_marker_search()
                    return True
        return super().eventFilter(obj, event)
