from __future__ import annotations

from datetime import date

import pytest

from mindnavigator.storage import Database


def test_character_storage_crud_and_entity_links(unique_temp_path) -> None:
    db_path = unique_temp_path("characters_mn204", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project(
            area="Product",
            title="Main Project",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        task = database.create_task(
            title="Main Task",
            description="Task Description",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
            project_id=project.id,
        )
        note = database.create_note(
            title="Main Note",
            preview="Preview",
            tags=["alpha"],
            project="Inbox",
        )
        character = database.create_character(
            name="Alice",
            role="Lead",
            description="Key actor",
            tags=["hero", "core"],
        )

        updated = database.update_character(
            character.id,
            name="Alice Updated",
            role="Lead",
            description="Updated profile",
            tags=["hero"],
        )
        assert updated.name == "Alice Updated"
        assert updated.tags == ["hero"]

        task_link = database.add_character_link(character.id, "task", task.id)
        note_link = database.add_character_link(character.id, "note", note.id)

        links = database.fetch_character_links(character.id)
        assert {(item.entity_kind, item.entity_id) for item in links} == {
            ("task", task.id),
            ("note", note.id),
        }
        assert "Задача:" in database.describe_character_link_target(task_link.entity_kind, task_link.entity_id)

        filtered = database.fetch_characters(linked_entity_kind="task", linked_entity_id=task.id)
        assert [item.id for item in filtered] == [character.id]

        database.delete_character_link(note_link.id)
        links_after_delete = database.fetch_character_links(character.id)
        assert [item.id for item in links_after_delete] == [task_link.id]

        database.delete_character(character.id)
        assert database.fetch_characters() == []
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_character_link_options_and_validation(unique_temp_path) -> None:
    db_path = unique_temp_path("characters_mn204_options", ".sqlite3")
    database = Database(path=db_path)
    try:
        project = database.create_project(
            area="AI",
            title="Codex Project",
            updated=date(2026, 3, 6),
            priority="High",
        )
        wishlist = database.create_wishlist("Wishlist A")
        character = database.create_character(name="Bob")

        project_options = database.fetch_character_link_options("project", search_text="codex")
        assert (project.id, "Codex Project · AI") in project_options

        wishlist_options = database.fetch_character_link_options("wishlist")
        assert (wishlist.id, "Wishlist A") in wishlist_options

        with pytest.raises(ValueError):
            database.fetch_character_link_options("unsupported")

        with pytest.raises(ValueError):
            database.add_character_link(character.id, "unsupported", 1)

        with pytest.raises(ValueError):
            database.add_character_link(character.id, "project", 999999)
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
