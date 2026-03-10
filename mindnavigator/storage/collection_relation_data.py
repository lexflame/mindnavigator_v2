"""CollectionRelationData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class CollectionRelationData:
    id: int
    left_item_id: int
    right_item_id: int
    relation_kind: str
    created_at: str

__all__ = ["CollectionRelationData"]
