from dataclasses import dataclass
from datetime import date

from mindnavigator.storage import Database
from mindnavigator.workspaces.tasks.task_advanced_filters import TaskAdvancedFilterState
from mindnavigator.workspaces.tasks import tasks_model


@dataclass
class _Task:
    id: int
    project_id: int | None = None
    parent_id: int | None = None
    project_task_type_id: int | None = None


def test_advanced_filters_match_each_supported_dimension() -> None:
    task = _Task(id=7, project_id=None, parent_id=3, project_task_type_id=11)

    assert TaskAdvancedFilterState(task_type=11).matches(task, set())
    assert not TaskAdvancedFilterState(task_type="none").matches(task, set())
    assert TaskAdvancedFilterState(links="linked").matches(task, {7})
    assert not TaskAdvancedFilterState(links="unlinked").matches(task, {7})
    assert TaskAdvancedFilterState(project="without").matches(task, set())
    assert TaskAdvancedFilterState(nesting="nested").matches(task, set())
    assert not TaskAdvancedFilterState(nesting="root").matches(task, set())


def test_advanced_filters_combine_with_and_semantics() -> None:
    state = TaskAdvancedFilterState(
        task_type="none",
        links="unlinked",
        project="without",
        nesting="root",
    )

    assert state.matches(_Task(id=1), set())
    assert not state.matches(_Task(id=2, project_id=4), set())


def test_tasks_model_applies_advanced_filters_from_database(monkeypatch, unique_temp_path) -> None:
    db_path = unique_temp_path("task_advanced_filters", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project("Area", "Project", date(2026, 6, 7), "Medium")
        task_type = database.add_project_task_type(project.id, "Research")
        typed = database.create_task(
            "Typed", "", date(2026, 6, 7), "09:00", "Medium",
            project_id=project.id, project_task_type_id=task_type.id,
        )
        root = database.create_task("Root", "", date(2026, 6, 7), "10:00", "Medium")
        child = database.create_task(
            "Child", "", date(2026, 6, 7), "11:00", "Medium", parent_id=root.id,
        )
        database.add_task_attachment(child.id, "task", typed.id)
        monkeypatch.setattr(tasks_model, "get_database", lambda: database)
        model = tasks_model.TasksModel()

        model.set_advanced_filters(task_type=task_type.id)
        assert [task.id for task in model._collect_base_tasks()] == [typed.id]

        model.set_advanced_filters(links="linked", nesting="nested")
        assert [task.id for task in model._collect_base_tasks()] == [child.id]

        model.set_advanced_filters(task_type="none", project="without", nesting="root")
        filtered_ids = {task.id for task in model._collect_base_tasks()}
        assert root.id in filtered_ids
        assert typed.id not in filtered_ids
        assert child.id not in filtered_ids
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
