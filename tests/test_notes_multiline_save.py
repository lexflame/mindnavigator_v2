from __future__ import annotations

from mindnavigator.storage import Database
from mindnavigator.workspaces.notes import normalize_note_body

def test_normalize_note_body_preserves_multiline_text() -> None:
    body = "first\r\nsecond\nthird\rfourth"

    normalized = normalize_note_body(body)

    assert normalized == "first\nsecond\nthird\nfourth"


def test_note_storage_keeps_text_after_line_breaks(unique_temp_path) -> None:
    db_path = unique_temp_path("notes_multiline", ".sqlite3")
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
