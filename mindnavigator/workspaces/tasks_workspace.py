# mindnavigator/workspaces/tasks_workspace.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
from ..repositories.tasks_repo import TasksRepo


# =========================
# Rows (UI model items)
# =========================

@dataclass(frozen=True)
class TaskRow:
    id: int
    day: date
    time_text: str
    title: str
    priority: str          # Low | Medium | High
    done: bool


@dataclass(frozen=True)
class HeaderRow:
    day: date


Row = Union[TaskRow, HeaderRow]


class TaskRoles:
    RowType = Qt.UserRole + 1     # "header" | "task"
    TaskId = Qt.UserRole + 2
    Day = Qt.UserRole + 3
    TimeText = Qt.UserRole + 4
    Title = Qt.UserRole + 5
    Priority = Qt.UserRole + 6
    Done = Qt.UserRole + 7


# =========================
# Model
# =========================

class TasksModel(QAbstractListModel):
    def __init__(
        self,
        rows: List[Row],
        parent=None,
        on_toggle_done: Optional[Callable[[int], None]] = None,
    ):
        super().__init__(parent)
        self._all_rows: List[Row] = rows[:]     # base dataset (headers+tasks)
        self._rows: List[Row] = rows[:]         # filtered view
        self._on_toggle_done = on_toggle_done

        self._filter_mode = "Все"   # Все | Сегодня | Выполнено
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

        # TaskRow
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

    # ---- filtering ----
    def set_filter_mode(self, mode: str):
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_focus_day(self, d: Optional[date]):
        self._focus_day = d
        self._rebuild()

    # ---- actions ----
    def toggle_done_by_row(self, row_idx: int):
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return

        if callable(self._on_toggle_done):
            self._on_toggle_done(int(r.id))

        # NOTE: we don't mutate rows here; workspace reloads _all_rows then we rebuild
        self._rebuild()

    # ---- rebuild view ----
    def _rebuild(self):
        search = self._search
        today = date.today()

        # Extract tasks from _all_rows, apply filters, then regroup with headers
        tasks: List[TaskRow] = [x for x in self._all_rows if isinstance(x, TaskRow)]

        filtered: List[TaskRow] = []
        for t in tasks:
            if self._focus_day is not None and t.day != self._focus_day:
                continue

            if self._filter_mode == "Сегодня" and t.day != today:
                continue

            if self._filter_mode == "Выполнено" and not t.done:
                continue

            if search and search not in t.title.lower():
                continue

            filtered.append(t)

        filtered.sort(key=lambda x: (x.day, x.time_text, x.id))

        new_rows: List[Row] = []
        cur_day: Optional[date] = None
        for t in filtered:
            if cur_day != t.day:
                cur_day = t.day
                new_rows.append(HeaderRow(cur_day))
            new_rows.append(t)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()


# =========================
# Delegate (fast paint)
# =========================

