"""MutaBoardData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class MutaBoardData:
    id: int
    title: str
    description: str
    capture_text: str
    planning_text: str
    links_text: str
    created_at: datetime
    updated_at: datetime


__all__ = ["MutaBoardData"]
