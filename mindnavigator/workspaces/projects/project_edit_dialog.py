"""ProjectEditDialog class module for projects workspace."""

from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QGridLayout, QPushButton, QScrollArea, QSizePolicy, QPlainTextEdit

from ._shared import *  # noqa: F401,F403

class ProjectEditDialog(QDialog):
    def __init__(self, project: Optional[ProjectRow] = None, parent=None):
        """Создает диалог создания или редактирования проекта."""
        super().__init__(parent)
        is_new = project is None
        self._project = project
        self._db = get_database()
        self._edit_mode = is_new
        self.setWindowTitle("Создание проекта" if is_new else "Редактирование проекта")
        self.setObjectName("ProjectEditDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.resize(1220, 780)
        self.setMinimumSize(1100, 700)

        self.area_edit = QLineEdit(project.area if project else "")
        self.area_edit.setPlaceholderText("Область проекта")

        self.title_edit = QLineEdit(project.title if project else "")
        self.title_edit.setPlaceholderText("Название проекта")

        self.updated_edit = QDateEdit()
        self.updated_edit.setCalendarPopup(True)
        self.updated_edit.setDisplayFormat("dd.MM.yyyy")
        self.updated_edit.setKeyboardTracking(False)
        self.updated_edit.setDate(QDate.currentDate())
        if project:
            self.updated_edit.setDate(QDate(project.updated.year, project.updated.month, project.updated.day))

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["Low", "Medium", "High"])
        self.priority_edit.setCurrentText(project.priority if project else "Medium")
        self.parent_project_edit = QComboBox()
        self.parent_project_edit.addItem("None", None)
        for item in self._db.fetch_projects():
            if project and item.id == project.id:
                continue
            self.parent_project_edit.addItem(f"{item.area} / {item.title}", item.id)
        parent_idx = self.parent_project_edit.findData(project.parent_project_id if project else None)
        if parent_idx >= 0:
            self.parent_project_edit.setCurrentIndex(parent_idx)

        self.default_task_priority_edit = QComboBox()
        self.default_task_priority_edit.addItem("None", "")
        self.default_task_priority_edit.addItem("High", "High")
        self.default_task_priority_edit.addItem("Medium", "Medium")
        self.default_task_priority_edit.addItem("Low", "Low")
        default_priority = (project.default_task_priority if project else "") or ""
        default_prio_idx = self.default_task_priority_edit.findData(default_priority)
        if default_prio_idx >= 0:
            self.default_task_priority_edit.setCurrentIndex(default_prio_idx)

        self.force_recurrence_kind_edit = QComboBox()
        self.force_recurrence_kind_edit.addItem("None", "")
        self.force_recurrence_kind_edit.addItem("Daily", "daily")
        self.force_recurrence_kind_edit.addItem("Weekly", "weekly")
        self.force_recurrence_kind_edit.addItem("Monthly", "monthly")
        recurrence_idx = self.force_recurrence_kind_edit.findData((project.force_recurrence_kind if project else "") or "")
        if recurrence_idx >= 0:
            self.force_recurrence_kind_edit.setCurrentIndex(recurrence_idx)

        self.linked_map_edit = QComboBox()
        self.linked_map_edit.addItem("None", None)
        for map_item in self._db.fetch_maps():
            self.linked_map_edit.addItem(map_item.title, map_item.id)
        linked_map_idx = self.linked_map_edit.findData(project.linked_map_id if project else None)
        if linked_map_idx >= 0:
            self.linked_map_edit.setCurrentIndex(linked_map_idx)

        self.linked_note_edit = QComboBox()
        self.linked_note_edit.addItem("None", None)
        for note_item in self._db.fetch_notes():
            self.linked_note_edit.addItem(note_item.title, note_item.id)
        linked_note_idx = self.linked_note_edit.findData(project.linked_note_id if project else None)
        if linked_note_idx >= 0:
            self.linked_note_edit.setCurrentIndex(linked_note_idx)

        self.linked_object_edit = QComboBox()
        self.linked_object_edit.addItem("None", None)
        for object_item in self._db.fetch_objects():
            self.linked_object_edit.addItem(object_item.title, object_item.id)
        linked_object_idx = self.linked_object_edit.findData(project.linked_object_id if project else None)
        if linked_object_idx >= 0:
            self.linked_object_edit.setCurrentIndex(linked_object_idx)

        self.marker_color_edit = QComboBox()
        self.marker_color_edit.addItem("None", "")
        self.marker_color_edit.addItem("Blue", "#4C78D0")
        self.marker_color_edit.addItem("Green", "#3FAF72")
        self.marker_color_edit.addItem("Orange", "#D68A3A")
        self.marker_color_edit.addItem("Red", "#C95656")
        self.marker_color_edit.addItem("Purple", "#8A63D2")
        marker_color_idx = self.marker_color_edit.findData((project.marker_color if project else "") or "")
        if marker_color_idx >= 0:
            self.marker_color_edit.setCurrentIndex(marker_color_idx)

        self.marker_theme_edit = QComboBox()
        self.marker_theme_edit.addItem("None", "")
        self.marker_theme_edit.addItem("Movies", "movies")
        self.marker_theme_edit.addItem("Games", "games")
        self.marker_theme_edit.addItem("Books", "books")
        self.marker_theme_edit.addItem("Music", "music")
        self.marker_theme_edit.addItem("Work", "work")
        self.marker_theme_edit.addItem("Personal", "personal")
        self.marker_theme_edit.addItem("Dev", "dev")
        marker_theme_idx = self.marker_theme_edit.findData((project.marker_theme if project else "") or "")
        if marker_theme_idx >= 0:
            self.marker_theme_edit.setCurrentIndex(marker_theme_idx)

        self.repository_catalog_edit = QLineEdit((project.repository_catalog if project else "") or "")
        self.repository_catalog_edit.setPlaceholderText("Путь к локальному репозиторию")

        self.archived_edit = QCheckBox("Архивировать")
        self.archived_edit.setChecked(project.archived if project else False)

        self.task_types_edit = self._make_multiline_edit(
            "DEV | #4C78D0 | dev | active\nMUSIC | #8A63D2 | music | active"
        )
        self.related_projects_edit = self._make_multiline_edit("ID связанных проектов, по одному в строке")
        self.related_tasks_edit = self._make_multiline_edit("ID связанных задач, по одному в строке")
        self.repository_links_edit = self._make_multiline_edit("MindNavigator Core | D:/_Branch/PROJECTS/mindnavigator")
        self.wiki_links_edit = self._make_multiline_edit("Project Wiki | https://docs.example.com/project")
        task_types_row = self._make_property_editor(
            self.task_types_edit,
            [
                ("Добавить", self._add_task_type_line),
                ("Изменить", self._edit_task_type_line),
                ("Актив./деакт.", self._toggle_task_type_line),
                ("Удалить", self._delete_task_type_line),
            ],
        )
        related_projects_row = self._make_property_editor(self.related_projects_edit, [("Добавить", self._add_related_project_line)])
        related_tasks_row = self._make_property_editor(self.related_tasks_edit, [("Добавить", self._add_related_task_line)])
        repository_links_row = self._make_property_editor(self.repository_links_edit, [("Добавить", self._add_repository_link_line)])
        wiki_links_row = self._make_property_editor(self.wiki_links_edit, [("Добавить", self._add_wiki_link_line)])
        if project:
            self._load_project_properties(project.id)

        self._editor_controls = [
            self.area_edit,
            self.title_edit,
            self.updated_edit,
            self.priority_edit,
            self.parent_project_edit,
            self.default_task_priority_edit,
            self.force_recurrence_kind_edit,
            self.linked_map_edit,
            self.linked_note_edit,
            self.linked_object_edit,
            self.marker_color_edit,
            self.marker_theme_edit,
            self.repository_catalog_edit,
            self.archived_edit,
            self.task_types_edit,
            self.related_projects_edit,
            self.related_tasks_edit,
            self.repository_links_edit,
            self.wiki_links_edit,
        ]
        self._edit_action_buttons: list[QWidget] = []
        for row in (task_types_row, related_projects_row, related_tasks_row, repository_links_row, wiki_links_row):
            self._edit_action_buttons.extend(row.findChildren(QToolButton))

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(0)

        self.shell = QFrame(self)
        self.shell.setObjectName("ProjectDialogShell")
        root.addWidget(self.shell, 1)
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(24, 20, 24, 16)
        shell_layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(4)
        self.title_label = QLabel(project.title if project else "Новый проект")
        self.title_label.setObjectName("DialogTitle")
        self.mode_label = QLabel("Редактирование проекта" if is_new else "Просмотр проекта")
        self.mode_label.setObjectName("ProjectDialogMode")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.mode_label)
        header_row.addLayout(title_box, 1)
        self.close_button = QPushButton("Закрыть")
        self.close_button.setObjectName("ProjectDialogSecondaryButton")
        self.edit_button = QPushButton("Редактировать")
        self.edit_button.setObjectName("ProjectDialogPrimaryButton")
        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("ProjectDialogPrimaryButton")
        self.cancel_button = QPushButton("Отменить")
        self.cancel_button.setObjectName("ProjectDialogSecondaryButton")
        self.close_button.clicked.connect(self.reject)
        self.edit_button.clicked.connect(lambda: self._set_edit_mode(True))
        self.save_button.clicked.connect(self._on_accept)
        self.cancel_button.clicked.connect(self.reject)
        header_row.addWidget(self.close_button)
        header_row.addWidget(self.edit_button)
        header_row.addWidget(self.cancel_button)
        header_row.addWidget(self.save_button)
        shell_layout.addLayout(header_row)

        metrics_grid = QGridLayout()
        metrics_grid.setContentsMargins(0, 0, 0, 0)
        metrics_grid.setHorizontalSpacing(10)
        metrics_grid.setVerticalSpacing(10)
        metrics_grid.addWidget(self._metric_card("Область", self.area_edit), 0, 0)
        metrics_grid.addWidget(self._metric_card("Дата обновления", self.updated_edit), 0, 1)
        metrics_grid.addWidget(self._metric_card("Приоритет", self.priority_edit), 0, 2)
        metrics_grid.addWidget(self._metric_card("Parent project", self.parent_project_edit), 0, 3)
        shell_layout.addLayout(metrics_grid)

        scroll = QScrollArea(self.shell)
        scroll.setObjectName("ProjectDialogScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("ProjectDialogContent")
        scroll.setWidget(content)
        content_layout = QGridLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setHorizontalSpacing(12)
        content_layout.setVerticalSpacing(12)

        main_card = self._section_card("Основное")
        main_form = self._section_form(main_card)
        main_form.addRow("Название", self.title_edit)
        main_form.addRow("Каталог репозитория", self.repository_catalog_edit)
        main_form.addRow("Репозитории", repository_links_row)
        main_form.addRow("Wiki", wiki_links_row)

        links_card = self._section_card("Связи")
        links_form = self._section_form(links_card)
        links_form.addRow("Связанные проекты", related_projects_row)
        links_form.addRow("Связанные задачи", related_tasks_row)
        links_form.addRow("Linked map", self.linked_map_edit)
        links_form.addRow("Linked note", self.linked_note_edit)
        links_form.addRow("Linked object", self.linked_object_edit)

        types_card = self._section_card("Типы задач")
        types_form = self._section_form(types_card)
        types_form.addRow("", task_types_row)

        properties_card = self._section_card("Свойства")
        properties_form = self._section_form(properties_card)
        properties_form.addRow("Task priority preset", self.default_task_priority_edit)
        properties_form.addRow("Force recurrence", self.force_recurrence_kind_edit)
        properties_form.addRow("Маркер (цвет)", self.marker_color_edit)
        properties_form.addRow("Тема маркера", self.marker_theme_edit)
        properties_form.addRow("Архивирован", self.archived_edit)

        hierarchy_card = self._section_card("Иерархия и правила")
        hierarchy_form = self._section_form(hierarchy_card)
        hierarchy_form.addRow("Parent project", QLabel(self.parent_project_edit.currentText()))
        preset_note = QLabel("Настройки поведения задач, повторяемости, напоминаний и другие правила наследуются из родительского проекта или глобальных параметров системы.")
        preset_note.setObjectName("ProjectDialogInfo")
        preset_note.setWordWrap(True)
        hierarchy_form.addRow("Поведение задач по умолчанию", QLabel("Preset не задан"))
        hierarchy_form.addRow("", preset_note)

        stats_card = self._section_card("Статистика")
        stats_layout = stats_card.layout()
        if isinstance(stats_layout, QVBoxLayout):
            stats_layout.addLayout(self._statistics_row())

        content_layout.addWidget(main_card, 0, 0)
        content_layout.addWidget(properties_card, 0, 1)
        content_layout.addWidget(links_card, 1, 0)
        content_layout.addWidget(hierarchy_card, 1, 1)
        content_layout.addWidget(types_card, 2, 0)
        content_layout.addWidget(stats_card, 2, 1)
        content_layout.setColumnStretch(0, 1)
        content_layout.setColumnStretch(1, 1)
        shell_layout.addWidget(scroll, 1)

        QShortcut(QKeySequence("Ctrl+E"), self, activated=lambda: self._set_edit_mode(True))
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_shortcut)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_accept)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_accept)

        self._set_edit_mode(self._edit_mode)

        self.setStyleSheet(f"""
            QDialog#ProjectEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QFrame#ProjectDialogShell {{
                background: rgba(15, 28, 47, 0.96);
                border: 1px solid #21324a;
                border-radius: 14px;
            }}

            QDialog#ProjectEditDialog QLabel {{
                color: #d7dce7;
            }}

            QDialog#ProjectEditDialog QLabel#DialogTitle {{
                color: #f6f8fb;
                font-size: 26px;
                font-weight: 600;
            }}

            QLabel#ProjectDialogMode {{
                color: #b7c1d5;
                font-size: 14px;
            }}

            QFrame#ProjectDialogMetric,
            QFrame#ProjectDialogSection {{
                background: rgba(17, 31, 52, 0.78);
                border: 1px solid #263a56;
                border-radius: 8px;
            }}

            QLabel#ProjectDialogSectionTitle {{
                color: #f1f5fb;
                font-size: 16px;
                font-weight: 600;
            }}

            QLabel#ProjectDialogMetricTitle {{
                color: #aeb8cb;
                font-size: 12px;
            }}

            QLabel#ProjectDialogInfo {{
                color: #b8c3d8;
                background: rgba(28, 47, 78, 0.62);
                border: 1px solid #2c4a74;
                border-radius: 7px;
                padding: 9px 11px;
            }}

            QScrollArea#ProjectDialogScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#ProjectDialogContent {{
                background: transparent;
            }}

            QDialog#ProjectEditDialog QLineEdit,
            QDialog#ProjectEditDialog QComboBox,
            QDialog#ProjectEditDialog QDateEdit,
            QDialog#ProjectEditDialog QPlainTextEdit {{
                background: rgba(9, 18, 31, 0.72);
                color: #edf2fb;
                border: 1px solid #2a405f;
                padding: 7px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#ProjectEditDialog QLineEdit:disabled,
            QDialog#ProjectEditDialog QComboBox:disabled,
            QDialog#ProjectEditDialog QDateEdit:disabled,
            QDialog#ProjectEditDialog QPlainTextEdit:disabled {{
                color: #dce5f4;
                background: rgba(9, 18, 31, 0.44);
                border: 1px solid #223650;
            }}

            QDialog#ProjectEditDialog QCheckBox {{
                color: #d7dce7;
                padding: 4px 0;
            }}

            QDialog#ProjectEditDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#ProjectEditDialog QPushButton,
            QDialog#ProjectEditDialog QToolButton {{
                background: rgba(33, 48, 70, 0.86);
                color: #e6e6e6;
                border: 1px solid #344b6b;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ProjectEditDialog QPushButton:hover,
            QDialog#ProjectEditDialog QToolButton:hover {{
                background: rgba(45, 64, 91, 0.95);
            }}

            QPushButton#ProjectDialogPrimaryButton {{
                background: #5227ff;
                border: 1px solid #6541ff;
                color: #ffffff;
                font-weight: 600;
                min-width: 132px;
            }}

            QPushButton#ProjectDialogSecondaryButton {{
                min-width: 118px;
            }}
        """)

    def _metric_card(self, title: str, editor: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("ProjectDialogMetric")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(4)
        label = QLabel(title)
        label.setObjectName("ProjectDialogMetricTitle")
        text_box.addWidget(label)
        text_box.addWidget(editor)
        layout.addLayout(text_box, 1)
        return card

    def _section_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("ProjectDialogSection")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(10)
        label = QLabel(title)
        label.setObjectName("ProjectDialogSectionTitle")
        card_layout.addWidget(label)
        return card

    def _section_form(self, card: QFrame) -> QFormLayout:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(9)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        layout = card.layout()
        if isinstance(layout, QVBoxLayout):
            layout.addLayout(form)
        return form

    def _statistics_row(self) -> QHBoxLayout:
        stats = self._project_statistics()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for title, value in (
            ("Задач", stats["total"]),
            ("Активных", stats["active"]),
            ("Готово", stats["done"]),
            ("Связей", stats["links"]),
        ):
            row.addWidget(self._stat_card(title, value))
        return row

    def _stat_card(self, title: str, value: int) -> QFrame:
        card = QFrame()
        card.setObjectName("ProjectDialogMetric")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        label = QLabel(title)
        label.setObjectName("ProjectDialogMetricTitle")
        number = QLabel(str(value))
        number.setObjectName("ProjectDialogSectionTitle")
        layout.addWidget(label)
        layout.addWidget(number)
        return card

    def _project_statistics(self) -> dict[str, int]:
        if self._project is None:
            return {"total": 0, "active": 0, "done": 0, "links": 0}
        project_id = self._project.id
        tasks = [task for task in self._db.fetch_tasks() if getattr(task, "project_id", None) == project_id]
        done = sum(1 for task in tasks if bool(getattr(task, "done", False)))
        links = len(self._parse_int_lines(self.related_projects_edit.toPlainText(), "Связанные проекты"))
        links += len(self._parse_int_lines(self.related_tasks_edit.toPlainText(), "Связанные задачи"))
        return {"total": len(tasks), "active": len(tasks) - done, "done": done, "links": links}

    def _set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        for control in self._editor_controls:
            control.setEnabled(enabled)
        for button in self._edit_action_buttons:
            button.setVisible(enabled)
            button.setEnabled(enabled)
        if hasattr(self, "title_label"):
            self.title_label.setText(self.title_edit.text().strip() or "Новый проект")
        self.mode_label.setText("Редактирование проекта" if enabled else "Просмотр проекта")
        self.close_button.setVisible(not enabled)
        self.edit_button.setVisible(not enabled)
        self.cancel_button.setVisible(enabled)
        self.save_button.setVisible(enabled)

    def _save_shortcut(self) -> None:
        if self._edit_mode:
            self._on_accept()

    def _make_multiline_edit(self, placeholder: str) -> QPlainTextEdit:
        edit = QPlainTextEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(64)
        return edit

    def _make_property_editor(self, edit: QPlainTextEdit, actions: list[tuple[str, object]]) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(edit)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        action_row.addStretch(1)
        for text, callback in actions:
            button = QToolButton()
            button.setText(text)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(callback)
            action_row.addWidget(button)
        layout.addLayout(action_row)
        return widget

    def _append_line(self, edit: QPlainTextEdit, line: str) -> None:
        line = (line or "").strip()
        if not line:
            return
        text = edit.toPlainText().strip()
        edit.setPlainText(f"{text}\n{line}" if text else line)

    def _current_line_info(self, edit: QPlainTextEdit) -> tuple[list[str], int, str]:
        lines = edit.toPlainText().splitlines()
        if not lines:
            return lines, -1, ""
        cursor = edit.textCursor()
        line_index = min(max(0, cursor.blockNumber()), len(lines) - 1)
        return lines, line_index, lines[line_index].strip()

    def _replace_line(self, edit: QPlainTextEdit, line_index: int, line: str) -> None:
        lines = edit.toPlainText().splitlines()
        if line_index < 0 or line_index >= len(lines):
            return
        lines[line_index] = line
        edit.setPlainText("\n".join(lines))
        cursor = edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        for _ in range(line_index):
            cursor.movePosition(cursor.MoveOperation.Down)
        edit.setTextCursor(cursor)

    def _remove_line(self, edit: QPlainTextEdit, line_index: int) -> None:
        lines = edit.toPlainText().splitlines()
        if line_index < 0 or line_index >= len(lines):
            return
        del lines[line_index]
        edit.setPlainText("\n".join(lines))

    def _copy_combo_items(self, source: QComboBox, target: QComboBox) -> None:
        for idx in range(source.count()):
            target.addItem(source.itemText(idx), source.itemData(idx))

    def _add_task_type_line(self) -> None:
        values = self._task_type_dialog()
        if values is None:
            return
        self._append_line(self.task_types_edit, self._format_task_type_line(values))

    def _edit_task_type_line(self) -> None:
        lines, line_index, line = self._current_line_info(self.task_types_edit)
        if line_index < 0 or not line:
            return
        values = self._parse_task_type_line(line)
        updated = self._task_type_dialog(values)
        if updated is None:
            return
        self._replace_line(self.task_types_edit, line_index, self._format_task_type_line(updated))

    def _toggle_task_type_line(self) -> None:
        lines, line_index, line = self._current_line_info(self.task_types_edit)
        if line_index < 0 or not line:
            return
        values = self._parse_task_type_line(line)
        values["active"] = not bool(values.get("active", True))
        self._replace_line(self.task_types_edit, line_index, self._format_task_type_line(values))

    def _delete_task_type_line(self) -> None:
        _lines, line_index, line = self._current_line_info(self.task_types_edit)
        if line_index < 0 or not line:
            return
        values = self._parse_task_type_line(line)
        title = str(values.get("title") or "")
        if self._project:
            existing = next(
                (
                    item
                    for item in self._db.fetch_project_task_types(self._project.id, include_inactive=True)
                    if item.title == title
                ),
                None,
            )
            if existing is not None and self._db.project_task_type_in_use(existing.id):
                QMessageBox.warning(
                    self,
                    "Тип задач",
                    "Тип используется задачами. Деактивируйте тип вместо удаления.",
                )
                return
        if QMessageBox.question(self, "Тип задач", f"Удалить тип {title}?") != QMessageBox.StandardButton.Yes:
            return
        self._remove_line(self.task_types_edit, line_index)

    def _task_type_dialog(self, initial: Optional[dict[str, object]] = None) -> Optional[dict[str, object]]:
        dialog = QDialog(self)
        dialog.setWindowTitle("Тип задач")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("DEV")
        if initial:
            title_edit.setText(str(initial.get("title") or ""))
        color_combo = QComboBox()
        self._copy_combo_items(self.marker_color_edit, color_combo)
        if initial:
            color_idx = color_combo.findData(str(initial.get("color_marker") or ""))
            if color_idx >= 0:
                color_combo.setCurrentIndex(color_idx)
        theme_combo = QComboBox()
        self._copy_combo_items(self.marker_theme_edit, theme_combo)
        if initial:
            theme_idx = theme_combo.findData(str(initial.get("theme_marker") or ""))
            if theme_idx >= 0:
                theme_combo.setCurrentIndex(theme_idx)
        active_edit = QCheckBox("Активен")
        active_edit.setChecked(bool(initial.get("active", True)) if initial else True)
        form.addRow("Название", title_edit)
        form.addRow("Цвет", color_combo)
        form.addRow("Тема", theme_combo)
        form.addRow("", active_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        title = " ".join(title_edit.text().strip().upper().split())
        if not title:
            QMessageBox.warning(self, "Проверка", "Название типа задач не должно быть пустым.")
            return None
        return {
            "title": title,
            "color_marker": color_combo.currentData() or "",
            "theme_marker": theme_combo.currentData() or "",
            "active": active_edit.isChecked(),
        }

    @staticmethod
    def _format_task_type_line(values: dict[str, object]) -> str:
        status = "active" if bool(values.get("active", True)) else "disabled"
        title = " ".join(str(values.get("title") or "").strip().upper().split())
        return f"{title} | {values.get('color_marker') or ''} | {values.get('theme_marker') or ''} | {status}"

    @staticmethod
    def _parse_task_type_line(line: str) -> dict[str, object]:
        parts = [part.strip() for part in (line or "").split("|")]
        title = " ".join((parts[0] if parts else "").strip().upper().split())
        status = (parts[3] if len(parts) > 3 else "active").strip().lower()
        return {
            "title": title,
            "color_marker": parts[1] if len(parts) > 1 else "",
            "theme_marker": parts[2] if len(parts) > 2 else "",
            "active": status not in {"disabled", "inactive", "off", "0", "false"},
        }

    def _add_related_project_line(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Связанный проект")
        layout = QVBoxLayout(dialog)
        combo = QComboBox()
        for project in self._db.fetch_projects():
            if self._project and project.id == self._project.id:
                continue
            combo.addItem(f"{project.area} / {project.title}", project.id)
        layout.addWidget(combo)
        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if combo.count() and dialog.exec() == QDialog.DialogCode.Accepted:
            self._append_line(self.related_projects_edit, str(combo.currentData()))

    def _add_related_task_line(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Связанная задача")
        layout = QVBoxLayout(dialog)
        combo = QComboBox()
        for task in self._db.fetch_tasks():
            combo.addItem(f"MN-{task.id} {task.title}", task.id)
        layout.addWidget(combo)
        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if combo.count() and dialog.exec() == QDialog.DialogCode.Accepted:
            self._append_line(self.related_tasks_edit, str(combo.currentData()))

    def _add_repository_link_line(self) -> None:
        self._add_link_line(self.repository_links_edit, "Репозиторий")

    def _add_wiki_link_line(self) -> None:
        self._add_link_line(self.wiki_links_edit, "Wiki")

    def _add_link_line(self, edit: QPlainTextEdit, title: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        title_edit = QLineEdit()
        url_edit = QLineEdit()
        form.addRow("Текст", title_edit)
        form.addRow("Ссылка", url_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url = url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Проверка", "Ссылка не должна быть пустой.")
            return
        link_title = title_edit.text().strip()
        self._append_line(edit, f"{link_title} | {url}" if link_title else url)

    def _load_project_properties(self, project_id: int) -> None:
        task_type_lines = []
        for item in self._db.fetch_project_task_types(project_id, include_inactive=True):
            status = "active" if item.active else "disabled"
            task_type_lines.append(f"{item.title} | {item.color_marker} | {item.theme_marker} | {status}")
        self.task_types_edit.setPlainText("\n".join(task_type_lines))
        self.related_projects_edit.setPlainText(
            "\n".join(str(item.related_project_id) for item in self._db.fetch_project_related_projects(project_id))
        )
        self.related_tasks_edit.setPlainText(
            "\n".join(str(item.task_id) for item in self._db.fetch_project_related_tasks(project_id))
        )
        self.repository_links_edit.setPlainText(self._format_links(self._db.fetch_project_repository_links(project_id)))
        self.wiki_links_edit.setPlainText(self._format_links(self._db.fetch_project_wiki_links(project_id)))

    @staticmethod
    def _format_links(links) -> str:
        return "\n".join(f"{item.title} | {item.url}" if item.title else item.url for item in links)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        try:
            validate_area(self.area_edit.text())
            validate_title(self.title_edit.text(), field_name="Название проекта")
            normalize_priority(self.priority_edit.currentText())
            self._parse_project_task_types()
            self._parse_int_lines(self.related_projects_edit.toPlainText(), "Связанные проекты")
            self._parse_int_lines(self.related_tasks_edit.toPlainText(), "Связанные задачи")
            self._parse_links(self.repository_links_edit.toPlainText())
            self._parse_links(self.wiki_links_edit.toPlainText())
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return

        self.accept()

    def apply_project_properties(self, project_id: int) -> None:
        self._db.replace_project_task_types(project_id, self._parse_project_task_types())
        self._db.replace_project_related_projects(
            project_id,
            self._parse_int_lines(self.related_projects_edit.toPlainText(), "Связанные проекты"),
        )
        self._db.replace_project_related_tasks(
            project_id,
            self._parse_int_lines(self.related_tasks_edit.toPlainText(), "Связанные задачи"),
        )
        self._db.replace_project_repository_links(project_id, self._parse_links(self.repository_links_edit.toPlainText()))
        self._db.replace_project_wiki_links(project_id, self._parse_links(self.wiki_links_edit.toPlainText()))

    def _parse_project_task_types(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        seen: set[str] = set()
        for raw_line in self.task_types_edit.toPlainText().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            values = self._parse_task_type_line(line)
            title = str(values.get("title") or "")
            if not title:
                raise ValueError("Название типа задач не должно быть пустым.")
            if title in seen:
                raise ValueError(f"Дублирующий тип задач: {title}")
            seen.add(title)
            result.append(
                {
                    "title": title,
                    "color_marker": str(values.get("color_marker") or ""),
                    "theme_marker": str(values.get("theme_marker") or ""),
                    "active": bool(values.get("active", True)),
                }
            )
        return result

    @staticmethod
    def _parse_int_lines(text: str, field_name: str) -> list[int]:
        result: list[int] = []
        seen: set[int] = set()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                item_id = int(line)
            except ValueError as exc:
                raise ValueError(f"{field_name}: ожидается числовой ID, получено {line!r}.") from exc
            if item_id not in seen:
                seen.add(item_id)
                result.append(item_id)
        return result

    @staticmethod
    def _parse_links(text: str) -> list[dict[str, str]]:
        links: list[dict[str, str]] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if "|" in line:
                title, url = [part.strip() for part in line.split("|", 1)]
            else:
                title, url = "", line
            if not url:
                raise ValueError("Ссылка repository/wiki не должна быть пустой.")
            links.append({"title": title, "url": url})
        return links

    def values(self) -> dict:
        """Возвращает значения формы проекта."""
        qd = self.updated_edit.date()
        return {
            "area": self.area_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "updated": date(qd.year(), qd.month(), qd.day()),
            "priority": self.priority_edit.currentText().strip() or "Medium",
            "parent_project_id": self.parent_project_edit.currentData(),
            "default_task_priority": self.default_task_priority_edit.currentData() or "",
            "force_recurrence_kind": self.force_recurrence_kind_edit.currentData() or "",
            "linked_map_id": self.linked_map_edit.currentData(),
            "linked_note_id": self.linked_note_edit.currentData(),
            "linked_object_id": self.linked_object_edit.currentData(),
            "marker_color": self.marker_color_edit.currentData() or "",
            "marker_theme": self.marker_theme_edit.currentData() or "",
            "repository_catalog": self.repository_catalog_edit.text().strip(),
            "archived": self.archived_edit.isChecked(),
        }

__all__ = ["ProjectEditDialog"]
