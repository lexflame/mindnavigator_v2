"""ProjectEditDialog class module for projects workspace."""

from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit

from ._shared import *  # noqa: F401,F403

class ProjectEditDialog(QDialog):
    def __init__(self, project: Optional[ProjectRow] = None, parent=None):
        """Создает диалог создания или редактирования проекта."""
        super().__init__(parent)
        is_new = project is None
        self._project = project
        self._db = get_database()
        self.setWindowTitle("Создание проекта" if is_new else "Редактирование проекта")
        self.setObjectName("ProjectEditDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(780, 860)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Создание проекта" if is_new else "Редактирование проекта")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

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

        form.addRow("Область", self.area_edit)
        form.addRow("Название", self.title_edit)
        form.addRow("Дата обновления", self.updated_edit)
        form.addRow("Приоритет", self.priority_edit)
        form.addRow("Parent project", self.parent_project_edit)
        form.addRow("Task priority preset", self.default_task_priority_edit)
        form.addRow("Force recurrence", self.force_recurrence_kind_edit)
        form.addRow("Linked map", self.linked_map_edit)
        form.addRow("Linked note", self.linked_note_edit)
        form.addRow("Linked object", self.linked_object_edit)
        form.addRow("Маркер (цвет)", self.marker_color_edit)
        form.addRow("Тема маркера", self.marker_theme_edit)
        form.addRow("Каталог репозитория", self.repository_catalog_edit)
        form.addRow("", self.archived_edit)
        form.addRow("Типы задач", task_types_row)
        form.addRow("Связанные проекты", related_projects_row)
        form.addRow("Связанные задачи", related_tasks_row)
        form.addRow("Репозитории", repository_links_row)
        form.addRow("Wiki", wiki_links_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#ProjectEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#ProjectEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#ProjectEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#ProjectEditDialog QLineEdit,
            QDialog#ProjectEditDialog QComboBox,
            QDialog#ProjectEditDialog QDateEdit,
            QDialog#ProjectEditDialog QPlainTextEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#ProjectEditDialog QCheckBox {{
                color: #cfcfcf;
                padding: 4px 0;
            }}

            QDialog#ProjectEditDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#ProjectEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ProjectEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

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
