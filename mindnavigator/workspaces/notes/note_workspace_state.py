"""NoteWorkspaceState class module for notes workspace."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class NoteWorkspaceState:
    selected_note_id: Optional[int] = None
    filter_mode: str = "Все"
    search_text: str = ""
    project_filter: Optional[str] = None
    tag_filter: Optional[str] = None
    task_filter: Optional[int] = None

__all__ = ["NoteWorkspaceState"]
