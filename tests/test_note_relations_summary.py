from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication, QWidget, QToolButton

from mindnavigator.storage import Database
from mindnavigator.workspaces.notes import note_workspace
from mindnavigator.workspaces.notes import notes_model as notes_model_module
from mindnavigator.workspaces.notes.notes_model import NotesModel


class _DummyPage:
    def __init__(self) -> None:
        self.selected: list[int] = []

    def focus_task(self, task_id: int) -> bool:
        self.selected.append(task_id)
        return True

    def select_idea(self, idea_id: int) -> bool:
        self.selected.append(idea_id)
        return True

    def select_dossier(self, dossier_id: int) -> bool:
        self.selected.append(dossier_id)
        return True

    def select_marker(self, marker_id: int) -> bool:
        self.selected.append(marker_id)
        return True


class _NavigationHost(QWidget):
    MODE_TASKS = "Задачи"
    MODE_IDEAS = "Идеи"
    MODE_DOSSIER = "Досье"
    MODE_MAPS = "Карты"

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, str]] = []
        self.page_tasks = _DummyPage()
        self.page_ideas = _DummyPage()
        self.page_dossier = _DummyPage()
        self.page_maps = _DummyPage()

    def set_mode(self, mode_name: str) -> None:
        self.calls.append(("mode", mode_name))


def test_notes_model_builds_relation_summary(monkeypatch, unique_temp_path) -> None:
    db_path = unique_temp_path("notes_relation_summary", ".sqlite3")
    database = Database(path=db_path)
    try:
        note = database.create_note(title="Signal note", preview="Body", tags=["ref"], project="")
        task = database.create_task(
            title="Task link",
            description="",
            day=date(2026, 5, 21),
            time_text="12:00",
            priority="Medium",
        )
        database.add_task_attachment(task.id, "note", note.id)
        idea = database.create_idea(title="Idea link", summary="", body_md="")
        database.add_idea_relation(idea.id, "note", note.id, "related")
        dossier = database.create_dossier(kind="book", title="Dossier link")
        database.add_dossier_link(dossier.id, "note", note.id)
        map_item = database.create_map("Map link", "", "", "", 2, 2)
        database.upsert_map_marker(0, map_item.id, "Marker link", 10, 10, "#ffffff", "point", 16, note_ids=[note.id])

        monkeypatch.setattr(note_workspace, "get_database", lambda: database)
        monkeypatch.setattr(notes_model_module, "get_database", lambda: database)
        model = NotesModel()
        note_item = model.note_by_id(note.id)

        assert note_item is not None
        assert note_item.relation_summary == "Задачи 1 · Идеи 1 · Досье 1 · Метки 1"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_note_workspace_shows_clickable_relation_badges(monkeypatch, unique_temp_path) -> None:
    app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("notes_relation_badges", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        note = database.create_note(title="Signal note", preview="Body", tags=["ref"], project="")
        dossier = database.create_dossier(kind="book", title="Dossier link")
        database.add_dossier_link(dossier.id, "note", note.id)

        host = _NavigationHost()
        monkeypatch.setattr(note_workspace, "get_database", lambda: database)
        monkeypatch.setattr(notes_model_module, "get_database", lambda: database)
        workspace = note_workspace.NoteWorkspace(parent=host)
        workspace.show()
        workspace.select_note(note.id)
        app.processEvents()

        badges = [
            button
            for button in workspace.findChildren(QToolButton)
            if button.objectName() == "NotesRelationBadge"
        ]
        assert [button.text() for button in badges] == ["Досье 1"]

        badges[0].click()
        app.processEvents()

        assert host.calls == [("mode", host.MODE_DOSSIER)]
        assert host.page_dossier.selected == [dossier.id]
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
