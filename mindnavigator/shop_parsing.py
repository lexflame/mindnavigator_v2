"""Parsing interfaces and service for shop sources."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence

from mindnavigator.storage import Database, ShopItemData, ShopSourceData, ShopSourcePropertyData


@dataclass(frozen=True)
class ParsedShopProperty:
    name: str
    value: str
    unit: str = ""
    normalized_key: str = ""


@dataclass(frozen=True)
class ParsedShopResult:
    title: str = ""
    sku: str = ""
    price: float | None = None
    currency: str = ""
    in_stock: bool = False
    stock_text: str = ""
    category_hint: str = ""
    properties: list[ParsedShopProperty] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    shop_code: str = ""
    canonical_url: str = ""
    raw: Any = None


class IShopParser(Protocol):
    def match(self, url: str) -> bool:
        ...

    def parse(self, url: str) -> ParsedShopResult:
        ...


class ShopParseService:
    """Selects parser by URL, parses and persists data."""

    def __init__(self, db: Database, parsers: Sequence[IShopParser]) -> None:
        self._db = db
        self._parsers = list(parsers)

    def _resolve_parser(self, url: str) -> IShopParser:
        for parser in self._parsers:
            if parser.match(url):
                return parser
        raise ValueError("Нет подходящего парсера для URL.")

    def resolve_parser(self, url: str) -> IShopParser:
        return self._resolve_parser(url)

    def parse_and_store(
        self,
        url: str,
        *,
        item_id: int | None = None,
    ) -> tuple[ShopItemData, ShopSourceData, ParsedShopResult]:
        parser = self._resolve_parser(url)
        result = parser.parse(url)
        canonical_url = result.canonical_url or url
        parsed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        if item_id is None:
            item_title = (result.title or canonical_url).strip()
            item = self._db.create_shop_item(item_title)
        else:
            item = self._db.get_shop_item(item_id)
            if item is None:
                raise ValueError("Товар для привязки не найден.")

        raw_payload = result.raw
        if raw_payload is None:
            raw_json = ""
        elif isinstance(raw_payload, str):
            raw_json = raw_payload
        else:
            raw_json = json.dumps(raw_payload, ensure_ascii=False)

        source = self._db.upsert_shop_source(
            item_id=item.id,
            shop_code=result.shop_code,
            url=canonical_url,
            sku=result.sku,
            currency=result.currency,
            price=result.price,
            in_stock=result.in_stock,
            stock_text=result.stock_text,
            parsed_at=parsed_at,
            raw_json=raw_json,
        )

        if result.properties:
            props = [
                ShopSourcePropertyData(
                    id=0,
                    source_id=source.id,
                    name=p.name,
                    value=p.value,
                    unit=p.unit,
                    normalized_key=p.normalized_key,
                )
                for p in result.properties
            ]
            self._db.replace_shop_source_properties(source.id, props)

        self._db.add_shop_price_history(
            source_id=source.id,
            price=result.price,
            currency=result.currency,
            in_stock=result.in_stock,
            captured_at=parsed_at,
        )

        status_code = None
        content_type = ""
        raw_snippet = ""
        if isinstance(result.raw, dict):
            status_code = result.raw.get("status")
            content_type = result.raw.get("content_type") or ""
            raw_snippet = json.dumps(result.raw, ensure_ascii=False)[:800]
        elif isinstance(result.raw, str):
            raw_snippet = result.raw[:800]
        self._db.add_shop_parse_log(
            source_id=source.id,
            shop_code=result.shop_code,
            url=canonical_url,
            status_code=status_code,
            content_type=content_type,
            fetched_at=parsed_at,
            raw_snippet=raw_snippet,
        )

        return item, source, result
