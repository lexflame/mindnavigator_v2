from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from mindnavigator.storage import Database
from mindnavigator.workspaces.notes_workspace import normalize_note_body


def _new_temp_db_path(prefix: str) -> Path:
    base_dir = Path.cwd() / ".pytest_dir" / "tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{prefix}_{uuid4().hex}.sqlite3"


def test_normalize_note_body_preserves_multiline_text() -> None:
    body = "first\r\nsecond\nthird\rfourth"

    normalized = normalize_note_body(body)

    assert normalized == "first\nsecond\nthird\nfourth"


def test_note_storage_keeps_text_after_line_breaks() -> None:
    db_path = _new_temp_db_path("notes_multiline")
    database = Database(path=db_path)
    try:
        created = database.create_note(
            title="Multiline note",
            preview="line-1\nline-2\nline-3",
            tags=[],
            project="",
        )

        updated = database.update_note(
            note_id=created.id,
            title=created.title,
            preview="alpha\nbeta\ngamma",
            tags=[],
        )
        fetched = next(note for note in database.fetch_notes() if note.id == created.id)

        assert updated.preview == "alpha\nbeta\ngamma"
        assert fetched.preview == "alpha\nbeta\ngamma"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
