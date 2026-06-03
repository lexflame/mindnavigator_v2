from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication, QWidget

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

        assert dialog.header_parent_card.action_button.isVisible()

        dialog._sync_schedule_to_parent()

        refreshed = next(item for item in database.fetch_tasks() if item.id == child.id)
        assert refreshed.day == parent.day
        assert refreshed.time_text == parent.time_text
        assert not dialog.header_parent_card.action_button.isVisible()
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_details_dialog_uses_tasks_model_for_parent_schedule_sync(monkeypatch, unique_temp_path) -> None:
    app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_details_parent_schedule_model", ".sqlite3")
    database = Database(path=db_path)
    host = None
    dialog = None
    try:
        parent = database.create_task(
            title="Parent task",
            description="",
            day=date(2026, 6, 3),
            time_text="14:20",
            priority="Medium",
        )
        child = database.create_task(
            title="Child task",
            description="",
            day=date(2026, 5, 29),
            time_text="08:10",
            priority="Medium",
            parent_id=parent.id,
        )

        class _FakeModel:
            def __init__(self) -> None:
                self.calls: list[tuple[int, int]] = []

            def row_for_task_id(self, task_id: int) -> int:
                return 0 if task_id == child.id else -1

            def move_task_to_parent_schedule(self, task_id: int, parent_task_id: int) -> bool:
                self.calls.append((task_id, parent_task_id))
                database.update_task(
                    child.id,
                    title=child.title,
                    description=child.description,
                    day=parent.day,
                    time_text=parent.time_text,
                    priority=child.priority,
                    done=child.done,
                    project_id=child.project_id,
                    parent_id=child.parent_id,
                    recurrence_kind=child.recurrence_kind,
                    recurrence_interval=child.recurrence_interval,
                    is_plan_task=child.is_plan_task,
                    plan_order=child.plan_order,
                    marker_color=child.marker_color,
                    marker_theme=child.marker_theme,
                )
                return True

            def update_task_by_row(self, *args, **kwargs) -> None:
                raise AssertionError("update_task_by_row should not be used in this scenario")

        class _Host(QWidget):
            def __init__(self, model) -> None:
                super().__init__()
                self._model = model

            def model(self):
                return self._model

        fake_model = _FakeModel()
        host = _Host(fake_model)

        monkeypatch.setattr(task_details_dialog, "get_database", lambda: database)
        dialog = task_details_dialog.TaskDetailsDialog(child, parent=host)
        dialog.show()
        app.processEvents()

        dialog._sync_schedule_to_parent()

        refreshed = next(item for item in database.fetch_tasks() if item.id == child.id)
        assert fake_model.calls == [(child.id, parent.id)]
        assert refreshed.day == parent.day
        assert refreshed.time_text == parent.time_text
    finally:
        if dialog is not None:
            dialog.deleteLater()
        if host is not None:
            host.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_details_dialog_save_uses_tasks_model_when_available(monkeypatch, unique_temp_path) -> None:
    app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_details_edit_model", ".sqlite3")
    database = Database(path=db_path)
    host = None
    dialog = None
    try:
        task = database.create_task(
            title="Source task",
            description="Old",
            day=date(2026, 6, 4),
            time_text="10:00",
            priority="Medium",
        )

        class _FakeModel:
            def __init__(self) -> None:
                self.row_calls: list[int] = []
                self.update_calls: list[dict] = []

            def row_for_task_id(self, task_id: int) -> int:
                self.row_calls.append(task_id)
                return 0 if task_id == task.id else -1

            def update_task_by_row(
                self,
                row_idx: int,
                title: str,
                description: str,
                day: date,
                time_text: str,
                priority: str,
                done: bool,
                project_id,
                recurrence_kind: str,
                recurrence_interval: int,
                is_plan_task: bool = False,
                marker_color: str = "",
                marker_theme: str = "",
            ) -> None:
                self.update_calls.append(
                    {
                        "row_idx": row_idx,
                        "title": title,
                        "description": description,
                        "day": day,
                        "time_text": time_text,
                        "priority": priority,
                        "done": done,
                        "project_id": project_id,
                        "recurrence_kind": recurrence_kind,
                        "recurrence_interval": recurrence_interval,
                        "is_plan_task": is_plan_task,
                        "marker_color": marker_color,
                        "marker_theme": marker_theme,
                    }
                )
                database.update_task(
                    task.id,
                    title=title,
                    description=description,
                    day=day,
                    time_text=time_text,
                    priority=priority,
                    done=done,
                    project_id=project_id,
                    parent_id=task.parent_id,
                    recurrence_kind=recurrence_kind,
                    recurrence_interval=recurrence_interval,
                    is_plan_task=is_plan_task,
                    plan_order=task.plan_order,
                    marker_color=marker_color,
                    marker_theme=marker_theme,
                )

            def move_task_to_parent_schedule(self, _task_id: int, _parent_task_id: int) -> bool:
                raise AssertionError("move_task_to_parent_schedule should not be used in this scenario")

        class _Host(QWidget):
            def __init__(self, model) -> None:
                super().__init__()
                self._model = model

            def model(self):
                return self._model

        fake_model = _FakeModel()
        host = _Host(fake_model)

        monkeypatch.setattr(task_details_dialog, "get_database", lambda: database)
        dialog = task_details_dialog.TaskDetailsDialog(task, parent=host)
        dialog.show()
        app.processEvents()

        dialog._open_edit_dialog()
        dialog.title_inline.editor.setText("Updated task")
        assert dialog.description_editor is not None
        dialog.description_editor.setPlainText("Updated")
        dialog.date_inline.set_value(date(2026, 6, 8))
        dialog.time_inline.editor.setText("18:05")
        dialog.priority_inline.editor.setCurrentIndex(dialog.priority_inline.editor.findData("High"))
        dialog.status_inline.editor.setCurrentIndex(dialog.status_inline.editor.findData(True))
        dialog._open_edit_dialog()

        refreshed = next(item for item in database.fetch_tasks() if item.id == task.id)
        assert fake_model.row_calls == [task.id]
        assert len(fake_model.update_calls) == 1
        assert refreshed.title == "Updated task"
        assert refreshed.description == "Updated"
        assert refreshed.day == date(2026, 6, 8)
        assert refreshed.time_text == "18:05"
        assert refreshed.priority == "High"
        assert refreshed.done is True
    finally:
        if dialog is not None:
            dialog.deleteLater()
        if host is not None:
            host.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