class TasksItemDelegate(QStyledItemDelegate):
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
    C_OVERDUE = QColor("#d94f4f")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_grip = qta.icon("fa5s.grip-lines", color="#8a8a8a")
        self._icon_menu = qta.icon("fa5s.ellipsis-v", color="#cfcfcf")
        self._icon_fire = qta.icon("fa5s.fire", color="#d0a93e")
        self._icon_check = qta.icon("fa5s.check", color="#cfcfcf")

        self._font = QFont()
        self._font.setPointSize(10)

        self._font_small = QFont()
        self._font_small.setPointSize(9)

        self._font_header = QFont()
        self._font_header.setPointSize(9)
        self._font_header.setBold(True)

    def sizeHint(self, option, index):
        t = index.data(TaskRoles.RowType)
        if t == "header":
            return QSize(option.rect.width(), self.HEADER_H)
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        row_type = index.data(TaskRoles.RowType)
        r = option.rect

        if row_type == "header":
            d: date = index.data(TaskRoles.Day)
            text = self._format_day_ru(d) if isinstance(d, date) else ""
            painter.fillRect(r, self.C_BG)

            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            painter.drawText(r.adjusted(10, 0, -10, 0), Qt.AlignVCenter | Qt.AlignLeft, text)

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())

            painter.restore()
            return

        # task row
        title: str = index.data(TaskRoles.Title) or ""
        time_text: str = index.data(TaskRoles.TimeText) or ""
        priority: str = index.data(TaskRoles.Priority) or "Medium"
        done: bool = bool(index.data(TaskRoles.Done))
        day_val: date = index.data(TaskRoles.Day)

        bg = self.C_ROW if (index.row() % 2 == 0) else self.C_ROW_ALT
        if option.state & QStyle.State_Selected:
            bg = QColor("#343844")
        painter.fillRect(r, bg)

        painter.setPen(self.C_BORDER)
        painter.drawRect(r.adjusted(0, 0, -1, -1))

        x = r.left() + 10
        cy = r.center().y()

        # grip
        self._icon_grip.paint(painter, QRect(x, cy - 8, 16, 16))
        x += 22

        # done box
        box_rect = QRect(x, cy - 7, 14, 14)
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#16171a"))
        painter.drawRect(box_rect)
        if done:
            self._icon_check.paint(painter, QRect(box_rect.left() - 1, box_rect.top() - 1, 16, 16))
        x += 22

        # time
        painter.setFont(self._font_small)
        painter.setPen(self.C_DIM)
        painter.drawText(QRect(x, r.top(), 64, r.height()), Qt.AlignVCenter | Qt.AlignLeft, time_text)
        x += 64

        # right block rects
        right_pad = 10
        menu_w = 30
        pr_w = 170
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 7, menu_w, r.height() - 14)
        pr_rect = QRect(menu_rect.left() - pr_w - 8, r.top(), pr_w, r.height())

        # title
        painter.setFont(self._font)
        painter.setPen(self.C_DIM if done else self.C_TEXT)
        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())
        elided = QFontMetrics(self._font).elidedText(title, Qt.ElideRight, max(10, title_rect.width()))
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        # priority block (label + value + gap + fire)
        overdue = self._is_overdue(day_val, done)

        label = "приоритет"
        value_text = "OVERDUE" if overdue else priority
        value_color = self.C_OVERDUE if overdue else self._prio_color(priority)

        icon_w = 18
        gap = 12       # <-- distance between value and fire icon
        value_w = 76

        label_w = max(10, pr_rect.width() - value_w - icon_w - gap)

        label_rect = QRect(pr_rect.left(), pr_rect.top(), label_w, pr_rect.height())
        value_rect = QRect(pr_rect.left() + label_w, pr_rect.top(), value_w, pr_rect.height())
        icon_rect = QRect(pr_rect.left() + label_w + value_w + gap, cy - 8, 16, 16)

        painter.setFont(self._font_small)
        painter.setPen(self.C_DIM)
        painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignRight, label)

        painter.setPen(value_color)
        painter.drawText(value_rect, Qt.AlignVCenter | Qt.AlignRight, value_text)

        self._icon_fire.paint(painter, icon_rect)

        # menu button
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 7, menu_rect.center().y() - 7, 14, 14))

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if index.data(TaskRoles.RowType) != "task":
            return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            r = option.rect
            cy = r.center().y()

            # checkbox rect (must match paint)
            x = r.left() + 10
            x += 22
            box_rect = QRect(x, cy - 7, 14, 14)

            # menu rect
            right_pad = 10
            menu_w = 30
            menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 7, menu_w, r.height() - 14)

            if box_rect.contains(pos):
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
        if done:
            return False
        if not isinstance(d, date):
            return False
        return d < date.today()

    def _format_day_ru(self, d: date) -> str:
        # lightweight, no locale dependency
        # dd.mm.yyyy
        return d.strftime("%d.%m.%Y")


# =========================
# Workspace
# =========================

