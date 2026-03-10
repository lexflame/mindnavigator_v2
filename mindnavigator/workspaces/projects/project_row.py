"""ProjectRow class module for projects workspace."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class ProjectRow:
    id: int
    area: str               # group header key
    title: str
    updated: date
    priority: str           # Low | Medium | High
    archived: bool
    parent_project_id: Optional[int] = None
    default_task_priority: str = ""
    force_recurrence_kind: str = ""
    linked_map_id: Optional[int] = None
    linked_note_id: Optional[int] = None
    linked_object_id: Optional[int] = None
    marker_color: str = ""
    marker_theme: str = ""
    repository_catalog: str = ""

__all__ = ["ProjectRow"]
