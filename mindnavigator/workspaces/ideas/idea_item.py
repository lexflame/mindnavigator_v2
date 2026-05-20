"""IdeaItem class module for ideas workspace."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class IdeaItem:
    id: int
    title: str
    summary: str
    body_md: str
    status: str
    idea_type: str
    value_score: int
    effort_score: int
    project_id: Optional[int]
    project_title: str
    archived: bool
    source: str = ""
    output_label: str = "нет"
    relations_count: int = 0
    materials_count: int = 0
    updated_label: str = ""

__all__ = ["IdeaItem"]
