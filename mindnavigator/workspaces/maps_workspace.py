from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional

import qtawesome as qta
from PySide6.QtCore import (
    Qt, QSize, QRect, QAbstractListModel, QModelIndex, QPoint, QPointF, QRectF, Signal, QTimer
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
    QFileDialog, QColorDialog, QDoubleSpinBox, QPlainTextEdit, QProgressBar
)

from mindnavigator.storage import get_database
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND
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
        super().__init__(parent)
        self._items: List[MapRow] = []
        self._all_items: List[MapRow] = []
        self._search = ""
        self._project_filter: Optional[str] = None
        self._db = get_database()
        self._load_maps()

    def _load_maps(self) -> None:
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
        self._rebuild()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int):
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
        title = (title or "").strip()
        if not title:
            return
        try:
            created = self._db.create_map(title, description, project, tiles_path, tiles_h, tiles_w)
        except ValueError:
            return
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
        title = (title or "").strip()
        if not title:
            return
        try:
            updated_map = self._db.update_map(map_id, title, description, project, tiles_path, tiles_h, tiles_w)
        except ValueError:
            return
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
        self._rebuild()

    def set_search(self, text: str) -> None:
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_project_filter(self, project: Optional[str]) -> None:
        self._project_filter = project
        self._rebuild()

    def _rebuild(self) -> None:
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
        super().__init__(parent)
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

        self._icon_map = qta.icon("fa5s.map-marked-alt", color="#cfcfcf")

    def sizeHint(self, option, index):
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

        layout = self._row_layout(r)
        title = index.data(MapRoles.Title) or ""
        desc = index.data(MapRoles.Description) or ""
        project = index.data(MapRoles.Project) or ""
        tiles_h = index.data(MapRoles.TilesHeight) or 0
        tiles_w = index.data(MapRoles.TilesWidth) or 0

        icon_rect = layout["icon"]
        self._icon_map.paint(painter, icon_rect, Qt.AlignCenter)

        painter.setPen(self.C_TEXT)
        painter.setFont(self._font_title)
        painter.drawText(layout["title"], Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, title)

        if desc:
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_desc)
            painter.drawText(layout["desc"], Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, desc)

        self._draw_pill(painter, layout["project"], project)
        self._draw_pill(painter, layout["tiles"], f"Тайлы: {tiles_w}×{tiles_h}")
        self._draw_button(painter, layout["edit_btn"], "Редактировать свойства")
        self._draw_button(painter, layout["open_btn"], "Перейти к карте")

        painter.restore()

    def _row_layout(self, r: QRect) -> dict:
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
        painter.save()
        painter.setPen(self.C_PILL_BORDER)
        painter.setBrush(self.C_PILL)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(self.C_TEXT)
        painter.setFont(self._font_pill)
        painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()

    def _draw_button(self, painter: QPainter, rect: QRect, text: str) -> None:
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
        super().mousePressEvent(event)


