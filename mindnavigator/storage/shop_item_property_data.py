"""ShopItemPropertyData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ShopItemPropertyData:
    id: int
    item_id: int
    name: str
    value: str
    unit: str
    normalized_key: str

__all__ = ["ShopItemPropertyData"]
