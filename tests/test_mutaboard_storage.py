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
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
