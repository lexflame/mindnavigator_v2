from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Union, Optional

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QEvent, QDate, QTime, QMimeData
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QDateEdit, QTimeEdit, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle,
    QCheckBox, QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QAbstractItemView, QPlainTextEdit
)

from mindnavigator.storage import get_database, normalize_priority, validate_time_text
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND

WEEKDAY_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


@dataclass(frozen=True)
class TaskRow:
    id: int
    day: date
    time_text: str
    title: str
    description: str
    priority: str   # Low | Medium | High
    done: bool
    project_id: Optional[int] = None
    project_title: str = ""


@dataclass(frozen=True)
class HeaderRow:
    day: date


@dataclass(frozen=True)
class SortHeaderRow:
    pass


Row = Union[TaskRow, HeaderRow, SortHeaderRow]


class TaskRoles:
    RowType = Qt.UserRole + 1  # header | task
    Day = Qt.UserRole + 2
    TimeText = Qt.UserRole + 3
    Title = Qt.UserRole + 4
    Description = Qt.UserRole + 5
    Priority = Qt.UserRole + 6
    Done = Qt.UserRole + 7
    TaskId = Qt.UserRole + 8
    SortKey = Qt.UserRole + 9
    SortDirection = Qt.UserRole + 10
    DisplayTime = Qt.UserRole + 11
    ProjectTitle = Qt.UserRole + 12
    Expanded = Qt.UserRole + 13


