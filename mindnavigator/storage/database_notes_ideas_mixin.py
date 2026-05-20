"""DatabaseNotesIdeasMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseNotesIdeasMixin:
    IDEA_RELATION_KINDS = {"related", "develops", "conflicts", "transforms_to", "source"}

    @staticmethod
    def _parse_idea_timestamp(value: Optional[str]) -> datetime:
        if value:
            parsed = datetime.fromisoformat(value)
        else:
            parsed = datetime.now(timezone.utc)
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def fetch_notes(self) -> List[NoteData]:
        """Возвращает список всех заметок."""
        rows = self._conn.execute(
            """
            SELECT
                id,
                title,
                preview,
                tags,
                project,
                favorite,
                attachment,
                locked,
                updated_at
            FROM notes
            ORDER BY updated_at DESC;
            """
        ).fetchall()
        notes = []
        for row in rows:
            tags = json.loads(row["tags"] or "[]")
            notes.append(
                NoteData(
                    id=row["id"],
                    title=row["title"],
                    preview=row["preview"] or "",
                    tags=tags if isinstance(tags, list) else [],
                    updated=datetime.fromisoformat(row["updated_at"]),
                    project=row["project"] or "",
                    favorite=bool(row["favorite"]),
                    attachment=bool(row["attachment"]),
                    locked=bool(row["locked"]),
                )
            )
        return notes

    def create_note(
        self,
        title: str,
        preview: str,
        tags: List[str],
        project: str,
        favorite: bool = False,
        attachment: bool = False,
        locked: bool = False,
    ) -> NoteData:
        """Создает заметку в базе данных."""
        title = validate_title(title, field_name="Название заметки")
        preview = (preview or "").strip()
        project = (project or "").strip()
        tags = [tag.strip() for tag in tags if tag.strip()]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO notes (title, preview, tags, project, favorite, attachment, locked, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    title,
                    preview,
                    json.dumps(tags),
                    project,
                    int(bool(favorite)),
                    int(bool(attachment)),
                    int(bool(locked)),
                    now,
                    now,
                ),
            )
        return NoteData(
            id=cur.lastrowid,
            title=title,
            preview=preview,
            tags=tags,
            updated=datetime.fromisoformat(now),
            project=project,
            favorite=bool(favorite),
            attachment=bool(attachment),
            locked=bool(locked),
        )

    def update_note(
        self,
        note_id: int,
        title: str,
        preview: str,
        tags: List[str],
    ) -> NoteData:
        """Обновляет данные заметки."""
        title = validate_title(title, field_name="Название заметки")
        preview = (preview or "").strip()
        tags = [tag.strip() for tag in tags if tag.strip()]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE notes
                SET title = ?, preview = ?, tags = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, preview, json.dumps(tags), now, note_id),
            )
        row = self._conn.execute(
            """
            SELECT id, project, favorite, attachment, locked
            FROM notes
            WHERE id = ?;
            """,
            (note_id,),
        ).fetchone()
        return NoteData(
            id=note_id,
            title=title,
            preview=preview,
            tags=tags,
            updated=datetime.fromisoformat(now),
            project=row["project"] if row else "",
            favorite=bool(row["favorite"]) if row else False,
            attachment=bool(row["attachment"]) if row else False,
            locked=bool(row["locked"]) if row else False,
        )

    def _fetch_project_title(self, project_id: Optional[int]) -> str:
        if project_id is None:
            return ""
        row = self._conn.execute(
            "SELECT title FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
        return row["title"] if row else ""

    @staticmethod
    def _normalize_idea_status_code(status: Optional[str]) -> str:
        return (status or "inbox").strip() or "inbox"

    @classmethod
    def _normalize_idea_relation_kind(cls, relation_kind: Optional[str]) -> str:
        normalized = (relation_kind or "related").strip().lower() or "related"
        return normalized if normalized in cls.IDEA_RELATION_KINDS else "related"

    @staticmethod
    def _default_idea_category_title(code: str) -> str:
        cleaned = " ".join(str(code or "").replace("_", " ").replace("-", " ").split())
        if not cleaned:
            return "Без категории"
        return cleaned[:1].upper() + cleaned[1:]

    def _ensure_idea_category_exists(
        self,
        code: str,
        *,
        title: Optional[str] = None,
        is_system: bool = False,
    ) -> None:
        normalized_code = self._normalize_idea_status_code(code)
        row = self._conn.execute(
            "SELECT code FROM idea_categories WHERE code = ?;",
            (normalized_code,),
        ).fetchone()
        if row is not None:
            return
        max_row = self._conn.execute("SELECT COALESCE(MAX(sort_index), 0) AS max_sort FROM idea_categories;").fetchone()
        sort_index = int(max_row["max_sort"] or 0) + 10
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._conn.execute(
            """
            INSERT INTO idea_categories (code, title, is_system, sort_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                normalized_code,
                (title or self._default_idea_category_title(normalized_code)).strip() or self._default_idea_category_title(normalized_code),
                int(bool(is_system)),
                sort_index,
                now,
                now,
            ),
        )

    def list_idea_categories(self) -> List[IdeaCategoryData]:
        rows = self._conn.execute(
            """
            SELECT code, title, is_system, sort_index, created_at, updated_at
            FROM idea_categories
            ORDER BY sort_index, title COLLATE NOCASE, code;
            """
        ).fetchall()
        return [
            IdeaCategoryData(
                code=row["code"],
                title=row["title"],
                is_system=bool(row["is_system"]),
                sort_index=int(row["sort_index"] or 0),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def get_idea_category(self, code: str) -> Optional[IdeaCategoryData]:
        normalized_code = self._normalize_idea_status_code(code)
        row = self._conn.execute(
            """
            SELECT code, title, is_system, sort_index, created_at, updated_at
            FROM idea_categories
            WHERE code = ?;
            """,
            (normalized_code,),
        ).fetchone()
        if row is None:
            return None
        return IdeaCategoryData(
            code=row["code"],
            title=row["title"],
            is_system=bool(row["is_system"]),
            sort_index=int(row["sort_index"] or 0),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_idea_category(self, title: str) -> IdeaCategoryData:
        normalized_title = " ".join((title or "").split())
        if not normalized_title:
            raise ValueError("Название категории не может быть пустым.")
        existing = self._conn.execute(
            "SELECT code FROM idea_categories WHERE lower(title) = lower(?);",
            (normalized_title,),
        ).fetchone()
        if existing is not None:
            raise ValueError("Категория с таким названием уже существует.")
        code = f"custom_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        max_row = self._conn.execute("SELECT COALESCE(MAX(sort_index), 0) AS max_sort FROM idea_categories;").fetchone()
        sort_index = int(max_row["max_sort"] or 0) + 10
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO idea_categories (code, title, is_system, sort_index, created_at, updated_at)
                VALUES (?, ?, 0, ?, ?, ?);
                """,
                (code, normalized_title, sort_index, now, now),
            )
        category = self.get_idea_category(code)
        if category is None:
            raise ValueError("Не удалось создать категорию идеи.")
        return category

    def update_idea_category_title(self, code: str, title: str) -> IdeaCategoryData:
        normalized_code = self._normalize_idea_status_code(code)
        normalized_title = " ".join((title or "").split())
        if not normalized_title:
            raise ValueError("Название категории не может быть пустым.")
        row = self._conn.execute(
            "SELECT code FROM idea_categories WHERE code = ?;",
            (normalized_code,),
        ).fetchone()
        if row is None:
            raise ValueError("Категория идеи не найдена.")
        duplicate = self._conn.execute(
            "SELECT code FROM idea_categories WHERE lower(title) = lower(?) AND code <> ?;",
            (normalized_title, normalized_code),
        ).fetchone()
        if duplicate is not None:
            raise ValueError("Категория с таким названием уже существует.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE idea_categories
                SET title = ?, updated_at = ?
                WHERE code = ?;
                """,
                (normalized_title, now, normalized_code),
            )
        category = self.get_idea_category(normalized_code)
        if category is None:
            raise ValueError("Категория идеи не найдена.")
        return category

    def delete_idea_category(self, code: str, move_ideas_to: str = "inbox") -> None:
        normalized_code = self._normalize_idea_status_code(code)
        target_code = self._normalize_idea_status_code(move_ideas_to)
        category = self.get_idea_category(normalized_code)
        if category is None:
            raise ValueError("Категория идеи не найдена.")
        if category.is_system:
            raise ValueError("Системную категорию идеи нельзя удалить.")
        self._ensure_idea_category_exists(target_code, is_system=(target_code in {"inbox", "work", "ripe", "done", "archived"}))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                "UPDATE ideas SET status = ?, updated_at = ? WHERE status = ?;",
                (target_code, now, normalized_code),
            )
            self._conn.execute("DELETE FROM idea_categories WHERE code = ?;", (normalized_code,))

    def fetch_ideas(
        self,
        project_id: Optional[int] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        idea_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        archived: bool = False,
    ) -> List[IdeaData]:
        """Возвращает список идей с учетом фильтров."""
        conditions = []
        params: list[object] = []
        if project_id is not None:
            conditions.append("ideas.project_id = ?")
            params.append(project_id)
        if search:
            like = f"%{search.strip().lower()}%"
            conditions.append(
                "("
                "lower(COALESCE(ideas.title, '')) LIKE ? "
                "OR lower(COALESCE(ideas.summary, '')) LIKE ? "
                "OR lower(COALESCE(ideas.body_md, '')) LIKE ? "
                "OR lower(COALESCE(ideas.source, '')) LIKE ?"
                ")"
            )
            params.extend([like, like, like, like])
        if status:
            conditions.append("ideas.status = ?")
            params.append(status)
        if idea_type:
            conditions.append("ideas.type = ?")
            params.append(idea_type)
        if archived:
            conditions.append("ideas.archived_at IS NOT NULL")
        else:
            conditions.append("ideas.archived_at IS NULL")
        if tags:
            tag_list = [tag.strip() for tag in tags if tag.strip()]
            if tag_list:
                placeholders = ",".join("?" for _ in tag_list)
                conditions.append(
                    "EXISTS (SELECT 1 FROM idea_tags WHERE idea_tags.idea_id = ideas.id "
                    f"AND idea_tags.tag_text IN ({placeholders}))"
                )
                params.extend(tag_list)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        rows = self._conn.execute(
            f"""
            SELECT
                ideas.id,
                ideas.project_id,
                ideas.title,
                ideas.summary,
                ideas.body_md,
                ideas.type,
                ideas.status,
                ideas.value_score,
                ideas.effort_score,
                ideas.source,
                ideas.created_at,
                ideas.updated_at,
                ideas.archived_at,
                projects.title AS project_title
            FROM ideas
            LEFT JOIN projects ON projects.id = ideas.project_id
            {where}
            ORDER BY ideas.updated_at DESC;
            """,
            params,
        ).fetchall()
        ideas: List[IdeaData] = []
        for row in rows:
            ideas.append(
                IdeaData(
                    id=row["id"],
                    project_id=row["project_id"],
                    title=row["title"] or "",
                    summary=row["summary"] or "",
                    body_md=row["body_md"] or "",
                    type=row["type"],
                    status=row["status"],
                    value_score=row["value_score"],
                    effort_score=row["effort_score"],
                    source=row["source"] or "",
                    created_at=self._parse_idea_timestamp(row["created_at"]),
                    updated_at=self._parse_idea_timestamp(row["updated_at"]),
                    archived_at=self._parse_idea_timestamp(row["archived_at"])
                    if row["archived_at"]
                    else None,
                    project_title=row["project_title"] or "",
                )
            )
        return ideas

    def get_idea(self, idea_id: int) -> Optional[IdeaData]:
        """Возвращает идею по ID."""
        row = self._conn.execute(
            """
            SELECT
                ideas.id,
                ideas.project_id,
                ideas.title,
                ideas.summary,
                ideas.body_md,
                ideas.type,
                ideas.status,
                ideas.value_score,
                ideas.effort_score,
                ideas.source,
                ideas.created_at,
                ideas.updated_at,
                ideas.archived_at,
                projects.title AS project_title
            FROM ideas
            LEFT JOIN projects ON projects.id = ideas.project_id
            WHERE ideas.id = ?;
            """,
            (idea_id,),
        ).fetchone()
        if row is None:
            return None
        return IdeaData(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"] or "",
            summary=row["summary"] or "",
            body_md=row["body_md"] or "",
            type=row["type"],
            status=row["status"],
            value_score=row["value_score"],
            effort_score=row["effort_score"],
            source=row["source"] or "",
            created_at=self._parse_idea_timestamp(row["created_at"]),
            updated_at=self._parse_idea_timestamp(row["updated_at"]),
            archived_at=self._parse_idea_timestamp(row["archived_at"]) if row["archived_at"] else None,
            project_title=row["project_title"] or "",
        )

    def create_idea(
        self,
        title: str,
        summary: str = "",
        body_md: str = "",
        idea_type: str = "other",
        status: str = "inbox",
        value_score: int = 3,
        effort_score: int = 3,
        project_id: Optional[int] = None,
        source: str = "",
    ) -> IdeaData:
        """Создает идею в базе данных."""
        title = (title or "").strip() or "Без названия"
        summary = (summary or "").strip()
        body_md = (body_md or "").strip()
        idea_type = (idea_type or "other").strip() or "other"
        status = self._normalize_idea_status_code(status)
        value_score = int(value_score or 3)
        effort_score = int(effort_score or 3)
        source = (source or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._ensure_idea_category_exists(status)
            cur = self._conn.execute(
                """
                INSERT INTO ideas (
                    project_id, title, summary, body_md, type, status,
                    value_score, effort_score, source, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    title,
                    summary,
                    body_md,
                    idea_type,
                    status,
                    value_score,
                    effort_score,
                    source,
                    now,
                    now,
                ),
            )
        return IdeaData(
            id=cur.lastrowid,
            project_id=project_id,
            title=title,
            summary=summary,
            body_md=body_md,
            type=idea_type,
            status=status,
            value_score=value_score,
            effort_score=effort_score,
            source=source,
            created_at=self._parse_idea_timestamp(now),
            updated_at=self._parse_idea_timestamp(now),
            archived_at=None,
            project_title=self._fetch_project_title(project_id),
        )

    def update_idea(
        self,
        idea_id: int,
        title: str,
        summary: str,
        body_md: str,
        idea_type: str,
        status: str,
        value_score: int,
        effort_score: int,
        project_id: Optional[int] = None,
        source: str = "",
    ) -> IdeaData:
        """Обновляет идею."""
        title = (title or "").strip() or "Без названия"
        summary = (summary or "").strip()
        body_md = (body_md or "").strip()
        idea_type = (idea_type or "other").strip() or "other"
        status = self._normalize_idea_status_code(status)
        value_score = int(value_score or 3)
        effort_score = int(effort_score or 3)
        source = (source or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._ensure_idea_category_exists(status)
            self._conn.execute(
                """
                UPDATE ideas
                SET project_id = ?, title = ?, summary = ?, body_md = ?, type = ?, status = ?,
                    value_score = ?, effort_score = ?, source = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    project_id,
                    title,
                    summary,
                    body_md,
                    idea_type,
                    status,
                    value_score,
                    effort_score,
                    source,
                    now,
                    idea_id,
                ),
            )
        meta_row = self._conn.execute(
            "SELECT created_at, archived_at FROM ideas WHERE id = ?;",
            (idea_id,),
        ).fetchone()
        created_at = (
            self._parse_idea_timestamp(meta_row["created_at"])
            if meta_row and meta_row["created_at"]
            else self._parse_idea_timestamp(now)
        )
        archived_at = (
            self._parse_idea_timestamp(meta_row["archived_at"])
            if meta_row and meta_row["archived_at"]
            else None
        )
        return IdeaData(
            id=idea_id,
            project_id=project_id,
            title=title,
            summary=summary,
            body_md=body_md,
            type=idea_type,
            status=status,
            value_score=value_score,
            effort_score=effort_score,
            source=source,
            created_at=created_at,
            updated_at=self._parse_idea_timestamp(now),
            archived_at=archived_at,
            project_title=self._fetch_project_title(project_id),
        )

    def set_idea_archived(self, idea_id: int, archived: bool) -> None:
        """Архивирует или восстанавливает идею."""
        archived_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if archived else None
        with self._conn:
            self._conn.execute(
                "UPDATE ideas SET archived_at = ?, updated_at = ? WHERE id = ?;",
                (archived_at, datetime.now(timezone.utc).isoformat(timespec="seconds"), idea_id),
            )

    def delete_idea(self, idea_id: int) -> None:
        """Удаляет идею."""
        with self._conn:
            self._conn.execute("DELETE FROM ideas WHERE id = ?;", (idea_id,))

    def fetch_idea_relations(self, idea_id: int) -> List[IdeaRelationData]:
        """Возвращает список связей идеи."""
        rows = self._conn.execute(
            """
            SELECT id, idea_id, entity_type, entity_id, relation_kind, created_at
            FROM idea_relations
            WHERE idea_id = ?
            ORDER BY created_at DESC;
            """,
            (idea_id,),
        ).fetchall()
        return [
            IdeaRelationData(
                id=row["id"],
                idea_id=row["idea_id"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                relation_kind=self._normalize_idea_relation_kind(row["relation_kind"]),
            )
            for row in rows
        ]

    def fetch_idea_images(self, idea_id: int) -> List[IdeaImageData]:
        """Returns idea images with idea-specific captions."""
        rows = self._conn.execute(
            """
            SELECT id, idea_id, rel_path, caption, created_at, updated_at
            FROM idea_images
            WHERE idea_id = ?
            ORDER BY created_at ASC, id ASC;
            """,
            (idea_id,),
        ).fetchall()
        return [
            IdeaImageData(
                row["id"],
                row["idea_id"],
                row["rel_path"],
                row["caption"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def add_idea_image(self, idea_id: int, rel_path: str, caption: str = "") -> IdeaImageData:
        """Attaches an image from cloud files to an idea."""
        rel_path = (rel_path or "").strip()
        if not rel_path:
            raise ValueError("Путь к изображению не должен быть пустым.")
        caption = (caption or "").strip()
        file_row = self._conn.execute(
            """
            SELECT is_image
            FROM cloud_files
            WHERE rel_path = ?;
            """,
            (rel_path,),
        ).fetchone()
        if file_row is None:
            raise ValueError("Файл не найден в базе облака.")
        if not bool(file_row["is_image"]):
            raise ValueError("Можно прикреплять только изображения.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO idea_images (idea_id, rel_path, caption, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (idea_id, rel_path, caption, now, now),
            )
        row = self._conn.execute(
            """
            SELECT id, idea_id, rel_path, caption, created_at, updated_at
            FROM idea_images
            WHERE idea_id = ? AND rel_path = ?;
            """,
            (idea_id, rel_path),
        ).fetchone()
        return IdeaImageData(
            row["id"],
            row["idea_id"],
            row["rel_path"],
            row["caption"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def update_idea_image(self, image_id: int, caption: str) -> IdeaImageData:
        """Updates an idea image caption."""
        caption = (caption or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE idea_images
                SET caption = ?, updated_at = ?
                WHERE id = ?;
                """,
                (caption, now, image_id),
            )
        row = self._conn.execute(
            """
            SELECT id, idea_id, rel_path, caption, created_at, updated_at
            FROM idea_images
            WHERE id = ?;
            """,
            (image_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Изображение идеи не найдено.")
        return IdeaImageData(
            row["id"],
            row["idea_id"],
            row["rel_path"],
            row["caption"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def delete_idea_image(self, image_id: int) -> None:
        """Deletes an image attachment from an idea."""
        with self._conn:
            self._conn.execute("DELETE FROM idea_images WHERE id = ?;", (image_id,))

    def add_idea_relation(
        self,
        idea_id: int,
        entity_type: str,
        entity_id: int,
        relation_kind: Optional[str] = None,
    ) -> None:
        """Создает связь идеи с сущностью."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        normalized_kind = self._normalize_idea_relation_kind(relation_kind)
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO idea_relations (idea_id, entity_type, entity_id, relation_kind, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (idea_id, entity_type, entity_id, normalized_kind, now),
            )

    def delete_idea_relation(self, relation_id: int) -> None:
        """Deletes an idea relation."""
        with self._conn:
            self._conn.execute("DELETE FROM idea_relations WHERE id = ?;", (relation_id,))

    def toggle_note_favorite(self, note_id: int) -> NoteData:
        """Переключает избранное у заметки."""
        row = self._conn.execute(
            """
            SELECT title, preview, tags, project, favorite, attachment, locked
            FROM notes
            WHERE id = ?;
            """,
            (note_id,),
        ).fetchone()
        if not row:
            raise ValueError("Заметка не найдена.")
        favorite = not bool(row["favorite"])
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE notes
                SET favorite = ?, updated_at = ?
                WHERE id = ?;
                """,
                (int(favorite), now, note_id),
            )
        tags = json.loads(row["tags"] or "[]")
        return NoteData(
            id=note_id,
            title=row["title"],
            preview=row["preview"] or "",
            tags=tags if isinstance(tags, list) else [],
            updated=datetime.fromisoformat(now),
            project=row["project"] or "",
            favorite=favorite,
            attachment=bool(row["attachment"]),
            locked=bool(row["locked"]),
        )

    def set_note_favorite(self, note_id: int, favorite: bool) -> NoteData:
        """Устанавливает статус избранного у заметки."""
        row = self._conn.execute(
            """
            SELECT title, preview, tags, project, attachment, locked
            FROM notes
            WHERE id = ?;
            """,
            (note_id,),
        ).fetchone()
        if not row:
            raise ValueError("Заметка не найдена.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE notes
                SET favorite = ?, updated_at = ?
                WHERE id = ?;
                """,
                (int(bool(favorite)), now, note_id),
            )
        tags = json.loads(row["tags"] or "[]")
        return NoteData(
            id=note_id,
            title=row["title"],
            preview=row["preview"] or "",
            tags=tags if isinstance(tags, list) else [],
            updated=datetime.fromisoformat(now),
            project=row["project"] or "",
            favorite=bool(favorite),
            attachment=bool(row["attachment"]),
            locked=bool(row["locked"]),
        )

    def set_note_locked(self, note_id: int, locked: bool) -> NoteData:
        """Устанавливает статус блокировки заметки."""
        row = self._conn.execute(
            """
            SELECT title, preview, tags, project, favorite, attachment
            FROM notes
            WHERE id = ?;
            """,
            (note_id,),
        ).fetchone()
        if not row:
            raise ValueError("Заметка не найдена.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE notes
                SET locked = ?, updated_at = ?
                WHERE id = ?;
                """,
                (int(bool(locked)), now, note_id),
            )
        tags = json.loads(row["tags"] or "[]")
        return NoteData(
            id=note_id,
            title=row["title"],
            preview=row["preview"] or "",
            tags=tags if isinstance(tags, list) else [],
            updated=datetime.fromisoformat(now),
            project=row["project"] or "",
            favorite=bool(row["favorite"]),
            attachment=bool(row["attachment"]),
            locked=bool(locked),
        )

    def delete_note(self, note_id: int) -> None:
        """Удаляет заметку."""
        with self._conn:
            self._conn.execute("DELETE FROM notes WHERE id = ?;", (note_id,))

__all__ = ["DatabaseNotesIdeasMixin"]
