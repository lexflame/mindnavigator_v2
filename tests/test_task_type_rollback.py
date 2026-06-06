from datetime import date

import pytest

from mindnavigator.services import TaskTypeService, TaskTypeUpdateValues
from mindnavigator.storage import Database


def _values(task, **changes) -> TaskTypeUpdateValues:
    payload = {
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
    payload.update(changes)
    return TaskTypeUpdateValues(**payload)


def _task_state(database: Database, *task_ids: int) -> dict[int, tuple[object, ...]]:
    tasks = {task.id: task for task in database.fetch_tasks()}
    return {
        task_id: (
            tasks[task_id].project_id,
            tasks[task_id].project_task_type_id,
            tasks[task_id].priority,
            tasks[task_id].importance,
            tasks[task_id].is_plan_task,
            tasks[task_id].marker_color,
            tasks[task_id].marker_theme,
        )
        for task_id in task_ids
    }


def test_project_task_type_cascade_rolls_back_root_and_descendants(monkeypatch, unique_temp_path) -> None:
    db_path = unique_temp_path("project_type_rollback", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project("Area", "Project", date(2026, 6, 7), "Medium")
        task_type = database.add_project_task_type(
            project_id=project.id,
            title="Development",
            value="DEV",
            priority="High",
            importance=5,
            is_plan_task=True,
        )
        root = database.create_task("Root", "", date(2026, 6, 7), "", "Low")
        child = database.create_task("Child", "", date(2026, 6, 7), "", "Medium", parent_id=root.id)
        before = _task_state(database, root.id, child.id)

        def fail_after_partial_cascade(_task_type_id) -> None:
            database._conn.execute("UPDATE tasks SET priority = 'High' WHERE id = ?;", (child.id,))
            raise RuntimeError("injected project type cascade failure")

        monkeypatch.setattr(database, "apply_project_task_type_defaults_to_task_tree", fail_after_partial_cascade)

        with pytest.raises(RuntimeError, match="injected project type cascade failure"):
            TaskTypeService(database).apply_type(
                task_id=root.id,
                project_id=project.id,
                project_task_type_id=task_type.id,
                is_plan_task=False,
                values=_values(root),
            )

        assert _task_state(database, root.id, child.id) == before
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_builtin_task_type_cascade_rolls_back_root_and_descendants(monkeypatch, unique_temp_path) -> None:
    db_path = unique_temp_path("builtin_type_rollback", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project("Area", "Project", date(2026, 6, 7), "Medium")
        task_type = database.add_project_task_type(
            project_id=project.id,
            title="Development",
            value="DEV",
            priority="High",
            importance=5,
            is_plan_task=True,
        )
        root = database.create_task("Root", "", date(2026, 6, 7), "", "Low", project_id=project.id)
        child = database.create_task("Child", "", date(2026, 6, 7), "", "Medium", parent_id=root.id)
        service = TaskTypeService(database)
        service.apply_type(
            task_id=root.id,
            project_id=project.id,
            project_task_type_id=task_type.id,
            is_plan_task=False,
            values=_values(root),
        )
        typed_root = next(task for task in database.fetch_tasks() if task.id == root.id)
        before = _task_state(database, root.id, child.id)

        def fail_after_partial_cascade(_task_id, **_kwargs) -> None:
            database._conn.execute("UPDATE tasks SET priority = 'Low' WHERE id = ?;", (child.id,))
            raise RuntimeError("injected builtin type cascade failure")

        monkeypatch.setattr(database, "apply_task_builtin_type_to_descendants", fail_after_partial_cascade)

        with pytest.raises(RuntimeError, match="injected builtin type cascade failure"):
            service.apply_type(
                task_id=root.id,
                project_id=project.id,
                project_task_type_id=None,
                is_plan_task=False,
                values=_values(typed_root, priority="Low", importance=2),
            )

        assert _task_state(database, root.id, child.id) == before
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
