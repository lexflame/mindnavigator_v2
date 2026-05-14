from __future__ import annotations

from datetime import date, datetime, timezone

from mindnavigator.storage import (
    BOARD_COLUMN_COMPLETED,
    BOARD_COLUMN_IN_PROGRESS,
    BOARD_COLUMN_QUEUE,
    DEFERRED_PRIORITY,
    IdeaData,
    IdeaRelationData,
    ObjectData,
    TaskData,
    TaskAttachmentData,
)
from mindnavigator.workspaces.mutaboard.module_impl import MutaBoardModel


class _MutaBoardDbStub:
    def __init__(self) -> None:
        self._attachments = {
            1: [
                TaskAttachmentData(
                    id=501,
                    task_id=1,
                    kind="idea",
                    ref_id=11,
                    created_at="2026-05-14T12:00:00+00:00",
                )
            ],
            2: [],
            3: [],
            4: [
                TaskAttachmentData(
                    id=502,
                    task_id=4,
                    kind="object",
                    ref_id=21,
                    created_at="2026-05-14T12:00:00+00:00",
                )
            ],
        }

    def fetch_tasks(self):
        return [
            TaskData(
                id=1,
                day=date(2026, 5, 14),
                time_text="09:00",
                title="Queued task",
                description="Implementation follow-up for board shell.",
                priority="Medium",
                done=False,
                board_column=BOARD_COLUMN_QUEUE,
                project_id=7,
                project_title="Project Seven",
            ),
            TaskData(
                id=2,
                day=date(2026, 5, 14),
                time_text="10:00",
                title="Deferred task",
                description="Should land in frozen stage.",
                priority=DEFERRED_PRIORITY,
                done=False,
                board_column=BOARD_COLUMN_QUEUE,
                project_id=7,
                project_title="Project Seven",
            ),
            TaskData(
                id=3,
                day=date(2026, 5, 14),
                time_text="11:00",
                title="Completed task",
                description="Already finished.",
                priority="High",
                done=True,
                board_column=BOARD_COLUMN_COMPLETED,
                project_id=9,
                project_title="Project Nine",
            ),
            TaskData(
                id=4,
                day=date(2026, 5, 14),
                time_text="12:00",
                title="Active task",
                description="In progress flow.",
                priority="High",
                done=False,
                board_column=BOARD_COLUMN_IN_PROGRESS,
                project_id=9,
                project_title="Project Nine",
            ),
        ]

    def fetch_ideas(self, archived=True):
        now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        active = [
            IdeaData(
                id=11,
                project_id=7,
                title="Inbox idea",
                summary="Unsorted thought",
                body_md="",
                type="concept",
                status="inbox",
                value_score=2,
                effort_score=1,
                source="",
                created_at=now,
                updated_at=now,
                archived_at=None,
                project_title="Project Seven",
            ),
            IdeaData(
                id=12,
                project_id=9,
                title="Ripe idea",
                summary="Ready for analysis",
                body_md="",
                type="feature",
                status="ripe",
                value_score=5,
                effort_score=3,
                source="",
                created_at=now,
                updated_at=now,
                archived_at=None,
                project_title="Project Nine",
            ),
        ]
        archived_items = [
            IdeaData(
                id=13,
                project_id=9,
                title="Archived idea",
                summary="No longer active",
                body_md="",
                type="archive",
                status="archived",
                value_score=1,
                effort_score=1,
                source="",
                created_at=now,
                updated_at=now,
                archived_at=now,
                project_title="Project Nine",
            ),
        ]
        return archived_items if archived else active

    def fetch_idea_relations(self, idea_id: int):
        now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        if idea_id == 11:
            return [IdeaRelationData(id=601, idea_id=11, entity_type="task", entity_id=1, created_at=now)]
        if idea_id == 12:
            return [IdeaRelationData(id=602, idea_id=12, entity_type="object", entity_id=21, created_at=now)]
        return []

    def fetch_objects(self):
        return [
            ObjectData(
                id=21,
                title="Active object",
                catalog="Ops",
                object_type="service",
                status="active",
                description="Operational service entity",
                created_at="2026-05-14T10:00:00+00:00",
                updated_at="2026-05-14T11:00:00+00:00",
            ),
            ObjectData(
                id=22,
                title="Archived object",
                catalog="Archive",
                object_type="asset",
                status="archived",
                description="Cold storage entity",
                created_at="2026-05-14T10:00:00+00:00",
                updated_at="2026-05-14T11:00:00+00:00",
            ),
            ObjectData(
                id=23,
                title="Loose object",
                catalog="Sandbox",
                object_type="draft",
                status="",
                description="No explicit lifecycle yet",
                created_at="2026-05-14T10:00:00+00:00",
                updated_at="2026-05-14T11:00:00+00:00",
            ),
        ]

    def fetch_task_attachments(self, task_id: int):
        return list(self._attachments.get(task_id, []))


