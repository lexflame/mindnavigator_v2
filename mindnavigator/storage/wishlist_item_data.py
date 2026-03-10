"""WishlistItemData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class WishlistItemData:
    wishlist_id: int
    item_id: int
    qty: int
    priority: int
    target_price: Optional[float]
    chosen_source_id: Optional[int]

__all__ = ["WishlistItemData"]
