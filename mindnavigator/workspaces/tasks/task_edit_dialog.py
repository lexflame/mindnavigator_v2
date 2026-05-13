"""TaskEditDialog class module for tasks workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from PySide6.QtCore import QEvent, QTimer
from mindnavigator.ui.dialogs.frameless_patch import (
    ensure_minimizable_task_dialog_overlay,
    prepare_minimizable_task_dialog_for_show,
    show_minimizable_task_dialog,
)
from mindnavigator.ui.dialogs.task_dialog_debug import debug_task_dialog
from .quick_project_create_dialog import QuickProjectCreateDialog
from .task_image_preview_dialog import TaskImagePreviewDialog

class TaskEditDialog(QDialog):
    _SIZE_SETTING_KEY = "ui.task_edit_dialog_size"

    def __init__(self, task: TaskRow, parent=None):
        """Создает диалог редактирования задачи."""
        super().__init__(parent)
        self.setWindowTitle("Редактирование задачи")
        self.setObjectName("TaskEditDialog")
        self.setProperty("task_dialog_minimizable", True)
        self.setProperty("task_dialog_id", int(task.id))
        self.setProperty("task_dialog_kind", "edit")
        self.setProperty("dialog_category", "keep_size")
        self.setMinimumWidth(460)
        self.setMinimumHeight(420)
        self._db = get_database()
        self._is_plan_item = self._resolve_plan_item_state(task.id)
        self._auto_minimize_pending = False
        debug_task_dialog(
            f"task_edit_dialog init task_id={self.property('task_dialog_id')} parent={type(parent).__name__ if parent is not None else 'None'}"
        )
        self.finished.connect(
            lambda result_code: debug_task_dialog(
                f"task_edit_dialog finished task_id={self.property('task_dialog_id')} "
                f"result={int(result_code)} state={self._debug_form_state()}"
            )
        )
        self._restore_saved_size()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Редактирование задачи")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit(task.title)
        self.title_edit.setPlaceholderText("Название задачи")

        self.description_edit = QPlainTextEdit(task.description)
        self.description_edit.setPlaceholderText("Описание задачи")
        self.description_edit.setMinimumHeight(90)
        self._quote_filters = attach_task_quote_autoreplace(self.title_edit, self.description_edit)

        self.project_edit = QComboBox()
        self._populate_projects(task.project_id)
        self._project_autosuggest_enabled = False
        self._project_autosuggest_internal = False
        self._project_autosuggest_active = True
        self.project_edit.currentIndexChanged.connect(self._on_project_selection_changed)

        self.project_create_btn = QToolButton()
        self.project_create_btn.setText("+")
        self.project_create_btn.setFixedSize(24, 24)
        self.project_create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_create_btn.setToolTip("Создать проект")
        self.project_create_btn.clicked.connect(self._open_project_create_dialog)

        project_row = QWidget()
        project_row_layout = QHBoxLayout(project_row)
        project_row_layout.setContentsMargins(0, 0, 0, 0)
        project_row_layout.setSpacing(6)
        project_row_layout.addWidget(self.project_create_btn)
        project_row_layout.addWidget(self.project_edit, 1)
        self.plan_task_edit = QCheckBox("Задача план")
        self.plan_task_edit.setChecked(bool(task.is_plan_task))
        if self._is_plan_item:
            self.plan_task_edit.setChecked(False)
            self.plan_task_edit.setEnabled(False)
            self.plan_task_edit.setToolTip("Свойство задается только для корневой задачи-плана.")
            self.project_edit.setEnabled(False)
            self.project_edit.setToolTip("Проект наследуется от родительской задачи-плана.")
            self.project_create_btn.setEnabled(False)
            self.project_create_btn.setToolTip("Для пунктов плана проект наследуется от родителя.")
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

        self.time_toggle = QCheckBox("Указать")
        self.time_toggle.setCursor(Qt.CursorShape.PointingHandCursor)

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
        time_block_layout.setContentsMargins(8, 4, 8, 4)
        time_block_layout.setSpacing(6)
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
        recurrence_layout.setSpacing(6)
        recurrence_layout.addWidget(self.recurrence_toggle)
        recurrence_layout.addWidget(self.recurrence_type_edit, 1)

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["High", "Medium", "Low", "Отложенная"])
        self.priority_edit.setCurrentText(task.priority or "Medium")
        if self._is_plan_item:
            self.priority_edit.setEnabled(False)
            self.priority_edit.setToolTip("Пункты плана не используют приоритет.")

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

        form.addRow("Название", self.title_edit)
        form.addRow("Описание", self.description_edit)
        form.addRow("Проект", project_row)
        form.addRow("Дата и время", time_block)
        form.addRow("Повтор", recurrence_row)
        form.addRow("Приоритет", self.priority_edit)
        form.addRow("Маркер (цвет)", self.marker_color_edit)
        form.addRow("Тема маркера", self.marker_theme_edit)
        form.addRow("", self.done_edit)

        layout.addLayout(form)

        self._task_id = task.id
        self._attachments: List = []
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
        attachments_title = QLabel("Вложения")
        attachments_title.setObjectName("TaskAttachmentsTitle")
        self.attachments_add_btn = QToolButton()
        self.attachments_add_btn.setText("Добавить")
        self.attachments_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attachments_add_btn.clicked.connect(self._open_attachment_dialog)
        attachments_header.addWidget(attachments_title)
        attachments_header.addStretch(1)
        attachments_header.addWidget(self.attachments_add_btn)
        attachments_layout.addLayout(attachments_header)

        self.attachments_list = QVBoxLayout()
        self.attachments_list.setSpacing(6)
        attachments_layout.addLayout(self.attachments_list)
        layout.addWidget(attachments_frame)

        self._load_attachment_sources()
        self._refresh_attachments()

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_accept)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self._on_accept)

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

            QDialog#TaskEditDialog QToolButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
            }}

            QDialog#TaskEditDialog QToolButton:hover {{
                background: #34363b;
            }}

            QDialog#TaskEditDialog QFrame#TaskAttachments {{
                background: #1c1d22;
                border: 1px solid #2a2b2f;
                border-radius: 8px;
            }}

            QDialog#TaskEditDialog QLabel#TaskAttachmentsTitle {{
                color: #f2f2f2;
                font-weight: 600;
            }}

            QDialog#TaskEditDialog QFrame#TaskAttachmentRow {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}

            QDialog#TaskEditDialog QLabel#TaskAttachmentKind {{
                color: #cfcfcf;
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

    def _restore_saved_size(self) -> None:
        raw = self._db.get_setting(self._SIZE_SETTING_KEY, default="").strip()
        if not raw:
            return
        width_str, separator, height_str = raw.partition("x")
        if not separator:
            return
        try:
            width = int(width_str)
            height = int(height_str)
        except ValueError:
            return
        self.resize(max(width, self.minimumWidth()), max(height, self.minimumHeight()))

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
            QMessageBox.warning(self, "Проверка", "Введите название задачи.")
            return
        time_text = self._current_time_text()
        try:
            validate_time_text(time_text)
            normalize_priority(self.priority_edit.currentText())
        except ValueError as exc:
            debug_task_dialog(
                f"task_edit_dialog accept_blocked_validation task_id={self.property('task_dialog_id')} error={exc}"
            )
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        debug_task_dialog(
            f"task_edit_dialog accept_commit task_id={self.property('task_dialog_id')} state={self._debug_form_state()}"
        )
        self.accept()

    def _current_time_text(self) -> str:
        if not self.time_toggle.isChecked():
            return ""
        return self.time_edit.time().toString("HH:mm")

    def _load_attachment_sources(self) -> None:
        notes = self._db.fetch_notes()
        ideas = self._db.fetch_ideas(archived=True)
        objects = self._db.fetch_objects()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        cloud_files = self._db.fetch_cloud_files()
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
            empty = QLabel("Нет вложений")
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
            link_label = QLabel(f"<a href='{attachment.id}'>{link_text}</a>")
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
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить вложение")
        dialog.setObjectName("TaskAttachmentDialog")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        kind_combo = QComboBox()
        kind_items = [
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

        item_combo = QComboBox()

        def fill_items(selected_kind: str) -> None:
            item_combo.clear()
            if selected_kind == "note":
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

        kind_combo.currentIndexChanged.connect(lambda idx: fill_items(kind_combo.currentData()))
        fill_items(kind_combo.currentData())

        form.addRow("Тип", kind_combo)
        form.addRow("Элемент", item_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
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
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QDialog#TaskAttachmentDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        kind = kind_combo.currentData()
        ref_id = item_combo.currentData()
        if ref_id is None:
            QMessageBox.warning(self, "Вложения", "Нет доступных элементов для добавления.")
            return
        self._db.add_task_attachment(self._task_id, kind, ref_id)
        self._refresh_attachments()

    def _remove_attachment(self, attachment) -> None:
        self._db.delete_task_attachment(attachment.id)
        self._refresh_attachments()

    def _open_attachment(self, attachment) -> None:
        if attachment.kind == "image":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Вложения", "Файл изображения не найден.")
                return
            self._open_image_preview(file_item)
            return
        if attachment.kind == "file":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Вложения", "Файл не найден.")
                return
            self._open_file_info(file_item)
            return
        if attachment.kind == "note":
            note = self._notes_by_id.get(attachment.ref_id)
            if not note:
                QMessageBox.warning(self, "Вложения", "Заметка не найдена.")
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
                QMessageBox.warning(self, "Вложения", "Идея не найдена.")
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
                QMessageBox.warning(self, "Вложения", "Объект не найден.")
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
                QMessageBox.warning(self, "Вложения", "Карта не найдена.")
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
                QMessageBox.warning(self, "Вложения", "Метка не найдена.")
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
                value_label = _build_markdown_preview_widget(value, dialog)
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
