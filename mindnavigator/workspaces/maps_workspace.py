from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

import qtawesome as qta
from PySide6.QtCore import (
    Qt, QSize, QRect, QAbstractListModel, QModelIndex, QPointF, QRectF, Signal, QTimer
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QFont,
    QFontMetrics,
    QPixmap,
    QPen,
    QCursor,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QLineEdit, QListView, QStyledItemDelegate, QSpinBox, QStyle,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QStackedWidget, QMenu,
    QFileDialog, QColorDialog, QGraphicsView, QGraphicsScene, QGraphicsObject,
    QGraphicsPathItem, QGraphicsItem, QListWidget, QListWidgetItem, QTabWidget, QAbstractItemView
)

from mindnavigator.storage import (
    get_database,
    MindNodeData,
    MindAttachmentData,
)
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


class MapCanvas(QWidget):
    markerSelected = Signal(object)
    markerAdded = Signal(object)
    markerRemoved = Signal(int)

    GRID_COLOR = QColor(70, 74, 82, 120)
    GRID_TEXT = QColor(150, 155, 160, 180)
    DEFAULT_MARKER_SIZE = 8.0
    MIN_MARKER_SIZE = 4.0
    MAX_MARKER_SIZE = 22.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._scale = 1.0
        self._absolute_min_scale = 0.1
        self._min_scale = 0.5
        self._max_scale = 2.6
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
        self._preview_pos: Optional[QPointF] = None
        self._dragging_marker_id: Optional[int] = None
        self._seed_markers()

    def _seed_markers(self) -> None:
        self._markers = [
            Marker(1, "Outpost", 320, 240, QColor("#57c7ff"), "Base", self.DEFAULT_MARKER_SIZE),
            Marker(2, "Echo", 520, 360, QColor("#8be26f"), "Point", self.DEFAULT_MARKER_SIZE),
            Marker(3, "Delta", 220, 420, QColor("#f2a05d"), "Risk", self.DEFAULT_MARKER_SIZE),
        ]
        self._next_id = 4

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
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(QPointF(marker.x + 10, marker.y - 6), marker.name)

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
        return (pos - self._offset) / self._scale

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
        self.update()

    def _zoom_to_marker(self, marker: Marker) -> None:
        target_scale = min(self._max_scale, max(self._min_scale, self._scale * 1.4))
        view_center = QPointF(self.width() / 2, self.height() / 2)
        self._scale = target_scale
        self._offset = view_center - QPointF(marker.x, marker.y) * self._scale
        self.update()

    def _adjust_marker_size(self, marker: Marker, delta: float) -> None:
        new_size = min(self.MAX_MARKER_SIZE, max(self.MIN_MARKER_SIZE, marker.size + delta))
        if new_size == marker.size:
            return
        self._set_marker(Marker(marker.id, marker.name, marker.x, marker.y, marker.color, marker.type, new_size))

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._open_context_menu(event.pos())
            return

        if event.button() == Qt.LeftButton:
            world_pos = self._map_to_world(event.position())
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
        dialog = QDialog(self)
        dialog.setWindowTitle("Редактирование маркера")
        dialog.setObjectName("MarkerEditDialog")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        name_edit = QLineEdit(marker.name)
        type_edit = QLineEdit(marker.type)
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

        def pick_color() -> None:
            chosen = QColorDialog.getColor(selected_color["value"], dialog, "Цвет маркера")
            if chosen.isValid():
                selected_color["value"] = chosen
                color_preview.setStyleSheet(f"background: {chosen.name()}; border: 1px solid #2a2b2f; border-radius: 4px;")

        color_btn.clicked.connect(pick_color)
        form.addRow("Название", name_edit)
        form.addRow("Тип", type_edit)
        form.addRow("Цвет", color_holder)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

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
                marker.size,
            )
            self._markers = [updated if m.id == marker.id else m for m in self._markers]
            self._selected = updated
            self.markerSelected.emit(updated)
            self.update()

    def _open_context_menu(self, pos) -> None:
        world_pos = self._map_to_world(pos)
        marker = self._marker_at(world_pos)
        menu = QMenu(self)
        act_add = menu.addAction("Добавить маркер")
        act_color = menu.addAction("Выбрать цвет")
        act_bigger = menu.addAction("Увеличить маркер")
        act_smaller = menu.addAction("Уменьшить маркер")
        act_edit = menu.addAction("Редактировать маркер")
        act_delete = menu.addAction("Удалить маркер")
        act_color.setEnabled(marker is not None)
        act_bigger.setEnabled(marker is not None)
        act_smaller.setEnabled(marker is not None)
        act_edit.setEnabled(marker is not None)
        act_delete.setEnabled(marker is not None)
        chosen = menu.exec(QCursor.pos())
        if chosen == act_add:
            self._add_marker(world_pos)
        elif chosen == act_color and marker:
            color = QColorDialog.getColor(marker.color, self, "Цвет маркера")
            if color.isValid():
                self._set_marker(Marker(marker.id, marker.name, marker.x, marker.y, color, marker.type, marker.size))
        elif chosen == act_bigger and marker:
            self._adjust_marker_size(marker, 1.5)
        elif chosen == act_smaller and marker:
            self._adjust_marker_size(marker, -1.5)
        elif chosen == act_edit and marker:
            self._edit_marker(marker)
        elif chosen == act_delete and marker:
            self._remove_marker(marker)


