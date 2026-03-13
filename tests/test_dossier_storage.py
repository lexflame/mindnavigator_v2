from __future__ import annotations

from datetime import date

import pytest

from mindnavigator.storage import Database, DossierData, DossierLinkData


def test_dossier_data_serialization_round_trip() -> None:
    payload = {
        "id": "12",
        "kind": "BoOk",
        "title": "Dune",
        "summary": "Sci-fi classic",
        "description": "Arrakis",
        "tags": [" sci-fi ", "classic", "classic"],
        "status": "AcTiVe",
        "rating": "9",
        "source": "Shelf",
        "cover_image": "covers/dune.jpg",
        "metadata": {
            "author_display": "Frank Herbert",
            "publication_year": "1965",
            "pages": 412,
        },
        "created_at": "2026-03-13T10:00:00+00:00",
        "updated_at": "2026-03-13T10:05:00+00:00",
    }

    dossier = DossierData.from_dict(payload)

    assert dossier.id == 12
    assert dossier.kind == "book"
    assert dossier.status == "active"
    assert dossier.rating == 9
    assert dossier.tags == ["sci-fi", "classic"]
    assert dossier.metadata == {
        "author_display": "Frank Herbert",
        "publication_year": 1965,
        "pages": 412,
    }
    assert dossier.to_dict()["kind"] == "book"


def test_dossier_link_data_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        DossierLinkData.normalize_entity_kind("project")


def test_dossier_storage_crud_and_link_filters(unique_temp_path) -> None:
    db_path = unique_temp_path("dossier_storage", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Read Dune",
            description="",
            day=date(2026, 3, 13),
            time_text="",
            priority="Medium",
        )
        note = database.create_note(
            title="Dune notes",
            preview="Desert power",
            tags=["book"],
            project="",
        )
        character = database.create_character(
            name="Paul Atreides",
            role="Heir of House Atreides",
        )

        created = database.create_dossier(
            kind="book",
            title="Dune",
            summary="Epic sci-fi saga",
            description="Set on Arrakis.",
            tags=["sci-fi", "classic"],
            status="active",
            rating=9,
            source="Shelf",
            cover_image="covers/dune.jpg",
            metadata={
                "author_display": "Frank Herbert",
                "publication_year": 1965,
                "pages": 412,
                "language": "EN",
            },
        )
        link_task = database.add_dossier_link(created.id, "task", task.id)
        link_note = database.add_dossier_link(created.id, "note", note.id)

        fetched = database.get_dossier(created.id)
        filtered_by_kind = database.fetch_dossiers(kind="book")
        filtered_by_link = database.fetch_dossiers(linked_entity_kind="task", linked_entity_id=task.id)
        links = database.fetch_dossier_links(created.id)
        task_link_options = database.fetch_dossier_link_options("task", "dune")
        character_link_options = database.fetch_dossier_link_options("character", "paul")

        assert fetched is not None
        assert fetched.metadata["publication_year"] == 1965
        assert [item.id for item in filtered_by_kind] == [created.id]
        assert [item.id for item in filtered_by_link] == [created.id]
        assert {(item.entity_kind, item.entity_id) for item in links} == {
            ("task", task.id),
            ("note", note.id),
        }
        assert task_link_options == [(task.id, "Read Dune")]
        assert character_link_options == [(character.id, "Paul Atreides · Heir of House Atreides")]
        assert DossierLinkData.from_dict(link_task.to_dict()) == link_task
        assert "Task: Read Dune" in database.describe_dossier_link_target(link_task.entity_kind, link_task.entity_id)

        updated = database.update_dossier(
            dossier_id=created.id,
            kind="book",
            title="Dune Messiah",
            summary="Sequel",
            description="Second book",
            tags=["sci-fi", "sequel"],
            status="completed",
            rating=8,
            source="Library",
            cover_image="covers/dune_messiah.jpg",
            metadata={
                "author_display": "Frank Herbert",
                "publication_year": 1969,
                "series": "Dune",
            },
        )

        assert updated.title == "Dune Messiah"
        assert updated.status == "completed"
        assert updated.metadata["series"] == "Dune"

        database.delete_dossier_link(link_note.id)
        assert {(item.entity_kind, item.entity_id) for item in database.fetch_dossier_links(created.id)} == {
            ("task", task.id),
        }

        database.delete_dossier(created.id)
        assert database.get_dossier(created.id) is None
        assert database.fetch_dossiers() == []
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_storage_rejects_invalid_metadata_for_kind(unique_temp_path) -> None:
    db_path = unique_temp_path("dossier_invalid_metadata", ".sqlite3")
    database = Database(path=db_path)
    try:
        with pytest.raises(ValueError):
            database.create_dossier(
                kind="film",
                title="Alien",
                metadata={"author_display": "Ridley Scott"},
            )
        with pytest.raises(ValueError):
            database.create_dossier(
                kind="writer",
                title="Frank Herbert",
                metadata={"birth_year": -1},
            )
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_dossier_storage_ignores_unknown_metadata_keys_on_read(unique_temp_path) -> None:
    db_path = unique_temp_path("dossier_unknown_metadata", ".sqlite3")
    database = Database(path=db_path)
    try:
        with database._conn:
            database._conn.execute(
                """
                INSERT INTO dossiers (
                    kind, title, summary, description, tags, status, rating,
                    source, cover_image, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, '', '', '[]', 'planned', NULL, '', '', ?, ?, ?);
                """,
                (
                    "book",
                    "Imported dossier",
                    '{"author_display":"Frank Herbert","unexpected":"future-field"}',
                    "2026-03-13T10:00:00+00:00",
                    "2026-03-13T10:00:00+00:00",
                ),
            )

        dossiers = database.fetch_dossiers()

        assert len(dossiers) == 1
        assert dossiers[0].metadata == {"author_display": "Frank Herbert"}
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
