from __future__ import annotations

import sqlite3
from datetime import timezone

from mindnavigator.storage import Database


def test_fetch_ideas_search_matches_summary_and_source(unique_temp_path) -> None:
    db_path = unique_temp_path("idea_search_summary_source", ".sqlite3")
    database = Database(path=db_path)
    try:
        summary_idea = database.create_idea(
            title="Alpha idea",
            summary="Unique framing text",
            body_md="Body",
            source="",
        )
        source_idea = database.create_idea(
            title="Beta idea",
            summary="",
            body_md="Body",
            source="Voice memo from tram",
        )
        database.create_idea(
            title="Gamma idea",
            summary="",
            body_md="Unrelated",
            source="",
        )

        summary_matches = database.fetch_ideas(search="framing")
        source_matches = database.fetch_ideas(search="tram")

        assert [item.id for item in summary_matches] == [summary_idea.id]
        assert [item.id for item in source_matches] == [source_idea.id]
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_fetch_ideas_normalizes_legacy_naive_timestamps(unique_temp_path) -> None:
    db_path = unique_temp_path("idea_search_naive_timestamps", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_idea(title="Naive legacy idea")
        with database._conn:
            database._conn.execute(
                "UPDATE ideas SET created_at = ?, updated_at = ? WHERE id = ?;",
                ("2026-05-20T10:00:00", "2026-05-20T11:00:00", created.id),
            )

        fetched = database.get_idea(created.id)
        items = database.fetch_ideas(search="naive legacy")

        assert fetched is not None
        assert fetched.created_at.tzinfo is not None
        assert fetched.created_at.tzinfo.utcoffset(fetched.created_at) == timezone.utc.utcoffset(fetched.created_at)
        assert fetched.updated_at.tzinfo is not None
        assert items
        assert items[0].updated_at.tzinfo is not None
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
