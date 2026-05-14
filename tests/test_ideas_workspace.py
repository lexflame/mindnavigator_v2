from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

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


def test_ideas_workspace_triage_focuses_first_inbox_idea(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_triage_start", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        database.create_idea(title="Old inbox", status="inbox")
        latest_inbox = database.create_idea(title="Latest inbox", status="inbox")
        database.create_idea(title="Already work", status="work")
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        workspace.actions["triage"].trigger()
        QApplication.processEvents()

        model = workspace.list_view.model()
        first_inbox_index = model.first_idea_index("inbox")
        assert first_inbox_index.isValid()
        assert workspace.status_filter.currentData() == "inbox"
        assert workspace.get_selection() == first_inbox_index.data(ideas_workspace_module.IdeaRoles.IdeaId)
        assert workspace.title_input.text() == first_inbox_index.data(ideas_workspace_module.IdeaRoles.Title)
        assert workspace.inspector_tabs.currentWidget() is workspace.transform_tab
        assert "Разбор инбокса" in workspace.status_row.text()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_triage_promotes_inbox_and_advances(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_triage_advance", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        older_inbox = database.create_idea(title="Older inbox", status="inbox")
        latest_inbox = database.create_idea(title="Latest inbox", status="inbox")
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        workspace.actions["triage"].trigger()
        QApplication.processEvents()
        current_before = workspace.get_selection()
        assert current_before in {older_inbox.id, latest_inbox.id}

        QTest.mouseClick(workspace.triage_work_btn, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        updated = database.get_idea(current_before)
        assert updated is not None
        assert updated.status == "work"
        remaining_inbox_id = older_inbox.id if current_before == latest_inbox.id else latest_inbox.id
        assert workspace.get_selection() == remaining_inbox_id
        assert database.get_idea(remaining_inbox_id).status == "inbox"
        assert "Осталось inbox: 1" in workspace.status_row.text()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_materials_attach_and_save_caption(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_materials", ".sqlite3")
    cloud_root = db_path.parent / "cloud"
    cloud_root.mkdir(parents=True, exist_ok=True)
    image_path = cloud_root / "ideas" / "sample.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(24, 24, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0xFF4A90E2)
    assert image.save(str(image_path))

    database = Database(path=db_path)
    workspace = None
    try:
        idea = database.create_idea(title="Idea with materials", status="inbox")
        database.set_setting("cloud_storage_path", str(cloud_root))
        database.upsert_cloud_file(
            rel_path="ideas/sample.png",
            name="sample.png",
            description="",
            checksum="checksum-material",
            hash_value="hash-material",
            size=image_path.stat().st_size,
            is_image=True,
            valid=True,
        )

        class _FakeAttachDialog(QDialog):
            def __init__(self, parent=None) -> None:
                super().__init__(parent)

            def selected_rel_path(self) -> str:
                return "ideas/sample.png"

        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "AttachFileSelectNav", _FakeAttachDialog)
        monkeypatch.setattr(
            ideas_workspace_module,
            "exec_with_overlay",
            lambda dialog, parent=None: QDialog.DialogCode.Accepted,
        )

        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        model = workspace.list_view.model()
        assert model is not None
        index = model.index_for_id(idea.id)
        workspace.list_view.setCurrentIndex(index)
        QApplication.processEvents()

        QTest.mouseClick(workspace.materials_attach_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert workspace.materials_thumbnail_list.count() == 1
        assert database.fetch_idea_images(idea.id)[0].rel_path == "ideas/sample.png"

        workspace.materials_caption_input.setPlainText("Главный референс")
        QTest.mouseClick(workspace.materials_save_caption_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        saved = database.fetch_idea_images(idea.id)
        assert len(saved) == 1
        assert saved[0].caption == "Главный референс"
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
