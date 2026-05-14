"""TaskRow class module for tasks workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class TaskRow:
    id: int
    day: date
    time_text: str
    title: str
    description: str
    priority: str   # Low | Medium | High
    done: bool
    board_column: str = "queue"
    project_id: Optional[int] = None
    project_title: str = ""
    project_area: str = ""
    parent_id: Optional[int] = None
    recurrence_kind: str = ""
    recurrence_interval: int = 1
    completion_delay_minutes: int = 0
    started_at: str = ""
    finished_at: str = ""
    actual_minutes: int = 0
    marker_color: str = ""
    marker_theme: str = ""
    is_plan_task: bool = False
    plan_order: int = 0

__all__ = ["TaskRow"]