class MindNodeItem(QGraphicsObject):
    def __init__(self, node: MindNodeData, attachment_count: int, on_moved=None, parent=None):
        super().__init__(parent)
        self.node = node
        self._attachment_count = attachment_count
        self._on_moved = on_moved
        self._color = QColor(node.color)
        self._title_font = QFont("Segoe UI", 10, QFont.Bold)
        self._meta_font = QFont("Segoe UI", 8)
        self._padding = 12
        self._corner = 10
        self._size = QSize(120, 48)
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self._update_layout()
        self.setPos(node.x, node.y)

    def _source_label(self) -> str:
        if self.node.source_type:
            return self.node.source_type.capitalize()
        return "Свободная тема"

    def _meta_text(self) -> str:
        return f"{self._source_label()} • {self._attachment_count} влож."

    def _update_layout(self) -> None:
        title_metrics = QFontMetrics(self._title_font)
        meta_metrics = QFontMetrics(self._meta_font)
        width = max(
            title_metrics.horizontalAdvance(self.node.title),
            meta_metrics.horizontalAdvance(self._meta_text()),
        )
        width = max(140, width + self._padding * 2)
        height = self._padding * 2 + title_metrics.height() + meta_metrics.height()
        self.prepareGeometryChange()
        self._size = QSize(int(width), int(height))

    def boundingRect(self):
        return QRectF(0, 0, float(self._size.width()), float(self._size.height()))

    def paint(self, painter, option, widget=None):
        rect = self.boundingRect()
        painter.setRenderHint(QPainter.Antialiasing, True)
        base_color = QColor(self._color)
        if self.isSelected():
            base_color = base_color.lighter(120)
        painter.setBrush(base_color)
        painter.setPen(QPen(QColor("#1c1e22"), 1.2))
        painter.drawRoundedRect(rect, self._corner, self._corner)

        painter.setPen(QColor("#f4f6fb"))
        painter.setFont(self._title_font)
        painter.drawText(
            QRectF(
                self._padding,
                self._padding - 2,
                rect.width() - self._padding * 2,
                rect.height(),
            ),
            Qt.AlignLeft | Qt.AlignTop,
            self.node.title,
        )

        painter.setPen(QColor("#d3d7dd"))
        painter.setFont(self._meta_font)
        painter.drawText(
            QRectF(
                self._padding,
                rect.height() - self._padding - 12,
                rect.width() - self._padding * 2,
                18,
            ),
            Qt.AlignLeft | Qt.AlignVCenter,
            self._meta_text(),
        )

    def update_title(self, title: str) -> None:
        self.node = MindNodeData(
            id=self.node.id,
            map_id=self.node.map_id,
            parent_id=self.node.parent_id,
            title=title,
            node_type=self.node.node_type,
            source_type=self.node.source_type,
            source_id=self.node.source_id,
            x=self.node.x,
            y=self.node.y,
            color=self.node.color,
        )
        self._update_layout()
        self.update()

    def update_attachment_count(self, count: int) -> None:
        self._attachment_count = count
        self._update_layout()
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            pos = value
            self.node = MindNodeData(
                id=self.node.id,
                map_id=self.node.map_id,
                parent_id=self.node.parent_id,
                title=self.node.title,
                node_type=self.node.node_type,
                source_type=self.node.source_type,
                source_id=self.node.source_id,
                x=float(pos.x()),
                y=float(pos.y()),
                color=self.node.color,
            )
            if self._on_moved:
                self._on_moved(self.node)
        return super().itemChange(change, value)


