from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication

from mindnavigator.storage import Database
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


def test_projects_model_cycles_priority_by_row(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("projects_priority_cycle", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project(
            area="Area",
            title="Project",
            updated=date(2026, 3, 6),
            priority="Low",
        )
        monkeypatch.setattr(projects_workspace, "get_database", lambda: database)
        model = projects_workspace.ProjectsModel()

        row_idx = _find_project_row(model, project.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(ProjectRoles.Priority) == "Low"

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_project_row(model, project.id)
        assert model.index(row_idx, 0).data(ProjectRoles.Priority) == "Medium"

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_project_row(model, project.id)
        assert model.index(row_idx, 0).data(ProjectRoles.Priority) == "High"

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_project_row(model, project.id)
        assert model.index(row_idx, 0).data(ProjectRoles.Priority) == "Low"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_projects_model_attachment_summary_rolls_up_child_projects(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("projects_attachment_summary", ".sqlite3")
    database = Database(path=db_path)
    try:
        parent = database.create_project(
            area="Area",
            title="Parent",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        child = database.create_project(
            area="Area",
            title="Child",
            updated=date(2026, 3, 6),
            priority="Medium",
            parent_project_id=parent.id,
        )
        parent_task = database.create_task(
            title="Parent task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
            project_id=parent.id,
        )
        child_task = database.create_task(
            title="Child task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="Medium",
            project_id=child.id,
        )
        database.add_task_attachment(parent_task.id, "note", 1)
        database.add_task_attachment(child_task.id, "note", 2)
        database.add_task_attachment(child_task.id, "image", 3)
        database.add_task_attachment(child_task.id, "image", 4)

        monkeypatch.setattr(projects_workspace, "get_database", lambda: database)
        model = projects_workspace.ProjectsModel()

        parent_row = _find_project_row(model, parent.id)
        child_row = _find_project_row(model, child.id)
        assert parent_row >= 0
        assert child_row >= 0

        parent_summary = dict(model.index(parent_row, 0).data(ProjectRoles.AttachmentSummary) or [])
        child_summary = dict(model.index(child_row, 0).data(ProjectRoles.AttachmentSummary) or [])

        assert parent_summary.get("note") == 2
        assert parent_summary.get("image") == 2
        assert child_summary.get("note") == 1
        assert child_summary.get("image") == 2
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_projects_model_keeps_child_rows_under_parent_and_promotes_orphans_in_search(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("projects_tree_order_visible_depth", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_project(
            area="Area",
            title="Alpha Root",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        sibling = database.create_project(
            area="Area",
            title="Beta Root",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        child = database.create_project(
            area="Area",
            title="Zulu Child",
            updated=date(2026, 3, 6),
            priority="Medium",
            parent_project_id=root.id,
        )

        monkeypatch.setattr(projects_workspace, "get_database", lambda: database)
        model = projects_workspace.ProjectsModel()

        visible_ids = [
            model.index(row, 0).data(ProjectRoles.ProjectId)
            for row in range(model.rowCount())
            if model.index(row, 0).data(ProjectRoles.RowType) == "project"
        ]
        visible_ids = [project_id for project_id in visible_ids if project_id in {root.id, child.id, sibling.id}]
        assert visible_ids == [root.id, child.id, sibling.id]

        child_row = _find_project_row(model, child.id)
        assert child_row >= 0
        assert model.index(child_row, 0).data(ProjectRoles.Depth) == 1

        model.set_search("Zulu")
        child_row = _find_project_row(model, child.id)
        assert child_row >= 0
        assert model.index(child_row, 0).data(ProjectRoles.Depth) == 0
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_projects_model_add_project_expands_collapsed_parent_chain(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("projects_add_child_expands_parent", ".sqlite3")
    database = Database(path=db_path)
    try:
        parent = database.create_project(
            area="Area",
            title="Parent",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        monkeypatch.setattr(projects_workspace, "get_database", lambda: database)
        model = projects_workspace.ProjectsModel()

        parent_row = _find_project_row(model, parent.id)
        assert parent_row >= 0
        model.toggle_project_collapsed_by_row(parent_row)

        child_id = model.add_project(
            area="Area",
            title="Child",
            updated=date(2026, 3, 6),
            priority="Medium",
            archived=False,
            parent_project_id=parent.id,
        )

        parent_row = _find_project_row(model, parent.id)
        child_row = _find_project_row(model, child_id)
        assert parent_row >= 0
        assert child_row >= 0
        assert model.index(parent_row, 0).data(ProjectRoles.IsCollapsed) is False
        assert model.index(child_row, 0).data(ProjectRoles.Depth) == 1
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_projects_workspace_adds_graph_button_after_import(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("projects_graph_button", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(projects_workspace, "get_database", lambda: database)
    workspace = projects_workspace.ProjectsWorkspace()
    try:
        assert workspace.btn_graph.text() == "GRAPH"
        top_layout = workspace.btn_import.parentWidget().layout()
        assert top_layout is not None
        assert top_layout.indexOf(workspace.btn_graph) == top_layout.indexOf(workspace.btn_import) + 1

        captured: list[tuple[str, str]] = []

        def _capture_information(_parent, title: str, text: str):
            captured.append((title, text))
            return 0

        monkeypatch.setattr(projects_workspace.QMessageBox, "information", _capture_information)
        workspace._on_graph_clicked()
        assert captured
        assert captured[0][0] == "Projects"
        assert "GRAPH" in captured[0][1]
    finally:
        workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
