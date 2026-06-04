from __future__ import annotations

import subprocess
from datetime import date

from PySide6.QtCore import QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLineEdit, QStyleOptionViewItem, QToolButton

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


def test_project_custom_task_type_inherits_task_defaults_and_display_properties(unique_temp_path) -> None:
    db_path = unique_temp_path("project_custom_task_type_defaults", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project(
            area="Area",
            title="Typed project",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        board = database.create_concept_board("Core board")
        task_type = database.add_project_task_type(
            project_id=project.id,
            title="Разработка",
            value="dev",
            color_marker="#20f5d2",
            theme_marker="debug",
            priority="High",
            importance=5,
            is_plan_task=True,
            concept_board_id=board.id,
        )
        database.replace_project_display_properties(
            project.id,
            [
                {"name": "wiki", "url": "https://docs.example.com", "display_mode": "name_link"},
                {"name": "repo", "url": "https://github.com/lexflame/mindnavigator", "display_mode": "url_text"},
            ],
        )

        created = database.create_task(
            title="Typed task",
            description="",
            day=date(2026, 3, 7),
            time_text="",
            priority="Low",
            project_id=project.id,
            marker_color="",
            marker_theme="",
            project_task_type_id=task_type.id,
            importance=1,
        )

        assert created.project_task_type_id == task_type.id
        assert created.priority == "High"
        assert created.importance == 5
        assert created.marker_color == "#20f5d2"
        assert created.marker_theme == "debug"
        assert created.is_plan_task is True

        fetched_type = database.fetch_project_task_type(task_type.id)
        assert fetched_type is not None
        assert fetched_type.value == "DEV"
        assert fetched_type.concept_board_id == board.id
        board_items = database.fetch_concept_board_items(board.id)
        assert [(item.entity_kind, item.entity_id) for item in board_items] == [("task", created.id)]

        display = database.fetch_project_display_properties(project.id)
        assert [(item.name, item.display_mode) for item in display] == [("WIKI", "name_link"), ("REPO", "url_text")]
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_display_properties_limit_is_four(unique_temp_path) -> None:
    db_path = unique_temp_path("project_display_property_limit", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project("Area", "Display props", date(2026, 3, 6), "Medium")
        too_many = [
            {"name": f"PROP{idx}", "url": f"https://example.com/{idx}", "display_mode": "name_link"}
            for idx in range(5)
        ]
        try:
            database.replace_project_display_properties(project.id, too_many)
        except ValueError as exc:
            assert "4" in str(exc)
        else:
            raise AssertionError("Expected display property limit validation")
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


def test_project_folder_release_does_not_toggle_archive(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_folder_release_no_archive", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        project = database.create_project(
            area="SPACE",
            title="MindNavigator v2",
            updated=date(2026, 1, 6),
            priority="High",
            archived=False,
        )
        monkeypatch.setattr(projects_workspace, "get_database", lambda: database)
        workspace = projects_workspace.ProjectsWorkspace()
        row = _find_project_row(workspace.model, project.id)
        assert row >= 0
        index = workspace.model.index(row, 0)
        option = QStyleOptionViewItem()
        option.rect = QRect(0, 0, 1200, workspace.delegate.ROW_H)
        option.widget = workspace.list
        folder_rect = workspace.delegate.project_folder_rect(option.rect)
        click_point = folder_rect.center()
        event = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(float(click_point.x()), float(click_point.y())),
            QPointF(float(click_point.x()), float(click_point.y())),
            QPointF(float(click_point.x()), float(click_point.y())),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        assert workspace.delegate.editorEvent(event, workspace.model, option, index) is False
        fetched = next(item for item in database.fetch_projects() if item.id == project.id)
        assert fetched.archived is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_dialog_relation_payload_updates_existing_editors(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_relation_payload", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(project_edit_dialog, "get_database", lambda: database)
    current = database.create_project(
        area="SPACE",
        title="Current",
        updated=date(2026, 1, 6),
        priority="High",
    )
    related = database.create_project(
        area="SPACE",
        title="Related",
        updated=date(2026, 1, 7),
        priority="Medium",
    )
    task = database.create_task("Relation task", "", date(2026, 1, 8), "", "Medium")
    map_item = database.create_map("Roadmap", "", "", "", 2, 2)
    note = database.create_note("Project note", "", [], "")
    obj = database.create_object("Project object", "", "", "", "")
    dialog = None
    try:
        dialog = project_edit_dialog.ProjectEditDialog(current)

        assert (related.id, "SPACE / Related") in dialog._relation_candidates("project")
        assert all(candidate_id != current.id for candidate_id, _label in dialog._relation_candidates("project"))

        dialog._apply_relation_payload("project", related.id)
        dialog._apply_relation_payload("project", related.id)
        dialog._apply_relation_payload("task", task.id)
        dialog._apply_relation_payload("map", map_item.id)
        dialog._apply_relation_payload("note", note.id)
        dialog._apply_relation_payload("object", obj.id)

        assert dialog.related_projects_edit.toPlainText().splitlines() == [str(related.id)]
        assert dialog.related_tasks_edit.toPlainText().splitlines() == [str(task.id)]
        assert dialog.linked_map_edit.currentData() == map_item.id
        assert dialog.linked_note_edit.currentData() == note.id
        assert dialog.linked_object_edit.currentData() == obj.id
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_dialog_custom_property_lists_use_inline_rows(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_inline_custom_property_lists", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(project_edit_dialog, "get_database", lambda: database)
    dialog = None
    try:
        dialog = project_edit_dialog.ProjectEditDialog()
        dialog.task_types_edit.setPlainText(
            "DEVELOPMENT | DEV | #20f5d2 | debug | High | 5 | 1 | | active\n"
            "MUSIC | MUSIC | #8A63D2 | music | Medium | 3 | 0 | | active"
        )
        dialog.display_properties_edit.setPlainText("WIKI | https://docs.example.com | name_link")
        dialog._refresh_inline_property_lists()

        task_inputs = dialog.task_types_list_widget.findChildren(QLineEdit)
        display_inputs = dialog.display_properties_list_widget.findChildren(QLineEdit)
        assert len(task_inputs) == 2
        assert task_inputs[0].isReadOnly() is True
        assert "DEVELOPMENT" in task_inputs[0].text()
        assert len(display_inputs) == 1
        assert "WIKI" in display_inputs[0].text()

        task_buttons = dialog.task_types_list_widget.findChildren(QToolButton)
        display_buttons = dialog.display_properties_list_widget.findChildren(QToolButton)
        assert len(task_buttons) == 6
        assert len(display_buttons) == 2
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_dialog_inline_task_type_actions_target_clicked_row(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_inline_task_type_actions", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(project_edit_dialog, "get_database", lambda: database)
    dialog = None
    try:
        dialog = project_edit_dialog.ProjectEditDialog()
        dialog.task_types_edit.setPlainText(
            "DEVELOPMENT | DEV | #20f5d2 | debug | High | 5 | 1 | | active\n"
            "MUSIC | MUSIC | #8A63D2 | music | Medium | 3 | 0 | | active"
        )
        dialog._refresh_inline_property_lists()
        monkeypatch.setattr(
            dialog,
            "_task_type_dialog",
            lambda initial=None: {
                "title": "UPDATED",
                "value": "UPD",
                "color_marker": "#4C78D0",
                "theme_marker": "dev",
                "priority": "Low",
                "importance": 2,
                "is_plan_task": False,
                "concept_board_id": None,
                "active": True,
            },
        )

        dialog._edit_task_type_line(1)
        lines = dialog.task_types_edit.toPlainText().splitlines()
        assert lines[0].startswith("DEVELOPMENT | DEV")
        assert lines[1].startswith("UPDATED | UPD")

        dialog._toggle_task_type_line(0)
        assert dialog._parse_task_type_line(dialog.task_types_edit.toPlainText().splitlines()[0])["active"] is False

        monkeypatch.setattr(project_edit_dialog.QMessageBox, "question", lambda *args, **kwargs: project_edit_dialog.QMessageBox.StandardButton.Yes)
        dialog._delete_task_type_line(0)
        remaining = dialog.task_types_edit.toPlainText().splitlines()
        assert len(remaining) == 1
        assert remaining[0].startswith("UPDATED | UPD")
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_dialog_inline_display_property_actions_target_clicked_row(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_inline_display_property_actions", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(project_edit_dialog, "get_database", lambda: database)
    dialog = None
    try:
        dialog = project_edit_dialog.ProjectEditDialog()
        dialog.display_properties_edit.setPlainText(
            "WIKI | https://docs.example.com | name_link\n"
            "REPO | https://github.com/lexflame/mindnavigator | url_text"
        )
        dialog._refresh_inline_property_lists()
        monkeypatch.setattr(
            dialog,
            "_display_property_dialog",
            lambda initial=None: {
                "name": "DOCS",
                "url": "https://docs.example.com/new",
                "display_mode": "name_link",
            },
        )

        dialog._edit_display_property_line(1)
        lines = dialog.display_properties_edit.toPlainText().splitlines()
        assert lines[0].startswith("WIKI | https://docs.example.com")
        assert lines[1] == "DOCS | https://docs.example.com/new | name_link"

        dialog._delete_display_property_line(0)
        remaining = dialog.display_properties_edit.toPlainText().splitlines()
        assert remaining == ["DOCS | https://docs.example.com/new | name_link"]
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_task_type_dialog_matches_preview_shell_contract(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_task_type_dialog_shell", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(project_edit_dialog, "get_database", lambda: database)
    captured_dialogs = []

    def fake_exec(self):
        captured_dialogs.append(self)
        return project_edit_dialog.QDialog.DialogCode.Accepted

    monkeypatch.setattr(project_edit_dialog.QDialog, "exec", fake_exec)
    dialog = None
    try:
        dialog = project_edit_dialog.ProjectEditDialog()
        result = dialog._task_type_dialog(
            {
                "title": "Development",
                "value": "DEV",
                "color_marker": "#20f5d2",
                "theme_marker": "debug",
                "priority": "High",
                "importance": 5,
                "is_plan_task": True,
                "concept_board_id": None,
                "active": True,
            }
        )

        assert result is not None
        assert result["title"] == "DEVELOPMENT"
        task_type_dialog = captured_dialogs[-1]
        assert task_type_dialog.objectName() == "ProjectTaskTypeDialog"
        assert task_type_dialog.findChild(project_edit_dialog.QFrame, "TaskTypePreviewCard") is not None
        assert task_type_dialog.findChild(project_edit_dialog.QFrame, "TaskTypeCard") is not None
        button_texts = {button.text() for button in task_type_dialog.findChildren(project_edit_dialog.QPushButton)}
        assert {"Предпросмотр", "Закрыть", "Отмена", "Сохранить", "Сохранить и добавить ещё"}.issubset(button_texts)
    finally:
        if dialog is not None:
            dialog.deleteLater()
        for captured in captured_dialogs:
            captured.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_project_display_property_dialog_matches_preview_shell_contract(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("project_display_property_dialog_shell", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(project_edit_dialog, "get_database", lambda: database)
    captured_dialogs = []

    def fake_exec(self):
        captured_dialogs.append(self)
        return project_edit_dialog.QDialog.DialogCode.Accepted

    monkeypatch.setattr(project_edit_dialog.QDialog, "exec", fake_exec)
    dialog = None
    try:
        dialog = project_edit_dialog.ProjectEditDialog()
        result = dialog._display_property_dialog(
            {
                "name": "wiki",
                "url": "https://docs.example.com/kazantip",
                "display_mode": "url_text",
            }
        )

        assert result == {
            "name": "WIKI",
            "url": "https://docs.example.com/kazantip",
            "display_mode": "url_text",
        }
        display_dialog = captured_dialogs[-1]
        assert display_dialog.objectName() == "ProjectDisplayPropertyDialog"
        assert display_dialog.findChild(project_edit_dialog.QFrame, "DisplayPropertyPreviewCard") is not None
        assert display_dialog.findChild(project_edit_dialog.QFrame, "DisplayPropertyCard") is not None
        button_texts = {button.text() for button in display_dialog.findChildren(project_edit_dialog.QPushButton)}
        assert {"Предпросмотр", "Закрыть", "Отмена", "Сохранить", "Сохранить и добавить ещё"}.issubset(button_texts)
    finally:
        if dialog is not None:
            dialog.deleteLater()
        for captured in captured_dialogs:
            captured.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