class TasksWorkspace(QWidget):
    """DB-backed TasksWorkspace (UI-only, fast list + delegate)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TasksWorkspace")

        seed_if_empty()
        self._repo = TasksRepo()

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ---- topbar ----
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
        self.tab_done = tab_btn("Выполнено")
        self.tab_all.setChecked(True)

        top_layout.addWidget(self.tab_all)
        top_layout.addWidget(self.tab_plan)
        top_layout.addWidget(self.tab_done)

        top_layout.addSpacing(12)

        # ---- plan day switcher (visible only in "План") ----
        self._plan_day = date.today()
        self._plan_span_days = 7  # window size for plan

        self.btn_prev_day = QToolButton()
        self.btn_prev_day.setCursor(Qt.PointingHandCursor)
        self.btn_prev_day.setAutoRaise(True)
        self.btn_prev_day.setText("◀")

        self.lbl_plan_day = QToolButton()
        self.lbl_plan_day.setAutoRaise(True)
        self.lbl_plan_day.setEnabled(False)
        self.lbl_plan_day.setText(self._plan_day.strftime("%d.%m.%Y"))

        self.btn_next_day = QToolButton()
        self.btn_next_day.setCursor(Qt.PointingHandCursor)
        self.btn_next_day.setAutoRaise(True)
        self.btn_next_day.setText("▶")

        top_layout.addWidget(self.btn_prev_day)
        top_layout.addWidget(self.lbl_plan_day)
        top_layout.addWidget(self.btn_next_day)

        self.cmb_focus = QComboBox()
        self.cmb_focus.setFixedWidth(180)
        self.cmb_focus.addItem("Все дни")
        top_layout.addWidget(self.cmb_focus)

        self.btn_create = QToolButton()
        self.btn_create.setText("Создать")
        self.btn_create.setCursor(Qt.PointingHandCursor)
        top_layout.addWidget(self.btn_create)

        top_layout.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)
        top_layout.addWidget(self.search)

        root.addWidget(top)

        # ---- list ----
        self.list = QListView()
        self.list.setObjectName("TasksList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        root.addWidget(self.list, 1)

        self.model = TasksModel(self._load_rows_from_db(), self, on_toggle_done=self._toggle_done_db)
        self.list.setModel(self.model)

        self.delegate = TasksItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        # wire
        for b in self.tabs_group.buttons():
            b.clicked.connect(self._on_tab_changed)

        self.search.textChanged.connect(self.model.set_search)
        self.cmb_focus.currentIndexChanged.connect(self._on_focus_changed)

        self.btn_prev_day.clicked.connect(self._plan_prev_day)
        self.btn_next_day.clicked.connect(self._plan_next_day)

        self._reload_focus_combo()

        self._update_plan_controls()

        # styles (minimal, fast)
        self.setStyleSheet("""
            QWidget#TasksWorkspace { background: #16171a; }

            QFrame#TasksTopbar {
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

            QListView#TasksList {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }
        """)

    # -------- DB glue --------
    def _toggle_done_db(self, task_id: int):
        self._repo.toggle_done(task_id)
        # Preserve current mode (All/Plan/Done)
        if self.tab_plan.isChecked():
            self._reload_plan_rows()
        else:
            self.model._all_rows = self._load_rows_from_db()
            self.model._rebuild()
            self._reload_focus_combo()

    def _load_rows_from_db(self) -> List[Row]:
        rows: List[Row] = []
        tasks = self._repo.list_tasks()

        def parse_day(s: str) -> date:
            return datetime.strptime(s, "%Y-%m-%d").date()

        cur: Optional[date] = None
        for t in tasks:
            d = parse_day(t.day)
            if cur != d:
                cur = d
                rows.append(HeaderRow(cur))
            rows.append(TaskRow(t.id, d, t.time_text, t.title, t.priority, t.done))
        return rows

    def _load_rows_from_db_range(self, day_from: date, day_to: date) -> List[Row]:
        """Build rows (with headers) from DB range."""
        rows: List[Row] = []
        tasks = self._repo.list_tasks_range(day_from, day_to, include_done=False)

        def parse_day(s: str) -> date:
            return datetime.strptime(s, "%Y-%m-%d").date()

        cur: Optional[date] = None
        for t in tasks:
            d = parse_day(t.day)
            if cur != d:
                cur = d
                rows.append(HeaderRow(cur))
            rows.append(TaskRow(t.id, d, t.time_text, t.title, t.priority, t.done))
        return rows

    def _reload_focus_combo(self):
        # rebuild focus day list from current dataset
        days: List[date] = []
        for r in self.model._all_rows:
            if isinstance(r, HeaderRow):
                days.append(r.day)

        cur_text = self.cmb_focus.currentText()

        self.cmb_focus.blockSignals(True)
        self.cmb_focus.clear()
        self.cmb_focus.addItem("Все дни")
        for d in days:
            self.cmb_focus.addItem(d.strftime("%d.%m.%Y"))
        self.cmb_focus.blockSignals(False)

        # try restore previous selection
        idx = self.cmb_focus.findText(cur_text)
        if idx >= 0:
            self.cmb_focus.setCurrentIndex(idx)
        else:
            self.cmb_focus.setCurrentIndex(0)

    # -------- UI handlers --------
    def _on_tab_changed(self):
        if self.tab_plan.isChecked():
            self._enter_plan_mode()
        elif self.tab_done.isChecked():
            self.model.set_filter_mode("Выполнено")
        else:
            # back to All mode dataset
            self.model._all_rows = self._load_rows_from_db()
            self.model._rebuild()
            self._reload_focus_combo()
            self.model.set_filter_mode("Все")

        self._update_plan_controls()

    # -------- Plan mode --------
    def _enter_plan_mode(self):
        # In plan mode we show a moving window starting at _plan_day
        self.model.set_filter_mode("Все")
        self.model.set_focus_day(None)
        self._reload_plan_rows()

    def _reload_plan_rows(self):
        day_from = self._plan_day
        day_to = self._plan_day + timedelta(days=self._plan_span_days - 1)
        self.model._all_rows = self._load_rows_from_db_range(day_from, day_to)
        self.model._rebuild()
        self._reload_focus_combo()  # keeps combo consistent (days shown)
        self._update_plan_controls()

    def _plan_prev_day(self):
        if not self.tab_plan.isChecked():
            return
        self._plan_day = self._plan_day - timedelta(days=1)
        self._reload_plan_rows()

    def _plan_next_day(self):
        if not self.tab_plan.isChecked():
            return
        self._plan_day = self._plan_day + timedelta(days=1)
        self._reload_plan_rows()

    def _update_plan_controls(self):
        is_plan = self.tab_plan.isChecked()
        self.btn_prev_day.setVisible(is_plan)
        self.lbl_plan_day.setVisible(is_plan)
        self.btn_next_day.setVisible(is_plan)
        if is_plan:
            # show "Сегодня" label when matching today
            if self._plan_day == date.today():
                self.lbl_plan_day.setText("Сегодня")
            else:
                self.lbl_plan_day.setText(self._plan_day.strftime("%d.%m.%Y"))

    def _on_focus_changed(self, idx: int):
        if idx <= 0:
            self.model.set_focus_day(None)
            return

        text = self.cmb_focus.currentText().strip()
        # dd.mm.yyyy
        try:
            d = datetime.strptime(text, "%d.%m.%Y").date()
        except Exception:
            d = None
        self.model.set_focus_day(d)
