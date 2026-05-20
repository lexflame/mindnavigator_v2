"""ConceptBoardItemData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class ConceptBoardItemData:
    id: int
    concept_board_id: int
    entity_kind: str
    entity_id: int
    created_at: datetime


__all__ = ["ConceptBoardItemData"]
