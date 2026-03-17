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
    project_id: Optional[int] = None
    project_title: str = ""
    project_area: str = ""
    parent_id: Optional[int] = None
    recurrence_kind: str = ""
    recurrence_interval: int = 1
    completion_delay_minutes: int = 0
    gantt_estimate_minutes: int = 0
    gantt_forecasted: bool = False
    marker_color: str = ""
    marker_theme: str = ""
    is_plan_task: bool = False
    plan_order: int = 0

__all__ = ["TaskData"]
