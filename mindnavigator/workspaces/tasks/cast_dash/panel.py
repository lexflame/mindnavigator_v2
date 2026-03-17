"""DASH mode panel helpers for TasksWorkspace."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple

from PySide6.QtCore import QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor

from .._shared import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QVBoxLayout,
    QWidget,
)


class _DashChartWidget(QWidget):
    def __init__(self, styler, parent=None) -> None:
        super().__init__(parent)
        self._styler = styler
        self._items: List[Tuple[str, int, QColor]] = []
        self._progress = 1.0
        self._theme_mode = "dark"
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(900)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._on_animation_value_changed)

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        self.update()

    def set_items(self, items: List[Tuple[str, int, QColor]], animate: bool = True) -> None:
        self._items = list(items)
        self._animation.stop()
        if animate:
            self._progress = 0.0
            self._animation.start()
        else:
            self._progress = 1.0
            self.update()

    def _on_animation_value_changed(self, value) -> None:
        self._progress = float(value)
        self.update()


class _DashBarChartWidget(_DashChartWidget):
    def __init__(self, styler, parent=None) -> None:
        super().__init__(styler, parent)
        self.setObjectName("TasksDashBarChart")
        self.setMinimumHeight(260)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self._styler.paint_dash_bar_chart(self, self._items, self._progress, self._theme_mode)


class _DashPieChartWidget(_DashChartWidget):
    def __init__(self, styler, parent=None) -> None:
        super().__init__(styler, parent)
        self.setObjectName("TasksDashPieChart")
        self.setMinimumHeight(260)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self._styler.paint_dash_pie_chart(self, self._items, self._progress, self._theme_mode)


class TasksDashCast:
    """Owns DASH page widgets and dash-specific statistics refresh logic."""

    def __init__(self, workspace, styler) -> None:
        self._workspace = workspace
        self._styler = styler
        self.page: QWidget | None = None
        self.summary_label: QLabel | None = None
        self.bar_chart: _DashBarChartWidget | None = None
        self.pie_chart: _DashPieChartWidget | None = None
        self.pulse_chart: _DashBarChartWidget | None = None
        self.projects_list: QListWidget | None = None

    def build_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.summary_label = QLabel("DASH: пересчет статистики и наполнение диаграмм по выбранному дню.")
        self.summary_label.setObjectName("TasksDashSummary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        charts_host = QWidget(page)
        charts_layout = QHBoxLayout(charts_host)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(8)

        totals_card = QFrame(charts_host)
        totals_card.setObjectName("TasksDashCard")
        totals_layout = QVBoxLayout(totals_card)
        totals_layout.setContentsMargins(10, 10, 10, 10)
        totals_layout.setSpacing(8)
        totals_title = QLabel("Столбичная статистика")
        totals_title.setObjectName("TasksDashChartTitle")
        totals_layout.addWidget(totals_title)
        self.bar_chart = _DashBarChartWidget(self._styler, totals_card)
        totals_layout.addWidget(self.bar_chart, 1)

        distribution_card = QFrame(charts_host)
        distribution_card.setObjectName("TasksDashCard")
        distribution_layout = QVBoxLayout(distribution_card)
        distribution_layout.setContentsMargins(10, 10, 10, 10)
        distribution_layout.setSpacing(8)
        distribution_title = QLabel("Круговая доля сущностей")
        distribution_title.setObjectName("TasksDashChartTitle")
        distribution_layout.addWidget(distribution_title)
        self.pie_chart = _DashPieChartWidget(self._styler, distribution_card)
        distribution_layout.addWidget(self.pie_chart, 1)

        charts_layout.addWidget(totals_card, 1)
        charts_layout.addWidget(distribution_card, 1)
        layout.addWidget(charts_host)

        pulse_card = QFrame(page)
        pulse_card.setObjectName("TasksDashCard")
        pulse_layout = QVBoxLayout(pulse_card)
        pulse_layout.setContentsMargins(10, 10, 10, 10)
        pulse_layout.setSpacing(8)
        pulse_title = QLabel("Пульс результативности")
        pulse_title.setObjectName("TasksDashChartTitle")
        pulse_layout.addWidget(pulse_title)
        self.pulse_chart = _DashBarChartWidget(self._styler, pulse_card)
        self.pulse_chart.setObjectName("TasksDashPulseChart")
        self.pulse_chart.setMinimumHeight(220)
        pulse_layout.addWidget(self.pulse_chart, 1)
        layout.addWidget(pulse_card)

        projects_title = QLabel("Топ проектов по активным задачам")
        projects_title.setObjectName("TasksDashProjectsTitle")
        layout.addWidget(projects_title)

        self.projects_list = QListWidget(page)
        self.projects_list.setObjectName("TasksDashProjectsList")
        self.projects_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.projects_list, 1)

        self.page = page
        return page

    def fetch_tasks_for_focus_day(self) -> List:
        priority_filter = None
        if hasattr(self._workspace, "cmb_priority") and self._workspace.cmb_priority.currentIndex() > 0:
            priority_filter = self._workspace.cmb_priority.currentText()
        tasks = [
            task
            for task in self._workspace._db.fetch_tasks()
            if task.day == self._workspace._focus_day and not task.done
        ]
        if priority_filter is not None:
            tasks = [task for task in tasks if task.priority == priority_filter]
        tasks.sort(
            key=lambda task: (
                self._workspace._parse_task_datetime(task.day, task.time_text),
                task.id,
            )
        )
        return tasks

    def calculate_resultativity(self, all_tasks: List) -> Tuple[int, float]:
        recent_start = self._workspace._focus_day - timedelta(days=1)
        recent_impulse = sum(
            1
            for task in all_tasks
            if task.done and recent_start <= task.day <= self._workspace._focus_day
        )
        previous_completion_days = [
            task.day
            for task in all_tasks
            if task.done and task.day < recent_start
        ]
        if not previous_completion_days:
            return recent_impulse, 0.0

        baseline_span_days = max(1, (recent_start - min(previous_completion_days)).days)
        baseline_impulse = len(previous_completion_days) / (baseline_span_days / 2.0)
        return recent_impulse, baseline_impulse

    def build_pulse_items(self, all_tasks: List) -> List[Tuple[str, int, QColor]]:
        window_start = self._workspace._focus_day - timedelta(days=self._workspace.DASH_PULSE_DAYS - 1)
        recent_start = self._workspace._focus_day - timedelta(days=1)
        completion_counts: Dict[date, int] = {}
        for task in all_tasks:
            if not task.done or task.day < window_start or task.day > self._workspace._focus_day:
                continue
            completion_counts[task.day] = completion_counts.get(task.day, 0) + 1

        items: List[Tuple[str, int, QColor]] = []
        for offset in range(self._workspace.DASH_PULSE_DAYS):
            current_day = window_start + timedelta(days=offset)
            if current_day < recent_start:
                color = QColor("#35536f")
            elif current_day == self._workspace._focus_day:
                color = QColor("#8fe3ff")
            else:
                color = QColor("#4f7ecf")
            items.append((current_day.strftime("%d.%m"), completion_counts.get(current_day, 0), color))
        return items

    def format_resultativity(self, all_tasks: List) -> str:
        recent_impulse, baseline_impulse = self.calculate_resultativity(all_tasks)
        if recent_impulse == 0 and baseline_impulse == 0:
            return "Результативность: нет завершенных задач для сравнения."
        if baseline_impulse <= 0:
            return (
                "Результативность: новый импульс "
                f"{recent_impulse} за последние 2 дня, прошлые периоды для сравнения еще не накоплены."
            )

        ratio = recent_impulse / baseline_impulse
        return (
            f"Результативность: {ratio:.2f}x к прошлому темпу "
            f"(импульс за последние 2 дня {recent_impulse}; "
            f"база прошлых периодов {baseline_impulse:.2f} на 2 дня)."
        )

    def refresh(self) -> None:
        if (
            self.summary_label is None
            or self.projects_list is None
            or self.bar_chart is None
            or self.pie_chart is None
            or self.pulse_chart is None
        ):
            return
        all_tasks = self._workspace._db.fetch_tasks()
        all_projects = self._workspace._db.fetch_projects()
        all_maps = self._workspace._db.fetch_maps()
        all_markers = self._workspace._db.fetch_map_markers()
        all_objects = self._workspace._db.fetch_objects()
        all_notes = self._workspace._db.fetch_notes()

        tasks = self.fetch_tasks_for_focus_day()
        total = len(tasks)
        high = sum(1 for task in tasks if task.priority == "High")
        medium = sum(1 for task in tasks if task.priority == "Medium")
        low = sum(1 for task in tasks if task.priority == "Low")
        deferred = sum(1 for task in tasks if task.priority == "Отложенная")
        entity_items = [
            ("Задачи", len(all_tasks), QColor("#4f7ecf")),
            ("Проекты", len(all_projects), QColor("#59c3c3")),
            ("Карты", len(all_maps), QColor("#f4a261")),
            ("Метки", len(all_markers), QColor("#e76f51")),
            ("Объекты", len(all_objects), QColor("#90be6d")),
            ("Заметки", len(all_notes), QColor("#e9c46a")),
        ]
        self.bar_chart.set_items(entity_items, animate=True)
        self.pie_chart.set_items(entity_items, animate=True)
        self.pulse_chart.set_items(self.build_pulse_items(all_tasks), animate=True)
        self.summary_label.setText(
            (
                f"DASH на {self._workspace._focus_day.isoformat()}: диаграммы пересчитаны и заполнены заново.\n"
                f"На {self._workspace._focus_day.isoformat()}: "
                f"активных задач {total}, High {high}, Medium {medium}, Low {low}, Отложенных {deferred}.\n"
                f"{self.format_resultativity(all_tasks)}"
            )
        )

        projects = {project.id: project for project in all_projects if not project.archived}
        counts: Dict[int, int] = {}
        for task in tasks:
            if task.project_id is None:
                continue
            counts[task.project_id] = counts.get(task.project_id, 0) + 1
        ranked = sorted(
            counts.items(),
            key=lambda entry: (
                -entry[1],
                (projects.get(entry[0]).title if projects.get(entry[0]) else "").lower(),
                entry[0],
            ),
        )[:12]
        self.projects_list.clear()
        for project_id, count in ranked:
            project = projects.get(project_id)
            if project is None:
                continue
            self.projects_list.addItem(f"{project.area} · {project.title} ({count})")
