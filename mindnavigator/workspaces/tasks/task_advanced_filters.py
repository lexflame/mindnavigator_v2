"""Testable advanced-filter state for task rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TaskFilterCandidate(Protocol):
    id: int
    project_id: int | None
    parent_id: int | None
    project_task_type_id: int | None


@dataclass(frozen=True)
class TaskAdvancedFilterState:
    task_type: int | str | None = None
    links: str = "all"
    project: str = "all"
    nesting: str = "all"

    def matches(self, task: TaskFilterCandidate, linked_task_ids: set[int]) -> bool:
        if self.task_type == "none" and task.project_task_type_id is not None:
            return False
        if isinstance(self.task_type, int) and task.project_task_type_id != self.task_type:
            return False
        if self.links == "linked" and task.id not in linked_task_ids:
            return False
        if self.links == "unlinked" and task.id in linked_task_ids:
            return False
        if self.project == "without" and task.project_id is not None:
            return False
        if self.nesting == "root" and task.parent_id is not None:
            return False
        if self.nesting == "nested" and task.parent_id is None:
            return False
        return True


__all__ = ["TaskAdvancedFilterState"]
