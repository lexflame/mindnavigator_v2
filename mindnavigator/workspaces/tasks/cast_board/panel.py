"""BOARD mode panel helpers for TasksWorkspace."""

from __future__ import annotations

from typing import Dict, List

from .._shared import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
    normalize_board_column,
)


class _BoardColumnListWidget(QListWidget):
    _drag_task_id: int | None = None

    def __init__(self, workspace, board_column: str, parent=None) -> None:
        super().__init__(parent)
        self._workspace = workspace
        self._board_column = board_column
        self.setObjectName("TasksBoardList")
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def startDrag(self, supported_actions: Qt.DropActions) -> None:
        current_item = self.currentItem()
        try:
            type(self)._drag_task_id = int(current_item.data(Qt.ItemDataRole.UserRole)) if current_item else None
        except (TypeError, ValueError):
            type(self)._drag_task_id = None
        super().startDrag(supported_actions)

    def dropEvent(self, event) -> None:
        if event.source() is self:
            event.ignore()
            type(self)._drag_task_id = None
            return
        task_id = type(self)._drag_task_id
        super().dropEvent(event)
        type(self)._drag_task_id = None
        if task_id is None or not event.isAccepted():
            return
        self._workspace._move_task_to_board_column(task_id, self._board_column)


class TasksBoardCast:
    """Owns BOARD page widgets and board-specific data refresh logic."""

    def __init__(self, workspace) -> None:
        self._workspace = workspace
        self.page: QWidget | None = None
        self.day_filter_checkbox: QCheckBox | None = None
        self.columns: Dict[str, QListWidget] = {}

    def build_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        board_hint = QLabel(
            "Режим Board: 4 локальные колонки важности на выбранный день, отдельно от приоритета задачи."
        )
        board_hint.setObjectName("TasksBoardHint")
        board_hint.setWordWrap(True)
        layout.addWidget(board_hint)

        board_options_row = QWidget(page)
        board_options_layout = QHBoxLayout(board_options_row)
        board_options_layout.setContentsMargins(0, 0, 0, 0)
        board_options_layout.setSpacing(8)
        self.day_filter_checkbox = QCheckBox("Фильтрация по дню", board_options_row)
        self.day_filter_checkbox.setObjectName("TasksBoardDayFilter")
        self.day_filter_checkbox.setChecked(bool(self._workspace._board_day_filter_enabled))
        self.day_filter_checkbox.toggled.connect(self._workspace._on_board_day_filter_toggled)
        board_options_layout.addWidget(self.day_filter_checkbox)
        board_options_layout.addStretch(1)
        layout.addWidget(board_options_row)

        columns_host = QWidget(page)
        columns_layout = QHBoxLayout(columns_host)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(8)

        self.columns = {}
        for board_column, header in self._workspace.BOARD_COLUMN_ORDER:
            column_frame = QFrame(columns_host)
            column_frame.setObjectName("TasksBoardColumn")
            column_layout = QVBoxLayout(column_frame)
            column_layout.setContentsMargins(8, 8, 8, 8)
            column_layout.setSpacing(6)

            label = QLabel(header)
            label.setObjectName("TasksBoardColumnTitle")
            column_layout.addWidget(label)

            list_widget = _BoardColumnListWidget(self._workspace, board_column, column_frame)
            column_layout.addWidget(list_widget, 1)
            columns_layout.addWidget(column_frame, 1)
            self.columns[board_column] = list_widget

        layout.addWidget(columns_host, 1)
        self.page = page
        return page

    def is_day_filter_enabled(self) -> bool:
        if isinstance(self.day_filter_checkbox, QCheckBox):
            self._workspace._board_day_filter_enabled = self.day_filter_checkbox.isChecked()
        return bool(self._workspace._board_day_filter_enabled)

    def set_day_filter_checked(self, enabled: bool) -> None:
        self._workspace._board_day_filter_enabled = bool(enabled)
        if isinstance(self.day_filter_checkbox, QCheckBox):
            self.day_filter_checkbox.blockSignals(True)
            self.day_filter_checkbox.setChecked(self._workspace._board_day_filter_enabled)
            self.day_filter_checkbox.blockSignals(False)

    def format_task_text(self, task) -> str:
        time_text = task.time_text or "—"
        if self.is_day_filter_enabled():
            return f"{time_text} · {task.title}"
        return f"{task.day.isoformat()} · {time_text} · {task.title}"

    def collect_tasks(self) -> List:
        priority_filter = None
        if hasattr(self._workspace, "cmb_priority") and self._workspace.cmb_priority.currentIndex() > 0:
            priority_filter = self._workspace.cmb_priority.currentText()
        filter_by_day = self.is_day_filter_enabled()
        tasks = [
            task
            for task in self._workspace._db.fetch_tasks()
            if not task.done and (not filter_by_day or task.day == self._workspace._focus_day)
        ]
        if priority_filter is not None:
            tasks = [task for task in tasks if task.priority == priority_filter]
        tasks.sort(
            key=lambda task: (
                task.day,
                self._workspace._parse_task_datetime(task.day, task.time_text),
                task.id,
            )
        )
        return tasks

    def refresh(self) -> None:
        if not self.columns:
            return
        tasks = self.collect_tasks()
        grouped: Dict[str, List] = {
            board_column: [] for board_column, _header in self._workspace.BOARD_COLUMN_ORDER
        }
        for task in tasks:
            board_column = normalize_board_column(getattr(task, "board_column", ""), task.priority)
            grouped.setdefault(board_column, []).append(task)
        for board_column, list_widget in self.columns.items():
            list_widget.clear()
            for task in grouped.get(board_column, []):
                item = QListWidgetItem(self.format_task_text(task))
                item.setData(Qt.ItemDataRole.UserRole, task.id)
                if task.project_title:
                    item.setToolTip(task.project_title)
                list_widget.addItem(item)

    def move_task_to_column(self, task_id: int, board_column: str) -> None:
        self._workspace._db.set_task_board_column(task_id, board_column)
        self._workspace.refresh()
