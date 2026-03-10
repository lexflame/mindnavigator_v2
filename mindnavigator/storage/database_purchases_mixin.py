"""DatabasePurchasesMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabasePurchasesMixin:
    def create_shop_category(self, title: str, parent_id: Optional[int] = None) -> ShopCategoryData:
        title = validate_title(title, field_name="РљР°С‚РµРіРѕСЂРёСЏ")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO shop_category (title, parent_id)
                VALUES (?, ?);
                """,
                (title, parent_id),
            )
        return ShopCategoryData(cur.lastrowid, title, parent_id)

    def fetch_shop_categories(self) -> List[ShopCategoryData]:
        rows = self._conn.execute(
            """
            SELECT id, title, parent_id
            FROM shop_category
            ORDER BY title COLLATE NOCASE ASC, id ASC;
            """
        ).fetchall()
        return [
            ShopCategoryData(
                row["id"],
                row["title"],
                row["parent_id"],
            )
            for row in rows
        ]

    def get_shop_category(self, category_id: int) -> Optional[ShopCategoryData]:
        row = self._conn.execute(
            "SELECT id, title, parent_id FROM shop_category WHERE id = ?;",
            (category_id,),
        ).fetchone()
        if row is None:
            return None
        return ShopCategoryData(row["id"], row["title"], row["parent_id"])

    def update_shop_category_title(self, category_id: int, title: str) -> ShopCategoryData:
        title = validate_title(title, field_name="Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ")
        with self._conn:
            self._conn.execute(
                """
                UPDATE shop_category
                SET title = ?
                WHERE id = ?;
                """,
                (title, category_id),
            )
        row = self._conn.execute(
            "SELECT id, title, parent_id FROM shop_category WHERE id = ?;",
            (category_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…Р В°.")
        return ShopCategoryData(row["id"], row["title"], row["parent_id"])

    def delete_shop_category(self, category_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_category WHERE id = ?;", (category_id,))

    def get_shop_item(self, item_id: int) -> Optional[ShopItemData]:
        row = self._conn.execute(
            """
            SELECT id, title, category_id, user_notes, created_at, updated_at
            FROM shop_item
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return ShopItemData(
            row["id"],
            row["title"],
            row["category_id"],
            row["user_notes"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def update_shop_item_category(
        self,
        item_id: int,
        category_id: Optional[int],
    ) -> ShopItemData:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE shop_item
                SET category_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (category_id, now, item_id),
            )
        row = self._conn.execute(
            """
            SELECT id, title, category_id, user_notes, created_at, updated_at
            FROM shop_item
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Р СћР С•Р Р†Р В°РЎР‚ Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р….")
        return ShopItemData(
            row["id"],
            row["title"],
            row["category_id"],
            row["user_notes"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def fetch_shop_sources(self, item_id: int) -> List[ShopSourceData]:
        rows = self._conn.execute(
            """
            SELECT id, item_id, shop_code, url, sku, currency, price, in_stock, stock_text, parsed_at, raw_json
            FROM shop_source
            WHERE item_id = ?
            ORDER BY parsed_at DESC, id DESC;
            """,
            (item_id,),
        ).fetchall()
        return [
            ShopSourceData(
                row["id"],
                row["item_id"],
                row["shop_code"] or "",
                row["url"] or "",
                row["sku"] or "",
                row["currency"] or "",
                row["price"],
                bool(row["in_stock"]),
                row["stock_text"] or "",
                row["parsed_at"] or "",
                row["raw_json"] or "",
            )
            for row in rows
        ]

    def fetch_shop_sources_for_items(self, item_ids: List[int]) -> List[ShopSourceData]:
        if not item_ids:
            return []
        placeholders = ",".join("?" for _ in item_ids)
        rows = self._conn.execute(
            f"""
            SELECT id, item_id, shop_code, url, sku, currency, price, in_stock, stock_text, parsed_at, raw_json
            FROM shop_source
            WHERE item_id IN ({placeholders})
            ORDER BY item_id ASC, parsed_at DESC, id DESC;
            """,
            tuple(item_ids),
        ).fetchall()
        return [
            ShopSourceData(
                row["id"],
                row["item_id"],
                row["shop_code"] or "",
                row["url"] or "",
                row["sku"] or "",
                row["currency"] or "",
                row["price"],
                bool(row["in_stock"]),
                row["stock_text"] or "",
                row["parsed_at"] or "",
                row["raw_json"] or "",
            )
            for row in rows
        ]

    def delete_shop_source(self, source_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_source WHERE id = ?;", (source_id,))

    def delete_shop_item(self, item_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_item WHERE id = ?;", (item_id,))

    def fetch_shop_item_properties(self, item_id: int) -> List[ShopItemPropertyData]:
        rows = self._conn.execute(
            """
            SELECT id, item_id, name, value, unit, normalized_key
            FROM shop_item_property
            WHERE item_id = ?
            ORDER BY normalized_key COLLATE NOCASE ASC, id ASC;
            """,
            (item_id,),
        ).fetchall()
        return [
            ShopItemPropertyData(
                row["id"],
                row["item_id"],
                row["name"] or "",
                row["value"] or "",
                row["unit"] or "",
                row["normalized_key"] or "",
            )
            for row in rows
        ]

    def fetch_shop_source_properties(self, source_id: int) -> List[ShopSourcePropertyData]:
        rows = self._conn.execute(
            """
            SELECT id, source_id, name, value, unit, normalized_key
            FROM shop_source_property
            WHERE source_id = ?
            ORDER BY normalized_key COLLATE NOCASE ASC, id ASC;
            """,
            (source_id,),
        ).fetchall()
        return [
            ShopSourcePropertyData(
                row["id"],
                row["source_id"],
                row["name"] or "",
                row["value"] or "",
                row["unit"] or "",
                row["normalized_key"] or "",
            )
            for row in rows
        ]

    def replace_shop_source_properties(
        self,
        source_id: int,
        properties: List[ShopSourcePropertyData],
    ) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_source_property WHERE source_id = ?;", (source_id,))
            for prop in properties:
                self._conn.execute(
                    """
                    INSERT INTO shop_source_property (source_id, name, value, unit, normalized_key)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        source_id,
                        prop.name,
                        prop.value,
                        prop.unit,
                        prop.normalized_key,
                    ),
                )

    def upsert_shop_item_property(
        self,
        *,
        item_id: int,
        name: str,
        value: str,
        unit: str = "",
        normalized_key: str = "",
    ) -> ShopItemPropertyData:
        name = (name or "").strip()
        value = (value or "").strip()
        unit = (unit or "").strip()
        normalized_key = (normalized_key or "").strip()
        with self._conn:
            row = self._conn.execute(
                """
                SELECT id FROM shop_item_property
                WHERE item_id = ? AND normalized_key = ?;
                """,
                (item_id, normalized_key),
            ).fetchone()
            if row is None:
                cur = self._conn.execute(
                    """
                    INSERT INTO shop_item_property (item_id, name, value, unit, normalized_key)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (item_id, name, value, unit, normalized_key),
                )
                prop_id = cur.lastrowid
            else:
                prop_id = row["id"]
                self._conn.execute(
                    """
                    UPDATE shop_item_property
                    SET name = ?, value = ?, unit = ?, normalized_key = ?
                    WHERE id = ?;
                    """,
                    (name, value, unit, normalized_key, prop_id),
                )
        return ShopItemPropertyData(prop_id, item_id, name, value, unit, normalized_key)

    def delete_shop_item_property(self, property_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_item_property WHERE id = ?;", (property_id,))

    def add_shop_compare_item(self, item_id: int, category_id: Optional[int]) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO shop_compare_set (category_id, item_id)
                VALUES (?, ?);
                """,
                (category_id, item_id),
            )

    def remove_shop_compare_item(self, item_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_compare_set WHERE item_id = ?;", (item_id,))

    def fetch_shop_compare_items(self, category_id: Optional[int]) -> List[ShopItemData]:
        if category_id is None:
            rows = self._conn.execute(
                """
                SELECT i.id, i.title, i.category_id, i.user_notes, i.created_at, i.updated_at
                FROM shop_compare_set c
                JOIN shop_item i ON i.id = c.item_id
                ORDER BY i.title COLLATE NOCASE ASC, i.id ASC;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT i.id, i.title, i.category_id, i.user_notes, i.created_at, i.updated_at
                FROM shop_compare_set c
                JOIN shop_item i ON i.id = c.item_id
                WHERE c.category_id = ?
                ORDER BY i.title COLLATE NOCASE ASC, i.id ASC;
                """,
                (category_id,),
            ).fetchall()
        return [
            ShopItemData(
                row["id"],
                row["title"],
                row["category_id"],
                row["user_notes"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def fetch_wishlists(self) -> List[WishlistData]:
        rows = self._conn.execute(
            """
            SELECT id, title, notes
            FROM wishlist
            ORDER BY title COLLATE NOCASE ASC, id ASC;
            """
        ).fetchall()
        return [WishlistData(row["id"], row["title"], row["notes"] or "") for row in rows]

    def create_wishlist(self, title: str, notes: str = "") -> WishlistData:
        title = validate_title(title, field_name="РЎРїРёСЃРѕРє")
        notes = (notes or "").strip()
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO wishlist (title, notes)
                VALUES (?, ?);
                """,
                (title, notes),
            )
        return WishlistData(cur.lastrowid, title, notes)

    def update_wishlist(self, wishlist_id: int, title: str, notes: str = "") -> WishlistData:
        title = validate_title(title, field_name="РЎРїРёСЃРѕРє")
        notes = (notes or "").strip()
        with self._conn:
            self._conn.execute(
                """
                UPDATE wishlist
                SET title = ?, notes = ?
                WHERE id = ?;
                """,
                (title, notes, wishlist_id),
            )
        return WishlistData(wishlist_id, title, notes)

    def delete_wishlist(self, wishlist_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM wishlist WHERE id = ?;", (wishlist_id,))

    def fetch_wishlist_items(self, wishlist_id: int) -> List[WishlistItemData]:
        rows = self._conn.execute(
            """
            SELECT wishlist_id, item_id, qty, priority, target_price, chosen_source_id
            FROM wishlist_item
            WHERE wishlist_id = ?
            ORDER BY priority ASC, item_id ASC;
            """,
            (wishlist_id,),
        ).fetchall()
        return [
            WishlistItemData(
                row["wishlist_id"],
                row["item_id"],
                row["qty"],
                row["priority"],
                row["target_price"],
                row["chosen_source_id"],
            )
            for row in rows
        ]

    def upsert_wishlist_item(
        self,
        *,
        wishlist_id: int,
        item_id: int,
        qty: int = 1,
        priority: int = 3,
        target_price: Optional[float] = None,
        chosen_source_id: Optional[int] = None,
    ) -> WishlistItemData:
        qty = max(1, int(qty))
        priority = max(1, min(5, int(priority)))
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO wishlist_item
                (wishlist_id, item_id, qty, priority, target_price, chosen_source_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(wishlist_id, item_id) DO UPDATE SET
                    qty = excluded.qty,
                    priority = excluded.priority,
                    target_price = excluded.target_price,
                    chosen_source_id = excluded.chosen_source_id;
                """,
                (wishlist_id, item_id, qty, priority, target_price, chosen_source_id),
            )
        return WishlistItemData(wishlist_id, item_id, qty, priority, target_price, chosen_source_id)

    def delete_wishlist_item(self, wishlist_id: int, item_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM wishlist_item WHERE wishlist_id = ? AND item_id = ?;",
                (wishlist_id, item_id),
            )

    def export_purchases_data(self) -> dict:
        def rows_to_dicts(query: str):
            rows = self._conn.execute(query).fetchall()
            return [dict(row) for row in rows]

        return {
            "categories": rows_to_dicts("SELECT * FROM shop_category;"),
            "items": rows_to_dicts("SELECT * FROM shop_item;"),
            "sources": rows_to_dicts("SELECT * FROM shop_source;"),
            "price_history": rows_to_dicts("SELECT * FROM shop_price_history;"),
            "item_properties": rows_to_dicts("SELECT * FROM shop_item_property;"),
            "source_properties": rows_to_dicts("SELECT * FROM shop_source_property;"),
            "wishlists": rows_to_dicts("SELECT * FROM wishlist;"),
            "wishlist_items": rows_to_dicts("SELECT * FROM wishlist_item;"),
            "compare_set": rows_to_dicts("SELECT * FROM shop_compare_set;"),
        }

    def import_purchases_data(self, payload: dict) -> None:
        categories = payload.get("categories") or []
        items = payload.get("items") or []
        sources = payload.get("sources") or []
        price_history = payload.get("price_history") or []
        item_props = payload.get("item_properties") or []
        source_props = payload.get("source_properties") or []
        wishlists = payload.get("wishlists") or []
        wishlist_items = payload.get("wishlist_items") or []
        compare_set = payload.get("compare_set") or []

        existing_categories = {(c.title, c.parent_id): c.id for c in self.fetch_shop_categories()}
        category_map: dict[int, Optional[int]] = {}
        for cat in categories:
            key = (cat.get("title"), cat.get("parent_id"))
            if key in existing_categories:
                category_map[cat["id"]] = existing_categories[key]
                continue
            created = self.create_shop_category(cat.get("title") or "Р‘РµР· РєР°С‚РµРіРѕСЂРёРё", cat.get("parent_id"))
            category_map[cat["id"]] = created.id

        source_by_url = {s.url: s for s in self.fetch_shop_sources_for_items([item.id for item in self.fetch_shop_items()])}
        item_sources: dict[int, list[dict]] = {}
        for src in sources:
            item_sources.setdefault(src["item_id"], []).append(src)

        item_map: dict[int, int] = {}
        for item in items:
            existing_item_id = None
            for src in item_sources.get(item["id"], []):
                if src.get("url") in source_by_url:
                    existing_item_id = source_by_url[src["url"]].item_id
                    break
            if existing_item_id is not None:
                item_map[item["id"]] = existing_item_id
                continue
            created = self.create_shop_item(
                item.get("title") or "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ",
                category_id=category_map.get(item.get("category_id")),
                user_notes=item.get("user_notes") or "",
            )
            item_map[item["id"]] = created.id

        source_map: dict[int, int] = {}
        for src in sources:
            url = src.get("url") or ""
            if url in source_by_url:
                source_map[src["id"]] = source_by_url[url].id
                continue
            source = self.upsert_shop_source(
                item_id=item_map.get(src.get("item_id")),
                shop_code=src.get("shop_code") or "",
                url=url,
                sku=src.get("sku") or "",
                currency=src.get("currency") or "",
                price=src.get("price"),
                in_stock=bool(src.get("in_stock")),
                stock_text=src.get("stock_text") or "",
                parsed_at=src.get("parsed_at") or "",
                raw_json=src.get("raw_json") or "",
            )
            source_map[src["id"]] = source.id

        for row in price_history:
            new_source_id = source_map.get(row.get("source_id"))
            if new_source_id is None:
                continue
            self.add_shop_price_history(
                source_id=new_source_id,
                price=row.get("price"),
                currency=row.get("currency") or "",
                in_stock=bool(row.get("in_stock")),
                captured_at=row.get("captured_at") or "",
            )

        for prop in item_props:
            new_item_id = item_map.get(prop.get("item_id"))
            if new_item_id is None:
                continue
            self.upsert_shop_item_property(
                item_id=new_item_id,
                name=prop.get("name") or "",
                value=prop.get("value") or "",
                unit=prop.get("unit") or "",
                normalized_key=prop.get("normalized_key") or "",
            )

        source_props_grouped: dict[int, list[ShopSourcePropertyData]] = {}
        for prop in source_props:
            new_source_id = source_map.get(prop.get("source_id"))
            if new_source_id is None:
                continue
            source_props_grouped.setdefault(new_source_id, []).append(
                ShopSourcePropertyData(
                    id=0,
                    source_id=new_source_id,
                    name=prop.get("name") or "",
                    value=prop.get("value") or "",
                    unit=prop.get("unit") or "",
                    normalized_key=prop.get("normalized_key") or "",
                )
            )
        for source_id, props in source_props_grouped.items():
            self.replace_shop_source_properties(source_id, props)

        wishlist_map: dict[int, int] = {}
        existing_wishlists = {w.title: w.id for w in self.fetch_wishlists()}
        for wl in wishlists:
            title = wl.get("title") or "РЎРїРёСЃРѕРє"
            if title in existing_wishlists:
                wishlist_map[wl["id"]] = existing_wishlists[title]
                continue
            created = self.create_wishlist(title, wl.get("notes") or "")
            wishlist_map[wl["id"]] = created.id

        for wi in wishlist_items:
            new_wishlist_id = wishlist_map.get(wi.get("wishlist_id"))
            new_item_id = item_map.get(wi.get("item_id"))
            if new_wishlist_id is None or new_item_id is None:
                continue
            self.upsert_wishlist_item(
                wishlist_id=new_wishlist_id,
                item_id=new_item_id,
                qty=wi.get("qty") or 1,
                priority=wi.get("priority") or 3,
                target_price=wi.get("target_price"),
                chosen_source_id=source_map.get(wi.get("chosen_source_id")),
            )

        for entry in compare_set:
            new_item_id = item_map.get(entry.get("item_id"))
            new_category_id = category_map.get(entry.get("category_id"))
            if new_item_id is None:
                continue
            self.add_shop_compare_item(new_item_id, new_category_id)

    def create_shop_item(
        self,
        title: str,
        *,
        category_id: Optional[int] = None,
        user_notes: str = "",
    ) -> ShopItemData:
        title = (title or "").strip() or "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ"
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN].rstrip()
        user_notes = (user_notes or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO shop_item (title, category_id, user_notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (title, category_id, user_notes, now, now),
            )
        return ShopItemData(cur.lastrowid, title, category_id, user_notes, now, now)

    def update_shop_item(
        self,
        item_id: int,
        *,
        title: str,
        category_id: Optional[int],
        user_notes: str,
    ) -> ShopItemData:
        title = (title or "").strip() or "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ"
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN].rstrip()
        user_notes = (user_notes or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE shop_item
                SET title = ?, category_id = ?, user_notes = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, category_id, user_notes, now, item_id),
            )
        row = self._conn.execute(
            """
            SELECT id, title, category_id, user_notes, created_at, updated_at
            FROM shop_item
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            raise ValueError("РўРѕРІР°СЂ РЅРµ РЅР°Р№РґРµРЅ.")
        return ShopItemData(
            row["id"],
            row["title"],
            row["category_id"],
            row["user_notes"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def upsert_shop_source(
        self,
        *,
        item_id: int,
        shop_code: str,
        url: str,
        sku: str = "",
        currency: str = "",
        price: Optional[float] = None,
        in_stock: bool = False,
        stock_text: str = "",
        parsed_at: str = "",
        raw_json: str = "",
    ) -> ShopSourceData:
        shop_code = (shop_code or "").strip()
        url = (url or "").strip()
        if not url:
            raise ValueError("URL РёСЃС‚РѕС‡РЅРёРєР° РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        sku = (sku or "").strip()
        currency = (currency or "").strip()
        stock_text = (stock_text or "").strip()
        parsed_at = (parsed_at or "").strip()
        raw_json = (raw_json or "").strip()
        with self._conn:
            row = self._conn.execute(
                "SELECT id FROM shop_source WHERE url = ?;",
                (url,),
            ).fetchone()
            if row is None:
                cur = self._conn.execute(
                    """
                    INSERT INTO shop_source
                    (item_id, shop_code, url, sku, currency, price, in_stock, stock_text, parsed_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        item_id,
                        shop_code,
                        url,
                        sku,
                        currency,
                        price,
                        int(bool(in_stock)),
                        stock_text,
                        parsed_at,
                        raw_json,
                    ),
                )
                source_id = cur.lastrowid
            else:
                source_id = row["id"]
                self._conn.execute(
                    """
                    UPDATE shop_source
                    SET item_id = ?, shop_code = ?, sku = ?, currency = ?, price = ?, in_stock = ?,
                        stock_text = ?, parsed_at = ?, raw_json = ?
                    WHERE id = ?;
                    """,
                    (
                        item_id,
                        shop_code,
                        sku,
                        currency,
                        price,
                        int(bool(in_stock)),
                        stock_text,
                        parsed_at,
                        raw_json,
                        source_id,
                    ),
                )
        return ShopSourceData(
            source_id,
            item_id,
            shop_code,
            url,
            sku,
            currency,
            price,
            bool(in_stock),
            stock_text,
            parsed_at,
            raw_json,
        )

    def add_shop_price_history(
        self,
        *,
        source_id: int,
        price: Optional[float],
        currency: str,
        in_stock: bool,
        captured_at: str,
    ) -> ShopPriceHistoryData:
        currency = (currency or "").strip()
        captured_at = (captured_at or "").strip()
        if not captured_at:
            captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO shop_price_history
                (source_id, price, currency, in_stock, captured_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (source_id, price, currency, int(bool(in_stock)), captured_at),
            )
        return ShopPriceHistoryData(cur.lastrowid, source_id, price, currency, bool(in_stock), captured_at)

    def fetch_shop_price_history(self, source_id: int, days: int) -> List[ShopPriceHistoryData]:
        rows = self._conn.execute(
            """
            SELECT id, source_id, price, currency, in_stock, captured_at
            FROM shop_price_history
            WHERE source_id = ? AND captured_at >= datetime('now', ?)
            ORDER BY captured_at ASC;
            """,
            (source_id, f"-{int(days)} days"),
        ).fetchall()
        return [
            ShopPriceHistoryData(
                row["id"],
                row["source_id"],
                row["price"],
                row["currency"] or "",
                bool(row["in_stock"]),
                row["captured_at"],
            )
            for row in rows
        ]

    def add_shop_parse_log(
        self,
        *,
        source_id: Optional[int],
        shop_code: str,
        url: str,
        status_code: Optional[int],
        content_type: str,
        fetched_at: str,
        raw_snippet: str,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO shop_parse_log
                (source_id, shop_code, url, status_code, content_type, fetched_at, raw_snippet)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    source_id,
                    shop_code,
                    url,
                    status_code,
                    content_type,
                    fetched_at,
                    raw_snippet,
                ),
            )

    def fetch_shop_parse_logs(self, source_id: Optional[int] = None) -> List[dict]:
        if source_id is None:
            rows = self._conn.execute(
                """
                SELECT id, source_id, shop_code, url, status_code, content_type, fetched_at, raw_snippet
                FROM shop_parse_log
                ORDER BY fetched_at DESC, id DESC;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, source_id, shop_code, url, status_code, content_type, fetched_at, raw_snippet
                FROM shop_parse_log
                WHERE source_id = ?
                ORDER BY fetched_at DESC, id DESC;
                """,
                (source_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_shop_items(self, search_text: str = "") -> List[ShopItemData]:
        search_text = (search_text or "").strip().lower()
        params: list[object] = []
        where_sql = ""
        if search_text:
            where_sql = "WHERE lower(title) LIKE ?"
            params.append(f"%{search_text}%")
        rows = self._conn.execute(
            f"""
            SELECT id, title, category_id, user_notes, created_at, updated_at
            FROM shop_item
            {where_sql}
            ORDER BY updated_at DESC, title COLLATE NOCASE ASC, id DESC;
            """,
            tuple(params),
        ).fetchall()
        return [
            ShopItemData(
                row["id"],
                row["title"],
                row["category_id"],
                row["user_notes"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def fetch_shop_items_with_stats(
        self,
        *,
        search_text: str = "",
        category_id: Optional[int] = None,
    ) -> List[dict]:
        search_text = (search_text or "").strip().lower()
        params: list[object] = []
        clauses: list[str] = []
        if search_text:
            clauses.append("lower(i.title) LIKE ?")
            params.append(f"%{search_text}%")
        if category_id is not None:
            clauses.append("i.category_id = ?")
            params.append(category_id)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT
                i.id,
                i.title,
                i.category_id,
                c.title AS category_title,
                i.created_at,
                i.updated_at,
                (
                    SELECT MIN(s.price)
                    FROM shop_source s
                    WHERE s.item_id = i.id AND s.in_stock = 1 AND s.price IS NOT NULL
                ) AS best_price,
                (
                    SELECT MIN(s.price)
                    FROM shop_source s
                    WHERE s.item_id = i.id AND s.price IS NOT NULL
                ) AS best_price_any,
                (
                    SELECT COUNT(*) FROM shop_source s WHERE s.item_id = i.id
                ) AS sources_count,
                (
                    SELECT MAX(s.parsed_at) FROM shop_source s WHERE s.item_id = i.id
                ) AS last_parsed_at
            FROM shop_item i
            LEFT JOIN shop_category c ON c.id = i.category_id
            {where_sql}
            ORDER BY i.updated_at DESC, i.title COLLATE NOCASE ASC, i.id DESC;
            """,
            tuple(params),
        ).fetchall()
        result = []
        for row in rows:
            best_price = row["best_price"]
            if best_price is None:
                best_price = row["best_price_any"]
            result.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "category_id": row["category_id"],
                    "category_title": row["category_title"] or "",
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "best_price": best_price,
                    "sources_count": row["sources_count"] or 0,
                    "last_parsed_at": row["last_parsed_at"] or "",
                }
            )
        return result

    def fetch_item_min_price_last_days(self, item_id: int, days: int) -> Optional[float]:
        row = self._conn.execute(
            """
            SELECT MIN(p.price) AS min_price
            FROM shop_price_history p
            JOIN shop_source s ON s.id = p.source_id
            WHERE s.item_id = ? AND p.price IS NOT NULL AND p.captured_at >= datetime('now', ?);
            """,
            (item_id, f"-{int(days)} days"),
        ).fetchone()
        if row is None:
            return None
        return row["min_price"]

__all__ = ["DatabasePurchasesMixin"]
