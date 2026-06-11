from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from mindnavigator.storage import DEFERRED_PRIORITY, Database
from mindnavigator.workspaces import tasks as tasks_workspace
from mindnavigator.workspaces.tasks import TaskRoles


def _visible_task_ids(model: tasks_workspace.TasksModel) -> list[int]:
    return [
        int(model.index(row, 0).data(TaskRoles.TaskId))
        for row in range(model.rowCount())
        if model.index(row, 0).data(TaskRoles.RowType) == "task"
    ]


def test_tasks_all_mode_shows_active_and_deferred_tasks_in_date_priority_order(
    monkeypatch, unique_temp_path
) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_all_mode_contract", ".sqlite3")
    database = Database(path=db_path)
    try:
        deferred = database.create_task(
            "Deferred", "", date(2026, 3, 7), "12:00", DEFERRED_PRIORITY
        )
        low = database.create_task("Low", "", date(2026, 3, 8), "09:00", "Low")
        high = database.create_task("High", "", date(2026, 3, 8), "11:00", "High")
        parent = database.create_task("Parent", "", date(2026, 3, 9), "10:00", "Medium")
        child = database.create_task(
            "Child", "", date(2026, 3, 10), "08:00", "High", parent_id=parent.id
        )
        completed = database.create_task("Completed", "", date(2026, 3, 6), "08:00", "High")
        database.update_task(
            completed.id,
            title=completed.title,
            description=completed.description,
            day=completed.day,
            time_text=completed.time_text,
            priority=completed.priority,
            done=True,
            project_id=completed.project_id,
            parent_id=completed.parent_id,
            recurrence_kind=completed.recurrence_kind,
            recurrence_interval=completed.recurrence_interval,
            marker_color=completed.marker_color,
            marker_theme=completed.marker_theme,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)

        model = tasks_workspace.TasksModel()
        model.set_filter_mode("Все")
        model.set_focus_day(None)

        contract_ids = {deferred.id, high.id, low.id, parent.id, child.id, completed.id}
        visible_contract_ids = [
            task_id for task_id in _visible_task_ids(model) if task_id in contract_ids
        ]
        assert visible_contract_ids == [deferred.id, high.id, low.id, parent.id]

        parent_row = model.row_for_task_id(parent.id)
        model.expand_subtasks_tree_by_row(parent_row)
        visible_contract_ids = [
            task_id for task_id in _visible_task_ids(model) if task_id in contract_ids
        ]
        assert visible_contract_ids == [deferred.id, high.id, low.id, parent.id, child.id]

        child_index = model.index(model.row_for_task_id(child.id), 0)
        assert child_index.data(TaskRoles.SubtaskDepth) == 1
        assert child_index.data(TaskRoles.DisplayTime) == "08:00 · 2026-03-10"
        assert child_index.data(Qt.ItemDataRole.DisplayRole).endswith("Child")
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_all_mode_clears_day_filter_and_hides_navigation(
    monkeypatch, unique_temp_path
) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_all_mode_navigation", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 8)

        workspace._apply_tab("all", focus_day=workspace._focus_day)

        assert workspace.model.filter_mode() == "Все"
        assert workspace.model._focus_day is None
        assert workspace.btn_prev_day.isHidden()
        assert workspace.lbl_day.isHidden()
        assert workspace.btn_next_day.isHidden()

        workspace._apply_tab("plan")
        assert not workspace.btn_prev_day.isHidden()
        assert not workspace.lbl_day.isHidden()
        assert not workspace.btn_next_day.isHidden()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
