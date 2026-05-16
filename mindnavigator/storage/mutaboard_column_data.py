"""MutaBoardColumnData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class MutaBoardColumnData:
    id: int
    mutaboard_id: int
    kind: str
    title: str
    position: int
    created_at: datetime
    updated_at: datetime


__all__ = ["MutaBoardColumnData"]
