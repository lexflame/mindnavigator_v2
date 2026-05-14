from __future__ import annotations

import pytest

from mindnavigator.storage import Database


def test_idea_images_round_trip(unique_temp_path) -> None:
    db_path = unique_temp_path("idea_images_round_trip", ".sqlite3")
    database = Database(path=db_path)
    try:
        idea = database.create_idea(title="Idea with image")
        database.upsert_cloud_file(
            rel_path="ideas/sample.png",
            name="sample.png",
            description="",
            checksum="checksum-1",
            hash_value="hash-1",
            size=128,
            is_image=True,
            valid=True,
        )

        attached = database.add_idea_image(idea.id, "ideas/sample.png")
        assert attached.idea_id == idea.id
        assert attached.rel_path == "ideas/sample.png"
        assert attached.caption == ""

        fetched = database.fetch_idea_images(idea.id)
        assert [item.rel_path for item in fetched] == ["ideas/sample.png"]

        updated = database.update_idea_image(attached.id, "Ключевой экран")
        assert updated.caption == "Ключевой экран"
        assert database.fetch_idea_images(idea.id)[0].caption == "Ключевой экран"

        database.delete_idea_image(attached.id)
        assert database.fetch_idea_images(idea.id) == []
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_idea_images_reject_non_image_files(unique_temp_path) -> None:
    db_path = unique_temp_path("idea_images_non_image", ".sqlite3")
    database = Database(path=db_path)
    try:
        idea = database.create_idea(title="Idea with invalid attachment")
        database.upsert_cloud_file(
            rel_path="ideas/spec.pdf",
            name="spec.pdf",
            description="",
            checksum="checksum-2",
            hash_value="hash-2",
            size=256,
            is_image=False,
            valid=True,
        )

        with pytest.raises(ValueError, match="изображ"):
            database.add_idea_image(idea.id, "ideas/spec.pdf")
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
