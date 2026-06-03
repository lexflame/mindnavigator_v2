from __future__ import annotations

import subprocess
from datetime import date

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from mindnavigator.storage import Database
from mindnavigator.workspaces.projects import project_edit_dialog
from mindnavigator.workspaces import projects as projects_workspace
from mindnavigator.workspaces.projects import ProjectRoles


def _find_project_row(model: projects_workspace.ProjectsModel, project_id: int) -> int:
    for row in range(model.rowCount()):
        index = model.index(row, 0)
        if index.data(ProjectRoles.RowType) != "project":
            continue
        if index.data(ProjectRoles.ProjectId) == project_id:
            return row
    return -1


def test_project_storage_persists_repository_catalog(unique_temp_path) -> None:
    db_path = unique_temp_path("project_repository_catalog", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_project(
            area="Area",
            title="Repo project",
            updated=date(2026, 3, 6),
            priority="Medium",
            repository_catalog="  D:/repo/main  ",
        )
        assert created.repository_catalog == "D:/repo/main"

        updated = database.update_project(
            project_id=created.id,
            area=created.area,
            title=created.title,
            updated=created.updated,
            priority=created.priority,
            archived=created.archived,
            parent_project_id=created.parent_project_id,
            default_task_priority=created.default_task_priority,
            force_recurrence_kind=created.force_recurrence_kind,
            linked_map_id=created.linked_map_id,
            linked_note_id=created.linked_note_id,
            linked_object_id=created.linked_object_id,
            repository_catalog="D:/repo/updated",
            marker_color=created.marker_color,
            marker_theme=created.marker_theme,
        )
        assert updated.repository_catalog == "D:/repo/updated"

        fetched = next(item for item in database.fetch_projects() if item.id == created.id)
        assert fetched.repository_catalog == "D:/repo/updated"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_projects_model_exposes_repository_catalog_role(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_repository_model_role", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_project(
            area="Area",
            title="Repo project",
            updated=date(2026, 3, 6),
            priority="Medium",
            repository_catalog="D:/repo/model",
        )

        monkeypatch.setattr(projects_workspace, "get_database", lambda: database)
        model = projects_workspace.ProjectsModel()
        row_idx = _find_project_row(model, created.id)
        assert row_idx >= 0

        index = model.index(row_idx, 0)
        assert index.data(ProjectRoles.RepositoryCatalog) == "D:/repo/model"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_repository_probe_reads_branch_and_dirty_state(monkeypatch, unique_temp_path) -> None:
    repo_dir = unique_temp_path("probe_repository", "")
    repo_dir.mkdir(parents=True, exist_ok=True)

    def _fake_run(cmd, check, capture_output, text, timeout):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="feature/mn-235\n", stderr="")
        if "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M mindnavigator/storage.py\n", stderr="")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(projects_workspace.subprocess, "run", _fake_run)
    state = projects_workspace.RepositoryProbe().inspect(str(repo_dir))

    assert state.available is True
    assert state.branch_name == "feature/mn-235"
    assert state.has_local_changes is True
    assert state.message == ""


def test_repository_probe_rejects_missing_catalog() -> None:
    state = projects_workspace.RepositoryProbe().inspect("")
    assert state.available is False
    assert state.branch_name == ""
    assert state.message != ""


def test_project_dialog_task_priority_preset_uses_high_medium_low_order(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_default_task_priority_order", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(project_edit_dialog, "get_database", lambda: database)
    dialog = None
    try:
        dialog = project_edit_dialog.ProjectEditDialog()
        assert [dialog.default_task_priority_edit.itemText(idx) for idx in range(dialog.default_task_priority_edit.count())] == [
            "None",
            "High",
            "Medium",
            "Low",
        ]
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_dialog_opens_existing_project_in_preview_mode(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_preview_mode", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(project_edit_dialog, "get_database", lambda: database)
    existing = database.create_project(
        area="SPACE",
        title="MindNavigator v2",
        updated=date(2026, 1, 6),
        priority="High",
    )
    dialog = None
    try:
        dialog = project_edit_dialog.ProjectEditDialog(existing)
        assert dialog._edit_mode is False
        assert dialog.title_edit.isEnabled() is False
        assert dialog.edit_button.isHidden() is False
        assert dialog.save_button.isHidden() is True

        dialog._set_edit_mode(True)
        assert dialog._edit_mode is True
        assert dialog.title_edit.isEnabled() is True
        assert dialog.save_button.isHidden() is False
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_folder_double_click_opens_project_dialog(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_folder_double_click", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        project = database.create_project(
            area="SPACE",
            title="MindNavigator v2",
            updated=date(2026, 1, 6),
            priority="High",
        )
        monkeypatch.setattr(projects_workspace, "get_database", lambda: database)
        workspace = projects_workspace.ProjectsWorkspace()
        row = _find_project_row(workspace.model, project.id)
        assert row >= 0
        index = workspace.model.index(row, 0)
        folder_rect = workspace.delegate.project_folder_rect(workspace.list.visualRect(index))
        click_point = folder_rect.center()
        opened_project_ids: list[int] = []

        def _capture_edit(project_index) -> None:
            value = project_index.data(ProjectRoles.ProjectId)
            if isinstance(value, int):
                opened_project_ids.append(value)

        monkeypatch.setattr(workspace.delegate, "open_project_editor", _capture_edit)
        event = QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            QPointF(float(click_point.x()), float(click_point.y())),
            QPointF(float(click_point.x()), float(click_point.y())),
            QPointF(float(click_point.x()), float(click_point.y())),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        workspace.list.mouseDoubleClickEvent(event)
        assert opened_project_ids == [project.id]
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
