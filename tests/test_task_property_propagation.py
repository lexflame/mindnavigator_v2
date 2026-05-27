from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication

from mindnavigator.storage import Database
from mindnavigator.workspaces.tasks import task_edit_dialog, tasks_model
from mindnavigator.workspaces.tasks.task_property_propagation import TASK_PROPAGATABLE_FIELDS


def test_tasks_model_applies_properties_to_children_and_descendants(monkeypatch, unique_temp_path) -> None:
    db_path = unique_temp_path("task_property_propagation", ".sqlite3")
    database = Database(path=db_path)
    try:
        project_parent = database.create_project("Work", "Parent project", date(2026, 5, 20), "Medium")
        project_child = database.create_project("Work", "Child project", date(2026, 5, 20), "Medium")
        parent = database.create_task(
            title="Parent",
            description="",
            day=date(2026, 5, 26),
            time_text="18:30",
            priority="High",
            project_id=project_parent.id,
            marker_color="#b74a4a",
            marker_theme="work",
        )
        child = database.create_task(
            title="Child",
            description="",
            day=date(2026, 5, 21),
            time_text="09:00",
            priority="Low",
            project_id=project_child.id,
            parent_id=parent.id,
            marker_color="#2f6edb",
            marker_theme="movies",
        )
        grandchild = database.create_task(
            title="Grandchild",
            description="",
            day=date(2026, 5, 22),
            time_text="10:00",
            priority="Medium",
            project_id=project_child.id,
            parent_id=child.id,
            marker_color="#2f9f63",
            marker_theme="games",
        )

        monkeypatch.setattr(tasks_model, "get_database", lambda: database)
        model = tasks_model.TasksModel()

        direct_result = model.apply_task_property_to_children(parent.id, "marker_color", parent.marker_color)
        assert direct_result.updated_count == 1
        assert model.task_by_id(child.id).marker_color == parent.marker_color
        assert model.task_by_id(grandchild.id).marker_color == "#2f9f63"

        for property_name, value in (
            ("project_id", project_parent.id),
            ("priority", parent.priority),
            ("marker_theme", parent.marker_theme),
            ("day", parent.day),
            ("time_text", parent.time_text),
        ):
            result = model.apply_task_property_to_children(parent.id, property_name, value, recursive=True)
            assert result.property_label == TASK_PROPAGATABLE_FIELDS[property_name]
            assert result.error_count == 0

        for task_id in (child.id, grandchild.id):
            task = model.task_by_id(task_id)
            assert task.project_id == project_parent.id
            assert task.priority == parent.priority
            assert task.marker_theme == parent.marker_theme
            assert task.day == parent.day
            assert task.time_text == parent.time_text
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_model_reports_missing_children(monkeypatch, unique_temp_path) -> None:
    db_path = unique_temp_path("task_property_no_children", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Parent",
            description="",
            day=date(2026, 5, 26),
            time_text="",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_model, "get_database", lambda: database)
        model = tasks_model.TasksModel()

        result = model.apply_task_property_to_children(task.id, "time_text", "", recursive=True)

        assert result.target_count == 0
        assert result.updated_count == 0
        assert result.error_count == 0
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_edit_dialog_builds_property_input_groups(monkeypatch, unique_temp_path) -> None:
    app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_property_input_groups", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        parent = database.create_task(
            title="Parent",
            description="",
            day=date(2026, 5, 26),
            time_text="18:30",
            priority="High",
        )
        database.create_task(
            title="Child",
            description="",
            day=date(2026, 5, 27),
            time_text="09:00",
            priority="Medium",
            parent_id=parent.id,
        )
        monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)

        dialog = task_edit_dialog.TaskEditDialog(parent)
        dialog.show()
        app.processEvents()

        assert set(dialog.property_groups) == set(TASK_PROPAGATABLE_FIELDS)
        for group in dialog.property_groups.values():
            assert group.menu_button.isVisible()
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
