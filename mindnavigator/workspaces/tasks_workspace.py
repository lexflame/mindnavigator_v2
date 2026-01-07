from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Union, Optional

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QEvent
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QDateEdit, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle
)

WEEKDAY_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


@dataclass(frozen=True)
class TaskRow:
    id: int
    day: date
    time_text: str
    title: str
    priority: str   # Low | Medium | High
    done: bool


@dataclass(frozen=True)
class HeaderRow:
    day: date


Row = Union[TaskRow, HeaderRow]


class TaskRoles:
    RowType = Qt.UserRole + 1  # header | task
    Day = Qt.UserRole + 2
    TimeText = Qt.UserRole + 3
    Title = Qt.UserRole + 4
    Priority = Qt.UserRole + 5
    Done = Qt.UserRole + 6
    TaskId = Qt.UserRole + 7


class TasksModel(QAbstractListModel):
    def __init__(self, rows: List[Row], parent=None):
        super().__init__(parent)
        self._all_rows: List[Row] = rows[:]
        self._rows: List[Row] = rows[:]
        self._filter_mode = "Все"      # Все | План | Сегодня | Выполнено
        self._search = ""
        self._focus_day: Optional[date] = None

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        r = self._rows[index.row()]

        if role == TaskRoles.RowType:
            return "header" if isinstance(r, HeaderRow) else "task"

        if isinstance(r, HeaderRow):
            if role == TaskRoles.Day:
                return r.day
            if role == Qt.DisplayRole:
                return r.day.isoformat()
            return None

        if role == TaskRoles.TaskId:
            return r.id
        if role == TaskRoles.Day:
            return r.day
        if role == TaskRoles.TimeText:
            return r.time_text
        if role == TaskRoles.Title:
            return r.title
        if role == TaskRoles.Priority:
            return r.priority
        if role == TaskRoles.Done:
            return r.done
        if role == Qt.DisplayRole:
            return r.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_filter_mode(self, mode: str):
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_focus_day(self, d: Optional[date]):
        self._focus_day = d
        self._rebuild()

    def add_task(self, title: str, day: date, priority: str):
        """Append a new task and rebuild current view."""
        title = (title or "").strip()
        if not title:
            return

        # next id
        max_id = 0
        for r in self._all_rows:
            if isinstance(r, TaskRow):
                max_id = max(max_id, r.id)
        new_id = max_id + 1

        self._all_rows.append(TaskRow(new_id, day, "", title, priority or "Medium", False))
        self._rebuild()

    def toggle_done_by_row(self, row_idx: int):
            if row_idx < 0 or row_idx >= len(self._rows):
                return
            r = self._rows[row_idx]
            if isinstance(r, HeaderRow):
                return

            new_all: List[Row] = []
            for it in self._all_rows:
                if isinstance(it, TaskRow) and it.id == r.id:
                    it = TaskRow(it.id, it.day, it.time_text, it.title, it.priority, not it.done)
                new_all.append(it)

            self._all_rows = new_all
            self._rebuild()

    def _rebuild(self):
        today = date.today()

        def is_today(d: date) -> bool:
            return d == today

        search = self._search

        tasks: List[TaskRow] = []
        for it in self._all_rows:
            if not isinstance(it, TaskRow):
                continue

            if self._focus_day is not None and it.day != self._focus_day:
                continue

            if self._filter_mode == "Сегодня":
                if not is_today(it.day):
                    continue
                if it.done:
                    continue
            elif self._filter_mode == "Выполнено":
                if not it.done:
                    continue
            elif self._filter_mode == "План":
                if it.done:
                    continue
                if is_today(it.day):
                    continue

            if search:
                if search not in it.title.lower():
                    continue

            tasks.append(it)

            def time_key(t: str):
                try:
                    return datetime.strptime(t, "%H:%M").time()
                except Exception:
                    return datetime.min.time()

            tasks.sort(key=lambda x: (x.day, time_key(x.time_text), x.id))

            new_rows: List[Row] = []
            current_day: Optional[date] = None
            for t in tasks:
                if current_day != t.day:
                    current_day = t.day
                    new_rows.append(HeaderRow(current_day))
                new_rows.append(t)

            self.beginResetModel()
            self._rows = new_rows
            self.endResetModel()


