"""Styling helpers for the Tasks workspace."""

from __future__ import annotations

import math
from typing import List, Tuple

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import QTableWidget, QWidget

from mindnavigator.ui.styles import get_theme_palette

from ..tasks_item_delegate import TasksItemDelegate


class TasksWorkspaceStyle:
    """Owns theme stylesheet generation and custom paint helpers for Tasks."""

    def __init__(self, workspace) -> None:
        self._workspace = workspace

    @staticmethod
    def normalize_theme_mode(theme_mode: str) -> str:
        return "light" if str(theme_mode).strip().lower() == "light" else "dark"

    def build_workspace_stylesheet(self, theme_mode: str) -> str:
        palette = get_theme_palette(theme_mode)
        return f"""
            QWidget#TasksWorkspace {{ background: {palette.window_bg}; }}

            QFrame#TasksCreateBar {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
            }}

            QFrame#TasksCreateBar QLineEdit {{
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                padding: 6px 8px;
                color: {palette.text};
            }}

            QFrame#TasksCreateBar QComboBox {{
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                padding: 4px 6px;
                color: {palette.text};
            }}

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock {{
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QDateEdit,
            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QTimeEdit {{
                background: transparent;
                border: none;
                padding: 4px 6px;
                color: {palette.text};
            }}

            QFrame#TasksCreateBar QFrame#TasksDateTimeBlock QCheckBox {{
                color: {palette.text};
                padding: 0 6px;
            }}

            QFrame#TasksCreateBar QToolButton {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border_strong};
                padding: 6px 10px;
                border-radius: 6px;
                color: {palette.text};
            }}
            QFrame#TasksCreateBar QToolButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}

            QToolButton {{
                color: {palette.text};
                border: none;
                padding: 6px 8px;
            }}
            QToolButton:checked {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}

            QWidget#TasksHavenHost {{
                background: transparent;
            }}
            QFrame#TasksHavenBadge {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border_strong};
                border-radius: 8px;
            }}
            QLabel#TasksHavenBadgeLabel {{
                color: {palette.text};
                font-weight: 600;
            }}
            QToolButton#TasksHavenClearButton {{
                color: {palette.dim_text};
                border: none;
                padding: 0px 5px;
                min-width: 18px;
            }}
            QToolButton#TasksHavenClearButton:hover {{
                color: {palette.selection_text};
                background: {palette.selection_bg};
                border-radius: 6px;
            }}

            QLabel#TasksDayLabel {{
                color: {palette.text};
                padding: 0px 6px;
            }}

            QComboBox, QLineEdit {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 6px 8px;
            }}

            QListView#TasksList {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
            }}
            QFrame#TasksBatchBar {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border_strong};
                border-radius: 12px;
            }}
            QLabel#TasksBatchSelectionLabel {{
                color: {palette.text};
                font-weight: 600;
            }}
            QLabel#TasksBatchHintLabel {{
                color: {palette.dim_text};
            }}
            QComboBox#TasksBatchAction,
            QComboBox#TasksBatchProject,
            QComboBox#TasksBatchMarkerColor,
            QComboBox#TasksBatchMarkerTheme,
            QDateEdit#TasksBatchDateEdit {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 8px;
                padding: 5px 8px;
            }}
            QToolButton#TasksBatchApplyButton,
            QToolButton#TasksBatchClearButton {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 8px;
                padding: 6px 10px;
            }}
            QToolButton#TasksBatchApplyButton:hover,
            QToolButton#TasksBatchClearButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QLabel#TasksStickyHeader {{
                background: {palette.window_bg};
                color: {palette.dim_text};
                border-bottom: 1px solid {palette.border_strong};
                font-size: 9pt;
                font-weight: 600;
                padding: 0 10px;
            }}

            QTableWidget#TasksGanttTable {{
                background: {palette.window_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                gridline-color: {palette.border};
                alternate-background-color: {palette.panel_alt_bg};
                selection-background-color: {palette.selection_bg};
                selection-color: {palette.selection_text};
            }}

            QTableWidget#TasksGanttTable::item {{
                padding: 4px 6px;
            }}

            QTableWidget#TasksGanttTable QHeaderView::section {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 4px 6px;
            }}

            QTableWidget#TasksGanttTable QTableCornerButton::section {{
                background: {palette.input_bg};
                border: 1px solid {palette.border};
            }}

            QTableWidget#TasksGanttTable QLineEdit,
            QTableWidget#TasksGanttTable QSpinBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 2px 6px;
            }}

            QTableWidget#TasksGanttTable QSpinBox::up-button,
            QTableWidget#TasksGanttTable QSpinBox::down-button {{
                background: {palette.elevated_bg};
                border-left: 1px solid {palette.border_strong};
                width: 14px;
            }}

            QTableWidget#TasksGanttTable QSpinBox::up-button:hover,
            QTableWidget#TasksGanttTable QSpinBox::down-button:hover {{
                background: {palette.selection_bg};
            }}

            QLabel#TasksGanttHint {{
                color: {palette.dim_text};
                padding: 2px 4px;
            }}

            QLabel#TasksBoardHint,
            QLabel#TasksDashSummary,
            QLabel#TasksDashProjectsTitle,
            QLabel#TasksDashChartTitle {{
                color: {palette.dim_text};
                padding: 2px 4px;
            }}

            QCheckBox#TasksBoardDayFilter {{
                color: {"#ffffff" if theme_mode == "dark" else palette.text};
                padding: 2px 4px;
            }}

            QFrame#TasksDashCard {{
                background: {palette.panel_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}

            QFrame#TasksBoardColumn {{
                background: {palette.panel_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}

            QLabel#TasksBoardColumnTitle {{
                color: {palette.text};
                font-weight: 600;
                padding: 2px 4px;
            }}

            QListWidget#TasksBoardList,
            QListWidget#TasksDashProjectsList {{
                background: {palette.window_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 6px;
            }}

            QListWidget#TasksBoardList::item,
            QListWidget#TasksDashProjectsList::item {{
                padding: 4px 6px;
                border-bottom: 1px solid {palette.border};
            }}
        """

    def apply_gantt_palette(self, gantt_table: QTableWidget | None, theme_mode: str | None = None) -> None:
        if not isinstance(gantt_table, QTableWidget):
            return
        palette = get_theme_palette(theme_mode or self._workspace._theme_mode)
        table_palette = gantt_table.palette()
        table_palette.setColor(QPalette.ColorRole.Base, QColor(palette.window_bg))
        table_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(palette.panel_alt_bg))
        table_palette.setColor(QPalette.ColorRole.Text, QColor(palette.text))
        table_palette.setColor(QPalette.ColorRole.Mid, QColor(palette.border_strong))
        table_palette.setColor(QPalette.ColorRole.Highlight, QColor(palette.accent))
        table_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(palette.selection_text))
        gantt_table.setPalette(table_palette)

    def apply_theme(self, theme_mode: str) -> None:
        normalized_mode = self.normalize_theme_mode(theme_mode)
        self._workspace._theme_mode = normalized_mode
        self._workspace.setStyleSheet(self.build_workspace_stylesheet(normalized_mode))
        self.apply_gantt_palette(getattr(self._workspace, "gantt_table", None), normalized_mode)

        delegate = getattr(self._workspace, "delegate", None)
        if isinstance(delegate, TasksItemDelegate):
            delegate.set_theme_mode(normalized_mode)
            tasks_list = getattr(self._workspace, "list", None)
            if tasks_list is not None and tasks_list.viewport() is not None:
                tasks_list.viewport().update()

        for chart_widget in (
            getattr(self._workspace, "dash_bar_chart", None),
            getattr(self._workspace, "dash_pie_chart", None),
            getattr(self._workspace, "dash_pulse_chart", None),
        ):
            set_theme_mode = getattr(chart_widget, "set_theme_mode", None)
            if callable(set_theme_mode):
                set_theme_mode(normalized_mode)

    def paint_dash_bar_chart(
        self,
        widget: QWidget,
        items: List[Tuple[str, int, QColor]],
        progress: float,
        theme_mode: str,
    ) -> None:
        palette = get_theme_palette(theme_mode)
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(widget.rect(), QColor(palette.chart_bg))
        chart_rect = widget.rect().adjusted(18, 18, -18, -18)
        if chart_rect.width() <= 0 or chart_rect.height() <= 0:
            return
        if not items:
            painter.setPen(QColor(palette.chart_muted))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Нет данных")
            return

        plot_rect = QRect(
            chart_rect.left() + 8,
            chart_rect.top() + 14,
            max(10, chart_rect.width() - 16),
            max(10, chart_rect.height() - 62),
        )
        baseline_y = plot_rect.bottom()
        painter.setPen(QColor(palette.chart_grid))
        painter.drawLine(plot_rect.left(), baseline_y, plot_rect.right(), baseline_y)

        max_value = max((value for _, value, _ in items), default=0)
        if max_value <= 0:
            max_value = 1
        slot_width = plot_rect.width() / max(1, len(items))
        bar_width = max(24, int(slot_width * 0.52))
        animated_values = [value * progress for _, value, _ in items]

        value_font = painter.font()
        value_font.setPointSize(max(8, value_font.pointSize() - 1))
        label_font = painter.font()
        label_font.setPointSize(max(8, label_font.pointSize() - 1))

        for index, (label, _value, color) in enumerate(items):
            center_x = plot_rect.left() + int(slot_width * index + slot_width / 2.0)
            current_value = animated_values[index]
            bar_height = int(plot_rect.height() * current_value / max_value)
            bar_rect = QRect(
                center_x - bar_width // 2,
                baseline_y - bar_height,
                bar_width,
                max(4, bar_height),
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(bar_rect, 8, 8)

            painter.setPen(QColor(palette.chart_text))
            painter.setFont(value_font)
            value_rect = QRect(center_x - 32, max(chart_rect.top(), bar_rect.top() - 24), 64, 18)
            painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, str(int(round(current_value))))

            painter.setPen(QColor(palette.chart_muted))
            painter.setFont(label_font)
            label_rect = QRect(center_x - int(slot_width / 2), baseline_y + 10, int(slot_width), 32)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                label,
            )

    def paint_dash_pie_chart(
        self,
        widget: QWidget,
        items: List[Tuple[str, int, QColor]],
        progress: float,
        theme_mode: str,
    ) -> None:
        palette = get_theme_palette(theme_mode)
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(widget.rect(), QColor(palette.chart_bg))
        chart_rect = widget.rect().adjusted(18, 18, -18, -18)
        if chart_rect.width() <= 0 or chart_rect.height() <= 0:
            return
        if not items:
            painter.setPen(QColor(palette.chart_muted))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Нет данных")
            return

        total = sum(value for _, value, _ in items)
        if total <= 0:
            painter.setPen(QColor(palette.chart_muted))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Нет данных")
            return

        legend_width = 150 if chart_rect.width() >= 430 else 0
        pie_side = min(chart_rect.width() - legend_width - 12, chart_rect.height())
        pie_side = max(120, pie_side)
        pie_rect = QRect(chart_rect.left(), chart_rect.top(), pie_side, pie_side)
        if legend_width > 0:
            pie_rect.moveTop(chart_rect.top() + max(0, (chart_rect.height() - pie_side) // 2))
        else:
            pie_rect.moveLeft(chart_rect.left() + max(0, (chart_rect.width() - pie_side) // 2))

        painter.setPen(QColor(palette.chart_grid))
        painter.setBrush(QColor(palette.panel_alt_bg))
        painter.drawEllipse(pie_rect)

        total_angle = int(round(360.0 * 16 * progress))
        start_angle = 90 * 16
        remaining_angle = total_angle
        for _label, value, color in items:
            span_angle = int(round((value / total) * 360.0 * 16))
            draw_angle = min(span_angle, remaining_angle)
            if draw_angle > 0:
                painter.setPen(QColor(palette.chart_bg))
                painter.setBrush(color)
                painter.drawPie(pie_rect, start_angle, -draw_angle)
                start_angle -= draw_angle
                remaining_angle -= draw_angle

        inner_rect = pie_rect.adjusted(
            pie_rect.width() // 4,
            pie_rect.height() // 4,
            -pie_rect.width() // 4,
            -pie_rect.height() // 4,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette.chart_bg))
        painter.drawEllipse(inner_rect)

        painter.setPen(QColor(palette.chart_text))
        total_font = painter.font()
        total_font.setPointSize(max(10, total_font.pointSize() + 1))
        total_font.setBold(True)
        painter.setFont(total_font)
        painter.drawText(
            inner_rect.adjusted(0, -8, 0, 0),
            Qt.AlignmentFlag.AlignCenter,
            str(int(round(total * progress))),
        )
        painter.setPen(QColor(palette.chart_muted))
        small_font = painter.font()
        small_font.setPointSize(max(8, small_font.pointSize() - 1))
        small_font.setBold(False)
        painter.setFont(small_font)
        painter.drawText(inner_rect.adjusted(0, 18, 0, 0), Qt.AlignmentFlag.AlignCenter, "всего")

        legend_left = pie_rect.right() + 18 if legend_width > 0 else chart_rect.left()
        legend_top = chart_rect.top() if legend_width > 0 else pie_rect.bottom() + 16
        row_height = 24
        for index, (label, value, color) in enumerate(items):
            row_y = legend_top + index * row_height
            if row_y + row_height > chart_rect.bottom() + 1:
                break
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QRect(legend_left, row_y + 5, 12, 12))
            painter.setPen(QColor(palette.chart_text))
            painter.drawText(
                QRect(legend_left + 20, row_y, 96, row_height),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                label,
            )
            painter.setPen(QColor(palette.chart_muted))
            painter.drawText(
                QRect(legend_left + 106, row_y, 42, row_height),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                str(value),
            )

    def paint_gantt_bar(
        self,
        widget: QWidget,
        start_minutes: int,
        end_minutes: int,
        day_start: int,
        day_end: int,
    ) -> None:
        painter = QPainter(widget)
        rect = widget.rect().adjusted(2, 3, -2, -3)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        palette = widget.palette()
        border_color = palette.mid().color()
        track_color = palette.alternateBase().color()
        accent_color = palette.highlight().color()
        label_color = palette.text().color()
        label_color.setAlpha(210)
        minor_tick_color = palette.mid().color()
        minor_tick_color.setAlpha(120)
        if track_color.lightness() > 120:
            border_color = QColor("#3a3b40")
            track_color = QColor("#1f2227")
            accent_color = QColor("#4f7ecf")
            label_color = QColor("#b3b7c2")
            minor_tick_color = QColor("#43464d")

        painter.setPen(border_color)
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect, 4, 4)

        span = max(1, day_end - day_start)
        label_height = max(12, widget.fontMetrics().height())
        tick_bottom = rect.bottom() - label_height - 4
        if tick_bottom <= rect.top() + 6:
            tick_bottom = rect.center().y()
        for hour in range(day_start // 60, day_end // 60 + 1):
            minute_mark = hour * 60
            x = rect.left() + int((minute_mark - day_start) / span * rect.width())
            strong_tick = (hour % 2 == 0) or (minute_mark == day_start) or (minute_mark == day_end)
            tick_color = border_color if strong_tick else minor_tick_color
            painter.setPen(tick_color)
            painter.drawLine(x, rect.top() + 1, x, tick_bottom)
            if strong_tick:
                label_rect = QRect(x - 14, tick_bottom + 2, 28, label_height)
                painter.setPen(label_color)
                painter.drawText(
                    label_rect,
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                    f"{hour:02d}",
                )

        start_clamped = min(max(start_minutes, day_start), day_end)
        end_clamped = min(max(end_minutes, day_start), day_end)
        if end_clamped <= start_clamped:
            return

        x1 = rect.left() + int((start_clamped - day_start) / span * rect.width())
        x2 = rect.left() + int((end_clamped - day_start) / span * rect.width())
        bar = QRect(x1, rect.top() + 1, max(2, x2 - x1), max(2, tick_bottom - rect.top() - 1))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent_color)
        painter.drawRoundedRect(bar, 4, 4)

    def paint_gantt_clock(
        self,
        widget: QWidget,
        start_minutes: int,
        end_minutes: int,
    ) -> None:
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = widget.rect().adjusted(4, 4, -4, -4)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        palette = widget.palette()
        border_color = palette.mid().color()
        face_color = palette.alternateBase().color()
        accent_color = palette.highlight().color()
        text_color = palette.text().color()
        text_color.setAlpha(210)
        tick_color = palette.mid().color()
        tick_color.setAlpha(140)
        if face_color.lightness() > 120:
            border_color = QColor("#3a3b40")
            face_color = QColor("#1f2227")
            accent_color = QColor("#4f7ecf")
            text_color = QColor("#b3b7c2")
            tick_color = QColor("#43464d")

        radius = max(10.0, min(rect.width(), rect.height()) / 2.0 - 2.0)
        center_x = rect.center().x()
        center_y = rect.center().y()

        def point_for(total_minutes: float, factor: float) -> tuple[float, float]:
            minute_on_dial = total_minutes % 720.0
            angle_rad = math.radians(minute_on_dial * 0.5 - 90.0)
            return (
                center_x + math.cos(angle_rad) * radius * factor,
                center_y + math.sin(angle_rad) * radius * factor,
            )

        painter.setPen(border_color)
        painter.setBrush(face_color)
        painter.drawEllipse(rect.center(), int(radius), int(radius))

        for hour in range(12):
            outer_x, outer_y = point_for(hour * 60.0, 1.0)
            inner_x, inner_y = point_for(hour * 60.0, 0.82 if hour % 3 == 0 else 0.88)
            painter.setPen(border_color if hour % 3 == 0 else tick_color)
            painter.drawLine(int(inner_x), int(inner_y), int(outer_x), int(outer_y))

        duration_minutes = max(0, int(end_minutes - start_minutes))
        if duration_minutes > 0:
            steps = max(6, min(48, duration_minutes // 10 or 1))
            polygon = [rect.center()]
            for step in range(steps + 1):
                current_minutes = float(start_minutes) + duration_minutes * step / steps
                x, y = point_for(current_minutes, 0.76)
                polygon.append(QPoint(int(x), int(y)))
            painter.setPen(Qt.PenStyle.NoPen)
            fill_color = QColor(accent_color)
            fill_color.setAlpha(110)
            painter.setBrush(fill_color)
            painter.drawPolygon(polygon)

        start_x, start_y = point_for(float(start_minutes), 0.8)
        end_x, end_y = point_for(float(end_minutes), 0.62)
        painter.setPen(QColor(accent_color))
        painter.drawLine(rect.center(), QPoint(int(start_x), int(start_y)))
        painter.setPen(QColor(text_color))
        painter.drawLine(rect.center(), QPoint(int(end_x), int(end_y)))
        painter.setBrush(accent_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect.center(), 3, 3)

        painter.setPen(text_color)
        painter.drawText(
            rect.adjusted(0, 0, 0, -2),
            Qt.AlignmentFlag.AlignCenter,
            f"{max(0, duration_minutes // 60):02d}:{max(0, duration_minutes % 60):02d}",
        )
