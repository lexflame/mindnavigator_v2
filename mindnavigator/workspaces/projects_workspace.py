from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union, Optional

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QEvent
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle
)

from mindnavigator.storage import format_project_date, get_database

# ProjectsWorkspace — UI-близнец TasksWorkspace:
# - та же структура верхней панели
# - тот же подход к группировке (заголовки + строки)
# - QListView + делегат ради скорости


@dataclass(frozen=True)
class ProjectRow:
    id: int
    area: str               # group header key
    title: str
    updated: str            # "dd.mm.yyyy"
    priority: str           # Low | Medium | High
    archived: bool


@dataclass(frozen=True)
class HeaderRow:
    area: str


Row = Union[ProjectRow, HeaderRow]


class ProjectRoles:
    RowType = Qt.UserRole + 1   # header | project
    Area = Qt.UserRole + 2
    Title = Qt.UserRole + 3
    Updated = Qt.UserRole + 4
    Priority = Qt.UserRole + 5
    Archived = Qt.UserRole + 6
    ProjectId = Qt.UserRole + 7


class ProjectsModel(QAbstractListModel):
    def __init__(self, parent=None):
        """Создает модель данных проектов."""
        super().__init__(parent)
        self._db = get_database()
        self._all_rows: List[Row] = []
        self._rows: List[Row] = []
        self._filter_mode = "Все"      # Все | Активные | Архив
        self._search = ""
        self._area_focus: Optional[str] = None
        self._reload_from_db()

    def _reload_from_db(self):
        """Обновляет список проектов из базы данных."""
        projects = self._db.fetch_projects()
        self._all_rows = [
            ProjectRow(
                p.id,
                p.area,
                p.title,
                format_project_date(p.updated),
                p.priority,
                p.archived,
            )
            for p in projects
        ]
        self._rebuild()

    def rowCount(self, parent=QModelIndex()) -> int:
        """Возвращает количество строк в модели."""
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int):
        """Отдает данные для делегата по ролям."""
        if not index.isValid():
            return None
        r = self._rows[index.row()]

        if role == ProjectRoles.RowType:
            return "header" if isinstance(r, HeaderRow) else "project"

        if isinstance(r, HeaderRow):
            if role == ProjectRoles.Area:
                return r.area
            if role == Qt.DisplayRole:
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

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Устанавливает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.NoItemFlags
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_filter_mode(self, mode: str):
        """Обновляет режим фильтрации."""
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        """Устанавливает строку поиска."""
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_area_focus(self, area: Optional[str]):
        """Фиксирует активную область проектов."""
        self._area_focus = area
        self._rebuild()

    def toggle_archive_by_row(self, row_idx: int):
        """Переключает архивный статус проекта по строке."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return

        new_archived = not r.archived
        self._db.set_project_archived(r.id, new_archived)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.id == r.id:
                it = ProjectRow(it.id, it.area, it.title, it.updated, it.priority, new_archived)
            new_all.append(it)

        self._all_rows = new_all
        self._rebuild()

    def _rebuild(self):
        """Пересобирает список проектов с учетом фильтров."""
        search = self._search

        projects: List[ProjectRow] = []
        for it in self._all_rows:
            if not isinstance(it, ProjectRow):
                continue

            if self._area_focus is not None and it.area != self._area_focus:
                continue

            if self._filter_mode == "Активные" and it.archived:
                continue
            if self._filter_mode == "Архив" and not it.archived:
                continue

            if search and search not in it.title.lower():
                continue

            projects.append(it)

        projects.sort(key=lambda x: (x.area.lower(), x.title.lower(), x.id))

        new_rows: List[Row] = []
        cur: Optional[str] = None
        for p in projects:
            if cur != p.area:
                cur = p.area
                new_rows.append(HeaderRow(cur))
            new_rows.append(p)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()


class ProjectsItemDelegate(QStyledItemDelegate):
    ROW_H = 42
    HEADER_H = 32

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#cfcfcf")
    C_DIM = QColor("#8a8a8a")

    C_ARCH = QColor("#6f7a87")
    C_HIGH = QColor("#d94f4f")
    C_MED = QColor("#d0a93e")
    C_LOW = QColor("#4caf50")

    def __init__(self, parent=None):
        """Инициализирует делегат отрисовки проектов."""
        super().__init__(parent)
        self._icon_folder = qta.icon("fa5s.folder-open", color="#cfcfcf")
        self._icon_grip = qta.icon("fa5s.grip-lines", color="#8a8a8a")
        self._icon_menu = qta.icon("fa5s.ellipsis-v", color="#cfcfcf")
        self._icon_pin = qta.icon("fa5s.thumbtack", color="#d0a93e")

        self._font = QFont()
        self._font.setPointSize(10)

        self._font_small = QFont()
        self._font_small.setPointSize(9)

        self._font_header = QFont()
        self._font_header.setPointSize(9)
        self._font_header.setBold(True)

    def sizeHint(self, option, index):
        """Возвращает размер строки списка."""
        row_type = index.data(ProjectRoles.RowType)
        if row_type == "header":
            return QSize(option.rect.width(), self.HEADER_H)
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        """Рисует строку проекта или заголовок области."""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        row_type = index.data(ProjectRoles.RowType)
        r = option.rect

        if row_type == "header":
            area: str = index.data(ProjectRoles.Area) or ""
            painter.fillRect(r, self.C_BG)
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            painter.drawText(r.adjusted(10, 0, -10, 0), Qt.AlignVCenter | Qt.AlignLeft, area)
            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.restore()
            return

        title: str = index.data(ProjectRoles.Title) or ""
        updated: str = index.data(ProjectRoles.Updated) or ""
        priority: str = index.data(ProjectRoles.Priority) or "Medium"
        archived: bool = bool(index.data(ProjectRoles.Archived))

        bg = self.C_ROW if (index.row() % 2 == 0) else self.C_ROW_ALT
        if option.state & QStyle.State_Selected:
            bg = QColor("#343844")

        painter.fillRect(r, bg)
        painter.setPen(self.C_BORDER)
        painter.drawRect(r.adjusted(0, 0, -1, -1))

        x = r.left() + 10
        cy = r.center().y()

        grip_rect = QRect(x, cy - 8, 16, 16)
        self._icon_grip.paint(painter, grip_rect)
        x += 22

        # archive checkbox-like indicator
        box_rect = QRect(x, cy - 7, 14, 14)
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#16171a"))
        painter.drawRect(box_rect)

        if archived:
            painter.setPen(QColor("#cfcfcf"))
            painter.drawLine(box_rect.left() + 3, box_rect.center().y(),
                             box_rect.center().x() - 1, box_rect.bottom() - 3)
            painter.drawLine(box_rect.center().x() - 1, box_rect.bottom() - 3,
                             box_rect.right() - 2, box_rect.top() + 3)

        x += 22

        icon_rect = QRect(x, cy - 8, 16, 16)
        self._icon_folder.paint(painter, icon_rect)
        x += 22

        painter.setFont(self._font)
        painter.setPen(self.C_TEXT if not archived else self.C_DIM)

        right_pad = 10
        menu_w = 30
        pr_w = 160
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 6, menu_w, r.height() - 12)
        pr_rect = QRect(menu_rect.left() - pr_w - 8, r.top(), pr_w, r.height())

        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())
        elided = QFontMetrics(self._font).elidedText(title, Qt.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        pr_color = self.C_ARCH if archived else self._prio_color(priority)
        painter.setFont(self._font_small)
        painter.setPen(pr_color)
        painter.drawText(pr_rect.adjusted(0, 0, -58, 0), Qt.AlignVCenter | Qt.AlignRight,
                         priority if not archived else "ARCH")

        painter.setPen(self.C_DIM)
        painter.drawText(pr_rect.adjusted(0, 0, -4, 0), Qt.AlignVCenter | Qt.AlignRight,
                         f"  обновл. {updated}")

        pin_rect = QRect(pr_rect.right() - 18, cy - 8, 16, 16)
        self._icon_pin.paint(painter, pin_rect)

        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 7, menu_rect.center().y() - 7, 14, 14))

        painter.restore()

    def editorEvent(self, event, model, option, index):
        """Обрабатывает клики по индикатору архивации и меню."""
        row_type = index.data(ProjectRoles.RowType)
        if row_type != "project":
            return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            r = option.rect
            cy = r.center().y()

            x = r.left() + 10
            x += 22
            box_rect = QRect(x, cy - 7, 14, 14)

            right_pad = 10
            menu_w = 30
            menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 6, menu_w, r.height() - 12)

            if box_rect.contains(pos):
                model.toggle_archive_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True

        return False

    def _show_row_menu(self, index: QModelIndex):
        """Показывает контекстное меню проекта."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #1f2227;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #2b2f36;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2b2f;
                margin: 4px 8px;
            }
        """)
        menu.addAction("Открыть")
        menu.addAction("Переименовать")
        menu.addSeparator()
        menu.addAction("Архивировать / Восстановить")
        menu.addAction("Удалить")
        menu.exec(QCursor.pos())

    def _prio_color(self, p: str) -> QColor:
        """Возвращает цвет для приоритета проекта."""
        p = (p or "").lower()
        if p == "high":
            return self.C_HIGH
        if p == "low":
            return self.C_LOW
        return self.C_MED


class ProjectsWorkspace(QWidget):
    def __init__(self, parent=None):
        """Создает рабочую область проектов."""
        super().__init__(parent)
        self.setObjectName("ProjectsWorkspace")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        top = QFrame()
        top.setObjectName("ProjectsTopbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str) -> QToolButton:
            """Создает кнопку вкладки фильтра."""
            b = QToolButton()
            b.setText(text)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setAutoRaise(True)
            self.tabs_group.addButton(b)
            return b

        self.tab_all = tab_btn("Все")
        self.tab_active = tab_btn("Активные")
        self.tab_arch = tab_btn("Архив")
        self.tab_all.setChecked(True)

        top_layout.addWidget(self.tab_all)
        top_layout.addWidget(self.tab_active)
        top_layout.addWidget(self.tab_arch)

        top_layout.addSpacing(12)

        self.cmb_area = QComboBox()
        self.cmb_area.addItems(["Все области", *get_database().project_areas()])
        self.cmb_area.setFixedWidth(180)
        top_layout.addWidget(self.cmb_area)

        top_layout.addSpacing(12)

        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Любой", "Low", "Medium", "High"])
        self.cmb_priority.setFixedWidth(110)

        self.btn_create = QToolButton()
        self.btn_create.setText("Создать")
        self.btn_create.setCursor(Qt.PointingHandCursor)

        top_layout.addWidget(self.cmb_priority)
        top_layout.addWidget(self.btn_create)

        top_layout.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)
        top_layout.addWidget(self.search)

        root.addWidget(top)

        self.list = QListView()
        self.list.setObjectName("ProjectsList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SingleSelection)
        root.addWidget(self.list, 1)

        self.model = ProjectsModel(self)
        self.list.setModel(self.model)

        self.delegate = ProjectsItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        for b in self.tabs_group.buttons():
            b.clicked.connect(self._on_tab_changed)

        self.search.textChanged.connect(self.model.set_search)
        self.cmb_area.currentTextChanged.connect(self._on_area_changed)

        self.setStyleSheet("""
            QWidget#ProjectsWorkspace { background: #16171a; }

            QFrame#ProjectsTopbar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QToolButton {
                color: #cfcfcf;
                border: none;
                padding: 6px 8px;
            }
            QToolButton:checked { background: #2a2b2f; }

            QComboBox, QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
            }

            QListView#ProjectsList {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }
        """)

    def _on_tab_changed(self):
        """Обрабатывает переключение фильтров по статусу."""
        if self.tab_arch.isChecked():
            self.model.set_filter_mode("Архив")
        elif self.tab_active.isChecked():
            self.model.set_filter_mode("Активные")
        else:
            self.model.set_filter_mode("Все")

    def _on_area_changed(self, text: str):
        """Обновляет фильтрацию по области проекта."""
        if text == "Все области":
            self.model.set_area_focus(None)
        else:
            self.model.set_area_focus(text)
