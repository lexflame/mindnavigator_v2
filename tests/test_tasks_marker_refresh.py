from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QCoreApplication
from PySide6.QtCore import QRect
from PySide6.QtCore import QTime
from PySide6.QtGui import QColor
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication

from mindnavigator.storage import Database
from mindnavigator.workspaces import tasks as tasks_workspace
from mindnavigator.workspaces.tasks import (
    TaskRoles,
    blend_task_row_background,
    format_task_list_title,
    is_marker_only_task_update,
    should_show_today_badge,
)

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


def test_format_task_list_title_prefixes_valid_id_and_falls_back_for_invalid_id() -> None:
    assert format_task_list_title(42, "Проверить релиз") == "MN-42: Проверить релиз"
    assert format_task_list_title("bad", "Проверить релиз") == "Проверить релиз"
    assert format_task_list_title(None, "") == "Без названия"


def test_should_show_today_badge_detects_current_day() -> None:
    assert should_show_today_badge(date.today()) is True
    assert should_show_today_badge(date.today() - timedelta(days=1)) is False


def test_header_quick_rect_reserves_space_for_today_badge() -> None:
    _app = QApplication.instance() or QApplication([])
    delegate = tasks_workspace.TasksItemDelegate()
    row_rect = QRect(0, 0, 1000, delegate.HEADER_H)
    header_text = delegate.format_header(date.today())

    base_rect = delegate._header_quick_rect(row_rect, header_text, include_today_badge=False)
    with_badge_rect = delegate._header_quick_rect(row_rect, header_text, include_today_badge=True)

    metrics = QFontMetrics(delegate._font_header)
    today_width = metrics.horizontalAdvance("СЕГОДНЯ")

    assert with_badge_rect.left() > base_rect.left()
    assert (with_badge_rect.left() - base_rect.left()) >= today_width


def test_tasks_model_marker_update_emits_data_changed(monkeypatch, unique_temp_path) -> None:
    _app = QCoreApplication.instance() or QCoreApplication([])
    db_path = unique_temp_path("tasks_marker_refresh", ".sqlite3")
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


def test_tasks_model_display_role_shows_prefixed_task_number(monkeypatch, unique_temp_path) -> None:
    _app = QCoreApplication.instance() or QCoreApplication([])
    db_path = unique_temp_path("tasks_title_prefix", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_task(
            title="Проверить релиз",
            description="",
            day=date(2026, 3, 2),
            time_text="",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()

        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if index.data(TaskRoles.RowType) != "task":
                continue
            if index.data(TaskRoles.TaskId) == created.id:
                assert index.data() == f"MN-{created.id}: Проверить релиз"
                assert index.data(TaskRoles.Title) == "Проверить релиз"
                break
        else:
            raise AssertionError("Task row was not found in the model.")
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_get_selection_is_safe_before_list_init() -> None:
    workspace = tasks_workspace.TasksWorkspace.__new__(tasks_workspace.TasksWorkspace)
    workspace.list = None
    workspace.model = None

    assert tasks_workspace.TasksWorkspace.get_selection(workspace) == []


def test_task_quick_buttons_use_full_row_height_and_icon() -> None:
    _app = QApplication.instance() or QApplication([])
    delegate = tasks_workspace.TasksItemDelegate()

    header_row = QRect(0, 0, 1000, delegate.HEADER_H)
    header_text = delegate.format_header(date.today())
    header_quick = delegate._header_quick_rect(header_row, header_text, include_today_badge=False)
    assert header_quick.top() == header_row.top()
    assert header_quick.height() == header_row.height()

    task_row = QRect(0, 0, 1000, delegate.ROW_H)
    layout = delegate._row_layout(task_row, depth=0, has_subtasks=True)
    task_quick = delegate._task_quick_rect(layout, task_row)
    assert task_quick.top() == task_row.top()
    assert task_quick.height() == task_row.height()
    assert hasattr(delegate, "_icon_quick_add")


def test_marker_theme_asset_pixmap_loads_from_project_assets() -> None:
    _app = QApplication.instance() or QApplication([])
    delegate = tasks_workspace.TasksItemDelegate()

    pixmap = delegate._marker_theme_asset_pixmap("movies")

    assert pixmap.isNull() is False


def test_marker_theme_overlay_rect_spans_full_task_row_width() -> None:
    _app = QApplication.instance() or QApplication([])
    delegate = tasks_workspace.TasksItemDelegate()
    task_row = QRect(0, 0, 1000, delegate.ROW_H)

    overlay_rect = delegate._marker_theme_overlay_rect(task_row)

    assert overlay_rect.left() == task_row.left() + 1
    assert overlay_rect.right() == task_row.right() - 1
    assert overlay_rect.height() == task_row.height() - 2


def test_tasks_model_expand_subtasks_tree_by_row_expands_nested_branch(monkeypatch, unique_temp_path) -> None:
    _app = QCoreApplication.instance() or QCoreApplication([])
    db_path = unique_temp_path("tasks_expand_tree", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        child = database.create_task(
            title="Child",
            description="",
            day=date(2026, 3, 6),
            time_text="09:30",
            priority="Medium",
            parent_id=root.id,
        )
        _grand = database.create_task(
            title="Grand",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="Medium",
            parent_id=child.id,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()

        root_row = -1
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if index.data(TaskRoles.RowType) != "task":
                continue
            if index.data(TaskRoles.TaskId) == root.id:
                root_row = row
                break
        assert root_row >= 0
        assert root.id in model._collapsed_subtask_ids
        assert child.id in model._collapsed_subtask_ids

        model.expand_subtasks_tree_by_row(root_row)

        assert root.id not in model._collapsed_subtask_ids
        assert child.id not in model._collapsed_subtask_ids
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_quick_create_defaults_to_enabled_time_plus_one_hour(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_quick_create_defaults", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = tasks_workspace.TasksWorkspace()
    try:
        assert workspace.new_time_toggle is not None
        assert workspace.new_time is not None
        assert workspace.new_time_toggle.isChecked() is True
        assert workspace.new_time.isEnabled() is True

        expected = QTime.currentTime().addSecs(3600)
        actual = workspace.new_time.time()
        diff = abs(actual.secsTo(expected))
        diff = min(diff, 24 * 3600 - diff)
        assert diff <= 120
    finally:
        workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
