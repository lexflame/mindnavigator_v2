"""TaskCreateDialog class module for tasks workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .task_details_dialog import TaskDetailsDialog

class TaskCreateDialog(TaskDetailsDialog):

    def __init__(
        self,
        parent=None,
        *,
        title: str = "",
        description: str = "",
        day: date | None = None,
        time_text: str = "",
        priority: str = "Medium",
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        recurrence_kind: str = "",
        recurrence_interval: int = 1,
        marker_color: str = "",
        marker_theme: str = "",
        project_task_type_id: Optional[int] = None,
        importance: int = 3,
        is_plan_task: bool = False,
    ):
        task = TaskRow(
            id=0,
            day=day or date.today(),
            time_text=time_text,
            title=title,
            description=description,
            priority=priority or "Medium",
            done=False,
            importance=importance,
            project_id=project_id,
            project_title="",
            project_area="",
            parent_id=parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
            marker_color=marker_color,
            marker_theme=marker_theme,
            project_task_type_id=project_task_type_id,
            is_plan_task=is_plan_task,
        )
        super().__init__(task, parent=parent)
        self.setProperty("task_dialog_minimizable", False)
        self.setProperty("task_dialog_id", 0)
        self.setProperty("task_dialog_kind", "create")
        self.setWindowTitle("Создание задачи")
        self._created_values: dict[str, object] | None = None
        self.title_inline.editor.setText(title)
        self._set_form_editing(True)
        self.header_edit_button.setText("Создать")
        self.header_add_button.setEnabled(False)
        self.links_add_button.setEnabled(False)
        self.images_add_button.setEnabled(False)
        self.detail_id_card.set_value("—")
        self.title_inline.editor.textChanged.connect(self._apply_project_suggestion)
        self._apply_project_suggestion(self.title_inline.editor.text())
        self.title_inline.editor.setFocus()

    def _save_form_updates(self) -> None:
        values = self.values()
        title = str(values["title"]).strip()
        if not title:
            QMessageBox.warning(self, "Проверка", "Введите название задачи.")
            self.title_inline.editor.setFocus()
            return
        try:
            validate_time_text(str(values["time_text"]))
            normalize_priority(str(values["priority"]))
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self._created_values = values
        self.accept()

    def values(self) -> dict[str, object]:
        qd_value = self.date_inline.current_value()
        day_value = qd_value if isinstance(qd_value, date) else self._task.day
        description = self._description_editor_text() if self.description_editor is not None else self._task.description
        return {
            "title": normalize_task_text_quotes(str(self.title_inline.current_value() or "")).strip(),
            "description": normalize_task_text_quotes(description).strip(),
            "day": day_value,
            "time_text": str(self.time_inline.current_value() or "").strip(),
            "priority": str(self.priority_inline.current_value() or "Medium").strip() or "Medium",
            "project_id": self.project_inline.current_value(),
            "project_task_type_id": self._type_project_task_type_id(),
            "recurrence_kind": str(self.recurrence_inline.current_value() or ""),
            "recurrence_interval": 1,
            "importance": int(self.importance_inline.current_value() or 3),
            "is_plan_task": bool(self.plan_task_checkbox.isChecked()),
            "marker_color": str(self.marker_color_inline.current_value() or ""),
            "marker_theme": str(self.marker_theme_inline.current_value() or ""),
        }

    def _type_project_task_type_id(self) -> Optional[int]:
        value = self.type_inline.current_value()
        if isinstance(value, int):
            return value
        return None

    def _apply_project_suggestion(self, title: str) -> None:
        editor = self.project_inline.editor
        if editor.currentData() is not None:
            return
        title_tokens = self._project_suggestion_tokens(title)
        if not title_tokens:
            return
        best_index = -1
        best_score = 0
        for index in range(editor.count()):
            if editor.itemData(index) is None:
                continue
            project_tokens = self._project_suggestion_tokens(editor.itemText(index))
            overlap = title_tokens & project_tokens
            if not overlap:
                continue
            score = sum(len(token) for token in overlap) + len(overlap) * 3
            if score > best_score:
                best_score = score
                best_index = index
        if best_index >= 0:
            editor.setCurrentIndex(best_index)

    @staticmethod
    def _project_suggestion_tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[\w]+", text.lower()) if len(token) >= 3}

__all__ = ["TaskCreateDialog"]
