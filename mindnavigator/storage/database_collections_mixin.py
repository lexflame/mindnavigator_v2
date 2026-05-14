"""DatabaseCollectionsMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseCollectionsMixin:
    @staticmethod
    def _normalize_collection_entity_type(entity_type: str) -> str:
        value = (entity_type or "").strip().lower() or "other"
        if value not in COLLECTION_ENTITY_TYPES:
            raise ValueError(
                "Тип коллекции должен быть одним из: building, city, film, game, character, other."
            )
        return value

    def fetch_collection_items(
        self,
        search_text: str = "",
        topic: Optional[str] = None,
        entity_type: Optional[str] = None,
        category_ids: Optional[Iterable[int]] = None,
    ) -> List[CollectionItemData]:
        """Возвращает элементы режима коллекций."""
        clauses: list[str] = []
        params: list[object] = []
        search_text = (search_text or "").strip().lower()
        topic = (topic or "").strip()
        if search_text:
            clauses.append(
                "(lower(title) LIKE ? OR lower(topic) LIKE ? OR lower(description) LIKE ? OR lower(source_url) LIKE ?)"
            )
            like = f"%{search_text}%"
            params.extend([like, like, like, like])
        if topic:
            clauses.append("topic = ?")
            params.append(topic)
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(self._normalize_collection_entity_type(entity_type))
        if category_ids is not None:
            category_list = [int(value) for value in category_ids if value is not None]
            if not category_list:
                return []
            placeholders = ", ".join("?" for _ in category_list)
            clauses.append(f"category_id IN ({placeholders})")
            params.extend(category_list)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT id, title, category_id, entity_type, topic, image_url, source_url, description,
                   source_folder_path, import_options_json, created_at, updated_at
            FROM collection_items
            {where_sql}
            ORDER BY updated_at DESC, title COLLATE NOCASE ASC, id DESC;
            """,
            tuple(params),
        ).fetchall()
        return [
            CollectionItemData(
                row["id"],
                row["title"],
                row["category_id"],
                row["entity_type"],
                row["topic"] or "",
                row["image_url"] or "",
                row["source_url"] or "",
                row["description"] or "",
                row["source_folder_path"] or "",
                row["import_options_json"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def fetch_collection_source_folders(self) -> List[dict]:
        rows = self._conn.execute(
            """
            SELECT id, title, source_folder_path
            FROM collection_items
            WHERE trim(source_folder_path) <> '';
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_collection_topics(self) -> List[str]:
        """Возвращает список тем коллекций."""
        rows = self._conn.execute(
            """
            SELECT DISTINCT topic
            FROM collection_items
            WHERE trim(topic) <> ''
            ORDER BY topic COLLATE NOCASE ASC;
            """
        ).fetchall()
        return [row["topic"] for row in rows]

    def create_collection_item(
        self,
        *,
        title: str,
        entity_type: str,
        category_id: Optional[int] = None,
        topic: str = "",
        image_url: str = "",
        source_url: str = "",
        description: str = "",
        source_folder_path: str = "",
        import_options_json: str = "",
    ) -> CollectionItemData:
        """Создает элемент коллекции."""
        title = validate_title(title)
        entity_type = self._normalize_collection_entity_type(entity_type)
        topic = (topic or "").strip()
        image_url = (image_url or "").strip()
        source_url = (source_url or "").strip()
        description = (description or "").strip()
        source_folder_path = (source_folder_path or "").strip()
        import_options_json = (import_options_json or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO collection_items
                (title, category_id, entity_type, topic, image_url, source_url, description,
                 source_folder_path, import_options_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    title,
                    category_id,
                    entity_type,
                    topic,
                    image_url,
                    source_url,
                    description,
                    source_folder_path,
                    import_options_json,
                    now,
                    now,
                ),
            )
        return CollectionItemData(
            cur.lastrowid,
            title,
            category_id,
            entity_type,
            topic,
            image_url,
            source_url,
            description,
            source_folder_path,
            import_options_json,
            now,
            now,
        )

    def update_collection_item(
        self,
        item_id: int,
        *,
        title: str,
        entity_type: str,
        category_id: Optional[int] = None,
        topic: str = "",
        image_url: str = "",
        source_url: str = "",
        description: str = "",
        source_folder_path: Optional[str] = None,
        import_options_json: Optional[str] = None,
    ) -> CollectionItemData:
        """Обновляет элемент коллекции."""
        title = validate_title(title)
        entity_type = self._normalize_collection_entity_type(entity_type)
        topic = (topic or "").strip()
        image_url = (image_url or "").strip()
        source_url = (source_url or "").strip()
        description = (description or "").strip()
        if source_folder_path is None or import_options_json is None:
            existing = self._conn.execute(
                """
                SELECT source_folder_path, import_options_json
                FROM collection_items
                WHERE id = ?;
                """,
                (item_id,),
            ).fetchone()
            if existing is None:
                raise ValueError("Элемент коллекции не найден.")
            if source_folder_path is None:
                source_folder_path = existing["source_folder_path"] or ""
            if import_options_json is None:
                import_options_json = existing["import_options_json"] or ""
        source_folder_path = (source_folder_path or "").strip()
        import_options_json = (import_options_json or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE collection_items
                SET title = ?, category_id = ?, entity_type = ?, topic = ?, image_url = ?, source_url = ?,
                    description = ?, source_folder_path = ?, import_options_json = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    category_id,
                    entity_type,
                    topic,
                    image_url,
                    source_url,
                    description,
                    source_folder_path,
                    import_options_json,
                    now,
                    item_id,
                ),
            )
        row = self._conn.execute(
            """
            SELECT id, title, category_id, entity_type, topic, image_url, source_url, description,
                   source_folder_path, import_options_json, created_at, updated_at
            FROM collection_items
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Элемент коллекции не найден.")
        return CollectionItemData(
            row["id"],
            row["title"],
            row["category_id"],
            row["entity_type"],
            row["topic"] or "",
            row["image_url"] or "",
            row["source_url"] or "",
            row["description"] or "",
            row["source_folder_path"] or "",
            row["import_options_json"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def delete_collection_item(self, item_id: int) -> None:
        """Удаляет элемент коллекции."""
        with self._conn:
            self._conn.execute("DELETE FROM collection_items WHERE id = ?;", (item_id,))

    def create_collection_category(
        self,
        title: str,
        parent_id: Optional[int] = None,
        sort_index: int = 0,
    ) -> CollectionCategoryData:
        title = validate_title(title, field_name="Категория")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO collection_category (title, parent_id, sort_index, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (title, parent_id, int(sort_index), now, now),
            )
        return CollectionCategoryData(cur.lastrowid, title, parent_id, int(sort_index), now, now)

    def fetch_collection_categories(self) -> List[CollectionCategoryData]:
        rows = self._conn.execute(
            """
            SELECT id, title, parent_id, sort_index, created_at, updated_at
            FROM collection_category
            ORDER BY sort_index ASC, title COLLATE NOCASE ASC, id ASC;
            """
        ).fetchall()
        return [
            CollectionCategoryData(
                row["id"],
                row["title"],
                row["parent_id"],
                row["sort_index"] or 0,
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def list_collection_category_tree(self) -> List[CollectionCategoryData]:
        return self.fetch_collection_categories()

    def ensure_collection_category_path(
        self,
        path: str,
        base_parent_id: Optional[int] = None,
    ) -> Optional[int]:
        parts = [part.strip() for part in (path or "").split("/") if part.strip()]
        if not parts:
            return base_parent_id
        parent_id = base_parent_id
        for title in parts:
            if parent_id is None:
                row = self._conn.execute(
                    """
                    SELECT id
                    FROM collection_category
                    WHERE title = ? AND parent_id IS NULL;
                    """,
                    (title,),
                ).fetchone()
            else:
                row = self._conn.execute(
                    """
                    SELECT id
                    FROM collection_category
                    WHERE title = ? AND parent_id = ?;
                    """,
                    (title, parent_id),
                ).fetchone()
            if row is None:
                category = self.create_collection_category(title, parent_id=parent_id)
                parent_id = category.id
            else:
                parent_id = row["id"]
        return parent_id

    def get_collection_category(self, category_id: int) -> Optional[CollectionCategoryData]:
        row = self._conn.execute(
            """
            SELECT id, title, parent_id, sort_index, created_at, updated_at
            FROM collection_category
            WHERE id = ?;
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            return None
        return CollectionCategoryData(
            row["id"],
            row["title"],
            row["parent_id"],
            row["sort_index"] or 0,
            row["created_at"],
            row["updated_at"],
        )

    def update_collection_category_title(self, category_id: int, title: str) -> CollectionCategoryData:
        title = validate_title(title, field_name="Категория")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE collection_category
                SET title = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, now, category_id),
            )
        row = self._conn.execute(
            """
            SELECT id, title, parent_id, sort_index, created_at, updated_at
            FROM collection_category
            WHERE id = ?;
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Категория не найдена.")
        return CollectionCategoryData(
            row["id"],
            row["title"],
            row["parent_id"],
            row["sort_index"] or 0,
            row["created_at"],
            row["updated_at"],
        )

    def move_collection_category(self, category_id: int, parent_id: Optional[int]) -> CollectionCategoryData:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE collection_category
                SET parent_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (parent_id, now, category_id),
            )
        row = self._conn.execute(
            """
            SELECT id, title, parent_id, sort_index, created_at, updated_at
            FROM collection_category
            WHERE id = ?;
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Категория не найдена.")
        return CollectionCategoryData(
            row["id"],
            row["title"],
            row["parent_id"],
            row["sort_index"] or 0,
            row["created_at"],
            row["updated_at"],
        )

    def delete_collection_category(
        self,
        category_id: int,
        *,
        move_children_to_root: bool = False,
        move_items_to_root: bool = False,
    ) -> None:
        children_count = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM collection_category WHERE parent_id = ?;",
            (category_id,),
        ).fetchone()["cnt"]
        items_count = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM collection_items WHERE category_id = ?;",
            (category_id,),
        ).fetchone()["cnt"]
        if children_count and not move_children_to_root:
            raise ValueError("Категория содержит подкатегории.")
        if items_count and not move_items_to_root:
            raise ValueError("Категория содержит коллекции.")
        with self._conn:
            if move_children_to_root:
                self._conn.execute(
                    "UPDATE collection_category SET parent_id = NULL WHERE parent_id = ?;",
                    (category_id,),
                )
            if move_items_to_root:
                self._conn.execute(
                    "UPDATE collection_items SET category_id = NULL WHERE category_id = ?;",
                    (category_id,),
                )
            self._conn.execute("DELETE FROM collection_category WHERE id = ?;", (category_id,))

    def fetch_collection_relations(self, item_id: Optional[int] = None) -> List[CollectionRelationData]:
        """Возвращает связи элементов коллекции."""
        if item_id is None:
            rows = self._conn.execute(
                """
                SELECT id, left_item_id, right_item_id, relation_kind, created_at
                FROM collection_relations
                ORDER BY created_at DESC, id DESC;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, left_item_id, right_item_id, relation_kind, created_at
                FROM collection_relations
                WHERE left_item_id = ? OR right_item_id = ?
                ORDER BY created_at DESC, id DESC;
                """,
                (item_id, item_id),
            ).fetchall()
        return [
            CollectionRelationData(
                row["id"],
                row["left_item_id"],
                row["right_item_id"],
                row["relation_kind"] or "=",
                row["created_at"],
            )
            for row in rows
        ]

    def create_collection_relation(
        self,
        left_item_id: int,
        right_item_id: int,
        relation_kind: str = "=",
    ) -> CollectionRelationData:
        """Создает перекрестную связь между элементами коллекции."""
        if left_item_id == right_item_id:
            raise ValueError("Нельзя связать элемент сам с собой.")
        left_id, right_id = sorted((int(left_item_id), int(right_item_id)))
        relation_kind = (relation_kind or "=").strip() or "="
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO collection_relations
                (left_item_id, right_item_id, relation_kind, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (left_id, right_id, relation_kind, now),
            )
        row = self._conn.execute(
            """
            SELECT id, left_item_id, right_item_id, relation_kind, created_at
            FROM collection_relations
            WHERE left_item_id = ? AND right_item_id = ? AND relation_kind = ?;
            """,
            (left_id, right_id, relation_kind),
        ).fetchone()
        if row is None:
            raise ValueError("Не удалось создать связь коллекции.")
        return CollectionRelationData(
            row["id"],
            row["left_item_id"],
            row["right_item_id"],
            row["relation_kind"] or "=",
            row["created_at"],
        )

    def delete_collection_relation(self, relation_id: int) -> None:
        """Удаляет связь коллекции."""
        with self._conn:
            self._conn.execute("DELETE FROM collection_relations WHERE id = ?;", (relation_id,))

    def create_collection_entries(
        self,
        collection_id: int,
        entries: Iterable[dict],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload = []
        for entry in entries:
            payload.append(
                (
                    collection_id,
                    (entry.get("source_path") or "").strip(),
                    (entry.get("rel_path") or "").strip(),
                    (entry.get("title") or "").strip(),
                    (entry.get("ext") or "").strip(),
                    (entry.get("mime") or "").strip(),
                    int(entry.get("size_bytes") or 0),
                    (entry.get("meta_json") or "").strip(),
                    int(bool(entry.get("is_missing") or 0)),
                    now,
                    now,
                )
            )
        if not payload:
            return
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO collection_item
                (collection_id, source_path, rel_path, title, ext, mime, size_bytes, meta_json, is_missing, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                payload,
            )

    def fetch_collection_entries(self, collection_id: int) -> List[CollectionEntryData]:
        rows = self._conn.execute(
            """
            SELECT id, collection_id, source_path, rel_path, title, ext, mime, size_bytes, meta_json, is_missing,
                   created_at, updated_at
            FROM collection_item
            WHERE collection_id = ?
            ORDER BY rel_path COLLATE NOCASE ASC, id ASC;
            """,
            (collection_id,),
        ).fetchall()
        return [
            CollectionEntryData(
                row["id"],
                row["collection_id"],
                row["source_path"],
                row["rel_path"],
                row["title"],
                row["ext"] or "",
                row["mime"] or "",
                row["size_bytes"] or 0,
                row["meta_json"] or "",
                bool(row["is_missing"]),
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def delete_collection_entry(self, entry_id: int) -> None:
        """Deletes a single entry row from a collection without touching source files."""
        with self._conn:
            self._conn.execute("DELETE FROM collection_item WHERE id = ?;", (entry_id,))

    def sync_collection_entries(
        self,
        collection_id: int,
        entries: Iterable[dict],
    ) -> None:
        existing_rows = self._conn.execute(
            """
            SELECT id, rel_path
            FROM collection_item
            WHERE collection_id = ?;
            """,
            (collection_id,),
        ).fetchall()
        existing_by_rel = {row["rel_path"]: row["id"] for row in existing_rows}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        incoming_rel = set()
        with self._conn:
            for entry in entries:
                rel_path = (entry.get("rel_path") or "").strip()
                if not rel_path:
                    continue
                incoming_rel.add(rel_path)
                if rel_path in existing_by_rel:
                    self._conn.execute(
                        """
                        UPDATE collection_item
                        SET source_path = ?, title = ?, ext = ?, mime = ?, size_bytes = ?, meta_json = ?,
                            is_missing = 0, updated_at = ?
                        WHERE id = ?;
                        """,
                        (
                            (entry.get("source_path") or "").strip(),
                            (entry.get("title") or "").strip(),
                            (entry.get("ext") or "").strip(),
                            (entry.get("mime") or "").strip(),
                            int(entry.get("size_bytes") or 0),
                            (entry.get("meta_json") or "").strip(),
                            now,
                            existing_by_rel[rel_path],
                        ),
                    )
                else:
                    self._conn.execute(
                        """
                        INSERT INTO collection_item
                        (collection_id, source_path, rel_path, title, ext, mime, size_bytes, meta_json, is_missing, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
                        """,
                        (
                            collection_id,
                            (entry.get("source_path") or "").strip(),
                            rel_path,
                            (entry.get("title") or "").strip(),
                            (entry.get("ext") or "").strip(),
                            (entry.get("mime") or "").strip(),
                            int(entry.get("size_bytes") or 0),
                            (entry.get("meta_json") or "").strip(),
                            now,
                            now,
                        ),
                    )
            missing_rel = set(existing_by_rel.keys()) - incoming_rel
            for rel_path in missing_rel:
                self._conn.execute(
                    """
                    UPDATE collection_item
                    SET is_missing = 1, updated_at = ?
                    WHERE id = ?;
                    """,
                    (now, existing_by_rel[rel_path]),
                )

__all__ = ["DatabaseCollectionsMixin"]
