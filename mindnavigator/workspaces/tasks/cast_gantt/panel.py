"""GANTT mode panel helpers for TasksWorkspace."""

from __future__ import annotations

from datetime import datetime, timedelta

from .._shared import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from ..gantt_duration_edit import GanttEstimateEdit, format_gantt_estimate_minutes


class _GanttBarWidget(QWidget):
    _MIN_HEIGHT = 34

    def __init__(self, styler, start_minutes: int, end_minutes: int, day_start: int, day_end: int, parent=None):
        super().__init__(parent)
        self._styler = styler
        self._start = int(start_minutes)
        self._end = int(end_minutes)
        self._day_start = int(day_start)
        self._day_end = int(day_end)
        self.setObjectName("TasksGanttTimelineWidget")
        self.setMinimumHeight(self._MIN_HEIGHT)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self._styler.paint_gantt_bar(self, self._start, self._end, self._day_start, self._day_end)


class _GanttClockWidget(QWidget):
    _MIN_HEIGHT = 40

    def __init__(self, styler, start_minutes: int, end_minutes: int, parent=None):
        super().__init__(parent)
        self._styler = styler
        self._start = int(start_minutes)
        self._end = int(end_minutes)
        self.setObjectName("TasksGanttClockWidget")
        self.setMinimumHeight(self._MIN_HEIGHT)
        self.setMinimumWidth(76)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self._styler.paint_gantt_clock(self, self._start, self._end)


