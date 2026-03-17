from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication

from mindnavigator.storage import (
    BOARD_COLUMN_COMPLETED,
    BOARD_COLUMN_DEFERRED,
    BOARD_COLUMN_IN_PROGRESS,
    BOARD_COLUMN_QUEUE,
    DEFERRED_PRIORITY,
    Database,
)
from mindnavigator.workspaces.tasks import task_edit_dialog
from mindnavigator.workspaces.tasks.task_row import TaskRow
from mindnavigator.workspaces import tasks as tasks_workspace
from mindnavigator.workspaces.tasks import TaskRoles


def _find_task_row(model: tasks_workspace.TasksModel, task_id: int) -> int:
    for row in range(model.rowCount()):
        index = model.index(row, 0)
        if index.data(TaskRoles.RowType) != "task":
            continue
        if index.data(TaskRoles.TaskId) == task_id:
            return row
    return -1


def _create_completed_task(database: Database, title: str, completion_day: date, priority: str = "Medium") -> int:
    created = database.create_task(
        title=title,
        description="",
        day=completion_day,
        time_text="",
        priority=priority,
    )
    database.update_task(
        created.id,
        title=created.title,
        description=created.description,
        day=completion_day,
        time_text=created.time_text,
        priority=priority,
        done=True,
        project_id=created.project_id,
        parent_id=created.parent_id,
        recurrence_kind=created.recurrence_kind,
        recurrence_interval=created.recurrence_interval,
        marker_color=created.marker_color,
        marker_theme=created.marker_theme,
    )
    return created.id


