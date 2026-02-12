"""Shop parsers (E2E4, ChipDip, DNS, Wildberries)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from mindnavigator.http_client import HttpClient
from mindnavigator.shop_parsing import IShopParser, ParsedShopResult


_PRICE_RE = re.compile(r"(\d[\d\s]*[.,]\d{2})")


def _normalize_price(raw: str) -> Optional[float]:
    value = (raw or "").strip().replace(" ", "").replace("\u00a0", "")
    value = value.replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def _extract_title(html: str) -> str:
    if not html:
        return ""
    meta = re.search(r'property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html, re.I)
    if meta:
        return meta.group(1).strip()
    title = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if title:
        return re.sub(r"\s+", " ", title.group(1)).strip()
    return ""


def _extract_jsonld(html: str) -> list[dict]:
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    )
    results: list[dict] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            results.append(data)
        elif isinstance(data, list):
            results.extend([item for item in data if isinstance(item, dict)])
    return results


def _find_product_ld(jsonld: list[dict]) -> Optional[dict]:
    for item in jsonld:
        kind = item.get("@type") or item.get("type")
        if isinstance(kind, list):
            kind = next((k for k in kind if isinstance(k, str)), "")
        if isinstance(kind, str) and "Product" in kind:
            return item
    return None


def _extract_product_from_ld(product: dict) -> dict:
    title = product.get("name") or ""
    sku = product.get("sku") or ""
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = offers.get("price")
    currency = offers.get("priceCurrency") or ""
    availability = offers.get("availability") or ""
    in_stock = "InStock" in availability or availability.lower().endswith("instock")
    return {
        "title": title,
        "sku": sku,
        "price": _normalize_price(str(price)) if price is not None else None,
        "currency": currency,
        "in_stock": in_stock,
    }


def _extract_price(html: str) -> Optional[float]:
    if not html:
        return None
    match = _PRICE_RE.search(html)
    if not match:
        return None
    return _normalize_price(match.group(1))


def _extract_currency(html: str) -> str:
    if not html:
        return ""
    if "₽" in html or "RUB" in html:
        return "RUB"
    if "$" in html or "USD" in html:
        return "USD"
    if "€" in html or "EUR" in html:
        return "EUR"
    return ""


def _url_matches(url: str, domain: str) -> bool:
    host = urlparse(url).netloc.lower()
    return domain in host


@dataclass
class BaseShopParser(IShopParser):
    domain: str
    shop_code: str
    http: HttpClient

    def match(self, url: str) -> bool:
        return _url_matches(url, self.domain)

    def parse(self, url: str) -> ParsedShopResult:
        response = self.http.fetch(url)
        html = response.text or ""
        jsonld = _extract_jsonld(html)
        product_ld = _find_product_ld(jsonld)
        product_data = _extract_product_from_ld(product_ld) if product_ld else {}
        title = product_data.get("title") or _extract_title(html)
        price = product_data.get("price")
        if price is None:
            price = _extract_price(html)
        currency = product_data.get("currency") or _extract_currency(html)
        in_stock = bool(product_data.get("in_stock")) if product_data else False
        return ParsedShopResult(
            title=title,
            sku="",
            price=price,
            currency=currency,
            in_stock=in_stock if price is not None else False,
            stock_text="",
            category_hint="",
            properties=[],
            images=[],
            shop_code=self.shop_code,
            canonical_url=url,
            raw={"status": response.status_code, "content_type": response.headers.get("Content-Type", "")},
        )


def build_default_parsers(http: HttpClient) -> list[IShopParser]:
    return [
        BaseShopParser(domain="e2e4online.ru", shop_code="e2e4", http=http),
        BaseShopParser(domain="chipdip.ru", shop_code="chipdip", http=http),
        BaseShopParser(domain="dns-shop.ru", shop_code="dns", http=http),
        BaseShopParser(domain="wildberries.ru", shop_code="wildberries", http=http),
    ]
