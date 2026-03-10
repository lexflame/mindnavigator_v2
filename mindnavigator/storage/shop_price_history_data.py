"""ShopPriceHistoryData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ShopPriceHistoryData:
    id: int
    source_id: int
    price: Optional[float]
    currency: str
    in_stock: bool
    captured_at: str

__all__ = ["ShopPriceHistoryData"]
