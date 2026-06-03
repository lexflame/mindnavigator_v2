from __future__ import annotations

from datetime import date

import pytest

from mindnavigator.storage import Database, TaskAttachmentData

def test_task_attachment_data_serialization_round_trip() -> None:
    payload = {
        "id": "12",
        "task_id": "7",
        "kind": "FiLe",
        "ref_id": "33",
        "created_at": "2026-02-25T10:00:00+00:00",
        "comment": "Local task comment",
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
        "comment": "Local task comment",
    }


def test_task_attachment_data_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        TaskAttachmentData.normalize_kind("unknown-kind")


def test_task_attachment_crud_with_database(unique_temp_path) -> None:
    db_path = unique_temp_path("task_attachment", ".sqlite3")
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


def test_task_attachment_comment_updates_without_changing_link(unique_temp_path) -> None:
    db_path = unique_temp_path("task_attachment_comment", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task("Comment target", "", date(2026, 2, 25), "", "Medium")
        note = database.create_note("Linked note", "", [], "")
        attachment = database.add_task_attachment(task.id, "note", note.id)

        updated = database.update_task_attachment_comment(attachment.id, "  Context for this task  ")

        assert updated.comment == "Context for this task"
        assert updated.kind == attachment.kind
        assert updated.ref_id == attachment.ref_id
        assert database.fetch_task_attachments(task.id)[0].comment == "Context for this task"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_attachment_supports_idea_entities(unique_temp_path) -> None:
    db_path = unique_temp_path("task_attachment_idea", ".sqlite3")
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


def test_task_attachment_supports_task_entities(unique_temp_path) -> None:
    db_path = unique_temp_path("task_attachment_task", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Attachment task target",
            description="",
            day=date(2026, 2, 25),
            time_text="",
            priority="Medium",
        )
        linked_task = database.create_task(
            title="Attached task",
            description="Linked body",
            day=date(2026, 2, 26),
            time_text="09:00",
            priority="High",
        )

        created = database.add_task_attachment(task.id, "task", linked_task.id)
        fetched = database.fetch_task_attachments(task.id)

        assert created.kind == "task"
        assert len(fetched) == 1
        assert fetched[0].kind == "task"
        assert fetched[0].ref_id == linked_task.id
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_attachment_add_rejects_non_positive_ids(unique_temp_path) -> None:
    db_path = unique_temp_path("task_attachment_invalid_ids", ".sqlite3")
    database = Database(path=db_path)
    try:
        with pytest.raises(ValueError):
            database.add_task_attachment(0, "note", 1)
        with pytest.raises(ValueError):
            database.add_task_attachment(1, "note", 0)
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_attachment_rejects_same_task_as_attachment(unique_temp_path) -> None:
    db_path = unique_temp_path("task_attachment_self_task", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Self attachment task",
            description="",
            day=date(2026, 2, 25),
            time_text="",
            priority="Medium",
        )

        with pytest.raises(ValueError):
            database.add_task_attachment(task.id, "task", task.id)
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_mentions_auto_attach_linked_tasks_on_create(unique_temp_path) -> None:
    db_path = unique_temp_path("task_attachment_mentions_create", ".sqlite3")
    database = Database(path=db_path)
    try:
        linked_task = database.create_task(
            title="Linked task",
            description="",
            day=date(2026, 2, 24),
            time_text="",
            priority="Medium",
        )

        task = database.create_task(
            title=f"Main task for MN-{linked_task.id}",
            description=f"Body with duplicate mention #{linked_task.id} and MN-{linked_task.id}.",
            day=date(2026, 2, 25),
            time_text="",
            priority="Medium",
        )

        fetched = database.fetch_task_attachments(task.id)

        assert len(fetched) == 1
        assert fetched[0].kind == "task"
        assert fetched[0].ref_id == linked_task.id
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_mentions_auto_attach_linked_tasks_on_update(unique_temp_path) -> None:
    db_path = unique_temp_path("task_attachment_mentions_update", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Main task",
            description="",
            day=date(2026, 2, 25),
            time_text="",
            priority="Medium",
        )
        linked_task = database.create_task(
            title="Linked later",
            description="",
            day=date(2026, 2, 26),
            time_text="10:00",
            priority="High",
        )

        database.update_task(
            task_id=task.id,
            title=f"Main task #{linked_task.id}",
            description=f"Also MN-{task.id} should ignore self and MN-99999 should ignore missing.",
            day=task.day,
            time_text=task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=task.project_id,
            parent_id=task.parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            is_plan_task=task.is_plan_task,
            plan_order=task.plan_order,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
        )

        fetched = database.fetch_task_attachments(task.id)

        assert len(fetched) == 1
        assert fetched[0].kind == "task"
        assert fetched[0].ref_id == linked_task.id
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
