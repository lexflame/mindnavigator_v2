from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Union, Optional

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QEvent, QDate
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QDateEdit, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle,
    QCheckBox, QMessageBox, QDialog, QDialogButtonBox, QFormLayout
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
        """Создает модель данных задач для списка."""
        super().__init__(parent)
        self._all_rows: List[Row] = rows[:]
        self._rows: List[Row] = rows[:]
        self._filter_mode = "Все"      # Все | План | Сегодня | Выполнено
        self._search = ""
        self._focus_day: Optional[date] = None

    def rowCount(self, parent=QModelIndex()) -> int:
        """Возвращает количество строк с учетом фильтрации."""
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int):
        """Отдает данные для делегата в зависимости от роли."""
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
        """Задает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.NoItemFlags
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_filter_mode(self, mode: str):
        """Устанавливает фильтр по режиму и пересобирает список."""
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        """Обновляет строку поиска и пересобирает список."""
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_focus_day(self, d: Optional[date]):
        """Фиксирует конкретный день для отображения задач."""
        self._focus_day = d
        self._rebuild()

    def add_task(self, title: str, day: date, priority: str):
        """Добавляет новую задачу и пересобирает текущий список."""
        title = (title or "").strip()
        if not title:
            return

        max_id = max((r.id for r in self._all_rows if isinstance(r, TaskRow)), default=0)
        new_id = max_id + 1

        self._all_rows.append(TaskRow(new_id, day, "", title, priority or "Medium", False))
        self._rebuild()

    def task_at_row(self, row_idx: int) -> Optional[TaskRow]:
        """Возвращает задачу по индексу строки или None."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return None
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return None
        return r

    def update_task_by_row(
        self,
        row_idx: int,
        title: str,
        day: date,
        time_text: str,
        priority: str,
        done: bool,
    ):
        """Обновляет задачу по индексу строки."""
        r = self.task_at_row(row_idx)
        if r is None:
            return

        title = (title or "").strip()
        if not title:
            return

        time_text = (time_text or "").strip()
        priority = (priority or "Medium").strip() or "Medium"

        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == r.id:
                it = TaskRow(it.id, day, time_text, title, priority, bool(done))
            new_all.append(it)

        self._all_rows = new_all
        self._rebuild()

    def toggle_done_by_row(self, row_idx: int):
        """Переключает статус выполнения задачи по индексу строки."""
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

    def delete_task_by_row(self, row_idx: int):
        """Удаляет задачу по индексу строки."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return

        self._all_rows = [it for it in self._all_rows if not (isinstance(it, TaskRow) and it.id == r.id)]
        self._rebuild()

    def _rebuild(self):
        """Пересобирает список задач с учетом фильтров и поиска."""
        today = date.today()

        def is_today(d: date) -> bool:
            """Проверяет, соответствует ли дата сегодняшнему дню."""
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
            """Преобразует строку времени в ключ сортировки."""
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


class TaskEditDialog(QDialog):
    def __init__(self, task: TaskRow, parent=None):
        """Создает диалог редактирования задачи."""
        super().__init__(parent)
        self.setWindowTitle("Редактирование задачи")
        self.setObjectName("TaskEditDialog")
        self.setMinimumWidth(460)
        self.setMinimumHeight(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit(task.title)
        self.title_edit.setPlaceholderText("Название задачи")

        self.day_edit = QDateEdit()
        self.day_edit.setCalendarPopup(True)
        self.day_edit.setDisplayFormat("yyyy-MM-dd")
        self.day_edit.setDate(task.day)
        self.day_edit.setKeyboardTracking(False)

        self.time_edit = QLineEdit(task.time_text or "")
        self.time_edit.setPlaceholderText("HH:MM")

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["Low", "Medium", "High"])
        self.priority_edit.setCurrentText(task.priority or "Medium")

        self.done_edit = QCheckBox("Выполнено")
        self.done_edit.setChecked(task.done)

        form.addRow("Название", self.title_edit)
        form.addRow("Дата", self.day_edit)
        form.addRow("Время", self.time_edit)
        form.addRow("Приоритет", self.priority_edit)
        form.addRow("", self.done_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog#TaskEditDialog {
                background: #16171a;
            }

            QDialog#TaskEditDialog QLabel {
                color: #cfcfcf;
            }

            QDialog#TaskEditDialog QLineEdit,
            QDialog#TaskEditDialog QComboBox,
            QDialog#TaskEditDialog QDateEdit {
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }

            QDialog#TaskEditDialog QComboBox::drop-down {
                border: none;
                width: 18px;
            }

            QDialog#TaskEditDialog QCheckBox {
                color: #cfcfcf;
                padding: 4px 0;
            }

            QDialog#TaskEditDialog QDialogButtonBox QPushButton {
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }

            QDialog#TaskEditDialog QDialogButtonBox QPushButton:hover {
                background: #34363b;
            }
        """)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Проверка", "Введите название задачи.")
            return
        self.accept()

    def values(self):
        """Возвращает текущие значения формы в виде словаря."""
        qd = self.day_edit.date()
        day = date(qd.year(), qd.month(), qd.day())
        time_text = self.time_edit.text().strip()
        if time_text == "__:__":
            time_text = ""
        return {
            "title": self.title_edit.text().strip(),
            "day": day,
            "time_text": time_text,
            "priority": self.priority_edit.currentText().strip() or "Medium",
            "done": self.done_edit.isChecked(),
        }


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
        """Инициализирует делегат отрисовки строк задач."""
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
        """Возвращает размер строки списка."""
        row_type = index.data(TaskRoles.RowType)
        if row_type == "header":
            return QSize(option.rect.width(), self.HEADER_H)
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        """Рисует строку задачи или заголовок дня."""
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
        """Обрабатывает клики по чекбоксу и меню строки."""
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
                # confirm только если ставим done=True
                currently_done = bool(index.data(TaskRoles.Done))
                if not currently_done:
                    res = QMessageBox.question(
                        option.widget,
                        "Подтверждение",
                        "Пометить задачу выполненной?",
                        QMessageBox.Yes | QMessageBox.Cancel,
                        QMessageBox.Cancel
                    )
                    if res != QMessageBox.Yes:
                        return True  # событие обработали, но действие отменили

                model.toggle_done_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True

        return False

    def _show_row_menu(self, index: QModelIndex):
        """Отображает контекстное меню строки."""
        menu = QMenu()
        act_open = menu.addAction("Открыть")
        act_edit = menu.addAction("Редактировать")
        menu.addSeparator()
        act_del = menu.addAction("Удалить")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit:
            self._edit_task(index)
            return
        if chosen != act_del:
            return

        # confirm delete
        title = index.data(TaskRoles.Title) or "задачу"
        res = QMessageBox.question(
            menu.parentWidget() or None,
            "Удалить задачу",
            f"Удалить задачу:\n«{title}» ?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel
        )
        if res != QMessageBox.Yes:
            return

        m = index.model()
        if hasattr(m, "delete_task_by_row"):
            m.delete_task_by_row(index.row())

    def _edit_task(self, index: QModelIndex):
        """Открывает диалог редактирования задачи."""
        model = index.model()
        if not hasattr(model, "task_at_row"):
            return

        task = model.task_at_row(index.row())
        if task is None:
            return

        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = TaskEditDialog(task, parent=parent)
        if dialog.exec() != QDialog.Accepted:
            return

        values = dialog.values()
        if hasattr(model, "update_task_by_row"):
            model.update_task_by_row(
                index.row(),
                title=values["title"],
                day=values["day"],
                time_text=values["time_text"],
                priority=values["priority"],
                done=values["done"],
            )

    def _prio_color(self, p: str) -> QColor:
        """Возвращает цвет для приоритета."""
        p = (p or "").lower()
        if p == "high":
            return self.C_HIGH
        if p == "low":
            return self.C_LOW
        return self.C_MED

    def _is_overdue(self, d: date, done: bool) -> bool:
        """Проверяет, просрочена ли задача."""
        return (d < date.today()) and (not done)

    def _format_header(self, d: date) -> str:
        """Формирует подпись для заголовка дня."""
        wd = WEEKDAY_RU[d.weekday()]
        return f"{d.isoformat()} — {wd}"


