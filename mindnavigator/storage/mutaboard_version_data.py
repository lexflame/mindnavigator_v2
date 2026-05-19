"""MutaBoardVersionData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class MutaBoardVersionData:
    id: int
    mutaboard_id: int
    title: str
    description: str
    why_yes: str
    why_no: str
    checks_text: str
    status: str
    created_at: datetime
    updated_at: datetime


__all__ = ["MutaBoardVersionData"]
