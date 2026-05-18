"""TaskDetailsDialog class module for tasks workspace."""

from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QGridLayout, QPushButton

from mindnavigator.storage import DEFERRED_PRIORITY
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND, TITLEBAR_BACKGROUND, get_theme_palette

from ._shared import *  # noqa: F401,F403
from .task_edit_dialog import TaskEditDialog
from .task_image_preview_dialog import TaskImagePreviewDialog


class _InfoCard(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None, *, accent_dot: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("TaskDetailsInfoCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("TaskDetailsCardTitle")
        layout.addWidget(self.title_label)

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(8)

        self.dot_label = QLabel("●")
        self.dot_label.setObjectName("TaskDetailsCardDot")
        self.dot_label.setVisible(accent_dot)
        value_row.addWidget(self.dot_label, 0, Qt.AlignmentFlag.AlignTop)

        self.value_label = QLabel("")
        self.value_label.setObjectName("TaskDetailsCardValue")
        self.value_label.setWordWrap(True)
        value_row.addWidget(self.value_label, 1)
        value_row.addStretch(0)

        layout.addLayout(value_row)

    def set_value(self, value: str, *, muted: bool = False) -> None:
        self.value_label.setText(value)
        self.value_label.setProperty("muted", bool(muted))
        self.value_label.style().unpolish(self.value_label)
        self.value_label.style().polish(self.value_label)
        self.value_label.update()

    def set_dot_color(self, color: str) -> None:
        normalized = (color or "").strip()
        self.dot_label.setVisible(bool(normalized))
        if normalized:
            self.dot_label.setStyleSheet(f"color: {normalized};")
        else:
            self.dot_label.setStyleSheet("")


class TaskDetailsDialog(QDialog):
    _DEFAULT_SIZE = QSize(1260, 840)
    _PARAM_BREAKPOINTS = ((960, 4), (0, 2))
    _DETAIL_BREAKPOINTS = ((1240, 6), (960, 3), (0, 2))

    _MARKER_COLOR_LABELS = {
        "": "Нет",
        "#2f6edb": "Синий",
        "#2f9f63": "Зеленый",
        "#d68a2f": "Оранжевый",
        "#b74a4a": "Красный",
        "#6b5ad4": "Фиолетовый",
    }
    _MARKER_THEME_LABELS = {
        "": "Нет",
        "movies": "Фильмы",
        "games": "Игры",
        "books": "Книги",
        "music": "Музыка",
        "work": "Работа",
        "personal": "Личное",
        "dev": "Разработка",
    }
    _RECURRENCE_LABELS = {
        "daily": "Ежедневно",
        "weekly": "Еженедельно",
        "monthly": "Ежемесячно",
    }

    def __init__(self, task: TaskRow, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Задача")
        self.setObjectName("TaskDetailsDialog")
        self.setProperty("task_dialog_minimizable", False)
        self.setProperty("task_dialog_id", int(task.id))
        self.setProperty("task_dialog_kind", "details")
        self.setProperty("dialog_category", "keep_size")
        self.setMinimumSize(1100, 700)
        self.resize(self._DEFAULT_SIZE)

        self._db = get_database()
        self._task = task
        self._theme_mode = "dark"
        self._palette = get_theme_palette(self._theme_mode)
        self._attachments: List = []
        self._tasks_by_id = {}
        self._notes_by_id = {}
        self._ideas_by_id = {}
        self._objects_by_id = {}
        self._maps_by_id = {}
        self._markers_by_id = {}
        self._cloud_files_by_id = {}
        self._param_cards: list[_InfoCard] = []
        self._detail_cards: list[_InfoCard] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("TaskDetailsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        root_layout.addWidget(self.scroll, 1)

        self.content = QWidget(self.scroll)
        self.content.setObjectName("TaskDetailsContent")
        self.scroll.setWidget(self.content)

        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(18, 18, 18, 8)
        self.content_layout.setSpacing(12)

        self._build_header()
        self._build_description_section()
        self._build_key_params_section()
        self._build_details_section()
        self._build_links_section()

        self.content_layout.addStretch(1)

        self.footer = QFrame(self)
        self.footer.setObjectName("TaskDetailsFooter")
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(18, 10, 18, 14)
        footer_layout.setSpacing(10)
        footer_layout.addStretch(1)

        self.close_button = QPushButton("Закрыть", self.footer)
        self.close_button.setObjectName("TaskDetailsSecondaryButton")
        self.close_button.clicked.connect(self.reject)
        footer_layout.addWidget(self.close_button)

        self.edit_button = QPushButton("Редактировать", self.footer)
        self.edit_button.setObjectName("TaskDetailsPrimaryButton")
        self.edit_button.clicked.connect(self._open_edit_dialog)
        footer_layout.addWidget(self.edit_button)

        root_layout.addWidget(self.footer)

        self._setup_shortcuts()
        self._apply_styles()
        self._refresh_view()

    def _build_header(self) -> None:
        self.header_card = QFrame(self.content)
        self.header_card.setObjectName("TaskDetailsHeaderCard")
        layout = QHBoxLayout(self.header_card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(8)

        self.title_label = QLabel("", self.header_card)
        self.title_label.setObjectName("TaskDetailsTitle")
        self.title_label.setWordWrap(True)
        title_column.addWidget(self.title_label)

        self.summary_label = QLabel("", self.header_card)
        self.summary_label.setObjectName("TaskDetailsSummary")
        self.summary_label.setWordWrap(True)
        title_column.addWidget(self.summary_label)

        layout.addLayout(title_column, 1)

        actions_column = QVBoxLayout()
        actions_column.setContentsMargins(0, 0, 0, 0)
        actions_column.setSpacing(10)

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setSpacing(8)
        badge_row.addStretch(1)

        self.plan_badge = QLabel("План", self.header_card)
        self.plan_badge.setObjectName("TaskDetailsBadge")
        self.plan_badge.setVisible(False)
        badge_row.addWidget(self.plan_badge)

        self.status_badge = QLabel("", self.header_card)
        self.status_badge.setObjectName("TaskDetailsBadge")
        badge_row.addWidget(self.status_badge)

        actions_column.addLayout(badge_row)

        self.header_edit_button = QToolButton(self.header_card)
        self.header_edit_button.setObjectName("TaskDetailsHeaderEditButton")
        self.header_edit_button.setText("Редактировать")
        self.header_edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_edit_button.clicked.connect(self._open_edit_dialog)
        actions_column.addWidget(self.header_edit_button, 0, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(actions_column)
        self.content_layout.addWidget(self.header_card)

    def _build_description_section(self) -> None:
        self.description_card = self._build_section_card("Описание")
        self.description_body = QWidget(self.description_card)
        self.description_body.setObjectName("TaskDetailsDescriptionBody")
        self.description_body_layout = QVBoxLayout(self.description_body)
        self.description_body_layout.setContentsMargins(0, 0, 0, 0)
        self.description_body_layout.setSpacing(0)
        self.description_card.layout().addWidget(self.description_body)
        self.content_layout.addWidget(self.description_card)

    def _build_key_params_section(self) -> None:
        self.params_card = self._build_section_card("Ключевые параметры")
        self.params_grid = QGridLayout()
        self.params_grid.setContentsMargins(0, 0, 0, 0)
        self.params_grid.setHorizontalSpacing(10)
        self.params_grid.setVerticalSpacing(10)

        self.date_card = _InfoCard("Дата", self.params_card)
        self.time_card = _InfoCard("Время", self.params_card)
        self.priority_card = _InfoCard("Приоритет", self.params_card)
        self.recurrence_card = _InfoCard("Повтор", self.params_card)
        self._param_cards = [
            self.date_card,
            self.time_card,
            self.priority_card,
            self.recurrence_card,
        ]
        for card in self._param_cards:
            self.params_grid.addWidget(card)
        self.params_card.layout().addLayout(self.params_grid)
        self.content_layout.addWidget(self.params_card)

    def _build_details_section(self) -> None:
        self.details_card = self._build_section_card("Детали")
        self.details_grid = QGridLayout()
        self.details_grid.setContentsMargins(0, 0, 0, 0)
        self.details_grid.setHorizontalSpacing(10)
        self.details_grid.setVerticalSpacing(10)

        self.detail_id_card = _InfoCard("ID", self.details_card)
        self.detail_project_card = _InfoCard("Проект", self.details_card)
        self.detail_parent_card = _InfoCard("Родительская задача", self.details_card)
        self.detail_type_card = _InfoCard("Тип", self.details_card)
        self.detail_marker_card = _InfoCard("Маркер", self.details_card, accent_dot=True)
        self.detail_theme_card = _InfoCard("Тема маркера", self.details_card)
        self._detail_cards = [
            self.detail_id_card,
            self.detail_project_card,
            self.detail_parent_card,
            self.detail_type_card,
            self.detail_marker_card,
            self.detail_theme_card,
        ]
        for card in self._detail_cards:
            self.details_grid.addWidget(card)
        self.details_card.layout().addLayout(self.details_grid)
        self.content_layout.addWidget(self.details_card)

    def _build_links_section(self) -> None:
        self.links_card = QFrame(self.content)
        self.links_card.setObjectName("TaskDetailsSectionCard")
        layout = QVBoxLayout(self.links_card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        self.links_title = QLabel("Связи", self.links_card)
        self.links_title.setObjectName("TaskDetailsSectionTitle")
        header_layout.addWidget(self.links_title)
        header_layout.addStretch(1)

        self.links_add_button = QToolButton(self.links_card)
        self.links_add_button.setObjectName("TaskDetailsLinkAction")
        self.links_add_button.setText("+ Добавить")
        self.links_add_button.setEnabled(False)
        self.links_add_button.setToolTip("Добавление связей доступно из режима редактирования.")
        header_layout.addWidget(self.links_add_button)

        layout.addLayout(header_layout)

        self.links_host = QWidget(self.links_card)
        self.links_host.setObjectName("TaskDetailsLinksHost")
        self.attachments_list = QVBoxLayout(self.links_host)
        self.attachments_list.setContentsMargins(0, 0, 0, 0)
        self.attachments_list.setSpacing(8)
        layout.addWidget(self.links_host)

        self.content_layout.addWidget(self.links_card)

    def _build_section_card(self, title: str) -> QFrame:
        section = QFrame(self.content)
        section.setObjectName("TaskDetailsSectionCard")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title, section)
        title_label.setObjectName("TaskDetailsSectionTitle")
        layout.addWidget(title_label)
        return section

    def _setup_shortcuts(self) -> None:
        self.edit_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        self.edit_shortcut.activated.connect(self._open_edit_dialog)

    def _apply_styles(self) -> None:
        palette = self._palette
        self.setStyleSheet(
            f"""
            QDialog#TaskDetailsDialog {{
                {MATH_PHYS_BACKGROUND}
                border: 1px solid {palette.border};
                border-radius: 12px;
            }}
            QScrollArea#TaskDetailsScroll,
            QScrollArea#TaskDetailsScroll QWidget {{
                background: transparent;
            }}
            QWidget#TaskDetailsContent {{
                background: transparent;
            }}
            QFrame#TaskDetailsHeaderCard {{
                {TITLEBAR_BACKGROUND}
                border: 1px solid {palette.border};
                border-radius: 12px;
            }}
            QFrame#TaskDetailsSectionCard,
            QFrame#TaskDetailsFooter {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
            }}
            QFrame#TaskDetailsSectionCard {{
                border-radius: 12px;
            }}
            QFrame#TaskDetailsFooter {{
                border-left: none;
                border-right: none;
                border-bottom: none;
            }}
            QFrame#TaskDetailsInfoCard {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}
            QLabel {{
                color: {palette.text};
            }}
            QLabel#TaskDetailsTitle {{
                color: #f2f5ff;
                font-size: 24px;
                font-weight: 700;
            }}
            QLabel#TaskDetailsSummary {{
                color: {palette.dim_text};
                font-size: 13px;
            }}
            QLabel#TaskDetailsSectionTitle {{
                color: #f2f2f2;
                font-size: 14px;
                font-weight: 600;
            }}
            QLabel#TaskDetailsCardTitle {{
                color: {palette.dim_text};
                font-size: 11px;
                font-weight: 600;
            }}
            QLabel#TaskDetailsCardValue {{
                color: {palette.text};
                font-size: 14px;
                font-weight: 600;
            }}
            QLabel#TaskDetailsCardValue[muted="true"] {{
                color: {palette.dim_text};
                font-weight: 500;
            }}
            QLabel#TaskDetailsCardDot {{
                color: {palette.dim_text};
                font-size: 15px;
            }}
            QLabel#TaskDetailsBadge {{
                background: {palette.chip_bg};
                border: 1px solid {palette.chip_border};
                border-radius: 12px;
                color: {palette.text};
                padding: 5px 10px;
                font-weight: 600;
            }}
            QWidget#TaskDetailsDescriptionBody {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}
            QWidget#TaskDetailsDescriptionBody QLabel {{
                color: {palette.text};
            }}
            QLabel#TaskDetailsDescriptionEmpty {{
                color: {palette.dim_text};
                font-style: italic;
                padding: 4px 2px;
            }}
            QLabel#TaskAttachmentKind {{
                color: {palette.dim_text};
                font-weight: 600;
            }}
            QLabel#TaskAttachmentLink {{
                color: #6ecbe0;
            }}
            QFrame#TaskAttachmentRow {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 9px;
            }}
            QLabel#TaskDetailsLinksEmpty {{
                color: {palette.dim_text};
                background: {palette.elevated_bg};
                border: 1px dashed {palette.border_strong};
                border-radius: 10px;
                padding: 18px 14px;
            }}
            QToolButton#TaskDetailsHeaderEditButton,
            QToolButton#TaskDetailsLinkAction,
            QPushButton#TaskDetailsSecondaryButton,
            QPushButton#TaskDetailsPrimaryButton {{
                border-radius: 9px;
                padding: 8px 14px;
                font-weight: 600;
            }}
            QToolButton#TaskDetailsHeaderEditButton,
            QToolButton#TaskDetailsLinkAction,
            QPushButton#TaskDetailsSecondaryButton {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
            }}
            QToolButton#TaskDetailsHeaderEditButton:hover,
            QPushButton#TaskDetailsSecondaryButton:hover {{
                background: {palette.selection_bg};
                border-color: {palette.accent};
            }}
            QToolButton#TaskDetailsLinkAction:disabled {{
                background: {palette.panel_alt_bg};
                color: {palette.muted_text};
                border: 1px solid {palette.border};
            }}
            QPushButton#TaskDetailsPrimaryButton {{
                background: {palette.accent};
                color: #f6f8ff;
                border: 1px solid {palette.accent};
            }}
            QPushButton#TaskDetailsPrimaryButton:hover {{
                background: {palette.accent_hover};
                border-color: {palette.accent_hover};
            }}
            """
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._reflow_cards()

    def _reflow_cards(self) -> None:
        content_width = max(0, self.scroll.viewport().width() - 44)
        self._reflow_grid(self.params_grid, self._param_cards, self._columns_for_width(content_width, self._PARAM_BREAKPOINTS, default=4))
        self._reflow_grid(self.details_grid, self._detail_cards, self._columns_for_width(content_width, self._DETAIL_BREAKPOINTS, default=3))

    @staticmethod
    def _reflow_grid(layout: QGridLayout, widgets: list[QWidget], columns: int) -> None:
        while layout.count():
            layout.takeAt(0)
        columns = max(1, columns)
        for index, widget in enumerate(widgets):
            row = index // columns
            column = index % columns
            layout.addWidget(widget, row, column)

    @staticmethod
    def _columns_for_width(width: int, breakpoints: tuple[tuple[int, int], ...], *, default: int) -> int:
        for min_width, columns in breakpoints:
            if width >= min_width:
                return columns
        return default

    def _refresh_view(self) -> None:
        self._refresh_task_data()
        title = self._format_title()
        self.title_label.setText(title)
        self.setWindowTitle(title)
        self.summary_label.setText(self._build_summary_line())
        self._apply_status_badges()
        self._refresh_description()
        self.date_card.set_value(self._task.day.isoformat() if isinstance(self._task.day, date) else "—")
        self.time_card.set_value(self._format_empty(self._task.time_text), muted=not bool((self._task.time_text or "").strip()))
        priority_text = self._format_empty(self._task.priority)
        self.priority_card.set_value(priority_text, muted=priority_text == "—")
        recurrence_text = self._format_recurrence()
        self.recurrence_card.set_value(recurrence_text, muted=recurrence_text == "—")

        project_text = self._project_text(fallback="Без проекта")
        parent_text = self._parent_title()
        marker_text = self._marker_color_text()
        marker_theme_text = self._marker_theme_text()
        self.detail_id_card.set_value(str(self._task.id))
        self.detail_project_card.set_value(project_text, muted=project_text == "Без проекта")
        self.detail_parent_card.set_value(parent_text, muted=parent_text == "—")
        self.detail_type_card.set_value(self._task_type_text())
        self.detail_marker_card.set_value(marker_text, muted=marker_text == "Нет")
        self.detail_marker_card.set_dot_color((self._task.marker_color or "").strip())
        self.detail_theme_card.set_value(marker_theme_text, muted=marker_theme_text == "Нет")

        self._refresh_attachments()
        self._reflow_cards()

    def _refresh_task_data(self) -> None:
        task = next((item for item in self._db.fetch_tasks() if item.id == self._task.id), None)
        if task is not None:
            self._task = task

    def _format_title(self) -> str:
        title = normalize_task_text_quotes((self._task.title or "").strip())
        return title or "Без названия"

    def _build_summary_line(self) -> str:
        parts = [self._project_text(fallback="Без проекта")]
        if isinstance(self._task.day, date):
            parts.append(self._task.day.isoformat())
        if (self._task.time_text or "").strip():
            parts.append(self._task.time_text.strip())
        if (self._task.priority or "").strip():
            parts.append(self._task.priority.strip())
        return " • ".join(part for part in parts if part)

    def _apply_status_badges(self) -> None:
        label, color = self._status_badge_payload()
        self.status_badge.setText(label)
        self.status_badge.setStyleSheet(self._badge_stylesheet(color))
        self.plan_badge.setVisible(bool(self._task.is_plan_task))
        if self._task.is_plan_task:
            self.plan_badge.setStyleSheet(self._badge_stylesheet("#6b5ad4"))

    def _status_badge_payload(self) -> tuple[str, str]:
        today = date.today()
        if self._task.done:
            return "Выполнено", self._palette.success
        if (self._task.priority or "").strip() == DEFERRED_PRIORITY:
            return "Отложено", self._palette.warning
        if isinstance(self._task.day, date) and self._task.day < today:
            return "! Просрочено", self._palette.danger
        return "В работе", self._palette.accent

    def _badge_stylesheet(self, accent: str) -> str:
        color = QColor(accent)
        bg = color.lighter(125).name() if color.isValid() else self._palette.chip_bg
        border = color.name() if color.isValid() else self._palette.chip_border
        return (
            f"background: {bg};"
            f"border: 1px solid {border};"
            "border-radius: 12px;"
            "padding: 5px 10px;"
            "font-weight: 600;"
            "color: #f4f6fb;"
        )

    def _refresh_description(self) -> None:
        self._clear_layout(self.description_body_layout)
        description = (self._task.description or "").strip()
        if not description:
            empty = QLabel("Нет описания", self.description_body)
            empty.setObjectName("TaskDetailsDescriptionEmpty")
            empty.setContentsMargins(14, 14, 14, 14)
            self.description_body_layout.addWidget(empty)
            return
        preview = _build_markdown_preview_widget(description, self.description_body, self._open_linked_task)
        preview.setContentsMargins(14, 14, 14, 14)
        preview.setMaximumHeight(112)
        self.description_body_layout.addWidget(preview)

    def _project_text(self, *, fallback: str = "—") -> str:
        if self._task.project_title:
            return f"{self._task.project_area} • {self._task.project_title}" if self._task.project_area else self._task.project_title
        return fallback

    def _parent_title(self) -> str:
        if self._task.parent_id is None:
            return "—"
        return self._task_title(self._task.parent_id)

    def _task_type_text(self) -> str:
        if self._task.parent_id is not None and self._task.is_plan_task:
            return "Пункт плана"
        if self._task.is_plan_task:
            return "Плановая задача"
        return "Обычная задача"

    def _marker_color_text(self) -> str:
        return self._MARKER_COLOR_LABELS.get((self._task.marker_color or "").strip(), "Нет")

    def _marker_theme_text(self) -> str:
        return self._MARKER_THEME_LABELS.get((self._task.marker_theme or "").strip().lower(), "Нет")

    def _format_recurrence(self) -> str:
        kind = (self._task.recurrence_kind or "").strip().lower()
        if not kind:
            return "—"
        base = self._RECURRENCE_LABELS.get(kind, kind)
        interval = max(1, int(self._task.recurrence_interval or 1))
        return base if interval <= 1 else f"{base}, интервал {interval}"

    @staticmethod
    def _format_empty(value: str, fallback: str = "—") -> str:
        normalized = (value or "").strip()
        return normalized or fallback

    def _task_title(self, task_id: int) -> str:
        if task_id not in self._tasks_by_id:
            self._tasks_by_id = {task.id: task for task in self._db.fetch_tasks()}
        task = self._tasks_by_id.get(task_id)
        if task is None:
            return "—"
        title = normalize_task_text_quotes((task.title or "").strip())
        return title or f"MN-{task_id}"

    def _open_edit_dialog(self) -> None:
        dialog = TaskEditDialog(self._task, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            self._db.update_task(
                self._task.id,
                title=values["title"],
                description=values["description"],
                day=values["day"],
                time_text=values["time_text"],
                priority=values["priority"],
                done=values["done"],
                project_id=values["project_id"],
                parent_id=self._task.parent_id,
                recurrence_kind=values["recurrence_kind"],
                recurrence_interval=values["recurrence_interval"],
                is_plan_task=values.get("is_plan_task", bool(self._task.is_plan_task)),
                plan_order=int(self._task.plan_order or 0),
                marker_color=values.get("marker_color", ""),
                marker_theme=values.get("marker_theme", ""),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self._refresh_view()

    def _open_linked_task(self, task_id: int) -> bool:
        task = self._tasks_by_id.get(task_id)
        if task is None:
            tasks = self._db.fetch_tasks()
            self._tasks_by_id = {item.id: item for item in tasks}
            task = self._tasks_by_id.get(task_id)
        if task is None:
            QMessageBox.warning(self, "Связанные задачи", f"Задача MN-{task_id} не найдена.")
            return False
        dialog = TaskDetailsDialog(task, parent=self)
        show_dialog_standard(dialog, self)
        return True

    def _load_attachment_sources(self) -> None:
        tasks = self._db.fetch_tasks()
        notes = self._db.fetch_notes()
        ideas_active = self._db.fetch_ideas(archived=False)
        active_ids = {idea.id for idea in ideas_active}
        ideas_archived = [idea for idea in self._db.fetch_ideas(archived=True) if idea.id not in active_ids]
        ideas = ideas_active + ideas_archived
        objects = self._db.fetch_objects()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        cloud_files = self._db.fetch_cloud_files()
        self._tasks_by_id = {task.id: task for task in tasks}
        self._notes_by_id = {note.id: note for note in notes}
        self._ideas_by_id = {idea.id: idea for idea in ideas}
        self._objects_by_id = {item.id: item for item in objects}
        self._maps_by_id = {item.id: item for item in maps}
        self._markers_by_id = {item.id: item for item in markers}
        self._cloud_files_by_id = {item.id: item for item in cloud_files}

    def _refresh_attachments(self) -> None:
        self._load_attachment_sources()
        self._attachments = self._db.fetch_task_attachments(self._task.id)
        self._clear_layout(self.attachments_list)
        if not self._attachments:
            empty = QLabel("Нет связанных элементов", self.links_host)
            empty.setObjectName("TaskDetailsLinksEmpty")
            self.attachments_list.addWidget(empty)
            return
        for attachment in self._attachments:
            row = QFrame(self.links_host)
            row.setObjectName("TaskAttachmentRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(10)

            kind_label = QLabel(attachment_kind_label(attachment.kind), row)
            kind_label.setObjectName("TaskAttachmentKind")
            link_text = self._attachment_display_text(attachment)
            link_label = QLabel(f"<a style='color:#6ecbe0;' href='{attachment.id}'>{link_text}</a>", row)
            link_label.setObjectName("TaskAttachmentLink")
            link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            link_label.setOpenExternalLinks(False)
            link_label.linkActivated.connect(lambda _link, att=attachment: self._open_attachment(att))

            row_layout.addWidget(kind_label)
            row_layout.addWidget(link_label, 1)
            self.attachments_list.addWidget(row)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout is not None:
                TaskDetailsDialog._clear_layout(child_layout)  # type: ignore[arg-type]
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _cloud_file_link_text(file_item) -> str:
        description = (file_item.description or "").strip()
        if description:
            try:
                payload = json.loads(description)
            except json.JSONDecodeError:
                return description
            if isinstance(payload, dict):
                text = (payload.get("text") or "").strip()
                if text:
                    return text
        return file_item.name

    def _attachment_display_text(self, attachment) -> str:
        if attachment.kind == "task":
            task = self._tasks_by_id.get(attachment.ref_id)
            if not task:
                return "Задача не найдена"
            if task.project_title:
                return f"{task.title} • {task.project_title}"
            return task.title
        if attachment.kind == "note":
            note = self._notes_by_id.get(attachment.ref_id)
            return note.title if note else "Заметка не найдена"
        if attachment.kind == "idea":
            idea = self._ideas_by_id.get(attachment.ref_id)
            if not idea:
                return "Идея не найдена"
            if idea.project_title:
                return f"{idea.title} • {idea.project_title}"
            return idea.title
        if attachment.kind == "object":
            obj = self._objects_by_id.get(attachment.ref_id)
            return obj.title if obj else "Объект не найден"
        if attachment.kind == "map":
            map_item = self._maps_by_id.get(attachment.ref_id)
            return map_item.title if map_item else "Карта не найдена"
        if attachment.kind == "marker":
            marker = self._markers_by_id.get(attachment.ref_id)
            if not marker:
                return "Метка не найдена"
            map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else ""
            if map_title:
                return f"{marker.name} • {map_title}"
            return marker.name
        if attachment.kind in {"file", "image"}:
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            return self._cloud_file_link_text(file_item) if file_item else "Файл не найден"
        return "Связь"

    def _open_attachment(self, attachment) -> None:
        if attachment.kind == "image":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Связи", "Файл изображения не найден.")
                return
            self._open_image_preview(file_item)
            return
        if attachment.kind == "task":
            task = self._tasks_by_id.get(attachment.ref_id)
            if not task:
                QMessageBox.warning(self, "Связи", "Задача не найдена.")
                return
            rows = [
                ("Название", task.title),
                ("Проект", task.project_title or "—"),
                ("Дата", task.day.isoformat()),
                ("Время", task.time_text or "—"),
                ("Приоритет", task.priority),
                ("Статус", "Выполнена" if task.done else "Активна"),
                ("Описание", task.description or "—"),
            ]
            self._open_info_dialog("Задача", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "file":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Связи", "Файл не найден.")
                return
            self._open_file_info(file_item)
            return
        if attachment.kind == "note":
            note = self._notes_by_id.get(attachment.ref_id)
            if not note:
                QMessageBox.warning(self, "Связи", "Заметка не найдена.")
                return
            rows = [
                ("Название", note.title),
                ("Проект", note.project or "—"),
                ("Обновлено", note.updated.strftime("%d.%m.%Y %H:%M")),
                ("Теги", ", ".join(note.tags) if note.tags else "—"),
                ("Избранное", "Да" if note.favorite else "Нет"),
                ("Вложения", "Да" if note.attachment else "Нет"),
                ("Описание", note.preview or "—"),
            ]
            self._open_info_dialog("Заметка", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "idea":
            idea = self._ideas_by_id.get(attachment.ref_id)
            if not idea:
                QMessageBox.warning(self, "Связи", "Идея не найдена.")
                return
            rows = [
                ("Название", idea.title),
                ("Проект", idea.project_title or "—"),
                ("Тип", idea.type or "—"),
                ("Статус", idea.status or "—"),
                ("Ценность", str(idea.value_score)),
                ("Сложность", str(idea.effort_score)),
                ("Источник", idea.source or "—"),
                ("Обновлено", idea.updated_at.strftime("%d.%m.%Y %H:%M")),
                ("Кратко", idea.summary or "—"),
                ("Описание", idea.body_md or "—"),
            ]
            self._open_info_dialog("Идея", rows, wrap_rows={"Кратко", "Описание"})
            return
        if attachment.kind == "object":
            obj = self._objects_by_id.get(attachment.ref_id)
            if not obj:
                QMessageBox.warning(self, "Связи", "Объект не найден.")
                return
            rows = [
                ("Название", obj.title),
                ("Каталог", obj.catalog or "—"),
                ("Тип", obj.object_type or "—"),
                ("Статус", obj.status or "—"),
                ("Создан", obj.created_at or "—"),
                ("Обновлен", obj.updated_at or "—"),
                ("Описание", obj.description or "—"),
            ]
            self._open_info_dialog("Объект", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "map":
            map_item = self._maps_by_id.get(attachment.ref_id)
            if not map_item:
                QMessageBox.warning(self, "Связи", "Карта не найдена.")
                return
            rows = [
                ("Название", map_item.title),
                ("Проект", map_item.project or "—"),
                ("Описание", map_item.description or "—"),
                ("Плитки", f"{map_item.tiles_w} × {map_item.tiles_h}"),
            ]
            self._open_info_dialog("Карта", rows, wrap_rows={"Описание"})
            return
        if attachment.kind == "marker":
            marker = self._markers_by_id.get(attachment.ref_id)
            if not marker:
                QMessageBox.warning(self, "Связи", "Метка не найдена.")
                return
            map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else "—"
            rows = [
                ("Название", marker.name),
                ("Карта", map_title),
                ("Тип", marker.type),
                ("Координаты", f"{marker.x:.0f}, {marker.y:.0f}"),
                ("Описание", marker.description or "—"),
                ("Свойства", marker.properties or "—"),
            ]
            self._open_info_dialog("Метка карты", rows, wrap_rows={"Описание", "Свойства"})

    def _open_info_dialog(self, title: str, rows: List[Tuple[str, str]], wrap_rows: Optional[Set[str]] = None) -> None:
        dialog = QDialog(self)
        dialog.setObjectName("TaskAttachmentInfoDialog")
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        wrap_rows = wrap_rows or set()
        for label, value in rows:
            if label in wrap_rows:
                value_label = _build_markdown_preview_widget(value, dialog, self._open_linked_task)
            else:
                value_label = QLabel(value or "—")
            form.addRow(label, value_label)
        layout.addLayout(form)

        close_button = QPushButton("Закрыть", dialog)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

        dialog.setStyleSheet(
            f"""
            QDialog#TaskAttachmentInfoDialog {{
                {MATH_PHYS_BACKGROUND}
                border: 1px solid {self._palette.border};
                border-radius: 10px;
            }}
            QDialog#TaskAttachmentInfoDialog QLabel {{
                color: {self._palette.text};
            }}
            QDialog#TaskAttachmentInfoDialog QPushButton {{
                background: {self._palette.elevated_bg};
                color: {self._palette.text};
                border: 1px solid {self._palette.border_strong};
                padding: 7px 14px;
                border-radius: 8px;
            }}
            """
        )
        show_dialog_standard(dialog, self)

    def _open_file_info(self, file_item) -> None:
        description = self._cloud_file_link_text(file_item)
        rows = [
            ("Название", file_item.name),
            ("Путь", file_item.rel_path),
            ("Описание", description),
            ("Размер", f"{file_item.size} байт"),
        ]
        self._open_info_dialog("Файл", rows, wrap_rows={"Путь", "Описание"})

    def _open_image_preview(self, file_item) -> None:
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "Изображение", "Папка облачного хранилища не настроена.")
            return
        images = collect_task_image_attachments(self._attachments, self._cloud_files_by_id)
        if not images:
            QMessageBox.warning(self, "Изображение", "Привязанные изображения не найдены.")
            return
        try:
            start_index = next(idx for idx, item in enumerate(images) if item.id == file_item.id)
        except StopIteration:
            start_index = 0
        dialog = TaskImagePreviewDialog(
            self,
            images=images,
            start_index=start_index,
            cloud_root=Path(cloud_root),
        )
        show_dialog_standard(dialog, self)

__all__ = ["TaskDetailsDialog"]