class TasksWorkspace(QWidget):
    """Рабочая область задач: панель управления и список с группировкой."""

    def __init__(self, parent=None):
        """Создает интерфейс рабочей области задач."""
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

        self.new_day = QDateEdit()
        self.new_day.setCalendarPopup(True)
        self.new_day.setDisplayFormat("yyyy-MM-dd")
        self.new_day.setFixedWidth(140)
        self.new_day.setDate(datetime.now().date())
        self.new_day.setToolTip("Дата выполнения (можно выбрать в календаре или ввести вручную)")
        self.new_day.setKeyboardTracking(False)

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
        """Обрабатывает переключение вкладок фильтра."""
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
        """Сдвигает фокусную дату на указанное число дней."""
        self._focus_day = self._focus_day + timedelta(days=delta)
        self._update_day_label()

        self.tab_today.setChecked(False)
        self.tab_all.setChecked(True)
        self.model.set_filter_mode("Все")
        self.model.set_focus_day(self._focus_day)

    def _update_day_label(self):
        """Обновляет подпись текущего дня."""
        wd = WEEKDAY_RU[self._focus_day.weekday()]
        self.lbl_day.setText(f"{self._focus_day.isoformat()} ({wd})")

    def _on_create_task(self):
        """Создает задачу из формы и очищает ввод."""
        title = self.new_title.text().strip()
        if not title:
            return

        qd = self.new_day.date()
        d = date(qd.year(), qd.month(), qd.day())

        pr = self.new_priority.currentText().strip() or "Medium"

        self.model.add_task(title=title, day=d, priority=pr)

        self.new_title.clear()
        self.new_title.setFocus()

    def _make_fake_rows(self) -> List[Row]:
        """Генерирует демонстрационный набор задач."""
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
