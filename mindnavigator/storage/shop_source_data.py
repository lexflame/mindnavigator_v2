"""ShopSourceData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ShopSourceData:
    id: int
    item_id: int
    shop_code: str
    url: str
    sku: str
    currency: str
    price: Optional[float]
    in_stock: bool
    stock_text: str
    parsed_at: str
    raw_json: str

__all__ = ["ShopSourceData"]
