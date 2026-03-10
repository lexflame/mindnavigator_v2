"""Compatibility exports for shop parsing types and service."""

from .transfer.shop.shop_parsing import IShopParser, ParsedShopProperty, ParsedShopResult, ShopParseService

__all__ = [
    "IShopParser",
    "ParsedShopProperty",
    "ParsedShopResult",
    "ShopParseService",
]
