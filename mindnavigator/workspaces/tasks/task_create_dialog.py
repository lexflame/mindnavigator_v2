"""TaskCreateDialog class module for tasks workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .task_edit_dialog import TaskEditDialog

class TaskCreateDialog(TaskEditDialog):
    _SIZE_SETTING_KEY = "ui.task_create_dialog_size"

    def __init__(self, parent=None):
        task = TaskRow(
            id=0,
            day=date.today(),
            time_text="",
            title="",
            description="",
            priority="Medium",
            done=False,
            project_id=None,
            project_title="",
            project_area="",
            parent_id=None,
        )
        super().__init__(task, parent=parent)
        self.setProperty("task_dialog_minimizable", False)
        self.setProperty("task_dialog_id", 0)
        self.setProperty("task_dialog_kind", "create")
        self.setWindowTitle("Создание задачи")
        title_labels = self.findChildren(QLabel, "DialogTitle")
        if title_labels:
            title_labels[0].setText("Создание задачи")
        self.done_edit.hide()
        attachments_frame = self.findChild(QFrame, "TaskAttachments")
        if attachments_frame is not None:
            attachments_frame.hide()
        buttons = self.findChild(QDialogButtonBox)
        if buttons is not None:
            save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
            if save_button is not None:
                save_button.setText("Создать")
        self._enable_title_project_suggestion()
        self._apply_project_suggestion(self.title_edit.text())
        self.title_edit.setFocus()

__all__ = ["TaskCreateDialog"]
