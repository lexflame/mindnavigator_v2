"""Context entity link persistence."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .context_entity_link_data import ContextEntityLinkData


class DatabaseContextLinksMixin:
    _CONTEXT_ENTITY_TYPES = {"task", "idea", "note", "object"}

    @classmethod
    def _normalize_context_entity_type(cls, entity_type: str) -> str:
        normalized = (entity_type or "").strip().lower()
        if normalized not in cls._CONTEXT_ENTITY_TYPES:
            supported = ", ".join(sorted(cls._CONTEXT_ENTITY_TYPES))
            raise ValueError(f"Unsupported context entity type: {entity_type!r}. Expected one of: {supported}.")
        return normalized

    def fetch_context_entity_links(
        self,
        *,
        source_type: Optional[str] = None,
        source_id: Optional[int] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
    ) -> List[ContextEntityLinkData]:
        clauses: list[str] = []
        params: list[object] = []
        if source_type is not None:
            clauses.append("source_type = ?")
            params.append(self._normalize_context_entity_type(source_type))
        if source_id is not None:
            clauses.append("source_id = ?")
            params.append(int(source_id))
        if target_type is not None:
            clauses.append("target_type = ?")
            params.append(self._normalize_context_entity_type(target_type))
        if target_id is not None:
            clauses.append("target_id = ?")
            params.append(int(target_id))
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT id, source_type, source_id, target_type, target_id, anchor_text, source_field, created_at
            FROM context_entity_links
            {where_sql}
            ORDER BY created_at DESC, id DESC;
            """,
            tuple(params),
        ).fetchall()
        return [self._context_entity_link_from_row(row) for row in rows]

    def add_context_entity_link(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        anchor_text: str = "",
        source_field: str = "",
    ) -> ContextEntityLinkData:
        normalized_source = self._normalize_context_entity_type(source_type)
        normalized_target = self._normalize_context_entity_type(target_type)
        normalized_source_id = int(source_id)
        normalized_target_id = int(target_id)
        if normalized_source_id <= 0 or normalized_target_id <= 0:
            raise ValueError("Context link entity ids must be positive.")
        anchor = (anchor_text or "").strip()
        field = (source_field or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO context_entity_links (
                    source_type, source_id, target_type, target_id, anchor_text, source_field, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (normalized_source, normalized_source_id, normalized_target, normalized_target_id, anchor, field, now),
            )
        row = self._conn.execute(
            """
            SELECT id, source_type, source_id, target_type, target_id, anchor_text, source_field, created_at
            FROM context_entity_links
            WHERE source_type = ? AND source_id = ? AND target_type = ? AND target_id = ?
              AND anchor_text = ? AND source_field = ?;
            """,
            (normalized_source, normalized_source_id, normalized_target, normalized_target_id, anchor, field),
        ).fetchone()
        if row is None:
            raise ValueError("Failed to create context entity link.")
        return self._context_entity_link_from_row(row)

    @staticmethod
    def _context_entity_link_from_row(row) -> ContextEntityLinkData:
        return ContextEntityLinkData(
            id=int(row["id"]),
            source_type=str(row["source_type"] or ""),
            source_id=int(row["source_id"]),
            target_type=str(row["target_type"] or ""),
            target_id=int(row["target_id"]),
            anchor_text=str(row["anchor_text"] or ""),
            source_field=str(row["source_field"] or ""),
            created_at=str(row["created_at"] or ""),
        )


__all__ = ["DatabaseContextLinksMixin"]
