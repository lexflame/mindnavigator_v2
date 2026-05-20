"""Unified card dataclass for the ConceptBoard workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONCEPT_BOARD_KIND_TASK = "task"
CONCEPT_BOARD_KIND_IDEA = "idea"
CONCEPT_BOARD_KIND_IMAGE = "image"
CONCEPT_BOARD_KIND_MAP = "map"
CONCEPT_BOARD_KIND_MARKER = "marker"
CONCEPT_BOARD_KIND_NOTE = "note"
CONCEPT_BOARD_KIND_PROJECT = "project"
CONCEPT_BOARD_KIND_OBJECT = "object"
CONCEPT_BOARD_KIND_VERSION = "version"
CONCEPT_BOARD_KIND_SOLUTION = "solution"
CONCEPT_BOARD_KIND_FILE = "file"
CONCEPT_BOARD_KIND_LINK = "link"
CONCEPT_BOARD_KINDS = (
    CONCEPT_BOARD_KIND_TASK,
    CONCEPT_BOARD_KIND_IDEA,
    CONCEPT_BOARD_KIND_IMAGE,
    CONCEPT_BOARD_KIND_MAP,
    CONCEPT_BOARD_KIND_MARKER,
    CONCEPT_BOARD_KIND_NOTE,
    CONCEPT_BOARD_KIND_PROJECT,
    CONCEPT_BOARD_KIND_OBJECT,
    CONCEPT_BOARD_KIND_VERSION,
    CONCEPT_BOARD_KIND_SOLUTION,
    CONCEPT_BOARD_KIND_FILE,
    CONCEPT_BOARD_KIND_LINK,
)


@dataclass(frozen=True)
class ConceptBoardCard:
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
        return f"T{self.linked_task_count} В· I{self.linked_idea_count} В· O{self.linked_object_count}"


__all__ = [
    "ConceptBoardCard",
    "CONCEPT_BOARD_KIND_TASK",
    "CONCEPT_BOARD_KIND_IDEA",
    "CONCEPT_BOARD_KIND_IMAGE",
    "CONCEPT_BOARD_KIND_MAP",
    "CONCEPT_BOARD_KIND_MARKER",
    "CONCEPT_BOARD_KIND_NOTE",
    "CONCEPT_BOARD_KIND_PROJECT",
    "CONCEPT_BOARD_KIND_OBJECT",
    "CONCEPT_BOARD_KIND_VERSION",
    "CONCEPT_BOARD_KIND_SOLUTION",
    "CONCEPT_BOARD_KIND_FILE",
    "CONCEPT_BOARD_KIND_LINK",
    "CONCEPT_BOARD_KINDS",
]
