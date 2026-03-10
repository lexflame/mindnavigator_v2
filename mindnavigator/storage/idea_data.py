"""IdeaData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class IdeaData:
    id: int
    project_id: Optional[int]
    title: str
    summary: str
    body_md: str
    type: str
    status: str
    value_score: int
    effort_score: int
    source: str
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]
    project_title: str = ""

__all__ = ["IdeaData"]
