from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication

from mindnavigator.storage import Database
from mindnavigator.workspaces import tasks_workspace
from mindnavigator.workspaces.tasks_workspace import TaskRoles


def _find_task_row(model: tasks_workspace.TasksModel, task_id: int) -> int:
    for row in range(model.rowCount()):
        index = model.index(row, 0)
        if index.data(TaskRoles.RowType) != "task":
            continue
        if index.data(TaskRoles.TaskId) == task_id:
            return row
    return -1


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
