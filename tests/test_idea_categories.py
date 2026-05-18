from __future__ import annotations

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from mindnavigator.storage import Database
from mindnavigator.workspaces import ideas as ideas_workspace
from mindnavigator.workspaces.ideas import ideas_workspace as ideas_workspace_module


def _combo_labels(combo) -> list[str]:
    return [combo.itemText(index) for index in range(combo.count())]


def test_database_idea_categories_create_rename_delete_round_trip(unique_temp_path) -> None:
    db_path = unique_temp_path("idea_categories_storage", ".sqlite3")
    database = Database(path=db_path)
    try:
        default_codes = {category.code for category in database.list_idea_categories()}
        assert {"inbox", "work", "ripe", "done", "archived"} <= default_codes

        created = database.create_idea_category("Backlog")
        assert created.title == "Backlog"
        assert not created.is_system

        idea = database.create_idea(title="Custom category idea", status=created.code)
        assert idea.status == created.code

        renamed = database.update_idea_category_title(created.code, "Pipeline")
        assert renamed.title == "Pipeline"
        assert database.get_idea_category(created.code).title == "Pipeline"

        database.delete_idea_category(created.code)
        moved = database.get_idea(idea.id)
        assert moved is not None
        assert moved.status == "inbox"
        assert database.get_idea_category(created.code) is None
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_category_actions_refresh_controls(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("idea_categories_workspace", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        custom_category = database.create_idea_category("Backlog")
        idea = database.create_idea(title="Idea in custom category", status=custom_category.code)

        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()
        QApplication.processEvents()

        assert "Backlog" in _combo_labels(workspace.status_filter)
        assert "Backlog" in _combo_labels(workspace.status_input)

        monkeypatch.setattr(
            ideas_workspace_module.QInputDialog,
            "getItem",
            lambda *args, **kwargs: ("Backlog", True),
        )

        class _FakeIdeaCategoryEditDialog(QDialog):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(kwargs.get("parent"))

            def title_value(self) -> str:
                return "Pipeline"

        monkeypatch.setattr(
            ideas_workspace_module,
            "IdeaCategoryEditDialog",
            _FakeIdeaCategoryEditDialog,
        )
        monkeypatch.setattr(
            ideas_workspace_module,
            "exec_with_overlay",
            lambda dialog, parent=None: QDialog.DialogCode.Accepted,
        )
        workspace._rename_idea_category()
        QApplication.processEvents()

        assert "Pipeline" in _combo_labels(workspace.status_filter)
        assert "Backlog" not in _combo_labels(workspace.status_filter)

        monkeypatch.setattr(
            ideas_workspace_module.QInputDialog,
            "getItem",
            lambda *args, **kwargs: ("Pipeline", True),
        )
        monkeypatch.setattr(
            ideas_workspace_module.QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        workspace._delete_idea_category()
        QApplication.processEvents()

        assert "Pipeline" not in _combo_labels(workspace.status_filter)
        moved = database.get_idea(idea.id)
        assert moved is not None
        assert moved.status == "inbox"
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
