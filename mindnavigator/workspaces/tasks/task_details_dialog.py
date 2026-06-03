"""TaskDetailsDialog class module for tasks workspace."""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QCheckBox, QGridLayout, QProgressBar, QPushButton, QSizePolicy, QTextEdit

from mindnavigator.storage import DEFERRED_PRIORITY
from mindnavigator.ui.context_entity_linking import attach_context_entity_linking
from mindnavigator.ui.dialogs import AttachFileSelectNav
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND, get_theme_palette

from ._shared import *  # noqa: F401,F403
from .gantt_duration_edit import GanttEstimateEdit
from .task_attachment_selector import (
    attachment_candidate_items,
    cloud_file_link_text,
    create_task_attachment_dialog,
    load_task_attachment_sources,
)
from .task_image_preview_dialog import TaskImagePreviewDialog
from .task_importance_labels import normalize_task_importance, task_importance_combo_items, task_importance_label


class _InlineViewLabel(QLabel):
    edit_requested = Signal()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            self.edit_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class InlineEditableField(QStackedWidget):
    value_committed = Signal(object)

    def __init__(self, editor: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TaskInlineEditableField")
        self.view_label = _InlineViewLabel("", self)
        self.view_label.setObjectName("TaskInlineViewLabel")
        self.view_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_label.edit_requested.connect(self.begin_edit)
        self.editor = editor

        edit_host = QWidget(self)
        edit_layout = QHBoxLayout(edit_host)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(6)
        edit_layout.addWidget(editor, 1)
        self.save_button = QToolButton(edit_host)
        self.save_button.setObjectName("TaskInlineCommitButton")
        self.save_button.setText("✓")
        self.save_button.setToolTip("Сохранить")
        self.save_button.clicked.connect(self.commit)
        edit_layout.addWidget(self.save_button)
        self.cancel_button = QToolButton(edit_host)
        self.cancel_button.setObjectName("TaskInlineCommitButton")
        self.cancel_button.setText("×")
        self.cancel_button.setToolTip("Отменить")
        self.cancel_button.clicked.connect(self.cancel)
        edit_layout.addWidget(self.cancel_button)

        self.addWidget(self.view_label)
        self.addWidget(edit_host)
        self.setCurrentIndex(0)

    def set_value(self, value: object, display_text: str | None = None) -> None:
        if isinstance(self.editor, QLineEdit):
            self.editor.setText(str(value or ""))
        elif isinstance(self.editor, QComboBox):
            index = self.editor.findData(value)
            if index >= 0:
                self.editor.setCurrentIndex(index)
        elif isinstance(self.editor, QDateEdit) and isinstance(value, date):
            self.editor.setDate(QDate(value.year, value.month, value.day))
        self.view_label.setText(display_text if display_text is not None else str(value or "—"))

    def begin_edit(self) -> None:
        self.setCurrentIndex(1)
        self.editor.setFocus()

    def set_form_editing(self, enabled: bool) -> None:
        self.save_button.setVisible(not enabled)
        self.cancel_button.setVisible(not enabled)
        self.setCurrentIndex(1 if enabled else 0)

    def cancel(self) -> None:
        self.setCurrentIndex(0)

    def commit(self) -> None:
        value = self.current_value()
        if value is None and not isinstance(self.editor, QComboBox):
            return
        self.value_committed.emit(value)
        self.setCurrentIndex(0)

    def current_value(self) -> object | None:
        if isinstance(self.editor, QLineEdit):
            text = self.editor.text().strip()
            if self.editor.inputMask() and not any(char.isdigit() for char in text):
                return ""
            return text
        elif isinstance(self.editor, QComboBox):
            return self.editor.currentData()
        elif isinstance(self.editor, QDateEdit):
            selected = self.editor.date()
            return date(selected.year(), selected.month(), selected.day())
        return None


class _InfoCard(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None, *, accent_dot: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("TaskDetailsInfoCard")
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("TaskDetailsCardTitle")
        self.title_label.setWordWrap(False)
        title_row.addWidget(self.title_label)
        title_row.addStretch(1)

        self.action_button = QToolButton(self)
        self.action_button.setObjectName("TaskDetailsCardAction")
        self.action_button.hide()
        title_row.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(title_row)

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(8)
        self.value_row = value_row

        self.dot_label = QLabel("●")
        self.dot_label.setObjectName("TaskDetailsCardDot")
        self.dot_label.setVisible(accent_dot)
        value_row.addWidget(self.dot_label, 0, Qt.AlignmentFlag.AlignTop)

        self.value_label = QLabel("")
        self.value_label.setObjectName("TaskDetailsCardValue")
        self.value_label.setWordWrap(True)
        value_row.addWidget(self.value_label, 1)
        value_row.addStretch(0)
        self._custom_value_widget = False

        layout.addLayout(value_row)
        self.setFixedHeight(62)

    def set_value(self, value: str, *, muted: bool = False) -> None:
        self.value_label.setText(value)
        self.value_label.setVisible(not self._custom_value_widget)
        self.value_label.setProperty("muted", bool(muted))
        self.value_label.style().unpolish(self.value_label)
        self.value_label.style().polish(self.value_label)
        self.value_label.update()

    def set_value_widget(self, widget: QWidget) -> None:
        self._custom_value_widget = True
        self.value_label.hide()
        self.value_row.insertWidget(1, widget, 1)

    def set_inline_editor(self, field: InlineEditableField) -> None:
        self.set_value_widget(field)

    def set_dot_color(self, color: str) -> None:
        normalized = (color or "").strip()
        self.dot_label.setVisible(bool(normalized))
        if normalized:
            self.dot_label.setStyleSheet(f"color: {normalized};")
        else:
            self.dot_label.setStyleSheet("")

    def set_action(self, text: str, handler) -> None:
        self.action_button.setText(text)
        self.action_button.clicked.connect(handler)

    def set_action_visible(self, visible: bool) -> None:
        self.action_button.setVisible(bool(visible))


class _PropertyRow(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None, *, accent_dot: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("TaskDetailsPropertyRow")
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(40)
        self._custom_value_widget = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 10, 4)
        layout.setSpacing(10)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("TaskDetailsPropertyTitle")
        self.title_label.setMinimumWidth(160)
        layout.addWidget(self.title_label, 0)

        self.dot_label = QLabel("●", self)
        self.dot_label.setObjectName("TaskDetailsCardDot")
        self.dot_label.setVisible(accent_dot)
        layout.addWidget(self.dot_label, 0)

        self.value_label = QLabel("", self)
        self.value_label.setObjectName("TaskDetailsPropertyValue")
        self.value_label.setWordWrap(False)
        layout.addWidget(self.value_label, 1)

        self.action_button = QToolButton(self)
        self.action_button.setObjectName("TaskDetailsPropertyAction")
        self.action_button.hide()
        layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignRight)

    def set_value(self, value: str, *, muted: bool = False) -> None:
        self.value_label.setText(value)
        self.value_label.setVisible(not self._custom_value_widget)
        self.value_label.setProperty("muted", bool(muted))
        self.value_label.style().unpolish(self.value_label)
        self.value_label.style().polish(self.value_label)
        self.value_label.update()

    def set_value_widget(self, widget: QWidget) -> None:
        self._custom_value_widget = True
        self.value_label.hide()
        self.layout().insertWidget(2, widget, 1)

    def set_inline_editor(self, field: InlineEditableField) -> None:
        self.set_value_widget(field)

    def set_dot_color(self, color: str) -> None:
        normalized = (color or "").strip()
        self.dot_label.setVisible(bool(normalized))
        self.dot_label.setStyleSheet(f"color: {normalized};" if normalized else "")

    def set_action(self, text: str, handler) -> None:
        self.action_button.setText(text)
        self.action_button.clicked.connect(handler)

    def set_action_visible(self, visible: bool) -> None:
        self.action_button.setVisible(bool(visible))


class TaskDetailsDialog(QDialog):
    _DEFAULT_SIZE = QSize(1360, 980)
    _PARAM_BREAKPOINTS = ((1040, 4), (720, 2), (0, 1))
    _DETAIL_BREAKPOINTS = ((1240, 6), (960, 3), (0, 2))

    _MARKER_COLOR_LABELS = {
        "": "Нет",
        "#2f6edb": "Синий",
        "#2f9f63": "Зеленый",
        "#d68a2f": "Оранжевый",
        "#b74a4a": "Красный",
        "#6b5ad4": "Фиолетовый",
        "#20f5d2": "Неоновый",
        "#4da3ff": "Голубой",
        "#8b5a3c": "Коричневый",
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
        "researches": "Исследования",
        "analysis": "Анализ",
        "dissection": "Разбор",
        "solution": "Решения",
        "debug": "Отладка",
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
        self.setMinimumSize(1180, 720)
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
        self._form_editing = False
        self.description_editor: QTextEdit | None = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("TaskDetailsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        root_layout.addWidget(self.scroll, 1)

        self.content = QWidget(self.scroll)
        self.content.setObjectName("TaskDetailsContent")
        self.content.setMinimumWidth(0)
        self.content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.scroll.setWidget(self.content)

        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(24, 16, 24, 14)
        self.content_layout.setSpacing(10)

        self._build_header()

        self.body_columns = QWidget(self.content)
        body_layout = QHBoxLayout(self.body_columns)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)
        self.left_column = QVBoxLayout()
        self.left_column.setContentsMargins(0, 0, 0, 0)
        self.left_column.setSpacing(10)
        self.right_column = QVBoxLayout()
        self.right_column.setContentsMargins(0, 0, 0, 0)
        self.right_column.setSpacing(10)
        body_layout.addLayout(self.left_column, 1)
        body_layout.addLayout(self.right_column, 1)
        self.content_layout.addWidget(self.body_columns, 1)

        self._build_description_section()
        self._build_key_params_section()
        self._build_details_section()
        self._build_links_section()
        self._build_images_section()
        self._build_concept_board_section()

        self.left_column.addStretch(1)
        self.right_column.addStretch(1)

        self.footer = QFrame(self)
        self.footer.setObjectName("TaskDetailsFooter")
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(26, 12, 26, 14)
        footer_layout.setSpacing(18)

        self.footer_created_label = QLabel("", self.footer)
        self.footer_created_label.setObjectName("TaskDetailsFooterMeta")
        footer_layout.addWidget(self.footer_created_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.footer_separator_label = QLabel("·", self.footer)
        self.footer_separator_label.setObjectName("TaskDetailsFooterMeta")
        footer_layout.addWidget(self.footer_separator_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.footer_updated_label = QLabel("", self.footer)
        self.footer_updated_label.setObjectName("TaskDetailsFooterMeta")
        footer_layout.addWidget(self.footer_updated_label, 0, Qt.AlignmentFlag.AlignVCenter)
        footer_layout.addStretch(1)

        self.footer_status_combo = QComboBox(self.footer)
        self.footer_status_combo.setObjectName("TaskDetailsFooterStatus")
        self.footer_status_combo.addItem("●  В работе", False)
        self.footer_status_combo.addItem("●  Выполнено", True)
        self.footer_status_combo.setEnabled(False)
        self.footer_status_combo.currentIndexChanged.connect(self._on_footer_status_changed)
        footer_layout.addWidget(self.footer_status_combo, 0, Qt.AlignmentFlag.AlignRight)

        root_layout.addWidget(self.footer)

        self._setup_shortcuts()
        self._apply_styles()
        self._refresh_view()

    def _build_header(self) -> None:
        self.header_card = QFrame(self.content)
        self.header_card.setObjectName("TaskDetailsHeaderCard")
        layout = QVBoxLayout(self.header_card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(12)

        self.title_inline = InlineEditableField(QLineEdit(self.header_card), self.header_card)
        self.title_inline.setObjectName("TaskDetailsTitleInline")
        self.title_inline.view_label.setObjectName("TaskDetailsTitle")
        self.title_inline.view_label.setWordWrap(True)
        self.title_inline.value_committed.connect(lambda value: self._save_inline_updates(title=str(value)))
        self.title_label = self.title_inline.view_label
        title_row.addWidget(self.title_inline, 1)

        self.header_close_button = QToolButton(self.header_card)
        self.header_close_button.setObjectName("TaskDetailsHeaderCloseButton")
        self.header_close_button.setText("Закрыть")
        self.header_close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_close_button.clicked.connect(self._cancel_or_close)
        title_row.addWidget(self.header_close_button, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        self.header_edit_button = QToolButton(self.header_card)
        self.header_edit_button.setObjectName("TaskDetailsHeaderEditButton")
        self.header_edit_button.setText("Редактировать")
        self.header_edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_edit_button.clicked.connect(self._open_edit_dialog)
        title_row.addWidget(self.header_edit_button, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        layout.addLayout(title_row)

        self.summary_label = QLabel("", self.header_card)
        self.summary_label.setObjectName("TaskDetailsSummary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.summary_label.hide()

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setSpacing(8)

        self.plan_badge = QLabel("План", self.header_card)
        self.plan_badge.setObjectName("TaskDetailsBadge")
        self.plan_badge.setVisible(False)
        badge_row.addWidget(self.plan_badge, 0, Qt.AlignmentFlag.AlignLeft)

        self.status_badge = QLabel("", self.header_card)
        self.status_badge.setObjectName("TaskDetailsBadge")
        badge_row.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignLeft)
        badge_row.addStretch(1)

        layout.addLayout(badge_row)
        self.status_badge.hide()
        self.content_layout.addWidget(self.header_card)

    def _build_description_section(self) -> None:
        self.description_card = self._build_section_card("Описание", icon="▤")
        self.description_body = QWidget(self.description_card)
        self.description_body.setObjectName("TaskDetailsDescriptionBody")
        self.description_body_layout = QVBoxLayout(self.description_body)
        self.description_body_layout.setContentsMargins(0, 0, 0, 0)
        self.description_body_layout.setSpacing(0)
        self.description_card.layout().addWidget(self.description_body)
        self.description_counter = QLabel("", self.description_card)
        self.description_counter.setObjectName("TaskDetailsDescriptionCounter")
        self.description_card.layout().addWidget(self.description_counter, 0, Qt.AlignmentFlag.AlignRight)
        self.left_column.addWidget(self.description_card, 1)

    def _build_key_params_section(self) -> None:
        self.params_card = QFrame(self.header_card)
        self.params_card.setObjectName("TaskDetailsHeaderParams")
        params_layout = QHBoxLayout(self.params_card)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.setSpacing(12)

        self.header_add_button = QToolButton(self.params_card)
        self.header_add_button.setObjectName("TaskDetailsHeaderAddButton")
        self.header_add_button.setText("+")
        self.header_add_button.setToolTip("Добавить связь")
        self.header_add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_add_button.setFixedSize(52, 62)
        self.header_add_button.clicked.connect(lambda _checked=False: self._open_attachment_dialog())
        self.header_add_button.setEnabled(False)
        params_layout.addWidget(self.header_add_button, 0, Qt.AlignmentFlag.AlignTop)

        self.params_host = QWidget(self.params_card)
        self.params_host.setObjectName("TaskDetailsHeaderParamsHost")
        params_layout.addWidget(self.params_host, 1)
        self.params_grid = QGridLayout()
        self.params_grid.setContentsMargins(0, 0, 0, 0)
        self.params_grid.setHorizontalSpacing(12)
        self.params_grid.setVerticalSpacing(8)
        self.params_host.setLayout(self.params_grid)

        self.detail_project_card = _InfoCard("Проект", self.params_card)
        self.project_inline = InlineEditableField(QComboBox(self.detail_project_card), self.detail_project_card)
        self.project_inline.editor.addItem("Без проекта", None)
        for project in self._db.fetch_projects():
            if project.archived:
                continue
            label = f"{project.area} • {project.title}" if project.area else project.title
            self.project_inline.editor.addItem(label, project.id)
        self.project_inline.value_committed.connect(lambda value: self._save_inline_updates(project_id=value))
        self.detail_project_card.set_inline_editor(self.project_inline)
        self.deadline_card = _InfoCard("Срок выполнения", self.params_card)
        self.priority_card = _InfoCard("Приоритет", self.params_card)
        self.importance_card = _InfoCard("Важность задачи", self.params_card)
        self.priority_inline = InlineEditableField(QComboBox(self.priority_card), self.priority_card)
        for label, value in (("Высокий", "High"), ("Средний", "Medium"), ("Низкий", "Low"), ("Отложенная", DEFERRED_PRIORITY)):
            self.priority_inline.editor.addItem(label, value)
        self.priority_inline.value_committed.connect(lambda value: self._save_inline_updates(priority=str(value)))
        self.priority_card.set_inline_editor(self.priority_inline)
        self.importance_inline = InlineEditableField(QComboBox(self.importance_card), self.importance_card)
        for label, value in task_importance_combo_items():
            self.importance_inline.editor.addItem(label, value)
        self.importance_inline.value_committed.connect(lambda value: self._save_inline_updates(importance=int(value)))
        self.importance_card.set_inline_editor(self.importance_inline)
        deadline_host = QWidget(self.deadline_card)
        deadline_host.setObjectName("TaskDetailsDeadlineEditor")
        deadline_layout = QHBoxLayout(deadline_host)
        deadline_layout.setContentsMargins(0, 0, 0, 0)
        deadline_layout.setSpacing(8)
        date_editor = QDateEdit(deadline_host)
        date_editor.setObjectName("TaskDetailsDeadlineDateEdit")
        date_editor.setCalendarPopup(True)
        date_editor.setDisplayFormat("dd.MM.yyyy")
        date_editor.setMinimumWidth(96)
        self.date_inline = InlineEditableField(date_editor, deadline_host)
        self.date_inline.setObjectName("TaskDetailsDeadlineDateInline")
        self.date_inline.setMinimumWidth(150)
        self.date_inline.value_committed.connect(lambda value: self._save_inline_updates(day=value))
        deadline_layout.addWidget(self.date_inline, 3)
        self.time_inline = InlineEditableField(QLineEdit(deadline_host), deadline_host)
        self.time_inline.setObjectName("TaskDetailsDeadlineTimeInline")
        self.time_inline.setMinimumWidth(90)
        self.time_inline.editor.setObjectName("TaskDetailsDeadlineTimeEdit")
        self.time_inline.editor.setPlaceholderText("HH:MM или пусто")
        self.time_inline.editor.setMinimumWidth(54)
        self.time_inline.editor.setInputMask("99:99;_")
        self.time_inline.value_committed.connect(lambda value: self._save_inline_updates(time_text=str(value)))
        deadline_layout.addWidget(self.time_inline, 2)
        self.deadline_card.set_value_widget(deadline_host)
        self.date_card = self.deadline_card
        self.time_card = self.deadline_card
        self._param_cards = [
            self.detail_project_card,
            self.deadline_card,
            self.priority_card,
            self.importance_card,
        ]
        for card in self._param_cards:
            self.params_grid.addWidget(card)
        self.header_card.layout().addWidget(self.params_card)

    def _build_details_section(self) -> None:
        self.details_card = QFrame(self.content)
        self.details_card.setObjectName("TaskDetailsSectionCard")
        details_layout = QVBoxLayout(self.details_card)
        details_layout.setContentsMargins(18, 16, 18, 16)
        details_layout.setSpacing(10)

        details_header = QHBoxLayout()
        details_header.setContentsMargins(0, 0, 0, 0)
        details_header.setSpacing(10)
        self.details_title = QLabel("☷  Свойства", self.details_card)
        self.details_title.setObjectName("TaskDetailsSectionTitle")
        details_header.addWidget(self.details_title, 0, Qt.AlignmentFlag.AlignLeft)
        details_header.addStretch(1)
        self.plan_task_checkbox = QCheckBox("План задача", self.details_card)
        self.plan_task_checkbox.setObjectName("TaskDetailsPlanCheck")
        self.plan_task_checkbox.setEnabled(False)
        details_header.addWidget(self.plan_task_checkbox, 0, Qt.AlignmentFlag.AlignRight)
        details_layout.addLayout(details_header)

        self.details_list = QVBoxLayout()
        self.details_list.setContentsMargins(0, 0, 0, 0)
        self.details_list.setSpacing(0)

        self.detail_id_card = _PropertyRow("ID", self.details_card)
        self.detail_parent_card = _PropertyRow("Родительская задача", self.details_card)
        self.detail_parent_card.set_action("Перенести к родителю", self._sync_schedule_to_parent)
        self.detail_type_card = _PropertyRow("Тип", self.details_card)
        self.detail_marker_card = _PropertyRow("Маркер", self.details_card, accent_dot=True)
        self.detail_theme_card = _PropertyRow("Тема маркера", self.details_card)
        self.status_card = _PropertyRow("Статус", self.details_card)
        self.recurrence_card = _PropertyRow("Повтор", self.details_card)
        self.recurrence_inline = InlineEditableField(QComboBox(self.recurrence_card), self.recurrence_card)
        for label, value in (("Без повтора", ""), ("Ежедневно", "daily"), ("Еженедельно", "weekly"), ("Ежемесячно", "monthly")):
            self.recurrence_inline.editor.addItem(label, value)
        self.recurrence_inline.value_committed.connect(lambda value: self._save_inline_updates(recurrence_kind=str(value)))
        self.recurrence_card.set_inline_editor(self.recurrence_inline)
        self.status_inline = InlineEditableField(QComboBox(self.status_card), self.status_card)
        self.status_inline.editor.addItem("Активна", False)
        self.status_inline.editor.addItem("Выполнена", True)
        self.status_inline.editor.currentIndexChanged.connect(self._on_status_inline_changed)
        self.status_inline.value_committed.connect(lambda value: self._save_inline_updates(done=bool(value)))
        self.status_card.set_inline_editor(self.status_inline)
        self.marker_color_inline = InlineEditableField(QComboBox(self.detail_marker_card), self.detail_marker_card)
        for value, label in self._MARKER_COLOR_LABELS.items():
            self.marker_color_inline.editor.addItem(label, value)
        self.marker_color_inline.value_committed.connect(lambda value: self._save_inline_updates(marker_color=str(value)))
        self.detail_marker_card.set_inline_editor(self.marker_color_inline)
        self.marker_theme_inline = InlineEditableField(QComboBox(self.detail_theme_card), self.detail_theme_card)
        for value, label in self._MARKER_THEME_LABELS.items():
            self.marker_theme_inline.editor.addItem(label, value)
        self.marker_theme_inline.value_committed.connect(lambda value: self._save_inline_updates(marker_theme=str(value)))
        self.detail_theme_card.set_inline_editor(self.marker_theme_inline)
        self._detail_cards = [
            self.detail_id_card,
            self.detail_parent_card,
            self.detail_type_card,
            self.detail_marker_card,
            self.detail_theme_card,
            self.status_card,
            self.recurrence_card,
        ]
        for card in self._detail_cards:
            self.details_list.addWidget(card)
        details_layout.addLayout(self.details_list)
        self.right_column.addWidget(self.details_card)

        self.gantt_card = self._build_section_card("GANTT / Время", icon="◴")
        self.gantt_metrics = QWidget(self.gantt_card)
        self.gantt_metrics.setObjectName("TaskDetailsGanttMetrics")
        gantt_metrics_layout = QHBoxLayout(self.gantt_metrics)
        gantt_metrics_layout.setContentsMargins(0, 0, 0, 0)
        gantt_metrics_layout.setSpacing(14)
        self.gantt_plan_label = self._build_gantt_metric("План")
        self.gantt_spent_label = self._build_gantt_metric("Потрачено")
        self.gantt_remaining_label = self._build_gantt_metric("Осталось")
        self.gantt_progress_label = self._build_gantt_metric("Прогресс")
        for metric in (
            self.gantt_plan_label,
            self.gantt_spent_label,
            self.gantt_remaining_label,
            self.gantt_progress_label,
        ):
            gantt_metrics_layout.addWidget(metric, 1)
        self.gantt_card.layout().addWidget(self.gantt_metrics)

        self.gantt_edit = GanttEstimateEdit(parent=self.gantt_card)
        self.gantt_edit.setObjectName("TaskDetailsGanttEdit")
        self.gantt_edit.setToolTip("Оценка длительности для режима GANTT в формате HH:MM.")
        self.gantt_edit.minutesCommitted.connect(self._on_gantt_estimate_committed)
        self.gantt_card.layout().addWidget(self.gantt_edit)
        self.gantt_progress = QProgressBar(self.gantt_card)
        self.gantt_progress.setObjectName("TaskDetailsGanttProgress")
        self.gantt_progress.setRange(0, 100)
        self.gantt_progress.setTextVisible(True)
        self.gantt_card.layout().addWidget(self.gantt_progress)
        self.right_column.addWidget(self.gantt_card)

    def _build_gantt_metric(self, title: str) -> QLabel:
        label = QLabel("", self.gantt_card)
        label.setObjectName("TaskDetailsGanttMetric")
        label.setProperty("metric_title", title)
        return label

    def _build_links_section(self) -> None:
        self.links_card = QFrame(self.content)
        self.links_card.setObjectName("TaskDetailsSectionCard")
        layout = QVBoxLayout(self.links_card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        self.links_title = QLabel("☍  Связи", self.links_card)
        self.links_title.setObjectName("TaskDetailsSectionTitle")
        header_layout.addWidget(self.links_title)
        header_layout.addStretch(1)

        self.links_add_button = QToolButton(self.links_card)
        self.links_add_button.setObjectName("TaskDetailsLinkAction")
        self.links_add_button.setText("+ Добавить")
        self.links_add_button.setEnabled(False)
        self.links_add_button.setToolTip("Добавление связей доступно из режима редактирования.")
        self.links_add_button.clicked.connect(lambda _checked=False: self._open_attachment_dialog())
        header_layout.addWidget(self.links_add_button)

        layout.addLayout(header_layout)

        self.links_toggle = QToolButton(self.links_card)
        self.links_toggle.setObjectName("TaskDetailsCollapseButton")
        self.links_toggle.setText("⌄")
        self.links_toggle.setToolTip("Развернуть связи")
        self.links_toggle.clicked.connect(lambda: self._toggle_section(self.links_host, self.links_toggle))
        header_layout.addWidget(self.links_toggle)

        self.links_host = QWidget(self.links_card)
        self.links_host.setObjectName("TaskDetailsLinksHost")
        self.attachments_list = QVBoxLayout(self.links_host)
        self.attachments_list.setContentsMargins(0, 0, 0, 0)
        self.attachments_list.setSpacing(8)
        layout.addWidget(self.links_host)
        self.links_host.setVisible(False)

        self.left_column.addWidget(self.links_card)

    def _build_images_section(self) -> None:
        self.images_card = QFrame(self.content)
        self.images_card.setObjectName("TaskDetailsSectionCard")
        layout = QVBoxLayout(self.images_card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        self.images_title = QLabel("▧  Изображения", self.images_card)
        self.images_title.setObjectName("TaskDetailsSectionTitle")
        header_layout.addWidget(self.images_title)
        header_layout.addStretch(1)
        self.images_add_button = QToolButton(self.images_card)
        self.images_add_button.setObjectName("TaskDetailsLinkAction")
        self.images_add_button.setText("+ Прикрепить")
        self.images_add_button.setEnabled(False)
        self.images_add_button.clicked.connect(lambda _checked=False: self._open_attachment_dialog(kind="image"))
        header_layout.addWidget(self.images_add_button)
        self.images_toggle = QToolButton(self.images_card)
        self.images_toggle.setObjectName("TaskDetailsCollapseButton")
        self.images_toggle.setText("⌄")
        self.images_toggle.setToolTip("Развернуть изображения")
        header_layout.addWidget(self.images_toggle)
        layout.addLayout(header_layout)

        self.images_host = QWidget(self.images_card)
        self.images_layout = QHBoxLayout(self.images_host)
        self.images_layout.setContentsMargins(0, 0, 0, 0)
        self.images_layout.setSpacing(8)
        layout.addWidget(self.images_host)
        self.images_host.setVisible(False)
        self.images_toggle.clicked.connect(lambda: self._toggle_section(self.images_host, self.images_toggle))
        self.left_column.addWidget(self.images_card)

    def _build_concept_board_section(self) -> None:
        self.concept_board_card = self._build_section_card("Навигатор концептборда", icon="⌘")
        self.concept_board_summary = QLabel(
            "Связанные идеи, заметки и объекты образуют маршрут задачи.",
            self.concept_board_card,
        )
        self.concept_board_summary.setObjectName("TaskDetailsLinksEmpty")
        self.concept_board_summary.setWordWrap(True)
        self.concept_board_card.layout().addWidget(self.concept_board_summary)
        self.concept_board_host = QWidget(self.concept_board_card)
        self.concept_board_layout = QHBoxLayout(self.concept_board_host)
        self.concept_board_layout.setContentsMargins(0, 0, 0, 0)
        self.concept_board_layout.setSpacing(6)
        self.concept_board_card.layout().addWidget(self.concept_board_host)
        self.right_column.addWidget(self.concept_board_card)

    @staticmethod
    def _toggle_section(body: QWidget, button: QToolButton) -> None:
        expanded = not body.isVisible()
        body.setVisible(expanded)
        button.setText("⌃" if expanded else "⌄")
        button.setToolTip("Свернуть блок" if expanded else "Развернуть блок")

    def _build_section_card(self, title: str, *, icon: str = "") -> QFrame:
        section = QFrame(self.content)
        section.setObjectName("TaskDetailsSectionCard")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title_text = f"{icon}  {title}" if icon else title
        title_label = QLabel(title_text, section)
        title_label.setObjectName("TaskDetailsSectionTitle")
        layout.addWidget(title_label)
        return section

    def _setup_shortcuts(self) -> None:
        self.edit_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        self.edit_shortcut.activated.connect(self._open_edit_dialog)
        self.cancel_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.cancel_shortcut.activated.connect(self._cancel_or_close)

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
                background: transparent;
                border: none;
            }}
            QFrame#TaskDetailsHeaderParams {{
                background: transparent;
                border: none;
            }}
            QFrame#TaskDetailsSectionCard,
            QFrame#TaskDetailsFooter {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
            }}
            QFrame#TaskDetailsSectionCard {{
                border-radius: 8px;
            }}
            QFrame#TaskDetailsFooter {{
                border-left: none;
                border-right: none;
                border-bottom: none;
                min-height: 54px;
            }}
            QFrame#TaskDetailsInfoCard {{
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.055);
                border-radius: 7px;
            }}
            QFrame#TaskDetailsPropertyRow {{
                background: rgba(255, 255, 255, 0.018);
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.045);
            }}
            QLabel#TaskDetailsPropertyTitle {{
                color: {palette.dim_text};
                font-size: 13px;
                font-weight: 500;
            }}
            QLabel#TaskDetailsPropertyValue {{
                color: {palette.text};
                font-size: 14px;
                font-weight: 600;
            }}
            QLabel#TaskDetailsPropertyValue[muted="true"] {{
                color: {palette.dim_text};
                font-weight: 500;
            }}
            QCheckBox#TaskDetailsPlanCheck {{
                color: {palette.text};
                font-size: 14px;
                spacing: 8px;
            }}
            QCheckBox#TaskDetailsPlanCheck::indicator {{
                width: 17px;
                height: 17px;
                border: 1px solid {palette.border_strong};
                border-radius: 4px;
                background: {palette.panel_alt_bg};
            }}
            QCheckBox#TaskDetailsPlanCheck::indicator:checked {{
                background: {palette.accent};
                border-color: {palette.accent};
            }}
            QToolButton#TaskDetailsHeaderAddButton {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
                font-size: 28px;
                font-weight: 300;
            }}
            QToolButton#TaskDetailsHeaderAddButton:hover {{
                border-color: {palette.accent};
                color: {palette.accent};
            }}
            QToolButton#TaskDetailsHeaderAddButton:disabled {{
                color: {palette.dim_text};
                background: {palette.panel_alt_bg};
                border: 1px solid {palette.border};
            }}
            QToolButton#TaskDetailsCollapseButton,
            QToolButton#TaskDetailsImageButton {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
                padding: 6px 10px;
            }}
            QToolButton#TaskDetailsCollapseButton:hover,
            QToolButton#TaskDetailsImageButton:hover {{
                border-color: {palette.accent};
                color: {palette.accent};
            }}
            QToolButton#TaskConceptBoardNode {{
                color: {palette.text};
                background: {palette.chip_bg};
                border: 1px solid {palette.chip_border};
                border-radius: 8px;
                padding: 10px 12px;
                min-height: 42px;
                text-align: left;
            }}
            QToolButton#TaskConceptBoardNode:hover {{
                border-color: {palette.accent};
                color: {palette.accent};
            }}
            QLabel#TaskConceptBoardArrow {{
                color: {palette.dim_text};
                font-size: 18px;
                padding: 0 2px;
            }}
            QLabel {{
                color: {palette.text};
            }}
            QLabel#TaskDetailsTitle {{
                color: #f2f5ff;
                font-size: 22px;
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
                font-size: 15px;
                font-weight: 600;
            }}
            QDialog#TaskDetailsDialog QLineEdit,
            QDialog#TaskDetailsDialog QTimeEdit {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 8px;
                padding: 6px 10px;
                min-height: 34px;
            }}
            QDialog#TaskDetailsDialog QLineEdit:focus,
            QDialog#TaskDetailsDialog QTimeEdit:focus {{
                border: 1px solid {palette.accent};
            }}
            QWidget#TaskDetailsDeadlineEditor {{
                background: transparent;
                border: none;
            }}
            QStackedWidget#TaskDetailsDeadlineDateInline {{
                min-width: 150px;
            }}
            QStackedWidget#TaskDetailsDeadlineTimeInline {{
                min-width: 90px;
            }}
            QDateEdit#TaskDetailsDeadlineDateEdit {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 8px;
                padding: 6px 6px;
                min-width: 96px;
                min-height: 34px;
            }}
            QLineEdit#TaskDetailsDeadlineTimeEdit {{
                min-width: 54px;
            }}
            QToolButton#TaskInlineCommitButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {palette.text};
                min-width: 22px;
                max-width: 22px;
                min-height: 30px;
                padding: 0;
            }}
            QToolButton#TaskInlineCommitButton:hover {{
                background: {palette.elevated_bg};
                border-color: {palette.border};
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
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.055);
                border-radius: 8px;
            }}
            QWidget#TaskDetailsDescriptionBody QLabel {{
                color: {palette.text};
            }}
            QLabel#TaskDetailsDescriptionEmpty {{
                color: {palette.dim_text};
                font-style: italic;
                padding: 4px 2px;
            }}
            QLabel#TaskDetailsDescriptionCounter {{
                color: {palette.dim_text};
                font-size: 12px;
            }}
            QLabel#TaskDetailsFooterMeta {{
                color: {palette.dim_text};
                font-size: 13px;
            }}
            QComboBox#TaskDetailsFooterStatus {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 8px;
                padding: 8px 34px 8px 14px;
                min-width: 150px;
                min-height: 28px;
                font-weight: 600;
            }}
            QComboBox#TaskDetailsFooterStatus:disabled {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
            }}
            QComboBox#TaskDetailsFooterStatus::drop-down {{
                border: none;
                width: 28px;
            }}
            QWidget#TaskDetailsDescriptionToolbar {{
                background: transparent;
                border: none;
            }}
            QToolButton#TaskDetailsDescriptionTool {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 6px;
                min-width: 30px;
                min-height: 26px;
                padding: 0 8px;
                font-weight: 700;
            }}
            QToolButton#TaskDetailsDescriptionTool:hover {{
                border-color: {palette.accent};
                color: {palette.accent};
            }}
            QTextEdit#TaskDetailsDescriptionInlineEdit {{
                background: transparent;
                color: {palette.text};
                border: none;
                padding: 8px 10px;
                selection-background-color: {palette.selection_bg};
            }}
            QProgressBar#TaskDetailsGanttProgress {{
                background: {palette.panel_alt_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 7px;
                min-height: 18px;
                text-align: center;
            }}
            QProgressBar#TaskDetailsGanttProgress::chunk {{
                background: {palette.accent};
                border-radius: 6px;
            }}
            QLabel#TaskDetailsGanttMetric {{
                color: {palette.text};
                font-size: 14px;
                font-weight: 600;
                padding: 2px 4px;
            }}
            QLabel#TaskAttachmentKind {{
                color: {palette.dim_text};
                font-weight: 600;
            }}
            QLabel#TaskAttachmentLink {{
                color: #6ecbe0;
            }}
            QFrame#TaskAttachmentRow {{
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}
            QLabel#TaskDetailsLinksEmpty {{
                color: {palette.dim_text};
                background: rgba(255, 255, 255, 0.025);
                border: 1px dashed {palette.border_strong};
                border-radius: 8px;
                padding: 16px 14px;
            }}
            QToolButton#TaskDetailsCardAction,
            QToolButton#TaskDetailsPropertyAction,
            QToolButton#TaskDetailsHeaderCloseButton,
            QToolButton#TaskDetailsHeaderEditButton,
            QToolButton#TaskDetailsLinkAction,
            QToolButton#TaskAttachmentRemove,
            QPushButton#TaskDetailsSecondaryButton,
            QPushButton#TaskDetailsPrimaryButton {{
                border-radius: 9px;
                min-height: 36px;
                padding: 0 18px;
                font-weight: 600;
                text-align: center;
            }}
            QToolButton#TaskDetailsCardAction,
            QToolButton#TaskDetailsPropertyAction,
            QToolButton#TaskDetailsHeaderCloseButton,
            QToolButton#TaskDetailsHeaderEditButton,
            QToolButton#TaskDetailsLinkAction,
            QToolButton#TaskAttachmentRemove,
            QPushButton#TaskDetailsSecondaryButton {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
            }}
            QToolButton#TaskDetailsCardAction:hover,
            QToolButton#TaskDetailsPropertyAction:hover,
            QToolButton#TaskDetailsHeaderCloseButton:hover,
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
            QToolButton#TaskAttachmentRemove {{
                color: {palette.danger};
                min-height: 24px;
                padding: 0 8px;
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
            QToolButton#TaskDetailsHeaderEditButton {{
                background: {palette.accent};
                color: #f6f8ff;
                border: 1px solid {palette.accent};
            }}
            QToolButton#TaskDetailsHeaderEditButton:hover {{
                background: {palette.accent_hover};
                border-color: {palette.accent_hover};
            }}
            """
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._reflow_cards()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        self._reflow_cards()

    def _reflow_cards(self) -> None:
        self._reflow_params_grid(4)

    def _reflow_params_grid(self, columns: int) -> None:
        while self.params_grid.count():
            self.params_grid.takeAt(0)
        columns = max(1, columns)
        for index, widget in enumerate(self._param_cards):
            row = index // columns
            column = index % columns
            self.params_grid.addWidget(widget, row, column)
        for column in range(columns):
            self.params_grid.setColumnStretch(column, 1)

    @staticmethod
    def _reflow_grid(layout: QGridLayout, widgets: list[QWidget], columns: int) -> None:
        while layout.count():
            layout.takeAt(0)
        columns = max(1, columns)
        for index, widget in enumerate(widgets):
            row = index // columns
            column = index % columns
            layout.addWidget(widget, row, column)
        for column in range(columns):
            layout.setColumnStretch(column, 1)

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
        self.title_inline.set_value(title, title)
        self.setWindowTitle(title)
        self.summary_label.setText(self._build_summary_line())
        self._apply_status_badges()
        self._refresh_description()
        date_text = self._task.day.isoformat() if isinstance(self._task.day, date) else "—"
        self.date_card.set_value(date_text)
        self.date_inline.set_value(self._task.day, date_text)
        time_text = self._format_empty(self._task.time_text)
        self.time_card.set_value(time_text, muted=not bool((self._task.time_text or "").strip()))
        self.time_inline.set_value(self._task.time_text, time_text)
        priority_text = self._format_empty(self._task.priority)
        self.priority_card.set_value(priority_text, muted=priority_text == "—")
        self.priority_inline.set_value(self._task.priority, priority_text)
        importance = normalize_task_importance(getattr(self._task, "importance", 3))
        importance_text = task_importance_label(importance)
        self.importance_card.set_value(importance_text)
        self.importance_inline.set_value(importance, importance_text)
        recurrence_text = self._format_recurrence()
        self.recurrence_card.set_value(recurrence_text, muted=recurrence_text == "—")
        self.recurrence_inline.set_value(self._task.recurrence_kind, recurrence_text)
        status_text = "Выполнена" if self._task.done else "Активна"
        self.status_card.set_value(status_text)
        self.status_inline.set_value(bool(self._task.done), status_text)
        self.footer_status_combo.blockSignals(True)
        self.footer_status_combo.setCurrentIndex(max(0, self.footer_status_combo.findData(bool(self._task.done))))
        self.footer_status_combo.blockSignals(False)
        self._refresh_footer_metadata()

        project_text = self._project_text(fallback="Без проекта")
        self.gantt_edit.set_minutes(self._effective_gantt_estimate_minutes())
        parent_text = self._parent_title()
        marker_text = self._marker_color_text()
        marker_theme_text = self._marker_theme_text()
        self.detail_id_card.set_value(str(self._task.id))
        self.plan_task_checkbox.setChecked(bool(self._task.is_plan_task))
        self.detail_project_card.set_value(project_text, muted=project_text == "Без проекта")
        self.project_inline.set_value(self._task.project_id, project_text)
        self._refresh_gantt_progress()
        self.detail_parent_card.set_value(parent_text, muted=parent_text == "—")
        self.detail_parent_card.set_action_visible(self._parent_schedule_mismatch())
        self.detail_type_card.set_value(self._task_type_text())
        self.detail_marker_card.set_value(marker_text, muted=marker_text == "Нет")
        self.detail_marker_card.set_dot_color((self._task.marker_color or "").strip())
        self.detail_theme_card.set_value(marker_theme_text, muted=marker_theme_text == "Нет")
        self.marker_color_inline.set_value(self._task.marker_color, marker_text)
        self.marker_theme_inline.set_value(self._task.marker_theme, marker_theme_text)

        self._refresh_attachments()
        self._reflow_cards()

    def _refresh_footer_metadata(self) -> None:
        created_text = self._format_task_timestamp(getattr(self._task, "created_at", ""))
        if created_text == "—":
            schedule_time = (self._task.time_text or "").strip()
            created_text = self._format_date_time(self._task.day, schedule_time)
        updated_text = self._format_task_timestamp(getattr(self._task, "updated_at", ""))
        self.footer_created_label.setText(f"Создано: {created_text}")
        self.footer_updated_label.setText(f"Обновлено: {updated_text}")

    @classmethod
    def _format_task_timestamp(cls, value: str) -> str:
        raw = (value or "").strip()
        if not raw:
            return "—"
        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return raw
        return cls._format_date_time(parsed.date(), f"{parsed.hour:02d}:{parsed.minute:02d}")

    @staticmethod
    def _format_date_time(day: date, time_text: str = "") -> str:
        months = (
            "янв", "фев", "мар", "апр", "мая", "июн",
            "июл", "авг", "сен", "окт", "ноя", "дек",
        )
        month = months[max(1, min(12, day.month)) - 1]
        time_part = (time_text or "").strip()
        if time_part:
            return f"{day.day} {month} {day.year}, {time_part}"
        return f"{day.day} {month} {day.year}"

    def _refresh_task_data(self) -> None:
        task = next((item for item in self._db.fetch_tasks() if item.id == self._task.id), None)
        if task is not None:
            self._task = task

    def _effective_gantt_estimate_minutes(self) -> int:
        stored_minutes = max(0, int(self._task.gantt_estimate_minutes or 0))
        if stored_minutes > 0:
            return stored_minutes
        from .cast_gantt import TasksGanttCast

        return max(5, int(TasksGanttCast.estimate_task_minutes(self._task)))

    def _refresh_gantt_progress(self) -> None:
        planned = max(0, int(self._effective_gantt_estimate_minutes()))
        spent = max(0, int(getattr(self._task, "time_spent_minutes", 0) or 0))
        remaining = max(0, planned - spent)
        progress = 0 if planned <= 0 else min(100, round(spent / planned * 100))
        self.gantt_plan_label.setText(f"План\n{self._format_minutes_short(planned)}")
        self.gantt_spent_label.setText(f"Потрачено\n{self._format_minutes_short(spent)}")
        self.gantt_remaining_label.setText(f"Осталось\n{self._format_minutes_short(remaining)}")
        self.gantt_progress_label.setText(f"Прогресс\n{progress}%")
        self.gantt_progress.setValue(progress)
        self.gantt_progress.setFormat(f"{progress}%")

    @staticmethod
    def _format_minutes_short(minutes: int) -> str:
        minutes = max(0, int(minutes or 0))
        hours, rest = divmod(minutes, 60)
        if hours and rest:
            return f"{hours} ч {rest} мин"
        if hours:
            return f"{hours} ч"
        return f"{rest} мин"

    def _on_gantt_estimate_committed(self, minutes: int) -> None:
        if (
            int(self._task.gantt_estimate_minutes or 0) == int(minutes)
            and bool(self._task.gantt_forecasted)
        ):
            return
        self._db.set_task_gantt_estimate(self._task.id, minutes, forecasted=True)
        self._refresh_task_data()
        self._refresh_parent_workspace()

    def _refresh_parent_workspace(self) -> None:
        current = self.parent()
        visited: set[int] = set()
        while current is not None and id(current) not in visited:
            visited.add(id(current))
            refresh = getattr(current, "refresh", None)
            if callable(refresh):
                refresh()
                return
            current = current.parent() if hasattr(current, "parent") else None

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
        self.description_editor = None
        self._clear_layout(self.description_body_layout)
        description = (self._task.description or "").strip()
        self.description_counter.setText(f"{len(description)} / 2000")
        if not description:
            empty = QLabel("Нет описания", self.description_body)
            empty.setObjectName("TaskDetailsDescriptionEmpty")
            empty.setContentsMargins(16, 16, 16, 16)
            empty.installEventFilter(self)
            self.description_body_layout.addWidget(empty)
            return
        preview = _build_markdown_preview_widget(description, self.description_body, self._open_linked_task)
        preview.setContentsMargins(16, 16, 16, 16)
        preview.setMinimumHeight(260)
        preview.installEventFilter(self)
        self.description_body_layout.addWidget(preview)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        if (
            event.type() == QEvent.Type.MouseButtonDblClick
            and watched.parent() is self.description_body
        ):
            self._begin_description_inline_edit()
            return True
        return super().eventFilter(watched, event)

    def _begin_description_inline_edit(self, *, form_editing: bool = False) -> None:
        self._clear_layout(self.description_body_layout)
        toolbar = self._build_description_toolbar()
        self.description_body_layout.addWidget(toolbar)
        editor = QTextEdit(self.description_body)
        editor.setObjectName("TaskDetailsDescriptionInlineEdit")
        editor.setAcceptRichText(True)
        editor.setMinimumHeight(260)
        self._set_description_editor_text(editor, self._task.description or "")
        editor.textChanged.connect(lambda: self.description_counter.setText(f"{len(editor.toPlainText().strip())} / 2000"))
        self.description_editor = editor
        attach_context_entity_linking(
            editor,
            self._db,
            source_type="task",
            source_id_getter=lambda: int(self._task.id),
            source_field="description",
            refresh_callback=self._refresh_attachments,
        )
        self.description_body_layout.addWidget(editor)
        if form_editing:
            return
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel_button = QPushButton("Отмена", self.description_body)
        cancel_button.clicked.connect(self._refresh_description)
        button_row.addWidget(cancel_button)
        save_button = QPushButton("Сохранить", self.description_body)
        save_button.clicked.connect(lambda: self._save_inline_updates(description=self._description_editor_text()))
        button_row.addWidget(save_button)
        self.description_body_layout.addLayout(button_row)
        editor.setFocus()

    def _build_description_toolbar(self) -> QWidget:
        toolbar = QWidget(self.description_body)
        toolbar.setObjectName("TaskDetailsDescriptionToolbar")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 8, 8, 0)
        layout.setSpacing(6)
        actions = (
            ("B", "Жирный", lambda: self._toggle_description_format("bold")),
            ("I", "Курсив", lambda: self._toggle_description_format("italic")),
            ("H2", "Подзаголовок", lambda: self._insert_description_prefix("## ")),
            ("•", "Список", lambda: self._insert_description_prefix("- ")),
            ("1.", "Нумерованный список", lambda: self._insert_description_prefix("1. ")),
            (">", "Цитата", lambda: self._insert_description_prefix("> ")),
        )
        for label, tooltip, handler in actions:
            button = QToolButton(toolbar)
            button.setObjectName("TaskDetailsDescriptionTool")
            button.setText(label)
            button.setToolTip(tooltip)
            button.clicked.connect(handler)
            layout.addWidget(button)
        layout.addStretch(1)
        return toolbar

    @staticmethod
    def _set_description_editor_text(editor: QTextEdit, text: str) -> None:
        if "<" in text and ">" in text:
            editor.setHtml(text)
            return
        editor.setMarkdown(text)

    def _description_editor_text(self) -> str:
        if self.description_editor is None:
            return self._task.description
        to_markdown = getattr(self.description_editor, "toMarkdown", None)
        if callable(to_markdown):
            return str(to_markdown()).strip()
        return self.description_editor.toPlainText().strip()

    def _toggle_description_format(self, mode: str) -> None:
        editor = self.description_editor
        if editor is None:
            return
        if mode == "bold":
            normal = int(QFont.Weight.Normal)
            bold = int(QFont.Weight.Bold)
            editor.setFontWeight(normal if editor.fontWeight() > normal else bold)
        elif mode == "italic":
            editor.setFontItalic(not editor.fontItalic())
        editor.setFocus()

    def _insert_description_prefix(self, prefix: str) -> None:
        editor = self.description_editor
        if editor is None:
            return
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText(prefix)
        editor.setTextCursor(cursor)
        editor.setFocus()

    def _save_inline_updates(self, **changes) -> bool:
        payload = {
            "title": self._task.title,
            "description": self._task.description,
            "day": self._task.day,
            "time_text": self._task.time_text,
            "priority": self._task.priority,
            "done": self._task.done,
            "project_id": self._task.project_id,
            "parent_id": self._task.parent_id,
            "recurrence_kind": self._task.recurrence_kind,
            "recurrence_interval": self._task.recurrence_interval,
            "is_plan_task": self._task.is_plan_task,
            "plan_order": self._task.plan_order,
            "marker_color": self._task.marker_color,
            "marker_theme": self._task.marker_theme,
            "project_task_type_id": self._task.project_task_type_id,
            "importance": self._task.importance,
        }
        payload.update(changes)
        tasks_model = self._tasks_model()
        if tasks_model is not None:
            row_idx = tasks_model.row_for_task_id(self._task.id)
            if row_idx >= 0:
                model_payload = {
                    key: payload[key]
                    for key in (
                        "title",
                        "description",
                        "day",
                        "time_text",
                        "priority",
                        "importance",
                        "done",
                        "project_id",
                        "recurrence_kind",
                        "recurrence_interval",
                        "is_plan_task",
                        "marker_color",
                        "marker_theme",
                        "project_task_type_id",
                    )
                }
                try:
                    while True:
                        try:
                            tasks_model.update_task_by_row(row_idx, **model_payload)
                            break
                        except TypeError as exc:
                            unsupported = next(
                                (
                                    field
                                    for field in ("project_task_type_id", "importance")
                                    if field in str(exc) and field in model_payload
                                ),
                                None,
                            )
                            if unsupported is None:
                                raise
                            model_payload.pop(unsupported)
                except ValueError as exc:
                    QMessageBox.warning(self, "Проверка", str(exc))
                    return False
                self._refresh_view()
                return True
        try:
            self._db.update_task(task_id=self._task.id, **payload)
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return False
        self._refresh_view()
        self._refresh_parent_workspace()
        return True

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

    def _parent_task(self) -> Optional[TaskRow]:
        if self._task.parent_id is None:
            return None
        if self._task.parent_id not in self._tasks_by_id:
            self._tasks_by_id = {task.id: task for task in self._db.fetch_tasks()}
        return self._tasks_by_id.get(self._task.parent_id)

    def _tasks_model(self):
        current = self.parent()
        visited: set[int] = set()
        while current is not None and id(current) not in visited:
            visited.add(id(current))
            model_getter = getattr(current, "model", None)
            if callable(model_getter):
                try:
                    model = model_getter()
                except TypeError:
                    model = None
                if (
                    model is not None
                    and hasattr(model, "row_for_task_id")
                    and hasattr(model, "update_task_by_row")
                    and hasattr(model, "move_task_to_parent_schedule")
                ):
                    return model
            current = current.parent() if hasattr(current, "parent") else None
        return None

    def _parent_schedule_mismatch(self) -> bool:
        parent_task = self._parent_task()
        if parent_task is None:
            return False
        return self._task.day != parent_task.day or (self._task.time_text or "") != (parent_task.time_text or "")

    def _sync_schedule_to_parent(self) -> None:
        parent_task = self._parent_task()
        if parent_task is None or not self._parent_schedule_mismatch():
            return
        tasks_model = self._tasks_model()
        if tasks_model is not None and tasks_model.move_task_to_parent_schedule(self._task.id, parent_task.id):
            self._refresh_view()
            return
        try:
            self._db.update_task(
                self._task.id,
                title=self._task.title,
                description=self._task.description,
                day=parent_task.day,
                time_text=parent_task.time_text,
                priority=self._task.priority,
                done=self._task.done,
                project_id=self._task.project_id,
                parent_id=self._task.parent_id,
                recurrence_kind=self._task.recurrence_kind,
                recurrence_interval=self._task.recurrence_interval,
                is_plan_task=bool(self._task.is_plan_task),
                plan_order=int(self._task.plan_order or 0),
                marker_color=self._task.marker_color,
                marker_theme=self._task.marker_theme,
                project_task_type_id=self._task.project_task_type_id,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self._refresh_view()

    def _open_edit_dialog(self) -> None:
        if self._form_editing:
            self._save_form_updates()
            return
        self._set_form_editing(True)

    def _editable_fields(self) -> tuple[InlineEditableField, ...]:
        return (
            self.title_inline,
            self.project_inline,
            self.date_inline,
            self.time_inline,
            self.priority_inline,
            self.importance_inline,
            self.recurrence_inline,
            self.status_inline,
            self.marker_color_inline,
            self.marker_theme_inline,
        )

    def _set_form_editing(self, enabled: bool) -> None:
        self._form_editing = bool(enabled)
        for field in self._editable_fields():
            field.set_form_editing(enabled)
        self.footer_status_combo.setEnabled(enabled)
        if enabled:
            self._begin_description_inline_edit(form_editing=True)
            self.header_close_button.setText("Отменить")
            self.header_edit_button.setText("Сохранить")
            self.links_add_button.setEnabled(True)
            self.images_add_button.setEnabled(True)
            self.header_add_button.setEnabled(True)
            self.plan_task_checkbox.setEnabled(True)
            if self.links_host.isHidden():
                self._toggle_section(self.links_host, self.links_toggle)
            if self.images_host.isHidden():
                self._toggle_section(self.images_host, self.images_toggle)
            self._refresh_attachments()
            self._reflow_cards()
            return
        self.header_close_button.setText("Закрыть")
        self.header_edit_button.setText("Редактировать")
        self.links_add_button.setEnabled(False)
        self.images_add_button.setEnabled(False)
        self.header_add_button.setEnabled(False)
        self.plan_task_checkbox.setEnabled(False)
        self._refresh_view()
        self._reflow_cards()

    def _cancel_or_close(self) -> None:
        if self._form_editing:
            self._set_form_editing(False)
            return
        self.reject()

    def _save_form_updates(self) -> None:
        description = self._description_editor_text() if self.description_editor is not None else self._task.description
        if not self._save_inline_updates(
            title=str(self.title_inline.current_value() or ""),
            description=description,
            project_id=self.project_inline.current_value(),
            day=self.date_inline.current_value(),
            time_text=str(self.time_inline.current_value() or ""),
            priority=str(self.priority_inline.current_value() or ""),
            importance=int(self.importance_inline.current_value() or 3),
            recurrence_kind=str(self.recurrence_inline.current_value() or ""),
            done=bool(self.footer_status_combo.currentData()),
            is_plan_task=bool(self.plan_task_checkbox.isChecked()),
            marker_color=str(self.marker_color_inline.current_value() or ""),
            marker_theme=str(self.marker_theme_inline.current_value() or ""),
        ):
            return
        self._set_form_editing(False)

    def _on_footer_status_changed(self, _index: int) -> None:
        if not hasattr(self, "status_inline"):
            return
        value = self.footer_status_combo.currentData()
        target_index = self.status_inline.editor.findData(bool(value))
        if target_index >= 0 and self.status_inline.editor.currentIndex() != target_index:
            self.status_inline.editor.blockSignals(True)
            self.status_inline.editor.setCurrentIndex(target_index)
            self.status_inline.editor.blockSignals(False)

    def _on_status_inline_changed(self, _index: int) -> None:
        if not hasattr(self, "footer_status_combo"):
            return
        value = self.status_inline.editor.currentData()
        target_index = self.footer_status_combo.findData(bool(value))
        if target_index >= 0 and self.footer_status_combo.currentIndex() != target_index:
            self.footer_status_combo.blockSignals(True)
            self.footer_status_combo.setCurrentIndex(target_index)
            self.footer_status_combo.blockSignals(False)

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
        sources = load_task_attachment_sources(self._db)
        self._tasks_by_id = sources.tasks_by_id
        self._notes_by_id = sources.notes_by_id
        self._ideas_by_id = sources.ideas_by_id
        self._objects_by_id = sources.objects_by_id
        self._maps_by_id = sources.maps_by_id
        self._markers_by_id = sources.markers_by_id
        self._cloud_files_by_id = sources.cloud_files_by_id

    def _open_attachment_dialog(self, *, kind: str | None = None) -> None:
        self._load_attachment_sources()
        sources = load_task_attachment_sources(self._db)
        dialog, kind_combo, item_combo = create_task_attachment_dialog(
            self,
            sources,
            current_task_id=self._task.id,
            kind=kind,
            file_picker_factory=AttachFileSelectNav,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        ref_id = item_combo.currentData()
        if ref_id is None:
            QMessageBox.warning(self, "Связи", "Нет доступных элементов для добавления.")
            return
        self._db.add_task_attachment(self._task.id, str(kind_combo.currentData()), int(ref_id))
        self._refresh_attachments()

    def _attachment_candidates(self, kind: str) -> list[tuple[str, int]]:
        sources = load_task_attachment_sources(self._db)
        return attachment_candidate_items(sources, kind, current_task_id=self._task.id)

    def _remove_attachment(self, attachment) -> None:
        self._db.delete_task_attachment(attachment.id)
        self._refresh_attachments()

    def _refresh_attachments(self) -> None:
        self._load_attachment_sources()
        self._attachments = self._db.fetch_task_attachments(self._task.id)
        self._clear_layout(self.attachments_list)
        self._clear_layout(self.images_layout)
        relation_attachments = [attachment for attachment in self._attachments if attachment.kind != "image"]
        image_attachments = [attachment for attachment in self._attachments if attachment.kind == "image"]
        self._refresh_concept_board_navigator(relation_attachments)
        if not relation_attachments:
            empty = QLabel("Нет связанных элементов", self.links_host)
            empty.setObjectName("TaskDetailsLinksEmpty")
            self.attachments_list.addWidget(empty)
        for attachment in relation_attachments:
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
            if self._form_editing:
                remove_button = QToolButton(row)
                remove_button.setObjectName("TaskAttachmentRemove")
                remove_button.setText("Удалить")
                remove_button.clicked.connect(lambda _checked=False, att=attachment: self._remove_attachment(att))
                row_layout.addWidget(remove_button)
            self.attachments_list.addWidget(row)
        if not image_attachments:
            empty = QLabel("Изображения не прикреплены", self.images_host)
            empty.setObjectName("TaskDetailsLinksEmpty")
            self.images_layout.addWidget(empty)
        for attachment in image_attachments:
            image_host = QFrame(self.images_host)
            image_layout = QVBoxLayout(image_host)
            image_layout.setContentsMargins(0, 0, 0, 0)
            image_layout.setSpacing(4)
            button = QToolButton(image_host)
            button.setObjectName("TaskDetailsImageButton")
            button.setText(self._attachment_display_text(attachment))
            button.setToolTip("Открыть изображение")
            button.clicked.connect(lambda _checked=False, att=attachment: self._open_attachment(att))
            image_layout.addWidget(button)
            if self._form_editing:
                remove_button = QToolButton(image_host)
                remove_button.setObjectName("TaskAttachmentRemove")
                remove_button.setText("Удалить")
                remove_button.clicked.connect(lambda _checked=False, att=attachment: self._remove_attachment(att))
                image_layout.addWidget(remove_button)
            self.images_layout.addWidget(image_host, 1)

    def _refresh_concept_board_navigator(self, attachments: List) -> None:
        self._clear_layout(self.concept_board_layout)
        navigable = [attachment for attachment in attachments if attachment.kind in {"idea", "note", "task", "object", "map", "marker"}]
        self.concept_board_summary.setVisible(not navigable)
        visible_items = navigable[:4]
        for index, attachment in enumerate(visible_items):
            button = QToolButton(self.concept_board_host)
            button.setObjectName("TaskConceptBoardNode")
            button.setText(f"{attachment_kind_label(attachment.kind)}\n{self._attachment_display_text(attachment)}")
            button.setToolTip("Открыть связанную сущность")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.clicked.connect(lambda _checked=False, att=attachment: self._open_attachment(att))
            self.concept_board_layout.addWidget(button, 1)
            if index < len(visible_items) - 1:
                arrow = QLabel("→", self.concept_board_host)
                arrow.setObjectName("TaskConceptBoardArrow")
                self.concept_board_layout.addWidget(arrow, 0, Qt.AlignmentFlag.AlignVCenter)

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
        return cloud_file_link_text(file_item)

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
            self._open_linked_task(attachment.ref_id)
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
            comments_by_file_id={
                int(attachment.ref_id): attachment.comment
                for attachment in self._attachments
                if attachment.kind == "image"
            },
        )
        show_dialog_standard(dialog, self)

__all__ = ["TaskDetailsDialog"]
