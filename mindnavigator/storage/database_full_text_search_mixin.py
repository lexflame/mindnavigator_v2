"""Fallback-compatible full-text search over primary text entities."""

from __future__ import annotations

import re
import sqlite3


_FTS_QUERY_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)


class DatabaseFullTextSearchMixin:
    @staticmethod
    def _fts_query(search_text: str) -> str:
        tokens = _FTS_QUERY_TOKEN_RE.findall(str(search_text or "").casefold())
        return " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens)

    def search_full_text(self, search_text: str, *, limit: int = 50) -> list[dict[str, object]] | None:
        query = self._fts_query(search_text)
        if not query or limit <= 0:
            return []
        searches = (
            (
                "task",
                """
                SELECT t.id, t.title, COALESCE(t.description, '') AS detail, bm25(tasks_fts) AS rank
                FROM tasks_fts JOIN tasks t ON t.id = tasks_fts.rowid
                WHERE tasks_fts MATCH ? ORDER BY rank, t.id LIMIT ?;
                """,
            ),
            (
                "idea",
                """
                SELECT i.id, i.title, COALESCE(i.summary, i.body_md, '') AS detail, bm25(ideas_fts) AS rank
                FROM ideas_fts JOIN ideas i ON i.id = ideas_fts.rowid
                WHERE ideas_fts MATCH ? ORDER BY rank, i.id LIMIT ?;
                """,
            ),
            (
                "note",
                """
                SELECT n.id, n.title, COALESCE(NULLIF(n.project, ''), n.preview, '') AS detail, bm25(notes_fts) AS rank
                FROM notes_fts JOIN notes n ON n.id = notes_fts.rowid
                WHERE notes_fts MATCH ? ORDER BY rank, n.id LIMIT ?;
                """,
            ),
            (
                "object",
                """
                SELECT o.id, o.title,
                       trim(COALESCE(o.catalog, '') || ' · ' || COALESCE(o.object_type, '') || ' · ' || COALESCE(o.status, ''), ' ·') AS detail,
                       bm25(objects_fts) AS rank
                FROM objects_fts JOIN objects o ON o.id = objects_fts.rowid
                WHERE objects_fts MATCH ? ORDER BY rank, o.id LIMIT ?;
                """,
            ),
        )
        results: list[dict[str, object]] = []
        try:
            for entity_kind, sql in searches:
                rows = self._conn.execute(sql, (query, int(limit))).fetchall()
                results.extend(
                    {
                        "entity": entity_kind,
                        "id": int(row["id"]),
                        "title": str(row["title"] or ""),
                        "detail": str(row["detail"] or ""),
                        "rank": float(row["rank"]),
                    }
                    for row in rows
                )
        except sqlite3.OperationalError:
            return None
        results.sort(key=lambda item: (float(item["rank"]), str(item["entity"]), int(item["id"])))
        return results[: int(limit)]


__all__ = ["DatabaseFullTextSearchMixin"]
