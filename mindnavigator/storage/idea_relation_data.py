"""IdeaRelationData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class IdeaRelationData:
    id: int
    idea_id: int
    entity_type: str
    entity_id: int
    created_at: datetime

__all__ = ["IdeaRelationData"]
