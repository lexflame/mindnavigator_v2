"""ContextEntityLinkData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class ContextEntityLinkData:
    id: int
    source_type: str
    source_id: int
    target_type: str
    target_id: int
    anchor_text: str
    source_field: str
    created_at: str


__all__ = ["ContextEntityLinkData"]
