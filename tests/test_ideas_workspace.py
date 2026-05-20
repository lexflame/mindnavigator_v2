from __future__ import annotations

from datetime import datetime, timezone

import pytest

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from mindnavigator.storage import Database
from mindnavigator.workspaces import ideas as ideas_workspace
from mindnavigator.workspaces.ideas import ideas_workspace as ideas_workspace_module


def test_ideas_workspace_format_relative_time_accepts_naive_and_aware_datetimes() -> None:
    aware_value = datetime.now(timezone.utc)
    naive_value = datetime.now()

    aware_result = ideas_workspace_module.IdeasWorkspace._format_relative_time(aware_value)
    naive_result = ideas_workspace_module.IdeasWorkspace._format_relative_time(naive_value)

    assert isinstance(aware_result, str)
    assert isinstance(naive_result, str)


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
            source="Legacy source",
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
        workspace.source_input.setText("Inbox capture")
        QApplication.processEvents()

        QTest.mouseClick(workspace.save_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        saved = database.get_idea(created.id)
        assert saved is not None
        assert saved.title == "Existing idea updated"
        assert saved.summary == "Updated summary"
        assert saved.body_md == "Updated body"
        assert saved.source == "Inbox capture"
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_remaster_tabs_and_source_field(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_tabs", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        database.create_idea(title="Workspace tabs", status="inbox", source="Voice memo")
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        tab_titles = [workspace.inspector_tabs.tabText(index) for index in range(workspace.inspector_tabs.count())]
        assert tab_titles == ["Суть", "Развитие", "Связи (0)", "Материалы и референсы (0)", "Выход"]
        assert workspace.search_input.placeholderText() == "Поиск по идеям, краткому описанию, тексту, источнику..."
        assert workspace.source_input.placeholderText() == "Откуда пришла идея"
        assert workspace.development_insert_button.text() == "Вставить шаблон развития"
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_save_button_persists_project_change(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_change_project", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        project_a = database.create_project(
            area="Work",
            title="Alpha",
            updated=ideas_workspace_module.date.today(),
            priority="Medium",
        )
        project_b = database.create_project(
            area="Work",
            title="Beta",
            updated=ideas_workspace_module.date.today(),
            priority="Medium",
        )
        created = database.create_idea(
            title="Existing idea",
            summary="Initial summary",
            body_md="Initial body",
            status="inbox",
            project_id=project_a.id,
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

        assert workspace.project_input.currentData() == project_a.id
        project_b_index = workspace.project_input.findData(project_b.id)
        assert project_b_index >= 0

        workspace.project_input.setCurrentIndex(project_b_index)
        QApplication.processEvents()

        QTest.mouseClick(workspace.save_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        saved = database.get_idea(created.id)
        assert saved is not None
        assert saved.project_id == project_b.id
        assert saved.project_title == project_b.title
        assert workspace.project_input.currentData() == project_b.id
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_relations_tab_adds_and_removes_relation(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_relations", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        idea = database.create_idea(title="Idea with relation", status="inbox")
        task = database.create_task(
            title="Linked task",
            description="Task description",
            day=ideas_workspace_module.date.today(),
            time_text="",
            priority="Medium",
        )

        class _FakeIdeaRelationDialog(QDialog):
            def __init__(self, candidates_by_kind, parent=None) -> None:
                super().__init__(parent)
                self.candidates_by_kind = candidates_by_kind

            def values(self) -> dict:
                return {
                    "entity_type": "task",
                    "entity_id": task.id,
                }

        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "IdeaRelationDialog", _FakeIdeaRelationDialog)
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

        QTest.mouseClick(workspace.relations_add_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        relations = database.fetch_idea_relations(idea.id)
        assert len(relations) == 1
        assert relations[0].entity_type == "task"
        assert relations[0].entity_id == task.id
        assert workspace.relations_list.count() == 1
        assert "Linked task" in workspace.relations_list.item(0).text()

        workspace.relations_list.setCurrentRow(0)
        QApplication.processEvents()
        QTest.mouseClick(workspace.relations_remove_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert database.fetch_idea_relations(idea.id) == []
        assert workspace.relations_list.count() == 1
        assert "Связей пока нет" in workspace.relations_list.item(0).text()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_refresh_current_relations_reloads_selected_idea_relations(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_refresh_relations", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        idea = database.create_idea(title="Idea with delayed relation", status="inbox")
        task = database.create_task(
            title="Late linked task",
            description="",
            day=ideas_workspace_module.date.today(),
            time_text="",
            priority="Medium",
        )
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        model = workspace.list_view.model()
        assert model is not None
        index = model.index_for_id(idea.id)
        workspace.list_view.setCurrentIndex(index)
        QApplication.processEvents()

        assert workspace.relations_list.count() == 1
        assert workspace.relations_list.item(0).data(Qt.ItemDataRole.UserRole) is None

        database.add_idea_relation(idea.id, "task", task.id)
        workspace.refresh_current_relations()
        QApplication.processEvents()

        assert workspace.relations_list.count() == 1
        assert "Late linked task" in workspace.relations_list.item(0).text()
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
        assert workspace.triage_progress_label.text() == "Разбор идеи 1 из 2"
        assert "Разбор идеи 1 из 2" in workspace.status_row.text()
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
        assert workspace.triage_progress_label.text() == "Разбор идеи 2 из 2"
        assert "Разбор идеи 2 из 2" in workspace.status_row.text()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_triage_hotkey_promotes_idea(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_triage_hotkey_work", ".sqlite3")
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

        workspace.list_view.setFocus()
        QTest.keyClick(workspace.list_view, Qt.Key.Key_W)
        QApplication.processEvents()

        updated = database.get_idea(current_before)
        assert updated is not None
        assert updated.status == "work"
        remaining_inbox_id = older_inbox.id if current_before == latest_inbox.id else latest_inbox.id
        assert workspace.get_selection() == remaining_inbox_id
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_triage_hotkeys_do_not_fire_inside_text_fields(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_triage_hotkey_guard", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        first_inbox = database.create_idea(title="First inbox", status="inbox")
        second_inbox = database.create_idea(title="Second inbox", status="inbox")
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        workspace.actions["triage"].trigger()
        QApplication.processEvents()
        current_before = workspace.get_selection()
        assert current_before in {first_inbox.id, second_inbox.id}

        workspace.title_input.setFocus()
        QTest.keyClick(workspace.title_input, Qt.Key.Key_W)
        QApplication.processEvents()

        unchanged = database.get_idea(current_before)
        assert unchanged is not None
        assert unchanged.status == "inbox"
        assert workspace.get_selection() == current_before
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("kind", "button_name", "created_status"),
    [
        ("note", "transform_note_btn", "Из идеи создана заметка."),
        ("object", "transform_object_btn", "Из идеи создан объект."),
    ],
)
def test_ideas_workspace_triage_advances_after_note_and_object_transform(
    monkeypatch,
    unique_temp_path,
    kind: str,
    button_name: str,
    created_status: str,
) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path(f"ideas_workspace_triage_{kind}", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        first_inbox = database.create_idea(title=f"First {kind}", status="inbox")
        second_inbox = database.create_idea(title=f"Second {kind}", status="inbox")
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        workspace.actions["triage"].trigger()
        QApplication.processEvents()
        current_before = workspace.get_selection()
        assert current_before in {first_inbox.id, second_inbox.id}

        button = getattr(workspace, button_name)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        updated = database.get_idea(current_before)
        assert updated is not None
        assert updated.status == "ripe"
        remaining_inbox_id = first_inbox.id if current_before == second_inbox.id else second_inbox.id
        assert workspace.get_selection() == remaining_inbox_id
        assert workspace.triage_progress_label.text() == "Разбор идеи 2 из 2"
        assert created_status in workspace.status_row.text()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_adds_current_idea_to_concept_board(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_concept_board", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        idea = database.create_idea(title="Idea to board", status="inbox")

        class _FakeConceptBoardPage:
            def __init__(self) -> None:
                self.selected_ids: list[int] = []

            def select_concept_board(self, concept_board_id: int) -> None:
                self.selected_ids.append(concept_board_id)

        class _FakeMainWindow(QWidget):
            MODE_CONCEPTBOARD = "Концептборд"

            def __init__(self) -> None:
                super().__init__()
                self.mode_calls: list[str] = []
                self.page_concept_board = _FakeConceptBoardPage()

            def set_mode(self, mode_name: str) -> None:
                self.mode_calls.append(mode_name)

        main_window = _FakeMainWindow()
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        workspace = ideas_workspace.IdeasWorkspace(parent=main_window)
        workspace.show()

        model = workspace.list_view.model()
        assert model is not None
        index = model.index_for_id(idea.id)
        workspace.list_view.setCurrentIndex(index)
        workspace.inspector_tabs.setCurrentWidget(workspace.transform_tab)
        QApplication.processEvents()

        QTest.mouseClick(workspace.transform_concept_board_btn, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        boards = database.fetch_concept_boards()
        assert len(boards) == 1
        board = boards[0]
        board_items = database.fetch_concept_board_items(board.id)
        assert [(item.entity_kind, item.entity_id) for item in board_items] == [("idea", idea.id)]
        idea_relations = database.fetch_idea_relations(idea.id)
        assert ("concept_board", board.id) in {(item.entity_type, item.entity_id) for item in idea_relations}
        updated = database.get_idea(idea.id)
        assert updated is not None
        assert updated.status == "ripe"
        assert main_window.mode_calls == [main_window.MODE_CONCEPTBOARD]
        assert main_window.page_concept_board.selected_ids == [board.id]
        assert "Выход: концептборд" == workspace.output_summary_label.text()
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
        assert workspace.findChild(type(workspace.materials_hint), "IdeasMaterialsPreviewLabel") is None
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


def test_ideas_workspace_materials_fullsize_preview_opens_only_on_thumbnail_double_click(
    monkeypatch,
    unique_temp_path,
) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_materials_preview", ".sqlite3")
    cloud_root = db_path.parent / "cloud"
    cloud_root.mkdir(parents=True, exist_ok=True)
    image_path = cloud_root / "ideas" / "preview.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(24, 24, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0xFF4A90E2)
    assert image.save(str(image_path))

    database = Database(path=db_path)
    workspace = None
    preview_calls: list[dict[str, object]] = []
    try:
        idea = database.create_idea(title="Idea with preview", status="inbox")
        database.set_setting("cloud_storage_path", str(cloud_root))
        database.upsert_cloud_file(
            rel_path="ideas/preview.png",
            name="preview.png",
            description="",
            checksum="checksum-preview",
            hash_value="hash-preview",
            size=image_path.stat().st_size,
            is_image=True,
            valid=True,
        )
        database.add_idea_image(idea.id, "ideas/preview.png")

        class _FakePreviewDialog:
            def __init__(self, parent=None, **kwargs) -> None:
                self._kwargs = kwargs

            def exec(self) -> int:
                preview_calls.append(self._kwargs)
                return 0

        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "IdeaImagePreviewDialog", _FakePreviewDialog)

        workspace = ideas_workspace.IdeasWorkspace()
        workspace.show()

        model = workspace.list_view.model()
        assert model is not None
        index = model.index_for_id(idea.id)
        workspace.list_view.setCurrentIndex(index)
        QApplication.processEvents()

        assert workspace.materials_thumbnail_list.count() == 1
        workspace.materials_thumbnail_list.setCurrentRow(0)
        QApplication.processEvents()
        assert preview_calls == []

        item = workspace.materials_thumbnail_list.item(0)
        assert item is not None
        workspace.materials_thumbnail_list.itemDoubleClicked.emit(item)
        QApplication.processEvents()

        assert len(preview_calls) == 1
        assert preview_calls[0]["idea_id"] == idea.id
        assert preview_calls[0]["start_index"] == 0
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_ideas_workspace_transform_buttons_share_row_and_width(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("ideas_workspace_transform_buttons", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        idea = database.create_idea(title="Idea for transform layout", status="inbox")
        monkeypatch.setattr(ideas_workspace, "get_database", lambda: database)
        monkeypatch.setattr(ideas_workspace_module, "get_database", lambda: database)

        workspace = ideas_workspace.IdeasWorkspace()
        workspace.resize(1400, 900)
        workspace.show()

        model = workspace.list_view.model()
        assert model is not None
        index = model.index_for_id(idea.id)
        workspace.list_view.setCurrentIndex(index)
        workspace.inspector_tabs.setCurrentWidget(workspace.transform_tab)
        QApplication.processEvents()

        buttons = [
            workspace.transform_task_btn,
            workspace.transform_note_btn,
            workspace.transform_object_btn,
            workspace.transform_marker_btn,
        ]
        row_host = workspace.transform_actions_host
        y_positions = {button.geometry().y() for button in buttons}
        widths = {button.width() for button in buttons}
        spacing = row_host.layout().spacing()
        total_button_width = sum(button.width() for button in buttons) + spacing * (len(buttons) - 1)

        assert len(y_positions) == 1
        assert len(widths) == 1
        assert abs(total_button_width - row_host.width()) <= 4
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
