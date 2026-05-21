from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication

from mindnavigator.storage import Database
from mindnavigator.workspaces.tasks import task_details_dialog, task_edit_dialog


def test_task_edit_dialog_can_sync_schedule_from_parent(monkeypatch, unique_temp_path) -> None:
    app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_edit_parent_schedule", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        parent = database.create_task(
            title="Parent task",
            description="",
            day=date(2026, 5, 24),
            time_text="13:45",
            priority="Medium",
        )
        child = database.create_task(
            title="Child task",
            description="",
            day=date(2026, 5, 21),
            time_text="09:00",
            priority="Medium",
            parent_id=parent.id,
        )

        monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)
        dialog = task_edit_dialog.TaskEditDialog(child)
        dialog.show()
        app.processEvents()

        assert dialog.parent_task_label.text() == "Parent task · 2026-05-24 13:45"
        assert dialog.parent_schedule_button.isVisible()

        dialog._sync_schedule_to_parent()

        values = dialog.values()
        assert values["day"] == parent.day
        assert values["time_text"] == parent.time_text
        assert not dialog.parent_schedule_button.isVisible()
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_details_dialog_updates_child_schedule_from_parent(monkeypatch, unique_temp_path) -> None:
    app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_details_parent_schedule", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        parent = database.create_task(
            title="Parent task",
            description="",
            day=date(2026, 6, 1),
            time_text="16:00",
            priority="Medium",
        )
        child = database.create_task(
            title="Child task",
            description="",
            day=date(2026, 5, 28),
            time_text="10:15",
            priority="Medium",
            parent_id=parent.id,
        )

        monkeypatch.setattr(task_details_dialog, "get_database", lambda: database)
        dialog = task_details_dialog.TaskDetailsDialog(child)
        dialog.show()
        app.processEvents()

        assert dialog.detail_parent_card.action_button.isVisible()

        dialog._sync_schedule_to_parent()

        refreshed = next(item for item in database.fetch_tasks() if item.id == child.id)
        assert refreshed.day == parent.day
        assert refreshed.time_text == parent.time_text
        assert not dialog.detail_parent_card.action_button.isVisible()
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