class TasksModel(QAbstractListModel):
    def __init__(self, parent=None):
        """Создает модель данных задач для списка."""
        super().__init__(parent)
        self._db = get_database()
        self._all_rows: List[Row] = []
        self._rows: List[Row] = []
        self._filter_mode = "Все"      # Все | План | Сегодня | Выполнено
        self._search = ""
        self._focus_day: Optional[date] = None
        self._project_filter_id: Optional[int] = None
        self._sort_key = "date"  # date | title | priority
        self._sort_asc = True
        self._drag_enabled = False
        self._expanded_task_ids: set[int] = set()
        self._reload_from_db()

    def _reload_from_db(self):
        """Обновляет список задач из базы данных."""
        tasks = self._db.fetch_tasks()
        self._all_rows = [
            TaskRow(
                t.id,
                t.day,
                t.time_text,
                t.title,
                t.description,
                t.priority,
                t.done,
                t.project_id,
                t.project_title,
            )
            for t in tasks
        ]
        self._rebuild()

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
            if isinstance(r, HeaderRow):
                return "header"
            if isinstance(r, SortHeaderRow):
                return "sort_header"
            return "task"

        if isinstance(r, HeaderRow):
            if role == TaskRoles.Day:
                return r.day
            if role == Qt.DisplayRole:
                return r.day.isoformat()
            return None

        if isinstance(r, SortHeaderRow):
            if role == TaskRoles.SortKey:
                return self._sort_key
            if role == TaskRoles.SortDirection:
                return "asc" if self._sort_asc else "desc"
            if role == Qt.DisplayRole:
                return "sort_header"
            return None

        if role == TaskRoles.TaskId:
            return r.id
        if role == TaskRoles.Day:
            return r.day
        if role == TaskRoles.TimeText:
            return r.time_text
        if role == TaskRoles.DisplayTime:
            return self._display_time_text(r)
        if role == TaskRoles.Title:
            return r.title
        if role == TaskRoles.Description:
            return r.description
        if role == TaskRoles.Priority:
            return r.priority
        if role == TaskRoles.Done:
            return r.done
        if role == TaskRoles.Expanded:
            return r.id in self._expanded_task_ids
        if role == TaskRoles.ProjectTitle:
            return r.project_title
        if role == Qt.DisplayRole:
            return r.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Задает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.NoItemFlags
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            flags = Qt.ItemIsEnabled
            if self._drag_enabled:
                flags |= Qt.ItemIsDropEnabled
            return flags
        if isinstance(r, SortHeaderRow):
            return Qt.ItemIsEnabled
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self._drag_enabled:
            flags |= Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        return flags

    def set_filter_mode(self, mode: str):
        """Устанавливает фильтр по режиму и пересобирает список."""
        self._filter_mode = mode
        self._drag_enabled = (mode == "План")
        self._rebuild()

    def filter_mode(self) -> str:
        """Возвращает текущий режим фильтра."""
        return self._filter_mode

    def set_search(self, text: str):
        """Обновляет строку поиска и пересобирает список."""
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_focus_day(self, d: Optional[date]):
        """Фиксирует конкретный день для отображения задач."""
        self._focus_day = d
        self._rebuild()

    def set_project_filter(self, project_id: Optional[int]):
        """Устанавливает фильтр по проекту."""
        self._project_filter_id = project_id
        self._rebuild()

    def add_task(self, title: str, day: date, time_text: str, priority: str):
        """Добавляет новую задачу и пересобирает текущий список."""
        task = self._db.create_task(title=title, description="", day=day, time_text=time_text, priority=priority)
        self._all_rows.append(
            TaskRow(
                task.id,
                task.day,
                task.time_text,
                task.title,
                task.description,
                task.priority,
                task.done,
                task.project_id,
                task.project_title,
            )
        )
        self._rebuild()

    def set_sort(self, key: str):
        """Устанавливает сортировку для режима «Все»."""
        if key == self._sort_key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_key = key
            self._sort_asc = True
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
        description: str,
        day: date,
        time_text: str,
        priority: str,
        done: bool,
        project_id: Optional[int],
    ):
        """Обновляет задачу по индексу строки."""
        r = self.task_at_row(row_idx)
        if r is None:
            return
        updated = self._db.update_task(
            task_id=r.id,
            title=title,
            description=description,
            day=day,
            time_text=time_text,
            priority=priority,
            done=done,
            project_id=project_id,
        )

        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == r.id:
                it = TaskRow(
                    updated.id,
                    updated.day,
                    updated.time_text,
                    updated.title,
                    updated.description,
                    updated.priority,
                    updated.done,
                    updated.project_id,
                    updated.project_title,
                )
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

        new_done = not r.done
        self._db.set_task_done(r.id, new_done)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == r.id:
                it = TaskRow(
                    it.id,
                    it.day,
                    it.time_text,
                    it.title,
                    it.description,
                    it.priority,
                    new_done,
                    it.project_id,
                    it.project_title,
                )
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

        self._db.delete_task(r.id)
        self._all_rows = [it for it in self._all_rows if not (isinstance(it, TaskRow) and it.id == r.id)]
        self._expanded_task_ids.discard(r.id)
        self._rebuild()

    def move_task_to_day(self, task_id: int, new_day: date) -> bool:
        """Переносит задачу на новую дату."""
        task = next((it for it in self._all_rows if isinstance(it, TaskRow) and it.id == task_id), None)
        if task is None:
            return False
        if task.day == new_day:
            return False

        updated = self._db.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            day=new_day,
            time_text=task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=task.project_id,
        )
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == task.id:
                it = TaskRow(
                    updated.id,
                    updated.day,
                    updated.time_text,
                    updated.title,
                    updated.description,
                    updated.priority,
                    updated.done,
                    updated.project_id,
                    updated.project_title,
                )
            new_all.append(it)
        self._all_rows = new_all
        self._rebuild()
        return True

    def next_day_for_task(self, task: TaskRow) -> date:
        """Возвращает дату для переноса задачи на следующий рабочий день."""
        target = task.day + timedelta(days=1)
        if target.weekday() == 5:
            target += timedelta(days=2)
        elif target.weekday() == 6:
            target += timedelta(days=6)

        if self._tasks_count_on_day(target, exclude_task_id=task.id) > 4:
            target += timedelta(days=1)
        return target

    def _tasks_count_on_day(self, day_value: date, exclude_task_id: Optional[int] = None) -> int:
        """Считает количество невыполненных задач на конкретный день."""
        count = 0
        for it in self._all_rows:
            if not isinstance(it, TaskRow):
                continue
            if exclude_task_id is not None and it.id == exclude_task_id:
                continue
            if it.day == day_value and not it.done:
                count += 1
        return count

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

            if self._project_filter_id is not None and it.project_id != self._project_filter_id:
                continue

            if self._filter_mode == "Сегодня":
                if not is_today(it.day):
                    continue
                if it.done:
                    continue
            elif self._filter_mode == "Все":
                if it.done:
                    continue
            elif self._filter_mode == "Выполнено":
                if not it.done:
                    continue
            elif self._filter_mode == "План":
                if it.done:
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

        if self._filter_mode == "Все":
            priority_order = {"high": 0, "medium": 1, "low": 2}

            def sort_key(task: TaskRow):
                if self._sort_key == "title":
                    return (task.title.lower(), task.day, time_key(task.time_text), task.id)
                if self._sort_key == "priority":
                    return (priority_order.get(task.priority.lower(), 3), task.day, time_key(task.time_text), task.id)
                return (task.day, time_key(task.time_text), task.id)

            tasks.sort(key=sort_key, reverse=not self._sort_asc)
        else:
            tasks.sort(key=lambda x: (x.day, time_key(x.time_text), x.id))

        new_rows: List[Row] = []
        if self._filter_mode == "Все":
            new_rows.append(SortHeaderRow())
            new_rows.extend(tasks)
        else:
            current_day: Optional[date] = None
            for t in tasks:
                if current_day != t.day:
                    current_day = t.day
                    new_rows.append(HeaderRow(current_day))
                new_rows.append(t)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()

    def _display_time_text(self, task: TaskRow) -> str:
        """Формирует отображаемое время с учетом режима."""
        if self._filter_mode == "Все":
            if task.time_text:
                return f"{task.time_text} · {task.day.isoformat()}"
            return task.day.isoformat()
        return task.time_text

    def toggle_expanded_by_row(self, row_idx: int) -> None:
        """Переключает раскрытие задачи по индексу строки."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        if task.id in self._expanded_task_ids:
            self._expanded_task_ids.remove(task.id)
        else:
            self._expanded_task_ids.add(task.id)
        idx = self.index(row_idx)
        if idx.isValid():
            self.dataChanged.emit(idx, idx, [TaskRoles.Expanded, Qt.SizeHintRole])

    def mimeTypes(self) -> List[str]:
        """Возвращает поддерживаемые типы данных для drag and drop."""
        return ["application/x-mindnavigator-task-id"]

    def mimeData(self, indexes) -> QMimeData:
        """Создает mime-данные для перетаскивания задачи."""
        mime_data = QMimeData()
        if not indexes:
            return mime_data
        idx = indexes[0]
        task = self.task_at_row(idx.row())
        if task is None:
            return mime_data
        mime_data.setData("application/x-mindnavigator-task-id", str(task.id).encode("utf-8"))
        return mime_data

    def supportedDropActions(self) -> Qt.DropActions:
        """Разрешает перенос с изменением позиции."""
        return Qt.MoveAction

    def dropMimeData(self, data, action, row, column, parent) -> bool:
        """Обрабатывает перенос задачи между днями."""
        if action == Qt.IgnoreAction:
            return True
        if not self._drag_enabled:
            return False
        if not data.hasFormat("application/x-mindnavigator-task-id"):
            return False

        task_id_bytes = data.data("application/x-mindnavigator-task-id")
        try:
            task_id = int(bytes(task_id_bytes).decode("utf-8"))
        except ValueError:
            return False

        target_row = row
        if target_row < 0 and parent.isValid():
            target_row = parent.row()
        if target_row < 0:
            target_row = len(self._rows) - 1

        target_day = self._drop_target_day(target_row)
        if target_day is None:
            return False

        return self.move_task_to_day(task_id, target_day)

    def _drop_target_day(self, row_idx: int) -> Optional[date]:
        """Определяет дату для переноса по позиции drop."""
        if not self._rows:
            return None
        if row_idx >= len(self._rows):
            row_idx = len(self._rows) - 1

        for idx in range(row_idx, -1, -1):
            r = self._rows[idx]
            if isinstance(r, HeaderRow):
                return r.day
            if isinstance(r, TaskRow):
                return r.day
        return None


class TaskEditDialog(QDialog):
    def __init__(self, task: TaskRow, parent=None):
        """Создает диалог редактирования задачи."""
        super().__init__(parent)
        self.setWindowTitle("Редактирование задачи")
        self.setObjectName("TaskEditDialog")
        self.setMinimumWidth(460)
        self.setMinimumHeight(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Редактирование задачи")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit(task.title)
        self.title_edit.setPlaceholderText("Название задачи")

        self.description_edit = QPlainTextEdit(task.description)
        self.description_edit.setPlaceholderText("Описание задачи")
        self.description_edit.setMinimumHeight(90)

        self.project_edit = QComboBox()
        self.project_edit.addItem("Без проекта", None)
        projects = get_database().fetch_projects()
        for project in projects:
            self.project_edit.addItem(f"{project.area} · {project.title}", project.id)
        if task.project_id is not None:
            idx = self.project_edit.findData(task.project_id)
            if idx >= 0:
                self.project_edit.setCurrentIndex(idx)

        self.day_edit = QDateEdit()
        self.day_edit.setCalendarPopup(True)
        self.day_edit.setDisplayFormat("yyyy-MM-dd")
        self.day_edit.setDate(task.day)
        self.day_edit.setKeyboardTracking(False)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(9, 0))
        self.time_edit.setKeyboardTracking(False)

        self.time_toggle = QCheckBox("Указать")
        self.time_toggle.setCursor(Qt.PointingHandCursor)

        if task.time_text:
            try:
                parsed = datetime.strptime(task.time_text, "%H:%M").time()
                self.time_edit.setTime(QTime(parsed.hour, parsed.minute))
                self.time_toggle.setChecked(True)
            except Exception:
                self.time_toggle.setChecked(False)
        else:
            self.time_toggle.setChecked(False)

        self.time_edit.setEnabled(self.time_toggle.isChecked())
        self.time_toggle.toggled.connect(self.time_edit.setEnabled)

        time_block = QFrame()
        time_block.setObjectName("TaskDateTimeBlock")
        time_block_layout = QHBoxLayout(time_block)
        time_block_layout.setContentsMargins(8, 4, 8, 4)
        time_block_layout.setSpacing(6)
        time_block_layout.addWidget(self.day_edit)
        time_block_layout.addWidget(self.time_toggle)
        time_block_layout.addWidget(self.time_edit)

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["Low", "Medium", "High"])
        self.priority_edit.setCurrentText(task.priority or "Medium")

        self.done_edit = QCheckBox("Выполнено")
        self.done_edit.setChecked(task.done)

        form.addRow("Название", self.title_edit)
        form.addRow("Описание", self.description_edit)
        form.addRow("Проект", self.project_edit)
        form.addRow("Дата и время", time_block)
        form.addRow("Приоритет", self.priority_edit)
        form.addRow("", self.done_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#TaskEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#TaskEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#TaskEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#TaskEditDialog QLineEdit,
            QDialog#TaskEditDialog QPlainTextEdit,
            QDialog#TaskEditDialog QComboBox,
            QDialog#TaskEditDialog QDateEdit,
            QDialog#TaskEditDialog QTimeEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#TaskEditDialog QPlainTextEdit {{
                padding: 8px 10px;
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QDateEdit,
            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QTimeEdit {{
                background: transparent;
                border: none;
                padding: 6px 6px;
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QCheckBox {{
                color: #cfcfcf;
                padding: 0 6px;
            }}

            QDialog#TaskEditDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView {{
                background: #1c1d22;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                selection-background-color: #2f3238;
                selection-color: #f2f2f2;
                outline: none;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView::item {{
                padding: 6px 10px;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView::item:selected {{
                background: #2f3238;
                color: #f2f2f2;
            }}

            QDialog#TaskEditDialog QCheckBox {{
                color: #cfcfcf;
                padding: 4px 0;
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Проверка", "Введите название задачи.")
            return
        time_text = self._current_time_text()
        try:
            validate_time_text(time_text)
            normalize_priority(self.priority_edit.currentText())
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self.accept()

    def _current_time_text(self) -> str:
        if not self.time_toggle.isChecked():
            return ""
        return self.time_edit.time().toString("HH:mm")

    def values(self):
        """Возвращает текущие значения формы в виде словаря."""
        qd = self.day_edit.date()
        day = date(qd.year(), qd.month(), qd.day())
        time_text = self._current_time_text()
        return {
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "day": day,
            "time_text": time_text,
            "priority": self.priority_edit.currentText().strip() or "Medium",
            "done": self.done_edit.isChecked(),
            "project_id": self.project_edit.currentData(),
        }


class TasksItemDelegate(QStyledItemDelegate):
    ROW_H = 42
    HEADER_H = 32
    TIME_W = 140
    PROJECT_W = 130
    TEXT_VPAD = 8
    TEXT_GAP = 6
    ROW_H_EXPANDED_MIN = 82

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#cfcfcf")
    C_DIM = QColor("#8a8a8a")
    C_TODAY = QColor("#f2a23a")

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
        self._icon_tomorrow = qta.icon("ph.arrow-u-right-down-bold", color="#cfcfcf")

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
        if row_type in ("header", "sort_header"):
            return QSize(option.rect.width(), self.HEADER_H)
        expanded = bool(index.data(TaskRoles.Expanded))
        if not expanded:
            return QSize(option.rect.width(), self.ROW_H)

        title = index.data(TaskRoles.Title) or ""
        description = index.data(TaskRoles.Description) or ""
        layout = self._row_layout(option.rect)
        text_width = max(10, layout["title"].width())

        title_metrics = QFontMetrics(self._font)
        desc_metrics = QFontMetrics(self._font_small)
        title_height = title_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextWordWrap, title).height()
        desc_height = 0
        if description:
            desc_height = desc_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextWordWrap, description).height()

        total_height = title_height + desc_height
        if description:
            total_height += self.TEXT_GAP
        total_height += self.TEXT_VPAD * 2
        total_height = max(total_height, self.ROW_H_EXPANDED_MIN)
        return QSize(option.rect.width(), total_height)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        """Рисует строку задачи или заголовок дня."""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        row_type = index.data(TaskRoles.RowType)
        r = option.rect

        if row_type == "header":
            d: date = index.data(TaskRoles.Day)
            txt = self._format_header(d)
            model = index.model()
            is_plan = False
            if hasattr(model, "filter_mode"):
                is_plan = model.filter_mode() == "План"
            show_today = is_plan and d == date.today()
            painter.fillRect(r, self.C_BG)

            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            text_rect = r.adjusted(10, 0, -10, 0)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, txt)

            if show_today:
                metrics = QFontMetrics(self._font_header)
                base_width = metrics.horizontalAdvance(txt)
                today_rect = QRect(
                    text_rect.left() + base_width + 6,
                    text_rect.top(),
                    text_rect.width() - base_width - 6,
                    text_rect.height(),
                )
                painter.setPen(self.C_TODAY)
                painter.drawText(today_rect, Qt.AlignVCenter | Qt.AlignLeft, "СЕГОДНЯ")

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.restore()
            return
        if row_type == "sort_header":
            sort_key = index.data(TaskRoles.SortKey) or "date"
            sort_dir = index.data(TaskRoles.SortDirection) or "asc"
            arrow = "▲" if sort_dir == "asc" else "▼"
            painter.fillRect(r, self.C_BG)

            layout = self._row_layout(r)
            painter.setFont(self._font_header)
            painter.setPen(self.C_DIM)
            painter.drawText(layout["date"], Qt.AlignVCenter | Qt.AlignLeft,
                             f"Дата {arrow}" if sort_key == "date" else "Дата")
            painter.drawText(layout["title"], Qt.AlignVCenter | Qt.AlignLeft,
                             f"Название {arrow}" if sort_key == "title" else "Название")
            painter.drawText(layout["priority"], Qt.AlignVCenter | Qt.AlignRight,
                             f"Приоритет {arrow}" if sort_key == "priority" else "Приоритет")

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.restore()
            return

        day: date = index.data(TaskRoles.Day)
        time_text: str = index.data(TaskRoles.DisplayTime) or ""
        title: str = index.data(TaskRoles.Title) or ""
        description: str = index.data(TaskRoles.Description) or ""
        project_title: str = index.data(TaskRoles.ProjectTitle) or ""
        priority: str = index.data(TaskRoles.Priority) or "Medium"
        done: bool = bool(index.data(TaskRoles.Done))
        overdue = self._is_overdue(day, done)
        expanded = bool(index.data(TaskRoles.Expanded))

        bg = self.C_ROW if (index.row() % 2 == 0) else self.C_ROW_ALT
        if option.state & QStyle.State_Selected:
            bg = QColor("#343844")

        painter.fillRect(r, bg)
        painter.setPen(self.C_BORDER)
        painter.drawRect(r.adjusted(0, 0, -1, -1))

        layout = self._row_layout(r)
        cy = r.center().y()

        grip_rect = layout["grip"]
        self._icon_grip.paint(painter, grip_rect)

        cb_rect = layout["checkbox"]
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#16171a"))
        painter.drawRect(cb_rect)

        if done:
            painter.setPen(QColor("#cfcfcf"))
            painter.drawLine(cb_rect.left() + 3, cb_rect.center().y(),
                             cb_rect.center().x() - 1, cb_rect.bottom() - 3)
            painter.drawLine(cb_rect.center().x() - 1, cb_rect.bottom() - 3,
                             cb_rect.right() - 2, cb_rect.top() + 3)

        painter.setFont(self._font_small)
        painter.setPen(self.C_OVERDUE if overdue else self.C_DIM)
        time_rect = layout["date"]
        painter.drawText(time_rect, Qt.AlignVCenter | Qt.AlignLeft, time_text)

        tomorrow_rect = layout["tomorrow"]
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(tomorrow_rect)
        self._icon_tomorrow.paint(painter, QRect(tomorrow_rect.left() + 3, tomorrow_rect.top() + 3, 14, 14))

        project_rect = layout["project"]
        if project_title:
            painter.setFont(self._font_small)
            painter.setPen(self.C_DIM)
            elided_project = QFontMetrics(self._font_small).elidedText(
                project_title,
                Qt.ElideRight,
                project_rect.width(),
            )
            painter.drawText(project_rect, Qt.AlignVCenter | Qt.AlignLeft, elided_project)

        icon_rect = layout["doc"]
        self._icon_doc.paint(painter, icon_rect)

        painter.setFont(self._font)
        if done:
            title_color = self.C_DIM
        elif overdue:
            title_color = self.C_OVERDUE
        else:
            title_color = self.C_TEXT
        painter.setPen(title_color)

        menu_rect = layout["menu"]
        pr_rect = layout["priority"]
        title_rect = layout["title"]
        if expanded:
            title_box = QRect(
                title_rect.left(),
                r.top() + self.TEXT_VPAD,
                title_rect.width(),
                r.height() - self.TEXT_VPAD * 2,
            )
            painter.drawText(title_box, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, title)

            if description:
                title_metrics = QFontMetrics(self._font)
                title_height = title_metrics.boundingRect(
                    0, 0, title_rect.width(), 1000, Qt.TextWordWrap, title
                ).height()
                desc_box = QRect(
                    title_rect.left(),
                    r.top() + self.TEXT_VPAD + title_height + self.TEXT_GAP,
                    title_rect.width(),
                    r.height() - self.TEXT_VPAD * 2 - title_height - self.TEXT_GAP,
                )
                painter.setFont(self._font_small)
                painter.setPen(self.C_DIM if not overdue else self.C_OVERDUE)
                painter.drawText(desc_box, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, description)
                painter.setFont(self._font)
        else:
            elided = QFontMetrics(self._font).elidedText(title, Qt.ElideRight, title_rect.width())
            painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        # --- PRIORITY BLOCK (fixed layout) ---
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
        if row_type == "sort_header":
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                pos = event.position().toPoint()
                layout = self._row_layout(option.rect)
                if layout["title"].contains(pos):
                    if hasattr(model, "set_sort"):
                        model.set_sort("title")
                    return True
                if layout["date"].contains(pos):
                    if hasattr(model, "set_sort"):
                        model.set_sort("date")
                    return True
                if layout["priority"].contains(pos):
                    if hasattr(model, "set_sort"):
                        model.set_sort("priority")
                    return True
            return False
        if row_type != "task":
            return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            r = option.rect
            cy = r.center().y()

            layout = self._row_layout(r)
            cb_rect = layout["checkbox"]
            tomorrow_rect = layout["tomorrow"]
            menu_rect = layout["menu"]

            if tomorrow_rect.contains(pos):
                task = model.task_at_row(index.row()) if hasattr(model, "task_at_row") else None
                if task is not None and hasattr(model, "next_day_for_task"):
                    new_day = model.next_day_for_task(task)
                    model.move_task_to_day(task.id, new_day)
                return True

            if cb_rect.contains(pos):
                # confirm только если ставим done=True
                currently_done = bool(index.data(TaskRoles.Done))
                if not currently_done:
                    parent = option.widget if isinstance(option.widget, QWidget) else None
                    dialog = ConfirmDialog(
                        "Подтверждение",
                        "Пометить задачу выполненной?",
                        parent=parent,
                        confirm_text="Да",
                        cancel_text="Отмена",
                    )
                    if exec_with_overlay(dialog, parent) != QDialog.Accepted:
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
        act_open = menu.addAction("Открыть")
        menu.addSeparator()
        act_edit = menu.addAction("Редактировать")
        # menu.addAction("Проект")
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
        parent = menu.parentWidget() or None
        dialog = ConfirmDialog(
            "Удалить задачу",
            f"Удалить задачу:\n«{title}» ?",
            parent=parent,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, parent) != QDialog.Accepted:
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
        if exec_with_overlay(dialog, parent) != QDialog.Accepted:
            return

        values = dialog.values()
        if hasattr(model, "update_task_by_row"):
            try:
                model.update_task_by_row(
                    index.row(),
                    title=values["title"],
                    description=values["description"],
                    day=values["day"],
                    time_text=values["time_text"],
                    priority=values["priority"],
                    done=values["done"],
                    project_id=values["project_id"],
                )
            except ValueError as exc:
                QMessageBox.warning(parent or self.parent(), "Проверка", str(exc))

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

    def _row_layout(self, r: QRect) -> dict:
        """Возвращает прямоугольники основных колонок строки."""
        x = r.left() + 10
        cy = r.center().y()

        grip_rect = QRect(x, cy - 8, 16, 16)
        x += 22

        cb_rect = QRect(x, cy - 7, 14, 14)
        x += 22

        tomorrow_rect = QRect(x, cy - 8, 20, 20)
        x += 28

        time_rect = QRect(x, r.top(), self.TIME_W, r.height())
        x += self.TIME_W + 6

        project_rect = QRect(x, r.top(), self.PROJECT_W, r.height())
        x += self.PROJECT_W + 6

        doc_rect = QRect(x, cy - 8, 16, 16)
        x += 22

        right_pad = 20
        menu_w = 30
        pr_w = 140
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 6, menu_w, r.height() - 12)
        pr_rect = QRect(menu_rect.left() - pr_w - 8, r.top(), pr_w, r.height())
        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())

        return {
            "grip": grip_rect,
            "checkbox": cb_rect,
            "tomorrow": tomorrow_rect,
            "date": time_rect,
            "project": project_rect,
            "doc": doc_rect,
            "title": title_rect,
            "priority": pr_rect,
            "menu": menu_rect,
        }


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

        self.new_time = QTimeEdit()
        self.new_time.setDisplayFormat("HH:mm")
        self.new_time.setFixedWidth(90)
        self.new_time.setTime(QTime.currentTime())
        self.new_time.setKeyboardTracking(False)

        self.new_time_toggle = QCheckBox("Время")
        self.new_time_toggle.setCursor(Qt.PointingHandCursor)
        self.new_time_toggle.setChecked(False)
        self.new_time.setEnabled(False)
        self.new_time_toggle.toggled.connect(self.new_time.setEnabled)

        datetime_block = QFrame()
        datetime_block.setObjectName("TasksDateTimeBlock")
        datetime_layout = QHBoxLayout(datetime_block)
        datetime_layout.setContentsMargins(6, 2, 6, 2)
        datetime_layout.setSpacing(6)
        datetime_layout.addWidget(self.new_day)
        datetime_layout.addWidget(self.new_time_toggle)
        datetime_layout.addWidget(self.new_time)

        self.new_priority = QComboBox()
        self.new_priority.setFixedWidth(110)
        self.new_priority.addItems(["Low", "Medium", "High"])
        self.new_priority.setCurrentText("Medium")

        self.btn_add = QToolButton()
        self.btn_add.setText("Создать")
        self.btn_add.setCursor(Qt.PointingHandCursor)

        create_layout.addWidget(self.new_title, 1)
        create_layout.addWidget(datetime_block)
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
        self.tab_plan.setChecked(True)

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
        self.list.setUniformItemSizes(False)
        self.list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SingleSelection)
        self.list.setDragDropMode(QAbstractItemView.NoDragDrop)
        root.addWidget(self.list, 1)

        self._focus_day = date.today()
        self.model = TasksModel(self)
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
        self.list.doubleClicked.connect(self._on_task_double_clicked)

        self._update_day_label()
        self._on_tab_changed()

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

            QFrame#TasksCreateBar QComboBox {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock {
                background: #131417;
                border: 1px solid #2a2b2f;
                border-radius: 8px;
            }

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QDateEdit,
            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QTimeEdit {
                background: transparent;
                border: none;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QCheckBox {
                color: #cfcfcf;
                padding: 0 6px;
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
            self._set_drag_drop_state(False)
        elif self.tab_done.isChecked():
            self.model.set_filter_mode("Выполнено")
            self.model.set_focus_day(None)
            self._set_drag_drop_state(False)
        elif self.tab_plan.isChecked():
            self.model.set_filter_mode("План")
            self.model.set_focus_day(None)
            self._set_drag_drop_state(True)
        else:
            self.model.set_filter_mode("Все")
            self.model.set_focus_day(None)
            self._set_drag_drop_state(False)

    def _shift_day(self, delta: int):
        """Сдвигает фокусную дату на указанное число дней."""
        self._focus_day = self._focus_day + timedelta(days=delta)
        self._update_day_label()

        self.tab_today.setChecked(False)
        self.tab_all.setChecked(True)
        self.model.set_filter_mode("Все")
        self.model.set_focus_day(self._focus_day)
        self._set_drag_drop_state(False)

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
        time_text = ""
        if self.new_time_toggle.isChecked():
            time_text = self.new_time.time().toString("HH:mm")

        try:
            self.model.add_task(title=title, day=d, time_text=time_text, priority=pr)
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return

        self.new_title.clear()
        self.new_title.setFocus()

    def _on_task_double_clicked(self, index: QModelIndex):
        """Раскрывает или сворачивает задачу по двойному клику."""
        if not index.isValid():
            return
        if index.data(TaskRoles.RowType) != "task":
            return
        self.model.toggle_expanded_by_row(index.row())

    def set_project_filter(self, project_id: Optional[int]):
        """Обновляет фильтр по проекту."""
        self.model.set_project_filter(project_id)

    def _set_drag_drop_state(self, enabled: bool):
        """Включает или выключает drag and drop списка."""
        if enabled:
            self.list.setDragEnabled(True)
            self.list.setAcceptDrops(True)
            self.list.setDropIndicatorShown(True)
            self.list.setDefaultDropAction(Qt.MoveAction)
            self.list.setDragDropMode(QAbstractItemView.DragDrop)
        else:
            self.list.setDragEnabled(False)
            self.list.setAcceptDrops(False)
            self.list.setDropIndicatorShown(False)
            self.list.setDragDropMode(QAbstractItemView.NoDragDrop)
