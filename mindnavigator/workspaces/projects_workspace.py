# mindnavigator/workspaces/projects_workspace.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union, Callable

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QEvent
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QToolButton,
    QButtonGroup,
    QComboBox,
    QLineEdit,
    QListView,
    QMenu,
    QStyledItemDelegate,
    QStyle,
    QAbstractItemView,
)

from ..seed import seed_if_empty
from ..repositories.projects_repo import ProjectsRepo


# =========================
# Rows
# =========================

@dataclass(frozen=True)
class ProjectRow:
    id: int
    area: str
    title: str
    updated: str      # dd.mm.yyyy
    priority: str     # Low | Medium | High
    archived: bool


@dataclass(frozen=True)
class HeaderRow:
    area: str


Row = Union[ProjectRow, HeaderRow]


class ProjectRoles:
    RowType = Qt.UserRole + 1
    ProjectId = Qt.UserRole + 2
    Area = Qt.UserRole + 3
    Title = Qt.UserRole + 4
    Updated = Qt.UserRole + 5
    Priority = Qt.UserRole + 6
    Archived = Qt.UserRole + 7


# =========================
# Model
# =========================

class ProjectsModel(QAbstractListModel):
    def __init__(
        self,
        rows: List[Row],
        parent=None,
        on_toggle_archived: Optional[Callable[[int], None]] = None,
    ):
        super().__init__(parent)
        self._all_rows = rows[:]
        self._rows = rows[:]
        self._on_toggle_archived = on_toggle_archived

        self._search = ""
        self._area_focus: Optional[str] = None
        self._show_archived = False

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None

        r = self._rows[index.row()]

        if role == ProjectRoles.RowType:
            return "header" if isinstance(r, HeaderRow) else "project"

        if isinstance(r, HeaderRow):
            if role == ProjectRoles.Area:
                return r.area
            return None

        if role == ProjectRoles.ProjectId:
            return r.id
        if role == ProjectRoles.Area:
            return r.area
        if role == ProjectRoles.Title:
            return r.title
        if role == ProjectRoles.Updated:
            return r.updated
        if role == ProjectRoles.Priority:
            return r.priority
        if role == ProjectRoles.Archived:
            return r.archived

        if role == Qt.DisplayRole:
            return r.title

        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags
        if isinstance(self._rows[index.row()], HeaderRow):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    # ---- filters ----
    def set_search(self, text: str):
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_area_focus(self, area: Optional[str]):
        self._area_focus = area
        self._rebuild()

    def set_show_archived(self, show: bool):
        self._show_archived = show
        self._rebuild()

    # ---- actions ----
    def toggle_archive_by_row(self, row_idx: int):
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return

        if callable(self._on_toggle_archived):
            self._on_toggle_archived(int(r.id))

        self._rebuild()

    # ---- rebuild ----
    def _rebuild(self):
        search = self._search

        projects = [x for x in self._all_rows if isinstance(x, ProjectRow)]

        filtered: List[ProjectRow] = []
        for p in projects:
            if not self._show_archived and p.archived:
                continue
            if self._area_focus and p.area != self._area_focus:
                continue
            if search and search not in p.title.lower():
                continue
            filtered.append(p)

        filtered.sort(key=lambda x: (x.area.lower(), x.title.lower(), x.id))

        new_rows: List[Row] = []
        cur_area: Optional[str] = None
        for p in filtered:
            if cur_area != p.area:
                cur_area = p.area
                new_rows.append(HeaderRow(cur_area))
            new_rows.append(p)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()


# =========================
# Delegate
# =========================

