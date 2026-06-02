"""Project property storage data classes."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class ProjectTaskTypeData:
    id: int
    project_id: int
    title: str
    color_marker: str = ""
    theme_marker: str = ""
    active: bool = True
    sort_order: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ProjectRelatedProjectData:
    id: int
    project_id: int
    related_project_id: int
    title: str = ""
    area: str = ""
    archived: bool = False
    sort_order: int = 0
    created_at: str = ""


@dataclass(frozen=True)
class ProjectRelatedTaskData:
    id: int
    project_id: int
    task_id: int
    title: str = ""
    priority: str = ""
    done: bool = False
    sort_order: int = 0
    created_at: str = ""


@dataclass(frozen=True)
class ProjectLinkData:
    id: int
    project_id: int
    title: str
    url: str
    sort_order: int = 0
    created_at: str = ""
    updated_at: str = ""


__all__ = [
    "ProjectTaskTypeData",
    "ProjectRelatedProjectData",
    "ProjectRelatedTaskData",
    "ProjectLinkData",
]
