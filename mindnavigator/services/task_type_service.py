"""Type-aware task update orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from mindnavigator.storage import TaskData


@dataclass(frozen=True)
class TaskTypeUpdateValues:
    """Editable task fields preserved while applying a task type."""

    title: str
    description: str
    day: date
    time_text: str
    priority: str
    importance: int
    done: bool
    parent_id: Optional[int]
    recurrence_kind: str
    recurrence_interval: int
    plan_order: int
    marker_color: str
    marker_theme: str


class TaskTypeService:
    """Applies built-in or project task types through the storage facade."""

    def __init__(self, database) -> None:
        self._database = database

    def apply_type(
        self,
        *,
        task_id: int,
        project_id: Optional[int],
        project_task_type_id: Optional[int],
        is_plan_task: bool,
        values: TaskTypeUpdateValues,
    ) -> TaskData:
        return self._database.update_task(
            task_id=int(task_id),
            title=values.title,
            description=values.description,
            day=values.day,
            time_text=values.time_text,
            priority=values.priority,
            importance=values.importance,
            done=values.done,
            project_id=project_id,
            parent_id=values.parent_id,
            recurrence_kind=values.recurrence_kind,
            recurrence_interval=values.recurrence_interval,
            is_plan_task=bool(is_plan_task),
            plan_order=values.plan_order,
            marker_color=values.marker_color,
            marker_theme=values.marker_theme,
            project_task_type_id=project_task_type_id,
        )
