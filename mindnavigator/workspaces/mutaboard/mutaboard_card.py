"""Unified card dataclass for the MutaBoard workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MUTABOARD_KIND_TASK = "task"
MUTABOARD_KIND_IDEA = "idea"
MUTABOARD_KIND_IMAGE = "image"
MUTABOARD_KIND_MAP = "map"
MUTABOARD_KIND_MARKER = "marker"
MUTABOARD_KIND_NOTE = "note"
MUTABOARD_KIND_PROJECT = "project"
MUTABOARD_KIND_OBJECT = "object"
MUTABOARD_KINDS = (
    MUTABOARD_KIND_TASK,
    MUTABOARD_KIND_IDEA,
    MUTABOARD_KIND_IMAGE,
    MUTABOARD_KIND_MAP,
    MUTABOARD_KIND_MARKER,
    MUTABOARD_KIND_NOTE,
    MUTABOARD_KIND_PROJECT,
    MUTABOARD_KIND_OBJECT,
)


@dataclass(frozen=True)
class MutaBoardCard:
    entity_kind: str
    entity_id: int
    title: str
    subtitle: str
    project_id: int | None
    project_title: str
    accent_color: str
    meta_text: str
    relation_count: int = 0
    relation_summary: str = ""
    linked_task_count: int = 0
    linked_idea_count: int = 0
    linked_object_count: int = 0
    stage: str = ""
    can_drag: bool = False
    can_mutate: bool = True
    is_actionable: bool = True
    is_attached: bool = False
    source_payload: Any = None

    @property
    def total_linked_count(self) -> int:
        return max(0, int(self.relation_count))

    @property
    def link_summary(self) -> str:
        if self.relation_summary:
            return self.relation_summary
        return f"T{self.linked_task_count} · I{self.linked_idea_count} · O{self.linked_object_count}"


__all__ = [
    "MutaBoardCard",
    "MUTABOARD_KIND_TASK",
    "MUTABOARD_KIND_IDEA",
    "MUTABOARD_KIND_IMAGE",
    "MUTABOARD_KIND_MAP",
    "MUTABOARD_KIND_MARKER",
    "MUTABOARD_KIND_NOTE",
    "MUTABOARD_KIND_PROJECT",
    "MUTABOARD_KIND_OBJECT",
    "MUTABOARD_KINDS",
]