class MapEditDialog(QDialog):
    def __init__(self, map_row: MapRow, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование карты")
        self.setObjectName("MapEditDialog")
        self.setMinimumWidth(460)
        self.setMinimumHeight(400)

        self._db = get_database()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Редактирование карты")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

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

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        projects = get_database().fetch_projects()
        titles = sorted({p.title for p in projects})
        return titles or ["Без проекта"]

    def _cloud_storage_root(self) -> str:
        return self._db.get_setting("cloud_storage_path", default="")

    def _on_pick_tiles_path(self) -> None:
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
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Проверка", "Введите название карты.")
            return
        self.accept()

    def values(self) -> dict:
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
    task_id: Optional[int] = None
    project_id: Optional[int] = None
    note_id: Optional[int] = None
    object_id: Optional[int] = None


class MapCanvas(QWidget):
    markerSelected = Signal(object)
    markerAdded = Signal(object)
    markerRemoved = Signal(int)
    markerUpdated = Signal(object)

    GRID_COLOR = QColor(70, 74, 82, 120)
    GRID_TEXT = QColor(150, 155, 160, 180)
    DEFAULT_MARKER_SIZE = 8.0
    MIN_MARKER_SIZE = 2.0
    MAX_MARKER_SIZE = 40.0
    RESIZE_FRAME_PADDING = 8.0
    HANDLE_PIXEL_SIZE = 12.0

    def __init__(self, parent=None):
        super().__init__(parent)
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
        self._tasks_by_id = {}
        self._projects_by_id = {}
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._seed_markers()

    @staticmethod
    def default_markers() -> List[Marker]:
        return [
            Marker(1, "Outpost", 320, 240, QColor("#57c7ff"), "Base", MapCanvas.DEFAULT_MARKER_SIZE, "Опорный пункт"),
            Marker(2, "Echo", 520, 360, QColor("#8be26f"), "Point", MapCanvas.DEFAULT_MARKER_SIZE, "Контрольная точка"),
            Marker(3, "Delta", 220, 420, QColor("#f2a05d"), "Risk", MapCanvas.DEFAULT_MARKER_SIZE, "Зона риска"),
        ]

    def _seed_markers(self) -> None:
        self._markers = self.default_markers()
        self._next_id = max((m.id for m in self._markers), default=0) + 1

    def set_markers(self, markers: List[Marker]) -> None:
        self._markers = list(markers)
        self._selected = None
        self._resize_marker_id = None
        self._next_id = max((m.id for m in self._markers), default=0) + 1
        self.markerSelected.emit(None)
        self.update()

    def markers(self) -> List[Marker]:
        return list(self._markers)

    def set_attachment_sources(self, tasks, projects, notes, objects) -> None:
        self._tasks = list(tasks)
        self._projects = list(projects)
        self._notes = list(notes)
        self._objects = list(objects)
        self._tasks_by_id = {item.id: item for item in tasks}
        self._projects_by_id = {item.id: item for item in projects}
        self._notes_by_id = {item.id: item for item in notes}
        self._objects_by_id = {item.id: item for item in objects}

    def _open_attachment_view(self, kind: str, item_id: int) -> None:
        sources = {
            "task": self._tasks_by_id,
            "project": self._projects_by_id,
            "note": self._notes_by_id,
            "object": self._objects_by_id,
        }
        item = sources.get(kind, {}).get(item_id)
        if not item:
            QMessageBox.warning(self, "Элемент не найден", "Не удалось найти выбранный элемент.")
            return

        dialog = QDialog(self)
        dialog.setObjectName("MapAttachmentDialog")
        dialog.setWindowTitle("Просмотр вложения")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        def add_row(label: str, value: str, wrap: bool = False) -> None:
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

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

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
        self._tool = tool
        self._preview_pos = None
        self.update()

    def set_grid_enabled(self, enabled: bool) -> None:
        self._grid_enabled = enabled
        self.update()

    def set_tiles(self, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        self._tiles_path = (tiles_path or "").strip()
        self._tiles_h = max(0, int(tiles_h or 0))
        self._tiles_w = max(0, int(tiles_w or 0))
        self._load_tiles()
        self.reset_view()
        self.update()

    def reset_view(self) -> None:
        fit_scale = self._fit_scale_to_view()
        self._min_scale = min(self._absolute_min_scale, fit_scale)
        self._scale = min(1.0, fit_scale) if fit_scale > 0 else 1.0
        self._offset = self._center_offset_for_scale(self._scale)

    def _content_bounds(self) -> QRectF:
        map_bounds = self._map_bounds()
        if not map_bounds.isNull():
            return map_bounds
        if not self._background.isNull():
            return QRectF(QPointF(0, 0), self._background.size())
        return QRectF(0, 0, 1200, 800)

    def _fit_scale_to_view(self) -> float:
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
        bounds = self._content_bounds()
        center_world = bounds.center()
        view_center = QPointF(self.width() / 2, self.height() / 2)
        return view_center - center_world * scale

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#1a1c20"))

        painter.save()
        painter.translate(self._offset)
        painter.scale(self._scale, self._scale)

        self._draw_background(painter)
        if self._grid_enabled:
            self._draw_grid(painter)
        self._draw_markers(painter)
        if self._preview_pos and self._tool == MapTool.ADD_MARKER:
            self._draw_preview(painter)

        painter.restore()

    def resizeEvent(self, event):
        world_center = self._map_to_world(QPointF(self.width() / 2, self.height() / 2))
        super().resizeEvent(event)
        fit_scale = self._fit_scale_to_view()
        self._min_scale = min(self._absolute_min_scale, fit_scale)
        if self._scale < self._min_scale:
            self._scale = self._min_scale
        self._offset = QPointF(self.width() / 2, self.height() / 2) - world_center * self._scale

    def _draw_background(self, painter: QPainter) -> None:
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

        for x in range(left, right + spacing_x, spacing_x):
            painter.drawLine(x, top, x, bottom)
        for y in range(top, bottom + spacing_y, spacing_y):
            painter.drawLine(left, y, right, y)

        painter.setPen(self.GRID_TEXT)
        painter.setFont(QFont("Segoe UI", 8))
        for x in range(left, right + spacing_x, spacing_x):
            painter.drawText(QPointF(x + 4, top + 14), f"{x}")
        for y in range(top, bottom + spacing_y, spacing_y):
            painter.drawText(QPointF(left + 4, y - 4), f"{y}")

    def _draw_markers(self, painter: QPainter) -> None:
        self._resize_handle_regions = {}
        for marker in self._markers:
            is_selected = self._selected and marker.id == self._selected.id
            radius = marker.size + (2.0 if is_selected else 0.0)
            painter.setBrush(marker.color)
            painter.setPen(QPen(QColor("#111111"), max(1.0, 1.0 / self._scale)))
            painter.drawEllipse(QPointF(marker.x, marker.y), radius, radius)
            if is_selected:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor("#dfe7f0"), max(1.0, 1.4 / self._scale)))
                painter.drawEllipse(QPointF(marker.x, marker.y), radius + 2, radius + 2)
            painter.setPen(QColor("#e5e5e5"))
            font_size = max(6.0, min(18.0, 8.0 * (marker.size / self.DEFAULT_MARKER_SIZE)))
            painter.setFont(QFont("Segoe UI", font_size))
            painter.drawText(
                QPointF(marker.x + marker.size + 6.0, marker.y - (marker.size + 2.0)),
                marker.name,
            )
            if self._resize_marker_id == marker.id:
                self._draw_resize_handles(painter, marker)

    def _draw_preview(self, painter: QPainter) -> None:
        if not self._preview_pos:
            return
        painter.setPen(QPen(QColor("#cfd8dc"), 1.0 / self._scale))
        painter.setBrush(QColor(200, 200, 200, 60))
        painter.drawEllipse(self._preview_pos, self.DEFAULT_MARKER_SIZE, self.DEFAULT_MARKER_SIZE)

    def _world_view_rect(self) -> QRectF:
        inv_scale = 1.0 / self._scale
        top_left = (QPointF(0, 0) - self._offset) * inv_scale
        bottom_right = (QPointF(self.width(), self.height()) - self._offset) * inv_scale
        return QRectF(top_left, bottom_right).normalized()

    def _map_to_world(self, pos: QPointF) -> QPointF:
        pos_f = QPointF(pos)
        return (pos_f - self._offset) / self._scale

    def _map_from_world(self, pos: QPointF) -> QPointF:
        return pos * self._scale + self._offset

    def _map_bounds(self) -> QRectF:
        if self._tiles_w <= 0 or self._tiles_h <= 0:
            return QRectF()
        width = self._tile_size.width() * self._tiles_w
        height = self._tile_size.height() * self._tiles_h
        return QRectF(0, 0, float(width), float(height))

    def _load_tiles(self) -> None:
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
        for marker in self._markers:
            if marker.id == marker_id:
                return marker
        return None

    def _set_marker(self, updated: Marker) -> None:
        self._markers = [updated if m.id == updated.id else m for m in self._markers]
        self._selected = updated
        self.markerSelected.emit(updated)
        self.markerUpdated.emit(updated)
        self.update()

    def _draw_resize_handles(self, painter: QPainter, marker: Marker) -> None:
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

    def _marker_label_rect(self, marker: Marker) -> QRectF:
        font_size = max(6.0, min(18.0, 8.0 * (marker.size / self.DEFAULT_MARKER_SIZE)))
        font = QFont("Segoe UI", font_size)
        metrics = QFontMetricsF(font)
        text = marker.name
        width = metrics.horizontalAdvance(text)
        height = metrics.height()
        pos = QPointF(marker.x + marker.size + 6.0, marker.y - (marker.size + 2.0))
        top = pos.y() - metrics.ascent()
        return QRectF(pos.x(), top, width, height)

    def _selection_rect(self, marker: Marker) -> QRectF:
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
        for direction, rect in self._resize_handle_regions.items():
            if rect.contains(world_pos):
                return direction
        return None

    def _resize_handle_cursor(self, handle: str) -> Qt.CursorShape:
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
        target_scale = min(self._max_scale, max(self._min_scale, self._scale * 1.4))
        view_center = QPointF(self.width() / 2, self.height() / 2)
        self._scale = target_scale
        self._offset = view_center - QPointF(marker.x, marker.y) * self._scale
        self.update()

    def focus_on_marker(self, marker: Marker, zoom_boost: float = 4.0) -> None:
        target_scale = min(self._max_scale, max(self._min_scale, self._scale + zoom_boost))
        view_center = QPointF(self.width() / 2, self.height() / 2)
        self._selected = marker
        self.markerSelected.emit(marker)
        self._scale = target_scale
        self._offset = view_center - QPointF(marker.x, marker.y) * self._scale
        self.setFocus(Qt.OtherFocusReason)
        self.update()

    def _adjust_marker_size(self, marker: Marker, delta: float) -> None:
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
                marker.task_id,
                marker.project_id,
                marker.note_id,
                marker.object_id,
            )
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._open_context_menu(event.pos())
            return

        if event.button() == Qt.LeftButton:
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
                marker = self._marker_by_id(self._resize_marker_id)
                if marker and self._selection_rect(marker).contains(world_pos):
                    self._resize_dragging = True
                    self._resize_drag_offset = world_pos - QPointF(marker.x, marker.y)
                    return
                self._resize_marker_id = None
                self._active_resize_handle = None
            if self._tool == MapTool.ADD_MARKER:
                self._add_marker(world_pos)
                return
            marker = self._marker_at(world_pos)
            if marker:
                self._selected = marker
                self.markerSelected.emit(marker)
                self._dragging_marker_id = marker.id
                self.update()
                return
            self._selected = None
            self.markerSelected.emit(None)
            self._dragging_marker_id = None
            self._panning = True
            self._last_pos = event.position()
            self.update()

    def mouseMoveEvent(self, event):
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
                        marker.task_id,
                        marker.project_id,
                        marker.note_id,
                        marker.object_id,
                    )
                    self._set_marker(updated)
                    return
            if marker and self._resize_dragging:
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
                    marker.task_id,
                    marker.project_id,
                    marker.note_id,
                    marker.object_id,
                )
                self._set_marker(updated)
                return
            if marker:
                handle = self._resize_handle_at(world_pos)
                if handle:
                    self.setCursor(self._resize_handle_cursor(handle))
                    return
                if self._selection_rect(marker).contains(world_pos):
                    self.setCursor(Qt.SizeAllCursor)
                    return
            self.unsetCursor()
        if self._dragging_marker_id is not None and self._tool == MapTool.SELECT:
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
                    marker.task_id,
                    marker.project_id,
                    marker.note_id,
                    marker.object_id,
                )
                self._set_marker(updated)
                return
        if self._panning:
            delta = event.position() - self._last_pos
            self._offset += delta
            self._last_pos = event.position()
            self.update()
            return
        if self._tool == MapTool.ADD_MARKER:
            self._preview_pos = self._map_to_world(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._panning = False
            self._dragging_marker_id = None
            self._active_resize_handle = None
            self._resize_dragging = False

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            world_pos = self._map_to_world(event.position())
            marker = self._marker_at(world_pos)
            if marker:
                self._selected = marker
                self.markerSelected.emit(marker)
                self._zoom_to_marker(marker)
                return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            cursor_pos = event.position()
            world_pos = self._map_to_world(cursor_pos)
            marker = self._marker_at(world_pos)
            if marker:
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
        marker = Marker(
            self._next_id,
            f"Marker {self._next_id}",
            float(world_pos.x()),
            float(world_pos.y()),
            QColor("#8be26f"),
            "Point",
            self.DEFAULT_MARKER_SIZE,
            "",
            "",
            None,
            None,
            None,
            None,
        )
        self._next_id += 1
        self._markers.append(marker)
        self._selected = marker
        self.markerAdded.emit(marker)
        self.markerSelected.emit(marker)
        self._preview_pos = None
        self.update()

    def _remove_marker(self, marker: Marker) -> None:
        self._markers = [m for m in self._markers if m.id != marker.id]
        self.markerRemoved.emit(marker.id)
        if self._selected and self._selected.id == marker.id:
            self._selected = None
            self.markerSelected.emit(None)
        self.update()

    def _edit_marker(self, marker: Marker) -> None:
        def task_label(item) -> str:
            return f"{item.title} · {item.project_title}" if item.project_title else item.title

        def project_label(item) -> str:
            return f"{item.title} · {item.area}" if item.area else item.title

        def note_label(item) -> str:
            return f"{item.title} · {item.project}" if item.project else item.title

        def object_label(item) -> str:
            return f"{item.title} · {item.catalog}" if item.catalog else item.title

        def fill_combo(combo: QComboBox, items, current_id: Optional[int], label_builder) -> None:
            combo.clear()
            combo.addItem("— не выбрано —", None)
            for item in items:
                combo.addItem(label_builder(item), item.id)
            if current_id is None:
                combo.setCurrentIndex(0)
            else:
                idx = combo.findData(current_id)
                combo.setCurrentIndex(idx if idx >= 0 else 0)

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактирование маркера")
        dialog.setObjectName("MarkerEditDialog")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        name_edit = QLineEdit(marker.name)
        type_edit = QLineEdit(marker.type)
        size_edit = QDoubleSpinBox()
        size_edit.setRange(self.MIN_MARKER_SIZE, self.MAX_MARKER_SIZE)
        size_edit.setDecimals(1)
        size_edit.setSingleStep(0.5)
        size_edit.setValue(marker.size)
        resize_btn = QToolButton()
        resize_btn.setText("Изменить размер")
        resize_btn.setCursor(Qt.PointingHandCursor)
        size_row = QHBoxLayout()
        size_row.addWidget(size_edit)
        size_row.addWidget(resize_btn)
        size_row.addStretch(1)
        size_holder = QWidget()
        size_holder.setLayout(size_row)
        task_combo = QComboBox()
        project_combo = QComboBox()
        note_combo = QComboBox()
        object_combo = QComboBox()
        fill_combo(task_combo, self._tasks, marker.task_id, task_label)
        fill_combo(project_combo, self._projects, marker.project_id, project_label)
        fill_combo(note_combo, self._notes, marker.note_id, note_label)
        fill_combo(object_combo, self._objects, marker.object_id, object_label)
        color_btn = QToolButton()
        color_btn.setText("Выбрать…")
        color_btn.setCursor(Qt.PointingHandCursor)
        color_preview = QLabel()
        color_preview.setFixedSize(26, 26)
        color_preview.setStyleSheet(f"background: {marker.color.name()}; border: 1px solid #2a2b2f; border-radius: 4px;")
        color_row = QHBoxLayout()
        color_row.addWidget(color_preview)
        color_row.addWidget(color_btn)
        color_row.addStretch(1)
        color_holder = QWidget()
        color_holder.setLayout(color_row)
        selected_color = {"value": marker.color}

        description_edit = QPlainTextEdit()
        description_edit.setPlaceholderText("Описание метки…")
        description_edit.setPlainText(marker.description)
        description_edit.setFixedHeight(80)

        properties_edit = QPlainTextEdit()
        properties_edit.setPlaceholderText("Свойства, теги или заметки…")
        properties_edit.setPlainText(marker.properties)
        properties_edit.setFixedHeight(90)

        def pick_color() -> None:
            chosen = QColorDialog.getColor(selected_color["value"], dialog, "Цвет маркера")
            if chosen.isValid():
                selected_color["value"] = chosen
                color_preview.setStyleSheet(f"background: {chosen.name()}; border: 1px solid #2a2b2f; border-radius: 4px;")

        color_btn.clicked.connect(pick_color)
        form.addRow("Название", name_edit)
        form.addRow("Тип", type_edit)
        form.addRow("Размер", size_holder)
        form.addRow("Задача", task_combo)
        form.addRow("Проект", project_combo)
        form.addRow("Заметка", note_combo)
        form.addRow("Объект", object_combo)
        form.addRow("Цвет", color_holder)
        form.addRow("Описание", description_edit)
        form.addRow("Свойства", properties_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        resize_requested = {"value": False}

        def request_resize() -> None:
            resize_requested["value"] = True
            dialog.accept()

        resize_btn.clicked.connect(request_resize)

        dialog.setStyleSheet(f"""
            QDialog#MarkerEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#MarkerEditDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#MarkerEditDialog QLineEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QDialog#MarkerEditDialog QPlainTextEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QDialog#MarkerEditDialog QDoubleSpinBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 4px 6px;
                border-radius: 6px;
            }}
            QDialog#MarkerEditDialog QToolButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
            }}
            QDialog#MarkerEditDialog QToolButton:hover {{
                background: #34363b;
            }}
            QDialog#MarkerEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)

        if dialog.exec() == QDialog.Accepted:
            updated = Marker(
                marker.id,
                name_edit.text().strip() or marker.name,
                marker.x,
                marker.y,
                selected_color["value"],
                type_edit.text().strip() or marker.type,
                size_edit.value(),
                description_edit.toPlainText().strip(),
                properties_edit.toPlainText().strip(),
                task_combo.currentData(),
                project_combo.currentData(),
                note_combo.currentData(),
                object_combo.currentData(),
            )
            self._set_marker(updated)
            if resize_requested["value"]:
                self._enable_resize_mode(updated.id)

    def _view_marker(self, marker: Marker) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Метка на карте")
        dialog.setObjectName("MarkerViewDialog")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QHBoxLayout()
        title_label = QLabel("Свойства метки")
        title_label.setObjectName("MarkerViewTitle")
        edit_btn = QToolButton()
        edit_btn.setText("Редактировать")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.clicked.connect(lambda _checked=False: (dialog.accept(), self._edit_marker(marker)))
        header.addWidget(title_label)
        header.addStretch(1)
        header.addWidget(edit_btn)
        layout.addLayout(header)

        form = QFormLayout()

        name_label = QLabel(marker.name)
        type_label = QLabel(marker.type or "—")
        coords_label = QLabel(f"{marker.x:.0f}, {marker.y:.0f}")
        size_label = QLabel(f"{marker.size:.1f}")
        color_label = QLabel(marker.color.name())
        desc_label = QLabel(marker.description or "—")
        desc_label.setWordWrap(True)
        props_label = QLabel(marker.properties or "—")
        props_label.setWordWrap(True)

        def attachment_label(kind: str, item_id: Optional[int], source: dict) -> QLabel:
            label = QLabel()
            label.setTextFormat(Qt.RichText)
            label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            label.setOpenExternalLinks(False)
            if item_id is None:
                label.setText("—")
                return label
            item = source.get(item_id)
            if not item:
                label.setText("не найдено")
                return label
            title = getattr(item, "title", None) or getattr(item, "name", "—")
            label.setText(f'<a href="{kind}:{item_id}">{title}</a>')
            label.linkActivated.connect(
                lambda _link, k=kind, i=item_id: self._open_attachment_view(k, i)
            )
            return label

        task_link = attachment_label("task", marker.task_id, self._tasks_by_id)
        project_link = attachment_label("project", marker.project_id, self._projects_by_id)
        note_link = attachment_label("note", marker.note_id, self._notes_by_id)
        object_link = attachment_label("object", marker.object_id, self._objects_by_id)

        form.addRow("Название", name_label)
        form.addRow("Тип", type_label)
        form.addRow("Координаты", coords_label)
        form.addRow("Размер", size_label)
        form.addRow("Цвет", color_label)
        form.addRow("Описание", desc_label)
        form.addRow("Свойства", props_label)
        form.addRow("Задача", task_link)
        form.addRow("Проект", project_link)
        form.addRow("Заметка", note_link)
        form.addRow("Объект", object_link)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setStyleSheet(f"""
            QDialog#MarkerViewDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#MarkerViewDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#MarkerViewDialog QLabel#MarkerViewTitle {{
                color: #f2f2f2;
                font-weight: 600;
            }}
            QDialog#MarkerViewDialog QToolButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
            QDialog#MarkerViewDialog QToolButton:hover {{
                background: #34363b;
            }}
            QDialog#MarkerViewDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)
        dialog.exec()

    def _open_context_menu(self, pos) -> None:
        world_pos = self._map_to_world(pos)
        marker = self._marker_at(world_pos)
        menu = QMenu(self)
        act_add = menu.addAction("Добавить маркер")
        act_view = menu.addAction("Просмотреть метку")
        act_color = menu.addAction("Выбрать цвет")
        act_bigger = menu.addAction("Увеличить маркер")
        act_smaller = menu.addAction("Уменьшить маркер")
        act_resize = menu.addAction("Изменить размер")
        act_edit = menu.addAction("Редактировать маркер")
        act_delete = menu.addAction("Удалить маркер")
        act_view.setEnabled(marker is not None)
        act_color.setEnabled(marker is not None)
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
        elif chosen == act_color and marker:
            color = QColorDialog.getColor(marker.color, self, "Цвет маркера")
            if color.isValid():
                self._set_marker(
                    Marker(
                        marker.id,
                        marker.name,
                        marker.x,
                        marker.y,
                        color,
                        marker.type,
                        marker.size,
                        marker.description,
                        marker.properties,
                        marker.task_id,
                        marker.project_id,
                        marker.note_id,
                        marker.object_id,
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
        super().__init__(parent)
        self._items: List[Marker] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int):
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
        self.beginResetModel()
        self._items = list(markers)
        self.endResetModel()


class MapEditorWorkspace(QWidget):
    fullscreenToggled = Signal(bool)
    markersChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapEditorWorkspace")
        self._db = get_database()
        self._tasks_by_id = {}
        self._projects_by_id = {}
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._info_panel_was_visible = False
        self._fullscreen_active = False
        self._current_map_id: Optional[int] = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

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
            btn = QToolButton()
            btn.setIcon(qta.icon(icon_name, color="#d7d7d7"))
            btn.setIconSize(QSize(20, 20))
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.PointingHandCursor)
            if tool is not None:
                self.tool_group.addButton(btn)
                btn.clicked.connect(lambda checked=False, t=tool: self.canvas.set_tool(t))
            return btn

        self.btn_select = tool_button("fa5s.mouse-pointer", "Выбрать", MapTool.SELECT)
        self.btn_marker = tool_button("fa5s.map-marker-alt", "Добавить маркер", MapTool.ADD_MARKER)
        self.btn_region = tool_button("fa5s.draw-polygon", "Добавить регион", MapTool.ADD_REGION)
        self.btn_measure = tool_button("fa5s.ruler", "Измерение", MapTool.MEASURE)
        self.btn_grid = tool_button("fa5s.border-all", "Сетка", None)
        self.btn_grid.setCheckable(True)
        self.btn_grid.setChecked(True)
        self.btn_grid.clicked.connect(lambda checked: self.canvas.set_grid_enabled(checked))

        self.btn_fullscreen = tool_button("fa5s.expand", "Полноэкранный режим", None)
        self.btn_fullscreen.setCheckable(True)
        self.btn_fullscreen.clicked.connect(self._on_fullscreen_toggled)

        self.btn_camera = tool_button("fa5s.camera", "Скриншот", None)
        self.btn_camera.setCheckable(False)

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

        self.btn_select.setChecked(True)

        self.canvas = MapCanvas()
        self.canvas.setObjectName("MapCanvas")
        self._load_attachment_sources()

        self.info_panel = QFrame()
        self.info_panel.setObjectName("MapInfoPanel")
        self.info_panel.setFixedWidth(220)
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(8)

        self.info_title = QLabel("Данные объекта")
        self.info_title.setObjectName("MapInfoTitle")
        self.info_name = QLabel("-")
        self.info_type = QLabel("-")
        self.info_coords = QLabel("-")
        self.info_task = QLabel("-")
        self.info_project = QLabel("-")
        self.info_note = QLabel("-")
        self.info_object = QLabel("-")
        for label in [
            self.info_name,
            self.info_type,
            self.info_coords,
            self.info_task,
            self.info_project,
            self.info_note,
            self.info_object,
        ]:
            label.setObjectName("MapInfoValue")

        info_layout.addWidget(self.info_title)
        info_layout.addWidget(self.info_name)
        info_layout.addWidget(self.info_type)
        info_layout.addWidget(self.info_coords)
        info_layout.addWidget(self.info_task)
        info_layout.addWidget(self.info_project)
        info_layout.addWidget(self.info_note)
        info_layout.addWidget(self.info_object)
        info_layout.addStretch(1)

        root.addWidget(self.toolbar)
        root.addWidget(self.canvas, 1)
        root.addWidget(self.info_panel)

        self.info_panel.hide()

        self.canvas.markerSelected.connect(self._on_marker_selected)
        self.canvas.markerAdded.connect(self._on_marker_added)
        self.canvas.markerUpdated.connect(self._on_marker_updated)
        self.canvas.markerRemoved.connect(self._on_marker_removed)

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
                background: rgba(26, 28, 32, 0.92);
                border-left: 1px solid #2a2b2f;
            }

            QLabel#MapInfoTitle {
                color: #f2f2f2;
                font-size: 14px;
                font-weight: 600;
            }

            QLabel#MapInfoValue {
                color: #cfcfcf;
                font-size: 12px;
            }
        """)

    def set_fullscreen_state(self, enabled: bool) -> None:
        self.btn_fullscreen.blockSignals(True)
        self.btn_fullscreen.setChecked(enabled)
        self.btn_fullscreen.blockSignals(False)
        self._fullscreen_active = enabled
        if enabled:
            self._info_panel_was_visible = self.info_panel.isVisible()
            self.info_panel.hide()
        elif self._info_panel_was_visible:
            self.info_panel.show()

    def _on_fullscreen_toggled(self, checked: bool) -> None:
        self.fullscreenToggled.emit(checked)

    def _on_marker_selected(self, marker: Optional[Marker]) -> None:
        if self._fullscreen_active:
            self.info_panel.hide()
            return
        if not marker:
            self.info_panel.hide()
            return
        self.info_panel.show()
        self.info_name.setText(f"Имя: {marker.name}")
        self.info_type.setText(f"Тип: {marker.type}")
        self.info_coords.setText(f"Координаты: {marker.x:.0f}, {marker.y:.0f}")
        self.info_task.setText(self._format_link("Задача", marker.task_id, self._tasks_by_id))
        self.info_project.setText(self._format_link("Проект", marker.project_id, self._projects_by_id))
        self.info_note.setText(self._format_link("Заметка", marker.note_id, self._notes_by_id))
        self.info_object.setText(self._format_link("Объект", marker.object_id, self._objects_by_id))

    def _load_attachment_sources(self) -> None:
        tasks = self._db.fetch_tasks()
        projects = self._db.fetch_projects()
        notes = self._db.fetch_notes()
        objects = self._db.fetch_objects()
        self._tasks_by_id = {task.id: task for task in tasks}
        self._projects_by_id = {project.id: project for project in projects}
        self._notes_by_id = {note.id: note for note in notes}
        self._objects_by_id = {item.id: item for item in objects}
        self.canvas.set_attachment_sources(tasks, projects, notes, objects)

    def load_map(self, map_id: int, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        self._current_map_id = map_id
        self.canvas.set_tiles(tiles_path, tiles_h, tiles_w)
        markers = self._db.fetch_map_markers(map_id)
        if not markers:
            defaults = self.canvas.default_markers()
            self.canvas.set_markers(defaults)
            for marker in defaults:
                self._sync_marker(marker)
            self.markersChanged.emit()
            return
        loaded = []
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
                    marker.task_id,
                    marker.project_id,
                    marker.note_id,
                    marker.object_id,
                )
            )
        self.canvas.set_markers(loaded)
        self.markersChanged.emit()

    def markers(self) -> List[Marker]:
        return self.canvas.markers()

    def focus_marker(self, marker: Marker, zoom_boost: float = 4.0) -> None:
        self.canvas.focus_on_marker(marker, zoom_boost=zoom_boost)

    def _sync_marker(self, marker: Marker) -> None:
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
            task_id=marker.task_id,
            project_id=marker.project_id,
            note_id=marker.note_id,
            object_id=marker.object_id,
        )

    def _on_marker_added(self, marker: Marker) -> None:
        self._sync_marker(marker)
        self.markersChanged.emit()

    def _on_marker_updated(self, marker: Marker) -> None:
        self._sync_marker(marker)
        self.markersChanged.emit()

    def _on_marker_removed(self, marker_id: int) -> None:
        if self._current_map_id is None:
            return
        self._db.delete_map_marker(marker_id)
        self.markersChanged.emit()

    def _format_link(self, label: str, item_id: Optional[int], source: dict) -> str:
        if item_id is None:
            return f"{label}: —"
        item = source.get(item_id)
        if not item:
            return f"{label}: не найдено"
        title = getattr(item, "title", None) or getattr(item, "name", "—")
        return f"{label}: {title}"


class MapsListWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapsWorkspace")

        self._db = get_database()
        self._map_fullscreen_active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        list_page = QWidget()
        list_layout = QVBoxLayout(list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(10)

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

        top = QFrame()
        top.setObjectName("MapsTopbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str) -> QToolButton:
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
        self.marker_search = QLineEdit()
        self.marker_search.setObjectName("MapMarkerSearch")
        self.marker_search.setPlaceholderText("Поиск меток…")
        self.marker_search.setFixedWidth(260)

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
        super().resizeEvent(event)
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.setGeometry(self.rect())
        if hasattr(self, "marker_search_results") and self.marker_search_results.isVisible():
            self._position_marker_search_results()

    def _project_titles(self) -> List[str]:
        projects = get_database().fetch_projects()
        titles = sorted({p.title for p in projects})
        return titles

    def _refresh_projects(self) -> None:
        self.new_project.clear()
        titles = self._project_titles()
        self.new_project.addItems(titles or ["Без проекта"])

    def _cloud_storage_root(self) -> str:
        return self._db.get_setting("cloud_storage_path", default="")

    def _on_pick_tiles_path(self) -> None:
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
        if self.tab_project.isChecked():
            current = self.filter_project.currentText()
            if current != "Все проекты":
                self.model.set_project_filter(current)
                return
        self.model.set_project_filter(None)

    def _on_project_changed(self, text: str) -> None:
        if self.tab_project.isChecked() and text != "Все проекты":
            self.model.set_project_filter(text)
        else:
            self.model.set_project_filter(None)

    def set_project_filter(self, project: Optional[str]) -> None:
        """Устанавливает фильтр карт из внешней навигации."""
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
        self.editor_workspace.load_map(map_id, tiles_path, tiles_h, tiles_w)
        QTimer.singleShot(0, self._hide_loading_overlay)

    def _show_loading_overlay(self) -> None:
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.raise_()
        self.loading_overlay.setVisible(True)
        self.loading_overlay.repaint()

    def _hide_loading_overlay(self) -> None:
        self.loading_overlay.setVisible(False)

    def _on_marker_search_changed(self, text: str) -> None:
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
        text = self.marker_search.text()
        if text.strip():
            self._on_marker_search_changed(text)

    def _filter_markers(self, query: str) -> List[Marker]:
        needle = query.lower()
        matches = []
        for marker in self.editor_workspace.markers():
            hay = f"{marker.name} {marker.type} {marker.description} {marker.properties}".lower()
            if needle in hay:
                matches.append(marker)
        return matches

    def _on_marker_search_selected(self, index: QModelIndex) -> None:
        marker = index.data(MarkerSearchModel.MarkerRole)
        if not marker:
            return
        self.editor_workspace.focus_marker(marker, zoom_boost=4.0)
        self.marker_search_results.setVisible(False)

    def _on_map_fullscreen_toggled(self, enabled: bool) -> None:
        window = self.window()
        if window and hasattr(window, "set_map_fullscreen"):
            window.set_map_fullscreen(enabled)
        else:
            self.set_map_fullscreen_state(enabled)

    def set_map_fullscreen_state(self, enabled: bool) -> None:
        if self._map_fullscreen_active == enabled:
            return
        self._map_fullscreen_active = enabled
        self.editor_header.setVisible(not enabled)
        if enabled:
            self.marker_search_results.setVisible(False)
        self.editor_workspace.set_fullscreen_state(enabled)

    def _show_marker_search_results(self) -> None:
        self._position_marker_search_results()
        self.marker_search_results.setVisible(True)
        self.marker_search_results.raise_()

    def _position_marker_search_results(self) -> None:
        if not self.marker_search.isVisible():
            return
        self.marker_search_results.setFixedWidth(self.marker_search.width())
        global_pos = self.marker_search.mapToGlobal(QPoint(0, self.marker_search.height()))
        self.marker_search_results.move(global_pos)
