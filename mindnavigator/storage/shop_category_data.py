"""ShopCategoryData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ShopCategoryData:
    id: int
    title: str
    parent_id: Optional[int]

__all__ = ["ShopCategoryData"]
