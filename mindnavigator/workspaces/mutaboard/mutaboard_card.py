"""Unified card dataclass for the MutaBoard workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MUTABOARD_KIND_TASK = "task"
MUTABOARD_KIND_IDEA = "idea"
MUTABOARD_KIND_OBJECT = "object"
MUTABOARD_KINDS = (
    MUTABOARD_KIND_TASK,
    MUTABOARD_KIND_IDEA,
    MUTABOARD_KIND_OBJECT,
)

MUTABOARD_STAGE_INBOX = "inbox"
MUTABOARD_STAGE_THINKING = "thinking"
MUTABOARD_STAGE_PREP = "prep"
MUTABOARD_STAGE_ACTIVE = "active"
MUTABOARD_STAGE_REVIEW = "review"
MUTABOARD_STAGE_DONE = "done"
MUTABOARD_STAGE_FROZEN = "frozen"
MUTABOARD_STAGES = (
    MUTABOARD_STAGE_INBOX,
    MUTABOARD_STAGE_THINKING,
    MUTABOARD_STAGE_PREP,
    MUTABOARD_STAGE_ACTIVE,
    MUTABOARD_STAGE_REVIEW,
    MUTABOARD_STAGE_DONE,
    MUTABOARD_STAGE_FROZEN,
)


@dataclass(frozen=True)
class MutaBoardCard:
    entity_kind: str
    entity_id: int
    title: str
    subtitle: str
    stage: str
    project_id: int | None
    project_title: str
    accent_color: str
    meta_text: str
    linked_task_count: int = 0
    linked_idea_count: int = 0
    linked_object_count: int = 0
    can_drag: bool = False
    can_mutate: bool = True
    is_actionable: bool = True
    source_payload: Any = None

    @property
    def total_linked_count(self) -> int:
        return self.linked_task_count + self.linked_idea_count + self.linked_object_count


__all__ = [
    "MutaBoardCard",
    "MUTABOARD_KIND_TASK",
    "MUTABOARD_KIND_IDEA",
    "MUTABOARD_KIND_OBJECT",
    "MUTABOARD_KINDS",
    "MUTABOARD_STAGE_INBOX",
    "MUTABOARD_STAGE_THINKING",
    "MUTABOARD_STAGE_PREP",
    "MUTABOARD_STAGE_ACTIVE",
    "MUTABOARD_STAGE_REVIEW",
    "MUTABOARD_STAGE_DONE",
    "MUTABOARD_STAGE_FROZEN",
    "MUTABOARD_STAGES",
]