class MindEdgeItem(QGraphicsPathItem):
    def __init__(self, parent_item: MindNodeItem, child_item: MindNodeItem):
        super().__init__()
        self._parent_item = parent_item
        self._child_item = child_item
        pen = QPen(QColor("#5b6b75"), 2)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        self.setZValue(-2)
        self.update_path()

    def update_path(self) -> None:
        parent_rect = self._parent_item.sceneBoundingRect()
        child_rect = self._child_item.sceneBoundingRect()
        start = parent_rect.center()
        end = child_rect.center()
        dx = max(60.0, abs(end.x() - start.x()) * 0.6)
        path = QPainterPath(start)
        path.cubicTo(start.x() + dx, start.y(), end.x() - dx, end.y(), end.x(), end.y())
        self.setPath(path)


class MindMapCanvas(QGraphicsView):
    nodeSelected = Signal(object)
    nodeMoved = Signal(int, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-2000, -2000, 4000, 4000)
        self.setScene(self._scene)
        self._nodes: dict[int, MindNodeItem] = {}
        self._edges: list[MindEdgeItem] = []
        self._edges_by_node: dict[int, list[MindEdgeItem]] = {}
        self._scene.selectionChanged.connect(self._on_selection_changed)

    def clear_nodes(self) -> None:
        self._scene.clear()
        self._nodes = {}
        self._edges = []
        self._edges_by_node = {}

    def add_node(self, node: MindNodeData, attachment_count: int) -> None:
        item = MindNodeItem(node, attachment_count, on_moved=self._on_node_moved)
        self._scene.addItem(item)
        self._nodes[node.id] = item
        if node.parent_id and node.parent_id in self._nodes:
            self._add_edge(self._nodes[node.parent_id], item)

    def _add_edge(self, parent_item: MindNodeItem, child_item: MindNodeItem) -> None:
        edge = MindEdgeItem(parent_item, child_item)
        self._scene.addItem(edge)
        self._edges.append(edge)
        for item in (parent_item, child_item):
            self._edges_by_node.setdefault(item.node.id, []).append(edge)

    def update_attachment_count(self, node_id: int, count: int) -> None:
        item = self._nodes.get(node_id)
        if item:
            item.update_attachment_count(count)

    def update_node_title(self, node_id: int, title: str) -> None:
        item = self._nodes.get(node_id)
        if item:
            item.update_title(title)

    def remove_nodes(self, node_ids: list[int]) -> None:
        for node_id in node_ids:
            item = self._nodes.pop(node_id, None)
            if item:
                self._scene.removeItem(item)
        remaining_edges = []
        for edge in self._edges:
            if edge._parent_item.node.id in node_ids or edge._child_item.node.id in node_ids:
                self._scene.removeItem(edge)
                continue
            remaining_edges.append(edge)
        self._edges = remaining_edges
        for node_id in node_ids:
            self._edges_by_node.pop(node_id, None)

    def _on_node_moved(self, node: MindNodeData) -> None:
        for edge in self._edges_by_node.get(node.id, []):
            edge.update_path()
        self.nodeMoved.emit(node.id, node.x, node.y)

    def _on_selection_changed(self) -> None:
        selected_items = self._scene.selectedItems()
        for item in selected_items:
            if isinstance(item, MindNodeItem):
                self.nodeSelected.emit(item.node)
                return
        self.nodeSelected.emit(None)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
            self.scale(factor, factor)
            return
        super().wheelEvent(event)


class MindWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MindWorkspace")
        self._db = get_database()
        self._map_id: Optional[int] = None
        self._map_title = ""
        self._nodes: dict[int, MindNodeData] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.source_panel = QFrame()
        self.source_panel.setObjectName("MindSourcePanel")
        self.source_panel.setFixedWidth(260)
        source_layout = QVBoxLayout(self.source_panel)
        source_layout.setContentsMargins(12, 12, 12, 12)
        source_layout.setSpacing(8)

        source_title = QLabel("Библиотека")
        source_title.setObjectName("MindPanelTitle")
        source_layout.addWidget(source_title)

        self.source_tabs = QTabWidget()
        self.source_tabs.setObjectName("MindSourceTabs")
        self.source_lists: dict[str, QListWidget] = {}
        self._source_keys = ["project", "task", "object", "tag"]
        for label, key in [
            ("Проекты", "project"),
            ("Задачи", "task"),
            ("Объекты", "object"),
            ("Метки", "tag"),
        ]:
            list_widget = QListWidget()
            list_widget.setObjectName(f"MindSourceList_{key}")
            list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
            self.source_lists[key] = list_widget
            self.source_tabs.addTab(list_widget, label)
        source_layout.addWidget(self.source_tabs, 1)

        self.btn_add_node = QToolButton()
        self.btn_add_node.setText("Создать узел")
        self.btn_add_node.setCursor(Qt.PointingHandCursor)
        self.btn_add_child = QToolButton()
        self.btn_add_child.setText("Создать дочерний")
        self.btn_add_child.setCursor(Qt.PointingHandCursor)
        source_layout.addWidget(self.btn_add_node)
        source_layout.addWidget(self.btn_add_child)

        self.canvas = MindMapCanvas()
        self.canvas.setObjectName("MindCanvas")

        self.details_panel = QFrame()
        self.details_panel.setObjectName("MindDetailsPanel")
        self.details_panel.setFixedWidth(300)
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(8)

        details_title = QLabel("Свойства узла")
        details_title.setObjectName("MindPanelTitle")
        details_layout.addWidget(details_title)

        self.node_title_edit = QLineEdit()
        self.node_title_edit.setPlaceholderText("Название узла…")
        details_layout.addWidget(self.node_title_edit)

        self.node_meta = QLabel("-")
        self.node_meta.setObjectName("MindMeta")
        details_layout.addWidget(self.node_meta)

        attachments_label = QLabel("Вложения")
        attachments_label.setObjectName("MindSectionTitle")
        details_layout.addWidget(attachments_label)

        self.attachments_list = QListWidget()
        self.attachments_list.setObjectName("MindAttachmentsList")
        details_layout.addWidget(self.attachments_list, 1)

        self.btn_remove_attachment = QToolButton()
        self.btn_remove_attachment.setText("Удалить вложение")
        self.btn_remove_attachment.setCursor(Qt.PointingHandCursor)
        details_layout.addWidget(self.btn_remove_attachment)

        attach_editor = QFrame()
        attach_layout = QVBoxLayout(attach_editor)
        attach_layout.setContentsMargins(0, 0, 0, 0)
        attach_layout.setSpacing(6)

        self.attach_type = QComboBox()
        self.attach_type.addItems(["Задачи", "Проекты", "Метки", "Заметки"])
        self.attach_items = QListWidget()
        self.attach_items.setObjectName("MindAttachItems")
        self.btn_attach = QToolButton()
        self.btn_attach.setText("Прикрепить")
        self.btn_attach.setCursor(Qt.PointingHandCursor)
        attach_layout.addWidget(self.attach_type)
        attach_layout.addWidget(self.attach_items)
        attach_layout.addWidget(self.btn_attach)
        details_layout.addWidget(attach_editor)

        self.btn_delete_node = QToolButton()
        self.btn_delete_node.setText("Удалить узел")
        self.btn_delete_node.setCursor(Qt.PointingHandCursor)
        details_layout.addWidget(self.btn_delete_node)

        root.addWidget(self.source_panel)
        root.addWidget(self.canvas, 1)
        root.addWidget(self.details_panel)

        self.canvas.nodeSelected.connect(self._on_node_selected)
        self.canvas.nodeMoved.connect(self._on_node_moved)
        self.btn_add_node.clicked.connect(lambda: self._create_node(parent_id=None))
        self.btn_add_child.clicked.connect(self._create_child_node)
        self.btn_attach.clicked.connect(self._attach_item)
        self.attach_type.currentIndexChanged.connect(self._refresh_attach_items)
        self.btn_remove_attachment.clicked.connect(self._remove_attachment)
        self.btn_delete_node.clicked.connect(self._delete_selected_node)
        self.node_title_edit.editingFinished.connect(self._rename_node)

        self.details_panel.setEnabled(False)
        self._refresh_sources()
        self._refresh_attach_items()

        self.setStyleSheet("""
            QWidget#MindWorkspace { background: #14161a; }

            QFrame#MindSourcePanel, QFrame#MindDetailsPanel {
                background: #1b1d22;
                border-right: 1px solid #2a2b2f;
            }

            QFrame#MindDetailsPanel {
                border-right: none;
                border-left: 1px solid #2a2b2f;
            }

            QLabel#MindPanelTitle {
                color: #f1f1f1;
                font-size: 14px;
                font-weight: 600;
            }

            QLabel#MindSectionTitle {
                color: #cfcfcf;
                font-size: 12px;
                font-weight: 600;
            }

            QLabel#MindMeta {
                color: #9aa3ab;
                font-size: 11px;
            }

            QTabWidget#MindSourceTabs::pane {
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }

            QTabBar::tab {
                background: #23252b;
                color: #cfcfcf;
                padding: 6px 10px;
                border: 1px solid #2a2b2f;
                border-bottom: none;
            }

            QTabBar::tab:selected {
                background: #2b2f36;
                color: #ffffff;
            }

            QListWidget, QLineEdit, QComboBox {
                background: #202127;
                color: #dfe2e6;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
                padding: 6px;
            }

            QToolButton {
                background: #2a2d33;
                border: 1px solid #3a3b40;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e6e6e6;
            }

            QToolButton:hover {
                background: #34363b;
            }
        """)

    def load_map(self, map_id: int, map_title: str) -> None:
        self._map_id = map_id
        self._map_title = map_title or "Mind Map"
        self._reload_nodes()

    def _reload_nodes(self) -> None:
        if self._map_id is None:
            return
        nodes = self._db.fetch_mind_nodes(self._map_id)
        if not nodes:
            root_node = self._db.create_mind_node(
                map_id=self._map_id,
                title=self._map_title,
                node_type="root",
                source_type="map",
                x=0,
                y=0,
                color="#2f80ed",
            )
            nodes = [root_node]
        self._nodes = {node.id: node for node in nodes}
        self.canvas.clear_nodes()
        attachment_counts = {
            node.id: len(self._db.fetch_mind_attachments(node.id)) for node in nodes
        }
        for node in nodes:
            self.canvas.add_node(node, attachment_counts.get(node.id, 0))
        self.details_panel.setEnabled(False)
        self.node_title_edit.clear()
        self.node_meta.setText("-")
        self.attachments_list.clear()

    def _refresh_sources(self) -> None:
        projects = self._db.fetch_projects()
        tasks = self._db.fetch_tasks()
        objects = self._db.fetch_objects()
        notes = self._db.fetch_notes()
        tags = sorted({tag for note in notes for tag in note.tags})

        def fill_list(key: str, items: list[tuple[str, Optional[int]]]) -> None:
            widget = self.source_lists[key]
            widget.clear()
            for title, item_id in items:
                item = QListWidgetItem(title)
                item.setData(Qt.UserRole, item_id)
                widget.addItem(item)

        fill_list("project", [(p.title, p.id) for p in projects])
        fill_list("task", [(t.title, t.id) for t in tasks])
        fill_list("object", [(o.title, o.id) for o in objects])
        fill_list("tag", [(tag, None) for tag in tags])

    def _selected_source(self) -> Optional[tuple[str, Optional[int], str]]:
        current_index = self.source_tabs.currentIndex()
        if current_index < 0 or current_index >= len(self._source_keys):
            return None
        key = self._source_keys[current_index]
        widget = self.source_lists[key]
        item = widget.currentItem()
        if not item:
            return None
        return key, item.data(Qt.UserRole), item.text()

    def _create_node(self, parent_id: Optional[int]) -> None:
        if self._map_id is None:
            return
        source = self._selected_source()
        if not source:
            QMessageBox.information(self, "Добавление узла", "Выберите элемент в библиотеке.")
            return
        source_type, source_id, title = source
        color_map = {
            "project": "#2f80ed",
            "task": "#6fcf97",
            "object": "#f2994a",
            "tag": "#bb6bd9",
        }
        color = color_map.get(source_type, "#2f80ed")
        if parent_id and parent_id in self._nodes:
            parent_item = self.canvas._nodes.get(parent_id)
            parent_pos = parent_item.pos() if parent_item else QPointF(0, 0)
        else:
            parent_pos = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        offset_x = 180
        offset_y = 80 * max(1, len([n for n in self._nodes.values() if n.parent_id == parent_id]))
        new_pos = QPointF(parent_pos.x() + offset_x, parent_pos.y() + offset_y)
        node = self._db.create_mind_node(
            map_id=self._map_id,
            title=title,
            node_type="source",
            source_type=source_type,
            source_id=source_id,
            x=new_pos.x(),
            y=new_pos.y(),
            color=color,
            parent_id=parent_id,
        )
        self._nodes[node.id] = node
        self.canvas.add_node(node, 0)

    def _create_child_node(self) -> None:
        selected = self._current_node()
        if not selected:
            QMessageBox.information(self, "Добавление узла", "Сначала выберите узел на карте.")
            return
        self._create_node(parent_id=selected.id)

    def _current_node(self) -> Optional[MindNodeData]:
        selected_items = self.canvas._scene.selectedItems()
        for item in selected_items:
            if isinstance(item, MindNodeItem):
                return item.node
        return None

    def _on_node_selected(self, node: Optional[MindNodeData]) -> None:
        if not node:
            self.details_panel.setEnabled(False)
            self.node_title_edit.clear()
            self.node_meta.setText("-")
            self.attachments_list.clear()
            return
        self.details_panel.setEnabled(True)
        self.node_title_edit.setText(node.title)
        source = node.source_type.capitalize() if node.source_type else "Свободная тема"
        self.node_meta.setText(f"{source} · ID {node.id}")
        self._refresh_attachments(node.id)

    def _refresh_attachments(self, node_id: int) -> None:
        self.attachments_list.clear()
        attachments = self._db.fetch_mind_attachments(node_id)
        for att in attachments:
            item = QListWidgetItem(f"{att.item_type}: {att.item_title}")
            item.setData(Qt.UserRole, att.id)
            self.attachments_list.addItem(item)
        self.canvas.update_attachment_count(node_id, len(attachments))

    def _refresh_attach_items(self) -> None:
        self.attach_items.clear()
        mode = self.attach_type.currentText()
        if mode == "Задачи":
            items = [(t.title, t.id, "task") for t in self._db.fetch_tasks()]
        elif mode == "Проекты":
            items = [(p.title, p.id, "project") for p in self._db.fetch_projects()]
        elif mode == "Заметки":
            items = [(n.title, n.id, "note") for n in self._db.fetch_notes()]
        else:
            tags = sorted({tag for note in self._db.fetch_notes() for tag in note.tags})
            items = [(tag, None, "tag") for tag in tags]
        for title, item_id, item_type in items:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, (item_type, item_id))
            self.attach_items.addItem(item)

    def _attach_item(self) -> None:
        node = self._current_node()
        if not node:
            QMessageBox.information(self, "Вложения", "Выберите узел, чтобы прикрепить данные.")
            return
        item = self.attach_items.currentItem()
        if not item:
            QMessageBox.information(self, "Вложения", "Выберите элемент для вложения.")
            return
        item_type, item_id = item.data(Qt.UserRole)
        self._db.add_mind_attachment(node.id, item_type, item.text(), item_id)
        self._refresh_attachments(node.id)

    def _remove_attachment(self) -> None:
        node = self._current_node()
        if not node:
            return
        item = self.attachments_list.currentItem()
        if not item:
            return
        attachment_id = item.data(Qt.UserRole)
        self._db.remove_mind_attachment(attachment_id)
        self._refresh_attachments(node.id)

    def _rename_node(self) -> None:
        node = self._current_node()
        if not node:
            return
        title = self.node_title_edit.text().strip()
        if not title:
            return
        self._db.update_mind_node_title(node.id, title)
        self.canvas.update_node_title(node.id, title)
        self._nodes[node.id] = MindNodeData(
            id=node.id,
            map_id=node.map_id,
            parent_id=node.parent_id,
            title=title,
            node_type=node.node_type,
            source_type=node.source_type,
            source_id=node.source_id,
            x=node.x,
            y=node.y,
            color=node.color,
        )
        self.node_meta.setText(f"{node.source_type.capitalize() if node.source_type else 'Свободная тема'} · ID {node.id}")

    def _on_node_moved(self, node_id: int, x: float, y: float) -> None:
        self._db.update_mind_node_position(node_id, x, y)
        if node_id in self._nodes:
            node = self._nodes[node_id]
            self._nodes[node_id] = MindNodeData(
                id=node.id,
                map_id=node.map_id,
                parent_id=node.parent_id,
                title=node.title,
                node_type=node.node_type,
                source_type=node.source_type,
                source_id=node.source_id,
                x=x,
                y=y,
                color=node.color,
            )

    def _collect_descendants(self, node_id: int) -> list[int]:
        to_visit = [node_id]
        collected = []
        while to_visit:
            current = to_visit.pop()
            collected.append(current)
            children = [n.id for n in self._nodes.values() if n.parent_id == current]
            to_visit.extend(children)
        return collected

    def _delete_selected_node(self) -> None:
        node = self._current_node()
        if not node:
            return
        if QMessageBox.question(
            self,
            "Удалить узел",
            "Удалить выбранный узел вместе с дочерними элементами?",
        ) != QMessageBox.Yes:
            return
        ids = self._collect_descendants(node.id)
        self._db.delete_mind_nodes(ids)
        for node_id in ids:
            self._nodes.pop(node_id, None)
        self.canvas.remove_nodes(ids)
        self.details_panel.setEnabled(False)
        self.node_title_edit.clear()
        self.node_meta.setText("-")
        self.attachments_list.clear()


class MapsListWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapsWorkspace")

        self._db = get_database()

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

        self.editor_workspace = MindWorkspace()
        self.editor_header = QFrame()
        self.editor_header.setObjectName("MapEditorHeader")
        header_layout = QHBoxLayout(self.editor_header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        self.btn_back = QToolButton()
        self.btn_back.setText("Назад к списку")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(list_page))
        self.map_title = QLabel("Mind Workspace")
        self.map_title.setObjectName("MapEditorTitle")
        header_layout.addWidget(self.btn_back)
        header_layout.addWidget(self.map_title)
        header_layout.addStretch(1)

        editor_page = QWidget()
        editor_layout = QVBoxLayout(editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)
        editor_layout.addWidget(self.editor_header)
        editor_layout.addWidget(self.editor_workspace, 1)

        self.stack.addWidget(list_page)
        self.stack.addWidget(editor_page)
        self.stack.setCurrentWidget(list_page)

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

            QLabel#MapEditorTitle {
                color: #e6e6e6;
                font-size: 14px;
                font-weight: 600;
            }
        """)

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
        else:
            self.map_title.setText(title)
        self.stack.setCurrentIndex(1)
        if map_id:
            QTimer.singleShot(0, lambda: self.editor_workspace.load_map(map_id, title))
