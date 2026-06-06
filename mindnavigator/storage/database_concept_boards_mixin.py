"""DatabaseConceptBoardsMixin for concept board storage operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

_DEFAULT_CONCEPT_BOARD_COLUMN_KINDS = ("task", "idea", "image")
_CONCEPT_BOARD_COLUMN_KINDS = (
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
_CONCEPT_BOARD_ENTITY_KINDS = _CONCEPT_BOARD_COLUMN_KINDS
_CONCEPT_BOARD_LINK_TYPES = ("relates_to", "inspires", "develops", "transforms_to", "contradicts")


class DatabaseConceptBoardsMixin:
    def fetch_concept_boards(self) -> List[ConceptBoardData]:
        rows = self._conn.execute(
            """
            SELECT id, title, description, capture_text, planning_text, links_text, created_at, updated_at
            FROM mutaboards
            ORDER BY updated_at DESC, id DESC;
            """
        ).fetchall()
        return [self._concept_board_from_row(row) for row in rows]

    def create_concept_board(
        self,
        title: str,
        description: str = "",
        capture_text: str = "",
        planning_text: str = "",
        links_text: str = "",
        column_kinds: Iterable[str] | None = None,
    ) -> ConceptBoardData:
        title = validate_title(title, field_name="Название мутборда")
        description = (description or "").strip()
        capture_text = (capture_text or "").strip()
        planning_text = (planning_text or "").strip()
        links_text = (links_text or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        normalized_kinds = self._normalize_concept_board_column_kinds(column_kinds)
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
        concept_board_id = int(cur.lastrowid)
        self.replace_concept_board_columns(concept_board_id, [(kind, "") for kind in normalized_kinds])
        created = self._fetch_concept_board_by_id(concept_board_id)
        assert created is not None
        return created

    def update_concept_board(
        self,
        concept_board_id: int,
        *,
        title: str,
        description: str,
        capture_text: str,
        planning_text: str,
        links_text: str,
    ) -> ConceptBoardData:
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
                (title, description, capture_text, planning_text, links_text, now, concept_board_id),
            )
        updated = self._fetch_concept_board_by_id(concept_board_id)
        assert updated is not None
        return updated

    def fetch_concept_board_columns(self, concept_board_id: int) -> List[ConceptBoardColumnData]:
        rows = self._conn.execute(
            """
            SELECT id, mutaboard_id, kind, title, position, created_at, updated_at
            FROM mutaboard_columns
            WHERE mutaboard_id = ?
            ORDER BY position, id;
            """,
            (concept_board_id,),
        ).fetchall()
        return [self._concept_board_column_from_row(row) for row in rows]

    def replace_concept_board_columns(
        self,
        concept_board_id: int,
        columns: Iterable[tuple[str, str]],
    ) -> List[ConceptBoardColumnData]:
        normalized = []
        for position, (kind, title) in enumerate(columns):
            normalized.append((self._normalize_concept_board_kind(kind), (title or "").strip(), position))
        if not normalized:
            normalized = [(kind, "", position) for position, kind in enumerate(_DEFAULT_CONCEPT_BOARD_COLUMN_KINDS)]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute("DELETE FROM mutaboard_columns WHERE mutaboard_id = ?;", (concept_board_id,))
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
                    (concept_board_id, kind, title, position, now, now),
                )
        self._touch_concept_board(concept_board_id)
        return self.fetch_concept_board_columns(concept_board_id)

    def add_concept_board_column(self, concept_board_id: int, kind: str, title: str = "") -> ConceptBoardColumnData:
        kind = self._normalize_concept_board_kind(kind)
        title = (title or "").strip()
        row = self._conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS max_position FROM mutaboard_columns WHERE mutaboard_id = ?;",
            (concept_board_id,),
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
                (concept_board_id, kind, title, position, now, now),
            )
        self._touch_concept_board(concept_board_id)
        column = self._fetch_concept_board_column_by_id(int(cur.lastrowid))
        assert column is not None
        return column

    def update_concept_board_column(
        self,
        column_id: int,
        *,
        kind: str,
        title: str,
        position: int | None = None,
    ) -> ConceptBoardColumnData:
        current = self._fetch_concept_board_column_by_id(column_id)
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
                (self._normalize_concept_board_kind(kind), (title or "").strip(), next_position, now, column_id),
            )
        self._touch_concept_board(current.concept_board_id)
        updated = self._fetch_concept_board_column_by_id(column_id)
        assert updated is not None
        return updated

    def fetch_concept_board_items(self, concept_board_id: int) -> List[ConceptBoardItemData]:
        rows = self._conn.execute(
            """
            SELECT id, mutaboard_id, entity_kind, entity_id, created_at
            FROM mutaboard_items
            WHERE mutaboard_id = ?
            ORDER BY created_at DESC, id DESC;
            """,
            (concept_board_id,),
        ).fetchall()
        return [self._concept_board_item_from_row(row) for row in rows]

    def attach_concept_board_item(self, concept_board_id: int, entity_kind: str, entity_id: int) -> ConceptBoardItemData:
        entity_kind = self._normalize_concept_board_kind(entity_kind)
        entity_id = int(entity_id)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.transaction():
            self._conn.execute(
                """
                INSERT OR IGNORE INTO mutaboard_items (mutaboard_id, entity_kind, entity_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (concept_board_id, entity_kind, entity_id, now),
            )
        self._touch_concept_board(concept_board_id)
        row = self._conn.execute(
            """
            SELECT id, mutaboard_id, entity_kind, entity_id, created_at
            FROM mutaboard_items
            WHERE mutaboard_id = ? AND entity_kind = ? AND entity_id = ?;
            """,
            (concept_board_id, entity_kind, entity_id),
        ).fetchone()
        assert row is not None
        return self._concept_board_item_from_row(row)

    def fetch_concept_board_versions(self, concept_board_id: int) -> List[ConceptBoardVersionData]:
        rows = self._conn.execute(
            """
            SELECT id, mutaboard_id, title, description, why_yes, why_no, checks_text, status, created_at, updated_at
            FROM mutaboard_versions
            WHERE mutaboard_id = ?
            ORDER BY updated_at DESC, id DESC;
            """,
            (concept_board_id,),
        ).fetchall()
        return [self._concept_board_version_from_row(row) for row in rows]

    def create_concept_board_version(
        self,
        concept_board_id: int,
        *,
        title: str,
        description: str = "",
        why_yes: str = "",
        why_no: str = "",
        checks_text: str = "",
        status: str = "draft",
    ) -> ConceptBoardVersionData:
        title = validate_title(title, field_name="Название версии концептборда")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO mutaboard_versions (
                    mutaboard_id, title, description, why_yes, why_no, checks_text, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    concept_board_id,
                    title,
                    (description or "").strip(),
                    (why_yes or "").strip(),
                    (why_no or "").strip(),
                    (checks_text or "").strip(),
                    (status or "draft").strip().lower() or "draft",
                    now,
                    now,
                ),
            )
        self._touch_concept_board(concept_board_id)
        created = self._fetch_concept_board_version_by_id(int(cur.lastrowid))
        assert created is not None
        return created

    def update_concept_board_version(
        self,
        version_id: int,
        *,
        title: str,
        description: str,
        why_yes: str,
        why_no: str,
        checks_text: str,
        status: str,
    ) -> ConceptBoardVersionData:
        current = self._fetch_concept_board_version_by_id(version_id)
        if current is None:
            raise ValueError("Версия концептборда не найдена.")
        title = validate_title(title, field_name="Название версии концептборда")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE mutaboard_versions
                SET title = ?, description = ?, why_yes = ?, why_no = ?, checks_text = ?, status = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    (description or "").strip(),
                    (why_yes or "").strip(),
                    (why_no or "").strip(),
                    (checks_text or "").strip(),
                    (status or "draft").strip().lower() or "draft",
                    now,
                    version_id,
                ),
            )
        self._touch_concept_board(current.concept_board_id)
        updated = self._fetch_concept_board_version_by_id(version_id)
        assert updated is not None
        return updated

    def fetch_concept_board_solutions(self, concept_board_id: int) -> List[ConceptBoardSolutionData]:
        rows = self._conn.execute(
            """
            SELECT id, mutaboard_id, title, summary, why_selected, rejected_text, next_steps_text, status,
                   selected_version_id, decided_at, created_at, updated_at
            FROM mutaboard_solutions
            WHERE mutaboard_id = ?
            ORDER BY updated_at DESC, id DESC;
            """,
            (concept_board_id,),
        ).fetchall()
        return [self._concept_board_solution_from_row(row) for row in rows]

    def create_concept_board_solution(
        self,
        concept_board_id: int,
        *,
        title: str,
        summary: str = "",
        why_selected: str = "",
        rejected_text: str = "",
        next_steps_text: str = "",
        status: str = "draft",
        selected_version_id: int | None = None,
        decided_at: str = "",
    ) -> ConceptBoardSolutionData:
        title = validate_title(title, field_name="Название решения концептборда")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO mutaboard_solutions (
                    mutaboard_id, title, summary, why_selected, rejected_text, next_steps_text, status,
                    selected_version_id, decided_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    concept_board_id,
                    title,
                    (summary or "").strip(),
                    (why_selected or "").strip(),
                    (rejected_text or "").strip(),
                    (next_steps_text or "").strip(),
                    (status or "draft").strip().lower() or "draft",
                    selected_version_id,
                    (decided_at or "").strip(),
                    now,
                    now,
                ),
            )
        self._touch_concept_board(concept_board_id)
        created = self._fetch_concept_board_solution_by_id(int(cur.lastrowid))
        assert created is not None
        return created

    def update_concept_board_solution(
        self,
        solution_id: int,
        *,
        title: str,
        summary: str,
        why_selected: str,
        rejected_text: str,
        next_steps_text: str,
        status: str,
        selected_version_id: int | None,
        decided_at: str,
    ) -> ConceptBoardSolutionData:
        current = self._fetch_concept_board_solution_by_id(solution_id)
        if current is None:
            raise ValueError("Решение концептборда не найдено.")
        title = validate_title(title, field_name="Название решения концептборда")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE mutaboard_solutions
                SET title = ?, summary = ?, why_selected = ?, rejected_text = ?, next_steps_text = ?, status = ?,
                    selected_version_id = ?, decided_at = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    (summary or "").strip(),
                    (why_selected or "").strip(),
                    (rejected_text or "").strip(),
                    (next_steps_text or "").strip(),
                    (status or "draft").strip().lower() or "draft",
                    selected_version_id,
                    (decided_at or "").strip(),
                    now,
                    solution_id,
                ),
            )
        self._touch_concept_board(current.concept_board_id)
        updated = self._fetch_concept_board_solution_by_id(solution_id)
        assert updated is not None
        return updated

    def fetch_concept_board_links(
        self,
        concept_board_id: int,
        *,
        source_kind: str | None = None,
        source_id: int | None = None,
        target_kind: str | None = None,
        target_id: int | None = None,
    ) -> List[ConceptBoardLinkData]:
        query = [
            "SELECT id, mutaboard_id, source_kind, source_id, target_kind, target_id, link_type, created_at",
            "FROM mutaboard_links",
            "WHERE mutaboard_id = ?",
        ]
        params: list[object] = [concept_board_id]
        if source_kind is not None:
            query.append("AND source_kind = ?")
            params.append(self._normalize_concept_board_kind(source_kind))
        if source_id is not None:
            query.append("AND source_id = ?")
            params.append(int(source_id))
        if target_kind is not None:
            query.append("AND target_kind = ?")
            params.append(self._normalize_concept_board_kind(target_kind))
        if target_id is not None:
            query.append("AND target_id = ?")
            params.append(int(target_id))
        query.append("ORDER BY created_at DESC, id DESC;")
        rows = self._conn.execute("\n".join(query), tuple(params)).fetchall()
        return [self._concept_board_link_from_row(row) for row in rows]

    def add_concept_board_link(
        self,
        concept_board_id: int,
        *,
        source_kind: str,
        source_id: int,
        target_kind: str,
        target_id: int,
        link_type: str = "relates_to",
    ) -> ConceptBoardLinkData:
        source_kind = self._normalize_concept_board_kind(source_kind)
        target_kind = self._normalize_concept_board_kind(target_kind)
        link_type = self._normalize_concept_board_link_type(link_type)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO mutaboard_links (
                    mutaboard_id, source_kind, source_id, target_kind, target_id, link_type, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (concept_board_id, source_kind, int(source_id), target_kind, int(target_id), link_type, now),
            )
        self._touch_concept_board(concept_board_id)
        row = self._conn.execute(
            """
            SELECT id, mutaboard_id, source_kind, source_id, target_kind, target_id, link_type, created_at
            FROM mutaboard_links
            WHERE mutaboard_id = ? AND source_kind = ? AND source_id = ? AND target_kind = ? AND target_id = ? AND link_type = ?;
            """,
            (concept_board_id, source_kind, int(source_id), target_kind, int(target_id), link_type),
        ).fetchone()
        assert row is not None
        return self._concept_board_link_from_row(row)

    def _fetch_concept_board_by_id(self, concept_board_id: int) -> Optional[ConceptBoardData]:
        row = self._conn.execute(
            """
            SELECT id, title, description, capture_text, planning_text, links_text, created_at, updated_at
            FROM mutaboards
            WHERE id = ?;
            """,
            (concept_board_id,),
        ).fetchone()
        return self._concept_board_from_row(row) if row else None

    def _fetch_concept_board_column_by_id(self, column_id: int) -> Optional[ConceptBoardColumnData]:
        row = self._conn.execute(
            """
            SELECT id, mutaboard_id, kind, title, position, created_at, updated_at
            FROM mutaboard_columns
            WHERE id = ?;
            """,
            (column_id,),
        ).fetchone()
        return self._concept_board_column_from_row(row) if row else None

    def _touch_concept_board(self, concept_board_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.transaction():
            self._conn.execute("UPDATE mutaboards SET updated_at = ? WHERE id = ?;", (now, concept_board_id))

    @staticmethod
    def _normalize_concept_board_kind(kind: str) -> str:
        normalized = (kind or "").strip().lower()
        if normalized not in _CONCEPT_BOARD_ENTITY_KINDS:
            raise ValueError("Неподдерживаемый тип колонки мутборда.")
        return normalized

    @staticmethod
    def _normalize_concept_board_link_type(link_type: str) -> str:
        normalized = (link_type or "").strip().lower()
        if normalized not in _CONCEPT_BOARD_LINK_TYPES:
            return "relates_to"
        return normalized

    def _normalize_concept_board_column_kinds(self, column_kinds: Iterable[str] | None) -> list[str]:
        result: list[str] = []
        for kind in column_kinds or _DEFAULT_CONCEPT_BOARD_COLUMN_KINDS:
            normalized = self._normalize_concept_board_kind(kind)
            if normalized in result:
                continue
            result.append(normalized)
        return result or list(_DEFAULT_CONCEPT_BOARD_COLUMN_KINDS)

    @staticmethod
    def _concept_board_from_row(row: sqlite3.Row) -> ConceptBoardData:
        return ConceptBoardData(
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
    def _concept_board_column_from_row(row: sqlite3.Row) -> ConceptBoardColumnData:
        return ConceptBoardColumnData(
            id=row["id"],
            concept_board_id=row["mutaboard_id"],
            kind=row["kind"],
            title=row["title"] or "",
            position=int(row["position"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _concept_board_item_from_row(row: sqlite3.Row) -> ConceptBoardItemData:
        return ConceptBoardItemData(
            id=row["id"],
            concept_board_id=row["mutaboard_id"],
            entity_kind=row["entity_kind"],
            entity_id=int(row["entity_id"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _concept_board_version_from_row(row: sqlite3.Row) -> ConceptBoardVersionData:
        return ConceptBoardVersionData(
            id=row["id"],
            concept_board_id=row["mutaboard_id"],
            title=row["title"] or "",
            description=row["description"] or "",
            why_yes=row["why_yes"] or "",
            why_no=row["why_no"] or "",
            checks_text=row["checks_text"] or "",
            status=row["status"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _concept_board_solution_from_row(row: sqlite3.Row) -> ConceptBoardSolutionData:
        return ConceptBoardSolutionData(
            id=row["id"],
            concept_board_id=row["mutaboard_id"],
            title=row["title"] or "",
            summary=row["summary"] or "",
            why_selected=row["why_selected"] or "",
            rejected_text=row["rejected_text"] or "",
            next_steps_text=row["next_steps_text"] or "",
            status=row["status"] or "",
            selected_version_id=row["selected_version_id"],
            decided_at=row["decided_at"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _concept_board_link_from_row(row: sqlite3.Row) -> ConceptBoardLinkData:
        return ConceptBoardLinkData(
            id=row["id"],
            concept_board_id=row["mutaboard_id"],
            source_kind=row["source_kind"] or "",
            source_id=int(row["source_id"]),
            target_kind=row["target_kind"] or "",
            target_id=int(row["target_id"]),
            link_type=row["link_type"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _fetch_concept_board_version_by_id(self, version_id: int) -> Optional[ConceptBoardVersionData]:
        row = self._conn.execute(
            """
            SELECT id, mutaboard_id, title, description, why_yes, why_no, checks_text, status, created_at, updated_at
            FROM mutaboard_versions
            WHERE id = ?;
            """,
            (version_id,),
        ).fetchone()
        return self._concept_board_version_from_row(row) if row else None

    def _fetch_concept_board_solution_by_id(self, solution_id: int) -> Optional[ConceptBoardSolutionData]:
        row = self._conn.execute(
            """
            SELECT id, mutaboard_id, title, summary, why_selected, rejected_text, next_steps_text, status,
                   selected_version_id, decided_at, created_at, updated_at
            FROM mutaboard_solutions
            WHERE id = ?;
            """,
            (solution_id,),
        ).fetchone()
        return self._concept_board_solution_from_row(row) if row else None


__all__ = ["DatabaseConceptBoardsMixin"]
