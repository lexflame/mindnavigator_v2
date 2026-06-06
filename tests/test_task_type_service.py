from datetime import date

from mindnavigator.services import TaskTypeService, TaskTypeUpdateValues
from mindnavigator.storage import Database


def _update_values(task, **changes) -> TaskTypeUpdateValues:
    values = {
        "title": task.title,
        "description": task.description,
        "day": task.day,
        "time_text": task.time_text,
        "priority": task.priority,
        "importance": task.importance,
        "done": task.done,
        "parent_id": task.parent_id,
        "recurrence_kind": task.recurrence_kind,
        "recurrence_interval": task.recurrence_interval,
        "plan_order": task.plan_order,
        "marker_color": task.marker_color,
        "marker_theme": task.marker_theme,
    }
    values.update(changes)
    return TaskTypeUpdateValues(**values)


def test_task_type_service_applies_project_type_to_task_tree(unique_temp_path) -> None:
    db_path = unique_temp_path("task_type_service_project", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project("Area", "Typed project", date(2026, 6, 7), "Medium")
        task_type = database.add_project_task_type(
            project_id=project.id,
            title="Development",
            value="DEV",
            color_marker="#20f5d2",
            theme_marker="debug",
            priority="High",
            importance=5,
            is_plan_task=True,
        )
        root = database.create_task("Root", "", date(2026, 6, 7), "", "Low")
        child = database.create_task("Child", "", date(2026, 6, 7), "", "Low", parent_id=root.id)

        updated = TaskTypeService(database).apply_type(
            task_id=root.id,
            project_id=project.id,
            project_task_type_id=task_type.id,
            is_plan_task=False,
            values=_update_values(root),
        )

        assert updated.project_task_type_id == task_type.id
        tasks = {task.id: task for task in database.fetch_tasks()}
        for task_id in (root.id, child.id):
            assert tasks[task_id].project_id == project.id
            assert tasks[task_id].project_task_type_id == task_type.id
            assert tasks[task_id].priority == "High"
            assert tasks[task_id].importance == 5
            assert tasks[task_id].is_plan_task is True
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_type_service_restores_builtin_type_for_task_tree(unique_temp_path) -> None:
    db_path = unique_temp_path("task_type_service_builtin", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project("Area", "Typed project", date(2026, 6, 7), "Medium")
        task_type = database.add_project_task_type(
            project_id=project.id,
            title="Development",
            value="DEV",
            priority="High",
            importance=5,
            is_plan_task=True,
        )
        root = database.create_task(
            "Root",
            "",
            date(2026, 6, 7),
            "",
            "Low",
            project_id=project.id,
            project_task_type_id=task_type.id,
        )
        child = database.create_task("Child", "", date(2026, 6, 7), "", "Low", parent_id=root.id)

        TaskTypeService(database).apply_type(
            task_id=root.id,
            project_id=project.id,
            project_task_type_id=None,
            is_plan_task=False,
            values=_update_values(root, priority="Low", importance=2),
        )

        tasks = {task.id: task for task in database.fetch_tasks()}
        for task_id in (root.id, child.id):
            assert tasks[task_id].project_id == project.id
            assert tasks[task_id].project_task_type_id is None
            assert tasks[task_id].priority == "Low"
            assert tasks[task_id].importance == 2
            assert tasks[task_id].is_plan_task is False
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
