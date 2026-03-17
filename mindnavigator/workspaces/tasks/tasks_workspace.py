"""TasksWorkspace class module for tasks workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .task_create_dialog import TaskCreateDialog
from .tasks_item_delegate import TasksItemDelegate
from .tasks_model import TasksModel
from mindnavigator.ui.styles import get_theme_palette

class TasksWorkspace(BaseWorkspace):
    """Рабочая область задач: панель управления и список с группировкой."""

    workspace_id = "tasks"
    workspace_title = "Задачи"
    DASH_PULSE_DAYS = 6
    GANTT_DAY_START_HOUR = 8
    GANTT_DAY_END_HOUR = 22
    BOARD_COLUMN_ORDER = [
        (BOARD_COLUMN_DEFERRED, "Отложенные"),
        (BOARD_COLUMN_QUEUE, "В очереди"),
        (BOARD_COLUMN_IN_PROGRESS, "Выполняется"),
        (BOARD_COLUMN_COMPLETED, "Выполнена"),
    ]

    class _BoardColumnListWidget(QListWidget):
        _drag_task_id: int | None = None

        def __init__(self, workspace: "TasksWorkspace", board_column: str, parent=None) -> None:
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

    class _DashChartWidget(QWidget):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
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

        def _theme_palette(self):
            return get_theme_palette(self._theme_mode)

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
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self.setObjectName("TasksDashBarChart")
            self.setMinimumHeight(260)

        def paintEvent(self, event) -> None:
            super().paintEvent(event)
            palette = self._theme_palette()
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(self.rect(), QColor(palette.chart_bg))
            chart_rect = self.rect().adjusted(18, 18, -18, -18)
            if chart_rect.width() <= 0 or chart_rect.height() <= 0:
                return
            if not self._items:
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

            max_value = max((value for _, value, _ in self._items), default=0)
            if max_value <= 0:
                max_value = 1
            slot_width = plot_rect.width() / max(1, len(self._items))
            bar_width = max(24, int(slot_width * 0.52))
            animated_values = [value * self._progress for _, value, _ in self._items]

            value_font = painter.font()
            value_font.setPointSize(max(8, value_font.pointSize() - 1))
            label_font = painter.font()
            label_font.setPointSize(max(8, label_font.pointSize() - 1))

            for index, (label, value, color) in enumerate(self._items):
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

    class _DashPieChartWidget(_DashChartWidget):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self.setObjectName("TasksDashPieChart")
            self.setMinimumHeight(260)

        def paintEvent(self, event) -> None:
            super().paintEvent(event)
            palette = self._theme_palette()
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(self.rect(), QColor(palette.chart_bg))
            chart_rect = self.rect().adjusted(18, 18, -18, -18)
            if chart_rect.width() <= 0 or chart_rect.height() <= 0:
                return
            if not self._items:
                painter.setPen(QColor(palette.chart_muted))
                painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Нет данных")
                return

            total = sum(value for _, value, _ in self._items)
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

            total_angle = int(round(360.0 * 16 * self._progress))
            start_angle = 90 * 16
            remaining_angle = total_angle
            for label, value, color in self._items:
                span_angle = int(round((value / total) * 360.0 * 16))
                draw_angle = min(span_angle, remaining_angle)
                if draw_angle > 0:
                    painter.setPen(QColor(palette.chart_bg))
                    painter.setBrush(color)
                    painter.drawPie(pie_rect, start_angle, -draw_angle)
                    start_angle -= draw_angle
                    remaining_angle -= draw_angle

            inner_rect = pie_rect.adjusted(pie_rect.width() // 4, pie_rect.height() // 4, -pie_rect.width() // 4, -pie_rect.height() // 4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(palette.chart_bg))
            painter.drawEllipse(inner_rect)

            painter.setPen(QColor(palette.chart_text))
            total_font = painter.font()
            total_font.setPointSize(max(10, total_font.pointSize() + 1))
            total_font.setBold(True)
            painter.setFont(total_font)
            painter.drawText(inner_rect.adjusted(0, -8, 0, 0), Qt.AlignmentFlag.AlignCenter, str(int(round(total * self._progress))))
            painter.setPen(QColor(palette.chart_muted))
            small_font = painter.font()
            small_font.setPointSize(max(8, small_font.pointSize() - 1))
            small_font.setBold(False)
            painter.setFont(small_font)
            painter.drawText(inner_rect.adjusted(0, 18, 0, 0), Qt.AlignmentFlag.AlignCenter, "всего")

            legend_left = pie_rect.right() + 18 if legend_width > 0 else chart_rect.left()
            legend_top = chart_rect.top() if legend_width > 0 else pie_rect.bottom() + 16
            row_height = 24
            for index, (label, value, color) in enumerate(self._items):
                row_y = legend_top + index * row_height
                if row_y + row_height > chart_rect.bottom() + 1:
                    break
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QRect(legend_left, row_y + 5, 12, 12))
                painter.setPen(QColor(palette.chart_text))
                painter.drawText(QRect(legend_left + 20, row_y, 96, row_height), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
                painter.setPen(QColor(palette.chart_muted))
                painter.drawText(QRect(legend_left + 106, row_y, 42, row_height), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, str(value))

    def __init__(self, parent=None):
        """Создает интерфейс рабочей области задач."""
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self._theme_mode = "dark"
        self._focus_day = date.today()
        self._applying_filters = False
        self._gantt_mode = False
        self._board_mode = False
        self._dash_mode = False
        self._smooth_scroll_controllers: list[object] = []
        self.new_title = None
        self.new_day = None
        self.new_time = None
        self.new_time_toggle = None
        self.new_priority = None
        self.btn_add = None
        self.list = None
        self.model = None
        self.delegate = None
        self._sticky_header = None
        self.content_stack = None
        self.gantt_page = None
        self.board_page = None
        self.dash_page = None
        self.btn_gantt = None
        self.btn_board = None
        self.btn_dash = None
        self._project_quick_links_host = None
        self._project_quick_links_layout = None
        self._project_filter_clear_button = None
        self._project_quick_link_buttons: List[QToolButton] = []
        self._task_flash_animations: Dict[int, QVariantAnimation] = {}
        self.board_columns: Dict[str, QListWidget] = {}
        self.dash_summary_label = None
        self.dash_bar_chart = None
        self.dash_pie_chart = None
        self.dash_pulse_chart = None
        self.dash_projects_list = None
        super().__init__(parent)
        self.setObjectName("TasksWorkspace")
        self.search_input.setPlaceholderText("Поиск…")

        self._build_filters()
        self.build_content()

        self._update_day_label()
        self._apply_tab("plan")
        self.update_action_states()
        self.set_theme_mode("dark")

    def _build_workspace_stylesheet(self, theme_mode: str) -> str:
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

    def _apply_gantt_palette(self) -> None:
        gantt_table = getattr(self, "gantt_table", None)
        if not isinstance(gantt_table, QTableWidget):
            return
        palette = get_theme_palette(self._theme_mode)
        table_palette = gantt_table.palette()
        table_palette.setColor(QPalette.ColorRole.Base, QColor(palette.window_bg))
        table_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(palette.panel_alt_bg))
        table_palette.setColor(QPalette.ColorRole.Text, QColor(palette.text))
        table_palette.setColor(QPalette.ColorRole.Mid, QColor(palette.border_strong))
        table_palette.setColor(QPalette.ColorRole.Highlight, QColor(palette.accent))
        table_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(palette.selection_text))
        gantt_table.setPalette(table_palette)

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        self.setStyleSheet(self._build_workspace_stylesheet(self._theme_mode))
        self._apply_gantt_palette()
        if isinstance(self.delegate, TasksItemDelegate):
            self.delegate.set_theme_mode(self._theme_mode)
            if self.list is not None and self.list.viewport() is not None:
                self.list.viewport().update()
        for chart_widget in (self.dash_bar_chart, self.dash_pie_chart, self.dash_pulse_chart):
            set_theme_mode = getattr(chart_widget, "set_theme_mode", None)
            if callable(set_theme_mode):
                set_theme_mode(self._theme_mode)

    def create_actions(self) -> dict[str, QAction]:
        action_export = QAction("Экспорт", self)
        action_export.triggered.connect(self._export_tasks_csv)
        action_import = QAction("Импорт", self)
        action_import.triggered.connect(self._import_tasks_csv)
        return {
            "export": action_export,
            "import": action_import,
        }

    def build_toolbar(self, actions: dict[str, QAction]) -> None:
        while self.toolbar_layout.count():
            item = self.toolbar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        mode_buttons = [self.btn_gantt, self.btn_board, self.btn_dash]
        for button in mode_buttons:
            if isinstance(button, QToolButton):
                self.toolbar_layout.addWidget(button)
        self.toolbar_layout.addStretch(1)
        for action in actions.values():
            button = QToolButton()
            button.setDefaultAction(action)
            self.toolbar_layout.addWidget(button)

    def build_content(self) -> None:
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

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
        today = datetime.now().date()
        self.new_day.setDate(QDate(today.year, today.month, today.day))
        self.new_day.setToolTip("Дата выполнения (можно выбрать в календаре или ввести вручную)")
        self.new_day.setKeyboardTracking(False)

        self.new_time = QTimeEdit()
        self.new_time.setDisplayFormat("HH:mm")
        self.new_time.setFixedWidth(90)
        self.new_time.setTime(QTime.currentTime().addSecs(3600))
        self.new_time.setKeyboardTracking(False)

        self.new_time_toggle = QCheckBox("Время")
        self.new_time_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_time_toggle.setChecked(True)
        self.new_time.setEnabled(True)
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
        self.new_priority.addItems(["High", "Medium", "Low", "Отложенная"])
        self.new_priority.setCurrentText("Medium")

        self.btn_add = QToolButton()
        self.btn_add.setText("Создать")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)

        create_layout.addWidget(self.new_title, 1)
        create_layout.addWidget(datetime_block)
        create_layout.addWidget(self.new_priority)
        create_layout.addWidget(self.btn_add)

        content_layout.addWidget(create)

        self.list = QListView()
        self.list.setObjectName("TasksList")
        self.list.setUniformItemSizes(False)
        self.list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.list.setMouseTracking(True)
        self.list.viewport().setMouseTracking(True)

        self.model = TasksModel(self)
        self.list.setModel(self.model)
        self.model.task_moved.connect(self._flash_task_after_move)

        self.delegate = TasksItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)
        self._sticky_header = QLabel(self.list.viewport())
        self._sticky_header.setObjectName("TasksStickyHeader")
        self._sticky_header.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._sticky_header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._sticky_header.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._sticky_header.hide()

        self.btn_add.clicked.connect(self._on_create_task)
        self.new_title.returnPressed.connect(self._on_create_task)
        self.list.viewport().installEventFilter(self)

        selection_model = self.list.selectionModel()
        selection_model.selectionChanged.connect(lambda *_: self.update_action_states())
        selection_model.currentChanged.connect(lambda *_: self.update_action_states())
        self.model.modelReset.connect(self.update_action_states)
        self.model.layoutChanged.connect(self.update_action_states)
        self.model.modelReset.connect(self._update_sticky_day_header)
        self.model.layoutChanged.connect(self._update_sticky_day_header)
        self.model.rowsInserted.connect(lambda *_: self._update_sticky_day_header())
        self.model.rowsRemoved.connect(lambda *_: self._update_sticky_day_header())
        self.list.verticalScrollBar().valueChanged.connect(lambda *_: self._update_sticky_day_header())

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.list)
        self.gantt_page = self._build_gantt_page()
        self.content_stack.addWidget(self.gantt_page)
        self.board_page = self._build_board_page()
        self.content_stack.addWidget(self.board_page)
        self.dash_page = self._build_dash_page()
        self.content_stack.addWidget(self.dash_page)
        self.content_stack.setCurrentWidget(self.list)
        content_layout.addWidget(self.content_stack, 1)
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.list),
            attach_smooth_scroll(self.gantt_table),
        ]
        for board_column in self.board_columns.values():
            self._smooth_scroll_controllers.append(attach_smooth_scroll(board_column))
        if isinstance(self.dash_projects_list, QListWidget):
            self._smooth_scroll_controllers.append(attach_smooth_scroll(self.dash_projects_list))
        self._update_sticky_day_header()

        self.set_content(content)

    def _build_gantt_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.gantt_hint = QLabel("Режим Gantt: прогноз длительности строится автоматически и сохраняется.")
        self.gantt_hint.setObjectName("TasksGanttHint")
        self.gantt_hint.setWordWrap(True)
        layout.addWidget(self.gantt_hint)

        self.gantt_table = QTableWidget(0, 6, page)
        self.gantt_table.setObjectName("TasksGanttTable")
        self.gantt_table.setHorizontalHeaderLabels(
            ["Задача", "Срок", "Старт", "Финиш", "Лента", "Минуты"]
        )
        self.gantt_table.verticalHeader().setVisible(False)
        self.gantt_table.setAlternatingRowColors(True)
        self.gantt_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.gantt_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._apply_gantt_palette()
        self.gantt_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.gantt_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.gantt_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.gantt_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.gantt_table, 1)
        return page

    def _build_board_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        board_hint = QLabel("Режим Board: канбан по выбранному дню с независимым статусом колонки.")
        board_hint.setObjectName("TasksBoardHint")
        board_hint.setWordWrap(True)
        layout.addWidget(board_hint)

        columns_host = QWidget(page)
        columns_layout = QHBoxLayout(columns_host)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(8)

        self.board_columns = {}
        for board_column, header in self.BOARD_COLUMN_ORDER:
            column_frame = QFrame(columns_host)
            column_frame.setObjectName("TasksBoardColumn")
            column_layout = QVBoxLayout(column_frame)
            column_layout.setContentsMargins(8, 8, 8, 8)
            column_layout.setSpacing(6)

            label = QLabel(header)
            label.setObjectName("TasksBoardColumnTitle")
            column_layout.addWidget(label)

            list_widget = self._BoardColumnListWidget(self, board_column, column_frame)
            column_layout.addWidget(list_widget, 1)
            columns_layout.addWidget(column_frame, 1)
            self.board_columns[board_column] = list_widget

        layout.addWidget(columns_host, 1)
        return page

    def _build_dash_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.dash_summary_label = QLabel("DASH: пересчет статистики и наполнение диаграмм по выбранному дню.")
        self.dash_summary_label.setObjectName("TasksDashSummary")
        self.dash_summary_label.setWordWrap(True)
        layout.addWidget(self.dash_summary_label)

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
        self.dash_bar_chart = self._DashBarChartWidget(totals_card)
        totals_layout.addWidget(self.dash_bar_chart, 1)

        distribution_card = QFrame(charts_host)
        distribution_card.setObjectName("TasksDashCard")
        distribution_layout = QVBoxLayout(distribution_card)
        distribution_layout.setContentsMargins(10, 10, 10, 10)
        distribution_layout.setSpacing(8)
        distribution_title = QLabel("Круговая доля сущностей")
        distribution_title.setObjectName("TasksDashChartTitle")
        distribution_layout.addWidget(distribution_title)
        self.dash_pie_chart = self._DashPieChartWidget(distribution_card)
        distribution_layout.addWidget(self.dash_pie_chart, 1)

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
        self.dash_pulse_chart = self._DashBarChartWidget(pulse_card)
        self.dash_pulse_chart.setObjectName("TasksDashPulseChart")
        self.dash_pulse_chart.setMinimumHeight(220)
        pulse_layout.addWidget(self.dash_pulse_chart, 1)
        layout.addWidget(pulse_card)

        projects_title = QLabel("Топ проектов по активным задачам")
        projects_title.setObjectName("TasksDashProjectsTitle")
        layout.addWidget(projects_title)

        self.dash_projects_list = QListWidget(page)
        self.dash_projects_list.setObjectName("TasksDashProjectsList")
        self.dash_projects_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.dash_projects_list, 1)

        return page

    def _fetch_tasks_for_focus_day(self) -> List:
        priority_value = self.cmb_priority.currentText() if hasattr(self, "cmb_priority") else "Любой"
        priority_filter = None if priority_value == "Любой" else priority_value
        tasks = [
            task
            for task in self._db.fetch_tasks()
            if task.day == self._focus_day and not task.done
        ]
        if priority_filter is not None:
            tasks = [task for task in tasks if task.priority == priority_filter]
        tasks.sort(key=lambda task: (self._parse_task_datetime(task.day, task.time_text), task.id))
        return tasks

    def _refresh_board_day(self) -> None:
        if not self.board_columns:
            return
        tasks = self._fetch_tasks_for_focus_day()
        grouped: Dict[str, List] = {column: [] for column, _ in self.BOARD_COLUMN_ORDER}
        for task in tasks:
            board_column = normalize_board_column(getattr(task, "board_column", ""), task.priority)
            grouped.setdefault(board_column, []).append(task)
        for board_column, list_widget in self.board_columns.items():
            list_widget.clear()
            for task in grouped.get(board_column, []):
                time_text = task.time_text or "—"
                item = QListWidgetItem(f"{time_text} · {task.title}")
                item.setData(Qt.ItemDataRole.UserRole, task.id)
                if task.project_title:
                    item.setToolTip(task.project_title)
                list_widget.addItem(item)

    def _move_task_to_board_column(self, task_id: int, board_column: str) -> None:
        self._db.set_task_board_column(task_id, board_column)
        self.refresh()

    def _flash_task_after_move(self, task_id: int) -> None:
        if self.delegate is None or self.list is None:
            return
        index = self._index_for_task_id(task_id)
        if index is None:
            return
        self.list.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
        active_animation = self._task_flash_animations.pop(task_id, None)
        if active_animation is not None:
            active_animation.stop()
            active_animation.deleteLater()

        animation = QVariantAnimation(self)
        animation.setDuration(780)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.valueChanged.connect(
            lambda value, moved_task_id=task_id: self._update_task_flash(moved_task_id, float(value))
        )
        animation.finished.connect(lambda moved_task_id=task_id: self._finish_task_flash(moved_task_id))
        self._task_flash_animations[task_id] = animation
        self._update_task_flash(task_id, 0.0)
        animation.start()

    def _update_task_flash(self, task_id: int, progress: float) -> None:
        if self.delegate is None or self.list is None:
            return
        self.delegate.set_task_flash_progress(task_id, progress)
        index = self._index_for_task_id(task_id)
        if index is None:
            self.list.viewport().update()
            return
        self.list.viewport().update(self.list.visualRect(index))

    def _finish_task_flash(self, task_id: int) -> None:
        animation = self._task_flash_animations.pop(task_id, None)
        if animation is not None:
            animation.deleteLater()
        if self.delegate is None or self.list is None:
            return
        self.delegate.clear_task_flash(task_id)
        index = self._index_for_task_id(task_id)
        if index is None:
            self.list.viewport().update()
            return
        self.list.viewport().update(self.list.visualRect(index))

    def _calculate_dash_resultativity(self, all_tasks: List) -> Tuple[int, float]:
        """Return recent completed-task impulse and the normalized baseline for previous periods."""
        recent_start = self._focus_day - timedelta(days=1)
        recent_impulse = sum(
            1
            for task in all_tasks
            if task.done and recent_start <= task.day <= self._focus_day
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

    def _build_dash_pulse_items(self, all_tasks: List) -> List[Tuple[str, int, QColor]]:
        """Build a short completion pulse histogram ending on the focused day."""
        window_start = self._focus_day - timedelta(days=self.DASH_PULSE_DAYS - 1)
        recent_start = self._focus_day - timedelta(days=1)
        completion_counts: Dict[date, int] = {}
        for task in all_tasks:
            if not task.done or task.day < window_start or task.day > self._focus_day:
                continue
            completion_counts[task.day] = completion_counts.get(task.day, 0) + 1

        items: List[Tuple[str, int, QColor]] = []
        for offset in range(self.DASH_PULSE_DAYS):
            current_day = window_start + timedelta(days=offset)
            if current_day < recent_start:
                color = QColor("#35536f")
            elif current_day == self._focus_day:
                color = QColor("#8fe3ff")
            else:
                color = QColor("#4f7ecf")
            items.append((current_day.strftime("%d.%m"), completion_counts.get(current_day, 0), color))
        return items

    def _format_dash_resultativity(self, all_tasks: List) -> str:
        """Build a readable DASH summary for recent completion impulse against prior periods."""
        recent_impulse, baseline_impulse = self._calculate_dash_resultativity(all_tasks)
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

    def _refresh_dash_day(self) -> None:
        if (
            self.dash_summary_label is None
            or self.dash_projects_list is None
            or self.dash_bar_chart is None
            or self.dash_pie_chart is None
            or self.dash_pulse_chart is None
        ):
            return
        all_tasks = self._db.fetch_tasks()
        all_projects = self._db.fetch_projects()
        all_maps = self._db.fetch_maps()
        all_markers = self._db.fetch_map_markers()
        all_objects = self._db.fetch_objects()
        all_notes = self._db.fetch_notes()

        tasks = self._fetch_tasks_for_focus_day()
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
        self.dash_bar_chart.set_items(entity_items, animate=True)
        self.dash_pie_chart.set_items(entity_items, animate=True)
        self.dash_pulse_chart.set_items(self._build_dash_pulse_items(all_tasks), animate=True)
        self.dash_summary_label.setText(
            (
                f"DASH на {self._focus_day.isoformat()}: диаграммы пересчитаны и заполнены заново.\n"
                f"На {self._focus_day.isoformat()}: "
                f"активных задач {total}, High {high}, Medium {medium}, Low {low}, Отложенных {deferred}.\n"
                f"{self._format_dash_resultativity(all_tasks)}"
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
        self.dash_projects_list.clear()
        for project_id, count in ranked:
            project = projects.get(project_id)
            if project is None:
                continue
            self.dash_projects_list.addItem(f"{project.area} · {project.title} ({count})")

    class _GanttBarWidget(QWidget):
        def __init__(self, start_minutes: int, end_minutes: int, day_start: int, day_end: int, parent=None):
            super().__init__(parent)
            self._start = int(start_minutes)
            self._end = int(end_minutes)
            self._day_start = int(day_start)
            self._day_end = int(day_end)
            self.setMinimumHeight(18)

        def paintEvent(self, event):
            super().paintEvent(event)
            painter = QPainter(self)
            r = self.rect().adjusted(2, 3, -2, -3)
            if r.width() <= 0 or r.height() <= 0:
                return

            pal = self.palette()
            border_color = pal.mid().color()
            track_color = pal.alternateBase().color()
            accent_color = pal.highlight().color()
            label_color = pal.text().color()
            label_color.setAlpha(140)
            minor_tick_color = pal.mid().color()
            minor_tick_color.setAlpha(120)
            if track_color.lightness() > 120:
                border_color = QColor("#3a3b40")
                track_color = QColor("#1f2227")
                accent_color = QColor("#4f7ecf")
                label_color = QColor("#8a8d95")
                minor_tick_color = QColor("#43464d")

            painter.setPen(border_color)
            painter.setBrush(track_color)
            painter.drawRoundedRect(r, 4, 4)

            # Почасовая сетка и подписи времени (каждые 2 часа).
            span = max(1, self._day_end - self._day_start)
            baseline_y = r.bottom() - 9
            for hour in range(self._day_start // 60, self._day_end // 60 + 1):
                minute_mark = hour * 60
                x = r.left() + int((minute_mark - self._day_start) / span * r.width())
                strong_tick = (hour % 2 == 0) or (minute_mark == self._day_start) or (minute_mark == self._day_end)
                tick_color = border_color if strong_tick else minor_tick_color
                painter.setPen(tick_color)
                painter.drawLine(x, r.top() + 1, x, baseline_y)
                if strong_tick:
                    label = f"{hour:02d}"
                    label_rect = QRect(x - 10, baseline_y + 1, 20, 8)
                    painter.setPen(label_color)
                    painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, label)

            start_clamped = min(max(self._start, self._day_start), self._day_end)
            end_clamped = min(max(self._end, self._day_start), self._day_end)
            if end_clamped <= start_clamped:
                return

            x1 = r.left() + int((start_clamped - self._day_start) / span * r.width())
            x2 = r.left() + int((end_clamped - self._day_start) / span * r.width())
            bar_w = max(2, x2 - x1)
            bar = QRect(x1, r.top() + 1, bar_w, max(2, baseline_y - r.top() - 1))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent_color)
            painter.drawRoundedRect(bar, 4, 4)

    def _build_filters(self) -> None:
        while self.filter_layout.count():
            item = self.filter_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str, tab_value: str) -> QToolButton:
            b = QToolButton()
            b.setText(text)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setAutoRaise(True)
            b.setProperty("tab", tab_value)
            self.tabs_group.addButton(b)
            b.clicked.connect(lambda checked=False, value=tab_value: self.set_filter("tab", value))
            return b

        self.tab_all = tab_btn("Все", "all")
        self.tab_plan = tab_btn("План", "plan")
        self.tab_today = tab_btn("Сегодня", "today")
        self.tab_done = tab_btn("Выполнено", "done")
        self.tab_deferred = tab_btn("Отложенные", "deferred")
        self.tab_plan.setChecked(True)

        self.btn_prev_day = QToolButton()
        self.btn_prev_day.setIcon(qta.icon("fa5s.chevron-left", color="#cfcfcf"))
        self.btn_prev_day.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_day.setAutoRaise(True)

        self.btn_next_day = QToolButton()
        self.btn_next_day.setIcon(qta.icon("fa5s.chevron-right", color="#cfcfcf"))
        self.btn_next_day.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_day.setAutoRaise(True)

        self.btn_gantt = QToolButton()
        self.btn_gantt.setText("GANTT")
        self.btn_gantt.setCheckable(True)
        self.btn_gantt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gantt.setAutoRaise(True)
        self.btn_gantt.setVisible(False)
        self.btn_board = QToolButton()
        self.btn_board.setText("BOARD")
        self.btn_board.setCheckable(True)
        self.btn_board.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_board.setAutoRaise(True)
        self.btn_board.setVisible(False)
        self.btn_dash = QToolButton()
        self.btn_dash.setText("DASH")
        self.btn_dash.setCheckable(True)
        self.btn_dash.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dash.setAutoRaise(True)
        self.btn_dash.setVisible(False)

        self.lbl_day = QLabel()
        self.lbl_day.setObjectName("TasksDayLabel")

        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Любой", "High", "Medium", "Low", "Отложенная"])
        self.cmb_priority.setFixedWidth(110)

        self.filter_layout.addWidget(self.tab_all)
        self.filter_layout.addWidget(self.tab_plan)
        self.filter_layout.addWidget(self.tab_today)
        self.filter_layout.addWidget(self.tab_done)
        self.filter_layout.addWidget(self.tab_deferred)
        self.filter_layout.addSpacing(12)
        self.filter_layout.addWidget(self.btn_prev_day)
        self.filter_layout.addWidget(self.lbl_day)
        self.filter_layout.addWidget(self.btn_next_day)
        self.filter_layout.addSpacing(8)
        self._project_quick_links_host = QWidget(self)
        self._project_quick_links_layout = QHBoxLayout(self._project_quick_links_host)
        self._project_quick_links_layout.setContentsMargins(0, 0, 0, 0)
        self._project_quick_links_layout.setSpacing(4)
        self._ensure_project_filter_clear_button()
        self.filter_layout.addWidget(self._project_quick_links_host, 1)
        self.filter_layout.addSpacing(12)
        self.filter_layout.addWidget(self.cmb_priority)
        self._relocate_search()
        self._refresh_project_quick_links()

        self.btn_prev_day.clicked.connect(lambda: self._shift_day(-1))
        self.btn_next_day.clicked.connect(lambda: self._shift_day(+1))
        self.btn_gantt.toggled.connect(self._set_gantt_mode)
        self.btn_board.toggled.connect(self._set_board_mode)
        self.btn_dash.toggled.connect(self._set_dash_mode)
        self.cmb_priority.currentTextChanged.connect(self._on_priority_filter_changed)
        self.build_toolbar(self.actions)

    def _relocate_search(self) -> None:
        """Перемещает строку поиска в панель фильтров."""
        self.search_row.setVisible(False)
        search_layout = self.search_row.layout()
        if search_layout is not None:
            search_layout.removeWidget(self.search_input)
            search_layout.removeWidget(self.clear_button)
        self.search_input.setFixedWidth(260)
        self.filter_layout.addWidget(self.search_input)
        self.filter_layout.addWidget(self.clear_button)

    def _ensure_project_filter_clear_button(self) -> QToolButton:
        button = self._project_filter_clear_button
        if button is not None:
            try:
                if self._project_quick_links_host is not None and button.parent() is not self._project_quick_links_host:
                    button.setParent(self._project_quick_links_host)
                return button
            except RuntimeError:
                self._project_filter_clear_button = None
        parent = self._project_quick_links_host
        button = QToolButton(parent)
        button.setIcon(qta.icon("fa5s.times", color="#cfcfcf"))
        button.setAutoRaise(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip("Сбросить фильтр по проекту")
        button.setVisible(False)
        button.clicked.connect(lambda: self.set_project_filter(None))
        self._project_filter_clear_button = button
        return button

    def _refresh_project_quick_links(self) -> None:
        if self._project_quick_links_layout is None:
            return
        clear_button = self._ensure_project_filter_clear_button()
        while self._project_quick_links_layout.count():
            item = self._project_quick_links_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if widget is clear_button:
                    widget.hide()
                    continue
                widget.deleteLater()
        self._project_quick_link_buttons = []

        projects = {project.id: project for project in self._db.fetch_projects() if not project.archived}
        counts: Dict[int, int] = {}
        for task in self._db.fetch_tasks():
            if task.done or task.project_id is None:
                continue
            if task.project_id not in projects:
                continue
            counts[task.project_id] = counts.get(task.project_id, 0) + 1

        top_projects = sorted(
            counts.items(),
            key=lambda item: (
                -item[1],
                (projects[item[0]].title or "").lower(),
                item[0],
            ),
        )[:5]
        for project_id, count in top_projects:
            project = projects[project_id]
            button = QToolButton(self._project_quick_links_host)
            button.setText(f"{project.title} ({count})")
            button.setCheckable(True)
            button.setAutoRaise(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(f"{project.area} · {project.title}")
            button.setProperty("project_id", project_id)
            button.clicked.connect(
                lambda checked=False, selected_project_id=project_id: self.set_project_filter(
                    selected_project_id if checked else None
                )
            )
            self._project_quick_links_layout.addWidget(button)
            self._project_quick_link_buttons.append(button)
        self._project_quick_links_layout.addWidget(clear_button)
        self._project_quick_links_layout.addStretch(1)
        self._sync_project_quick_links_selection()

    def _sync_project_quick_links_selection(self) -> None:
        active_project_id = None
        if hasattr(self, "model") and self.model is not None:
            active_project_id = getattr(self.model, "_project_filter_id", None)
        for button in self._project_quick_link_buttons:
            button_project_id = button.property("project_id")
            button.blockSignals(True)
            button.setChecked(button_project_id is not None and button_project_id == active_project_id)
            button.blockSignals(False)
        self._ensure_project_filter_clear_button().setVisible(active_project_id is not None)

    def refresh(self) -> None:
        """Перезагружает список задач из базы."""
        self.model.refresh()
        if self._gantt_mode:
            self._refresh_gantt_day()
        elif self._board_mode:
            self._refresh_board_day()
        elif self._dash_mode:
            self._refresh_dash_day()
        self._refresh_project_quick_links()

    def _export_tasks_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Tasks",
            "tasks_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_tasks_rows(self._db.fetch_tasks())
        if not rows:
            self.set_status("Нет данных для экспорта")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=TASKS_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Tasks", f"Export failed: {exc}")
            return
        self.set_status("Экспорт завершен")

    def _import_tasks_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Tasks",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Tasks", f"Import failed: {exc}")
            return
        result = import_tasks_rows(self._db, rows)
        self.refresh()
        self.set_status(f"Импорт завершен: {result.imported}, пропущено: {result.skipped}")

    def on_enter(self, context: dict | None = None) -> None:
        super().on_enter(context)

    def apply_query(self, query: str) -> None:
        priority_value = self.cmb_priority.currentText() if hasattr(self, "cmb_priority") else "Любой"
        priority = None if priority_value == "Любой" else priority_value
        self.model.set_priority_filter(priority)
        self.model.set_search(query)

    def apply_filters(self, filters: Dict[str, object]) -> None:
        self._applying_filters = True
        try:
            tab = filters.get("tab")
            if not tab:
                mode_raw = filters.get("mode")
                mode = mode_raw if isinstance(mode_raw, str) else None
                if mode:
                    tab = self._tab_from_mode(mode)
                else:
                    tab = "plan"
            focus_day = filters.get("focus_day")
            project_id = filters.get("project_id")
            priority = filters.get("priority")
            if isinstance(focus_day, str):
                try:
                    focus_day = date.fromisoformat(focus_day)
                except ValueError:
                    focus_day = None
            if isinstance(focus_day, date):
                self._focus_day = focus_day
            self._apply_tab(tab, focus_day=focus_day)
            self.model.set_project_filter(project_id)
            self.model.set_priority_filter(priority if isinstance(priority, str) else None)
            if priority:
                self.cmb_priority.setCurrentText(priority)
            else:
                self.cmb_priority.setCurrentText("Любой")
            self._sync_project_quick_links_selection()
            if self._gantt_mode or self._board_mode or self._dash_mode:
                self._refresh_secondary_view()
        finally:
            self._applying_filters = False

    def get_selection(self) -> List[TaskRow]:
        model = getattr(self, "model", None)
        if model is None:
            return []
        index = self._selected_task_index()
        if index is None:
            return []
        if hasattr(model, "task_at_row"):
            task = model.task_at_row(index.row())
            return [task] if task else []
        return []

    def _selected_task_index(self) -> Optional[QModelIndex]:
        list_widget = getattr(self, "list", None)
        if not isinstance(list_widget, QListView):
            return None
        index = list_widget.currentIndex()
        if not index.isValid():
            return None
        if index.data(TaskRoles.RowType) != "task":
            return None
        return index

    def _index_for_task_id(self, task_id: int) -> Optional[QModelIndex]:
        if not hasattr(self, "model"):
            return None
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            if not index.isValid():
                continue
            if index.data(TaskRoles.RowType) != "task":
                continue
            if index.data(TaskRoles.TaskId) == task_id:
                return index
        return None

    def focus_task(self, task_id: int) -> bool:
        index = self._index_for_task_id(task_id)
        if index is None:
            if self._gantt_mode or self._board_mode or self._dash_mode:
                self._gantt_mode = False
                self._board_mode = False
                self._dash_mode = False
                self.btn_gantt.blockSignals(True)
                self.btn_board.blockSignals(True)
                self.btn_dash.blockSignals(True)
                self.btn_gantt.setChecked(False)
                self.btn_board.setChecked(False)
                self.btn_dash.setChecked(False)
                self.btn_gantt.blockSignals(False)
                self.btn_board.blockSignals(False)
                self.btn_dash.blockSignals(False)
                self.content_stack.setCurrentWidget(self.list)
            self._apply_tab("plan")
            self.model.set_project_filter(None)
            self.model.set_priority_filter(None)
            self.model.set_search("")
            self.cmb_priority.setCurrentText("Любой")
            self._sync_project_quick_links_selection()
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)
            index = self._index_for_task_id(task_id)
        if index is None:
            return False

        self.content_stack.setCurrentWidget(self.list)
        self.list.setCurrentIndex(index)
        selection_model = self.list.selectionModel()
        if selection_model is not None:
            selection_model.select(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )
            selection_model.setCurrentIndex(
                index,
                QItemSelectionModel.SelectionFlag.Current,
            )
        self.list.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
        self.list.setFocus(Qt.FocusReason.OtherFocusReason)
        return True

    def _edit_selected_task(self) -> None:
        index = self._selected_task_index()
        if index is None:
            return
        self.delegate.edit_task(index)

    def _delete_selected_task(self) -> None:
        index = self._selected_task_index()
        if index is None:
            return
        title = index.data(TaskRoles.Title) or "задачу"
        dialog = ConfirmDialog(
            "Удалить задачу",
            f"Удалить задачу:\n«{title}» ?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        model = index.model()
        if hasattr(model, "delete_task_by_row"):
            model.delete_task_by_row(index.row())

    def _shift_day(self, delta: int):
        """Сдвигает фокусную дату на указанное число дней."""
        self._focus_day = self._focus_day + timedelta(days=delta)
        self._update_day_label()
        self._update_sticky_day_header()
        if self._gantt_mode or self._board_mode or self._dash_mode:
            self._remember_filter("focus_day", self._focus_day.isoformat())
            self._refresh_secondary_view()
            return
        if not self._applying_filters:
            self._filters["focus_day"] = self._focus_day.isoformat()
            self.set_filter("tab", "all")
        else:
            self._apply_tab("all", focus_day=self._focus_day)

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

        if (self._gantt_mode or self._board_mode or self._dash_mode) and d == self._focus_day:
            self._refresh_secondary_view()
        self._refresh_project_quick_links()

        self.new_title.clear()
        self.new_time.setTime(QTime.currentTime().addSecs(3600))
        self.new_title.setFocus()

    def open_create_task_dialog(self) -> None:
        dialog = TaskCreateDialog(parent=self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            self.model.add_task(
                title=values["title"],
                description=values["description"],
                day=values["day"],
                time_text=values["time_text"],
                priority=values["priority"],
                project_id=values["project_id"],
                recurrence_kind=values["recurrence_kind"],
                recurrence_interval=values["recurrence_interval"],
                marker_color=values["marker_color"],
                marker_theme=values["marker_theme"],
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        if (self._gantt_mode or self._board_mode or self._dash_mode) and values["day"] == self._focus_day:
            self._refresh_secondary_view()
        self._refresh_project_quick_links()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.list.viewport() and event.type() == QEvent.Type.Resize:
            self._update_sticky_day_header()
        if obj is self.list.viewport() and event.type() == QEvent.Type.MouseButtonDblClick:
            if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                index = self.list.indexAt(pos)
                if not index.isValid() or index.data(TaskRoles.RowType) != "task":
                    return False
                rect = self.list.visualRect(index)
                depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
                has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
                layout = self.delegate.row_layout(rect, depth, has_subtasks)
                if has_subtasks and layout["title"].contains(pos):
                    self.model.toggle_subtasks_expanded_by_row(index.row())
                elif layout["doc"].contains(pos):
                    self.delegate.open_task_view(index)
                else:
                    if has_subtasks:
                        self.model.toggle_subtasks_expanded_by_row(index.row())
                    else:
                        self.delegate.open_task_view(index)
                return True
        return super().eventFilter(obj, event)

    def set_project_filter(self, project_id: Optional[int]):
        """Обновляет фильтр по проекту."""
        if self._applying_filters:
            self.model.set_project_filter(project_id)
            self._sync_project_quick_links_selection()
            return
        self._remember_filter("project_id", project_id)
        self.model.set_project_filter(project_id)
        self._sync_project_quick_links_selection()

    def refresh_tasks(self) -> None:
        """Перезагружает список задач из базы."""
        self.model.refresh()

    @staticmethod
    def _tab_from_mode(mode: Optional[str]) -> str:
        if mode == "Сегодня":
            return "today"
        if mode == "Выполнено":
            return "done"
        if mode == "План":
            return "plan"
        if mode == "Отложенные":
            return "deferred"
        return "all"

    def _apply_tab(self, tab: Optional[str], focus_day: Optional[date] = None) -> None:
        if tab == "today":
            self._apply_mode("Сегодня")
        elif tab == "done":
            self._apply_mode("Выполнено")
        elif tab == "plan":
            self._apply_mode("План")
        elif tab == "deferred":
            self._apply_mode("Отложенные")
        else:
            self._apply_mode("Все", focus_day=focus_day)

    def _apply_mode(self, mode: str, focus_day: Optional[date] = None) -> None:
        def _set_secondary_buttons_visible(visible: bool) -> None:
            self.btn_gantt.setVisible(visible)
            self.btn_board.setVisible(visible)
            self.btn_dash.setVisible(visible)

        def _reset_secondary_modes() -> None:
            self._gantt_mode = False
            self._board_mode = False
            self._dash_mode = False
            self.btn_gantt.blockSignals(True)
            self.btn_board.blockSignals(True)
            self.btn_dash.blockSignals(True)
            self.btn_gantt.setChecked(False)
            self.btn_board.setChecked(False)
            self.btn_dash.setChecked(False)
            self.btn_gantt.blockSignals(False)
            self.btn_board.blockSignals(False)
            self.btn_dash.blockSignals(False)

        if mode == "Сегодня":
            _reset_secondary_modes()
            self.model.set_filter_mode("Сегодня")
            self._focus_day = date.today()
            self.model.set_focus_day(self._focus_day)
            self._set_drag_drop_state(False)
            _set_secondary_buttons_visible(False)
            self.content_stack.setCurrentWidget(self.list)
            self.tab_today.setChecked(True)
        elif mode == "Выполнено":
            _reset_secondary_modes()
            self.model.set_filter_mode("Выполнено")
            self.model.set_focus_day(None)
            self._set_drag_drop_state(False)
            _set_secondary_buttons_visible(False)
            self.content_stack.setCurrentWidget(self.list)
            self.tab_done.setChecked(True)
        elif mode == "План":
            self.model.set_filter_mode("План")
            _set_secondary_buttons_visible(True)
            if self._gantt_mode or self._board_mode or self._dash_mode:
                self.model.set_focus_day(self._focus_day)
                self._set_drag_drop_state(False)
                self._refresh_secondary_view()
            else:
                self.model.set_focus_day(None)
                self._set_drag_drop_state(True)
                self.content_stack.setCurrentWidget(self.list)
            if hasattr(self, "tab_plan"):
                self.tab_plan.setChecked(True)
        elif mode == "Отложенные":
            _reset_secondary_modes()
            self.model.set_filter_mode("Отложенные")
            self.model.set_focus_day(None)
            self._set_drag_drop_state(False)
            _set_secondary_buttons_visible(False)
            self.content_stack.setCurrentWidget(self.list)
            if hasattr(self, "tab_deferred"):
                self.tab_deferred.setChecked(True)
        else:
            _reset_secondary_modes()
            self.model.set_filter_mode("Все")
            if focus_day is not None:
                self._focus_day = focus_day
            self.model.set_focus_day(self._focus_day)
            self._set_drag_drop_state(False)
            _set_secondary_buttons_visible(False)
            self.content_stack.setCurrentWidget(self.list)
            self.tab_all.setChecked(True)
        self._update_day_label()
        self._update_sticky_day_header()

    def _remember_filter(self, key: str, value: Optional[object]) -> None:
        if value is None:
            self._filters.pop(key, None)
        else:
            self._filters[key] = value
        self.save_state()

    def _on_priority_filter_changed(self, value: str) -> None:
        if self._applying_filters:
            return
        priority = None if value == "Любой" else value
        self._remember_filter("priority", priority)
        self.model.set_priority_filter(priority)
        self._refresh_secondary_view()

    def _set_secondary_mode(self, mode: str, enabled: bool) -> None:
        plan_mode = self.model.filter_mode() == "План"
        if enabled and not plan_mode:
            button_by_mode = {
                "gantt": self.btn_gantt,
                "board": self.btn_board,
                "dash": self.btn_dash,
            }
            target_button = button_by_mode.get(mode)
            if target_button is not None:
                target_button.blockSignals(True)
                target_button.setChecked(False)
                target_button.blockSignals(False)
            return

        self._gantt_mode = bool(enabled and mode == "gantt" and plan_mode)
        self._board_mode = bool(enabled and mode == "board" and plan_mode)
        self._dash_mode = bool(enabled and mode == "dash" and plan_mode)

        self.btn_gantt.blockSignals(True)
        self.btn_board.blockSignals(True)
        self.btn_dash.blockSignals(True)
        self.btn_gantt.setChecked(self._gantt_mode)
        self.btn_board.setChecked(self._board_mode)
        self.btn_dash.setChecked(self._dash_mode)
        self.btn_gantt.blockSignals(False)
        self.btn_board.blockSignals(False)
        self.btn_dash.blockSignals(False)

        if self._gantt_mode or self._board_mode or self._dash_mode:
            self.model.set_filter_mode("План")
            self.model.set_focus_day(self._focus_day)
            self._set_drag_drop_state(False)
        else:
            if plan_mode:
                self.model.set_filter_mode("План")
                self.model.set_focus_day(None)
                self._set_drag_drop_state(True)
            self.content_stack.setCurrentWidget(self.list)

        self._refresh_secondary_view()
        self._update_sticky_day_header()

    def _set_gantt_mode(self, enabled: bool) -> None:
        self._set_secondary_mode("gantt", enabled)

    def _set_board_mode(self, enabled: bool) -> None:
        self._set_secondary_mode("board", enabled)

    def _set_dash_mode(self, enabled: bool) -> None:
        self._set_secondary_mode("dash", enabled)

    def _refresh_secondary_view(self) -> None:
        if self._gantt_mode:
            self.content_stack.setCurrentWidget(self.gantt_page)
            self._refresh_gantt_day()
            return
        if self._board_mode:
            self.content_stack.setCurrentWidget(self.board_page)
            self._refresh_board_day()
            return
        if self._dash_mode:
            self.content_stack.setCurrentWidget(self.dash_page)
            self._refresh_dash_day()
            return
        self.content_stack.setCurrentWidget(self.list)

    def _is_sticky_header_enabled(self) -> bool:
        return (
            not self._gantt_mode
            and not self._board_mode
            and not self._dash_mode
            and self.content_stack.currentWidget() is self.list
        )

    def _update_sticky_day_header(self) -> None:
        if not hasattr(self, "_sticky_header"):
            return
        if not self._is_sticky_header_enabled():
            self._sticky_header.hide()
            return

        row_count = self.model.rowCount()
        if row_count <= 0:
            self._sticky_header.hide()
            return

        top_index = self.list.indexAt(QPoint(2, 2))
        if not top_index.isValid():
            top_index = self.model.index(0, 0)
            if not top_index.isValid():
                self._sticky_header.hide()
                return
        top_row = top_index.row()

        active_row = -1
        active_day: Optional[date] = None
        for row in range(top_row, -1, -1):
            idx = self.model.index(row, 0)
            if idx.data(TaskRoles.RowType) == "header":
                active_row = row
                active_day = idx.data(TaskRoles.Day)
                break
        if active_row < 0 or active_day is None:
            self._sticky_header.hide()
            return

        active_index = self.model.index(active_row, 0)
        active_rect = self.list.visualRect(active_index)
        if active_row == top_row and active_rect.top() >= 0:
            self._sticky_header.hide()
            return

        text = self.delegate.format_header(active_day)
        if active_day == date.today():
            text = f"{text}  СЕГОДНЯ"
        self._sticky_header.setText(text)

        next_header_top: Optional[int] = None
        for row in range(active_row + 1, row_count):
            idx = self.model.index(row, 0)
            if idx.data(TaskRoles.RowType) == "header":
                rect = self.list.visualRect(idx)
                if rect.isValid() and not rect.isEmpty():
                    next_header_top = rect.top()
                    break
        header_h = self.delegate.HEADER_H
        y = 0
        if next_header_top is not None and next_header_top < header_h:
            y = next_header_top - header_h

        self._sticky_header.setGeometry(0, y, self.list.viewport().width(), header_h)
        self._sticky_header.raise_()
        self._sticky_header.show()

    @staticmethod
    def _estimate_task_minutes(task) -> int:
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

    @staticmethod
    def _parse_task_datetime(task_day: date, time_text: str) -> datetime:
        if time_text:
            try:
                return datetime.strptime(f"{task_day.isoformat()} {time_text}", "%Y-%m-%d %H:%M")
            except ValueError:
                pass
        return datetime.combine(task_day, datetime.min.time())

    def _refresh_gantt_day(self) -> None:
        db = get_database()
        priority_value = self.cmb_priority.currentText() if hasattr(self, "cmb_priority") else "Любой"
        priority_filter = None if priority_value == "Любой" else priority_value
        tasks = [
            task
            for task in db.fetch_tasks()
            if task.day == self._focus_day
            and not task.done
            and task.priority != "Отложенная"
            and (priority_filter is None or task.priority == priority_filter)
        ]
        tasks.sort(key=lambda task: (self._parse_task_datetime(task.day, task.time_text), task.id))

        predicted = 0
        for task in tasks:
            if not task.gantt_forecasted or task.gantt_estimate_minutes <= 0:
                db.set_task_gantt_estimate(task.id, self._estimate_task_minutes(task), forecasted=True)
                predicted += 1
        if predicted:
            tasks = [
                task
                for task in db.fetch_tasks()
                if task.day == self._focus_day
                and not task.done
                and task.priority != "Отложенная"
                and (priority_filter is None or task.priority == priority_filter)
            ]
            tasks.sort(key=lambda task: (self._parse_task_datetime(task.day, task.time_text), task.id))

        self.gantt_table.setRowCount(0)
        if not tasks:
            self.gantt_hint.setText("На выбранный день нет активных задач для диаграммы Gantt.")
            return

        cursor = datetime.combine(self._focus_day, datetime.strptime("09:00", "%H:%M").time())
        total_minutes = 0
        day_start_minutes = self.GANTT_DAY_START_HOUR * 60
        day_end_minutes = self.GANTT_DAY_END_HOUR * 60
        self.gantt_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            pref_dt = self._parse_task_datetime(task.day, task.time_text)
            start_dt = max(cursor, pref_dt)
            estimate = max(15, int(task.gantt_estimate_minutes or 0))
            end_dt = start_dt + timedelta(minutes=estimate)
            cursor = end_dt
            total_minutes += estimate

            self.gantt_table.setItem(row, 0, QTableWidgetItem(task.title))
            self.gantt_table.setItem(row, 1, QTableWidgetItem(task.time_text or "—"))
            self.gantt_table.setItem(row, 2, QTableWidgetItem(start_dt.strftime("%H:%M")))
            self.gantt_table.setItem(row, 3, QTableWidgetItem(end_dt.strftime("%H:%M")))

            start_minutes = start_dt.hour * 60 + start_dt.minute
            end_minutes = end_dt.hour * 60 + end_dt.minute
            bar_widget = self._GanttBarWidget(
                start_minutes=start_minutes,
                end_minutes=end_minutes,
                day_start=day_start_minutes,
                day_end=day_end_minutes,
                parent=self.gantt_table,
            )
            self.gantt_table.setCellWidget(row, 4, bar_widget)
            self.gantt_table.setRowHeight(row, 34)

            minutes_spin = QSpinBox(self.gantt_table)
            minutes_spin.setRange(5, 8 * 60)
            minutes_spin.setSingleStep(5)
            minutes_spin.setValue(estimate)
            minutes_spin.setEnabled(bool(task.gantt_forecasted))
            minutes_spin.valueChanged.connect(
                lambda value, task_id=task.id: self._on_gantt_minutes_changed(task_id, value)
            )
            self.gantt_table.setCellWidget(row, 5, minutes_spin)

        total_hours = total_minutes / 60.0
        self.gantt_hint.setText(
            f"Gantt на {self._focus_day.isoformat()}: {len(tasks)} задач, {total_minutes} мин (~{total_hours:.1f} ч)."
        )

    def _on_gantt_minutes_changed(self, task_id: int, minutes: int) -> None:
        get_database().set_task_gantt_estimate(task_id, minutes, forecasted=True)
        self._refresh_gantt_day()

    def _set_drag_drop_state(self, enabled: bool):
        """Включает или выключает drag and drop списка."""
        if enabled:
            self.list.setDragEnabled(True)
            self.list.setAcceptDrops(True)
            self.list.setDropIndicatorShown(True)
            self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
            self.list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        else:
            self.list.setDragEnabled(False)
            self.list.setAcceptDrops(False)
            self.list.setDropIndicatorShown(False)
            self.list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

__all__ = ["TasksWorkspace"]
