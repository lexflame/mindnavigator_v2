"""CollectionCategoryData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class CollectionCategoryData:
    id: int
    title: str
    parent_id: Optional[int]
    sort_index: int
    created_at: str
    updated_at: str

__all__ = ["CollectionCategoryData"]
