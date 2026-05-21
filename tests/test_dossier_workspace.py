from __future__ import annotations

from datetime import date

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QWidget

from mindnavigator.storage import Database
from mindnavigator.ui.workspaces import base_workspace as base_workspace_module
from mindnavigator.workspaces import dossier as dossier_workspace
from mindnavigator.workspaces.dossier import dossier_workspace as dossier_workspace_module
from mindnavigator.workspaces.dossier.dossier_roles import DossierRoles


def _set_combo_to_data(combo, value) -> None:
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            combo.setCurrentIndex(index)
            return
    raise AssertionError(f"Value {value!r} not found in combo box.")


def test_dossier_workspace_filters_preview_and_links(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    settings = QSettings()
    settings.remove("workspace/dossier/search_text")
    settings.remove("workspace/dossier/filters")

    db_path = unique_temp_path("dossier_workspace_filters", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        book = database.create_dossier(
            kind="book",
            title="The Left Hand of Darkness",
            summary="Cold planet politics.",
            description="Envoys, ice, and divided loyalties.",
            status="active",
            rating=9,
            source="Le Guin shelf",
            tags=["sci-fi", "classic"],
            metadata={"author_display": "Ursula K. Le Guin", "publication_year": 1969},
        )
        database.create_dossier(
            kind="film",
            title="Stalker",
            summary="A slow walk into the Zone.",
            description="Guide, writer, professor.",
            status="completed",
            rating=8,
            source="Blu-ray",
            metadata={"director": "Andrei Tarkovsky", "release_year": 1979},
        )
        task = database.create_task(
            title="Outline winter reading notes",
            description="",
            day=date(2026, 3, 13),
            time_text="09:00",
            priority="Medium",
        )
        database.add_dossier_link(book.id, "task", task.id)

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        workspace = dossier_workspace.DossierWorkspace()

        model = workspace.list_view.model()
        assert model is not None
        assert model.rowCount() == 2

        _set_combo_to_data(workspace.kind_filter, "book")
        QApplication.processEvents()
        assert model.rowCount() == 1

        workspace.list_view.setCurrentIndex(model.index(0, 0))
        QApplication.processEvents()

        assert workspace.preview_title_label.text() == "The Left Hand of Darkness"
        assert "Книга" in workspace.preview_meta_label.text()
        assert "Le Guin shelf" in workspace.preview_meta_label.text()
        assert "Ursula K. Le Guin" in workspace.preview_metadata_label.text()
        assert workspace.preview_links.count() == 1
        assert "Outline winter reading notes" in workspace.preview_links.item(0).text()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_workspace_create_and_delete_round_trip(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    settings = QSettings()
    settings.remove("workspace/dossier/search_text")
    settings.remove("workspace/dossier/filters")

    db_path = unique_temp_path("dossier_workspace_create_delete", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        workspace = dossier_workspace.DossierWorkspace()

        class _AcceptedCreateDialog:
            def __init__(self, *args, **kwargs) -> None:
                self._values = {
                    "kind": "writer",
                    "title": "Arkady dossier",
                    "summary": "",
                    "description": "",
                    "tags": [],
                    "status": "planned",
                    "rating": None,
                    "source": "",
                    "cover_image": "",
                    "metadata": {"country": "USSR"},
                }

            def values(self) -> dict[str, object]:
                return dict(self._values)

        monkeypatch.setattr(dossier_workspace_module, "DossierCreateDialog", _AcceptedCreateDialog)
        monkeypatch.setattr(
            dossier_workspace_module,
            "show_dialog_standard",
            lambda dialog, parent=None: QDialog.DialogCode.Accepted,
        )

        workspace._open_create_dialog()
        QApplication.processEvents()

        created = database.fetch_dossiers()
        assert len(created) == 1
        assert created[0].title == "Arkady dossier"
        assert created[0].kind == "writer"
        assert created[0].metadata["country"] == "USSR"
        assert workspace.get_selection() == created[0].id

        workspace._delete_selected(require_confirmation=False)
        QApplication.processEvents()

        assert database.fetch_dossiers() == []
        model = workspace.list_view.model()
        assert model is not None
        assert model.rowCount() == 0
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_workspace_add_and_remove_link(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    settings = QSettings()
    settings.remove("workspace/dossier/search_text")
    settings.remove("workspace/dossier/filters")

    db_path = unique_temp_path("dossier_workspace_links", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        dossier = database.create_dossier(
            kind="book",
            title="Hyperion",
            summary="Pilgrims and the Shrike.",
            description="A frame narrative on the edge of war.",
            status="active",
            metadata={"author_display": "Dan Simmons"},
        )
        task = database.create_task(
            title="Draft Hyperion notes",
            description="",
            day=date(2026, 3, 13),
            time_text="11:00",
            priority="Medium",
        )

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        workspace = dossier_workspace.DossierWorkspace()
        model = workspace.list_view.model()
        assert model is not None
        workspace.list_view.setCurrentIndex(model.index(0, 0))
        QApplication.processEvents()

        class _AcceptedLinkDialog:
            def __init__(self, *args, **kwargs) -> None:
                self._values = {
                    "entity_kind": "task",
                    "entity_id": task.id,
                }

            def values(self) -> dict[str, object]:
                return dict(self._values)

        monkeypatch.setattr(dossier_workspace_module, "DossierLinkDialog", _AcceptedLinkDialog)
        monkeypatch.setattr(
            dossier_workspace_module,
            "show_dialog_standard",
            lambda dialog, parent=None: QDialog.DialogCode.Accepted,
        )

        assert workspace.get_selection() == dossier.id
        assert workspace.add_link_button.isEnabled()
        assert not workspace.remove_link_button.isEnabled()

        workspace._open_add_link_dialog()
        QApplication.processEvents()

        links = database.fetch_dossier_links(dossier.id)
        assert len(links) == 1
        assert workspace.preview_links.count() == 1
        assert "Draft Hyperion notes" in workspace.preview_links.item(0).text()

        workspace.preview_links.setCurrentRow(0)
        QApplication.processEvents()
        assert workspace.remove_link_button.isEnabled()

        workspace._remove_selected_link()
        QApplication.processEvents()

        assert database.fetch_dossier_links(dossier.id) == []
        assert workspace.preview_links.count() == 1
        assert "Связей пока нет" in workspace.preview_links.item(0).text()
        assert not workspace.remove_link_button.isEnabled()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_workspace_tag_filter_grouping_and_summary(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    settings = QSettings()
    settings.remove("workspace/dossier/search_text")
    settings.remove("workspace/dossier/filters")

    db_path = unique_temp_path("dossier_workspace_grouping", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        database.create_dossier(
            kind="book",
            title="A Wizard of Earthsea",
            summary="Ged begins.",
            description="",
            status="active",
            rating=9,
            tags=["classic", "fantasy"],
            metadata={"author_display": "Ursula K. Le Guin"},
        )
        database.create_dossier(
            kind="book",
            title="Tehanu",
            summary="Later Earthsea.",
            description="",
            status="completed",
            rating=8,
            tags=["classic"],
            metadata={"author_display": "Ursula K. Le Guin"},
        )
        database.create_dossier(
            kind="film",
            title="Solaris",
            summary="Station over the ocean.",
            description="",
            status="active",
            rating=8,
            tags=["arthouse"],
            metadata={"director": "Andrei Tarkovsky", "release_year": 1972},
        )

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        workspace = dossier_workspace.DossierWorkspace()
        model = workspace.list_view.model()
        assert model is not None
        assert "Итого: 3" in workspace.summary_label.text()

        workspace.tag_filter_input.setText("classic")
        QApplication.processEvents()

        assert "Итого: 2" in workspace.summary_label.text()
        assert "classic" in workspace.summary_label.text()
        assert model.rowCount() == 2

        _set_combo_to_data(workspace.group_filter, "status")
        QApplication.processEvents()

        assert model.rowCount() == 4
        assert model.data(model.index(0, 0), DossierRoles.RowType) == "group"
        assert model.data(model.index(1, 0), DossierRoles.RowType) == "dossier"
        assert workspace.get_selection() is not None
        assert workspace.preview_title_label.text() == "Tehanu"
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_workspace_restores_tag_and_group_filters(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])

    db_path = unique_temp_path("dossier_workspace_restore_state", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    restored_workspace = None
    try:
        store: dict[str, object] = {}

        class _FakeSettings:
            def value(self, key: str, default=None, type=None):
                _ = type
                return store.get(key, default)

            def setValue(self, key: str, value) -> None:
                store[key] = value

            def remove(self, key: str) -> None:
                store.pop(key, None)

        monkeypatch.setattr(base_workspace_module, "QSettings", _FakeSettings)

        database.create_dossier(
            kind="book",
            title="The Tombs of Atuan",
            summary="Tenar and Ged.",
            description="",
            status="active",
            rating=9,
            tags=["classic"],
            metadata={"author_display": "Ursula K. Le Guin"},
        )
        database.create_dossier(
            kind="book",
            title="The Farthest Shore",
            summary="Journey west.",
            description="",
            status="completed",
            rating=8,
            tags=["classic"],
            metadata={"author_display": "Ursula K. Le Guin"},
        )
        database.create_dossier(
            kind="film",
            title="Mirror",
            summary="Memory fragments.",
            description="",
            status="active",
            rating=8,
            tags=["arthouse"],
            metadata={"director": "Andrei Tarkovsky", "release_year": 1975},
        )

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        workspace = dossier_workspace.DossierWorkspace()
        workspace.on_enter()
        QApplication.processEvents()

        _set_combo_to_data(workspace.kind_filter, "book")
        workspace.tag_filter_input.setText("classic")
        _set_combo_to_data(workspace.group_filter, "status")
        QApplication.processEvents()
        workspace.save_state()

        restored_workspace = dossier_workspace.DossierWorkspace()
        restored_workspace.on_enter()
        QApplication.processEvents()

        model = restored_workspace.list_view.model()
        assert model is not None
        assert restored_workspace.kind_filter.currentData() == "book"
        assert restored_workspace.tag_filter_input.text() == "classic"
        assert restored_workspace.group_filter.currentData() == "status"
        assert "Итого: 2" in restored_workspace.summary_label.text()
        assert model.rowCount() == 4
    finally:
        if workspace is not None:
            workspace.deleteLater()
        if restored_workspace is not None:
            restored_workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_workspace_dark_theme_covers_preview_and_popups(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("dossier_workspace_dark_theme", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        database.create_dossier(
            kind="book",
            title="Always Coming Home",
            summary="Notes from a future anthropology.",
            description="",
            status="planned",
            metadata={"author_display": "Ursula K. Le Guin"},
        )

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        workspace = dossier_workspace.DossierWorkspace()

        preview_card = workspace.findChild(QFrame, "DossierPreviewCard")
        assert preview_card is not None

        stylesheet = workspace.styleSheet()
        assert "QFrame#DossierPreviewCard" in stylesheet
        assert "QComboBox QAbstractItemView" in stylesheet
        assert "QMenu {" in stylesheet
        assert "QSplitter::handle" in stylesheet
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_workspace_quick_actions_create_idea_and_task(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    settings = QSettings()
    settings.remove("workspace/dossier/search_text")
    settings.remove("workspace/dossier/filters")

    db_path = unique_temp_path("dossier_workspace_quick_actions", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    host = None
    try:
        dossier = database.create_dossier(
            kind="book",
            title="Roadside Picnic",
            summary="Zone as a source of ideas.",
            description="Use as a reference for restricted spaces and dangerous wonder.",
            status="active",
            tags=["sci-fi"],
            metadata={"author_display": "Arkady and Boris Strugatsky"},
        )

        class _PageIdeas:
            def __init__(self) -> None:
                self.selected: list[int] = []

            def select_idea(self, idea_id: int) -> bool:
                self.selected.append(idea_id)
                return True

        class _PageTasks:
            def __init__(self) -> None:
                self.focused: list[int] = []

            def focus_task(self, task_id: int) -> bool:
                self.focused.append(task_id)
                return True

        class _Host(QWidget):
            MODE_IDEAS = "ideas"
            MODE_TASKS = "tasks"

            def __init__(self) -> None:
                super().__init__()
                self.modes: list[str] = []
                self.page_ideas = _PageIdeas()
                self.page_tasks = _PageTasks()

            def set_mode(self, mode_name: str) -> None:
                self.modes.append(mode_name)

        host = _Host()
        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        workspace = dossier_workspace.DossierWorkspace(parent=host)
        workspace.on_enter()
        QApplication.processEvents()

        assert workspace.get_selection() == dossier.id
        tasks_before = database.fetch_tasks()

        workspace._create_idea_from_dossier()
        QApplication.processEvents()
        workspace._create_task_from_dossier()
        QApplication.processEvents()

        ideas = database.fetch_ideas()
        tasks = database.fetch_tasks()
        created_tasks = [item for item in tasks if item.title == "Roadside Picnic"]
        links = database.fetch_dossier_links(dossier.id)

        assert len(ideas) == 1
        assert ideas[0].title == "Roadside Picnic"
        assert ideas[0].source == "Досье: Roadside Picnic"
        assert len(tasks) == len(tasks_before) + 1
        assert len(created_tasks) == 1
        assert "Источник: досье" in created_tasks[0].description
        assert {(link.entity_kind, link.entity_id) for link in links} == {
            ("idea", ideas[0].id),
            ("task", created_tasks[0].id),
        }
        assert host.page_ideas.selected == [ideas[0].id]
        assert host.page_tasks.focused == [created_tasks[0].id]
        assert host.modes == ["ideas", "tasks"]
    finally:
        if workspace is not None:
            workspace.deleteLater()
        if host is not None:
            host.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_workspace_switches_between_view_modes(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    settings = QSettings()
    settings.remove("workspace/dossier/search_text")
    settings.remove("workspace/dossier/filters")

    db_path = unique_temp_path("dossier_workspace_view_modes", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        first = database.create_dossier(
            kind="book",
            title="A Fire Upon the Deep",
            summary="Zones of thought.",
            description="",
            status="active",
            rating=None,
            tags=["space"],
            metadata={"author_display": "Vernor Vinge"},
        )
        second = database.create_dossier(
            kind="film",
            title="Solaris",
            summary="Memory over the ocean.",
            description="",
            status="completed",
            rating=9,
            tags=["arthouse"],
            metadata={"director": "Andrei Tarkovsky"},
        )
        task = database.create_task(
            title="Write Solaris comparison notes",
            description="",
            day=date(2026, 3, 13),
            time_text="10:00",
            priority="Medium",
        )
        database.add_dossier_link(second.id, "task", task.id)

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        workspace = dossier_workspace.DossierWorkspace()
        workspace.on_enter()
        QApplication.processEvents()

        workspace._set_view_mode("shelf")
        QApplication.processEvents()
        assert workspace.left_mode_stack.currentIndex() == 1
        assert workspace.shelf_view.count() == 2

        workspace._set_view_mode("matrix")
        QApplication.processEvents()
        assert workspace.left_mode_stack.currentIndex() == 2
        assert workspace.matrix_view.count() >= 4

        workspace._set_view_mode("links")
        QApplication.processEvents()
        assert workspace.left_mode_stack.currentIndex() == 3
        assert workspace.links_mode_view.count() == 2

        workspace.links_mode_view.setCurrentRow(1)
        QApplication.processEvents()
        assert workspace.get_selection() in {first.id, second.id}
        assert workspace.preview_title_label.text() in {"A Fire Upon the Deep", "Solaris"}
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_workspace_export_and_import_csv(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    settings = QSettings()
    settings.remove("workspace/dossier/search_text")
    settings.remove("workspace/dossier/filters")

    source_db_path = unique_temp_path("dossier_workspace_export_source", ".sqlite3")
    target_db_path = unique_temp_path("dossier_workspace_export_target", ".sqlite3")
    export_path = unique_temp_path("dossier_workspace_export", ".csv")
    source_db = Database(path=source_db_path)
    target_db = Database(path=target_db_path)
    source_workspace = None
    target_workspace = None
    try:
        source_db.create_dossier(
            kind="writer",
            title="Stanislaw Lem",
            summary="Philosophical science fiction.",
            description="Useful for tone, speculation and epistemic uncertainty.",
            status="completed",
            tags=["classic", "sci-fi"],
            metadata={"country": "Poland", "languages": ["Polish"]},
        )

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: source_db)
        monkeypatch.setattr(
            dossier_workspace_module.QFileDialog,
            "getSaveFileName",
            staticmethod(lambda *args, **kwargs: (str(export_path), "CSV (*.csv)")),
        )
        source_workspace = dossier_workspace.DossierWorkspace()
        source_workspace._export_dossiers_csv()
        QApplication.processEvents()

        assert export_path.exists()
        csv_text = export_path.read_text(encoding="utf-8")
        assert "Stanislaw Lem" in csv_text
        assert "metadata_json" in csv_text

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: target_db)
        monkeypatch.setattr(
            dossier_workspace_module.QFileDialog,
            "getOpenFileName",
            staticmethod(lambda *args, **kwargs: (str(export_path), "CSV (*.csv)")),
        )
        target_workspace = dossier_workspace.DossierWorkspace()
        target_workspace._import_dossiers_csv()
        QApplication.processEvents()

        imported = [item for item in target_db.fetch_dossiers() if item.title == "Stanislaw Lem"]
        assert len(imported) == 1
        assert imported[0].metadata == {"country": "Poland", "languages": ["Polish"]}
    finally:
        if source_workspace is not None:
            source_workspace.deleteLater()
        if target_workspace is not None:
            target_workspace.deleteLater()
        source_db.close()
        target_db.close()
        source_db_path.unlink(missing_ok=True)
        target_db_path.unlink(missing_ok=True)
        export_path.unlink(missing_ok=True)
