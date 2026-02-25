from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from mindnavigator.storage import Database, TaskAttachmentData


def _new_temp_db_path(prefix: str) -> Path:
    base_dir = Path.cwd() / ".pytest_dir" / "tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{prefix}_{uuid4().hex}.sqlite3"


def test_task_attachment_data_serialization_round_trip() -> None:
    payload = {
        "id": "12",
        "task_id": "7",
        "kind": "FiLe",
        "ref_id": "33",
        "created_at": "2026-02-25T10:00:00+00:00",
    }

    attachment = TaskAttachmentData.from_dict(payload)

    assert attachment.id == 12
    assert attachment.task_id == 7
    assert attachment.kind == "file"
    assert attachment.ref_id == 33
    assert attachment.to_dict() == {
        "id": 12,
        "task_id": 7,
        "kind": "file",
        "ref_id": 33,
        "created_at": "2026-02-25T10:00:00+00:00",
    }


def test_task_attachment_data_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        TaskAttachmentData.normalize_kind("unknown-kind")


def test_task_attachment_crud_with_database() -> None:
    db_path = _new_temp_db_path("task_attachment")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Attachment target",
            description="",
            day=date(2026, 2, 25),
            time_text="",
            priority="Medium",
        )
        note = database.create_note(
            title="Attachment note",
            preview="preview",
            tags=[],
            project="",
        )

        created = database.add_task_attachment(task.id, "NoTe", note.id)
        fetched = database.fetch_task_attachments(task.id)

        assert created.kind == "note"
        assert len(fetched) == 1
        assert fetched[0].to_dict() == created.to_dict()
        assert TaskAttachmentData.from_dict(created.to_dict()) == created

        database.delete_task_attachment(created.id)
        assert database.fetch_task_attachments(task.id) == []
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_attachment_supports_idea_entities() -> None:
    db_path = _new_temp_db_path("task_attachment_idea")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Attachment idea target",
            description="",
            day=date(2026, 2, 25),
            time_text="",
            priority="Medium",
        )
        idea = database.create_idea(
            title="Idea attachment",
            summary="Summary",
            body_md="Body",
        )

        created = database.add_task_attachment(task.id, "idea", idea.id)
        fetched = database.fetch_task_attachments(task.id)

        assert created.kind == "idea"
        assert len(fetched) == 1
        assert fetched[0].kind == "idea"
        assert fetched[0].ref_id == idea.id
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_attachment_add_rejects_non_positive_ids() -> None:
    db_path = _new_temp_db_path("task_attachment_invalid_ids")
    database = Database(path=db_path)
    try:
        with pytest.raises(ValueError):
            database.add_task_attachment(0, "note", 1)
        with pytest.raises(ValueError):
            database.add_task_attachment(1, "note", 0)
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