def test_mutaboard_model_derives_mixed_entity_stages() -> None:
    model = MutaBoardModel(db=_MutaBoardDbStub())

    cards = model.reload()
    by_title = {card.title: card for card in cards}

    assert by_title["Queued task"].stage == "prep"
    assert by_title["Deferred task"].stage == "frozen"
    assert by_title["Completed task"].stage == "done"
    assert by_title["Active task"].stage == "active"
    assert by_title["Inbox idea"].stage == "inbox"
    assert by_title["Ripe idea"].stage == "thinking"
    assert by_title["Archived idea"].stage == "frozen"
    assert by_title["Active object"].stage == "active"
    assert by_title["Archived object"].stage == "frozen"
    assert by_title["Loose object"].stage == "thinking"


def test_mutaboard_model_filters_by_kind_project_query_and_actionable() -> None:
    model = MutaBoardModel(db=_MutaBoardDbStub())
    model.reload()

    idea_cards = model.filtered_cards(entity_kind="idea")
    assert {card.title for card in idea_cards} == {"Inbox idea", "Ripe idea", "Archived idea"}

    project_cards = model.filtered_cards(project_id=7)
    assert {card.title for card in project_cards} == {"Queued task", "Deferred task", "Inbox idea"}

    actionable_cards = model.filtered_cards(actionable_only=True)
    assert "Deferred task" not in {card.title for card in actionable_cards}
    assert "Completed task" not in {card.title for card in actionable_cards}
    assert "Archived idea" not in {card.title for card in actionable_cards}
    assert "Archived object" not in {card.title for card in actionable_cards}

    query_cards = model.filtered_cards(query="analysis")
    assert [card.title for card in query_cards] == ["Ripe idea"]

    linked_cards = model.filtered_cards(linked_only=True)
    assert {card.title for card in linked_cards} == {"Queued task", "Active task", "Inbox idea", "Ripe idea", "Active object"}

    unlinked_cards = model.filtered_cards(linked_only=False)
    assert {card.title for card in unlinked_cards} == {
        "Deferred task",
        "Completed task",
        "Archived idea",
        "Archived object",
        "Loose object",
    }


def test_mutaboard_model_groups_cards_by_stage() -> None:
    model = MutaBoardModel(db=_MutaBoardDbStub())
    grouped = model.grouped_cards(model.reload())

    assert {card.title for card in grouped["prep"]} == {"Queued task"}
    assert {card.title for card in grouped["active"]} == {"Active task", "Active object"}
    assert {card.title for card in grouped["frozen"]} == {"Deferred task", "Archived idea", "Archived object"}


def test_mutaboard_model_populates_link_counts() -> None:
    model = MutaBoardModel(db=_MutaBoardDbStub())
    cards = {card.title: card for card in model.reload()}

    assert cards["Queued task"].linked_idea_count == 1
    assert cards["Inbox idea"].linked_task_count == 1
    assert cards["Ripe idea"].linked_object_count == 1
    assert cards["Active task"].linked_object_count == 1
    assert cards["Active object"].linked_task_count == 1
    assert cards["Active object"].linked_idea_count == 1