class TasksGanttCast:
    """Owns GANTT page widgets and gantt-specific data refresh logic."""

    _ROW_HEIGHT = 56

    def __init__(self, workspace, styler) -> None:
        self._workspace = workspace
        self._styler = styler
        self._view_mode = "timeline"
        self.page: QWidget | None = None
        self.hint_label: QLabel | None = None
        self.table: QTableWidget | None = None
        self.view_combo: QComboBox | None = None

    def build_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        controls_row = QWidget(page)
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        view_label = QLabel("Вид:", controls_row)
        view_label.setObjectName("TasksGanttViewLabel")
        controls_layout.addWidget(view_label)

        self.view_combo = QComboBox(controls_row)
        self.view_combo.setObjectName("TasksGanttViewCombo")
        self.view_combo.addItem("Шкала времени", "timeline")
        self.view_combo.addItem("Циферблат", "clock")
        self.view_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        controls_layout.addWidget(self.view_combo)
        controls_layout.addStretch(1)
        layout.addWidget(controls_row)

        self.hint_label = QLabel(
            "Режим Gantt: прогноз длительности строится автоматически и сохраняется."
        )
        self.hint_label.setObjectName("TasksGanttHint")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self.table = QTableWidget(0, 6, page)
        self.table.setObjectName("TasksGanttTable")
        self.table.setHorizontalHeaderLabels(
            ["Задача", "Срок", "Старт", "Финиш", "Лента", "Минуты"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._styler.apply_gantt_palette(self.table, self._workspace._theme_mode)
        self._update_timeline_header()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        self.page = page
        return page

    def _on_view_mode_changed(self, _index: int) -> None:
        if self.view_combo is None:
            return
        next_mode = str(self.view_combo.currentData() or "timeline")
        if next_mode == self._view_mode:
            return
        self._view_mode = next_mode
        self._update_timeline_header()
        self.refresh()

    def _update_timeline_header(self) -> None:
        if self.table is None:
            return
        label = "Циферблат" if self._view_mode == "clock" else "Шкала"
        header_item = self.table.horizontalHeaderItem(4)
        if header_item is not None:
            header_item.setText(label)

    @staticmethod
    def estimate_task_minutes(task) -> int:
        text = f"{task.title} {task.description or ''}".lower()
        words = len((task.description or "").split())
        base = 50
        if task.priority == "High":
            base = 90
        elif task.priority == "Low":
            base = 35
        elif task.priority == "Отложенная":
            base = 25
        complexity_markers = [
            "исследование", "архитектура", "интеграция", "рефакторинг", "оптимизация",
            "debug", "тест", "документация", "design", "api", "sql",
            "миграция", "парсинг", "настройка", "синхрон",
        ]
        marker_hits = sum(1 for marker in complexity_markers if marker in text)
        raw = base + words * 2 + marker_hits * 15
        return max(15, min(8 * 60, int(round(raw / 5.0) * 5)))

    def refresh(self) -> None:
        if self.table is None or self.hint_label is None:
            return
        db = self._workspace._db
        priority_filter = None
        if hasattr(self._workspace, "cmb_priority") and self._workspace.cmb_priority.currentIndex() > 0:
            priority_filter = self._workspace.cmb_priority.currentText()
        tasks = [
            task
            for task in db.fetch_tasks()
            if task.day == self._workspace._focus_day
            and not task.done
            and task.priority != "Отложенная"
            and (priority_filter is None or task.priority == priority_filter)
        ]
        tasks.sort(
            key=lambda task: (
                self._workspace._parse_task_datetime(task.day, task.time_text),
                task.id,
            )
        )

        predicted = 0
        for task in tasks:
            if not task.gantt_forecasted or task.gantt_estimate_minutes <= 0:
                db.set_task_gantt_estimate(task.id, self.estimate_task_minutes(task), forecasted=True)
                predicted += 1
        if predicted:
            tasks = [
                task
                for task in db.fetch_tasks()
                if task.day == self._workspace._focus_day
                and not task.done
                and task.priority != "Отложенная"
                and (priority_filter is None or task.priority == priority_filter)
            ]
            tasks.sort(
                key=lambda task: (
                    self._workspace._parse_task_datetime(task.day, task.time_text),
                    task.id,
                )
            )

        self.table.setRowCount(0)
        if not tasks:
            self.hint_label.setText("На выбранный день нет активных задач для диаграммы Gantt.")
            return

        cursor = datetime.combine(self._workspace._focus_day, datetime.strptime("09:00", "%H:%M").time())
        total_minutes = 0
        day_start_minutes = self._workspace.GANTT_DAY_START_HOUR * 60
        day_end_minutes = self._workspace.GANTT_DAY_END_HOUR * 60
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            pref_dt = self._workspace._parse_task_datetime(task.day, task.time_text)
            start_dt = max(cursor, pref_dt)
            estimate = max(15, int(task.gantt_estimate_minutes or 0))
            end_dt = start_dt + timedelta(minutes=estimate)
            cursor = end_dt
            total_minutes += estimate

            self.table.setItem(row, 0, QTableWidgetItem(task.title))
            self.table.setItem(row, 1, QTableWidgetItem(task.time_text or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(start_dt.strftime("%H:%M")))
            self.table.setItem(row, 3, QTableWidgetItem(end_dt.strftime("%H:%M")))

            start_minutes = start_dt.hour * 60 + start_dt.minute
            end_minutes = end_dt.hour * 60 + end_dt.minute
            if self._view_mode == "clock":
                gantt_widget = _GanttClockWidget(
                    styler=self._styler,
                    start_minutes=start_minutes,
                    end_minutes=end_minutes,
                    parent=self.table,
                )
            else:
                gantt_widget = _GanttBarWidget(
                    styler=self._styler,
                    start_minutes=start_minutes,
                    end_minutes=end_minutes,
                    day_start=day_start_minutes,
                    day_end=day_end_minutes,
                    parent=self.table,
                )
            self.table.setCellWidget(row, 4, gantt_widget)
            self.table.setRowHeight(row, self._ROW_HEIGHT)

            duration_edit = GanttEstimateEdit(estimate, self.table)
            duration_edit.setEnabled(bool(task.gantt_forecasted))
            duration_edit.setToolTip(format_gantt_estimate_minutes(estimate))
            duration_edit.minutesCommitted.connect(
                lambda value, task_id=task.id: self.on_minutes_changed(task_id, value)
            )
            self.table.setCellWidget(row, 5, duration_edit)

        total_hours = total_minutes / 60.0
        self.hint_label.setText(
            f"Gantt на {self._workspace._focus_day.isoformat()}: {len(tasks)} задач, {total_minutes} мин (~{total_hours:.1f} ч)."
        )

    def on_minutes_changed(self, task_id: int, minutes: int) -> None:
        self._workspace._db.set_task_gantt_estimate(task_id, minutes, forecasted=True)
        self.refresh()