class ProjectsItemDelegate(QStyledItemDelegate):
    ROW_H = 44
    HEADER_H = 32

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#cfcfcf")
    C_DIM = QColor("#8a8a8a")

    C_HIGH = QColor("#d94f4f")
    C_MED = QColor("#d0a93e")
    C_LOW = QColor("#4caf50")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_folder = qta.icon("fa5s.folder", color="#cfcfcf")
        self._icon_menu = qta.icon("fa5s.ellipsis-v", color="#cfcfcf")
        self._icon_fire = qta.icon("fa5s.fire", color="#d0a93e")

        self._font = QFont()
        self._font.setPointSize(10)

        self._font_small = QFont()
        self._font_small.setPointSize(9)

        self._font_header = QFont()
        self._font_header.setPointSize(9)
        self._font_header.setBold(True)

    def sizeHint(self, option, index):
        return QSize(option.rect.width(),
                     self.HEADER_H if index.data(ProjectRoles.RowType) == "header" else self.ROW_H)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        r = option.rect
        row_type = index.data(ProjectRoles.RowType)

        if row_type == "header":
            area = index.data(ProjectRoles.Area) or ""
            painter.fillRect(r, self.C_BG)
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            painter.drawText(r.adjusted(10, 0, -10, 0),
                             Qt.AlignVCenter | Qt.AlignLeft, area)
            painter.restore()
            return

        title = index.data(ProjectRoles.Title) or ""
        updated = index.data(ProjectRoles.Updated) or ""
        priority = index.data(ProjectRoles.Priority) or "Medium"

        bg = self.C_ROW if index.row() % 2 == 0 else self.C_ROW_ALT
        if option.state & QStyle.State_Selected:
            bg = QColor("#343844")
        painter.fillRect(r, bg)

        painter.setPen(self.C_BORDER)
        painter.drawRect(r.adjusted(0, 0, -1, -1))

        x = r.left() + 10
        cy = r.center().y()

        self._icon_folder.paint(painter, QRect(x, cy - 8, 16, 16))
        x += 24

        painter.setFont(self._font)
        painter.setPen(self.C_TEXT)
        title_rect = QRect(x, r.top(), r.width() // 2, r.height())
        elided = QFontMetrics(self._font).elidedText(title, Qt.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        right_pad = 10
        menu_w = 30
        pr_w = 170
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 7, menu_w, r.height() - 14)
        pr_rect = QRect(menu_rect.left() - pr_w - 8, r.top(), pr_w, r.height())

        painter.setFont(self._font_small)
        painter.setPen(self.C_DIM)
        painter.drawText(pr_rect.adjusted(0, 0, -40, 0),
                         Qt.AlignVCenter | Qt.AlignRight, "приоритет")

        painter.setPen(self._prio_color(priority))
        painter.drawText(pr_rect.adjusted(0, 0, -12, 0),
                         Qt.AlignVCenter | Qt.AlignRight, priority)

        self._icon_fire.paint(painter, QRect(pr_rect.right() - 18, cy - 8, 16, 16))

        painter.setPen(self.C_BORDER)
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter,
                              QRect(menu_rect.center().x() - 7,
                                    menu_rect.center().y() - 7, 14, 14))

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if index.data(ProjectRoles.RowType) != "project":
            return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            r = option.rect

            right_pad = 10
            menu_w = 30
            menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 7, menu_w, r.height() - 14)

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True

        return False

    def _show_row_menu(self, index: QModelIndex):
        menu = QMenu()
        menu.addAction("Открыть")
        menu.addAction("Архивировать")
        menu.addSeparator()
        menu.addAction("Удалить")
        menu.exec(QCursor.pos())

    def _prio_color(self, p: str) -> QColor:
        p = (p or "").lower()
        if p == "high":
            return self.C_HIGH
        if p == "low":
            return self.C_LOW
        return self.C_MED


# =========================
# Workspace
# =========================

class ProjectsWorkspace(QWidget):
    """DB-backed ProjectsWorkspace (UI-only)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProjectsWorkspace")

        seed_if_empty()
        self._repo = ProjectsRepo()

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ---- topbar ----
        top = QFrame()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.cmb_area = QComboBox()
        self.cmb_area.addItem("Все области")
        for a in self._repo.list_areas():
            self.cmb_area.addItem(a)

        self.chk_archived = QToolButton()
        self.chk_archived.setText("Архив")
        self.chk_archived.setCheckable(True)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)

        top_layout.addWidget(self.cmb_area)
        top_layout.addWidget(self.chk_archived)
        top_layout.addStretch(1)
        top_layout.addWidget(self.search)

        root.addWidget(top)

        # ---- list ----
        self.list = QListView()
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(self.list, 1)

        self.model = ProjectsModel(
            self._load_rows_from_db(),
            self,
            on_toggle_archived=self._toggle_archived_db
        )
        self.list.setModel(self.model)

        self.delegate = ProjectsItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        # wire
        self.search.textChanged.connect(self.model.set_search)
        self.chk_archived.toggled.connect(self.model.set_show_archived)
        self.cmb_area.currentIndexChanged.connect(self._on_area_changed)

        # styles
        self.setStyleSheet("""
            QWidget#ProjectsWorkspace { background: #16171a; }
            QFrame { background: #1b1c1f; border: 1px solid #2a2b2f; }
            QComboBox, QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
            }
            QToolButton {
                color: #cfcfcf;
                border: none;
                padding: 6px 8px;
            }
            QListView {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }
        """)

    # ---- DB glue ----
    def _toggle_archived_db(self, project_id: int):
        self._repo.toggle_archived(project_id)
        self.model._all_rows = self._load_rows_from_db()
        self.model._rebuild()

    def _load_rows_from_db(self) -> List[Row]:
        rows: List[Row] = []
        projects = self._repo.list_projects()

        cur: Optional[str] = None
        for p in projects:
            if cur != p.area:
                cur = p.area
                rows.append(HeaderRow(cur))

            y, m, d = p.updated_at[:10].split("-")
            updated_ru = f"{d}.{m}.{y}"

            rows.append(
                ProjectRow(
                    p.id,
                    p.area,
                    p.title,
                    updated_ru,
                    p.priority,
                    p.archived
                )
            )
        return rows

    # ---- handlers ----
    def _on_area_changed(self, idx: int):
        if idx <= 0:
            self.model.set_area_focus(None)
        else:
            self.model.set_area_focus(self.cmb_area.currentText())
