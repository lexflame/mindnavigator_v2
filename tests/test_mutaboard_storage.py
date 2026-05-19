from __future__ import annotations

from mindnavigator.storage import Database


def test_mutaboard_storage_persists_boards_columns_and_items(unique_temp_path) -> None:
    db_path = unique_temp_path("mutaboard_storage", ".sqlite3")
    database = Database(path=db_path)
    try:
        board = database.create_mutaboard(
            "Main Board",
            description="Board description",
            capture_text="Capture flow",
            planning_text="Planning flow",
            links_text="Link flow",
        )

        assert board.title == "Main Board"
        assert [column.kind for column in database.fetch_mutaboard_columns(board.id)] == ["task", "idea", "image"]

        database.add_mutaboard_column(board.id, "note")
        database.attach_mutaboard_item(board.id, "task", 101)
        version = database.create_mutaboard_version(
            board.id,
            title="Version A",
            description="Direction",
            why_yes="Fits the board",
            why_no="Need validation",
            checks_text="Check narrative",
            status="review",
        )
        solution = database.create_mutaboard_solution(
            board.id,
            title="Solution A",
            summary="Chosen path",
            why_selected="Strongest option",
            next_steps_text="Do next thing",
            status="accepted",
            selected_version_id=version.id,
            decided_at="2026-05-17",
        )
        database.add_mutaboard_link(
            board.id,
            source_kind="version",
            source_id=version.id,
            target_kind="solution",
            target_id=solution.id,
            link_type="transforms_to",
        )
        updated = database.update_mutaboard(
            board.id,
            title="Updated Board",
            description="Updated description",
            capture_text="Updated capture",
            planning_text="Updated planning",
            links_text="Updated links",
        )

        assert updated.title == "Updated Board"
        assert [column.kind for column in database.fetch_mutaboard_columns(board.id)] == ["task", "idea", "image", "note"]
        items = database.fetch_mutaboard_items(board.id)
        assert [(item.entity_kind, item.entity_id) for item in items] == [("task", 101)]
        versions = database.fetch_mutaboard_versions(board.id)
        solutions = database.fetch_mutaboard_solutions(board.id)
        links = database.fetch_mutaboard_links(board.id)
        assert [(item.title, item.status) for item in versions] == [("Version A", "review")]
        assert [(item.title, item.status, item.selected_version_id) for item in solutions] == [("Solution A", "accepted", version.id)]
        assert [(item.source_kind, item.target_kind, item.link_type) for item in links] == [("version", "solution", "transforms_to")]
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
