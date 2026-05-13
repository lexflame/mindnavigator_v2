"""TaskDetailsDialog class module for tasks workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from PySide6.QtCore import QEvent, QTimer
from .task_image_preview_dialog import TaskImagePreviewDialog

class TaskDetailsDialog(QDialog):
    def __init__(self, task: TaskRow, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Подробности задачи")
        self.setObjectName("TaskDetailsDialog")
        self.setProperty("task_dialog_minimizable", True)
        self.setProperty("task_dialog_id", int(task.id))
        self.setProperty("task_dialog_kind", "details")
        self.setMinimumWidth(760)
        self.setMinimumHeight(680)
        self._auto_minimize_pending = False

        self._db = get_database()
        self._task = task
        self._attachments: List = []
        self._tasks_by_id = {}
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._maps_by_id = {}
        self._markers_by_id = {}
        self._cloud_files_by_id = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_label = QLabel(task.title)
        title_label.setObjectName("TaskDetailsTitle")
        status_label = QLabel("Выполнено" if task.done else "В работе")
        status_label.setObjectName("TaskDetailsStatus")
        header.addWidget(title_label, 1)
        header.addWidget(status_label)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("TaskDetailsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QFrame()
        content.setObjectName("TaskDetailsContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        desc_block = QFrame()
        desc_block.setObjectName("TaskDetailsDescription")
        desc_layout = QVBoxLayout(desc_block)
        desc_layout.setContentsMargins(14, 12, 14, 12)
        desc_title = QLabel("Описание")
        desc_title.setObjectName("TaskDetailsSectionTitle")
        desc_layout.addWidget(desc_title)
        desc_layout.addWidget(_build_markdown_preview_widget(task.description, desc_block, self._open_linked_task))
        content_layout.addWidget(desc_block)

        props_block = QFrame()
        props_block.setObjectName("TaskDetailsProps")
        props_layout = QVBoxLayout(props_block)
        props_layout.setContentsMargins(14, 12, 14, 12)
        props_title = QLabel("Свойства")
        props_title.setObjectName("TaskDetailsSectionTitle")
        props_layout.addWidget(props_title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)

        time_text = task.time_text or "—"
        project_text = "—"
        if task.project_title:
            project_text = f"{task.project_area} · {task.project_title}" if task.project_area else task.project_title
        parent_title = "—"
        if task.parent_id is not None:
            parent_title = self._task_title(task.parent_id)
        recurrence_text = "—"
        if task.recurrence_kind:
            labels = {"daily": "Ежедневно", "weekly": "Еженедельно", "monthly": "Ежемесячно"}
            base = labels.get(task.recurrence_kind, task.recurrence_kind)
            if task.recurrence_interval > 1:
                recurrence_text = f"{base}, интервал {task.recurrence_interval}"
            else:
                recurrence_text = base

        form.addRow("ID", QLabel(str(task.id)))
        form.addRow("Дата", QLabel(task.day.isoformat()))
        form.addRow("Время", QLabel(time_text))
        form.addRow("Приоритет", QLabel(task.priority or "—"))
        form.addRow("Статус", QLabel("Выполнено" if task.done else "В работе"))
        form.addRow("Проект", QLabel(project_text))
        form.addRow("Родитель", QLabel(parent_title))
        form.addRow("Повтор", QLabel(recurrence_text))
        props_layout.addLayout(form)
        content_layout.addWidget(props_block)

        attachments_block = QFrame()
        attachments_block.setObjectName("TaskDetailsAttachments")
        attachments_layout = QVBoxLayout(attachments_block)
        attachments_layout.setContentsMargins(14, 12, 14, 12)
        attachments_layout.setSpacing(10)

        attachments_title = QLabel("Вложения")
        attachments_title.setObjectName("TaskDetailsSectionTitle")
        attachments_layout.addWidget(attachments_title)

        self.attachments_list = QVBoxLayout()
        self.attachments_list.setSpacing(6)
        attachments_layout.addLayout(self.attachments_list)
        content_layout.addWidget(attachments_block)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh_attachments()

        self.setStyleSheet(f"""
            QDialog#TaskDetailsDialog {{
                {MATH_PHYS_BACKGROUND}
                border: 1px solid #25272c;
                border-radius: 12px;
            }}
            QDialog#TaskDetailsDialog QLabel {{
                color: #cfcfcf;
            }}
            QLabel#TaskDetailsTitle {{
                color: #f2f2f2;
                font-size: 22px;
                font-weight: 600;
            }}
            QLabel#TaskDetailsStatus {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 12px;
                padding: 6px 12px;
                color: #d8d8d8;
            }}
            QLabel#TaskDetailsSectionTitle {{
                color: #f2f2f2;
                font-weight: 600;
            }}
            QScrollArea#TaskDetailsScroll {{
                background: transparent;
            }}
            QScrollArea#TaskDetailsScroll QWidget {{
                background: transparent;
            }}
            QFrame#TaskDetailsContent {{
                background: transparent;
            }}
            QFrame#TaskDetailsDescription,
            QFrame#TaskDetailsProps,
            QFrame#TaskDetailsAttachments {{
                background: #1c1d22;
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }}
            QFrame#TaskDetailsAttachments QFrame#TaskAttachmentRow {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}
            QDialog#TaskDetailsDialog QLabel#TaskAttachmentKind {{
                color: #cfcfcf;
            }}
            QDialog#TaskDetailsDialog QLabel#TaskAttachmentLink {{
                color: #6ab7ff;
            }}
            QDialog#TaskDetailsDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 8px;
            }}
            QDialog#TaskDetailsDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _task_title(self, task_id: int) -> str:
        tasks = self._db.fetch_tasks()
        for task in tasks:
            if task.id == task_id:
                return task.title
        return "—"

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
        ideas = self._db.fetch_ideas(archived=True)
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

            kind_label = QLabel(attachment_kind_label(attachment.kind))
            kind_label.setObjectName("TaskAttachmentKind")
            link_text = self._attachment_display_text(attachment)
            link_label = QLabel(f"<a href='{attachment.id}'>{link_text}</a>")
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
            widget = item.widget()
            if widget:
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

    def _open_attachment(self, attachment) -> None:
        if attachment.kind == "image":
            file_item = self._cloud_files_by_id.get(attachment.ref_id)
            if not file_item:
                QMessageBox.warning(self, "Вложения", "Файл изображения не найден.")
                return
            self._open_image_preview(file_item)
            return
        if attachment.kind == "task":
            task = self._tasks_by_id.get(attachment.ref_id)
            if not task:
                QMessageBox.warning(self, "Вложения", "Задача не найдена.")
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

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow():
            self._schedule_auto_minimize_on_deactivate()
        super().changeEvent(event)

    def _schedule_auto_minimize_on_deactivate(self) -> None:
        if self._auto_minimize_pending:
            return
        self._auto_minimize_pending = True
        QTimer.singleShot(0, self._maybe_auto_minimize_on_deactivate)

    def _maybe_auto_minimize_on_deactivate(self) -> None:
        self._auto_minimize_pending = False
        if not self.isVisible():
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
            return
        minimize_fn(dialog=self, task_id=int(self.property("task_dialog_id") or 0), is_edit_dialog=False)

    def _is_own_widget(self, widget: QWidget) -> bool:
        current: QWidget | None = widget
        while current is not None:
            if current is self:
                return True
            current = current.parentWidget()
        return False

__all__ = ["TaskDetailsDialog"]
