
from __future__ import annotations

from typing import List, Tuple

from ..db import connect


class FileLinksRepo:
    def __init__(self, db_path=None):
        self._db_path = db_path

    def list_links_for_file(self, file_id: int) -> List[Tuple[str, int]]:
        conn = connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT entity_type, entity_id FROM file_links WHERE file_id=? ORDER BY entity_type, entity_id",
                (file_id,),
            ).fetchall()
            return [(str(r["entity_type"]), int(r["entity_id"])) for r in rows]
        finally:
            conn.close()

    def set_links(self, file_id: int, links: List[Tuple[str, int]]) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute("DELETE FROM file_links WHERE file_id=?", (file_id,))
            for t, eid in links:
                conn.execute(
                    "INSERT OR IGNORE INTO file_links(file_id, entity_type, entity_id, created_at) "
                    "VALUES(?,?,?, datetime('now'))",
                    (file_id, str(t), int(eid)),
                )
            conn.commit()
        finally:
            conn.close()

    def count_links(self, file_id: int) -> int:
        conn = connect(self._db_path)
        try:
            r = conn.execute("SELECT COUNT(1) AS c FROM file_links WHERE file_id=?", (file_id,)).fetchone()
            return int(r["c"]) if r else 0
        finally:
            conn.close()
