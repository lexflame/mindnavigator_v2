"""DatabaseMutaBoardsMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

_DEFAULT_MUTABOARD_COLUMN_KINDS = ("task", "idea", "image")
_MUTABOARD_COLUMN_KINDS = (
    "task",
    "idea",
    "image",
    "map",
    "marker",
    "note",
    "project",
    "object",
    "version",
    "solution",
    "file",
    "link",
)
_MUTABOARD_ENTITY_KINDS = _MUTABOARD_COLUMN_KINDS


class DatabaseMutaBoardsMixin:
    def fetch_mutaboards(self) -> List[MutaBoardData]:
        rows = self._conn.execute(
            """
            SELECT id, title, description, capture_text, planning_text, links_text, created_at, updated_at
            FROM mutaboards
            ORDER BY updated_at DESC, id DESC;
            """
        ).fetchall()
        return [self._mutaboard_from_row(row) for row in rows]

    def create_mutaboard(
        self,
        title: str,
        description: str = "",
        capture_text: str = "",
        planning_text: str = "",
        links_text: str = "",
        column_kinds: Iterable[str] | None = None,
    ) -> MutaBoardData:
        title = validate_title(title, field_name="Название мутборда")
        description = (description or "").strip()
        capture_text = (capture_text or "").strip()
        planning_text = (planning_text or "").strip()
        links_text = (links_text or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        normalized_kinds = self._normalize_mutaboard_column_kinds(column_kinds)
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO mutaboards (
                    title,
                    description,
                    capture_text,
                    planning_text,
                    links_text,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (title, description, capture_text, planning_text, links_text, now, now),
            )
        mutaboard_id = int(cur.lastrowid)
        self.replace_mutaboard_columns(mutaboard_id, [(kind, "") for kind in normalized_kinds])
        created = self._fetch_mutaboard_by_id(mutaboard_id)
        assert created is not None
        return created

    def update_mutaboard(
        self,
        mutaboard_id: int,
        *,
        title: str,
        description: str,
        capture_text: str,
        planning_text: str,
        links_text: str,
    ) -> MutaBoardData:
        title = validate_title(title, field_name="Название мутборда")
        description = (description or "").strip()
        capture_text = (capture_text or "").strip()
        planning_text = (planning_text or "").strip()
        links_text = (links_text or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE mutaboards
                SET title = ?, description = ?, capture_text = ?, planning_text = ?, links_text = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, description, capture_text, planning_text, links_text, now, mutaboard_id),
            )
        updated = self._fetch_mutaboard_by_id(mutaboard_id)
        assert updated is not None
        return updated

    def fetch_mutaboard_columns(self, mutaboard_id: int) -> List[MutaBoardColumnData]:
        rows = self._conn.execute(
            """
            SELECT id, mutaboard_id, kind, title, position, created_at, updated_at
            FROM mutaboard_columns
            WHERE mutaboard_id = ?
            ORDER BY position, id;
            """,
            (mutaboard_id,),
        ).fetchall()
        return [self._mutaboard_column_from_row(row) for row in rows]

    def replace_mutaboard_columns(
        self,
        mutaboard_id: int,
        columns: Iterable[tuple[str, str]],
    ) -> List[MutaBoardColumnData]:
        normalized = []
        for position, (kind, title) in enumerate(columns):
            normalized.append((self._normalize_mutaboard_kind(kind), (title or "").strip(), position))
        if not normalized:
            normalized = [(kind, "", position) for position, kind in enumerate(_DEFAULT_MUTABOARD_COLUMN_KINDS)]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute("DELETE FROM mutaboard_columns WHERE mutaboard_id = ?;", (mutaboard_id,))
            for kind, title, position in normalized:
                self._conn.execute(
                    """
                    INSERT INTO mutaboard_columns (
                        mutaboard_id,
                        kind,
                        title,
                        position,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (mutaboard_id, kind, title, position, now, now),
                )
        self._touch_mutaboard(mutaboard_id)
        return self.fetch_mutaboard_columns(mutaboard_id)

    def add_mutaboard_column(self, mutaboard_id: int, kind: str, title: str = "") -> MutaBoardColumnData:
        kind = self._normalize_mutaboard_kind(kind)
        title = (title or "").strip()
        row = self._conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS max_position FROM mutaboard_columns WHERE mutaboard_id = ?;",
            (mutaboard_id,),
        ).fetchone()
        position = int(row["max_position"]) + 1 if row else 0
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO mutaboard_columns (
                    mutaboard_id,
                    kind,
                    title,
                    position,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (mutaboard_id, kind, title, position, now, now),
            )
        self._touch_mutaboard(mutaboard_id)
        column = self._fetch_mutaboard_column_by_id(int(cur.lastrowid))
        assert column is not None
        return column

    def update_mutaboard_column(
        self,
        column_id: int,
        *,
        kind: str,
        title: str,
        position: int | None = None,
    ) -> MutaBoardColumnData:
        current = self._fetch_mutaboard_column_by_id(column_id)
        if current is None:
            raise ValueError("Колонка мутборда не найдена.")
        next_position = current.position if position is None else max(0, int(position))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE mutaboard_columns
                SET kind = ?, title = ?, position = ?, updated_at = ?
                WHERE id = ?;
                """,
                (self._normalize_mutaboard_kind(kind), (title or "").strip(), next_position, now, column_id),
            )
        self._touch_mutaboard(current.mutaboard_id)
        updated = self._fetch_mutaboard_column_by_id(column_id)
        assert updated is not None
        return updated

    def fetch_mutaboard_items(self, mutaboard_id: int) -> List[MutaBoardItemData]:
        rows = self._conn.execute(
            """
            SELECT id, mutaboard_id, entity_kind, entity_id, created_at
            FROM mutaboard_items
            WHERE mutaboard_id = ?
            ORDER BY created_at DESC, id DESC;
            """,
            (mutaboard_id,),
        ).fetchall()
        return [self._mutaboard_item_from_row(row) for row in rows]

    def attach_mutaboard_item(self, mutaboard_id: int, entity_kind: str, entity_id: int) -> MutaBoardItemData:
        entity_kind = self._normalize_mutaboard_kind(entity_kind)
        entity_id = int(entity_id)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO mutaboard_items (mutaboard_id, entity_kind, entity_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (mutaboard_id, entity_kind, entity_id, now),
            )
        self._touch_mutaboard(mutaboard_id)
        row = self._conn.execute(
            """
            SELECT id, mutaboard_id, entity_kind, entity_id, created_at
            FROM mutaboard_items
            WHERE mutaboard_id = ? AND entity_kind = ? AND entity_id = ?;
            """,
            (mutaboard_id, entity_kind, entity_id),
        ).fetchone()
        assert row is not None
        return self._mutaboard_item_from_row(row)

    def _fetch_mutaboard_by_id(self, mutaboard_id: int) -> Optional[MutaBoardData]:
        row = self._conn.execute(
            """
            SELECT id, title, description, capture_text, planning_text, links_text, created_at, updated_at
            FROM mutaboards
            WHERE id = ?;
            """,
            (mutaboard_id,),
        ).fetchone()
        return self._mutaboard_from_row(row) if row else None

    def _fetch_mutaboard_column_by_id(self, column_id: int) -> Optional[MutaBoardColumnData]:
        row = self._conn.execute(
            """
            SELECT id, mutaboard_id, kind, title, position, created_at, updated_at
            FROM mutaboard_columns
            WHERE id = ?;
            """,
            (column_id,),
        ).fetchone()
        return self._mutaboard_column_from_row(row) if row else None

    def _touch_mutaboard(self, mutaboard_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute("UPDATE mutaboards SET updated_at = ? WHERE id = ?;", (now, mutaboard_id))

    @staticmethod
    def _normalize_mutaboard_kind(kind: str) -> str:
        normalized = (kind or "").strip().lower()
        if normalized not in _MUTABOARD_ENTITY_KINDS:
            raise ValueError("Неподдерживаемый тип колонки мутборда.")
        return normalized

    def _normalize_mutaboard_column_kinds(self, column_kinds: Iterable[str] | None) -> list[str]:
        result: list[str] = []
        for kind in column_kinds or _DEFAULT_MUTABOARD_COLUMN_KINDS:
            normalized = self._normalize_mutaboard_kind(kind)
            if normalized in result:
                continue
            result.append(normalized)
        return result or list(_DEFAULT_MUTABOARD_COLUMN_KINDS)

    @staticmethod
    def _mutaboard_from_row(row: sqlite3.Row) -> MutaBoardData:
        return MutaBoardData(
            id=row["id"],
            title=row["title"] or "",
            description=row["description"] or "",
            capture_text=row["capture_text"] or "",
            planning_text=row["planning_text"] or "",
            links_text=row["links_text"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _mutaboard_column_from_row(row: sqlite3.Row) -> MutaBoardColumnData:
        return MutaBoardColumnData(
            id=row["id"],
            mutaboard_id=row["mutaboard_id"],
            kind=row["kind"],
            title=row["title"] or "",
            position=int(row["position"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _mutaboard_item_from_row(row: sqlite3.Row) -> MutaBoardItemData:
        return MutaBoardItemData(
            id=row["id"],
            mutaboard_id=row["mutaboard_id"],
            entity_kind=row["entity_kind"],
            entity_id=int(row["entity_id"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


__all__ = ["DatabaseMutaBoardsMixin"]
