"""DatabaseDossierMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403


class DatabaseDossierMixin:
    def _dossier_entity_exists(self, entity_kind: str, entity_id: int) -> bool:
        target_map = {
            "task": "tasks",
            "map": "maps",
            "marker": "map_markers",
            "note": "notes",
            "idea": "ideas",
            "object": "objects",
            "character": "characters",
        }
        table_name = target_map.get(entity_kind)
        if table_name is None:
            return False
        row = self._conn.execute(
            f"SELECT 1 FROM {table_name} WHERE id = ?;",
            (int(entity_id),),
        ).fetchone()
        return row is not None

    @staticmethod
    def _normalize_dossier_tags(tags: Optional[Iterable[str]]) -> List[str]:
        if tags is None:
            return []
        normalized: List[str] = []
        for raw_tag in tags:
            tag = str(raw_tag or "").strip()
            if tag and tag not in normalized:
                normalized.append(tag)
        return normalized

    def fetch_dossiers(
        self,
        kind: Optional[str] = None,
        status: Optional[str] = None,
        search_text: str = "",
        tag: Optional[str] = None,
        linked_entity_kind: Optional[str] = None,
        linked_entity_id: Optional[int] = None,
    ) -> List[DossierData]:
        """Return dossiers with optional filters."""
        clauses: list[str] = []
        params: list[object] = []

        if kind is not None:
            clauses.append("dossiers.kind = ?")
            params.append(DossierData.normalize_kind(kind))
        if status is not None:
            clauses.append("dossiers.status = ?")
            params.append(DossierData.normalize_status(status))

        query = (search_text or "").strip().lower()
        if query:
            like = f"%{query}%"
            clauses.append(
                "("
                "lower(dossiers.title) LIKE ? OR "
                "lower(dossiers.summary) LIKE ? OR "
                "lower(dossiers.description) LIKE ? OR "
                "lower(dossiers.source) LIKE ? OR "
                "lower(dossiers.tags) LIKE ? OR "
                "lower(dossiers.metadata_json) LIKE ?"
                ")"
            )
            params.extend([like, like, like, like, like, like])

        normalized_tag = str(tag or "").strip().lower()
        if normalized_tag:
            clauses.append("lower(dossiers.tags) LIKE ?")
            params.append(f'%"{normalized_tag}"%')

        if linked_entity_kind is not None or linked_entity_id is not None:
            if linked_entity_kind is None or linked_entity_id is None:
                return []
            normalized_kind = DossierLinkData.normalize_entity_kind(linked_entity_kind)
            normalized_id = int(linked_entity_id)
            if normalized_id <= 0:
                return []
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM dossier_links
                    WHERE dossier_links.dossier_id = dossiers.id
                    AND dossier_links.entity_kind = ?
                    AND dossier_links.entity_id = ?
                )
                """
            )
            params.extend([normalized_kind, normalized_id])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT
                id,
                kind,
                title,
                summary,
                description,
                tags,
                status,
                rating,
                source,
                cover_image,
                metadata_json,
                created_at,
                updated_at
            FROM dossiers
            {where_sql}
            ORDER BY updated_at DESC, id DESC;
            """,
            tuple(params),
        ).fetchall()
        return [DossierData.from_row(row) for row in rows]

    def get_dossier(self, dossier_id: int) -> Optional[DossierData]:
        """Return a single dossier by id."""
        row = self._conn.execute(
            """
            SELECT
                id,
                kind,
                title,
                summary,
                description,
                tags,
                status,
                rating,
                source,
                cover_image,
                metadata_json,
                created_at,
                updated_at
            FROM dossiers
            WHERE id = ?;
            """,
            (int(dossier_id),),
        ).fetchone()
        return DossierData.from_row(row) if row is not None else None

    def create_dossier(
        self,
        kind: str,
        title: str,
        summary: str = "",
        description: str = "",
        tags: Optional[Iterable[str]] = None,
        status: str = "planned",
        rating: Optional[int] = None,
        source: str = "",
        cover_image: str = "",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> DossierData:
        """Create a dossier item."""
        normalized_kind = DossierData.normalize_kind(kind)
        normalized_title = validate_title(title, field_name="Dossier title")
        normalized_summary = str(summary or "").strip()
        normalized_description = str(description or "").strip()
        normalized_tags = self._normalize_dossier_tags(tags)
        normalized_status = DossierData.normalize_status(status)
        normalized_rating = DossierData.normalize_rating(rating)
        normalized_source = str(source or "").strip()
        normalized_cover_image = str(cover_image or "").strip()
        normalized_metadata = DossierData.normalize_metadata(normalized_kind, metadata)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO dossiers (
                    kind, title, summary, description, tags, status, rating,
                    source, cover_image, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    normalized_kind,
                    normalized_title,
                    normalized_summary,
                    normalized_description,
                    json.dumps(normalized_tags, ensure_ascii=False),
                    normalized_status,
                    normalized_rating,
                    normalized_source,
                    normalized_cover_image,
                    json.dumps(normalized_metadata, ensure_ascii=False, sort_keys=True),
                    now,
                    now,
                ),
            )
        return DossierData(
            id=int(cursor.lastrowid),
            kind=normalized_kind,
            title=normalized_title,
            summary=normalized_summary,
            description=normalized_description,
            tags=normalized_tags,
            status=normalized_status,
            rating=normalized_rating,
            source=normalized_source,
            cover_image=normalized_cover_image,
            metadata=normalized_metadata,
            created_at=now,
            updated_at=now,
        )

    def update_dossier(
        self,
        dossier_id: int,
        kind: str,
        title: str,
        summary: str = "",
        description: str = "",
        tags: Optional[Iterable[str]] = None,
        status: str = "planned",
        rating: Optional[int] = None,
        source: str = "",
        cover_image: str = "",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> DossierData:
        """Update a dossier item."""
        normalized_kind = DossierData.normalize_kind(kind)
        normalized_title = validate_title(title, field_name="Dossier title")
        normalized_summary = str(summary or "").strip()
        normalized_description = str(description or "").strip()
        normalized_tags = self._normalize_dossier_tags(tags)
        normalized_status = DossierData.normalize_status(status)
        normalized_rating = DossierData.normalize_rating(rating)
        normalized_source = str(source or "").strip()
        normalized_cover_image = str(cover_image or "").strip()
        normalized_metadata = DossierData.normalize_metadata(normalized_kind, metadata)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE dossiers
                SET kind = ?, title = ?, summary = ?, description = ?, tags = ?, status = ?, rating = ?,
                    source = ?, cover_image = ?, metadata_json = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    normalized_kind,
                    normalized_title,
                    normalized_summary,
                    normalized_description,
                    json.dumps(normalized_tags, ensure_ascii=False),
                    normalized_status,
                    normalized_rating,
                    normalized_source,
                    normalized_cover_image,
                    json.dumps(normalized_metadata, ensure_ascii=False, sort_keys=True),
                    now,
                    int(dossier_id),
                ),
            )
        row = self._conn.execute(
            "SELECT created_at FROM dossiers WHERE id = ?;",
            (int(dossier_id),),
        ).fetchone()
        if row is None:
            raise ValueError("Dossier not found.")
        return DossierData(
            id=int(dossier_id),
            kind=normalized_kind,
            title=normalized_title,
            summary=normalized_summary,
            description=normalized_description,
            tags=normalized_tags,
            status=normalized_status,
            rating=normalized_rating,
            source=normalized_source,
            cover_image=normalized_cover_image,
            metadata=normalized_metadata,
            created_at=str(row["created_at"] or ""),
            updated_at=now,
        )

    def delete_dossier(self, dossier_id: int) -> None:
        """Delete a dossier item."""
        with self._conn:
            self._conn.execute("DELETE FROM dossiers WHERE id = ?;", (int(dossier_id),))

    def fetch_dossier_links(self, dossier_id: int) -> List[DossierLinkData]:
        """Return links from a dossier to application entities."""
        rows = self._conn.execute(
            """
            SELECT id, dossier_id, entity_kind, entity_id, created_at
            FROM dossier_links
            WHERE dossier_id = ?
            ORDER BY created_at DESC, id DESC;
            """,
            (int(dossier_id),),
        ).fetchall()
        return [DossierLinkData.from_row(row) for row in rows]

    def add_dossier_link(self, dossier_id: int, entity_kind: str, entity_id: int) -> DossierLinkData:
        """Create a dossier link to an application entity."""
        normalized_kind = DossierLinkData.normalize_entity_kind(entity_kind)
        normalized_dossier_id = int(dossier_id)
        normalized_entity_id = int(entity_id)
        if normalized_dossier_id <= 0:
            raise ValueError("Invalid dossier id.")
        if normalized_entity_id <= 0:
            raise ValueError("Invalid linked entity id.")
        dossier_row = self._conn.execute(
            "SELECT 1 FROM dossiers WHERE id = ?;",
            (normalized_dossier_id,),
        ).fetchone()
        if dossier_row is None:
            raise ValueError("Dossier not found.")
        if not self._dossier_entity_exists(normalized_kind, normalized_entity_id):
            raise ValueError("Linked entity not found.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO dossier_links (dossier_id, entity_kind, entity_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (normalized_dossier_id, normalized_kind, normalized_entity_id, now),
            )
        row = self._conn.execute(
            """
            SELECT id, dossier_id, entity_kind, entity_id, created_at
            FROM dossier_links
            WHERE dossier_id = ? AND entity_kind = ? AND entity_id = ?;
            """,
            (normalized_dossier_id, normalized_kind, normalized_entity_id),
        ).fetchone()
        if row is None:
            raise ValueError("Failed to create dossier link.")
        return DossierLinkData.from_row(row)

    def delete_dossier_link(self, link_id: int) -> None:
        """Delete a dossier link."""
        with self._conn:
            self._conn.execute("DELETE FROM dossier_links WHERE id = ?;", (int(link_id),))

    def describe_dossier_link_target(self, entity_kind: str, entity_id: int) -> str:
        """Return a human-readable label for a dossier link target."""
        normalized_id = int(entity_id)
        if normalized_id <= 0:
            return "Invalid link"
        try:
            normalized_kind = DossierLinkData.normalize_entity_kind(entity_kind)
        except ValueError:
            return f"{entity_kind} #{normalized_id}"

        if normalized_kind == "task":
            row = self._conn.execute(
                """
                SELECT tasks.title AS task_title, COALESCE(projects.title, '') AS project_title
                FROM tasks
                LEFT JOIN projects ON projects.id = tasks.project_id
                WHERE tasks.id = ?;
                """,
                (normalized_id,),
            ).fetchone()
            if row:
                project_title = row["project_title"] or ""
                return (
                    f"Task: {row['task_title']} · {project_title}"
                    if project_title
                    else f"Task: {row['task_title']}"
                )
        elif normalized_kind == "map":
            row = self._conn.execute(
                "SELECT title FROM maps WHERE id = ?;",
                (normalized_id,),
            ).fetchone()
            if row:
                return f"Map: {row['title']}"
        elif normalized_kind == "marker":
            row = self._conn.execute(
                """
                SELECT map_markers.name, COALESCE(maps.title, '') AS map_title
                FROM map_markers
                LEFT JOIN maps ON maps.id = map_markers.map_id
                WHERE map_markers.id = ?;
                """,
                (normalized_id,),
            ).fetchone()
            if row:
                map_title = row["map_title"] or ""
                return f"Marker: {row['name']} · {map_title}" if map_title else f"Marker: {row['name']}"
        elif normalized_kind == "note":
            row = self._conn.execute(
                "SELECT title FROM notes WHERE id = ?;",
                (normalized_id,),
            ).fetchone()
            if row:
                return f"Note: {row['title']}"
        elif normalized_kind == "idea":
            row = self._conn.execute(
                "SELECT title FROM ideas WHERE id = ?;",
                (normalized_id,),
            ).fetchone()
            if row:
                return f"Idea: {row['title']}"
        elif normalized_kind == "object":
            row = self._conn.execute(
                "SELECT title FROM objects WHERE id = ?;",
                (normalized_id,),
            ).fetchone()
            if row:
                return f"Object: {row['title']}"
        elif normalized_kind == "character":
            row = self._conn.execute(
                "SELECT name FROM characters WHERE id = ?;",
                (normalized_id,),
            ).fetchone()
            if row:
                return f"Character: {row['name']}"

        return f"{normalized_kind} #{normalized_id}"


__all__ = ["DatabaseDossierMixin"]
