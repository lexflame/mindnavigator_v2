"""ShopItemData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ShopItemData:
    id: int
    title: str
    category_id: Optional[int]
    user_notes: str
    created_at: str
    updated_at: str

__all__ = ["ShopItemData"]
