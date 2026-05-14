"""DatabaseObjectsCharactersMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseObjectsCharactersMixin:
    def fetch_objects(self) -> List[ObjectData]:
        """Возвращает список архитектурных объектов."""
        rows = self._conn.execute(
            """
            SELECT id, title, catalog, object_type, status, description, created_at, updated_at
            FROM objects
            ORDER BY updated_at DESC;
            """
        ).fetchall()
        return [
            ObjectData(
                row["id"],
                row["title"],
                row["catalog"] or "",
                row["object_type"] or "",
                row["status"] or "",
                row["description"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def create_object(
        self,
        title: str,
        catalog: str,
        object_type: str,
        status: str,
        description: str,
    ) -> ObjectData:
        """Создает архитектурный объект."""
        title = validate_title(title, field_name="Название объекта")
        catalog = (catalog or "").strip()
        object_type = (object_type or "").strip()
        status = (status or "").strip()
        description = (description or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO objects (title, catalog, object_type, status, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (title, catalog, object_type, status, description, now, now),
            )
        return ObjectData(cur.lastrowid, title, catalog, object_type, status, description, now, now)

    def update_object(
        self,
        object_id: int,
        title: str,
        catalog: str,
        object_type: str,
        status: str,
        description: str,
    ) -> ObjectData:
        """Обновляет архитектурный объект."""
        title = validate_title(title, field_name="Название объекта")
        catalog = (catalog or "").strip()
        object_type = (object_type or "").strip()
        status = (status or "").strip()
        description = (description or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE objects
                SET title = ?, catalog = ?, object_type = ?, status = ?, description = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, catalog, object_type, status, description, now, object_id),
            )
        row = self._conn.execute(
            """
            SELECT created_at
            FROM objects
            WHERE id = ?;
            """,
            (object_id,),
        ).fetchone()
        created_at = row["created_at"] if row else now
        return ObjectData(object_id, title, catalog, object_type, status, description, created_at, now)

    def delete_object(self, object_id: int) -> None:
        """Удаляет архитектурный объект."""
        with self._conn:
            self._conn.execute("DELETE FROM objects WHERE id = ?;", (object_id,))

    def create_object_from_folder_path(self, folder_path: str) -> ObjectData:
        """Создает объект на основе пути к папке."""
        path = (folder_path or "").strip().strip("/")
        if not path:
            raise ValueError("Путь к папке не должен быть пустым.")
        parts = [part for part in path.split("/") if part]
        title = parts[-1] if parts else "Новый объект"
        catalog = " / ".join(parts[:-1])
        description = f"Объект создан из папки: {path}"
        return self.create_object(title, catalog, "", "", description)

    def fetch_object_images(self, object_id: int) -> List[ObjectImageData]:
        """Возвращает список изображений объекта."""
        rows = self._conn.execute(
            """
            SELECT id, object_id, rel_path, description, created_at, updated_at
            FROM object_images
            WHERE object_id = ?
            ORDER BY created_at ASC;
            """,
            (object_id,),
        ).fetchall()
        return [
            ObjectImageData(
                row["id"],
                row["object_id"],
                row["rel_path"],
                row["description"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def add_object_image(self, object_id: int, rel_path: str, description: str = "") -> ObjectImageData:
        """Добавляет изображение к объекту."""
        rel_path = (rel_path or "").strip()
        if not rel_path:
            raise ValueError("Путь к изображению не должен быть пустым.")
        description = (description or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO object_images (object_id, rel_path, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (object_id, rel_path, description, now, now),
            )
        row = self._conn.execute(
            """
            SELECT id, object_id, rel_path, description, created_at, updated_at
            FROM object_images
            WHERE object_id = ? AND rel_path = ?;
            """,
            (object_id, rel_path),
        ).fetchone()
        return ObjectImageData(
            row["id"],
            row["object_id"],
            row["rel_path"],
            row["description"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def update_object_image(self, image_id: int, description: str) -> ObjectImageData:
        """Обновляет описание изображения объекта."""
        description = (description or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE object_images
                SET description = ?, updated_at = ?
                WHERE id = ?;
                """,
                (description, now, image_id),
            )
        row = self._conn.execute(
            """
            SELECT id, object_id, rel_path, description, created_at, updated_at
            FROM object_images
            WHERE id = ?;
            """,
            (image_id,),
        ).fetchone()
        return ObjectImageData(
            row["id"],
            row["object_id"],
            row["rel_path"],
            row["description"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def delete_object_image(self, image_id: int) -> None:
        """Удаляет изображение объекта."""
        with self._conn:
            self._conn.execute("DELETE FROM object_images WHERE id = ?;", (image_id,))

    @staticmethod
    def _normalize_character_entity_kind(entity_kind: str) -> str:
        value = (entity_kind or "").strip().lower()
        if value not in CHARACTER_ENTITY_KINDS:
            supported = ", ".join(CHARACTER_ENTITY_KINDS)
            raise ValueError(f"Тип связанной сущности должен быть одним из: {supported}.")
        return value

    @staticmethod
    def _normalize_character_tags(tags: Optional[Iterable[str]]) -> List[str]:
        if tags is None:
            return []
        normalized: List[str] = []
        for raw_tag in tags:
            tag = str(raw_tag or "").strip()
            if tag and tag not in normalized:
                normalized.append(tag)
        return normalized

    @staticmethod
    def _character_tags_from_row(row: Mapping[str, Any]) -> List[str]:
        try:
            raw_tags = json.loads(row["tags"] or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(raw_tags, list):
            return []
        return [str(item).strip() for item in raw_tags if str(item).strip()]

    def _character_entity_exists(self, entity_kind: str, entity_id: int) -> bool:
        target_map = {
            "task": "tasks",
            "project": "projects",
            "note": "notes",
            "idea": "ideas",
            "object": "objects",
            "map": "maps",
            "marker": "map_markers",
            "file": "cloud_files",
            "collection_item": "collection_items",
            "collection_category": "collection_category",
            "shop_category": "shop_category",
            "shop_item": "shop_item",
            "shop_source": "shop_source",
            "wishlist": "wishlist",
        }
        table_name = target_map.get(entity_kind)
        if table_name is None:
            return False
        row = self._conn.execute(
            f"SELECT 1 FROM {table_name} WHERE id = ?;",
            (int(entity_id),),
        ).fetchone()
        return row is not None

    def fetch_characters(
        self,
        search_text: str = "",
        linked_entity_kind: Optional[str] = None,
        linked_entity_id: Optional[int] = None,
    ) -> List[CharacterData]:
        """Возвращает персонажей с фильтрацией по тексту и связанной сущности."""
        clauses: list[str] = []
        params: list[object] = []
        query = (search_text or "").strip().lower()
        if query:
            like = f"%{query}%"
            clauses.append("(lower(name) LIKE ? OR lower(role) LIKE ? OR lower(description) LIKE ? OR lower(tags) LIKE ?)")
            params.extend([like, like, like, like])

        if linked_entity_kind is not None or linked_entity_id is not None:
            if linked_entity_kind is None or linked_entity_id is None:
                return []
            normalized_kind = self._normalize_character_entity_kind(linked_entity_kind)
            linked_id = int(linked_entity_id)
            if linked_id <= 0:
                return []
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM character_links
                    WHERE character_links.character_id = characters.id
                    AND character_links.entity_kind = ?
                    AND character_links.entity_id = ?
                )
                """
            )
            params.extend([normalized_kind, linked_id])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT id, name, role, description, tags, created_at, updated_at
            FROM characters
            {where_sql}
            ORDER BY updated_at DESC, id DESC;
            """,
            tuple(params),
        ).fetchall()
        return [
            CharacterData(
                id=row["id"],
                name=row["name"] or "",
                role=row["role"] or "",
                description=row["description"] or "",
                tags=self._character_tags_from_row(row),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def create_character(
        self,
        name: str,
        role: str = "",
        description: str = "",
        tags: Optional[Iterable[str]] = None,
    ) -> CharacterData:
        """Создает персонажа."""
        name = validate_title(name, field_name="Имя персонажа")
        role = (role or "").strip()
        description = (description or "").strip()
        normalized_tags = self._normalize_character_tags(tags)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO characters (name, role, description, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (name, role, description, json.dumps(normalized_tags, ensure_ascii=False), now, now),
            )
        return CharacterData(
            id=cursor.lastrowid,
            name=name,
            role=role,
            description=description,
            tags=normalized_tags,
            created_at=now,
            updated_at=now,
        )

    def update_character(
        self,
        character_id: int,
        name: str,
        role: str = "",
        description: str = "",
        tags: Optional[Iterable[str]] = None,
    ) -> CharacterData:
        """Обновляет персонажа."""
        name = validate_title(name, field_name="Имя персонажа")
        role = (role or "").strip()
        description = (description or "").strip()
        normalized_tags = self._normalize_character_tags(tags)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE characters
                SET name = ?, role = ?, description = ?, tags = ?, updated_at = ?
                WHERE id = ?;
                """,
                (name, role, description, json.dumps(normalized_tags, ensure_ascii=False), now, int(character_id)),
            )
        row = self._conn.execute(
            "SELECT created_at FROM characters WHERE id = ?;",
            (int(character_id),),
        ).fetchone()
        if row is None:
            raise ValueError("Персонаж не найден.")
        return CharacterData(
            id=int(character_id),
            name=name,
            role=role,
            description=description,
            tags=normalized_tags,
            created_at=row["created_at"],
            updated_at=now,
        )

    def delete_character(self, character_id: int) -> None:
        """Удаляет персонажа вместе со всеми связями."""
        with self._conn:
            self._conn.execute("DELETE FROM characters WHERE id = ?;", (int(character_id),))

    def fetch_character_links(self, character_id: int) -> List[CharacterLinkData]:
        """Возвращает связи персонажа с сущностями приложения."""
        rows = self._conn.execute(
            """
            SELECT id, character_id, entity_kind, entity_id, created_at
            FROM character_links
            WHERE character_id = ?
            ORDER BY created_at DESC, id DESC;
            """,
            (int(character_id),),
        ).fetchall()
        return [
            CharacterLinkData(
                id=row["id"],
                character_id=row["character_id"],
                entity_kind=row["entity_kind"],
                entity_id=row["entity_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def add_character_link(self, character_id: int, entity_kind: str, entity_id: int) -> CharacterLinkData:
        """Добавляет связь персонажа с сущностью приложения."""
        normalized_kind = self._normalize_character_entity_kind(entity_kind)
        character_id = int(character_id)
        entity_id = int(entity_id)
        if character_id <= 0:
            raise ValueError("Некорректный идентификатор персонажа.")
        if entity_id <= 0:
            raise ValueError("Некорректный идентификатор сущности.")
        character_row = self._conn.execute(
            "SELECT 1 FROM characters WHERE id = ?;",
            (character_id,),
        ).fetchone()
        if character_row is None:
            raise ValueError("Персонаж не найден.")
        if not self._character_entity_exists(normalized_kind, entity_id):
            raise ValueError("Связываемая сущность не найдена.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO character_links (character_id, entity_kind, entity_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (character_id, normalized_kind, entity_id, now),
            )
        row = self._conn.execute(
            """
            SELECT id, character_id, entity_kind, entity_id, created_at
            FROM character_links
            WHERE character_id = ? AND entity_kind = ? AND entity_id = ?;
            """,
            (character_id, normalized_kind, entity_id),
        ).fetchone()
        if row is None:
            raise ValueError("Не удалось создать связь персонажа.")
        return CharacterLinkData(
            id=row["id"],
            character_id=row["character_id"],
            entity_kind=row["entity_kind"],
            entity_id=row["entity_id"],
            created_at=row["created_at"],
        )

    def delete_character_link(self, link_id: int) -> None:
        """Удаляет связь персонажа с сущностью."""
        with self._conn:
            self._conn.execute("DELETE FROM character_links WHERE id = ?;", (int(link_id),))

    def describe_character_link_target(self, entity_kind: str, entity_id: int) -> str:
        """Возвращает человекочитаемую подпись связанной сущности."""
        entity_id = int(entity_id)
        if entity_id <= 0:
            return "Некорректная ссылка"
        try:
            normalized_kind = self._normalize_character_entity_kind(entity_kind)
        except ValueError:
            return f"{entity_kind} #{entity_id}"

        if normalized_kind == "task":
            row = self._conn.execute(
                """
                SELECT tasks.title AS task_title, COALESCE(projects.title, '') AS project_title
                FROM tasks
                LEFT JOIN projects ON projects.id = tasks.project_id
                WHERE tasks.id = ?;
                """,
                (entity_id,),
            ).fetchone()
            if row:
                project_title = row["project_title"] or ""
                task_title = row["task_title"] or ""
                return f"Задача: {task_title} · {project_title}" if project_title else f"Задача: {task_title}"
        elif normalized_kind == "project":
            row = self._conn.execute(
                "SELECT title, area FROM projects WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                area = row["area"] or ""
                return f"Проект: {row['title']} · {area}" if area else f"Проект: {row['title']}"
        elif normalized_kind == "note":
            row = self._conn.execute(
                "SELECT title FROM notes WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Заметка: {row['title']}"
        elif normalized_kind == "idea":
            row = self._conn.execute(
                "SELECT title FROM ideas WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Идея: {row['title']}"
        elif normalized_kind == "object":
            row = self._conn.execute(
                "SELECT title FROM objects WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Объект: {row['title']}"
        elif normalized_kind == "map":
            row = self._conn.execute(
                "SELECT title FROM maps WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Карта: {row['title']}"
        elif normalized_kind == "marker":
            row = self._conn.execute(
                """
                SELECT map_markers.name, COALESCE(maps.title, '') AS map_title
                FROM map_markers
                LEFT JOIN maps ON maps.id = map_markers.map_id
                WHERE map_markers.id = ?;
                """,
                (entity_id,),
            ).fetchone()
            if row:
                map_title = row["map_title"] or ""
                return f"Метка: {row['name']} · {map_title}" if map_title else f"Метка: {row['name']}"
        elif normalized_kind == "file":
            row = self._conn.execute(
                "SELECT name FROM cloud_files WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Файл: {row['name']}"
        elif normalized_kind == "collection_item":
            row = self._conn.execute(
                "SELECT title FROM collection_items WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Коллекция: {row['title']}"
        elif normalized_kind == "collection_category":
            row = self._conn.execute(
                "SELECT title FROM collection_category WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Категория коллекций: {row['title']}"
        elif normalized_kind == "shop_category":
            row = self._conn.execute(
                "SELECT title FROM shop_category WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Категория покупок: {row['title']}"
        elif normalized_kind == "shop_item":
            row = self._conn.execute(
                "SELECT title FROM shop_item WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Покупка: {row['title']}"
        elif normalized_kind == "shop_source":
            row = self._conn.execute(
                "SELECT url FROM shop_source WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Источник цены: {row['url']}"
        elif normalized_kind == "wishlist":
            row = self._conn.execute(
                "SELECT title FROM wishlist WHERE id = ?;",
                (entity_id,),
            ).fetchone()
            if row:
                return f"Вишлист: {row['title']}"

        return f"{normalized_kind} #{entity_id}"

    def fetch_character_link_options(self, entity_kind: str, search_text: str = "") -> List[Tuple[int, str]]:
        """Возвращает список сущностей для выбора в привязках персонажей."""
        normalized_kind = self._normalize_character_entity_kind(entity_kind)
        needle = (search_text or "").strip().lower()

        def _matches(*chunks: str) -> bool:
            if not needle:
                return True
            haystack = " ".join(chunk for chunk in chunks if chunk).lower()
            return needle in haystack

        options: List[Tuple[int, str]] = []
        if normalized_kind == "task":
            for task in self.fetch_tasks():
                label = f"{task.title} · {task.project_title}" if task.project_title else task.title
                if _matches(task.title, task.project_title, task.description):
                    options.append((task.id, label))
        elif normalized_kind == "project":
            for project in self.fetch_projects():
                label = f"{project.title} · {project.area}" if project.area else project.title
                if _matches(project.title, project.area):
                    options.append((project.id, label))
        elif normalized_kind == "note":
            for note in self.fetch_notes():
                label = f"{note.title} · {note.project}" if note.project else note.title
                if _matches(note.title, note.project, note.preview):
                    options.append((note.id, label))
        elif normalized_kind == "idea":
            for idea in self.fetch_ideas(archived=True):
                label = f"{idea.title} · {idea.project_title}" if idea.project_title else idea.title
                if _matches(idea.title, idea.project_title, idea.summary, idea.body_md):
                    options.append((idea.id, label))
        elif normalized_kind == "object":
            for obj in self.fetch_objects():
                label = f"{obj.title} · {obj.catalog}" if obj.catalog else obj.title
                if _matches(obj.title, obj.catalog, obj.description):
                    options.append((obj.id, label))
        elif normalized_kind == "map":
            for map_item in self.fetch_maps():
                label = f"{map_item.title} · {map_item.project}" if map_item.project else map_item.title
                if _matches(map_item.title, map_item.project, map_item.description):
                    options.append((map_item.id, label))
        elif normalized_kind == "marker":
            map_titles = {item.id: item.title for item in self.fetch_maps()}
            for marker in self.fetch_map_markers():
                map_title = map_titles.get(marker.map_id, "")
                label = f"{marker.name} · {map_title}" if map_title else marker.name
                if _matches(marker.name, map_title, marker.description, marker.properties):
                    options.append((marker.id, label))
        elif normalized_kind == "file":
            for cloud_file in self.fetch_cloud_files():
                label = cloud_file.name
                if _matches(cloud_file.name, cloud_file.rel_path, cloud_file.description):
                    options.append((cloud_file.id, label))
        elif normalized_kind == "collection_item":
            for item in self.fetch_collection_items(search_text=needle):
                label = f"{item.title} · {item.topic}" if item.topic else item.title
                options.append((item.id, label))
        elif normalized_kind == "collection_category":
            for category in self.fetch_collection_categories():
                if _matches(category.title):
                    options.append((category.id, category.title))
        elif normalized_kind == "shop_category":
            for category in self.fetch_shop_categories():
                if _matches(category.title):
                    options.append((category.id, category.title))
        elif normalized_kind == "shop_item":
            for item in self.fetch_shop_items(search_text=needle):
                options.append((item.id, item.title))
        elif normalized_kind == "shop_source":
            rows = self._conn.execute(
                """
                SELECT id, url, sku
                FROM shop_source
                ORDER BY id DESC;
                """
            ).fetchall()
            for row in rows:
                url = row["url"] or ""
                sku = row["sku"] or ""
                label = f"{url} · {sku}" if sku else url
                if _matches(url, sku):
                    options.append((row["id"], label))
        elif normalized_kind == "wishlist":
            for wishlist in self.fetch_wishlists():
                if _matches(wishlist.title, wishlist.notes):
                    options.append((wishlist.id, wishlist.title))
        options.sort(key=lambda pair: (pair[1].lower(), pair[0]))
        return options

__all__ = ["DatabaseObjectsCharactersMixin"]
