from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

import qtawesome as qta
from PySide6.QtCore import (
    Qt, QSize, QRect, QAbstractListModel, QModelIndex, QPointF, QRectF, Signal
)
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPixmap, QPen, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QLineEdit, QListView, QStyledItemDelegate, QSpinBox, QStyle,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QStackedWidget, QMenu
)

from mindnavigator.storage import get_database


@dataclass(frozen=True)
class MapRow:
    id: int
    title: str
    description: str
    project: str
    tiles_h: int
    tiles_w: int


class MapRoles:
    Id = Qt.UserRole + 1
    Title = Qt.UserRole + 2
    Description = Qt.UserRole + 3
    Project = Qt.UserRole + 4
    TilesHeight = Qt.UserRole + 5
    TilesWidth = Qt.UserRole + 6


class MapsModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[MapRow] = []
        self._all_items: List[MapRow] = []
        self._search = ""
        self._project_filter: Optional[str] = None
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        self._all_items = [
            MapRow(1, "Northern Ridge", "Точки обзора и маршруты патрулей.", "MindNavigator v2", 18, 24),
            MapRow(2, "Sector 12", "Зоны контроля и минные поля.", "TACMap", 32, 32),
            MapRow(3, "Green Hills", "Артиллерийские позиции и наблюдатели.", "Wiki", 12, 20),
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
        if role == MapRoles.TilesHeight:
            return item.tiles_h
        if role == MapRoles.TilesWidth:
            return item.tiles_w
        if role == Qt.DisplayRole:
            return item.title
        return None

    def add_map(self, title: str, description: str, project: str, tiles_h: int, tiles_w: int) -> None:
        title = (title or "").strip()
        if not title:
            return
        new_id = max((item.id for item in self._all_items), default=0) + 1
        self._all_items.append(MapRow(new_id, title, description.strip(), project, tiles_h, tiles_w))
        self._rebuild()

    def update_map(
        self, map_id: int, title: str, description: str, project: str, tiles_h: int, tiles_w: int
    ) -> None:
        title = (title or "").strip()
        if not title:
            return
        updated = []
        for item in self._all_items:
            if item.id == map_id:
                updated.append(MapRow(map_id, title, description.strip(), project, tiles_h, tiles_w))
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
    ROW_H_MIN = 108

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

        total_height = title_height + desc_height + 72
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
        self.setMinimumHeight(360)

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
        form.addRow("Тайлы", tiles_block)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog#MapEditDialog {
                background: #16171a;
            }

            QDialog#MapEditDialog QLabel {
                color: #cfcfcf;
            }

            QDialog#MapEditDialog QLabel#DialogTitle {
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }

            QDialog#MapEditDialog QLineEdit,
            QDialog#MapEditDialog QComboBox,
            QDialog#MapEditDialog QSpinBox {
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }

            QDialog#MapEditDialog QFrame#MapTilesBlock {
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }

            QDialog#MapEditDialog QFrame#MapTilesBlock QSpinBox {
                background: transparent;
                border: none;
                padding: 6px 6px;
            }

            QDialog#MapEditDialog QDialogButtonBox QPushButton {
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }

            QDialog#MapEditDialog QDialogButtonBox QPushButton:hover {
                background: #34363b;
            }
        """)

    def _project_titles(self) -> List[str]:
        projects = get_database().fetch_projects()
        titles = sorted({p.title for p in projects})
        return titles or ["Без проекта"]

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


class MapCanvas(QWidget):
    markerSelected = Signal(object)
    markerAdded = Signal(object)
    markerRemoved = Signal(int)

    GRID_COLOR = QColor(70, 74, 82, 120)
    GRID_TEXT = QColor(150, 155, 160, 180)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._scale = 1.0
        self._min_scale = 0.5
        self._max_scale = 2.6
        self._offset = QPointF(80, 60)
        self._panning = False
        self._last_pos = QPointF()
        self._grid_enabled = True
        self._tool = MapTool.SELECT
        self._background = QPixmap("assets/splash.png")
        self._markers: List[Marker] = []
        self._next_id = 1
        self._selected: Optional[Marker] = None
        self._preview_pos: Optional[QPointF] = None
        self._seed_markers()

    def _seed_markers(self) -> None:
        self._markers = [
            Marker(1, "Outpost", 320, 240, QColor("#57c7ff"), "Base"),
            Marker(2, "Echo", 520, 360, QColor("#8be26f"), "Point"),
            Marker(3, "Delta", 220, 420, QColor("#f2a05d"), "Risk"),
        ]
        self._next_id = 4

    def set_tool(self, tool: MapTool) -> None:
        self._tool = tool
        self._preview_pos = None
        self.update()

    def set_grid_enabled(self, enabled: bool) -> None:
        self._grid_enabled = enabled
        self.update()

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

    def _draw_background(self, painter: QPainter) -> None:
        if self._background.isNull():
            painter.fillRect(QRectF(0, 0, 1200, 800), QColor("#3a3f36"))
            return
        painter.setOpacity(0.9)
        painter.drawPixmap(QPointF(0, 0), self._background)
        painter.setOpacity(1.0)

    def _draw_grid(self, painter: QPainter) -> None:
        spacing = 80
        rect = self._world_view_rect()
        left = int(rect.left() // spacing * spacing)
        top = int(rect.top() // spacing * spacing)
        right = int(rect.right())
        bottom = int(rect.bottom())

        pen = QPen(self.GRID_COLOR)
        pen.setWidthF(1.0 / self._scale)
        painter.setPen(pen)

        for x in range(left, right + spacing, spacing):
            painter.drawLine(x, top, x, bottom)
        for y in range(top, bottom + spacing, spacing):
            painter.drawLine(left, y, right, y)

        painter.setPen(self.GRID_TEXT)
        painter.setFont(QFont("Segoe UI", 8))
        for x in range(left, right + spacing, spacing):
            painter.drawText(QPointF(x + 4, top + 14), f"{x}")
        for y in range(top, bottom + spacing, spacing):
            painter.drawText(QPointF(left + 4, y - 4), f"{y}")

    def _draw_markers(self, painter: QPainter) -> None:
        for marker in self._markers:
            is_selected = self._selected and marker.id == self._selected.id
            radius = 7 if is_selected else 5
            painter.setBrush(marker.color)
            painter.setPen(QPen(QColor("#111111"), 1.0 / self._scale))
            painter.drawEllipse(QPointF(marker.x, marker.y), radius, radius)
            painter.setPen(QColor("#e5e5e5"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(QPointF(marker.x + 10, marker.y - 6), marker.name)

    def _draw_preview(self, painter: QPainter) -> None:
        if not self._preview_pos:
            return
        painter.setPen(QPen(QColor("#cfd8dc"), 1.0 / self._scale))
        painter.setBrush(QColor(200, 200, 200, 60))
        painter.drawEllipse(self._preview_pos, 6, 6)

    def _world_view_rect(self) -> QRectF:
        inv_scale = 1.0 / self._scale
        top_left = (QPointF(0, 0) - self._offset) * inv_scale
        bottom_right = (QPointF(self.width(), self.height()) - self._offset) * inv_scale
        return QRectF(top_left, bottom_right).normalized()

    def _map_to_world(self, pos: QPointF) -> QPointF:
        return (pos - self._offset) / self._scale

    def _map_from_world(self, pos: QPointF) -> QPointF:
        return pos * self._scale + self._offset

    def _marker_at(self, world_pos: QPointF) -> Optional[Marker]:
        for marker in reversed(self._markers):
            dist = (QPointF(marker.x, marker.y) - world_pos)
            if dist.manhattanLength() <= 10:
                return marker
        return None

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
                self.update()
                return
            self._selected = None
            self.markerSelected.emit(None)
            self._panning = True
            self._last_pos = event.position()
            self.update()

    def mouseMoveEvent(self, event):
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

    def wheelEvent(self, event):
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
        form.addRow("Название", name_edit)
        form.addRow("Тип", type_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setStyleSheet("""
            QDialog#MarkerEditDialog {
                background: #16171a;
            }
            QDialog#MarkerEditDialog QLabel {
                color: #cfcfcf;
            }
            QDialog#MarkerEditDialog QLineEdit {
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }
            QDialog#MarkerEditDialog QDialogButtonBox QPushButton {
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }
        """)

        if dialog.exec() == QDialog.Accepted:
            updated = Marker(marker.id, name_edit.text().strip() or marker.name, marker.x, marker.y, marker.color, type_edit.text().strip() or marker.type)
            self._markers = [updated if m.id == marker.id else m for m in self._markers]
            self._selected = updated
            self.markerSelected.emit(updated)
            self.update()

    def _open_context_menu(self, pos) -> None:
        world_pos = self._map_to_world(pos)
        marker = self._marker_at(world_pos)
        menu = QMenu(self)
        act_add = menu.addAction("Добавить маркер")
        act_edit = menu.addAction("Редактировать маркер")
        act_delete = menu.addAction("Удалить маркер")
        act_edit.setEnabled(marker is not None)
        act_delete.setEnabled(marker is not None)
        chosen = menu.exec(QCursor.pos())
        if chosen == act_add:
            self._add_marker(world_pos)
        elif chosen == act_edit and marker:
            self._edit_marker(marker)
        elif chosen == act_delete and marker:
            self._remove_marker(marker)


class MapEditorWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapEditorWorkspace")

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

        self.btn_camera = tool_button("fa5s.camera", "Скриншот", None)
        self.btn_camera.setCheckable(False)

        for btn in [self.btn_select, self.btn_marker, self.btn_region, self.btn_measure, self.btn_grid, self.btn_camera]:
            toolbar_layout.addWidget(btn)

        self.btn_select.setChecked(True)

        self.canvas = MapCanvas()
        self.canvas.setObjectName("MapCanvas")

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
        for label in [self.info_name, self.info_type, self.info_coords]:
            label.setObjectName("MapInfoValue")

        info_layout.addWidget(self.info_title)
        info_layout.addWidget(self.info_name)
        info_layout.addWidget(self.info_type)
        info_layout.addWidget(self.info_coords)
        info_layout.addStretch(1)

        root.addWidget(self.toolbar)
        root.addWidget(self.canvas, 1)
        root.addWidget(self.info_panel)

        self.info_panel.hide()

        self.canvas.markerSelected.connect(self._on_marker_selected)

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

    def _on_marker_selected(self, marker: Optional[Marker]) -> None:
        if not marker:
            self.info_panel.hide()
            return
        self.info_panel.show()
        self.info_name.setText(f"Имя: {marker.name}")
        self.info_type.setText(f"Тип: {marker.type}")
        self.info_coords.setText(f"Координаты: {marker.x:.0f}, {marker.y:.0f}")


class MapsListWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapsWorkspace")

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
            self.tiles_h.value(),
            self.tiles_w.value(),
        )
        self.new_title.clear()
        self.new_desc.clear()
        self.new_title.setFocus()

    def _on_edit_map(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        map_row = MapRow(
            id=index.data(MapRoles.Id),
            title=index.data(MapRoles.Title) or "",
            description=index.data(MapRoles.Description) or "",
            project=index.data(MapRoles.Project) or "",
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
                values["tiles_h"],
                values["tiles_w"],
            )

    def _on_open_map(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        title = index.data(MapRoles.Title) or "Карта"
        project = index.data(MapRoles.Project) or ""
        if project:
            self.map_title.setText(f"{title} · {project}")
        else:
            self.map_title.setText(title)
        self.stack.setCurrentIndex(1)