class TasksItemDelegate(QStyledItemDelegate):
    ROW_H = 42
    HEADER_H = 32

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#cfcfcf")
    C_DIM = QColor("#8a8a8a")

    C_OVERDUE = QColor("#c84b4b")
    C_HIGH = QColor("#d94f4f")
    C_MED = QColor("#d0a93e")
    C_LOW = QColor("#4caf50")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_doc = qta.icon("fa5s.file-alt", color="#cfcfcf")
        self._icon_grip = qta.icon("fa5s.grip-lines", color="#8a8a8a")
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
        row_type = index.data(TaskRoles.RowType)
        if row_type == "header":
            return QSize(option.rect.width(), self.HEADER_H)
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        row_type = index.data(TaskRoles.RowType)
        r = option.rect

        if row_type == "header":
            d: date = index.data(TaskRoles.Day)
            txt = self._format_header(d)
            painter.fillRect(r, self.C_BG)

            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            painter.drawText(r.adjusted(10, 0, -10, 0), Qt.AlignVCenter | Qt.AlignLeft, txt)

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.restore()
            return

        day: date = index.data(TaskRoles.Day)
        time_text: str = index.data(TaskRoles.TimeText) or ""
        title: str = index.data(TaskRoles.Title) or ""
        priority: str = index.data(TaskRoles.Priority) or "Medium"
        done: bool = bool(index.data(TaskRoles.Done))

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

        cb_rect = QRect(x, cy - 7, 14, 14)
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#16171a"))
        painter.drawRect(cb_rect)

        if done:
            painter.setPen(QColor("#cfcfcf"))
            painter.drawLine(cb_rect.left() + 3, cb_rect.center().y(),
                             cb_rect.center().x() - 1, cb_rect.bottom() - 3)
            painter.drawLine(cb_rect.center().x() - 1, cb_rect.bottom() - 3,
                             cb_rect.right() - 2, cb_rect.top() + 3)

        x += 22

        painter.setFont(self._font_small)
        painter.setPen(self.C_DIM)
        time_rect = QRect(x, r.top(), 64, r.height())
        painter.drawText(time_rect, Qt.AlignVCenter | Qt.AlignLeft, time_text)
        x += 70

        icon_rect = QRect(x, cy - 8, 16, 16)
        self._icon_doc.paint(painter, icon_rect)
        x += 22

        painter.setFont(self._font)
        painter.setPen(self.C_TEXT if not done else self.C_DIM)

        right_pad = 10
        menu_w = 30
        pr_w = 140
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 6, menu_w, r.height() - 12)
        pr_rect = QRect(menu_rect.left() - pr_w - 8, r.top(), pr_w, r.height())

        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())
        elided = QFontMetrics(self._font).elidedText(title, Qt.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        # --- PRIORITY BLOCK (fixed layout) ---
        overdue = self._is_overdue(day, done)
        value_text = "OVERDUE" if overdue else priority
        value_color = self.C_OVERDUE if overdue else self._prio_color(priority)

        # Жёсткая сетка справа
        icon_w = 18
        value_w = 72
        gap = 10
        label_w = pr_rect.width() - value_w - icon_w - gap

        label_rect = QRect(
            pr_rect.left(),
            pr_rect.top(),
            label_w,
            pr_rect.height()
        )

        value_rect = QRect(
            pr_rect.left() + label_w,
            pr_rect.top(),
            value_w,
            pr_rect.height()
        )

        icon_rect = QRect(
            pr_rect.right() - icon_w,
            cy - 8,
            16,
            16
        )

        painter.setFont(self._font_small)

        # label
        painter.setPen(self.C_DIM)
        # painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignRight, "приоритет")

        # value
        painter.setPen(value_color)
        painter.drawText(value_rect, Qt.AlignVCenter | Qt.AlignRight, value_text)

        # icon
        self._icon_fire.paint(painter, icon_rect)

        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 5, menu_rect.center().y() - 7, 14, 14))

        painter.restore()

    def editorEvent(self, event, model, option, index):
        row_type = index.data(TaskRoles.RowType)
        if row_type != "task":
            return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            r = option.rect
            cy = r.center().y()

            x = r.left() + 10
            x += 22
            cb_rect = QRect(x, cy - 7, 14, 14)

            right_pad = 10
            menu_w = 30
            menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 6, menu_w, r.height() - 12)

            if cb_rect.contains(pos):
                model.toggle_done_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True

        return False

    def _show_row_menu(self, index: QModelIndex):
        menu = QMenu()
        menu.addAction("Открыть")
        menu.addAction("Редактировать")
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

    def _is_overdue(self, d: date, done: bool) -> bool:
        return (d < date.today()) and (not done)

    def _format_header(self, d: date) -> str:
        wd = WEEKDAY_RU[d.weekday()]
        return f"{d.isoformat()} — {wd}"


