from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication

from mindnavigator.storage import Database
from mindnavigator.workspaces.tasks import tasks_model as tasks_model_module
from mindnavigator.workspaces.tasks.task_roles import TaskRoles


def test_task_attachment_summaries_load_once_and_can_be_invalidated(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_attachment_summary_cache", ".sqlite3")
    database = Database(path=db_path)
    model = None
    try:
        first_task = database.create_task("First", "", date(2026, 2, 25), "", "Medium")
        second_task = database.create_task("Second", "", date(2026, 2, 25), "", "Medium")
        first_note = database.create_note("First note", "", [], "")
        second_note = database.create_note("Second note", "", [], "")
        database.add_task_attachment(first_task.id, "note", first_note.id)
        database.add_task_attachment(first_task.id, "note", second_note.id)

        calls = 0
        original_fetch_counts = database.fetch_task_attachment_counts

        def fetch_counts():
            nonlocal calls
            calls += 1
            return original_fetch_counts()

        monkeypatch.setattr(database, "fetch_task_attachment_counts", fetch_counts)
        monkeypatch.setattr(tasks_model_module, "get_database", lambda: database)
        model = tasks_model_module.TasksModel()

        first_index = next(
            model.index(row, 0)
            for row in range(model.rowCount())
            if model.index(row, 0).data(TaskRoles.TaskId) == first_task.id
        )
        second_index = next(
            model.index(row, 0)
            for row in range(model.rowCount())
            if model.index(row, 0).data(TaskRoles.TaskId) == second_task.id
        )

        assert calls == 0
        assert first_index.data(TaskRoles.AttachmentSummary) == ["Заметка ×2"]
        assert second_index.data(TaskRoles.AttachmentSummary) == []
        assert calls == 1

        database.add_task_attachment(second_task.id, "task", first_task.id)
        assert second_index.data(TaskRoles.AttachmentSummary) == []

        model.invalidate_attachment_summary_cache()
        assert second_index.data(TaskRoles.AttachmentSummary) == ["Задача"]
        assert calls == 2
    finally:
        if model is not None:
            model.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
