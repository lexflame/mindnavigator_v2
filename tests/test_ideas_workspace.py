from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from mindnavigator.storage import Database
from mindnavigator.workspaces import ideas as ideas_workspace
from mindnavigator.workspaces.ideas import ideas_workspace as ideas_workspace_module


def test_ideas_workspace_toolbar_create_and_edit_round_trip(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_create_edit", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()

        workspace.actions["new"].trigger()
        QApplication.processEvents()

        ideas = database.fetch_ideas()
        assert len(ideas) == 1
        assert ideas[0].title == "Новая идея"
        assert workspace.get_selection() == ideas[0].id
        assert workspace.title_input.text() == "Новая идея"

        workspace.title_input.setText("Идея обновлена")
        workspace.summary_input.setText("Краткое описание")
        workspace.body_input.setPlainText("Подробности идеи")
        workspace.save_button.click()
        QApplication.processEvents()

        saved = database.get_idea(ideas[0].id)
        assert saved is not None
        assert saved.title == "Идея обновлена"
        assert saved.summary == "Краткое описание"
        assert saved.body_md == "Подробности идеи"
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_save_button_persists_existing_idea_edits(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_save_existing", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        created = database.create_idea(
            title="Existing idea",
            summary="Initial summary",
            body_md="Initial body",
            status="inbox",
        )
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        model = workspace.list_view.model()
        assert model is not None
        index = model.index_for_id(created.id)
        workspace.list_view.setCurrentIndex(index)
        QApplication.processEvents()

        workspace.title_input.setText("Existing idea updated")
        workspace.summary_input.setText("Updated summary")
        workspace.body_input.setPlainText("Updated body")
        QApplication.processEvents()

        QTest.mouseClick(workspace.save_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        saved = database.get_idea(created.id)
        assert saved is not None
        assert saved.title == "Existing idea updated"
        assert saved.summary == "Updated summary"
        assert saved.body_md == "Updated body"
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
