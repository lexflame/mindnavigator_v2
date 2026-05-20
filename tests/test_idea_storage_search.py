from __future__ import annotations

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
