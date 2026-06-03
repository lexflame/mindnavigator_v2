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
    importance: int = 3
    project_id: Optional[int] = None
    project_title: str = ""
    project_area: str = ""
    parent_id: Optional[int] = None
    recurrence_kind: str = ""
    recurrence_interval: int = 1
    completion_delay_minutes: int = 0
    gantt_estimate_minutes: int = 0
    started_at: str = ""
    finished_at: str = ""
    actual_minutes: int = 0
    marker_color: str = ""
    marker_theme: str = ""
    project_task_type_id: Optional[int] = None
    project_task_type_title: str = ""
    project_task_type_value: str = ""
    project_task_type_color: str = ""
    project_task_type_theme: str = ""
    project_task_type_priority: str = ""
    project_task_type_importance: int = 3
    project_task_type_is_plan_task: bool = False
    project_task_type_concept_board_id: Optional[int] = None
    postponed_reason: str = ""
    postponed_by_project_task_type_id: Optional[int] = None
    is_plan_task: bool = False
    plan_order: int = 0
    created_at: str = ""
    updated_at: str = ""

__all__ = ["TaskRow"]
