"""NotesModel class module for notes workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class NotesModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = get_database()
        self._notes: List[NoteItem] = []
        self._rows: List[NoteRow] = []
        self._filter_mode = "Все"
        self._search = ""
        self._project_filter: Optional[str] = None
        self._tag_filter: Optional[str] = None
        self._task_filter_id: Optional[int] = None
        self._loading = True
        self._load_notes()

    def _load_notes(self):
        relation_summaries = self._build_note_relation_summaries()
        self._notes = [
            NoteItem(
                note.id,
                note.title,
                note.preview,
                note.tags,
                note.updated,
                note.project,
                favorite=note.favorite,
                attachment=note.attachment,
                locked=note.locked,
                relation_summary=relation_summaries.get(note.id, ""),
            )
            for note in self._db.fetch_notes()
        ]
        self._rebuild()

    def reload(self) -> None:
        self._load_notes()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        if self._loading:
            return 6
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid():
            return None
        if self._loading:
            if role == NoteRoles.RowType:
                return "skeleton"
            return None

        row = self._rows[index.row()]

        if role == NoteRoles.RowType:
            return "category" if isinstance(row, NoteCategoryRow) else "note"
        if isinstance(row, NoteCategoryRow):
            if role == NoteRoles.Title:
                return row.category
            if role == Qt.ItemDataRole.DisplayRole:
                return row.category
            return None
        note = row
        if role == NoteRoles.NoteId:
            return note.id
        if role == NoteRoles.Title:
            return note.title
        if role == NoteRoles.Preview:
            return note.preview
        if role == NoteRoles.Tags:
            return note.tags
        if role == NoteRoles.Updated:
            return note.updated
        if role == NoteRoles.Project:
            return note.project
        if role == NoteRoles.Favorite:
            return note.favorite
        if role == NoteRoles.Attachment:
            return note.attachment
        if role == NoteRoles.Locked:
            return note.locked
        if role == NoteRoles.RelationSummary:
            return note.relation_summary
        if role == Qt.ItemDataRole.DisplayRole:
            return note.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        if self._loading:
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        row = self._rows[index.row()]
        if isinstance(row, NoteCategoryRow):
            return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags |= Qt.ItemFlag.ItemIsSelectable
        return flags

    def set_loading(self, loading: bool):
        if self._loading == loading:
            return
        self.beginResetModel()
        self._loading = loading
        self.endResetModel()

    def is_loading(self) -> bool:
        return self._loading

    def set_filter_mode(self, mode: str):
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_project_filter(self, project: Optional[str]):
        self._project_filter = project
        self._task_filter_id = None
        self._filter_mode = "По проекту" if project else self._filter_mode
        self._rebuild()

    def set_tag_filter(self, tag: Optional[str]):
        self._tag_filter = tag
        self._filter_mode = "По тегу" if tag else self._filter_mode
        self._rebuild()

    def set_task_filter(self, task_id: Optional[int]):
        self._task_filter_id = task_id
        self._project_filter = None
        if task_id is not None:
            self._filter_mode = "По задаче"
        self._rebuild()

    def add_note(self, note: NoteItem):
        self._notes.insert(0, note)
        self._rebuild()

    def update_note(self, note_id: int, title: str, preview: str, tags: List[str]):
        updated_note = self._db.update_note(note_id, title, preview, tags)
        self._notes = [
            NoteItem(
                item.id,
                updated_note.title if item.id == note_id else item.title,
                updated_note.preview if item.id == note_id else item.preview,
                updated_note.tags if item.id == note_id else item.tags,
                updated_note.updated if item.id == note_id else item.updated,
                updated_note.project if item.id == note_id else item.project,
                favorite=updated_note.favorite if item.id == note_id else item.favorite,
                attachment=updated_note.attachment if item.id == note_id else item.attachment,
                locked=updated_note.locked if item.id == note_id else item.locked,
                relation_summary=item.relation_summary,
            )
            for item in self._notes
        ]
        self._rebuild()

    def note_by_id(self, note_id: int) -> Optional[NoteItem]:
        for note in self._notes:
            if note.id == note_id:
                return note
        return None

    def projects(self) -> List[str]:
        return sorted({normalize_note_category(note.project) for note in self._notes})

    def toggle_favorite(self, note_id: int):
        updated_note = self._db.toggle_note_favorite(note_id)
        self._notes = [
            NoteItem(
                item.id,
                updated_note.title if item.id == note_id else item.title,
                updated_note.preview if item.id == note_id else item.preview,
                updated_note.tags if item.id == note_id else item.tags,
                updated_note.updated if item.id == note_id else item.updated,
                updated_note.project if item.id == note_id else item.project,
                favorite=updated_note.favorite if item.id == note_id else item.favorite,
                attachment=updated_note.attachment if item.id == note_id else item.attachment,
                locked=updated_note.locked if item.id == note_id else item.locked,
                relation_summary=item.relation_summary,
            )
            for item in self._notes
        ]
        self._rebuild()

    def _build_note_relation_summaries(self) -> dict[int, str]:
        counts: dict[int, dict[str, int]] = {}

        def bump(note_id: int, label: str) -> None:
            bucket = counts.setdefault(int(note_id), {})
            bucket[label] = bucket.get(label, 0) + 1

        for task in self._db.fetch_tasks():
            for attachment in self._db.fetch_task_attachments(task.id):
                if attachment.kind == "note":
                    bump(attachment.ref_id, "Задачи")

        active_ideas = self._db.fetch_ideas(archived=False)
        archived_ideas = [idea for idea in self._db.fetch_ideas(archived=True) if idea.id not in {item.id for item in active_ideas}]
        for idea in [*active_ideas, *archived_ideas]:
            for relation in self._db.fetch_idea_relations(idea.id):
                if (relation.entity_type or "").strip().lower() == "note":
                    bump(relation.entity_id, "Идеи")

        fetch_dossiers = getattr(self._db, "fetch_dossiers", None)
        fetch_dossier_links = getattr(self._db, "fetch_dossier_links", None)
        if callable(fetch_dossiers) and callable(fetch_dossier_links):
            for dossier in fetch_dossiers():
                for link in fetch_dossier_links(dossier.id):
                    if (link.entity_kind or "").strip().lower() == "note":
                        bump(link.entity_id, "Досье")

        fetch_markers = getattr(self._db, "fetch_map_markers", None)
        if callable(fetch_markers):
            for marker in fetch_markers():
                for note_id in getattr(marker, "note_ids", []):
                    bump(note_id, "Метки")

        return {
            note_id: " · ".join(
                f"{label} {bucket[label]}"
                for label in ("Задачи", "Идеи", "Досье", "Метки")
                if bucket.get(label)
            )
            for note_id, bucket in counts.items()
        }

    def create_note(
        self,
        title: str,
        preview: str,
        tags: List[str],
        project: str,
    ) -> NoteItem:
        created = self._db.create_note(title, preview, tags, project)
        note = NoteItem(
            created.id,
            created.title,
            created.preview,
            created.tags,
            created.updated,
            created.project,
            favorite=created.favorite,
            attachment=created.attachment,
            locked=created.locked,
        )
        self.add_note(note)
        return note

    def delete_note(self, note_id: int):
        self._db.delete_note(note_id)
        self._notes = [n for n in self._notes if n.id != note_id]
        self._rebuild()

    def _rebuild(self):
        if self._loading:
            self.beginResetModel()
            self._rows = []
            self.endResetModel()
            return

        notes = list(self._notes)

        if self._filter_mode == "Избранные":
            notes = [n for n in notes if n.favorite]
        elif self._filter_mode == "Последние":
            notes.sort(key=lambda n: n.updated, reverse=True)
            notes = notes[:12]
        elif self._filter_mode == "По задаче" and self._task_filter_id is not None:
            task_project = None
            for task in self._db.fetch_tasks():
                if task.id == self._task_filter_id:
                    task_project = task.project_title
                    break
            if task_project:
                notes = [n for n in notes if n.project == task_project]
            else:
                notes = []
        elif self._filter_mode == "По проекту" and self._project_filter:
            notes = [n for n in notes if n.project == self._project_filter]
        elif self._filter_mode == "По тегу" and self._tag_filter:
            notes = [n for n in notes if self._tag_filter in n.tags]

        if self._search:
            notes = [
                n
                for n in notes
                if self._search in n.title.lower()
                or self._search in n.preview.lower()
                or any(self._search in tag.lower() for tag in n.tags)
            ]

        notes.sort(key=lambda n: n.updated, reverse=True)
        self.beginResetModel()
        self._rows = group_notes_by_category(notes)
        self.endResetModel()

__all__ = ["NotesModel"]
