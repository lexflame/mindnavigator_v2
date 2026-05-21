"""NoteItem class module for notes workspace."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass(frozen=True)
class NoteItem:
    id: int
    title: str
    preview: str
    tags: List[str]
    updated: datetime
    project: str
    favorite: bool = False
    attachment: bool = False
    locked: bool = False
    relation_summary: str = ""

__all__ = ["NoteItem"]
