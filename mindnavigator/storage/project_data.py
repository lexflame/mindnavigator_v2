"""ProjectData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ProjectData:
    id: int
    area: str
    title: str
    updated: date
    priority: str
    archived: bool
    parent_project_id: Optional[int] = None
    default_task_priority: str = ""
    force_recurrence_kind: str = ""
    linked_map_id: Optional[int] = None
    linked_note_id: Optional[int] = None
    linked_object_id: Optional[int] = None
    sort_order: int = 0
    marker_color: str = ""
    marker_theme: str = ""
    repository_catalog: str = ""

__all__ = ["ProjectData"]
