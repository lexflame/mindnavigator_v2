from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor

from mindnavigator.storage import Database
from mindnavigator.workspaces import tasks_workspace
from mindnavigator.workspaces.tasks_workspace import (
    TaskRoles,
    blend_task_row_background,
    is_marker_only_task_update,
)


def _new_temp_db_path(prefix: str) -> Path:
    base_dir = Path.cwd() / ".pytest_dir" / "tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{prefix}_{uuid4().hex}.sqlite3"


def test_is_marker_only_task_update_detects_marker_change() -> None:
    base = tasks_workspace.TaskRow(
        id=42,
        day=date(2026, 2, 25),
        time_text="09:00",
        title="Task",
        description="Body",
        priority="Medium",
        done=False,
        marker_color="",
        marker_theme="",
    )
    changed = tasks_workspace.TaskRow(
        id=42,
        day=date(2026, 2, 25),
        time_text="09:00",
        title="Task",
        description="Body",
        priority="Medium",
        done=False,
        marker_color="#2f6edb",
        marker_theme="work",
    )
    title_changed = tasks_workspace.TaskRow(
        id=42,
        day=date(2026, 2, 25),
        time_text="09:00",
        title="Task updated",
        description="Body",
        priority="Medium",
        done=False,
        marker_color="#2f6edb",
        marker_theme="work",
    )

    assert is_marker_only_task_update(base, changed) is True
    assert is_marker_only_task_update(base, title_changed) is False


def test_blend_task_row_background_tints_selected_row() -> None:
    base = QColor("#343844")
    tinted = blend_task_row_background(base, "#2f6edb", selected=True)

    assert tinted != base


def test_tasks_model_marker_update_emits_data_changed(monkeypatch) -> None:
    _app = QCoreApplication.instance() or QCoreApplication([])
    db_path = _new_temp_db_path("tasks_marker_refresh")
    database = Database(path=db_path)
    try:
        created = database.create_task(
            title="Marker refresh",
            description="Task body",
            day=date(2026, 2, 25),
            time_text="09:00",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()

        task_row_idx = -1
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if index.data(TaskRoles.RowType) != "task":
                continue
            if index.data(TaskRoles.TaskId) == created.id:
                task_row_idx = row
                break
        assert task_row_idx >= 0

        row_task = model.task_at_row(task_row_idx)
        assert row_task is not None

        changes: list[list[int]] = []

        def _on_data_changed(_top_left, _bottom_right, roles) -> None:
            changes.append(list(roles))

        model.dataChanged.connect(_on_data_changed)
        model.update_task_by_row(
            task_row_idx,
            title=row_task.title,
            description=row_task.description,
            day=row_task.day,
            time_text=row_task.time_text,
            priority=row_task.priority,
            done=row_task.done,
            project_id=row_task.project_id,
            recurrence_kind=row_task.recurrence_kind,
            recurrence_interval=row_task.recurrence_interval,
            marker_color="#2f6edb",
            marker_theme="work",
        )

        updated_index = model.index(task_row_idx, 0)
        assert (updated_index.data(TaskRoles.MarkerColor) or "") == "#2f6edb"
        assert (updated_index.data(TaskRoles.MarkerTheme) or "") == "work"
        assert any(
            TaskRoles.MarkerColor in role_list and TaskRoles.MarkerTheme in role_list
            for role_list in changes
        )
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_get_selection_is_safe_before_list_init() -> None:
    workspace = tasks_workspace.TasksWorkspace.__new__(tasks_workspace.TasksWorkspace)
    workspace.list = None
    workspace.model = None

    assert tasks_workspace.TasksWorkspace.get_selection(workspace) == []
