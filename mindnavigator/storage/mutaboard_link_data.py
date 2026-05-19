"""MutaBoardLinkData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class MutaBoardLinkData:
    id: int
    mutaboard_id: int
    source_kind: str
    source_id: int
    target_kind: str
    target_id: int
    link_type: str
    created_at: datetime


__all__ = ["MutaBoardLinkData"]
