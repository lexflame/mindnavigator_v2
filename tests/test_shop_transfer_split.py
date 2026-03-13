from __future__ import annotations

from dataclasses import dataclass

from mindnavigator.transfer.shop import ParsedShopProperty, ParsedShopResult, ShopParseService, build_default_parsers


class _FakeHttp:
    pass


@dataclass
class _FakeItem:
    id: int
    title: str


@dataclass
class _FakeSource:
    id: int


class _FakeDb:
    def __init__(self) -> None:
        self.item = _FakeItem(id=11, title="Parsed Title")
        self.source = _FakeSource(id=22)
        self.created_titles: list[str] = []
        self.replaced_properties: list[tuple[int, list[object]]] = []
        self.price_history_calls: list[dict[str, object]] = []
        self.parse_log_calls: list[dict[str, object]] = []
        self.upsert_calls: list[dict[str, object]] = []

    def create_shop_item(self, title: str) -> _FakeItem:
        self.created_titles.append(title)
        return self.item

    def get_shop_item(self, item_id: int) -> _FakeItem | None:
        return self.item if item_id == self.item.id else None

    def upsert_shop_source(self, **kwargs: object) -> _FakeSource:
        self.upsert_calls.append(kwargs)
        return self.source

    def replace_shop_source_properties(self, source_id: int, props: list[object]) -> None:
        self.replaced_properties.append((source_id, props))

    def add_shop_price_history(self, **kwargs: object) -> None:
        self.price_history_calls.append(kwargs)

    def add_shop_parse_log(self, **kwargs: object) -> None:
        self.parse_log_calls.append(kwargs)


class _FakeParser:
    def match(self, url: str) -> bool:
        return "shop.test" in url

    def parse(self, url: str) -> ParsedShopResult:
        return ParsedShopResult(
            title="Parsed Title",
            sku="SKU-1",
            price=19.99,
            currency="RUB",
            in_stock=True,
            properties=[ParsedShopProperty(name="Power", value="5W")],
            shop_code="shop-test",
            canonical_url=url,
            raw={"status": 200, "content_type": "text/html"},
        )


def test_shop_transfer_package_exports_expected_symbols() -> None:
    assert ParsedShopProperty is not None
    assert ParsedShopResult is not None
    assert ShopParseService is not None
    assert build_default_parsers is not None


def test_shop_parse_service_keeps_basic_parse_and_store_flow() -> None:
    db = _FakeDb()
    service = ShopParseService(db, [_FakeParser()])

    item, source, result = service.parse_and_store("https://shop.test/item/1")

    assert item is db.item
    assert source is db.source
    assert result.title == "Parsed Title"
    assert db.created_titles == ["Parsed Title"]
    assert db.upsert_calls[0]["shop_code"] == "shop-test"
    assert db.upsert_calls[0]["price"] == 19.99
    assert db.replaced_properties[0][0] == db.source.id
    assert len(db.replaced_properties[0][1]) == 1
    assert db.price_history_calls[0]["source_id"] == db.source.id
    assert db.parse_log_calls[0]["shop_code"] == "shop-test"


def test_build_default_parsers_returns_transfer_parser_types() -> None:
    parsers = build_default_parsers(_FakeHttp())

    assert [parser.shop_code for parser in parsers] == ["e2e4", "chipdip", "dns", "wildberries"]
    assert all(parser.__class__.__module__ == "mindnavigator.transfer.shop.shop_parsers" for parser in parsers)