def test_tasks_model_cycles_priority_including_deferred(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_priority_cycle", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_task(
            title="Priority cycle",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Low",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Medium"

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "High"

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_task_row(model, created.id)
        assert row_idx == -1
        model.set_filter_mode("Отложенные")
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Отложенная"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_model_steps_priority_up_and_down_without_wrap(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_priority_step", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_task(
            title="Priority step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0

        model.step_priority_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "High"

        model.step_priority_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "High"

        model.step_priority_by_row(row_idx, -1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Medium"

        model.step_priority_by_row(row_idx, -1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Low"

        model.step_priority_by_row(row_idx, -1)
        model.set_filter_mode("Отложенные")
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Отложенная"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_model_steps_board_stage_up_and_down_without_wrap(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_stage_step", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_task(
            title="Board stage step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_QUEUE

        model.step_board_column_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_IN_PROGRESS

        model.step_board_column_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_COMPLETED

        model.step_board_column_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_COMPLETED

        model.step_board_column_by_row(row_idx, -1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_IN_PROGRESS

        model.step_board_column_by_row(row_idx, -1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_QUEUE

        model.step_board_column_by_row(row_idx, -1)
        model.set_filter_mode("Отложенные")
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_DEFERRED
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_delegate_priority_block_orders_icon_controls_and_stage_text() -> None:
    delegate = tasks_workspace.TasksItemDelegate()
    rects = delegate._priority_control_rects(tasks_workspace.QRect(0, 0, 220, 30))
    assert rects["icon"].left() < rects["priority_arrows"].left()
    assert rects["priority_arrows"].right() < rects["value"].left()
    assert rects["value"].right() < rects["stage_arrows"].left()


def test_task_priority_pickers_use_high_medium_low_deferred_order(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_priority_picker_order", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)
    workspace = None
    dialog = None
    try:
        workspace = tasks_workspace.TasksWorkspace()
        assert [workspace.new_priority.itemText(idx) for idx in range(workspace.new_priority.count())] == [
            "High",
            "Medium",
            "Low",
            "Отложенная",
        ]
        assert [workspace.cmb_priority.itemText(idx) for idx in range(workspace.cmb_priority.count())] == [
            "Любой",
            "High",
            "Medium",
            "Low",
            "Отложенная",
        ]

        dialog = task_edit_dialog.TaskEditDialog(
            TaskRow(
                id=0,
                day=date(2026, 3, 6),
                time_text="",
                title="Task",
                description="",
                priority="Medium",
                done=False,
            )
        )
        assert [dialog.priority_edit.itemText(idx) for idx in range(dialog.priority_edit.count())] == [
            "High",
            "Medium",
            "Low",
            "Отложенная",
        ]
    finally:
        if dialog is not None:
            dialog.deleteLater()
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_create_dialog_suggests_project_by_title(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_suggest", ".sqlite3")
    database = Database(path=db_path)
    try:
        backend = database.create_project(
            area="Work",
            title="Backend API",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        _personal = database.create_project(
            area="Life",
            title="Personal Home",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)

        dialog = tasks_workspace.TaskCreateDialog()
        try:
            dialog.title_edit.setText("Refactor backend API endpoints")
            QApplication.processEvents()
            assert dialog.project_edit.currentData() == backend.id
        finally:
            dialog.deleteLater()
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_switches_board_and_dash_modes(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_dash_modes", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = tasks_workspace.TasksWorkspace()
    try:
        assert workspace.btn_gantt.text() == "GANTT"
        assert workspace.btn_board.text() == "BOARD"
        assert workspace.btn_dash.text() == "DASH"
        assert workspace.btn_gantt.parent() is workspace.toolbar_row
        assert workspace.btn_board.parent() is workspace.toolbar_row
        assert workspace.btn_dash.parent() is workspace.toolbar_row

        toolbar_texts = [
            widget.text()
            for idx in range(workspace.toolbar_layout.count())
            if (item := workspace.toolbar_layout.itemAt(idx)) is not None
            if (widget := item.widget()) is not None
            if isinstance(widget, tasks_workspace.QToolButton)
        ]
        assert toolbar_texts[:3] == ["GANTT", "BOARD", "DASH"]

        workspace.btn_board.setChecked(True)
        assert workspace._board_mode is True
        assert workspace._dash_mode is False
        assert workspace.content_stack.currentWidget() is workspace.board_page

        workspace.btn_dash.setChecked(True)
        assert workspace._board_mode is False
        assert workspace._dash_mode is True
        assert workspace.content_stack.currentWidget() is workspace.dash_page

        workspace.btn_dash.setChecked(False)
        assert workspace._gantt_mode is False
        assert workspace._board_mode is False
        assert workspace._dash_mode is False
        assert workspace.content_stack.currentWidget() is workspace.list
    finally:
        workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_board_uses_kanban_columns_in_expected_order(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_columns_order", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = tasks_workspace.TasksWorkspace()
    try:
        assert list(workspace.board_columns.keys()) == [
            BOARD_COLUMN_DEFERRED,
            BOARD_COLUMN_QUEUE,
            BOARD_COLUMN_IN_PROGRESS,
            BOARD_COLUMN_COMPLETED,
        ]
    finally:
        workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_project_quick_links_show_top_five(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_quick_links", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        projects = []
        for idx, count in enumerate([6, 5, 4, 3, 2, 1], start=1):
            project = database.create_project(
                area="Area",
                title=f"Project {idx}",
                updated=date(2026, 3, 6),
                priority="Medium",
            )
            projects.append((project, count))
        for project, count in projects:
            for task_idx in range(count):
                database.create_task(
                    title=f"T{project.id}-{task_idx}",
                    description="",
                    day=date(2026, 3, 6),
                    time_text="09:00",
                    priority="Medium",
                    project_id=project.id,
                )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._refresh_project_quick_links()
        labels = [button.text() for button in workspace._project_quick_link_buttons]

        assert len(labels) == 5
        assert labels[0].endswith("(6)")
        assert labels[-1].endswith("(2)")
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_project_quick_link_click_toggles_filter(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_quick_link_toggle", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        project = database.create_project(
            area="Area",
            title="Pinned Project",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        database.create_task(
            title="Pinned task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
            project_id=project.id,
        )
        database.create_task(
            title="Unfiltered task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="Medium",
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._refresh_project_quick_links()
        assert len(workspace._project_quick_link_buttons) == 1
        quick_link = workspace._project_quick_link_buttons[0]

        quick_link.click()
        QApplication.processEvents()
        assert workspace.model._project_filter_id == project.id
        assert quick_link.isChecked() is True

        quick_link.click()
        QApplication.processEvents()
        assert workspace.model._project_filter_id is None
        assert quick_link.isChecked() is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_project_filter_can_be_cleared_after_mode_switch(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_quick_link_clear_button", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        project = database.create_project(
            area="Area",
            title="CODEX",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        database.create_task(
            title="CODEX task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
            project_id=project.id,
        )
        database.create_task(
            title="Common task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="Medium",
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace.set_filter("tab", "all")
        workspace._refresh_project_quick_links()
        quick_link = workspace._project_quick_link_buttons[0]

        quick_link.click()
        QApplication.processEvents()
        assert workspace.model._project_filter_id == project.id
        assert workspace._project_filter_clear_button is not None
        assert workspace._project_filter_clear_button.isHidden() is False

        workspace.set_filter("tab", "plan")
        QApplication.processEvents()
        assert workspace.model._project_filter_id == project.id
        assert workspace._project_filter_clear_button.isHidden() is False

        workspace._project_filter_clear_button.click()
        QApplication.processEvents()
        assert workspace.model._project_filter_id is None
        assert workspace._project_filter_clear_button.isHidden() is True
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_project_clear_button_survives_refresh_event_cycle(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_clear_button_lifetime", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        project = database.create_project(
            area="Area",
            title="Live Project",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        database.create_task(
            title="Live task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
            project_id=project.id,
        )

        workspace = tasks_workspace.TasksWorkspace()
        QApplication.processEvents()
        workspace._refresh_project_quick_links()
        QApplication.processEvents()

        workspace.set_filter("tab", "all")
        QApplication.processEvents()
        workspace._project_quick_link_buttons[0].click()
        QApplication.processEvents()

        assert workspace.model._project_filter_id == project.id
        assert workspace._project_filter_clear_button is not None
        assert workspace._project_filter_clear_button.isHidden() is False

        workspace.set_filter("tab", "plan")
        QApplication.processEvents()
        assert workspace._project_filter_clear_button.isHidden() is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_board_defaults_to_queue_and_completed_is_not_done(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_default_and_completed", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        queued_task = database.create_task(
            title="Queued task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        deferred_task = database.create_task(
            title="Deferred task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority=DEFERRED_PRIORITY,
        )

        fetched = {task.id: task for task in database.fetch_tasks()}
        assert fetched[queued_task.id].board_column == BOARD_COLUMN_QUEUE
        assert fetched[deferred_task.id].board_column == BOARD_COLUMN_DEFERRED

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._move_task_to_board_column(queued_task.id, BOARD_COLUMN_COMPLETED)

        updated = {task.id: task for task in database.fetch_tasks()}[queued_task.id]
        assert updated.board_column == BOARD_COLUMN_COMPLETED
        assert updated.done is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_board_move_to_deferred_and_in_progress_persists(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_move_persists", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        task = database.create_task(
            title="Board task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._move_task_to_board_column(task.id, BOARD_COLUMN_DEFERRED)
        deferred_state = {item.id: item for item in database.fetch_tasks()}[task.id]
        assert deferred_state.board_column == BOARD_COLUMN_DEFERRED
        assert deferred_state.priority == DEFERRED_PRIORITY

        workspace._move_task_to_board_column(task.id, BOARD_COLUMN_IN_PROGRESS)
        active_state = {item.id: item for item in database.fetch_tasks()}[task.id]
        assert active_state.board_column == BOARD_COLUMN_IN_PROGRESS
        assert active_state.priority == "Medium"
        assert active_state.done is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_board_refresh_groups_tasks_by_board_column(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_groups", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        queue_task = database.create_task(
            title="Queue task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        in_progress_task = database.create_task(
            title="In progress task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="High",
        )
        completed_task = database.create_task(
            title="Completed task",
            description="",
            day=date(2026, 3, 6),
            time_text="11:00",
            priority="Low",
        )
        deferred_task = database.create_task(
            title="Deferred task",
            description="",
            day=date(2026, 3, 6),
            time_text="12:00",
            priority=DEFERRED_PRIORITY,
        )
        database.set_task_board_column(in_progress_task.id, BOARD_COLUMN_IN_PROGRESS)
        database.set_task_board_column(completed_task.id, BOARD_COLUMN_COMPLETED)

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._refresh_board_day()

        assert workspace.board_columns[BOARD_COLUMN_QUEUE].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_IN_PROGRESS].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_COMPLETED].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_DEFERRED].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_QUEUE].item(0).data(tasks_workspace.Qt.ItemDataRole.UserRole) == queue_task.id
        assert workspace.board_columns[BOARD_COLUMN_DEFERRED].item(0).data(tasks_workspace.Qt.ItemDataRole.UserRole) == deferred_task.id
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_flashes_task_after_move_to_tomorrow(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_flash_after_tomorrow_move", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        task = database.create_task(
            title="Tomorrow move task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )

        workspace = tasks_workspace.TasksWorkspace()
        moved = workspace.model.move_task_to_day(task.id, date(2026, 3, 7))
        QApplication.processEvents()

        assert moved is True
        assert task.id in workspace.delegate._task_flash_progress
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_flashes_task_after_drag_and_drop(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_flash_after_drag_drop", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        moved_task = database.create_task(
            title="Drag source",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        database.create_task(
            title="Next day anchor",
            description="",
            day=date(2026, 3, 7),
            time_text="10:00",
            priority="Medium",
        )

        workspace = tasks_workspace.TasksWorkspace()
        source_row = _find_task_row(workspace.model, moved_task.id)
        assert source_row >= 0
        source_index = workspace.model.index(source_row, 0)
        mime_data = workspace.model.mimeData([source_index])
        header_index = next(
            (
                workspace.model.index(row, 0)
                for row in range(workspace.model.rowCount())
                if workspace.model.index(row, 0).data(TaskRoles.RowType) == "header"
                and workspace.model.index(row, 0).data(TaskRoles.Day) == date(2026, 3, 7)
            ),
            None,
        )
        assert header_index is not None

        dropped = workspace.model.dropMimeData(
            mime_data,
            tasks_workspace.Qt.DropAction.MoveAction,
            -1,
            0,
            header_index,
        )
        QApplication.processEvents()

        assert dropped is True
        assert moved_task.id in workspace.delegate._task_flash_progress
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_dash_shows_classic_entity_statistics(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_dash_classic_stats", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        project = database.create_project(
            area="Area",
            title="Dash Project",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        database.create_task(
            title="Dash task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            project_id=project.id,
        )
        map_item = database.create_map(
            title="Dash Map",
            description="",
            project=project.title,
            tiles_path="",
            tiles_h=10,
            tiles_w=10,
        )
        database.upsert_map_marker(
            marker_id=101,
            map_id=map_item.id,
            name="Dash Marker",
            x=10.0,
            y=20.0,
            color="#ffffff",
            marker_type="pin",
            size=16.0,
        )
        database.create_object(
            title="Dash Object",
            catalog="Catalog",
            object_type="Type",
            status="Active",
            description="",
        )
        database.create_note(
            title="Dash Note",
            preview="Body",
            tags=[],
            project=project.title,
        )
        expected_totals = (
            len(database.fetch_tasks()),
            len(database.fetch_projects()),
            len(database.fetch_maps()),
            len(database.fetch_map_markers()),
            len(database.fetch_objects()),
            len(database.fetch_notes()),
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._refresh_dash_day()
        QApplication.processEvents()

        summary = workspace.dash_summary_label.text()
        assert f"DASH на 2026-03-06: диаграммы пересчитаны и заполнены заново." in summary
        assert "На 2026-03-06: активных задач 1, High 1, Medium 0, Low 0, Отложенных 0." in summary
        assert "Результативность: нет завершенных задач для сравнения." in summary
        assert workspace.dash_bar_chart is not None
        assert workspace.dash_pie_chart is not None
        assert workspace.dash_pulse_chart is not None
        assert [(label, value) for label, value, _ in workspace.dash_bar_chart._items] == [
            ("Задачи", expected_totals[0]),
            ("Проекты", expected_totals[1]),
            ("Карты", expected_totals[2]),
            ("Метки", expected_totals[3]),
            ("Объекты", expected_totals[4]),
            ("Заметки", expected_totals[5]),
        ]
        assert [(label, value) for label, value, _ in workspace.dash_pie_chart._items] == [
            ("Задачи", expected_totals[0]),
            ("Проекты", expected_totals[1]),
            ("Карты", expected_totals[2]),
            ("Метки", expected_totals[3]),
            ("Объекты", expected_totals[4]),
            ("Заметки", expected_totals[5]),
        ]
        assert [(label, value) for label, value, _ in workspace.dash_pulse_chart._items] == [
            ("01.03", 0),
            ("02.03", 0),
            ("03.03", 0),
            ("04.03", 0),
            ("05.03", 0),
            ("06.03", 0),
        ]
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_dash_shows_resultativity_against_previous_periods(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_dash_resultativity", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        _create_completed_task(database, "Prev 1", date(2026, 3, 1))
        _create_completed_task(database, "Prev 2", date(2026, 3, 2))
        _create_completed_task(database, "Prev 3", date(2026, 3, 4))
        _create_completed_task(database, "Recent 1", date(2026, 3, 5))
        _create_completed_task(database, "Recent 2", date(2026, 3, 6))
        _create_completed_task(database, "Recent 3", date(2026, 3, 6), priority="High")

        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._refresh_dash_day()
        QApplication.processEvents()

        summary = workspace.dash_summary_label.text()
        assert (
            "Результативность: 2.00x к прошлому темпу "
            "(импульс за последние 2 дня 3; база прошлых периодов 1.50 на 2 дня)."
        ) in summary
        assert workspace.dash_pulse_chart is not None
        assert [(label, value) for label, value, _ in workspace.dash_pulse_chart._items] == [
            ("01.03", 1),
            ("02.03", 1),
            ("03.03", 0),
            ("04.03", 1),
            ("05.03", 1),
            ("06.03", 2),
        ]
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_delegate_attachment_display_name_for_note(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_attachment_menu_note", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Task with attachment",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        note = database.create_note(
            title="Attached note",
            preview="Body",
            tags=[],
            project="Area",
        )
        database.add_task_attachment(task.id, "note", note.id)
        attachment = database.fetch_task_attachments(task.id)[0]
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        delegate = tasks_workspace.TasksItemDelegate()
        assert delegate._attachment_display_name(attachment) == "Attached note"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
