from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QLineEdit, QListView, QStyledItemDelegate, QSpinBox, QStyle
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
    Title = Qt.UserRole + 1
    Description = Qt.UserRole + 2
    Project = Qt.UserRole + 3
    TilesHeight = Qt.UserRole + 4
    TilesWidth = Qt.UserRole + 5


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
    ROW_H = 72
    ROW_H_MIN = 68

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#e1e1e1")
    C_DIM = QColor("#9a9a9a")
    C_PILL = QColor("#1f2126")
    C_PILL_BORDER = QColor("#2d2f35")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_title = QFont()
        self._font_title.setPointSize(10)
        self._font_title.setBold(True)

        self._font_desc = QFont()
        self._font_desc.setPointSize(9)

        self._font_pill = QFont()
        self._font_pill.setPointSize(9)

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

        total_height = title_height + desc_height + 20
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

        painter.restore()

    def _row_layout(self, r: QRect) -> dict:
        left = r.left() + 14
        right = r.right() - 14
        top = r.top() + 10
        bottom = r.bottom() - 10
        icon_rect = QRect(left, top + 6, 18, 18)
        info_w = 190
        text_rect = QRect(left + 28, top, right - info_w - (left + 28), bottom - top)
        title_rect = QRect(text_rect.left(), text_rect.top(), text_rect.width(), 22)
        desc_rect = QRect(text_rect.left(), text_rect.top() + 24, text_rect.width(), text_rect.height() - 24)

        pill_x = right - info_w + 6
        pill_w = info_w - 12
        project_rect = QRect(pill_x, top, pill_w, 22)
        tiles_rect = QRect(pill_x, top + 28, pill_w, 22)

        return {
            "icon": icon_rect,
            "text": text_rect,
            "title": title_rect,
            "desc": desc_rect,
            "project": project_rect,
            "tiles": tiles_rect,
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


class MapsListWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapsWorkspace")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

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

        root.addWidget(create)

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

        root.addWidget(top)

        self.list = QListView()
        self.list.setObjectName("MapsList")
        self.list.setUniformItemSizes(False)
        self.list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SingleSelection)
        root.addWidget(self.list, 1)

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
