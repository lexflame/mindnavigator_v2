"""NotesController class module for notes workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .notes_model import NotesModel

class NotesController(QObject):
    note_open_requested = Signal(int)

    def __init__(self, model: NotesModel, state: NoteWorkspaceState, parent=None):
        super().__init__(parent)
        self._model = model
        self._state = state
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(2000)
        self._autosave_timer.timeout.connect(self._autosave_stub)

    def initialize(self):
        self._model.set_loading(True)
        QTimer.singleShot(450, lambda: self._model.set_loading(False))

    def set_search(self, text: str):
        self._state.search_text = text
        self._model.set_search(text)

    def set_filter(self, mode: str):
        self._state.filter_mode = mode
        self._model.set_filter_mode(mode)

    def set_project_filter(self, project: Optional[str]):
        self._state.project_filter = project
        self._model.set_project_filter(project)

    def set_tag_filter(self, tag: Optional[str]):
        self._state.tag_filter = tag
        self._model.set_tag_filter(tag)

    def set_task_filter(self, task_id: Optional[int]):
        self._state.task_filter = task_id
        self._model.set_task_filter(task_id)

    def open_note(self, note_id: int):
        self._state.selected_note_id = note_id
        self.note_open_requested.emit(note_id)

    def create_note(self, title: str = "Новая заметка", project: str = "Inbox"):
        note = self._model.create_note(
            title,
            "Краткое описание...",
            ["draft"],
            project,
        )
        self.open_note(note.id)

    def rename_note(self, note_id: int, title: str):
        note = self._model.note_by_id(note_id)
        if not note:
            return
        self._model.update_note(note_id, title, note.preview, note.tags)

    def toggle_favorite(self, note_id: int):
        self._model.toggle_favorite(note_id)

    def delete_note(self, note_id: int):
        self._model.delete_note(note_id)
        if self._state.selected_note_id == note_id:
            self._state.selected_note_id = None

    def start_autosave(self):
        if not self._autosave_timer.isActive():
            self._autosave_timer.start()

    def stop_autosave(self):
        if self._autosave_timer.isActive():
            self._autosave_timer.stop()

    def _autosave_stub(self):
        # TODO: интеграция с FastAPI/SQLite синхронизацией.
        pass

__all__ = ["NotesController"]
