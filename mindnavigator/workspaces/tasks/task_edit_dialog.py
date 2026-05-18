"""TaskEditDialog class module for tasks workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from PySide6.QtCore import QEvent, QTimer
from mindnavigator.ui.dialogs.frameless_patch import (
    ensure_minimizable_task_dialog_overlay,
    prepare_minimizable_task_dialog_for_show,
    show_minimizable_task_dialog,
)
from mindnavigator.ui.dialogs import AttachFileSelectNav
from mindnavigator.ui.dialogs.task_dialog_debug import debug_task_dialog
from mindnavigator.ui.filterable_combobox import FilterableComboBox
from mindnavigator.ui.styles import TITLEBAR_BACKGROUND, get_theme_palette
from .quick_project_create_dialog import QuickProjectCreateDialog
from .task_image_preview_dialog import TaskImagePreviewDialog


class _TaskDialogHeader(QFrame):
    def __init__(self, dialog: "TaskEditDialog", title: str) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._dragging = False
        self._drag_pos = QPoint()
        self.setObjectName("TaskDialogHeader")
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 10, 0)
        layout.setSpacing(10)

        self.marker_label = QLabel("✦")
        self.marker_label.setObjectName("TaskDialogHeaderMarker")
        layout.addWidget(self.marker_label)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("DialogTitle")
        layout.addWidget(self.title_label)
        layout.addStretch(1)

        self.minimize_button = QToolButton(self)
        self.minimize_button.setObjectName("TaskDialogHeaderButton")
        self.minimize_button.setText("–")
        self.minimize_button.setToolTip("Свернуть")
        self.minimize_button.clicked.connect(dialog._minimize_from_header)
        layout.addWidget(self.minimize_button)

        self.close_button = QToolButton(self)
        self.close_button.setObjectName("TaskDialogCloseButton")
        self.close_button.setText("✕")
        self.close_button.setToolTip("Закрыть")
        self.close_button.clicked.connect(dialog.reject)
        layout.addWidget(self.close_button)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_minimize_visible(self, visible: bool) -> None:
        self.minimize_button.setVisible(visible)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._dragging:
            self._dialog.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._dragging = False
        super().mouseReleaseEvent(event)


class TaskEditDialog(QDialog):
    _SIZE_SETTING_KEY = "ui.task_edit_dialog_size"
    _DEFAULT_SIZE = QSize(680, 560)
    _LABEL_WIDTH = 138

    def __init__(self, task: TaskRow, parent=None):
        """Создает диалог редактирования задачи."""
        super().__init__(parent)
        self.setWindowTitle("Редактирование задачи")
        self.setObjectName("TaskEditDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("task_dialog_minimizable", True)
        self.setProperty("task_dialog_id", int(task.id))
        self.setProperty("task_dialog_kind", "edit")
        self.setProperty("dialog_category", "keep_size")
        self.setMinimumSize(640, 520)
        self._db = get_database()
        self._is_plan_item = self._resolve_plan_item_state(task.id)
        self._auto_minimize_pending = False
        self._validation_widgets: tuple[QWidget, ...] = ()
        debug_task_dialog(
            f"task_edit_dialog init task_id={self.property('task_dialog_id')} parent={type(parent).__name__ if parent is not None else 'None'}"
        )
        self.finished.connect(
            lambda result_code: debug_task_dialog(
                f"task_edit_dialog finished task_id={self.property('task_dialog_id')} "
                f"result={int(result_code)} state={self._debug_form_state()}"
            )
        )
        if not self._restore_saved_size():
            self.resize(self._DEFAULT_SIZE)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.header_bar = _TaskDialogHeader(self, "Задача")
        root_layout.addWidget(self.header_bar)

        content = QWidget(self)
        content.setObjectName("TaskDialogContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        root_layout.addWidget(content)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit(task.title)
        self.title_edit.setPlaceholderText("Введите название задачи")

        self.description_edit = QPlainTextEdit(task.description)
        self.description_edit.setPlaceholderText("Описание задачи...")
        self.description_edit.setFixedHeight(108)
        self._quote_filters = attach_task_quote_autoreplace(self.title_edit, self.description_edit)

        self.project_edit = QComboBox()
        self._populate_projects(task.project_id)
        self._project_autosuggest_enabled = False
        self._project_autosuggest_internal = False
        self._project_autosuggest_active = True
        self.project_edit.currentIndexChanged.connect(self._on_project_selection_changed)

        self.project_create_btn = QToolButton()
        self.project_create_btn.setText("+")
        self.project_create_btn.setFixedSize(38, 38)
        self.project_create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_create_btn.setToolTip("Создать проект")
        self.project_create_btn.clicked.connect(self._open_project_create_dialog)

        project_row = QWidget()
        project_row_layout = QHBoxLayout(project_row)
        project_row_layout.setContentsMargins(0, 0, 0, 0)
        project_row_layout.setSpacing(8)
        project_row_layout.addWidget(self.project_create_btn)
        project_row_layout.addWidget(self.project_edit, 1)
        self.plan_task_edit = QCheckBox("План")
        self.plan_task_edit.setChecked(bool(task.is_plan_task))
        project_row_layout.addWidget(self.plan_task_edit)

        self.day_edit = QDateEdit()
        self.day_edit.setCalendarPopup(True)
        self.day_edit.setDisplayFormat("yyyy-MM-dd")
        self.day_edit.setDate(QDate(task.day.year, task.day.month, task.day.day))
        self.day_edit.setKeyboardTracking(False)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(9, 0))
        self.time_edit.setKeyboardTracking(False)

        self.time_toggle = QCheckBox("")
        self.time_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.time_toggle.setToolTip("Указать точное время")
        self.time_toggle.setFixedWidth(28)

        if task.time_text:
            try:
                parsed = datetime.strptime(task.time_text, "%H:%M").time()
                self.time_edit.setTime(QTime(parsed.hour, parsed.minute))
                self.time_toggle.setChecked(True)
            except ValueError:
                self.time_toggle.setChecked(False)
        else:
            self.time_toggle.setChecked(False)

        self.time_edit.setEnabled(self.time_toggle.isChecked())
        self.time_toggle.toggled.connect(self.time_edit.setEnabled)

        time_block = QFrame()
        time_block.setObjectName("TaskDateTimeBlock")
        time_block_layout = QHBoxLayout(time_block)
        time_block_layout.setContentsMargins(0, 0, 0, 0)
        time_block_layout.setSpacing(8)
        time_block_layout.addWidget(self.day_edit)
        time_block_layout.addWidget(self.time_toggle)
        time_block_layout.addWidget(self.time_edit)

        self.recurrence_toggle = QCheckBox("По расписанию")
        self.recurrence_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recurrence_type_edit = QComboBox()
        self.recurrence_type_edit.addItem("Ежедневно", "daily")
        self.recurrence_type_edit.addItem("Еженедельно", "weekly")
        self.recurrence_type_edit.addItem("Ежемесячно", "monthly")
        recurrence_idx = self.recurrence_type_edit.findData(task.recurrence_kind)
        if recurrence_idx >= 0:
            self.recurrence_type_edit.setCurrentIndex(recurrence_idx)
        self.recurrence_toggle.setChecked(bool(task.recurrence_kind))
        self.recurrence_type_edit.setEnabled(self.recurrence_toggle.isChecked())
        self.recurrence_toggle.toggled.connect(self.recurrence_type_edit.setEnabled)

        recurrence_row = QWidget()
        recurrence_layout = QHBoxLayout(recurrence_row)
        recurrence_layout.setContentsMargins(0, 0, 0, 0)
        recurrence_layout.setSpacing(8)
        recurrence_layout.addWidget(self.recurrence_toggle)
        recurrence_layout.addWidget(self.recurrence_type_edit, 1)

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["High", "Medium", "Low", "Отложенная"])
        self.priority_edit.setCurrentText(task.priority or "Medium")

        self.marker_color_edit = QComboBox()
        self.marker_color_edit.addItem("Нет", "")
        self.marker_color_edit.addItem("Синий", "#2f6edb")
        self.marker_color_edit.addItem("Зеленый", "#2f9f63")
        self.marker_color_edit.addItem("Оранжевый", "#d68a2f")
        self.marker_color_edit.addItem("Красный", "#b74a4a")
        self.marker_color_edit.addItem("Фиолетовый", "#6b5ad4")
        marker_color_idx = self.marker_color_edit.findData((task.marker_color or "").strip())
        if marker_color_idx >= 0:
            self.marker_color_edit.setCurrentIndex(marker_color_idx)

        self.marker_theme_edit = QComboBox()
        self.marker_theme_edit.addItem("Нет", "")
        self.marker_theme_edit.addItem("Фильмы", "movies")
        self.marker_theme_edit.addItem("Игры", "games")
        self.marker_theme_edit.addItem("Книги", "books")
        self.marker_theme_edit.addItem("Музыка", "music")
        self.marker_theme_edit.addItem("Работа", "work")
        self.marker_theme_edit.addItem("Личное", "personal")
        self.marker_theme_edit.addItem("Разработка", "dev")
        marker_theme_idx = self.marker_theme_edit.findData((task.marker_theme or "").strip().lower())
        if marker_theme_idx >= 0:
            self.marker_theme_edit.setCurrentIndex(marker_theme_idx)

        self.done_edit = QCheckBox("Выполнено")
        self.done_edit.setChecked(task.done)

        params_row = QWidget()
        params_layout = QHBoxLayout(params_row)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.setSpacing(8)
        params_layout.addWidget(self.priority_edit, 1)
        params_layout.addWidget(self.marker_color_edit, 1)
        params_layout.addWidget(self.marker_theme_edit, 1)

        form.addRow(self._make_form_label("Название"), self.title_edit)
        form.addRow(self._make_form_label("Описание"), self.description_edit)
        form.addRow(self._make_form_label("Проект"), project_row)
        form.addRow(self._make_form_label("Дата и время"), time_block)
        form.addRow(self._make_form_label("Повтор"), recurrence_row)
        form.addRow(self._make_form_label("Параметры"), params_row)
        form.addRow(self._make_form_label(""), self.done_edit)

        layout.addLayout(form)

        self._task_id = task.id
        self._attachments: List = []
        self._tasks_by_id = {}
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._maps_by_id = {}
        self._markers_by_id = {}
        self._cloud_files_by_id = {}

        attachments_frame = QFrame()
        attachments_frame.setObjectName("TaskAttachments")
        attachments_layout = QVBoxLayout(attachments_frame)
        attachments_layout.setContentsMargins(12, 10, 12, 10)
        attachments_layout.setSpacing(8)

        attachments_header = QHBoxLayout()
        attachments_title = QLabel("Связи")
        attachments_title.setObjectName("TaskAttachmentsTitle")
        self.attachments_add_btn = QToolButton()
        self.attachments_add_btn.setText("+ Добавить")
        self.attachments_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attachments_add_btn.clicked.connect(self._open_attachment_dialog)
        attachments_header.addWidget(attachments_title)
        attachments_header.addStretch(1)
        attachments_header.addWidget(self.attachments_add_btn)
        attachments_layout.addLayout(attachments_header)

        attachments_scroll = QScrollArea(attachments_frame)
        attachments_scroll.setObjectName("TaskAttachmentsScroll")
        attachments_scroll.setWidgetResizable(True)
        attachments_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        attachments_scroll.setFrameShape(QFrame.Shape.NoFrame)
        attachments_scroll.setMinimumHeight(150)

        attachments_host = QWidget(attachments_scroll)
        attachments_host.setObjectName("TaskAttachmentsHost")
        self.attachments_list = QVBoxLayout(attachments_host)
        self.attachments_list.setContentsMargins(0, 0, 0, 0)
        self.attachments_list.setSpacing(6)
        self.attachments_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        attachments_scroll.setWidget(attachments_host)
        attachments_layout.addWidget(attachments_scroll)
        layout.addWidget(attachments_frame)

        self._load_attachment_sources()
        self._refresh_attachments()

        buttons = QDialogButtonBox(self)
        save_button = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        cancel_button = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText("Сохранить")
            save_button.setObjectName("PrimaryAction")
            save_button.setDefault(False)
            save_button.setAutoDefault(False)
        if cancel_button is not None:
            cancel_button.setText("Отмена")
            cancel_button.setObjectName("SecondaryAction")
            cancel_button.setAutoDefault(False)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 4, 0, 0)
        footer.addStretch(1)
        footer.addWidget(buttons)
        layout.addLayout(footer)

        self._validation_widgets = (self.title_edit, self.time_edit, self.priority_edit)
        self._setup_shortcuts()
        self._setup_error_reset_handlers()
        self._apply_plan_child_restrictions()
        self.header_bar.set_minimize_visible(bool(self.property("task_dialog_minimizable")))
        palette = get_theme_palette("dark")

        self.setStyleSheet(f"""
            QDialog#TaskEditDialog {{
                {MATH_PHYS_BACKGROUND}
                border: 1px solid #25272c;
                border-radius: 12px;
            }}

            QDialog#TaskEditDialog QLabel {{
                color: {palette.text};
            }}

            QDialog#TaskEditDialog QFrame#TaskDialogHeader {{
                {TITLEBAR_BACKGROUND}
                border-bottom: 1px solid {palette.border};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}

            QDialog#TaskEditDialog QLabel#TaskDialogHeaderMarker {{
                color: {palette.accent};
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#TaskEditDialog QLabel#DialogTitle {{
                color: #eef1ff;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#TaskEditDialog QWidget#TaskDialogContent {{
                background: transparent;
            }}

            QDialog#TaskEditDialog QLabel#TaskFormLabel {{
                color: {palette.text};
                font-size: 13px;
            }}

            QDialog#TaskEditDialog QLineEdit,
            QDialog#TaskEditDialog QPlainTextEdit,
            QDialog#TaskEditDialog QComboBox,
            QDialog#TaskEditDialog QDateEdit,
            QDialog#TaskEditDialog QTimeEdit {{
                background: {palette.input_bg};
                color: #e6e6e6;
                border: 1px solid {palette.border};
                padding: 8px 10px;
                border-radius: 8px;
                min-height: 36px;
            }}

            QDialog#TaskEditDialog QPlainTextEdit {{
                padding: 8px 10px;
            }}

            QDialog#TaskEditDialog QLineEdit:focus,
            QDialog#TaskEditDialog QPlainTextEdit:focus,
            QDialog#TaskEditDialog QComboBox:focus,
            QDialog#TaskEditDialog QDateEdit:focus,
            QDialog#TaskEditDialog QTimeEdit:focus {{
                border: 1px solid {palette.accent};
            }}

            QDialog#TaskEditDialog QLineEdit:disabled,
            QDialog#TaskEditDialog QPlainTextEdit:disabled,
            QDialog#TaskEditDialog QComboBox:disabled,
            QDialog#TaskEditDialog QDateEdit:disabled,
            QDialog#TaskEditDialog QTimeEdit:disabled,
            QDialog#TaskEditDialog QToolButton:disabled,
            QDialog#TaskEditDialog QCheckBox:disabled {{
                color: {palette.dim_text};
                background: {palette.input_alt_bg};
                border-color: {palette.border};
            }}

            QDialog#TaskEditDialog QLineEdit[error="true"],
            QDialog#TaskEditDialog QComboBox[error="true"],
            QDialog#TaskEditDialog QTimeEdit[error="true"] {{
                border: 1px solid {palette.danger};
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock {{
                background: transparent;
                border: none;
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QDateEdit,
            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QTimeEdit {{
                min-height: 36px;
            }}

            QDialog#TaskEditDialog QFrame#TaskDateTimeBlock QCheckBox {{
                color: {palette.dim_text};
                padding: 0;
            }}

            QDialog#TaskEditDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                selection-background-color: {palette.selection_bg};
                selection-color: {palette.selection_text};
                outline: none;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView::item {{
                padding: 6px 10px;
            }}

            QDialog#TaskEditDialog QComboBox QAbstractItemView::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}

            QDialog#TaskEditDialog QCheckBox {{
                color: {palette.text};
                padding: 4px 0;
            }}

            QDialog#TaskEditDialog QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {palette.border_strong};
                border-radius: 5px;
                background: {palette.panel_bg};
            }}

            QDialog#TaskEditDialog QCheckBox::indicator:checked {{
                background: {palette.accent};
                border-color: {palette.accent};
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton {{
                padding: 10px 18px;
                border-radius: 8px;
                min-width: 120px;
                border: 1px solid {palette.border_strong};
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton:hover {{
                border-color: {palette.accent};
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton#PrimaryAction {{
                background: #3b4a7a;
                color: #f5f7ff;
                border-color: #4b5c90;
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton#PrimaryAction:hover {{
                background: #475a91;
                border-color: #5b6ea5;
            }}

            QDialog#TaskEditDialog QDialogButtonBox QPushButton#SecondaryAction {{
                background: #2a2b2f;
                color: #e6e6e6;
            }}

            QDialog#TaskEditDialog QToolButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 12px;
                border-radius: 8px;
            }}

            QDialog#TaskEditDialog QToolButton:hover {{
                background: #34363b;
                border-color: {palette.border_strong};
            }}

            QDialog#TaskEditDialog QToolButton#TaskDialogHeaderButton,
            QDialog#TaskEditDialog QToolButton#TaskDialogCloseButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                min-width: 28px;
                min-height: 26px;
                padding: 0;
                font-size: 15px;
            }}

            QDialog#TaskEditDialog QToolButton#TaskDialogHeaderButton:hover {{
                background: #2a2b2f;
            }}

            QDialog#TaskEditDialog QToolButton#TaskDialogCloseButton:hover {{
                background: #b23b3b;
                color: #ffffff;
            }}

            QDialog#TaskEditDialog QFrame#TaskAttachments {{
                background: #1c1d22;
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}

            QDialog#TaskEditDialog QLabel#TaskAttachmentsTitle {{
                color: #f2f2f2;
                font-weight: 600;
            }}

            QDialog#TaskEditDialog QScrollArea#TaskAttachmentsScroll,
            QDialog#TaskEditDialog QWidget#TaskAttachmentsHost {{
                background: transparent;
            }}

            QDialog#TaskEditDialog QFrame#TaskAttachmentRow {{
                background: {palette.input_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}

            QDialog#TaskEditDialog QLabel#TaskAttachmentKind {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border_strong};
                border-radius: 6px;
                padding: 4px 8px;
            }}

            QDialog#TaskEditDialog QLabel#TaskAttachmentLink {{
                color: #6ab7ff;
            }}

            QDialog#TaskEditDialog QToolButton#TaskAttachmentRemove {{
                background: transparent;
                border: none;
                padding: 4px;
            }}
        """)

    @classmethod
    def _make_form_label(cls, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("TaskFormLabel")
        label.setFixedWidth(cls._LABEL_WIDTH)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_accept)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self._on_accept)
        QShortcut(QKeySequence("Esc"), self, self.reject)

    def _setup_error_reset_handlers(self) -> None:
        self.title_edit.textChanged.connect(lambda *_: self._apply_error_state(self.title_edit, False))
        self.time_edit.timeChanged.connect(lambda *_: self._apply_error_state(self.time_edit, False))
        self.time_toggle.toggled.connect(lambda *_: self._apply_error_state(self.time_edit, False))
        self.priority_edit.currentIndexChanged.connect(lambda *_: self._apply_error_state(self.priority_edit, False))

    def _apply_plan_child_restrictions(self) -> None:
        if not self._is_plan_item:
            return
        inherit_tip = "Наследуется от родительского плана"
        self.plan_task_edit.setChecked(False)
        self.plan_task_edit.setEnabled(False)
        self.plan_task_edit.setToolTip(inherit_tip)
        self.project_edit.setEnabled(False)
        self.project_edit.setToolTip(inherit_tip)
        self.project_create_btn.setEnabled(False)
        self.project_create_btn.setToolTip(inherit_tip)
        self.priority_edit.setEnabled(False)
        self.priority_edit.setToolTip(inherit_tip)

    def _apply_error_state(self, widget: QWidget, enabled: bool, message: str = "") -> None:
        base_tooltip = widget.property("base_tooltip")
        if base_tooltip is None:
            base_tooltip = widget.toolTip()
            widget.setProperty("base_tooltip", base_tooltip)
        widget.setProperty("error", enabled)
        widget.setToolTip(message if enabled and message else str(base_tooltip or ""))
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _clear_validation_errors(self) -> None:
        for widget in self._validation_widgets:
            self._apply_error_state(widget, False)

    def _minimize_from_header(self) -> None:
        if bool(self.property("task_dialog_minimizable")):
            window = self.parentWidget().window() if self.parentWidget() is not None else QApplication.activeWindow()
            minimize_fn = getattr(window, "minimize_task_dialog", None)
            if callable(minimize_fn):
                minimize_fn(
                    dialog=self,
                    task_id=int(self.property("task_dialog_id") or 0),
                    is_edit_dialog=(str(self.property("task_dialog_kind") or "").strip().lower() == "edit"),
                )
                return
        self.showMinimized()

    def _restore_saved_size(self) -> bool:
        raw = self._db.get_setting(self._SIZE_SETTING_KEY, default="").strip()
        if not raw:
            return False
        width_str, separator, height_str = raw.partition("x")
        if not separator:
            return False
        try:
            width = int(width_str)
            height = int(height_str)
        except ValueError:
            return False
        self.resize(max(width, self.minimumWidth()), max(height, self.minimumHeight()))
        return True

    def _save_current_size(self) -> None:
        size = self.size()
        self._db.set_setting(self._SIZE_SETTING_KEY, f"{size.width()}x{size.height()}")

    def closeEvent(self, event) -> None:
        debug_task_dialog(
            f"task_edit_dialog close task_id={self.property('task_dialog_id')} state={self._debug_form_state()}"
        )
        self._save_current_size()
        super().closeEvent(event)

    def exec(self) -> int:  # noqa: A003 - Qt API name
        return show_minimizable_task_dialog(self, self.parentWidget())

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        prepare_minimizable_task_dialog_for_show(self, self.parentWidget(), center=True)
        ensure_minimizable_task_dialog_overlay(self)
        self.raise_()
        self.activateWindow()
        debug_task_dialog(
            f"task_edit_dialog show task_id={self.property('task_dialog_id')} geometry={self.geometry().getRect()}"
        )

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow():
            self._schedule_auto_minimize_on_deactivate()
        super().changeEvent(event)

    def _schedule_auto_minimize_on_deactivate(self) -> None:
        if self._auto_minimize_pending:
            return
        self._auto_minimize_pending = True
        debug_task_dialog(f"task_edit_dialog schedule_deactivate task_id={self.property('task_dialog_id')}")
        QTimer.singleShot(0, self._maybe_auto_minimize_on_deactivate)

    def _maybe_auto_minimize_on_deactivate(self) -> None:
        self._auto_minimize_pending = False
        if not self.isVisible():
            debug_task_dialog(f"task_edit_dialog deactivate skipped invisible task_id={self.property('task_dialog_id')}")
            return
        if QApplication.activePopupWidget() is not None and self._is_own_widget(QApplication.activePopupWidget()):
            return
        if QApplication.activeModalWidget() is not None and self._is_own_widget(QApplication.activeModalWidget()):
            return
        active_window = QApplication.activeWindow()
        if isinstance(active_window, QWidget) and self._is_own_widget(active_window):
            return
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, QWidget) and self._is_own_widget(focus_widget):
            return
        window = self.parentWidget().window() if self.parentWidget() is not None else QApplication.activeWindow()
        minimize_fn = getattr(window, "minimize_task_dialog", None)
        if not callable(minimize_fn):
            debug_task_dialog(
                f"task_edit_dialog deactivate missing minimize_fn task_id={self.property('task_dialog_id')} "
                f"window={type(window).__name__ if window is not None else 'None'}"
            )
            return
        debug_task_dialog(
            f"task_edit_dialog deactivate minimize task_id={self.property('task_dialog_id')} "
            f"window={type(window).__name__ if window is not None else 'None'}"
        )
        minimize_fn(dialog=self, task_id=int(self.property("task_dialog_id") or 0), is_edit_dialog=True)

    def _is_own_widget(self, widget: QWidget) -> bool:
        current: QWidget | None = widget
        while current is not None:
            if current is self:
                return True
            current = current.parentWidget()
        return False

    def _populate_projects(self, selected_id: Optional[int] = None) -> None:
        self.project_edit.blockSignals(True)
        self.project_edit.clear()
        self.project_edit.addItem("Без проекта", None)
        projects = get_database().fetch_projects()
        projects_by_id = {project.id: project for project in projects}
        title_cache: Dict[int, str] = {}

        def full_title(project_id: int, seen: Optional[set[int]] = None) -> str:
            cached = title_cache.get(project_id)
            if cached is not None:
                return cached
            project = projects_by_id.get(project_id)
            if project is None:
                return ""
            seen_set = seen or set()
            if project_id in seen_set:
                title_cache[project_id] = project.title
                return project.title
            if project.parent_project_id is None:
                title_cache[project_id] = project.title
                return project.title
            parent_title = full_title(project.parent_project_id, seen_set | {project_id})
            resolved = f"{parent_title} / {project.title}" if parent_title else project.title
            title_cache[project_id] = resolved
            return resolved
        priority_order = {"High": 0, "Medium": 1, "Low": 2, "Отложенная": 3}
        projects.sort(
            key=lambda project: (
                project.area.lower(),
                priority_order.get(normalize_priority(project.priority), 4),
                full_title(project.id).lower(),
                project.id,
            )
        )
        for project in projects:
            if project.archived:
                continue
            title = full_title(project.id)
            self.project_edit.addItem(f"{project.area} · {title}", project.id)
        if selected_id is not None:
            idx = self.project_edit.findData(selected_id)
            if idx >= 0:
                self.project_edit.setCurrentIndex(idx)
        self.project_edit.blockSignals(False)

    def _on_project_selection_changed(self, _index: int) -> None:
        if self._project_autosuggest_internal:
            return
        if not self._project_autosuggest_enabled:
            return
        current_project_id = self.project_edit.currentData()
        self._project_autosuggest_active = current_project_id is None

    def _best_project_index_for_title(self, title: str) -> Optional[int]:
        title_tokens = set(_tokenize_text_for_match(title))
        if not title_tokens:
            return None

        best_index: Optional[int] = None
        best_score = 0
        best_length = 10**9
        for combo_index in range(1, self.project_edit.count()):
            project_id = self.project_edit.itemData(combo_index)
            if project_id is None:
                continue
            project_text = self.project_edit.itemText(combo_index)
            project_tokens = set(_tokenize_text_for_match(project_text))
            if not project_tokens:
                continue
            overlap = title_tokens & project_tokens
            if not overlap:
                continue
            overlap_weight = sum(len(token) for token in overlap)
            score = overlap_weight + len(overlap) * 3
            text_length = len(project_text)
            if score > best_score or (score == best_score and text_length < best_length):
                best_score = score
                best_index = combo_index
                best_length = text_length
        return best_index

    def _apply_project_suggestion(self, title: str) -> None:
        if not self._project_autosuggest_enabled or not self._project_autosuggest_active:
            return
        suggested_index = self._best_project_index_for_title(title)
        target_index = suggested_index if suggested_index is not None else 0
        if target_index == self.project_edit.currentIndex():
            return
        self._project_autosuggest_internal = True
        try:
            self.project_edit.setCurrentIndex(target_index)
        finally:
            self._project_autosuggest_internal = False

    def _enable_title_project_suggestion(self) -> None:
        self._project_autosuggest_enabled = True
        self._project_autosuggest_active = self.project_edit.currentData() is None
        self.title_edit.textChanged.connect(self._apply_project_suggestion)

    def _open_project_create_dialog(self) -> None:
        dialog = QuickProjectCreateDialog(parent=self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            created = get_database().create_project(
                area=values["area"],
                title=values["title"],
                updated=values["updated"],
                priority=values["priority"],
                archived=False,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self._populate_projects(created.id)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        self._clear_validation_errors()
        normalized_title = normalize_task_text_quotes(self.title_edit.text())
        if normalized_title != self.title_edit.text():
            self.title_edit.setText(normalized_title)
        normalized_description = normalize_task_text_quotes(self.description_edit.toPlainText())
        if normalized_description != self.description_edit.toPlainText():
            self.description_edit.setPlainText(normalized_description)
        title = self.title_edit.text().strip()
        debug_task_dialog(
            f"task_edit_dialog accept_start task_id={self.property('task_dialog_id')} state={self._debug_form_state()}"
        )
        if not title:
            debug_task_dialog(
                f"task_edit_dialog accept_blocked_empty_title task_id={self.property('task_dialog_id')}"
            )
            self._apply_error_state(self.title_edit, True, "Введите название задачи.")
            self.title_edit.setFocus()
            return
        time_text = self._current_time_text()
        try:
            validate_time_text(time_text)
        except ValueError as exc:
            debug_task_dialog(
                f"task_edit_dialog accept_blocked_validation task_id={self.property('task_dialog_id')} error={exc}"
            )
            self._apply_error_state(self.time_edit, True, str(exc))
            self.time_edit.setFocus()
            return
        try:
            normalize_priority(self.priority_edit.currentText())
        except ValueError as exc:
            debug_task_dialog(
                f"task_edit_dialog accept_blocked_validation task_id={self.property('task_dialog_id')} error={exc}"
            )
            self._apply_error_state(self.priority_edit, True, str(exc))
            self.priority_edit.setFocus()
            return
        debug_task_dialog(
            f"task_edit_dialog accept_commit task_id={self.property('task_dialog_id')} state={self._debug_form_state()}"
        )
        self.accept()

    def _current_time_text(self) -> str:
        if not self.time_toggle.isChecked():
            return ""
        return self.time_edit.time().toString("HH:mm")

    def _safe_db_fetch(self, method_name: str, *args, **kwargs) -> List:
        fetch_method = getattr(self._db, method_name, None)
        if not callable(fetch_method):
            return []
        result = fetch_method(*args, **kwargs)
        return list(result or [])

    def _load_attachment_sources(self) -> None:
        tasks = self._safe_db_fetch("fetch_tasks")
        notes = self._safe_db_fetch("fetch_notes")
        ideas_active = self._safe_db_fetch("fetch_ideas", archived=False)
        active_ids = {idea.id for idea in ideas_active}
        ideas_archived = [idea for idea in self._safe_db_fetch("fetch_ideas", archived=True) if idea.id not in active_ids]
        ideas = ideas_active + ideas_archived
        objects = self._safe_db_fetch("fetch_objects")
        maps = self._safe_db_fetch("fetch_maps")
        markers = self._safe_db_fetch("fetch_map_markers")
        cloud_files = self._safe_db_fetch("fetch_cloud_files")
        self._tasks_by_id = {task.id: task for task in tasks}
        self._notes_by_id = {note.id: note for note in notes}
        self._ideas_by_id = {idea.id: idea for idea in ideas}
        self._objects_by_id = {item.id: item for item in objects}
        self._maps_by_id = {item.id: item for item in maps}
        self._markers_by_id = {item.id: item for item in markers}
        self._cloud_files_by_id = {item.id: item for item in cloud_files}

    def _refresh_attachments(self) -> None:
        self._load_attachment_sources()
        self._attachments = self._db.fetch_task_attachments(self._task_id)
        self._clear_layout(self.attachments_list)
        if not self._attachments:
            empty = QLabel("Нет связанных элементов")
            empty.setStyleSheet("color: #8a8a8a;")
            self.attachments_list.addWidget(empty)
            return
        for attachment in self._attachments:
            row = QFrame()
            row.setObjectName("TaskAttachmentRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)

            kind_label = QLabel(self._attachment_kind_label(attachment.kind))
            kind_label.setObjectName("TaskAttachmentKind")
            link_text = self._attachment_display_text(attachment)
            link_label = QLabel(f"<a style='color:#6ecbe0;' href='{attachment.id}'>{link_text}</a>")
            link_label.setObjectName("TaskAttachmentLink")
            link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            link_label.setOpenExternalLinks(False)
            link_label.linkActivated.connect(lambda _link, att=attachment: self._open_attachment(att))

            remove_btn = QToolButton()
            remove_btn.setObjectName("TaskAttachmentRemove")
            remove_btn.setIcon(qta.icon("fa5s.times", color="#cfcfcf"))
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(lambda _checked=False, att=attachment: self._remove_attachment(att))

            row_layout.addWidget(kind_label)
            row_layout.addWidget(link_label, 1)
            row_layout.addWidget(remove_btn)
            self.attachments_list.addWidget(row)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    @staticmethod
    def _attachment_kind_label(kind: str) -> str:
        return attachment_kind_label(kind)

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
                return f"{task.title} · {task.project_title}"
            return task.title
        if attachment.kind == "note":
            note = self._notes_by_id.get(attachment.ref_id)
            return note.title if note else "Заметка не найдена"
        if attachment.kind == "idea":
            idea = self._ideas_by_id.get(attachment.ref_id)
            if not idea:
                return "Идея не найдена"
            if idea.project_title:
                return f"{idea.title} · {idea.project_title}"
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
                return f"{marker.name} · {map_title}"
            return marker.name
        if attachment.kind in {"file", "image"}:
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            return self._cloud_file_link_text(file_item) if file_item else "Файл не найден"
        return "Вложение"

    def _open_attachment_dialog(self) -> None:
        self._load_attachment_sources()
        dialog, kind_combo, item_combo = self._create_attachment_dialog()

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        kind = kind_combo.currentData()
        ref_id = item_combo.currentData()
        if ref_id is None:
            QMessageBox.warning(self, "Связи", "Нет доступных элементов для добавления.")
            return
        self._db.add_task_attachment(self._task_id, kind, ref_id)
        self._refresh_attachments()

    def _create_attachment_dialog(self) -> tuple[QDialog, QComboBox, FilterableComboBox]:
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить связь")
        dialog.setObjectName("TaskAttachmentDialog")
        dialog.setFixedSize(550, 200)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        kind_combo = QComboBox()
        kind_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        kind_items = [
            ("Задача", "task"),
            ("Заметка", "note"),
            ("Идея", "idea"),
            ("Объект", "object"),
            ("Карта", "map"),
            ("Метка карты", "marker"),
            ("Файл", "file"),
            ("Изображение", "image"),
        ]
        for label, key in kind_items:
            kind_combo.addItem(label, key)

        item_combo = FilterableComboBox(dialog)
        item_combo.setMinimumContentsLength(24)
        item_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        item_view = item_combo.view()
        if item_view is not None:
            item_view.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        file_picker_open = {"active": False}

        def fill_items(selected_kind: str) -> None:
            item_combo.clear()
            if selected_kind == "task":
                tasks = [task for task in self._tasks_by_id.values() if task.id != self._task_id]
                for task_row in sorted(tasks, key=lambda task: (task.title.lower(), task.id)):
                    row_label = f"{task_row.title} · {task_row.project_title}" if task_row.project_title else task_row.title
                    item_combo.addItem(row_label, task_row.id)
            elif selected_kind == "note":
                for note_row in sorted(self._notes_by_id.values(), key=lambda note: note.title.lower()):
                    row_label = f"{note_row.title} · {note_row.project}" if note_row.project else note_row.title
                    item_combo.addItem(row_label, note_row.id)
            elif selected_kind == "idea":
                for idea_row in sorted(self._ideas_by_id.values(), key=lambda idea: idea.title.lower()):
                    row_label = (
                        f"{idea_row.title} · {idea_row.project_title}" if idea_row.project_title else idea_row.title
                    )
                    item_combo.addItem(row_label, idea_row.id)
            elif selected_kind == "object":
                for object_row in sorted(self._objects_by_id.values(), key=lambda obj: obj.title.lower()):
                    row_label = f"{object_row.title} · {object_row.catalog}" if object_row.catalog else object_row.title
                    item_combo.addItem(row_label, object_row.id)
            elif selected_kind == "map":
                for map_row in sorted(self._maps_by_id.values(), key=lambda map_item: map_item.title.lower()):
                    row_label = f"{map_row.title} · {map_row.project}" if map_row.project else map_row.title
                    item_combo.addItem(row_label, map_row.id)
            elif selected_kind == "marker":
                markers = sorted(self._markers_by_id.values(), key=lambda marker_row: marker_row.name.lower())
                for marker in markers:
                    map_title = self._maps_by_id.get(marker.map_id).title if marker.map_id in self._maps_by_id else ""
                    marker_label = f"{marker.name} · {map_title}" if map_title else marker.name
                    item_combo.addItem(marker_label, marker.id)
            elif selected_kind in {"file", "image"}:
                files = [
                    file_row
                    for file_row in self._cloud_files_by_id.values()
                    if file_row.is_image == (selected_kind == "image")
                ]
                files = sorted(files, key=lambda file_row: file_row.name.lower())
                for file_row in files:
                    item_combo.addItem(self._cloud_file_link_text(file_row), file_row.id)
            if item_combo.count() == 0:
                item_combo.addItem("— нет доступных —", None)
            item_combo.clear_filter()
            item_combo.setCurrentIndex(0 if item_combo.count() else -1)

        def select_file_from_picker() -> None:
            if file_picker_open["active"]:
                return
            file_picker_open["active"] = True
            try:
                selected_file_id = self._pick_task_attachment_file()
            finally:
                file_picker_open["active"] = False
            if selected_file_id is None:
                return
            selected_index = item_combo.findData(selected_file_id)
            if selected_index >= 0:
                item_combo.setCurrentIndex(selected_index)

        def on_kind_changed(_idx: int) -> None:
            selected_kind = kind_combo.currentData()
            fill_items(selected_kind)
            if selected_kind == "file":
                QTimer.singleShot(0, select_file_from_picker)

        kind_combo.currentIndexChanged.connect(on_kind_changed)
        fill_items(kind_combo.currentData())

        form.addRow("Тип", kind_combo)
        form.addRow("Элемент", item_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setStyleSheet(f"""
            QDialog#TaskAttachmentDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#TaskAttachmentDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#TaskAttachmentDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 4px 8px;
                border-radius: 6px;
                min-height: 28px;
            }}
            QDialog#TaskAttachmentDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 4px 10px;
                min-height: 28px;
                border-radius: 6px;
            }}
        """)
        return dialog, kind_combo, item_combo

    def _pick_task_attachment_file(self) -> Optional[int]:
        dialog = AttachFileSelectNav(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        rel_path = dialog.selected_rel_path()
        if not rel_path:
            return None
        normalized = rel_path.strip().strip("/")
        matched = next(
            (
                file_item.id
                for file_item in self._cloud_files_by_id.values()
                if (file_item.rel_path or "").strip().strip("/") == normalized and not file_item.is_image
            ),
            None,
        )
        if matched is None:
            QMessageBox.warning(self, "Связи", "Файл не найден в базе.")
            return None
        return matched

    def _remove_attachment(self, attachment) -> None:
        self._db.delete_task_attachment(attachment.id)
        self._refresh_attachments()

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

    def _open_linked_task(self, task_id: int) -> bool:
        task = self._tasks_by_id.get(task_id)
        if task is None:
            tasks = self._safe_db_fetch("fetch_tasks")
            self._tasks_by_id = {item.id: item for item in tasks}
            task = self._tasks_by_id.get(task_id)
        if task is None:
            QMessageBox.warning(self, "Связанные задачи", f"Задача MN-{task_id} не найдена.")
            return False
        from .task_details_dialog import TaskDetailsDialog

        dialog = TaskDetailsDialog(task, parent=self)
        show_dialog_standard(dialog, self)
        return True

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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setStyleSheet(f"""
            QDialog#TaskAttachmentInfoDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#TaskAttachmentInfoDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#TaskAttachmentInfoDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)
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

    def _resolve_plan_item_state(self, task_id: int) -> bool:
        fetch_tasks = getattr(self._db, "fetch_tasks", None)
        if not callable(fetch_tasks):
            return False
        by_id = {task.id: task for task in fetch_tasks()}
        current = by_id.get(task_id)
        if current is None or current.parent_id is None:
            return False
        parent_task = by_id.get(current.parent_id)
        return bool(parent_task is not None and parent_task.is_plan_task)

    def values(self):
        """Возвращает текущие значения формы в виде словаря."""
        qd = self.day_edit.date()
        day = date(qd.year(), qd.month(), qd.day())
        time_text = self._current_time_text()
        payload = {
            "title": normalize_task_text_quotes(self.title_edit.text()).strip(),
            "description": normalize_task_text_quotes(self.description_edit.toPlainText()).strip(),
            "day": day,
            "time_text": time_text,
            "priority": self.priority_edit.currentText().strip() or "Medium",
            "done": self.done_edit.isChecked(),
            "project_id": self.project_edit.currentData(),
            "recurrence_kind": self.recurrence_type_edit.currentData() if self.recurrence_toggle.isChecked() else "",
            "recurrence_interval": 1,
            "is_plan_task": self.plan_task_edit.isChecked(),
            "marker_color": self.marker_color_edit.currentData() or "",
            "marker_theme": self.marker_theme_edit.currentData() or "",
        }
        debug_task_dialog(
            f"task_edit_dialog values task_id={self.property('task_dialog_id')} "
            f"title={payload['title']!r} day={payload['day'].isoformat()} time={payload['time_text']!r} "
            f"priority={payload['priority']!r} done={payload['done']} project_id={payload['project_id']} "
            f"recurrence={payload['recurrence_kind']!r} is_plan_task={payload['is_plan_task']} marker_color={payload['marker_color']!r} "
            f"marker_theme={payload['marker_theme']!r} description_len={len(payload['description'])}"
        )
        return payload

    def _debug_form_state(self) -> str:
        title = self.title_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        qd = self.day_edit.date()
        day = date(qd.year(), qd.month(), qd.day()).isoformat()
        return (
            f"title={title!r} day={day} time={self._current_time_text()!r} "
            f"priority={self.priority_edit.currentText()!r} done={self.done_edit.isChecked()} "
            f"project_id={self.project_edit.currentData()} is_plan_task={self.plan_task_edit.isChecked()} "
            f"recurrence_enabled={self.recurrence_toggle.isChecked()} "
            f"recurrence={self.recurrence_type_edit.currentData()!r} marker_color={self.marker_color_edit.currentData()!r} "
            f"marker_theme={self.marker_theme_edit.currentData()!r} description_len={len(description)}"
        )

__all__ = ["TaskEditDialog"]
