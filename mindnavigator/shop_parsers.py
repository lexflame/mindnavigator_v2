"""Shop parsers (E2E4, ChipDip, DNS, Wildberries)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from mindnavigator.http_client import HttpClient
from mindnavigator.shop_parsing import IShopParser, ParsedShopResult, ParsedShopProperty


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
    images = product.get("image") or []
    if isinstance(images, str):
        images = [images]
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
        "images": images,
    }


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def _extract_properties_from_ld(product: dict) -> list[ParsedShopProperty]:
    props: list[ParsedShopProperty] = []
    if not product:
        return props
    additional = product.get("additionalProperty") or []
    if isinstance(additional, dict):
        additional = [additional]
    for prop in additional:
        if not isinstance(prop, dict):
            continue
        name = str(prop.get("name") or "").strip()
        value = str(prop.get("value") or "").strip()
        if name and value:
            props.append(ParsedShopProperty(name=name, value=value))
    return props


def _extract_properties_from_html(html: str) -> list[ParsedShopProperty]:
    props: list[ParsedShopProperty] = []
    if not html:
        return props
    # Try to extract simple spec tables: <tr><th>..</th><td>..</td>
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.I | re.S)
    for row in rows:
        th = re.search(r"<th[^>]*>(.*?)</th>", row, re.I | re.S)
        td = re.search(r"<td[^>]*>(.*?)</td>", row, re.I | re.S)
        if not th or not td:
            continue
        name = _strip_html(th.group(1))
        value = _strip_html(td.group(1))
        if name and value:
            props.append(ParsedShopProperty(name=name, value=value))
    # Fallback: <div class="spec">Name</div><div class="value">Value</div>
    if not props:
        pairs = re.findall(
            r"<div[^>]*class=[\"'][^\"']*(spec|name)[^\"']*[\"'][^>]*>(.*?)</div>\s*"
            r"<div[^>]*class=[\"'][^\"']*(value|val)[^\"']*[\"'][^>]*>(.*?)</div>",
            html,
            re.I | re.S,
        )
        for _, name_html, __, value_html in pairs:
            name = _strip_html(name_html)
            value = _strip_html(value_html)
            if name and value:
                props.append(ParsedShopProperty(name=name, value=value))
    return props


def _extract_price(html: str) -> Optional[float]:
    if not html:
        return None
    meta = re.search(r'itemprop=["\']price["\']\s+content=["\']([^"\']+)["\']', html, re.I)
    if meta:
        return _normalize_price(meta.group(1))
    og_price = re.search(r'property=["\']product:price:amount["\']\s+content=["\']([^"\']+)["\']', html, re.I)
    if og_price:
        return _normalize_price(og_price.group(1))
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
        properties = []
        if product_ld:
            properties.extend(_extract_properties_from_ld(product_ld))
        properties.extend(_extract_properties_from_html(html))
        title = product_data.get("title") or _extract_title(html)
        price = product_data.get("price")
        if price is None:
            price = _extract_price(html)
        currency = product_data.get("currency") or _extract_currency(html)
        in_stock = bool(product_data.get("in_stock")) if product_data else False
        sku = product_data.get("sku") or ""
        images = product_data.get("images") or []
        return ParsedShopResult(
            title=title,
            sku=sku,
            price=price,
            currency=currency,
            in_stock=in_stock if price is not None else False,
            stock_text="",
            category_hint="",
            properties=properties,
            images=images,
            shop_code=self.shop_code,
            canonical_url=url,
            raw={"status": response.status_code, "content_type": response.headers.get("Content-Type", "")},
        )


class E2E4Parser(BaseShopParser):
    def parse(self, url: str) -> ParsedShopResult:
        response = self.http.fetch(url)
        html = response.text or ""
        jsonld = _extract_jsonld(html)
        product_ld = _find_product_ld(jsonld)
        product_data = _extract_product_from_ld(product_ld) if product_ld else {}

        title = product_data.get("title") or _extract_title(html)
        price = product_data.get("price") or _extract_price(html)
        currency = product_data.get("currency") or _extract_currency(html)
        sku = product_data.get("sku") or ""
        if not sku:
            match = re.search(r"Артикул[^<]*</[^>]+>\s*([^<]+)", html, re.I)
            if match:
                sku = match.group(1).strip()
        in_stock = bool(product_data.get("in_stock")) if product_data else False
        properties = []
        if product_ld:
            properties.extend(_extract_properties_from_ld(product_ld))
        properties.extend(_extract_properties_from_html(html))
        return ParsedShopResult(
            title=title,
            sku=sku,
            price=price,
            currency=currency,
            in_stock=in_stock if price is not None else False,
            stock_text="",
            category_hint="",
            properties=properties,
            images=product_data.get("images") or [],
            shop_code=self.shop_code,
            canonical_url=url,
            raw={"status": response.status_code, "content_type": response.headers.get("Content-Type", "")},
        )


class ChipDipParser(BaseShopParser):
    def parse(self, url: str) -> ParsedShopResult:
        response = self.http.fetch(url)
        html = response.text or ""
        jsonld = _extract_jsonld(html)
        product_ld = _find_product_ld(jsonld)
        product_data = _extract_product_from_ld(product_ld) if product_ld else {}

        title = product_data.get("title") or _extract_title(html)
        price = product_data.get("price")
        if price is None:
            match = re.search(r"price[^>]*content=[\"']([^\"']+)[\"']", html, re.I)
            if match:
                price = _normalize_price(match.group(1))
            else:
                price = _extract_price(html)
        currency = product_data.get("currency") or _extract_currency(html)
        sku = product_data.get("sku") or ""
        if not sku:
            match = re.search(r"Код товара[^<]*</[^>]+>\s*([^<]+)", html, re.I)
            if match:
                sku = match.group(1).strip()
        in_stock = bool(product_data.get("in_stock")) if product_data else False
        properties = []
        if product_ld:
            properties.extend(_extract_properties_from_ld(product_ld))
        properties.extend(_extract_properties_from_html(html))
        return ParsedShopResult(
            title=title,
            sku=sku,
            price=price,
            currency=currency,
            in_stock=in_stock if price is not None else False,
            stock_text="",
            category_hint="",
            properties=properties,
            images=product_data.get("images") or [],
            shop_code=self.shop_code,
            canonical_url=url,
            raw={"status": response.status_code, "content_type": response.headers.get("Content-Type", "")},
        )


class DNSParser(BaseShopParser):
    def parse(self, url: str) -> ParsedShopResult:
        response = self.http.fetch(url)
        html = response.text or ""
        jsonld = _extract_jsonld(html)
        product_ld = _find_product_ld(jsonld)
        product_data = _extract_product_from_ld(product_ld) if product_ld else {}

        price = product_data.get("price")
        if price is None:
            match = re.search(r'"price":\s*\{"current":\s*(\d+)', html)
            if match:
                price = _normalize_price(match.group(1))
        title = product_data.get("title") or _extract_title(html)
        currency = product_data.get("currency") or _extract_currency(html)
        in_stock = bool(product_data.get("in_stock")) if product_data else False
        sku = product_data.get("sku") or ""
        images = product_data.get("images") or []
        properties = []
        if product_ld:
            properties.extend(_extract_properties_from_ld(product_ld))
        properties.extend(_extract_properties_from_html(html))
        return ParsedShopResult(
            title=title,
            sku=sku,
            price=price,
            currency=currency,
            in_stock=in_stock if price is not None else False,
            stock_text="",
            category_hint="",
            properties=properties,
            images=images,
            shop_code=self.shop_code,
            canonical_url=url,
            raw={"status": response.status_code, "content_type": response.headers.get("Content-Type", "")},
        )


class WildberriesParser(BaseShopParser):
    def parse(self, url: str) -> ParsedShopResult:
        nm_match = re.search(r"/(?:catalog|product|detail)/(\d+)", url)
        nm_id = nm_match.group(1) if nm_match else None
        if nm_id:
            api_url = (
                "https://card.wb.ru/cards/v1/detail"
                f"?appType=1&curr=rub&dest=-1257786&nm={nm_id}"
            )
            try:
                response = self.http.fetch(api_url)
                data = json.loads(response.text)
                product = (data.get("data") or {}).get("products") or []
                product = product[0] if product else {}
                title = product.get("name") or ""
                sku = str(product.get("id") or "")
                price_u = product.get("salePriceU") or product.get("priceU")
                price = float(price_u) / 100 if price_u is not None else None
                in_stock = bool(product.get("qty") or product.get("quantity") or product.get("totalQuantity"))
                return ParsedShopResult(
                    title=title,
                    sku=sku,
                    price=price,
                    currency="RUB",
                    in_stock=in_stock if price is not None else False,
                    stock_text="",
                    category_hint="",
                    properties=[],
                    images=[],
                    shop_code=self.shop_code,
                    canonical_url=url,
                    raw={"status": response.status_code, "content_type": response.headers.get("Content-Type", "")},
                )
            except Exception:
                pass
        return super().parse(url)


def build_default_parsers(http: HttpClient) -> list[IShopParser]:
    return [
        E2E4Parser(domain="e2e4online.ru", shop_code="e2e4", http=http),
        ChipDipParser(domain="chipdip.ru", shop_code="chipdip", http=http),
        DNSParser(domain="dns-shop.ru", shop_code="dns", http=http),
        WildberriesParser(domain="wildberries.ru", shop_code="wildberries", http=http),
    ]