class TasksWorkspace(QWidget):
    """UI-only tasks workspace: topbar + grouped list view (fast)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TasksWorkspace")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        create = QFrame()
        create.setObjectName("TasksCreateBar")
        create_layout = QHBoxLayout(create)
        create_layout.setContentsMargins(10, 8, 10, 8)
        create_layout.setSpacing(8)

        self.new_title = QLineEdit()
        self.new_title.setPlaceholderText("Название задачи…")

        self.new_day = QComboBox()
        self.new_day.setFixedWidth(120)
        self.new_day.addItems(["Сегодня", "Завтра"])

        self.new_priority = QComboBox()
        self.new_priority.setFixedWidth(110)
        self.new_priority.addItems(["Low", "Medium", "High"])
        self.new_priority.setCurrentText("Medium")

        self.btn_add = QToolButton()
        self.btn_add.setText("Создать")
        self.btn_add.setCursor(Qt.PointingHandCursor)

        create_layout.addWidget(self.new_title, 1)
        create_layout.addWidget(self.new_day)
        create_layout.addWidget(self.new_priority)
        create_layout.addWidget(self.btn_add)

        root.addWidget(create)

        top = QFrame()
        top.setObjectName("TasksTopbar")
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
        self.tab_plan = tab_btn("План")
        self.tab_today = tab_btn("Сегодня")
        self.tab_done = tab_btn("Выполнено")
        self.tab_all.setChecked(True)

        top_layout.addWidget(self.tab_all)
        top_layout.addWidget(self.tab_plan)
        top_layout.addWidget(self.tab_today)
        top_layout.addWidget(self.tab_done)

        top_layout.addSpacing(12)

        self.btn_prev_day = QToolButton()
        self.btn_prev_day.setIcon(qta.icon("fa5s.chevron-left", color="#cfcfcf"))
        self.btn_prev_day.setCursor(Qt.PointingHandCursor)
        self.btn_prev_day.setAutoRaise(True)

        self.btn_next_day = QToolButton()
        self.btn_next_day.setIcon(qta.icon("fa5s.chevron-right", color="#cfcfcf"))
        self.btn_next_day.setCursor(Qt.PointingHandCursor)
        self.btn_next_day.setAutoRaise(True)

        self.lbl_day = QLabel()
        self.lbl_day.setObjectName("TasksDayLabel")

        top_layout.addWidget(self.btn_prev_day)
        top_layout.addWidget(self.lbl_day)
        top_layout.addWidget(self.btn_next_day)

        top_layout.addSpacing(12)

        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Любой", "Low", "Medium", "High"])
        self.cmb_priority.setFixedWidth(110)


        top_layout.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)
        top_layout.addWidget(self.search)

        root.addWidget(top)

        self.list = QListView()
        self.list.setObjectName("TasksList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SingleSelection)
        root.addWidget(self.list, 1)

        self._focus_day = date.today()
        self.model = TasksModel(self._make_fake_rows(), self)
        self.list.setModel(self.model)

        self.delegate = TasksItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        for b in self.tabs_group.buttons():
            b.clicked.connect(self._on_tab_changed)

        self.search.textChanged.connect(self.model.set_search)
        self.btn_add.clicked.connect(self._on_create_task)
        self.new_title.returnPressed.connect(self._on_create_task)
        self.btn_prev_day.clicked.connect(lambda: self._shift_day(-1))
        self.btn_next_day.clicked.connect(lambda: self._shift_day(+1))

        self._update_day_label()
        self.model.set_focus_day(None)

        self.setStyleSheet("""
            QWidget#TasksWorkspace { background: #16171a; }


            QFrame#TasksCreateBar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QFrame#TasksCreateBar QLineEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                color: #e6e6e6;
            }

            QFrame#TasksCreateBar QComboBox, QFrame#TasksCreateBar QDateEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#TasksCreateBar QToolButton {
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QFrame#TasksCreateBar QToolButton:hover { background: #34363b; }

            QFrame#TasksTopbar {
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

            QLabel#TasksDayLabel {
                color: #cfcfcf;
                padding: 0px 6px;
            }

            QComboBox, QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
            }

            QListView#TasksList {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }
        """)

    def _on_tab_changed(self):
        if self.tab_today.isChecked():
            self.model.set_filter_mode("Сегодня")
            self.model.set_focus_day(date.today())
        elif self.tab_done.isChecked():
            self.model.set_filter_mode("Выполнено")
            self.model.set_focus_day(None)
        elif self.tab_plan.isChecked():
            self.model.set_filter_mode("План")
            self.model.set_focus_day(None)
        else:
            self.model.set_filter_mode("Все")
            self.model.set_focus_day(None)

    def _shift_day(self, delta: int):
        self._focus_day = self._focus_day + timedelta(days=delta)
        self._update_day_label()

        self.tab_today.setChecked(False)
        self.tab_all.setChecked(True)
        self.model.set_filter_mode("Все")
        self.model.set_focus_day(self._focus_day)

    def _update_day_label(self):
        wd = WEEKDAY_RU[self._focus_day.weekday()]
        self.lbl_day.setText(f"{self._focus_day.isoformat()} ({wd})")


    def _on_create_task(self):
        title = self.new_title.text().strip()
        if not title:
            return

        base = date.today()
        if self.new_day.currentText() == "Завтра":
            d = base + timedelta(days=1)
        else:
            d = base

        pr = self.new_priority.currentText().strip() or "Medium"

        self.model.add_task(title=title, day=d, priority=pr)
        self.new_title.clear()
        self.new_title.setFocus()

        # keep current filter mode logic
        self.list.scrollToTop()

    def _make_fake_rows(self) -> List[Row]:
        t0 = date.today()
        days = [t0 - timedelta(days=1), t0, t0 + timedelta(days=1), t0 + timedelta(days=2)]

        tasks = [
            TaskRow(1, days[0], "13:00", "BorderDev", "High", False),
            TaskRow(2, days[0], "14:00", "Wiki → Picture", "High", False),

            TaskRow(3, days[1], "15:00", "Подумать над DragAndDrop для списка задач в режиме план", "Medium", False),
            TaskRow(4, days[1], "16:00", "Билеты ПДД", "Low", False),
            TaskRow(5, days[1], "17:00", "Просмотреть FAV", "Medium", False),
            TaskRow(6, days[1], "19:00", "Просмотреть записи во всех каналах Избранного", "Medium", False),

            TaskRow(7, days[2], "20:00", "SimCity Societies → KitBash → Здания усадьбы. Здание школы. Многоэтажка…", "High", False),

            TaskRow(8, days[3], "22:00", "Stygian · Reign of the Old Ones", "High", False),
            TaskRow(9, days[3], "23:00", "The Council", "High", True),
        ]

        tasks.sort(key=lambda x: (x.day, x.time_text, x.id))
        rows: List[Row] = []
        cur: Optional[date] = None
        for t in tasks:
            if cur != t.day:
                cur = t.day
                rows.append(HeaderRow(cur))
            rows.append(t)
        return rows