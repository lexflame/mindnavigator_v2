"""TaskData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class TaskData:
    id: int
    day: date
    time_text: str
    title: str
    description: str
    priority: str
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
    gantt_forecasted: bool = False
    started_at: str = ""
    finished_at: str = ""
    actual_minutes: int = 0
    marker_color: str = ""
    marker_theme: str = ""
    project_task_type_id: Optional[int] = None
    project_task_type_title: str = ""
    project_task_type_color: str = ""
    project_task_type_theme: str = ""
    postponed_reason: str = ""
    postponed_by_project_task_type_id: Optional[int] = None
    is_plan_task: bool = False
    plan_order: int = 0
    created_at: str = ""
    updated_at: str = ""

__all__ = ["TaskData"]
